# -*- coding: utf-8 -*-
"""Testes do adapter Godot (.tscn/.tres/.csv/.po/.json).

Cobertura:
- detect com project.godot => True; sem => False.
- detect com path inexistente => False.
- detect via detect_engine.
- extract: .tscn com nos textuais, .csv com traducoes, .po com msgstr.
- Ignora text="X" vazio.
- metadata correta com tscn_count, csv_count, po_count.
- register_adapter registrou "godot" no REGISTRY.
- Todas entries tem campos obrigatorios.

Somente biblioteca padrao. Mensagens em pt-BR sem acento.
"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIB_DIR = HERE.parent / "scripts" / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from adapters import (  # noqa: E402
    EngineAdapter,
    TextEntry,
    REGISTRY,
    detect_engine,
    get_adapter,
)

FIXTURE_GAME = str(HERE / "fixtures" / "game_godot")
FIXTURE_NON_GODOT = str(HERE / "fixtures" / "report")  # pasta sem project.godot


class GodotRegistryTests(unittest.TestCase):
    """Testes de registro do adapter godot."""

    def test_godot_in_registry(self):
        self.assertIn("godot", REGISTRY)

    def test_get_adapter_godot_returns_instance(self):
        adapter = get_adapter("godot")
        self.assertIsInstance(adapter, EngineAdapter)


class GodotDetectTests(unittest.TestCase):
    """Testes de deteccao de engine Godot."""

    def setUp(self):
        self.adapter = get_adapter("godot")

    def test_detect_godot_game_returns_true(self):
        self.assertTrue(self.adapter.detect(FIXTURE_GAME))

    def test_detect_non_godot_returns_false(self):
        self.assertFalse(self.adapter.detect(FIXTURE_NON_GODOT))

    def test_detect_nonexistent_path_returns_false(self):
        self.assertFalse(self.adapter.detect("/caminho/inexistente/xyz"))

    def test_detect_via_detect_engine(self):
        name, meta = detect_engine(FIXTURE_GAME)
        self.assertEqual(name, "godot")
        self.assertEqual(meta.get("engine"), "godot")
        self.assertGreaterEqual(meta.get("tscn_count", 0), 1)


class GodotExtractTscnTests(unittest.TestCase):
    """Testes de extracao de .tscn/.tres."""

    def setUp(self):
        self.adapter = get_adapter("godot")
        self.entries = list(self.adapter.extract(FIXTURE_GAME))

    def _tscn_entries(self):
        return [e for e in self.entries if e.category == "godot_tscn"]

    def test_tscn_entries_present(self):
        tscn = self._tscn_entries()
        self.assertGreater(len(tscn), 0, "deve haver entradas godot_tscn")

    def test_tscn_extracts_text_property(self):
        tscn = self._tscn_entries()
        sources = [e.source for e in tscn]
        self.assertIn(
            "Pressione Enter",
            sources,
            "tscn deve extrair text='Pressione Enter'",
        )

    def test_tscn_extracts_tooltip_text(self):
        tscn = self._tscn_entries()
        sources = [e.source for e in tscn]
        self.assertIn(
            "Clique aqui para continuar",
            sources,
            "tscn deve extrair tooltip_text",
        )

    def test_tscn_extracts_placeholder_text(self):
        tscn = self._tscn_entries()
        sources = [e.source for e in tscn]
        self.assertIn(
            "Digite seu nome",
            sources,
            "tscn deve extrair placeholder_text",
        )

    def test_tscn_extracts_dialog_text(self):
        tscn = self._tscn_entries()
        sources = [e.source for e in tscn]
        self.assertIn(
            "Bem-vindo ao jogo!",
            sources,
            "tscn deve extrair dialog_text",
        )

    def test_tscn_extracts_title(self):
        tscn = self._tscn_entries()
        sources = [e.source for e in tscn]
        self.assertIn(
            "Menu Principal",
            sources,
            "tscn deve extrair title",
        )

    def test_tscn_ignores_empty_text(self):
        """text="" nao deve ser extraido."""
        tscn = self._tscn_entries()
        sources = [e.source for e in tscn]
        self.assertNotIn(
            "",
            sources,
            "tscn nao deve extrair text vazio",
        )

    def test_tscn_extracts_button_text(self):
        tscn = self._tscn_entries()
        sources = [e.source for e in tscn]
        self.assertIn(
            "Iniciar",
            sources,
            "tscn deve extrair text='Iniciar' do Button",
        )


class GodotExtractCsvTests(unittest.TestCase):
    """Testes de extracao de .csv de traducao."""

    def setUp(self):
        self.adapter = get_adapter("godot")
        self.entries = list(self.adapter.extract(FIXTURE_GAME))

    def _csv_entries(self):
        return [e for e in self.entries if e.category == "godot_csv"]

    def test_csv_entries_present(self):
        csv = self._csv_entries()
        self.assertGreater(len(csv), 0, "deve haver entradas godot_csv")

    def test_csv_extracts_japanese(self):
        csv = self._csv_entries()
        sources = [e.source for e in csv]
        self.assertIn(
            "こんにちは",
            sources,
            "csv deve extrair valor ja (japones)",
        )

    def test_csv_extracts_japanese_farewell(self):
        csv = self._csv_entries()
        sources = [e.source for e in csv]
        self.assertIn(
            "さようなら",
            sources,
            "csv deve extrair farewell ja",
        )

    def test_csv_does_not_extract_english(self):
        """Coluna en (ingles) nao deve ser extraida (ja esta em ingles)."""
        csv = self._csv_entries()
        sources = [e.source for e in csv]
        # English values should not appear since _is_english_only returns True
        self.assertNotIn("Hello", sources)
        self.assertNotIn("Goodbye", sources)

    def test_csv_has_key_in_source_key(self):
        csv = self._csv_entries()
        keys = [e.source_key for e in csv]
        self.assertTrue(
            any("greeting" in k for k in keys),
            "source_key deve conter 'greeting'",
        )

    def test_csv_has_language_in_context(self):
        csv = self._csv_entries()
        langs = [e.context.get("language") for e in csv]
        self.assertIn("ja", langs, "context deve conter language=ja")


class GodotExtractPoTests(unittest.TestCase):
    """Testes de extracao de .po."""

    def setUp(self):
        self.adapter = get_adapter("godot")
        self.entries = list(self.adapter.extract(FIXTURE_GAME))

    def _po_entries(self):
        return [e for e in self.entries if e.category == "godot_po"]

    def test_po_entries_present(self):
        po = self._po_entries()
        self.assertGreater(len(po), 0, "deve haver entradas godot_po")

    def test_po_extracts_msgstr(self):
        po = self._po_entries()
        sources = [e.source for e in po]
        self.assertIn(
            "Press Enter",
            sources,
            "po deve extrair msgstr 'Press Enter'",
        )

    def test_po_extracts_second_entry(self):
        po = self._po_entries()
        sources = [e.source for e in po]
        self.assertIn(
            "Welcome to the game!",
            sources,
            "po deve extrair msgstr 'Welcome to the game!'",
        )

    def test_po_context_has_msgid(self):
        po = self._po_entries()
        msgids = [e.context.get("msgid") for e in po]
        self.assertIn(
            "Pressione Enter",
            msgids,
            "context deve conter msgid original",
        )


class GodotMetadataTests(unittest.TestCase):
    """Testes de metadata do adapter Godot."""

    def setUp(self):
        self.adapter = get_adapter("godot")
        self.meta = self.adapter.metadata(FIXTURE_GAME)

    def test_metadata_engine(self):
        self.assertEqual(self.meta["engine"], "godot")

    def test_metadata_tscn_count(self):
        self.assertIn("tscn_count", self.meta)
        self.assertGreaterEqual(self.meta["tscn_count"], 1)

    def test_metadata_csv_count(self):
        self.assertIn("csv_count", self.meta)
        self.assertGreaterEqual(self.meta["csv_count"], 1)

    def test_metadata_po_count(self):
        self.assertIn("po_count", self.meta)
        self.assertGreaterEqual(self.meta["po_count"], 1)


class GodotEntryFieldsTests(unittest.TestCase):
    """Testes de campos obrigatorios em todas as entries."""

    def setUp(self):
        self.adapter = get_adapter("godot")
        self.entries = list(self.adapter.extract(FIXTURE_GAME))

    def test_all_entries_have_required_fields(self):
        for entry in self.entries:
            self.assertIsInstance(entry, TextEntry)
            self.assertTrue(entry.file, "file nao pode ser vazio")
            self.assertGreater(entry.line, 0, "line deve ser > 0")
            self.assertTrue(entry.source, "source nao pode ser vazio")
            self.assertTrue(entry.source_key, "source_key nao pode ser vazio")
            self.assertTrue(entry.category, "category nao pode ser vazio")

    def test_all_entries_are_godot_categories(self):
        valid = {"godot_tscn", "godot_csv", "godot_po", "godot_json"}
        for entry in self.entries:
            self.assertIn(
                entry.category,
                valid,
                "category %r deve ser uma categoria godot valida" % entry.category,
            )


if __name__ == "__main__":
    unittest.main()
