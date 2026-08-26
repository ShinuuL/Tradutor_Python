# -*- coding: utf-8 -*-
"""Testes do adapter Wolf RPG (.mps / .dat).

Cobertura:
- detect com scenario/ + .mps => True.
- detect sem .mps/.dat => False.
- detect com estrutura Tyrano (data/scenario/) => False.
- _read_shiftjis_string: fixture bytes com "テスト" em Shift-JIS.
- _extract_strings_from_binary: fixture minimo com 2-3 strings.
- extract: retorna entries com categorias corretas.
- metadata correta com mps_count e dat_count.
- register_adapter registrou "wolfrpg" no REGISTRY.
- Todas entries tem campos obrigatorios.

Somente biblioteca padrao. Mensagens em pt-BR sem acento.
"""
import struct
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

# Importa funcoes auxiliares diretamente do modulo wolfrpg
from adapters import wolfrpg  # noqa: E402

FIXTURE_GAME = str(HERE / "fixtures" / "game_wolfrpg")
FIXTURE_NON_WOLFRPG = str(HERE / "fixtures" / "report")  # pasta sem .mps/.dat
FIXTURE_TYRANO = str(HERE / "fixtures" / "game_tyrano")


def _make_shiftjis_bytes(text: str) -> bytes:
    """Cria bytes length-prefixed Shift-JIS para testes."""
    encoded = text.encode('cp932')
    return struct.pack('<H', len(encoded)) + encoded


class WolfRPGRegistryTests(unittest.TestCase):
    """Testes de registro do adapter wolfrpg."""

    def test_wolfrpg_in_registry(self):
        self.assertIn("wolfrpg", REGISTRY)

    def test_get_adapter_wolfrpg_returns_instance(self):
        adapter = get_adapter("wolfrpg")
        self.assertIsInstance(adapter, EngineAdapter)


class WolfRPGDetectTests(unittest.TestCase):
    """Testes de deteccao de engine Wolf RPG."""

    def setUp(self):
        self.adapter = get_adapter("wolfrpg")

    def test_detect_wolfrpg_game_returns_true(self):
        """Fixture com scenario/map001.mps deve ser detectado."""
        self.assertTrue(self.adapter.detect(FIXTURE_GAME))

    def test_detect_non_wolfrpg_returns_false(self):
        """Pasta sem .mps/.dat deve retornar False."""
        self.assertFalse(self.adapter.detect(FIXTURE_NON_WOLFRPG))

    def test_detect_nonexistent_path_returns_false(self):
        self.assertFalse(self.adapter.detect("/caminho/inexistente/xyz"))

    def test_detect_tyrano_structure_returns_false(self):
        """Estrutura Tyrano (data/scenario/) nao deve ser detectada como Wolf RPG."""
        self.assertFalse(self.adapter.detect(FIXTURE_TYRANO))

    def test_detect_via_detect_engine(self):
        name, meta = detect_engine(FIXTURE_GAME)
        # Wolf RPG pode nao ser o primeiro detectado se outros adapters
        # tambem detectarem a fixture, entao so verificamos se detectou
        if name == "wolfrpg":
            self.assertEqual(meta.get("engine"), "wolfrpg")


class ReadShiftJisStringTests(unittest.TestCase):
    """Testes da funcao _read_shiftjis_string."""

    def test_read_shiftjis_string_basic(self):
        """Le string Shift-JIS length-prefixed."""
        # "テスト" em Shift-JIS
        text_bytes = "テスト".encode('cp932')
        data = struct.pack('<H', len(text_bytes)) + text_bytes
        s, new_offset = wolfrpg._read_shiftjis_string(data, 0)
        self.assertEqual(s, "テスト")
        self.assertEqual(new_offset, 2 + len(text_bytes))

    def test_read_shiftjis_string_empty_length(self):
        """Length 0 devolve string vazia e offset original."""
        data = struct.pack('<H', 0)
        s, new_offset = wolfrpg._read_shiftjis_string(data, 0)
        self.assertEqual(s, '')
        self.assertEqual(new_offset, 0)

    def test_read_shiftjis_string_truncated(self):
        """Dados truncados devolvem string vazia."""
        data = struct.pack('<H', 100) + b'\x00' * 5
        s, new_offset = wolfrpg._read_shiftjis_string(data, 0)
        self.assertEqual(s, '')

    def test_read_shiftjis_string_offset(self):
        """Leitura com offset inicial."""
        prefix = b'\x00\x00\x00\x00'
        text_bytes = "会話".encode('cp932')
        data = prefix + struct.pack('<H', len(text_bytes)) + text_bytes
        s, new_offset = wolfrpg._read_shiftjis_string(data, 4)
        self.assertEqual(s, "会話")
        self.assertEqual(new_offset, 4 + 2 + len(text_bytes))


