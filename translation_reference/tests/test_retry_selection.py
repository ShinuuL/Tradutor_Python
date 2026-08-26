# -*- coding: utf-8 -*-
"""Testes offline do subcomando retry (unittest, somente stdlib).

Cobertura exigida pelo passo B2 do plano aprovado:
- selecao correta de item_ids por status no translation_report.csv;
- CSV ausente na pasta de saida => exit 2 com mensagem clara;
- fake engine prova que recebe SOMENTE os textos selecionados
  (--force-engine bypassa a memoria);
- resultado regrava CSV/MD normalmente ao final;
- sem --force-engine vale a cadeia normal (TM por-jogo resolve);
- status desconhecido em --statuses => exit 2 sem construir engine.

Cenario inicial: 3 itens com status llm / failed / needs_review gerados
por um engine fake com falha isolada no segundo item. Arquivos
temporarios ficam em tests/tmp_retry (limpo no tearDown).
"""
import shutil
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent / "scripts"
LIB_DIR = SCRIPTS_DIR / "lib"
for extra in (str(SCRIPTS_DIR), str(LIB_DIR)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

import translate_game_text as tcli  # noqa: E402
from tm_store import TMStore  # noqa: E402

FIXTURES_GAME = HERE / "fixtures" / "game"
TMP = HERE / "tmp_retry"

JP_GREETING = "{player_name}、こんにちは！"  # demo.txt linha 4 (aplica bem)
HELLO_WORLD = "こんにちは、世界。"  # script.rpy linha 3 (linha real, reaplicavel)
REVIEW_TEXT = "この行はファイルに存在しません。"  # demo.txt linha 4 divergente


def make_pair(source, target):
    return {
        "source": source,
        "target": target,
        "lang": "ja-en",
        "file": "txt/script.rpy",
        "item_id": "T000002",
    }


def make_row(item_id, rel_file, line, text):
    ext = "." + rel_file.rsplit(".", 1)[-1].lower()
    return {
        "item_id": item_id,
        "batch": "B0001",
        "root": str(FIXTURES_GAME),
        "file": rel_file,
        "line": line,
        "extension": ext,
        "encoding": "utf-8-sig",
        "reason": "kana",
        "category": "documentation",
        "priority": 35,
        "source_key": "",
        "occurrences": 1,
        "text": text,
    }


def read_csv_rows(path):
    import csv

    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


class FakeEngine:
    """Engine injetavel que registra os lotes recebidos."""

    def __init__(self, mapping=None, fail=False, fail_indices=None):
        self.calls = []
        self.mapping = dict(mapping or {})
        self.fail = fail
        self.fail_indices = set(fail_indices or ())
        from translation_engine import TranslationError

        self._error_class = TranslationError

    def translate_batch_resilient(self, texts):
        self.calls.append(list(texts))
        if self.fail:
            raise self._error_class("Servidor de traducao indisponivel.")
        outputs = []
        failed = []
        for index, text in enumerate(texts):
            if index in self.fail_indices:
                outputs.append("")
                failed.append(index)
            else:
                outputs.append(self.mapping.get(text, "EN:" + text))
        return outputs, failed


class RecordingEngine:
    """Substituto de OpenAICompatEngine que conta construcoes."""

    instances = []

    def __init__(self, **kwargs):
        self.kwargs = dict(kwargs)
        RecordingEngine.instances.append(self)

    def translate_batch_resilient(self, texts):
        return ["EN:" + t for t in texts], []


class SelectIdsFromReportTests(unittest.TestCase):
    """A funcao pura de selecao sobre um relatorio real do CLI."""

    @classmethod
    def setUpClass(cls):
        shutil.rmtree(TMP, ignore_errors=True)
        TMP.mkdir(parents=True)
        scan = TMP / "scan.jsonl"
        with open(scan, "w", encoding="utf-8", newline="\n") as fh:
            import json

            rows = [
                make_row("T000001", "txt/demo.txt", 4, JP_GREETING),
                make_row("T000002", "txt/script.rpy", 3, HELLO_WORLD),
                make_row("T000003", "txt/demo.txt", 4, REVIEW_TEXT),
            ]
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        cls.csv_path = tcli.run_translate(
            scan_path=scan,
            out_dir=TMP / "out_sel",
            tm_path=None,
            engine=FakeEngine(fail_indices={1}),
            dry_run=False,
        )["csv_path"]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TMP, ignore_errors=True)

    def test_initial_report_has_the_expected_mix(self):
        records = {
            r["item_id"]: r["status"] for r in read_csv_rows(self.csv_path)
        }
        self.assertEqual(
            records,
            {
                "T000001": "llm",
                "T000002": "failed",
                "T000003": "needs_review",
            },
        )

    def test_selects_only_requested_statuses(self):
        self.assertEqual(
            tcli.select_ids_from_report(self.csv_path, {"failed"}), {"T000002"}
        )
        self.assertEqual(
            tcli.select_ids_from_report(self.csv_path, {"failed", "needs_review"}),
            {"T000002", "T000003"},
        )
        self.assertEqual(
            tcli.select_ids_from_report(self.csv_path, {"FAILED"}),
            {"T000002"},
            "comparacao ignora caixa",
        )
        self.assertEqual(
            tcli.select_ids_from_report(self.csv_path, {"llm"}), {"T000001"}
        )

    def test_no_match_returns_empty_set(self):
        self.assertEqual(
            tcli.select_ids_from_report(self.csv_path, {"status_inexistente"}),
            set(),
        )

    def test_csv_sem_colunas_retorna_conjunto_vazio(self):
        other = TMP / "malformado.csv"
        other.write_text("coluna_a,coluna_b\n1,2\n", encoding="utf-8-sig")
        self.assertEqual(tcli.select_ids_from_report(other, {"failed"}), set())


class RetryCliTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(TMP, ignore_errors=True)
        TMP.mkdir(parents=True)
        self.scan = TMP / "scan.jsonl"
        with open(self.scan, "w", encoding="utf-8", newline="\n") as fh:
            import json

            rows = [
                make_row("T000001", "txt/demo.txt", 4, JP_GREETING),
                make_row("T000002", "txt/script.rpy", 3, HELLO_WORLD),
                make_row("T000003", "txt/demo.txt", 4, REVIEW_TEXT),
            ]
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        self.out_dir = TMP / "reports" / "translated" / "jogoteste"
        self.initial_engine = FakeEngine(fail_indices={1})
        self.initial = tcli.run_translate(
            scan_path=self.scan,
            out_dir=self.out_dir,
            tm_path=None,
            engine=self.initial_engine,
            dry_run=False,
        )

    def tearDown(self):
        shutil.rmtree(TMP, ignore_errors=True)

    def _retry_argv(self, extra=None):
        argv = [
            "retry",
            "--scan",
            str(self.scan),
            "--out-dir",
            str(self.out_dir),
        ]
        return argv + list(extra or [])

    def test_missing_csv_returns_exit_2(self):
        empty_out = TMP / "reports" / "translated" / "vazio"
        empty_out.mkdir(parents=True)
        code = tcli.main(
            ["retry", "--scan", str(self.scan), "--out-dir", str(empty_out)]
        )
        self.assertEqual(code, 2)

    def test_force_engine_receives_only_selected_texts_and_rewrites_reports(self):
        retry_engine = FakeEngine()
        with mock.patch.object(
            tcli, "OpenAICompatEngine", lambda **kwargs: retry_engine
        ):
            code = tcli.main(
                self._retry_argv(["--statuses", "failed", "--force-engine"])
            )

        self.assertEqual(code, 0)
        # Prova central: o motor recebeu SOMENTE o texto do item failed.
        self.assertEqual(retry_engine.calls, [[HELLO_WORLD]])

        # CSV mergesado: todas as linhas preservadas, status atualizado.
        records = {
            r["item_id"]: r for r in read_csv_rows(self.out_dir / tcli.REPORT_CSV)
        }
        self.assertEqual(len(records), 3, "CSV mergesado deve ter todos os itens")
        self.assertEqual(records["T000001"]["status"], "llm", "item llm intocado")
        self.assertEqual(records["T000002"]["status"], "llm", "failed re-traduzido")
        self.assertEqual(records["T000002"]["translated"], "EN:" + HELLO_WORLD)
        self.assertEqual(
            records["T000003"]["status"], "needs_review",
            "needs_review permanece (texto nao existe no arquivo)"
        )

        # MD regravado com contagens completas do merge.
        md_text = (self.out_dir / tcli.REPORT_MD).read_text(encoding="utf-8")
        self.assertIn("- llm: 2", md_text, "2 itens llm apos merge")
        self.assertIn("- needs_review: 1", md_text, "1 needs_review preservado")

    def test_default_statuses_cover_failed_and_needs_review(self):
        retry_engine = FakeEngine()
        with mock.patch.object(
            tcli, "OpenAICompatEngine", lambda **kwargs: retry_engine
        ):
            code = tcli.main(self._retry_argv(["--force-engine"]))

        self.assertEqual(code, 0)
        received = [text for batch in retry_engine.calls for text in batch]
        self.assertEqual(sorted(received), sorted([HELLO_WORLD, REVIEW_TEXT]))
        self.assertNotIn(JP_GREETING, received, "item llm nao pode ir ao motor")

        # CSV mergesado: todos os 3 itens presentes, failed re-traduzido
        records = {
            r["item_id"]: r for r in read_csv_rows(self.out_dir / tcli.REPORT_CSV)
        }
        self.assertEqual(len(records), 3, "CSV mergesado deve ter todos os itens")
        self.assertEqual(records["T000001"]["status"], "llm", "item llm intocado")
        self.assertEqual(records["T000002"]["status"], "llm", "failed re-traduzido")
        # REVIEW_TEXT nao existe no arquivo => applier marca needs_review
        self.assertEqual(
            records["T000003"]["status"], "needs_review",
            "needs_review permanece (texto nao existe no arquivo)"
        )

    def test_without_force_engine_uses_tm_chain(self):
        tm_path = TMP / "reports" / "tm" / "jogoteste.jsonl"
        TMStore(tm_path).add_many([make_pair(HELLO_WORLD, "RESCUED BY TM")])
        retry_engine = FakeEngine()
        with mock.patch.object(
            tcli, "OpenAICompatEngine", lambda **kwargs: retry_engine
        ):
            code = tcli.main(
                self._retry_argv(["--statuses", "failed", "--tm", str(tm_path)])
            )

        self.assertEqual(code, 0)
        self.assertEqual(
            retry_engine.calls, [], "cadeia normal resolveu sem chamar o motor"
        )
        # CSV mergesado: todos os 3 itens presentes, failed resgatado por TM
        records = {
            r["item_id"]: r for r in read_csv_rows(self.out_dir / tcli.REPORT_CSV)
        }
        self.assertEqual(len(records), 3, "CSV mergesado deve ter todos os itens")
        self.assertEqual(records["T000002"]["status"], "tm_hit")
        self.assertEqual(records["T000002"]["translated"], "RESCUED BY TM")

    def test_unknown_status_returns_exit_2_without_building_engine(self):
        with mock.patch.object(tcli, "OpenAICompatEngine", RecordingEngine):
            RecordingEngine.instances = []
            code = tcli.main(self._retry_argv(["--statuses", "faild"]))
            self.assertEqual(code, 2)
            self.assertEqual(
                RecordingEngine.instances,
                [],
                "status invalido nao pode construir engine",
            )


