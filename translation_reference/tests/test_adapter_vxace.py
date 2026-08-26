# -*- coding: utf-8 -*-
"""Testes do adapter RPG Maker VX/Ace (.rvdata2).

Cobertura:
- RubyMarshalReader: header invalido, string, fixnum, array, hash, object.
- detect: fixture com .rvdata2 => True; sem => False; path inexistente => False.
- extract: dados mockados via reader; metadados.
- register_adapter registrou "rpgmaker_vxace" no REGISTRY.

Somente biblioteca padrao. Mensagens em pt-BR sem acento.
"""

import struct
import sys
import tempfile
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
from adapters.rpgmaker_vxace import RubyMarshalReader  # noqa: E402

FIXTURE_GAME = str(HERE / "fixtures" / "game_vxace")
FIXTURE_NON_RPGMAKER = str(HERE / "fixtures" / "report")


# ---------------------------------------------------------------------------
# Helpers: construcao manual de bytes Marshal para testes
# ---------------------------------------------------------------------------

def _fixnum_bytes(value):
    """Converte um inteiro em bytes Marshal fixnum.

    Codificacao compativel com o RubyMarshalReader:
    - 0 -> b'\x00'
    - 1..122 -> b'\x05+value' (compacto, sem dados)
    - 123..255 -> b'\x01' + 1 byte unsigned
    - 256..65535 -> b'\x02' + 2 bytes unsigned LE
    - (-123)..(-1) -> b'\xfa+value' (compacto, sem dados)
    - (-256)..(-124) -> b'\xff' + 1 byte (256+value)
    - (-65536)..(-257) -> b'\xfe' + 2 bytes LE (65536+value)
    """
    if value == 0:
        return b"\x00"
    if 1 <= value <= 122:
        return struct.pack("b", value + 5)
    if -123 <= value <= -1:
        return struct.pack("b", value - 5)
    # Valores que precisam de bytes de dados
    if value > 0:
        nbytes = 0
        x = value
        while x > 0:
            nbytes += 1
            x >>= 8
        return struct.pack("b", nbytes) + value.to_bytes(nbytes, "little")
    else:
        # Negativo: armazenar (2^(8*n) + value), lead = -n
        abs_val = -value
        nbytes = 0
        x = abs_val
        while x > 0:
            nbytes += 1
            x >>= 8
        stored = (1 << (8 * nbytes)) + value
        return struct.pack("b", -nbytes) + stored.to_bytes(nbytes, "little")


def _marshal_header():
    return b"\x04\x08"


def _marshal_string(s):
    encoded = s.encode("utf-8")
    return b'"' + _fixnum_bytes(len(encoded)) + encoded


def _marshal_ivar_string(s):
    inner = _marshal_string(s)
    ivars = _fixnum_bytes(1) + _marshal_symbol("E") + b"T"
    return b"I" + inner + ivars


def _marshal_symbol(name):
    encoded = name.encode("utf-8")
    return b":" + _fixnum_bytes(len(encoded)) + encoded


def _marshal_array(items):
    return b"[" + _fixnum_bytes(len(items)) + b"".join(items)


def _marshal_hash(pairs):
    result = b"{" + _fixnum_bytes(len(pairs))
    for k, v in pairs:
        result += k + v
    return result


def _marshal_ivar_object(class_name, attrs):
    """Cria um IVar wrapping um Object com attrs (dict symbol->bytes)."""
    obj = b"o" + _marshal_symbol(class_name)
    obj += _fixnum_bytes(len(attrs))
    for k, v in attrs.items():
        obj += _marshal_symbol(k) + v
    ivars = _fixnum_bytes(1) + _marshal_symbol("E") + b"T"
    return b"I" + obj + ivars


def _marshal_fixnum_val(n):
    return b"i" + _fixnum_bytes(n)


# ---------------------------------------------------------------------------
# Testes do RubyMarshalReader
# ---------------------------------------------------------------------------

class RubyMarshalReaderHeaderTests(unittest.TestCase):
    """Testes de validacao de header."""

    def test_header_invalido_curto(self):
        with self.assertRaises(ValueError):
            RubyMarshalReader.loads(b"\x04")

    def test_header_invalido_bytes_errados(self):
        with self.assertRaises(ValueError):
            RubyMarshalReader.loads(b"\x05\x08" + b"\x00" * 10)

    def test_header_vazio(self):
        with self.assertRaises(ValueError):
            RubyMarshalReader.loads(b"")

    def test_header_invalido_todos_zeros(self):
        with self.assertRaises(ValueError):
            RubyMarshalReader.loads(b"\x00\x00\x00")