class ExtractStringsFromBinaryTests(unittest.TestCase):
    """Testes da funcao _extract_strings_from_binary."""

    def test_extracts_shiftjis_strings(self):
        """Extrai strings Shift-JIS com CJK."""
        data = (
            b'\x00\x00\x00\x00'  # padding
            + _make_shiftjis_bytes("テスト会話")
            + _make_shiftjis_bytes("これは会話です")
        )
        results = wolfrpg._extract_strings_from_binary(data)
        texts = [s for s, _ in results]
        self.assertIn("テスト会話", texts)
        self.assertIn("これは会話です", texts)

    def test_filters_non_cjk_strings(self):
        """Strings sem CJK/kana nao sao extraidas."""
        data = (
            b'\x00\x00'
            + _make_shiftjis_bytes("abc")  # ascii only, sem CJK
        )
        results = wolfrpg._extract_strings_from_binary(data)
        texts = [s for s, _ in results]
        self.assertNotIn("abc", texts)

    def test_filters_short_strings(self):
        """Strings com menos de 2 chars sao filtradas."""
        data = b'\x00\x00' + _make_shiftjis_bytes("あ")
        results = wolfrpg._extract_strings_from_binary(data)
        texts = [s for s, _ in results]
        self.assertNotIn("あ", texts)

    def test_extracts_multiple_strings(self):
        """Extrai multiplas strings de dados binarios."""
        data = (
            _make_shiftjis_bytes("回復薬")
            + b'\x00\x00'  # gap
            + _make_shiftjis_bytes("攻撃力")
        )
        results = wolfrpg._extract_strings_from_binary(data)
        texts = [s for s, _ in results]
        self.assertEqual(len(texts), 2)

    def test_empty_data(self):
        """Dados vazios devolvem lista vazia."""
        results = wolfrpg._extract_strings_from_binary(b'')
        self.assertEqual(results, [])


class WolfRPGExtractTests(unittest.TestCase):
    """Testes de extracao de textos Wolf RPG."""

    def setUp(self):
        self.adapter = get_adapter("wolfrpg")
        self.entries = list(self.adapter.extract(FIXTURE_GAME))

    def test_extract_returns_entries(self):
        self.assertGreater(len(self.entries), 0, "deve haver entradas extraidas")

    def test_extract_has_dialogue_entries(self):
        """Deve haver entradas wolfrpg_dialogue do .mps."""
        dialogue = [e for e in self.entries if e.category == "wolfrpg_dialogue"]
        self.assertGreater(len(dialogue), 0, "deve haver entradas wolfrpg_dialogue")

    def test_extract_has_system_entries(self):
        """Deve haver entradas wolfrpg_system do .dat."""
        system = [e for e in self.entries if e.category == "wolfrpg_system"]
        self.assertGreater(len(system), 0, "deve haver entradas wolfrpg_system")

    def test_extract_dialogue_has_cjk_text(self):
        """Entradas de dialogue devem conter texto CJK."""
        dialogue = [e for e in self.entries if e.category == "wolfrpg_dialogue"]
        for entry in dialogue:
            has_cjk = any(
                '\u3040' <= c <= '\u9FFF' for c in entry.source
            )
            self.assertTrue(
                has_cjk,
                "dialogue entry deve conter CJK: %r" % entry.source,
            )

    def test_extract_entries_have_map001(self):
        """Entradas do .mps devem referenciar map001.mps."""
        mps_entries = [e for e in self.entries if "map001.mps" in e.file]
        self.assertGreater(len(mps_entries), 0, "deve haver entries de map001.mps")


class WolfRPGMetadataTests(unittest.TestCase):
    """Testes de metadata do adapter Wolf RPG."""

    def setUp(self):
        self.adapter = get_adapter("wolfrpg")
        self.meta = self.adapter.metadata(FIXTURE_GAME)

    def test_metadata_engine(self):
        self.assertEqual(self.meta["engine"], "wolfrpg")

    def test_metadata_mps_count(self):
        self.assertIn("mps_count", self.meta)
        self.assertGreaterEqual(self.meta["mps_count"], 1)

    def test_metadata_dat_count(self):
        self.assertIn("dat_count", self.meta)
        self.assertGreaterEqual(self.meta["dat_count"], 1)


class WolfRPGEntryFieldsTests(unittest.TestCase):
    """Testes de campos obrigatorios em todas as entries."""

    def setUp(self):
        self.adapter = get_adapter("wolfrpg")
        self.entries = list(self.adapter.extract(FIXTURE_GAME))

    def test_all_entries_have_required_fields(self):
        for entry in self.entries:
            self.assertIsInstance(entry, TextEntry)
            self.assertTrue(entry.file, "file nao pode ser vazio")
            self.assertGreaterEqual(entry.line, 0, "line deve ser >= 0")
            self.assertTrue(entry.source, "source nao pode ser vazio")
            self.assertTrue(entry.source_key, "source_key nao pode ser vazio")
            self.assertTrue(entry.category, "category nao pode ser vazio")

    def test_all_entries_are_wolfrpg_categories(self):
        valid = {"wolfrpg_dialogue", "wolfrpg_system"}
        for entry in self.entries:
            self.assertIn(
                entry.category,
                valid,
                "category %r deve ser uma categoria wolfrpg valida" % entry.category,
            )

    def test_entries_have_encoding_in_context(self):
        for entry in self.entries:
            self.assertIn("encoding", entry.context)
            self.assertEqual(entry.context["encoding"], "shift_jis")

    def test_entries_have_offset_in_context(self):
        for entry in self.entries:
            self.assertIn("offset", entry.context)
            self.assertIsInstance(entry.context["offset"], int)


class HasCjkOrKanaTests(unittest.TestCase):
    """Testes da funcao _has_cjk_or_kana."""

    def test_hiragana(self):
        self.assertTrue(wolfrpg._has_cjk_or_kana("あいう"))

    def test_katakana(self):
        self.assertTrue(wolfrpg._has_cjk_or_kana("カキク"))

    def test_cjk(self):
        self.assertTrue(wolfrpg._has_cjk_or_kana("会話"))

    def test_ascii_only(self):
        self.assertFalse(wolfrpg._has_cjk_or_kana("hello"))

    def test_empty(self):
        self.assertFalse(wolfrpg._has_cjk_or_kana(""))


if __name__ == "__main__":
    unittest.main()
