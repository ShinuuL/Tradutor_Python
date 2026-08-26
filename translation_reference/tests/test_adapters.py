# -*- coding: utf-8 -*-
"""Testes dos adapters multi-engine e do adapter Ren'Py (unittest, stdlib).

Cobertura:
- TextEntry: criacao e campos.
- REGISTRY: get_adapter("renpy") retorna instancia.
- detect_engine com fixture Ren'Py retorna ("renpy", {...}).
- detect_engine com pasta nao-RenPy retorna (None, {}).
- extract em fixture .rpy contem dialogue, menu items, translate blocks, variables.
- filter_by_engine: adapter vence; fallback mantem scanner.

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
from adapters.scanner_integration import filter_by_engine  # noqa: E402

FIXTURE_GAME = str(HERE / "fixtures" / "game_renpy")
FIXTURE_NON_RENPY = str(HERE / "fixtures" / "report")  # pasta sem .rpy


class TextEntryTests(unittest.TestCase):
    """Testes de criacao e campos do TextEntry."""

    def test_creation_with_required_fields(self):
        entry = TextEntry(
            file="script.rpy",
            line=10,
            source="Bom dia!",
            source_key="dialogue.start.10",
            category="renpy_dialogue",
        )
        self.assertEqual(entry.file, "script.rpy")
        self.assertEqual(entry.line, 10)
        self.assertEqual(entry.source, "Bom dia!")
        self.assertEqual(entry.source_key, "dialogue.start.10")
        self.assertEqual(entry.category, "renpy_dialogue")
        self.assertEqual(entry.context, {})

    def test_creation_with_context(self):
        ctx = {"label": "start", "extra": True}
        entry = TextEntry(
            file="script.rpy",
            line=5,
            source="Hello",
            source_key="dialogue.start.5",
            category="renpy_dialogue",
            context=ctx,
        )
        self.assertEqual(entry.context, ctx)

    def test_immutable(self):
        entry = TextEntry(
            file="script.rpy",
            line=1,
            source="X",
            source_key="k",
            category="cat",
        )
        with self.assertRaises(AttributeError):
            entry.source = "Y"


class RegistryTests(unittest.TestCase):
    """Testes do registro global de adapters."""

    def test_get_adapter_renpy_returns_instance(self):
        adapter = get_adapter("renpy")
        self.assertIsInstance(adapter, EngineAdapter)

    def test_get_adapter_unknown_raises_key_error(self):
        with self.assertRaises(KeyError):
            get_adapter("motor_desconhecido")

    def test_renpy_in_registry(self):
        self.assertIn("renpy", REGISTRY)


class DetectEngineTests(unittest.TestCase):
    """Testes de deteccao de engine por pasta."""

    def test_detect_renpy_game_returns_renpy(self):
        name, meta = detect_engine(FIXTURE_GAME)
        self.assertEqual(name, "renpy")
        self.assertEqual(meta.get("engine"), "renpy")
        self.assertGreaterEqual(meta.get("rpy_count", 0), 1)

    def test_detect_non_renpy_returns_none(self):
        name, meta = detect_engine(FIXTURE_NON_RENPY)
        self.assertIsNone(name)
        self.assertEqual(meta, {})

    def test_detect_nonexistent_path_returns_none(self):
        name, meta = detect_engine("/caminho/inexistente/xyz")
        self.assertIsNone(name)
        self.assertEqual(meta, {})


class ExtractTests(unittest.TestCase):
    """Testes de extracao semantica do adapter Ren'Py."""

    def setUp(self):
        self.adapter = get_adapter("renpy")
        self.entries = list(self.adapter.extract(FIXTURE_GAME))

    def _categories_of(self):
        return {e.category for e in self.entries}

    def _sources_of(self, category):
        return [e.source for e in self.entries if e.category == category]

    def test_extract_returns_entries(self):
        self.assertGreater(len(self.entries), 0)

    def test_dialogue_present(self):
        cats = self._categories_of()
        self.assertIn("renpy_dialogue", cats)
        sources = self._sources_of("renpy_dialogue")
        self.assertTrue(
            any("Bom dia" in s for s in sources),
            "dialogue deve conter 'Bom dia'",
        )

    def test_menu_items_present(self):
        cats = self._categories_of()
        self.assertIn("renpy_menu", cats)
        sources = self._sources_of("renpy_menu")
        self.assertTrue(
            any("Opcao um" in s for s in sources),
            "menu deve conter 'Opcao um'",
        )

    def test_translate_blocks_present(self):
        cats = self._categories_of()
        self.assertIn("renpy_translate", cats)
        sources = self._sources_of("renpy_translate")
        self.assertTrue(
            any("Bom dia" in s for s in sources),
            "translate deve conter old 'Bom dia'",
        )

    def test_variable_strings_present(self):
        cats = self._categories_of()
        self.assertIn("renpy_variable", cats)
        sources = self._sources_of("renpy_variable")
        self.assertTrue(
            any("Personagem Teste" in s for s in sources),
            "variable deve conter 'Personagem Teste'",
        )

    def test_all_entries_have_required_fields(self):
        for entry in self.entries:
            self.assertIsInstance(entry, TextEntry)
            self.assertTrue(entry.file)
            self.assertGreater(entry.line, 0)
            self.assertTrue(entry.source)
            self.assertTrue(entry.source_key)
            self.assertTrue(entry.category)

    def test_metadata_has_expected_keys(self):
        meta = self.adapter.metadata(FIXTURE_GAME)
        self.assertEqual(meta["engine"], "renpy")
        self.assertIn("rpy_count", meta)
        self.assertIn("label_count", meta)
        self.assertGreaterEqual(meta["rpy_count"], 1)
        self.assertGreaterEqual(meta["label_count"], 1)


class FilterByEngineTests(unittest.TestCase):
    """Testes de integracao scanner/adapters."""

    def _make_scanner_row(self, text="linha bruta", category="generic_text"):
        return {
            "root": "/jogo",
            "file": "data/Map001.json",
            "line": 1,
            "extension": ".json",
            "encoding": "utf-8",
            "reason": "cjk",
            "category": category,
            "priority": 50,
            "source_key": "$[0].name",
            "text": text,
            "occurrences": 1,
        }

    def test_no_engine_keeps_scanner_rows(self):
        scanner = [self._make_scanner_row(), self._make_scanner_row("outro")]
        result = filter_by_engine(scanner, None, [])
        self.assertEqual(result, scanner)

    def test_empty_adapter_falls_back_to_scanner(self):
        scanner = [self._make_scanner_row()]
        result = filter_by_engine(scanner, "renpy", [])
        self.assertEqual(result, scanner)

    def test_adapter_entries_replace_scanner(self):
        scanner = [self._make_scanner_row("bruto")]
        entries = [
            TextEntry(
                file="script.rpy",
                line=5,
                source="Dialogo do adapter",
                source_key="dialogue.start.5",
                category="renpy_dialogue",
                context={"label": "start"},
            )
        ]
        result = filter_by_engine(scanner, "renpy", entries)
        self.assertEqual(len(result), 1)
        row = result[0]
        self.assertEqual(row["category"], "renpy_dialogue")
        self.assertEqual(row["text"], "Dialogo do adapter")
        self.assertEqual(row["reason"], "adapter:renpy")
        self.assertEqual(row["priority"], 95)


if __name__ == "__main__":
    unittest.main()