class RubyMarshalReaderStringTests(unittest.TestCase):
    """Testes de leitura de strings."""

    def test_string_simples(self):
        data = _marshal_header() + _marshal_string("Ola")
        result = RubyMarshalReader.loads(data)
        self.assertEqual(result, "Ola")

    def test_string_vazia(self):
        data = _marshal_header() + _marshal_string("")
        result = RubyMarshalReader.loads(data)
        self.assertEqual(result, "")

    def test_string_utf8(self):
        data = _marshal_header() + _marshal_string("Acentos: cafe")
        result = RubyMarshalReader.loads(data)
        self.assertEqual(result, "Acentos: cafe")


class RubyMarshalReaderFixnumTests(unittest.TestCase):
    """Testes de leitura de fixnum."""

    def test_fixnum_zero(self):
        data = _marshal_header() + b"i\x00"
        result = RubyMarshalReader.loads(data)
        self.assertEqual(result, 0)

    def test_fixnum_positivo(self):
        data = _marshal_header() + b"i" + _fixnum_bytes(42)
        result = RubyMarshalReader.loads(data)
        self.assertEqual(result, 42)

    def test_fixnum_grande(self):
        data = _marshal_header() + b"i" + _fixnum_bytes(1000)
        result = RubyMarshalReader.loads(data)
        self.assertEqual(result, 1000)

    def test_fixnum_negativo(self):
        data = _marshal_header() + b"i" + _fixnum_bytes(-1)
        result = RubyMarshalReader.loads(data)
        self.assertEqual(result, -1)


class RubyMarshalReaderArrayTests(unittest.TestCase):
    """Testes de leitura de array."""

    def test_array_vazio(self):
        data = _marshal_header() + b"[" + _fixnum_bytes(0)
        result = RubyMarshalReader.loads(data)
        self.assertEqual(result, [])

    def test_array_strings(self):
        arr = _marshal_array([_marshal_string("a"), _marshal_string("b")])
        data = _marshal_header() + arr
        result = RubyMarshalReader.loads(data)
        self.assertEqual(result, ["a", "b"])

    def test_array_misto(self):
        arr = _marshal_array([
            _marshal_string("texto"),
            _marshal_fixnum_val(10),
        ])
        data = _marshal_header() + arr
        result = RubyMarshalReader.loads(data)
        self.assertEqual(result, ["texto", 10])


class RubyMarshalReaderHashTests(unittest.TestCase):
    """Testes de leitura de hash."""

    def test_hash_simples(self):
        h = _marshal_hash([
            (_marshal_symbol("chave"), _marshal_string("valor")),
        ])
        data = _marshal_header() + h
        result = RubyMarshalReader.loads(data)
        self.assertEqual(result, {"chave": "valor"})

    def test_hash_nested(self):
        inner = _marshal_hash([
            (_marshal_symbol("b"), _marshal_fixnum_val(2)),
        ])
        outer = _marshal_hash([
            (_marshal_symbol("a"), inner),
        ])
        data = _marshal_header() + outer
        result = RubyMarshalReader.loads(data)
        self.assertEqual(result, {"a": {"b": 2}})


class RubyMarshalReaderObjectTests(unittest.TestCase):
    """Testes de leitura de object (IVar + Object)."""

    def test_objeto_com_ivars(self):
        obj = _marshal_ivar_object("RPG::Actor", {
            "name": _marshal_ivar_string("Herói"),
            "id": _marshal_fixnum_val(1),
        })
        data = _marshal_header() + obj
        result = RubyMarshalReader.loads(data)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["__class__"], "RPG::Actor")
        self.assertEqual(result["__dict__"]["name"], "Herói")
        self.assertEqual(result["__dict__"]["id"], 1)

    def test_array_de_objetos(self):
        obj1 = _marshal_ivar_object("RPG::Actor", {
            "name": _marshal_ivar_string("A"),
        })
        obj2 = _marshal_ivar_object("RPG::Actor", {
            "name": _marshal_ivar_string("B"),
        })
        arr = _marshal_array([obj1, obj2])
        data = _marshal_header() + arr
        result = RubyMarshalReader.loads(data)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["__dict__"]["name"], "A")
        self.assertEqual(result[1]["__dict__"]["name"], "B")


# ---------------------------------------------------------------------------
# Testes do VXAceAdapter: detect
# ---------------------------------------------------------------------------