class RetryMergeTests(unittest.TestCase):
    """Testes especificos do merge apos retry: o CSV final deve preservar
    todas as linhas originais e atualizar apenas as re-traduzidas.
    """

    def setUp(self):
        shutil.rmtree(TMP, ignore_errors=True)
        TMP.mkdir(parents=True)
        self.scan = TMP / "scan_merge.jsonl"
        with open(self.scan, "w", encoding="utf-8", newline="\n") as fh:
            import json

            rows = [
                make_row("T000001", "txt/demo.txt", 2, "Primeira linha."),
                make_row("T000002", "txt/demo.txt", 3, "Segunda linha."),
                make_row("T000003", "txt/demo.txt", 4, JP_GREETING),
                make_row("T000004", "txt/script.rpy", 3, HELLO_WORLD),
                make_row("T000005", "txt/script.rpy", 5, "Quinta linha."),
            ]
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        self.out_dir = TMP / "merge_out"
        self.initial_engine = FakeEngine(fail_indices={1})
        self.initial = tcli.run_translate(
            scan_path=self.scan,
            out_dir=self.out_dir,
            tm_path=None,
            engine=self.initial_engine,
            dry_run=False,
        )

    def tearDown(self):
        shutil.rmtree(TMP, ignore_errors=True)

    def _retry_argv(self, extra=None):
        argv = [
            "retry",
            "--scan",
            str(self.scan),
            "--out-dir",
            str(self.out_dir),
        ]
        return argv + list(extra or [])

    def test_merge_preserves_all_rows_after_partial_retry(self):
        """Fixture CSV com 5 linhas (2 failed, 1 needs_review, 2 llm OK)
        retry com --statuses failed regrava com 2 linhas
        merge resulta em 5 linhas (2 agora com status atualizado, 3 intocadas)
        """
        retry_engine = FakeEngine()
        with mock.patch.object(
            tcli, "OpenAICompatEngine", lambda **kwargs: retry_engine
        ):
            code = tcli.main(
                self._retry_argv(["--statuses", "failed", "--force-engine"])
            )

        self.assertEqual(code, 0)
        # O retry so envia os itens failed ao motor. Com fail_indices={1},
        # o item na posicao 1 ("Segunda linha.") falhou. O retry tem somente
        # esse 1 item; FakeEngine agora sem fail_indices traduz com sucesso.
        self.assertEqual(retry_engine.calls, [["Segunda linha."]])

        records = {
            r["item_id"]: r for r in read_csv_rows(self.out_dir / tcli.REPORT_CSV)
        }
        self.assertEqual(len(records), 5, "CSV mergesado deve ter todas as 5 linhas")
        # Itens llm originais intocados (JP_GREETING e HELLO_WORLD)
        self.assertEqual(records["T000003"]["status"], "llm")
        self.assertEqual(records["T000004"]["status"], "llm")
        # Item failed re-traduzido mas applier marca needs_review
        # (texto original nao existe na linha do arquivo)
        self.assertEqual(records["T000002"]["status"], "needs_review")
        # Itens needs_review intocados
        self.assertEqual(records["T000001"]["status"], "needs_review")
        self.assertEqual(records["T000005"]["status"], "needs_review")

    def test_empty_csv_plus_retry_has_only_subset(self):
        """Fixture CSV vazio + retry com scan: resultado e so o subconjunto
        (sem merge necessario, pois nao ha original).
        """
        empty_dir = TMP / "empty_out"
        empty_dir.mkdir(parents=True)
        scan_path = TMP / "scan_single.jsonl"
        with open(scan_path, "w", encoding="utf-8", newline="\n") as fh:
            import json

            row = make_row("T000099", "txt/demo.txt", 1, HELLO_WORLD)
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

        result = tcli.run_translate(
            scan_path=scan_path,
            out_dir=empty_dir,
            engine=FakeEngine(),
            dry_run=False,
        )
        records = read_csv_rows(result["csv_path"])
        self.assertEqual(len(records), 1, "sem CSV original, so o subconjunto")
        self.assertEqual(records[0]["item_id"], "T000099")

    def test_md_status_counts_reflect_full_merge(self):
        """Verificar que contagem de status no MD reflete o merge completo."""
        retry_engine = FakeEngine()
        with mock.patch.object(
            tcli, "OpenAICompatEngine", lambda **kwargs: retry_engine
        ):
            tcli.main(
                self._retry_argv(["--statuses", "failed", "--force-engine"])
            )

        md_text = (self.out_dir / tcli.REPORT_MD).read_text(encoding="utf-8")
        # 5 itens: 2 llm (JP_GREETING + HELLO_WORLD), 3 needs_review
        # (T000001 + T000002 re-traduzido mas applier marca needs_review + T000005)
        self.assertIn("- llm: 2", md_text, "2 itens llm no merge")
        self.assertIn("- needs_review: 3", md_text, "3 needs_review (inclui o antigo failed)")
        self.assertIn("- failed: 0", md_text, "0 failed apos re-traduzir")
        self.assertIn("- tm_hit: 0", md_text)


if __name__ == "__main__":
    unittest.main()
