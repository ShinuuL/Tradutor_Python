# -*- coding: utf-8 -*-
"""Testes offline dos subcomandos no-tokens e low-cost (unittest, stdlib).

Cobertura:
- classify_lowcost: classificacao correta (repetidos, novos, CJK denso, TM hit)
- _cjk_dense_ratio: razao CJK correta
- no-tokens: scan com 5 textos (3 com hit, 2 novos) -> CSV + pendencias.md
- no-tokens: todos traduzidos -> exit 0
- low-cost: gera CSV/MD corretos
- low-cost: textos com hit no TM -> tm_hit direto

Arquivos temporarios ficam em tests/tmp_no_tokens (limpo no tearDown).
"""
import csv
import shutil
import sys
import unittest
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIB_DIR = HERE.parent / "scripts" / "lib"
SCRIPTS_DIR = HERE.parent / "scripts"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import tm_db  # noqa: E402
from tm_store import TMStore  # noqa: E402
from global_tm import ChainedTM  # noqa: E402
from translate_game_text import (  # noqa: E402
    classify_lowcost,
    _cjk_dense_ratio,
    cmd_no_tokens,
    cmd_low_cost,
    load_rows,
    CliError,
)

TMP = HERE / "tmp_no_tokens"


def _write_jsonl(path, records):
    """Escreve records como JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for rec in records:
            fh.write(
                __import__("json").dumps(rec, ensure_ascii=False) + "\n"
            )


def _make_scan_rows():
    """5 rows de scan: 3 com texto traduzivel no TM, 2 novos."""
    return [
        {
            "item_id": "S001",
            "file": "script.rpy",
            "line": 10,
            "text": "Bonjour le monde",
            "source_key": "line_10",
            "root": "/fake/game",
        },
        {
            "item_id": "S002",
            "file": "script.rpy",
            "line": 20,
            "text": "Merci beaucoup",
            "source_key": "line_20",
            "root": "/fake/game",
        },
        {
            "item_id": "S003",
            "file": "dialogue.txt",
            "line": 5,
            "text": "Au revoir",
            "source_key": "line_5",
            "root": "/fake/game",
        },
        {
            "item_id": "S004",
            "file": "dialogue.txt",
            "line": 15,
            "text": "Texto novo sem traducao",
            "source_key": "line_15",
            "root": "/fake/game",
        },
        {
            "item_id": "S005",
            "file": "menu.txt",
            "line": 1,
            "text": "Outro texto pendente",
            "source_key": "line_1",
            "root": "/fake/game",
        },
    ]


class BaseTestCase(unittest.TestCase):
    """Base com setup/teardown de diretorio temporario."""

    def setUp(self):
        shutil.rmtree(TMP, ignore_errors=True)
        TMP.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(TMP, ignore_errors=True)

    def tmp_path(self, *parts):
        p = TMP.joinpath(*parts)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p


# ======================================================================
# Testes de _cjk_dense_ratio
# ======================================================================


class CJKDenseRatioTests(unittest.TestCase):
    def test_all_latin(self):
        self.assertAlmostEqual(_cjk_dense_ratio("Hello World"), 0.0)

    def test_all_cjk(self):
        self.assertAlmostEqual(_cjk_dense_ratio("日本語テスト"), 1.0)

    def test_mixed_half(self):
        ratio = _cjk_dense_ratio("日本ABC")
        # 2 CJK (日本) + 3 latin (ABC) = 2/5 = 0.4
        self.assertAlmostEqual(ratio, 0.4)

    def test_empty_string(self):
        self.assertAlmostEqual(_cjk_dense_ratio(""), 0.0)

    def test_none_input(self):
        self.assertAlmostEqual(_cjk_dense_ratio(None), 0.0)

    def test_only_spaces(self):
        self.assertAlmostEqual(_cjk_dense_ratio("   "), 0.0)


# ======================================================================
# Testes de classify_lowcost
# ======================================================================


class ClassifyLowcostTests(BaseTestCase):
    def _make_tm_with_hits(self, tm_path):
        """Cria TM com 3 traducoes para os textos do scan."""
        tm = TMStore(str(tm_path))
        tm.add_many([
            {"source": "Bonjour le monde", "target": "Hello world",
             "file": "script.rpy", "item_id": "S001"},
            {"source": "Merci beaucoup", "target": "Thank you very much",
             "file": "script.rpy", "item_id": "S002"},
            {"source": "Au revoir", "target": "Goodbye",
             "file": "dialogue.txt", "item_id": "S003"},
        ])
        return tm

    def test_classify_with_tm_hits_and_new_texts(self):
        tm_path = self.tmp_path("tm", "test.jsonl")
        tm = self._make_tm_with_hits(tm_path)
        rows = _make_scan_rows()
        to_translate, skip, tm_hits = classify_lowcost(rows, tm, threshold=3)

        # 3 com hit no TM
        self.assertEqual(len(tm_hits), 3)
        hit_keys = {r["key"] for r in tm_hits}
        self.assertIn("Bonjour le monde", hit_keys)
        self.assertIn("Merci beaucoup", hit_keys)
        self.assertIn("Au revoir", hit_keys)

        # 2 novos (sem hit, nao repetidos o suficiente)
        self.assertEqual(len(to_translate), 2)
        new_keys = {r["key"] for r in to_translate}
        self.assertIn("Texto novo sem traducao", new_keys)
        self.assertIn("Outro texto pendente", new_keys)

        # Nenhum skip
        self.assertEqual(len(skip), 0)

    def test_classify_repeated_text_high_impact(self):
        """Texto repetido >= threshold -> to_translate com motivo repetido."""
        tm = TMStore(str(self.tmp_path("tm", "empty.jsonl")))
        rows = [
            {"item_id": "R1", "file": "a.txt", "line": 1,
             "text": "Texto repetido", "root": "/x"},
            {"item_id": "R2", "file": "a.txt", "line": 5,
             "text": "Texto repetido", "root": "/x"},
            {"item_id": "R3", "file": "b.txt", "line": 1,
             "text": "Texto repetido", "root": "/x"},
            {"item_id": "R4", "file": "c.txt", "line": 1,
             "text": "Unico", "root": "/x"},
        ]
        to_translate, skip, tm_hits = classify_lowcost(rows, tm, threshold=3)

        # "Texto repetido" aparece 3x -> repetido
        repeated = [r for r in to_translate if r["key"] == "Texto repetido"]
        self.assertEqual(len(repeated), 1)
        self.assertTrue(
            any("repetido" in reason for reason in repeated[0]["reasons"])
        )

        # "Unico" aparece 1x -> texto_novo
        unico = [r for r in to_translate if r["key"] == "Unico"]
        self.assertEqual(len(unico), 1)
        self.assertIn("texto_novo", unico[0]["reasons"])

    def test_classify_cjk_dense_text(self):
        """Texto com CJK denso (> 0.5) -> to_translate com motivo cjk_denso."""
        tm = TMStore(str(self.tmp_path("tm", "empty.jsonl")))
        rows = [
            {"item_id": "C1", "file": "a.txt", "line": 1,
             "text": "テスト文章です", "root": "/x"},
        ]
        to_translate, skip, tm_hits = classify_lowcost(rows, tm, threshold=3)
        self.assertEqual(len(to_translate), 1)
        self.assertTrue(
            any("cjk" in reason for reason in to_translate[0]["reasons"])
        )

    def test_classify_tm_none(self):
        """Com TM=None, todos os textos vao para to_translate."""
        rows = _make_scan_rows()
        to_translate, skip, tm_hits = classify_lowcost(rows, None, threshold=3)
        self.assertEqual(len(tm_hits), 0)
        self.assertEqual(len(to_translate), 5)
        self.assertEqual(len(skip), 0)

    def test_classify_dedup_by_key(self):
        """Textos duplicados no scan sao processados uma vez so."""
        tm = TMStore(str(self.tmp_path("tm", "empty.jsonl")))
        rows = [
            {"item_id": "D1", "file": "a.txt", "line": 1,
             "text": "Duplicado", "root": "/x"},
            {"item_id": "D2", "file": "a.txt", "line": 5,
             "text": "Duplicado", "root": "/x"},
        ]
        to_translate, skip, tm_hits = classify_lowcost(rows, tm, threshold=3)
        # So uma entrada em to_translate (dedupe)
        self.assertEqual(len(to_translate), 1)


# ======================================================================
# Testes de no-tokens
# ======================================================================


class NoTokensTests(BaseTestCase):
    def _make_scan(self):
        scan = self.tmp_path("scan.jsonl")
        _write_jsonl(scan, _make_scan_rows())
        return scan

    def _make_tm_with_hits(self, tm_path):
        tm = TMStore(str(tm_path))
        tm.add_many([
            {"source": "Bonjour le monde", "target": "Hello world",
             "file": "script.rpy", "item_id": "S001"},
            {"source": "Merci beaucoup", "target": "Thank you very much",
             "file": "script.rpy", "item_id": "S002"},
            {"source": "Au revoir", "target": "Goodbye",
             "file": "dialogue.txt", "item_id": "S003"},
        ])
        return tm

    def test_no_tokens_generates_csv_and_md(self):
        scan = self._make_scan()
        tm_path = self.tmp_path("tm", "game.jsonl")
        self._make_tm_with_hits(tm_path)
        out = self.tmp_path("out")

        exit_code = cmd_no_tokens(
            scan_path=str(scan),
            out_dir=str(out),
            engine_name="test_game",
            tm_path=str(tm_path),
        )

        # Exit code 1 (ha pendencias)
        self.assertEqual(exit_code, 1)

        # CSV existe e tem 5 linhas
        csv_path = out / "no_tokens_report.csv"
        self.assertTrue(csv_path.exists())
        with open(csv_path, "r", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
        self.assertEqual(len(rows), 5)

        # 3 tm_hit + 2 pending
        statuses = Counter(r["status"] for r in rows)
        self.assertEqual(statuses["tm_hit"], 3)
        self.assertEqual(statuses["pending"], 2)

        # pendencias.md existe e menciona os 2 pendentes
        md_path = out / "pendencias.md"
        self.assertTrue(md_path.exists())
        md_content = md_path.read_text(encoding="utf-8")
        self.assertIn("Texto novo sem traducao", md_content)
        self.assertIn("Outro texto pendente", md_content)
        self.assertIn("Pendentes de traducao: 2", md_content)

    def test_no_tokens_all_translated_exit_0(self):
        """Todos traduzidos -> exit code 0 e pendencias.md sem pendentes."""
        scan = self._make_scan()
        tm_path = self.tmp_path("tm", "game.jsonl")
        # TM com TODOS os textos
        tm = TMStore(str(tm_path))
        tm.add_many([
            {"source": "Bonjour le monde", "target": "Hello world",
             "file": "script.rpy", "item_id": "S001"},
            {"source": "Merci beaucoup", "target": "Thank you",
             "file": "script.rpy", "item_id": "S002"},
            {"source": "Au revoir", "target": "Goodbye",
             "file": "dialogue.txt", "item_id": "S003"},
            {"source": "Texto novo sem traducao", "target": "New text without translation",
             "file": "dialogue.txt", "item_id": "S004"},
            {"source": "Outro texto pendente", "target": "Another pending text",
             "file": "menu.txt", "item_id": "S005"},
        ])
        out = self.tmp_path("out")

        exit_code = cmd_no_tokens(
            scan_path=str(scan),
            out_dir=str(out),
            engine_name="test_game",
            tm_path=str(tm_path),
        )

        self.assertEqual(exit_code, 0)

        md_content = (out / "pendencias.md").read_text(encoding="utf-8")
        self.assertIn("Pendentes de traducao: 0", md_content)
        self.assertIn("Nenhum texto pendente", md_content)

    def test_no_tokens_invalid_scan_exits_2(self):
        out = self.tmp_path("out")
        with self.assertRaises(CliError) as ctx:
            cmd_no_tokens(
                scan_path=str(self.tmp_path("nonexistent.jsonl")),
                out_dir=str(out),
                engine_name="test",
            )
        self.assertEqual(ctx.exception.exit_code, 2)

    def test_no_tokens_with_chained_tm(self):
        """Cadeia global + por-jogo funciona no no-tokens."""
        scan = self._make_scan()
        global_path = self.tmp_path("tm", "global.jsonl")
        game_path = self.tmp_path("tm", "game.jsonl")

        global_tm = TMStore(str(global_path))
        global_tm.add_many([
            {"source": "Bonjour le monde", "target": "Hello world global",
             "file": "script.rpy", "item_id": "G001"},
        ])
        game_tm = TMStore(str(game_path))
        game_tm.add_many([
            {"source": "Merci beaucoup", "target": "Thank you game",
             "file": "script.rpy", "item_id": "G002"},
        ])

        out = self.tmp_path("out")
        exit_code = cmd_no_tokens(
            scan_path=str(scan),
            out_dir=str(out),
            engine_name="chained_test",
            tm_path=str(game_path),
            tm_global_path=str(global_path),
        )

        self.assertEqual(exit_code, 1)  # ainda ha pendencias

        csv_path = out / "no_tokens_report.csv"
        with open(csv_path, "r", encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        statuses = Counter(r["status"] for r in rows)
        # 2 tm_hit (1 global + 1 game) + 3 pending
        self.assertEqual(statuses["tm_hit"], 2)
        self.assertEqual(statuses["pending"], 3)


# ======================================================================
# Testes de low-cost
# ======================================================================


class LowCostTests(BaseTestCase):
    def _make_scan(self, extra_rows=None):
        rows = _make_scan_rows()
        if extra_rows:
            rows.extend(extra_rows)
        scan = self.tmp_path("scan.jsonl")
        _write_jsonl(scan, rows)
        return scan

    def _make_tm(self, entries):
        tm_path = self.tmp_path("tm", "game.jsonl")
        tm = TMStore(str(tm_path))
        tm.add_many(entries)
        return str(tm_path)

    def test_low_cost_generates_csv_and_md_no_engine(self):
        """Sem engine, so tm_hits e skip; CSV/MD gerados corretamente."""
        scan = self._make_scan()
        tm_path = self._make_tm([
            {"source": "Bonjour le monde", "target": "Hello world",
             "file": "script.rpy", "item_id": "S001"},
            {"source": "Merci beaucoup", "target": "Thank you",
             "file": "script.rpy", "item_id": "S002"},
            {"source": "Au revoir", "target": "Goodbye",
             "file": "dialogue.txt", "item_id": "S003"},
        ])
        out = self.tmp_path("out")

        exit_code = cmd_low_cost(
            scan_path=str(scan),
            out_dir=str(out),
            threshold=3,
            engine=None,
            tm_path=tm_path,
        )

        self.assertEqual(exit_code, 0)

        csv_path = out / "low_cost_report.csv"
        self.assertTrue(csv_path.exists())
        with open(csv_path, "r", encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(len(rows), 5)

        statuses = Counter(r["status"] for r in rows)
        self.assertEqual(statuses["tm_hit"], 3)
        # 2 novos sem engine -> failed
        self.assertEqual(statuses["failed"], 2)

        md_path = out / "low_cost_report.md"
        self.assertTrue(md_path.exists())
        md_content = md_path.read_text(encoding="utf-8")
        self.assertIn("tm_hit: 3", md_content)
        self.assertIn("failed: 2", md_content)

    def test_low_cost_classifies_repeated_text(self):
        """Texto repetido >= threshold e classificado corretamente."""
        extra = [
            {"item_id": "R1", "file": "a.txt", "line": 1,
             "text": "Texto repetido", "root": "/fake/game"},
            {"item_id": "R2", "file": "a.txt", "line": 5,
             "text": "Texto repetido", "root": "/fake/game"},
            {"item_id": "R3", "file": "b.txt", "line": 1,
             "text": "Texto repetido", "root": "/fake/game"},
        ]
        scan = self._make_scan(extra_rows=extra)
        out = self.tmp_path("out")

        exit_code = cmd_low_cost(
            scan_path=str(scan),
            out_dir=str(out),
            threshold=3,
            engine=None,
        )

        csv_path = out / "low_cost_report.csv"
        with open(csv_path, "r", encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        # Total: 5 originais + 3 repetidos (deduped para 1 unico) + 2 novos = 7
        # Nota: os 3 extras viram 1 unico por dedupe, entao 5 + 1 = 6
        self.assertEqual(len(rows), 6)

        # O texto repetido deve estar como failed (sem engine) com motivo repetido
        repeated = [r for r in rows if r["source"] == "Texto repetido"]
        self.assertEqual(len(repeated), 1)
        self.assertIn("repetido", repeated[0]["notes"])

    def test_low_cost_with_chained_tm(self):
        """Cadeia global + por-jogo funciona no low-cost."""
        scan = self._make_scan()
        global_path = self.tmp_path("tm", "global.jsonl")
        game_path = self.tmp_path("tm", "game.jsonl")

        global_tm = TMStore(str(global_path))
        global_tm.add_many([
            {"source": "Bonjour le monde", "target": "Hello global",
             "file": "script.rpy", "item_id": "G001"},
        ])
        game_tm = TMStore(str(game_path))
        game_tm.add_many([
            {"source": "Merci beaucoup", "target": "Thank you game",
             "file": "script.rpy", "item_id": "G002"},
        ])

        out = self.tmp_path("out")
        exit_code = cmd_low_cost(
            scan_path=str(scan),
            out_dir=str(out),
            threshold=3,
            engine=None,
            tm_path=str(game_path),
            tm_global_path=str(global_path),
        )

        csv_path = out / "low_cost_report.csv"
        with open(csv_path, "r", encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        statuses = Counter(r["status"] for r in rows)
        # 2 tm_hit (1 global + 1 game) + 3 failed (novos sem engine)
        self.assertEqual(statuses["tm_hit"], 2)
        self.assertEqual(statuses["failed"], 3)

    def test_low_cost_invalid_scan_exits_2(self):
        out = self.tmp_path("out")
        with self.assertRaises(CliError) as ctx:
            cmd_low_cost(
                scan_path=str(self.tmp_path("nonexistent.jsonl")),
                out_dir=str(out),
                engine=None,
            )
        self.assertEqual(ctx.exception.exit_code, 2)


if __name__ == "__main__":
    unittest.main()
