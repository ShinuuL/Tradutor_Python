# -*- coding: utf-8 -*-
"""Testes offline da memoria de traducao (unittest, somente stdlib).

Cobertura exigida pelo objetivo "memoria de traducao":
- lookup acerta e erra por texto exato com strip;
- carga preguicosa (lazy): construtor nao toca no disco;
- gravacao append-only: arquivo cresce e bytes antigos permanecem;
- recarga apos reopen mantendo a traducao MAIS RECENTE em duplicatas;
- linha corrompida/vazia e ignorada sem interromper a carga;
- fixture sample_tm.jsonl permanece intocado em uso somente leitura.

Arquivos temporarios ficam em tests/tmp_tm (limpo no tearDown).
"""
import json
import shutil
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIB_DIR = HERE.parent / "scripts" / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

import tm_store  # noqa: E402

FIXTURE_TM = HERE / "fixtures" / "tm" / "sample_tm.jsonl"
TMP = HERE / "tmp_tm"

JP_DEMO = "これは日本語のテキストです。"
HELLO_WORLD = "こんにちは、世界。"
SLIME = "スライム"
GOBLIN = "ゴブリン"


def make_pair(source, target, **overrides):
    pair = {
        "source": source,
        "target": target,
        "lang": "ja-en",
        "file": "txt/demo.txt",
        "item_id": "T000099",
    }
    pair.update(overrides)
    return pair


def jsonl_lines(raw):
    return [line for line in raw.decode("utf-8").split("\n") if line.strip()]


class TMStoreCase(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(TMP, ignore_errors=True)
        TMP.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(TMP, ignore_errors=True)

    def tmp_file(self, name="tm.jsonl"):
        return TMP / name


class LookupTests(TMStoreCase):
    def test_hit_miss_and_strip_from_fixture(self):
        before = FIXTURE_TM.read_bytes()
        store = tm_store.TMStore(FIXTURE_TM)

        self.assertEqual(store.lookup(JP_DEMO), "This is Japanese text.")
        self.assertEqual(store.lookup(HELLO_WORLD), "Hello, world.")
        self.assertEqual(store.lookup("  " + SLIME + "\n"), "Slime", "chave ignora espacos")
        self.assertIsNone(store.lookup("存在しないテキスト"))
        self.assertIsNone(store.lookup(""))
        self.assertEqual(
            FIXTURE_TM.read_bytes(),
            before,
            "fixture nao pode mudar em uso somente leitura",
        )

    def test_fixture_duplicate_keeps_most_recent(self):
        store = tm_store.TMStore(FIXTURE_TM)
        self.assertEqual(store.lookup(GOBLIN), "Goblin")

    def test_corrupted_and_blank_lines_are_ignored(self):
        store = tm_store.TMStore(FIXTURE_TM)
        # Entradas antes e depois da linha corrompida continuam acessiveis.
        self.assertIsNotNone(store.lookup(JP_DEMO))
        self.assertIsNotNone(store.lookup(SLIME))

    def test_custom_corrupted_lines_do_not_crash_load(self):
        path = self.tmp_file()
        lines = [
            json.dumps(make_pair("A", "Alpha", ts=1.0), ensure_ascii=False),
            "{json truncado de proposito",
            "",
            "nao-e-json",
            json.dumps(make_pair("B", "Beta", ts=2.0), ensure_ascii=False),
        ]
        path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))

        store = tm_store.TMStore(path)
        self.assertEqual(store.lookup("A"), "Alpha")
        self.assertEqual(store.lookup("B"), "Beta")


