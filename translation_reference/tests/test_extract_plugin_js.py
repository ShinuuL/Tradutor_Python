# -*- coding: utf-8 -*-
"""Testes do extrator: filtro jp-dense para plugins.js (passo A2).

Primeiro teste dedicado de extract_non_english_text.py. Cobertura
exigida pelo plano A2:

- is_jp_dense puro: kana, colchetes japoneses e razao CJK >= 0.30
  (limite exatamente 0.30 passa; abaixo falha);
- modo jp-dense (default) ignora o snippet tecnico "PA_INIT 6 12 横"
  e mantem o snippet com kana;
- modo all restaura o comportamento atual (tudo emitido);
- contador plugin_js_tecnico_ignorado correto no summary.

NOTA: .js foi removido de TEXT_EXTENSIONS (saude do jogo).
Os testes CLI usam --include-ext js para opt-in explicito.

Somente stdlib. Nenhum fixture e alterado (copias em tmp local).
"""
import hashlib
import io
import json
import shutil
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import extract_non_english_text as ext  # noqa: E402

FIXTURES_ROOT = HERE / "fixtures"
FIXTURE_PLUGIN_JS = FIXTURES_ROOT / "game" / "js" / "plugins" / "fakeplugin.js"
WORK = HERE / "tmp_extract_plugin_js"

TECHNICAL_TEXT = "PA_INIT 6 12 横"
KANA_TEXT = "こいつは話さない"
BRACKET_TEXT = "「GOLD 討」"


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


def scan_plugin_rows(game_root):
    """Varre a arvore espelhada como o main() faria (sem gravar nada)."""
    rows = []
    for path in ext.iter_files(game_root):
        if path.suffix.lower() != ".js":
            continue
        rows.extend(ext.scan_file(path, game_root, 180))
    return rows


def texts_of(rows):
    return sorted(row["text"] for row in rows)


class PluginJsFixtureCase(unittest.TestCase):
    """Base com arvore espelhada e fixtures intocaveis."""

    def setUp(self):
        shutil.rmtree(WORK, ignore_errors=True)
        WORK.mkdir(parents=True)
        self.fixtures_snapshot = snapshot(FIXTURES_ROOT)
        # Espelho com o mesmo layout relativo "js/plugins/fakeplugin.js"
        # para classify_path devolver rpgmaker_plugin_js.
        self.game = WORK / "mini_game"
        dest = self.game / "js" / "plugins" / "fakeplugin.js"
        dest.parent.mkdir(parents=True)
        shutil.copyfile(FIXTURE_PLUGIN_JS, dest)

    def tearDown(self):
        shutil.rmtree(WORK, ignore_errors=True)
        self.assertEqual(snapshot(FIXTURES_ROOT), self.fixtures_snapshot)


class IsJpDenseTests(unittest.TestCase):
    def test_technical_pa_init_is_not_jp_dense(self):
        # 1 CJK entre ~11 chars nao-espaco (~9%), sem kana e sem 「」.
        self.assertFalse(ext.is_jp_dense(TECHNICAL_TEXT))

    def test_kana_snippet_is_jp_dense(self):
        self.assertTrue(ext.is_jp_dense(KANA_TEXT))

    def test_corner_brackets_alone_make_snippet_dense(self):
        # Sem kana e razao CJK baixa (1/7): denso apenas pelos colchetes.
        self.assertTrue(ext.is_jp_dense(BRACKET_TEXT))
        self.assertFalse(any("\u3040" <= ch <= "\u30ff" for ch in BRACKET_TEXT))

    def test_cjk_ratio_exactly_thirty_percent_passes(self):
        # 3 CJK entre 10 caracteres nao-espaco => 0.30 (limite inclusivo).
        self.assertTrue(ext.is_jp_dense("漢字漢 abcdefg"))

    def test_cjk_ratio_below_thirty_percent_fails(self):
        # 3 CJK entre 11 caracteres nao-espaco => ~0.27.
        self.assertFalse(ext.is_jp_dense("漢字漢 abcdefgh"))

    def test_blank_snippet_is_not_jp_dense(self):
        self.assertFalse(ext.is_jp_dense(""))
        self.assertFalse(ext.is_jp_dense("   \t "))


