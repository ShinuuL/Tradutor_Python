# -*- coding: utf-8 -*-
"""Testes do adapter Kirikiri/NScripter (.ks).

Cobertura:
- detect com fixture .ks em scenario/ => True; com estrutura Tyrano => False.
- detect com path inexistente => False.
- extract: dialogue, eval strings, dialog tags, macros.
- skip: linhas puramente comandos nao emitidas.
- metadata correta com ks_count.
- register_adapter registrou "kirikiri" no REGISTRY.

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

FIXTURE_GAME = str(HERE / "fixtures" / "game_kirikiri")
FIXTURE_TYRANO = str(HERE / "fixtures" / "game_tyrano")  # tem data/scenario/
FIXTURE_NON_KIRIKIRI = str(HERE / "fixtures" / "report")  # pasta sem .ks em scenario/


class KirikiriRegistryTests(unittest.TestCase):
    """Testes de registro do adapter kirikiri."""

    def test_kirikiri_in_registry(self):
        self.assertIn("kirikiri", REGISTRY)

    def test_get_adapter_kirikiri_returns_instance(self):
        adapter = get_adapter("kirikiri")
        self.assertIsInstance(adapter, EngineAdapter)


class KirikiriDetectTests(unittest.TestCase):
    """Testes de deteccao de engine Kirikiri."""

    def setUp(self):
        self.adapter = get_adapter("kirikiri")

    def test_detect_kirikiri_game_returns_true(self):
        self.assertTrue(self.adapter.detect(FIXTURE_GAME))

    def test_detect_tyrano_structure_returns_false(self):
        """Estrutura Tyrano (data/scenario/) nao deve ser detectada como Kirikiri."""
        self.assertFalse(self.adapter.detect(FIXTURE_TYRANO))

    def test_detect_non_kirikiri_returns_false(self):
        self.assertFalse(self.adapter.detect(FIXTURE_NON_KIRIKIRI))

    def test_detect_nonexistent_path_returns_false(self):
        self.assertFalse(self.adapter.detect("/caminho/inexistente/xyz"))

    def test_detect_via_detect_engine(self):
        name, meta = detect_engine(FIXTURE_GAME)
        self.assertEqual(name, "kirikiri")
        self.assertEqual(meta.get("engine"), "kirikiri")
        self.assertGreaterEqual(meta.get("ks_count", 0), 1)


class KirikiriExtractTests(unittest.TestCase):
    """Testes de extracao semantica do adapter Kirikiri."""

    def setUp(self):
        self.adapter = get_adapter("kirikiri")
        self.entries = list(self.adapter.extract(FIXTURE_GAME))

    def _categories_of(self):
        return {e.category for e in self.entries}

    def _sources_of(self, category):
        return [e.source for e in self.entries if e.category == category]

    def test_extract_returns_entries(self):
        self.assertGreater(len(self.entries), 0)

    def test_dialogue_present(self):
        cats = self._categories_of()
        self.assertIn("kirikiri_dialogue", cats)
        sources = self._sources_of("kirikiri_dialogue")
        self.assertTrue(
            any("Dialogo simples entre comandos." in s for s in sources),
            "dialogue deve conter 'Dialogo simples entre comandos.'",
        )

    def test_dialogue_second_line(self):
        sources = self._sources_of("kirikiri_dialogue")
        self.assertTrue(
            any("Essa e a segunda linha de dialogo." in s for s in sources),
            "dialogue deve conter 'Essa e a segunda linha de dialogo.'",
        )

    def test_eval_string_present(self):
        cats = self._categories_of()
        self.assertIn("kirikiri_eval", cats)
        sources = self._sources_of("kirikiri_eval")
        self.assertTrue(
            any("Ola, mundo!" in s for s in sources),
            "eval deve conter 'Ola, mundo!'",
        )

    def test_dialog_tag_present(self):
        cats = self._categories_of()
        self.assertIn("kirikiri_dialog", cats)
        sources = self._sources_of("kirikiri_dialog")
        self.assertTrue(
            any("Texto via dialog tag" in s for s in sources),
            "dialog deve conter 'Texto via dialog tag'",
        )

    def test_macro_text_present(self):
        cats = self._categories_of()
        self.assertIn("kirikiri_macro", cats)
        sources = self._sources_of("kirikiri_macro")
        self.assertTrue(
            any("Texto dentro do macro." in s for s in sources),
            "macro deve conter 'Texto dentro do macro.'",
        )

    def test_macro_second_line(self):
        sources = self._sources_of("kirikiri_macro")
        self.assertTrue(
            any("Segunda linha do macro." in s for s in sources),
            "macro deve conter 'Segunda linha do macro.'",
        )

    def test_text_after_endmacro_is_dialogue(self):
        """Texto apos [endmacro] deve ser dialogue, nao macro."""
        sources_d = self._sources_of("kirikiri_dialogue")
        self.assertTrue(
            any("Macro apos endmacro nao e mais macro." in s for s in sources_d),
            "texto apos endmacro deve ser dialogue",
        )

    def test_skip_pure_command_lines(self):
        """Linhas puramente comandos ([jump], [eval], [if] etc) nao devem ser emitidas."""
        sources_all = [e.source for e in self.entries]
        self.assertNotIn("[jump storage=\"chapter1.ks\" target=\"*begin\"]", sources_all)
        self.assertNotIn("[eval exp=\"f.flag = 0\"]", sources_all)
        self.assertNotIn("[playbgm storage=\"bgm01.ogg\"]", sources_all)
        self.assertNotIn("[wait time=1000]", sources_all)
        self.assertNotIn("[stop]", sources_all)
        self.assertNotIn("[return]", sources_all)

    def test_skip_if_endif_block(self):
        """Blocos [if]...[endif] nao devem produzir entradas."""
        sources_all = [e.source for e in self.entries]
        self.assertNotIn("[if exp=\"f.flag == 1\"]", sources_all)
        self.assertNotIn("[endif]", sources_all)

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
        self.assertEqual(meta["engine"], "kirikiri")
        self.assertIn("ks_count", meta)
        self.assertGreaterEqual(meta["ks_count"], 1)


if __name__ == "__main__":
    unittest.main()