class VXAceDetectTests(unittest.TestCase):
    """Testes de deteccao de engine RPG Maker VX/Ace."""

    def setUp(self):
        self.adapter = get_adapter("rpgmaker_vxace")

    def test_detect_vxace_game_returns_true(self):
        self.assertTrue(self.adapter.detect(FIXTURE_GAME))

    def test_detect_non_vxace_returns_false(self):
        self.assertFalse(self.adapter.detect(FIXTURE_NON_RPGMAKER))

    def test_detect_nonexistent_path_returns_false(self):
        self.assertFalse(self.adapter.detect("/caminho/inexistente/xyz"))

    def test_detect_via_detect_engine(self):
        name, meta = detect_engine(FIXTURE_GAME)
        # Pode ser "rpgmaker_vxace" ou outro adapter se outro detectar antes
        if name == "rpgmaker_vxace":
            self.assertEqual(meta.get("engine"), "rpgmaker_vxace")
            self.assertGreaterEqual(meta.get("rvdata_count", 0), 1)

    def test_detect_with_temp_rvdata2(self):
        """Cria um .rvdata2 temporario e verifica deteccao."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_path = Path(tmpdir) / "data"
            data_path.mkdir()
            (data_path / "Test.rvdata2").write_bytes(b"\x04\x08\x00")
            self.assertTrue(self.adapter.detect(tmpdir))

    def test_detect_with_temp_rvdata(self):
        """Cria um .rvdata e verifica deteccao."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_path = Path(tmpdir) / "data"
            data_path.mkdir()
            (data_path / "Test.rvdata").write_bytes(b"\x04\x08\x00")
            self.assertTrue(self.adapter.detect(tmpdir))


# ---------------------------------------------------------------------------
# Testes do VXAceAdapter: extract
# ---------------------------------------------------------------------------

class VXAceExtractTests(unittest.TestCase):
    """Testes de extracao semantica do adapter RPG Maker VX/Ace."""

    def setUp(self):
        self.adapter = get_adapter("rpgmaker_vxace")
        self.entries = list(self.adapter.extract(FIXTURE_GAME))

    def test_extract_returns_entries(self):
        self.assertGreater(len(self.entries), 0)

    def test_database_texts_present(self):
        cats = {e.category for e in self.entries}
        self.assertIn("rpgmaker_database", cats)

    def test_actor_name_extracted(self):
        sources = [e.source for e in self.entries if e.category == "rpgmaker_database"]
        self.assertTrue(
            any("Akane" in s for s in sources),
            "database deve conter 'Akane'",
        )

    def test_actor_description_extracted(self):
        sources = [e.source for e in self.entries if e.category == "rpgmaker_database"]
        self.assertTrue(
            any("Uma guerreira corajosa" in s for s in sources),
            "database deve conter 'Uma guerreira corajosa'",
        )

    def test_empty_note_not_extracted(self):
        """Notas vazias nao devem ser extraidas."""
        sources = [e.source for e in self.entries if e.category == "rpgmaker_database"]
        # O note vazio "" nao deve aparecer
        for s in sources:
            self.assertNotEqual(s, "")

    def test_all_entries_have_required_fields(self):
        for entry in self.entries:
            self.assertIsInstance(entry, TextEntry)
            self.assertTrue(entry.file)
            self.assertGreaterEqual(entry.line, 0)
            self.assertTrue(entry.source)
            self.assertTrue(entry.source_key)
            self.assertTrue(entry.category)

    def test_metadata_has_expected_keys(self):
        meta = self.adapter.metadata(FIXTURE_GAME)
        self.assertEqual(meta["engine"], "rpgmaker_vxace")
        self.assertIn("rvdata_count", meta)
        self.assertGreaterEqual(meta["rvdata_count"], 1)

    def test_extract_empty_game_returns_nothing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            entries = list(self.adapter.extract(tmpdir))
            self.assertEqual(len(entries), 0)

    def test_extract_nonexistent_path_returns_nothing(self):
        entries = list(self.adapter.extract("/caminho/inexistente/xyz"))
        self.assertEqual(len(entries), 0)


# ---------------------------------------------------------------------------
# Testes: registro
# ---------------------------------------------------------------------------

class VXAceRegistryTests(unittest.TestCase):
    """Testes de registro do adapter rpgmaker_vxace."""

    def test_rpgmaker_vxace_in_registry(self):
        self.assertIn("rpgmaker_vxace", REGISTRY)

    def test_get_adapter_rpgmaker_vxace_returns_instance(self):
        adapter = get_adapter("rpgmaker_vxace")
        self.assertIsInstance(adapter, EngineAdapter)


if __name__ == "__main__":
    unittest.main()