class PluginJsModeScanTests(PluginJsFixtureCase):
    def test_baseline_scan_emits_three_plugin_rows(self):
        # Comportamento atual (modo all): os 3 snippets sao emitidos.
        rows = scan_plugin_rows(self.game)
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertEqual(row["category"], "rpgmaker_plugin_js")
            self.assertEqual(int(row["priority"]), 25)
        self.assertIn(TECHNICAL_TEXT, texts_of(rows))
        self.assertIn(KANA_TEXT, texts_of(rows))
        self.assertIn(BRACKET_TEXT, texts_of(rows))

    def test_jp_dense_filters_technical_and_keeps_kana(self):
        rows = scan_plugin_rows(self.game)
        kept, ignored = ext.apply_plugin_js_mode(rows, "jp-dense")
        self.assertEqual(texts_of(kept), [BRACKET_TEXT, KANA_TEXT])
        self.assertEqual(ignored, 1)

    def test_all_mode_keeps_everything(self):
        rows = scan_plugin_rows(self.game)
        kept, ignored = ext.apply_plugin_js_mode(rows, "all")
        self.assertEqual(len(kept), 3)
        self.assertEqual(ignored, 0)


class ExtractorCliTests(PluginJsFixtureCase):
    def run_extractor(self, extra_args=()):
        out_base = WORK / "reports" / "_smoke_a2"
        # .js removido de TEXT_EXTENSIONS; opt-in via --include-ext js
        argv = [str(self.game), "--out", str(out_base), "--include-ext", ".js"] + list(extra_args)
        buffer = io.StringIO()
        with mock.patch.object(sys, "argv", ["extract_non_english_text.py"] + argv):
            with redirect_stdout(buffer):
                ext.main()
        return {
            "stdout": buffer.getvalue(),
            "jsonl": out_base.with_suffix(".jsonl"),
            "summary": out_base.with_suffix(".summary.md"),
        }

    def read_jsonl_texts_and_counter(self, result):
        rows = [
            json.loads(line)
            for line in result["jsonl"].read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        plugin_texts = texts_of(
            [row for row in rows if row["category"] == "rpgmaker_plugin_js"]
        )
        summary = result["summary"].read_text(encoding="utf-8")
        counter = next(
            (
                line.strip("- ").strip()
                for line in summary.splitlines()
                if "plugin_js_tecnico_ignorado:" in line
            ),
            None,
        )
        return plugin_texts, counter

    def test_default_mode_is_jp_dense_and_counts_ignored(self):
        result = self.run_extractor()
        plugin_texts, counter = self.read_jsonl_texts_and_counter(result)
        self.assertEqual(plugin_texts, [BRACKET_TEXT, KANA_TEXT])
        self.assertNotIn(TECHNICAL_TEXT, plugin_texts)
        self.assertEqual(counter, "plugin_js_tecnico_ignorado: 1")

    def test_explicit_jp_dense_matches_default(self):
        default = self.run_extractor()
        explicit = self.run_extractor(["--plugin-js-mode", "jp-dense"])
        _, default_counter = self.read_jsonl_texts_and_counter(default)
        _, explicit_counter = self.read_jsonl_texts_and_counter(explicit)
        self.assertEqual(default_counter, explicit_counter)

    def test_all_mode_restores_current_behavior(self):
        result = self.run_extractor(["--plugin-js-mode", "all"])
        plugin_texts, counter = self.read_jsonl_texts_and_counter(result)
        self.assertEqual(len(plugin_texts), 3)
        self.assertIn(TECHNICAL_TEXT, plugin_texts)
        self.assertIn(KANA_TEXT, plugin_texts)
        self.assertIn(BRACKET_TEXT, plugin_texts)
        self.assertEqual(counter, "plugin_js_tecnico_ignorado: 0")


if __name__ == "__main__":
    unittest.main()
