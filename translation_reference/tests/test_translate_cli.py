# -*- coding: utf-8 -*-
"""Testes offline do CLI translate_game_text.py (unittest, somente stdlib).

Cobertura exigida pela Fase 2:
- TM hit nao chama o engine;
- relatorio CSV com status corretos (tm_hit/llm/needs_review/failed);
- nenhum arquivo fora da area de saida e escrito (hash dos fixtures antes/depois);
- --dry-run nao escreve nada em disco;
- progresso incremental: "PROGRESS 0/N" sai ANTES da primeira chamada ao
  engine e "PROGRESS i/N" incremental enquanto cada chunk e resolvido;
- linhas JSONL invalidas sao ignoradas e contadas;
- modo resiliente: item com indice falho vira "failed" individual no CSV
  com nota curta, sem afetar os vizinhos do mesmo lote;
- motivo reportado pelo engine via collect_reasons chega ao CSV
  ("motor de traducao indisponivel" em vez de nota generica);
- falha sistematica (todos os itens) emite AVISO agregado no stdout;
- --chunk-size chega ao construtor do engine (padrao 10, faixa 1..50).
"""
import csv
import hashlib
import io
import json
import shutil
import sys
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent / "scripts"
LIB_DIR = SCRIPTS_DIR / "lib"
for extra in (str(SCRIPTS_DIR), str(LIB_DIR)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

import translate_game_text as tcli  # noqa: E402
from translation_engine import NOTE_UNAVAILABLE, TranslationError  # noqa: E402

FIXTURES_ROOT = HERE / "fixtures"
FIXTURES_GAME = FIXTURES_ROOT / "game"
TM_FIXTURE = FIXTURES_ROOT / "tm" / "sample_tm.jsonl"
SCAN_FIXTURE = FIXTURES_ROOT / "report" / "sample_scan.jsonl"
WORK = HERE / "tmp_cli"


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot(root):
    base = Path(root)
    if not base.exists():
        return {}
    return {
        str(p.relative_to(base)).replace("\\", "/"): sha256_of(p)
        for p in sorted(base.rglob("*"))
        if p.is_file()
    }


class FakeEngine:
    """Engine injetavel: devolve mapeamento fixo ou prefixo EN:.

    Implementa o contrato resiliente usado pelo CLI; ``fail_indices``
    marca posicoes que falham individualmente (traducao "" + indice em
    ``failed_indices``) e ``fail=True`` derruba o lote inteiro.
    """

    def __init__(self, mapping=None, fail=False, fail_indices=None):
        self.calls = []
        self.mapping = dict(mapping or {})
        self.fail = fail
        self.fail_indices = set(fail_indices or ())

    def translate_batch(self, texts):
        self.calls.append(list(texts))
        if self.fail:
            raise TranslationError("Servidor de traducao indisponivel apos 1 tentativas.")
        return [self.mapping.get(t, "EN:" + t) for t in texts]

    def translate_batch_resilient(self, texts):
        self.calls.append(list(texts))
        if self.fail:
            raise TranslationError("Servidor de traducao indisponivel apos 1 tentativas.")
        outputs = []
        failed_indices = []
        for index, text in enumerate(texts):
            if index in self.fail_indices:
                outputs.append("")
                failed_indices.append(index)
            else:
                outputs.append(self.mapping.get(text, "EN:" + text))
        return outputs, failed_indices


class ReasonsFakeEngine(FakeEngine):
    """FakeEngine que tambem reporta o motivo por item (collect_reasons)."""

    def __init__(self, mapping=None, fail_indices=None, reason=NOTE_UNAVAILABLE):
        super().__init__(mapping=mapping, fail_indices=fail_indices)
        self.reason = reason

    def translate_batch_resilient(
        self, texts, on_progress=None, collect_reasons=None
    ):
        self.calls.append(list(texts))
        outputs = []
        for index, text in enumerate(texts):
            if index in self.fail_indices:
                outputs.append("")
                if collect_reasons is not None:
                    collect_reasons[index] = self.reason
            else:
                outputs.append(self.mapping.get(text, "EN:" + text))
        failed = [i for i in range(len(texts)) if i in self.fail_indices]
        return outputs, failed


class RecordingEngine:
    """Substituto de OpenAICompatEngine que captura os kwargs do construtor."""

    instances = []

    def __init__(self, **kwargs):
        self.kwargs = dict(kwargs)
        self.fake = FakeEngine()
        RecordingEngine.instances.append(self)

    def translate_batch(self, texts):
        return self.fake.translate_batch(texts)

    def translate_batch_resilient(self, texts):
        return self.fake.translate_batch_resilient(texts)


class SlowResilientEngine:
    """Engine fake LENTO que segue o contrato do OpenAICompatEngine real.

    Aceita ``on_progress`` (como o engine real apos a correcao), dorme um
    pouco por chunk para simular LLM local e imprime um marcador
    ``ENGINE-CHUNK`` ANTES de reportar o progresso daquele chunk. Isso
    permite provar, pela ordem do stdout, que "PROGRESS 0/N" sai antes da
    primeira traducao e que os incrementos acompanham cada chunk.
    """

    def __init__(self, chunk_size=2, delay=0.02):
        self.chunk_size = chunk_size
        self.delay = delay

    def translate_batch_resilient(self, texts, on_progress=None):
        outputs = []
        failed_indices = []
        for start in range(0, len(texts), self.chunk_size):
            time.sleep(self.delay)
            chunk = texts[start : start + self.chunk_size]
            print("ENGINE-CHUNK %d" % len(chunk))
            outputs.extend("EN:" + text for text in chunk)
            if on_progress is not None:
                on_progress(min(start + self.chunk_size, len(texts)), len(texts))
        return outputs, failed_indices


def write_scan(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def make_row(item_id, rel_file, line, text, encoding="utf-8-sig", source_key=""):
    ext = "." + rel_file.rsplit(".", 1)[-1].lower()
    return {
        "item_id": item_id,
        "batch": "B0001",
        "root": str(FIXTURES_GAME),
        "file": rel_file,
        "line": line,
        "extension": ext,
        "encoding": encoding,
        "reason": "kana",
        "category": "documentation",
        "priority": 35,
        "source_key": source_key,
        "occurrences": 1,
        "text": text,
    }


def read_csv_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


class TranslateCliCase(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(WORK, ignore_errors=True)
        WORK.mkdir(parents=True)
        self.fixtures_snapshot = snapshot(FIXTURES_ROOT)

    def tearDown(self):
        shutil.rmtree(WORK, ignore_errors=True)

    def assert_fixtures_untouched(self):
        self.assertEqual(snapshot(FIXTURES_ROOT), self.fixtures_snapshot)

    def copied_tm(self):
        """Copia a TM compartilhada para temp: nenhum teste grava em fixtures."""
        target = WORK / "tm" / "sample_tm.jsonl"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(TM_FIXTURE, target)
        return target


class TmHitTests(TranslateCliCase):
    def test_tm_hit_does_not_call_engine(self):
        scan = write_scan(
            WORK / "scan.jsonl",
            [
                make_row("T000001", "txt/demo.txt", 2, "これは日本語のテキストです。"),
            ],
        )
        out_dir = WORK / "reports" / "translated" / "jogo"
        engine = FakeEngine()
        result = tcli.run_translate(
            scan_path=scan,
            out_dir=out_dir,
            tm_path=self.copied_tm(),
            engine=engine,
            dry_run=False,
        )
        self.assertEqual(engine.calls, [])
        self.assertEqual(result["statuses"].get("tm_hit"), 1)
        records = read_csv_rows(result["csv_path"])
        self.assertEqual(records[0]["status"], "tm_hit")
        self.assertEqual(records[0]["translated"], "This is Japanese text.")
        self.assert_fixtures_untouched()


class ReportStatusTests(TranslateCliCase):
    def test_csv_report_statuses_and_columns(self):
        scan = write_scan(
            WORK / "scan.jsonl",
            [
                make_row("T000001", "txt/demo.txt", 2, "これは日本語のテキストです。"),
                make_row("T000002", "txt/demo.txt", 4, "{player_name}、こんにちは！"),
                make_row("T000003", "txt/script.rpy", 3, "こんにちは、世界。"),
                make_row("T000004", "data/Actors.json", 0, "アレックス", source_key="$[1].name"),
                make_row("T000005", "txt/demo.txt", 999, "存在しない行のテキスト。"),
                make_row("T000006", "txt/demo.txt", 4, "この行はファイルに存在しません。"),
            ],
        )
        out_dir = WORK / "out_status"
        engine = FakeEngine()
        result = tcli.run_translate(
            scan_path=scan,
            out_dir=out_dir,
            tm_path=self.copied_tm(),
            engine=engine,
            dry_run=False,
        )
        expected_header = [
            "item_id",
            "status",
            "file",
            "line",
            "source_key",
            "source",
            "translated",
            "notes",
        ]
        with open(result["csv_path"], newline="", encoding="utf-8-sig") as fh:
            header = next(csv.reader(fh))
        self.assertEqual(header, expected_header)
        records = {r["item_id"]: r for r in read_csv_rows(result["csv_path"])}
        self.assertEqual(records["T000001"]["status"], "tm_hit")
        self.assertEqual(records["T000002"]["status"], "llm")
        self.assertEqual(records["T000003"]["status"], "tm_hit")
        self.assertEqual(records["T000004"]["status"], "llm")
        # linha fora do intervalo: falha operacional
        self.assertEqual(records["T000005"]["status"], "failed")
        # trecho nao encontrado na linha alvo: precisa revisao
        self.assertEqual(records["T000006"]["status"], "needs_review")
        self.assertTrue(out_dir.joinpath("txt", "demo.txt").exists())
        self.assertTrue(out_dir.joinpath("txt", "script.rpy").exists())
        self.assertTrue(out_dir.joinpath("data", "Actors.json").exists())
        self.assert_fixtures_untouched()

    def test_new_llm_pairs_are_saved_to_tm(self):
        scan = write_scan(
            WORK / "scan.jsonl",
            [
                make_row("T000001", "txt/demo_cp932.txt", 1, "やあ、世界。", encoding="cp932"),
            ],
        )
        tm_path = WORK / "reports" / "tm" / "jogo.jsonl"
        result = tcli.run_translate(
            scan_path=scan,
            out_dir=WORK / "out_tm",
            tm_path=tm_path,
            engine=FakeEngine(),
            dry_run=False,
        )
        self.assertEqual(result["statuses"].get("llm"), 1)
        lines = [
            json.loads(line)
            for line in tm_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["source"], "やあ、世界。")
        self.assertEqual(lines[0]["target"], "EN:やあ、世界。")


class ResilientFailureReportTests(TranslateCliCase):
    def test_individual_failed_item_does_not_affect_neighbors(self):
        middle_text = "エンジンが失敗するテキスト。"
        scan = write_scan(
            WORK / "scan_resiliente.jsonl",
            [
                make_row("T000001", "txt/demo.txt", 4, "{player_name}、こんにちは！"),
                make_row("T000002", "txt/demo.txt", 999, middle_text),
                make_row(
                    "T000003",
                    "data/Actors.json",
                    0,
                    "アレックス",
                    source_key="$[1].name",
                ),
            ],
        )
        engine = FakeEngine(fail_indices={1})

        result = tcli.run_translate(
            scan_path=scan,
            out_dir=WORK / "out_resiliente",
            tm_path=None,
            engine=engine,
            dry_run=False,
        )

        self.assertEqual(result["statuses"].get("llm"), 2)
        self.assertEqual(result["statuses"].get("failed"), 1)
        records = {r["item_id"]: r for r in read_csv_rows(result["csv_path"])}
        # Item vizinho ANTES do falho segue normalmente.
        self.assertEqual(records["T000001"]["status"], "llm")
        self.assertEqual(records["T000001"]["translated"], "EN:{player_name}、こんにちは！")
        # Item falho: status failed INDIVIDUAL com nota curta do motivo.
        self.assertEqual(records["T000002"]["status"], "failed")
        self.assertEqual(records["T000002"]["translated"], "")
        self.assertIn("chunk divergente apos subdivisao", records["T000002"]["notes"])
        self.assertIn("sem traducao disponivel", records["T000002"]["notes"])
        # Item vizinho DEPOIS do falho tambem segue normalmente.
        self.assertEqual(records["T000003"]["status"], "llm")
        self.assertEqual(records["T000003"]["translated"], "EN:アレックス")
        self.assert_fixtures_untouched()

    def test_failed_item_is_not_saved_to_tm(self):
        middle_text = "エンジンが失敗するテキスト。"
        scan = write_scan(
            WORK / "scan_tm_fail.jsonl",
            [
                make_row("T000001", "txt/demo.txt", 4, "{player_name}、こんにちは！"),
                make_row("T000002", "txt/demo.txt", 999, middle_text),
            ],
        )
        tm_path = WORK / "reports" / "tm" / "jogo.jsonl"
        result = tcli.run_translate(
            scan_path=scan,
            out_dir=WORK / "out_tm_fail",
            tm_path=tm_path,
            engine=FakeEngine(fail_indices={1}),
            dry_run=False,
        )
        self.assertEqual(result["statuses"].get("failed"), 1)
        pairs = result["new_tm_pairs"]
        self.assertEqual(len(pairs), 1)
        self.assertNotEqual(pairs[0]["source"], middle_text)

    def test_engine_failure_reason_reaches_csv_notes(self):
        """Motivo real do engine (indisponivel) substitui a nota generica."""
        middle_text = "エンジンが失敗するテキスト。"
        scan = write_scan(
            WORK / "scan_reason.jsonl",
            [
                make_row("T000001", "txt/demo.txt", 4, "{player_name}、こんにちは！"),
                make_row("T000002", "txt/demo.txt", 999, middle_text),
            ],
        )
        engine = ReasonsFakeEngine(fail_indices={1}, reason=NOTE_UNAVAILABLE)

        result = tcli.run_translate(
            scan_path=scan,
            out_dir=WORK / "out_reason",
            tm_path=None,
            engine=engine,
            dry_run=False,
        )

        self.assertEqual(result["statuses"].get("llm"), 1)
        self.assertEqual(result["statuses"].get("failed"), 1)
        records = {r["item_id"]: r for r in read_csv_rows(result["csv_path"])}
        self.assertIn("motor de traducao indisponivel", records["T000002"]["notes"])
        self.assertNotIn(
            "chunk divergente apos subdivisao", records["T000002"]["notes"]
        )
        self.assertEqual(records["T000001"]["status"], "llm")

    def test_all_items_failed_prints_aggregate_warning(self):
        """Falha sistematica fica visivel no log, nao so no CSV."""
        middle_text = "エンジンが失敗するテキスト。"
        scan = write_scan(
            WORK / "scan_all_fail.jsonl",
            [
                make_row("T000001", "txt/demo.txt", 4, "{player_name}、こんにちは！"),
                make_row("T000002", "txt/demo.txt", 999, middle_text),
            ],
        )
        engine = ReasonsFakeEngine(
            fail_indices={0, 1}, reason=NOTE_UNAVAILABLE
        )

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            result = tcli.run_translate(
                scan_path=scan,
                out_dir=WORK / "out_all_fail",
                tm_path=None,
                engine=engine,
                dry_run=False,
            )
        output = buffer.getvalue()

        self.assertIn(
            "AVISO: o motor falhou para todos os 2 itens novos", output
        )
        records = {r["item_id"]: r for r in read_csv_rows(result["csv_path"])}
        for item_id in ("T000001", "T000002"):
            self.assertEqual(records[item_id]["status"], "failed")
            self.assertIn(
                "motor de traducao indisponivel", records[item_id]["notes"]
            )


class ChunkSizeFlagTests(TranslateCliCase):
    def _argv(self, scan):
        return [str(scan), "--out-dir", str(WORK / "out_chunk"), "--dry-run"]

    def test_chunk_size_default_and_custom_reach_engine_constructor(self):
        scan = write_scan(
            WORK / "scan_chunk.jsonl",
            [make_row("T000001", "txt/demo.txt", 2, "チャンクサイズのテスト。")],
        )

        with mock.patch.object(tcli, "OpenAICompatEngine", RecordingEngine):
            RecordingEngine.instances = []
            self.assertEqual(tcli.main(self._argv(scan)), 0)
            self.assertEqual(len(RecordingEngine.instances), 1)
            self.assertEqual(RecordingEngine.instances[0].kwargs.get("chunk_size"), 10)

            RecordingEngine.instances = []
            self.assertEqual(
                tcli.main(self._argv(scan) + ["--chunk-size", "25"]), 0
            )
            self.assertEqual(RecordingEngine.instances[0].kwargs.get("chunk_size"), 25)

    def test_chunk_size_out_of_range_is_rejected_without_building_engine(self):
        scan = write_scan(
            WORK / "scan_chunk_bad.jsonl",
            [make_row("T000001", "txt/demo.txt", 2, "チャンクサイズのテスト。")],
        )
        for bad_value in ("0", "-3", "51"):
            with mock.patch.object(tcli, "OpenAICompatEngine", RecordingEngine):
                RecordingEngine.instances = []
                code = tcli.main(self._argv(scan) + ["--chunk-size", bad_value])
                self.assertEqual(code, 2)
                self.assertEqual(
                    RecordingEngine.instances,
                    [],
                    "--chunk-size %s nao pode construir engine" % bad_value,
                )


class SafetyTests(TranslateCliCase):
    def test_dry_run_writes_nothing(self):
        work_before = snapshot(WORK)
        result = tcli.run_translate(
            scan_path=SCAN_FIXTURE,
            out_dir=WORK / "reports" / "translated" / "_dry",
            tm_path=None,
            engine=FakeEngine(),
            dry_run=True,
        )
        self.assertEqual(snapshot(WORK), work_before)
        self.assertFalse((WORK / "reports" / "translated" / "_dry").exists())
        self.assertIsNone(result.get("csv_path"))
        self.assertIsNone(result.get("md_path"))

    def test_invalid_jsonl_lines_are_ignored_and_counted(self):
        raw_dir = WORK / "raw"
        raw_dir.mkdir(parents=True)
        good = make_row("T000001", "txt/demo.txt", 2, "これは日本語のテキストです。")
        scan = raw_dir / "scan.jsonl"
        scan.write_text(
            json.dumps(good, ensure_ascii=False)
            + "\n{linha quebrada\n[]\n{\"item_id\": \"\", \"file\": \"a.txt\", \"text\": \"x\"}\n"
            + "{\"item_id\": \"T9\", \"text\": \"sem file\"}\n",
            encoding="utf-8",
        )
        result = tcli.run_translate(
            scan_path=scan,
            out_dir=WORK / "out_invalid",
            tm_path=None,
            engine=FakeEngine(),
            dry_run=True,
        )
        self.assertEqual(result["loaded"], 1)
        self.assertEqual(result["skipped"], 4)


class ProgressTests(TranslateCliCase):
    def _progress_lines(self, output):
        return [line for line in output.splitlines() if line.startswith("PROGRESS ")]

    def test_progress_starts_at_zero_and_reaches_total(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            result = tcli.run_translate(
                scan_path=SCAN_FIXTURE,
                out_dir=WORK / "out_progress",
                tm_path=None,
                engine=FakeEngine(),
                dry_run=True,
            )
        total = result["loaded"]
        progress_lines = self._progress_lines(buffer.getvalue())
        self.assertEqual(progress_lines[0], "PROGRESS 0/%d" % total)
        self.assertEqual(progress_lines[-1], "PROGRESS %d/%d" % (total, total))
        for line in progress_lines:
            self.assertRegex(line, r"^PROGRESS \d+/\d+$")

    def test_progress_zero_before_first_translation_and_incremental(self):
        scan = write_scan(
            WORK / "scan_progresso_lento.jsonl",
            [
                make_row("T000001", "txt/demo.txt", 2, "テキスト進行その一。"),
                make_row("T000002", "txt/demo.txt", 4, "テキスト進行その二。"),
                make_row("T000003", "txt/script.rpy", 3, "テキスト進行その三。"),
                make_row("T000004", "data/Actors.json", 0, "テキスト進行その四。"),
                make_row("T000005", "txt/demo.txt", 6, "テキスト進行その五。"),
                make_row("T000006", "txt/script.rpy", 5, "テキスト進行その六。"),
            ],
        )
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            tcli.run_translate(
                scan_path=scan,
                out_dir=WORK / "out_progresso_lento",
                tm_path=None,
                engine=SlowResilientEngine(chunk_size=2, delay=0.02),
                dry_run=True,
            )
        lines = buffer.getvalue().splitlines()
        progress_lines = self._progress_lines("\n".join(lines))
        # "PROGRESS 0/N" sai ANTES da primeira traducao do engine.
        self.assertEqual(progress_lines[0], "PROGRESS 0/6")
        first_chunk = next(
            index for index, line in enumerate(lines) if line.startswith("ENGINE-CHUNK")
        )
        first_progress = next(
            index for index, line in enumerate(lines) if line.startswith("PROGRESS ")
        )
        self.assertLess(first_progress, first_chunk)
        # Multiplos incrementos DURANTE a execucao: um por chunk resolvido.
        self.assertGreaterEqual(len(progress_lines), 4)
        self.assertEqual(progress_lines[1], "PROGRESS 2/6")
        self.assertEqual(progress_lines[2], "PROGRESS 4/6")
        self.assertEqual(progress_lines[-1], "PROGRESS 6/6")


class ExitCodeTests(TranslateCliCase):
    def test_missing_scan_file_returns_exit_code_2(self):
        code = tcli.main(
            [
                str(WORK / "nao_existe.jsonl"),
                "--out-dir",
                str(WORK / "out_x"),
            ]
        )
        self.assertEqual(code, 2)

    def test_apply_without_approval_flag_returns_exit_code_3(self):
        game = WORK / "mini_game"
        (game / "txt").mkdir(parents=True)
        (game / "txt" / "story.txt").write_bytes(
            "# Titulo\nこれはテストです。\n".encode("utf-8")
        )
        before = snapshot(game)
        code = tcli.main(
            [
                "apply",
                "--translated-dir",
                str(WORK / "nao_importa_out"),
                "--game-root",
                str(game),
            ]
        )
        self.assertEqual(code, 3)
        self.assertEqual(snapshot(game), before)


if __name__ == "__main__":
    unittest.main()
