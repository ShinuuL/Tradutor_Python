# -*- coding: utf-8 -*-
"""Testes do adapter TyranoScript/TyranoBuilder (.ks).

Cobertura:
- detect com fixture .ks => True; sem => False.
- detect com path inexistente => False.
- extract: dialogue, menu, font-styled text.
- skip: linhas puramente tags nao emitidas.
- metadata correta com ks_count.
- register_adapter registrou "tyrano" no REGISTRY.

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

FIXTURE_GAME = str(HERE / "fixtures" / "game_tyrano")
FIXTURE_NON_TYRANO = str(HERE / "fixtures" / "report")  # pasta sem .ks em data/scenario/


class TyranoRegistryTests(unittest.TestCase):
    """Testes de registro do adapter tyrano."""

    def test_tyrano_in_registry(self):
        self.assertIn("tyrano", REGISTRY)

    def test_get_adapter_tyrano_returns_instance(self):
        adapter = get_adapter("tyrano")
        self.assertIsInstance(adapter, EngineAdapter)


class TyranoDetectTests(unittest.TestCase):
    """Testes de deteccao de engine TyranoScript."""

    def setUp(self):
        self.adapter = get_adapter("tyrano")

    def test_detect_tyrano_game_returns_true(self):
        self.assertTrue(self.adapter.detect(FIXTURE_GAME))

    def test_detect_non_tyrano_returns_false(self):
        self.assertFalse(self.adapter.detect(FIXTURE_NON_TYRANO))

    def test_detect_nonexistent_path_returns_false(self):
        self.assertFalse(self.adapter.detect("/caminho/inexistente/xyz"))

    def test_detect_via_detect_engine(self):
        name, meta = detect_engine(FIXTURE_GAME)
        self.assertEqual(name, "tyrano")
        self.assertEqual(meta.get("engine"), "tyrano")
        self.assertGreaterEqual(meta.get("ks_count", 0), 1)


class TyranoExtractTests(unittest.TestCase):
    """Testes de extracao semantica do adapter TyranoScript."""

    def setUp(self):
        self.adapter = get_adapter("tyrano")
        self.entries = list(self.adapter.extract(FIXTURE_GAME))

    def _categories_of(self):
        return {e.category for e in self.entries}

    def _sources_of(self, category):
        return [e.source for e in self.entries if e.category == category]

    def test_extract_returns_entries(self):
        self.assertGreater(len(self.entries), 0)

    def test_dialogue_present(self):
        cats = self._categories_of()
        self.assertIn("tyrano_dialogue", cats)
        sources = self._sources_of("tyrano_dialogue")
        self.assertTrue(
            any("Ola, mundo!" in s for s in sources),
            "dialogue deve conter 'Ola, mundo!'",
        )

    def test_character_name_present(self):
        cats = self._categories_of()
        self.assertIn("tyrano_name", cats)
        sources = self._sources_of("tyrano_name")
        self.assertTrue(
            any("hero" in s for s in sources),
            "name deve conter 'hero'",
        )

    def test_menu_items_present(self):
        cats = self._categories_of()
        self.assertIn("tyrano_menu", cats)
        sources = self._sources_of("tyrano_menu")
        self.assertTrue(
            any("Opcao A" in s for s in sources),
            "menu deve conter 'Opcao A'",
        )

    def test_font_styled_text_present(self):
        cats = self._categories_of()
        self.assertIn("tyrano_font", cats)
        sources = self._sources_of("tyrano_font")
        self.assertTrue(
            any("Bem-vindos" in s for s in sources),
            "font deve conter 'Bem-vindos'",
        )

    def test_skip_pure_tag_lines(self):
        """Linhas puramente tags ([return], [op], [l]) nao devem ser emitidas."""
        sources_all = [e.source for e in self.entries]
        # [return] e [op] sao tags puras e nao devem aparecer como dialogue.
        self.assertNotIn("[return]", sources_all)
        self.assertNotIn("[l]", sources_all)
        # [op]Isso e um comando[/op] e uma tag com conteudo; o conteudo
        # "Isso e um comando" esta entre tags e nao e dialogue puro.
        self.assertNotIn("[op]Isso e um comando[/op]", sources_all)

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
        self.assertEqual(meta["engine"], "tyrano")
        self.assertIn("ks_count", meta)
        self.assertGreaterEqual(meta["ks_count"], 1)


if __name__ == "__main__":
    unittest.main()