class AppendPersistenceTests(TMStoreCase):
    def test_add_many_appends_and_grows_file(self):
        path = self.tmp_file()
        store = tm_store.TMStore(path)
        self.assertFalse(path.exists())

        store.add_many([make_pair("一つ目", "First")])
        self.assertTrue(path.exists(), "add_many cria o arquivo")
        first_raw = path.read_bytes()
        self.assertEqual(len(jsonl_lines(first_raw)), 1)

        store.add_many([make_pair("二つ目", "Second"), make_pair("三つ目", "Third")])
        second_raw = path.read_bytes()
        self.assertGreater(len(second_raw), len(first_raw), "arquivo deve crescer no append")
        self.assertTrue(second_raw.startswith(first_raw), "append-only: bytes antigos intactos")
        self.assertEqual(len(jsonl_lines(second_raw)), 3)
        self.assertEqual(store.lookup("二つ目"), "Second")
        self.assertEqual(store.lookup("三つ目"), "Third")

    def test_reopen_reloads_latest_translation_on_duplicates(self):
        path = self.tmp_file()
        session_one = tm_store.TMStore(path)
        session_one.add_many([make_pair(GOBLIN, "Gobrin", ts=100.0)])

        reopened = tm_store.TMStore(path)
        self.assertEqual(reopened.lookup(GOBLIN), "Gobrin")

        session_one.add_many([make_pair(GOBLIN, "Goblin", ts=200.0)])

        again = tm_store.TMStore(path)
        self.assertEqual(again.lookup(GOBLIN), "Goblin", "ultima ocorrencia deve vencer")
        self.assertEqual(
            len(jsonl_lines(path.read_bytes())),
            2,
            "duplicata permanece como duas linhas (sem reescrita)",
        )

    def test_reopen_sees_entries_from_previous_session(self):
        path = self.tmp_file()
        session_one = tm_store.TMStore(path)
        session_one.add_many([make_pair(JP_DEMO, "This is Japanese text.")])

        session_two = tm_store.TMStore(path)
        self.assertEqual(session_two.lookup(JP_DEMO), "This is Japanese text.")


class LazyLoadAndDirsTests(TMStoreCase):
    def test_constructor_does_not_touch_disk_until_first_use(self):
        nested = TMP / "a" / "b" / "tm.jsonl"
        store = tm_store.TMStore(nested)
        self.assertFalse((TMP / "a").exists(), "construtor nao deve criar diretorios")

        store.add_many([make_pair("テスト", "Test")])
        self.assertTrue(nested.exists(), "add_many cria diretorio pai e arquivo")

    def test_lookup_on_missing_file_returns_none_without_creating_it(self):
        path = self.tmp_file()
        store = tm_store.TMStore(path)
        self.assertIsNone(store.lookup("qualquer"))
        self.assertFalse(path.exists(), "lookup nao deve criar o arquivo")

    def test_empty_add_many_writes_nothing(self):
        path = self.tmp_file()
        store = tm_store.TMStore(path)
        store.add_many([])
        self.assertFalse(path.exists())


class ValidationAndEncodingTests(TMStoreCase):
    def test_record_fields_have_defaults(self):
        path = self.tmp_file()
        store = tm_store.TMStore(path)
        store.add_many([{"source": "鍵", "target": "Key"}])

        record = json.loads(jsonl_lines(path.read_bytes())[0])
        self.assertEqual(
            set(record),
            {"source", "target", "lang", "file", "item_id", "ts"},
        )
        self.assertEqual(record["lang"], "ja-en")
        self.assertEqual(record["file"], "")
        self.assertEqual(record["item_id"], "")
        self.assertIsInstance(record["ts"], float)

    def test_invalid_pairs_raise_before_any_write(self):
        path = self.tmp_file()
        store = tm_store.TMStore(path)

        with self.assertRaises(ValueError):
            store.add_many([{"source": "ソース"}])  # target ausente
        with self.assertRaises(ValueError):
            store.add_many([{"source": "", "target": ""}])
        with self.assertRaises(TypeError):
            store.add_many(["nao sou um dict"])
        with self.assertRaises(ValueError):
            store.add_many([make_pair("x", "y", ts="ontem")])

        self.assertFalse(path.exists(), "par invalido nao pode gravar nada")

    def test_file_is_utf8_jsonl_without_bom(self):
        path = self.tmp_file()
        store = tm_store.TMStore(path)
        store.add_many([make_pair("日本語", "Japanese")])

        raw = path.read_bytes()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
        records = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
        self.assertEqual(records[0]["source"], "日本語")


if __name__ == "__main__":
    unittest.main()
