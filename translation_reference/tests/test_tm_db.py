# -*- coding: utf-8 -*-
"""Testes offline do banco de traducoes indexado (unittest, somente stdlib).

Cobertura exigida pelo objetivo TranslationDB:
- upsert + lookup por hash: cross-game reutilizacao;
- upsert duplicado: atualiza, nao duplica;
- count_by_status correto;
- export_jsonl: saida legivel com todos os campos;
- import_from_tmstore: JSONL existente populado corretamente;
- pending_entries e needs_translation: filtragem correta;
- DB vazio: tabelas criadas, zero entries.

Arquivos temporarios ficam em tests/tmp_tm_db (limpo no tearDown).
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

import tm_db  # noqa: E402

TMP = HERE / "tmp_tm_db"


def _make_entry(
    engine="renpy",
    game_id="GAME01",
    file="script.rpy",
    source_key="line_001",
    original="Bonjour le monde",
    translated="Hello world",
    status="tm_hit",
    notes=None,
):
    """Helper para criar um entry dict padrao."""
    entry = {
        "engine": engine,
        "game_id": game_id,
        "file": file,
        "source_key": source_key,
        "original": original,
    }
    if translated is not None:
        entry["translated"] = translated
    entry["status"] = status
    if notes is not None:
        entry["notes"] = notes
    return entry


def _make_jsonl(path, records):
    """Escreve uma lista de records como JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


class TranslationDBTestCase(unittest.TestCase):
    """Base com setup/teardown de diretorio temporario."""

    def setUp(self):
        shutil.rmtree(TMP, ignore_errors=True)
        TMP.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(TMP, ignore_errors=True)

    def tmp_db(self, name="test.sqlite"):
        return str(TMP / name)

    def tmp_jsonl(self, name="tm.jsonl"):
        return TMP / name


# ======================================================================
# Testes de tabelas vazias
# ======================================================================


class EmptyDBTests(TranslationDBTestCase):
    def test_empty_db_has_tables_and_zero_entries(self):
        db = tm_db.TranslationDB(self.tmp_db())
        try:
            result = db.lookup_by_game("ANY")
            self.assertEqual(result, [])
            counts = db.count_by_status("ANY")
            self.assertEqual(counts, {})
        finally:
            db.close()


# ======================================================================
# Testes de upsert + lookup por hash (cross-game)
# ======================================================================


class UpsertAndLookupTests(TranslationDBTestCase):
    def test_upsert_and_lookup_by_hash(self):
        db = tm_db.TranslationDB(self.tmp_db())
        try:
            entry = _make_entry()
            db.upsert(entry)

            h = tm_db.hash_text(entry["original"])
            results = db.lookup(h)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["original"], entry["original"])
            self.assertEqual(results[0]["translated"], entry["translated"])
            self.assertEqual(results[0]["engine"], entry["engine"])
            self.assertEqual(results[0]["game_id"], entry["game_id"])
        finally:
            db.close()

    def test_cross_game_reuse_by_hash(self):
        """Mesmo original em dois jogos diferentes -> lookup por hash devolve ambos."""
        db = tm_db.TranslationDB(self.tmp_db())
        try:
            e1 = _make_entry(game_id="GAME01", file="a.txt", source_key="k1")
            e2 = _make_entry(game_id="GAME02", file="b.txt", source_key="k2")
            db.upsert(e1)
            db.upsert(e2)

            h = tm_db.hash_text(e1["original"])
            results = db.lookup(h)
            self.assertEqual(len(results), 2)
            game_ids = {r["game_id"] for r in results}
            self.assertEqual(game_ids, {"GAME01", "GAME02"})
        finally:
            db.close()


# ======================================================================
# Testes de upsert duplicado (atualiza, nao duplica)
# ======================================================================


class UpsertDuplicateTests(TranslationDBTestCase):
    def test_upsert_duplicate_updates_does_not_duplicate(self):
        db = tm_db.TranslationDB(self.tmp_db())
        try:
            entry = _make_entry(translated=None, status="pending")
            db.upsert(entry)
            entry2 = _make_entry(translated="Hello!", status="tm_hit")
            db.upsert(entry2)

            h = tm_db.hash_text(entry["original"])
            results = db.lookup(h)
            self.assertEqual(len(results), 1, "nao pode duplicar")
            self.assertEqual(results[0]["translated"], "Hello!")
            self.assertEqual(results[0]["status"], "tm_hit")

            all_entries = db.lookup_by_game(entry["game_id"])
            self.assertEqual(len(all_entries), 1)
        finally:
            db.close()


# ======================================================================
# Testes de count_by_status
# ======================================================================


class CountByStatusTests(TranslationDBTestCase):
    def test_count_by_status(self):
        db = tm_db.TranslationDB(self.tmp_db())
        try:
            db.upsert(_make_entry(source_key="k1", status="pending"))
            db.upsert(_make_entry(source_key="k2", status="tm_hit"))
            db.upsert(_make_entry(source_key="k3", status="tm_hit"))
            db.upsert(_make_entry(source_key="k4", status="failed"))
            db.upsert(_make_entry(source_key="k5", status="pending"))

            counts = db.count_by_status("GAME01")
            self.assertEqual(counts, {"pending": 2, "tm_hit": 2, "failed": 1})
        finally:
            db.close()

    def test_count_by_status_empty_game(self):
        db = tm_db.TranslationDB(self.tmp_db())
        try:
            db.upsert(_make_entry(game_id="G1", source_key="k1"))
            counts = db.count_by_status("G_NONEXISTENT")
            self.assertEqual(counts, {})
        finally:
            db.close()


# ======================================================================
# Testes de export_jsonl
# ======================================================================


class ExportJsonlTests(TranslationDBTestCase):
    def test_export_jsonl_readable_all_fields(self):
        db = tm_db.TranslationDB(self.tmp_db())
        try:
            entry = _make_entry(notes="nota teste")
            db.upsert(entry)

            out = self.tmp_jsonl("exported.jsonl")
            count = db.export_jsonl(entry["game_id"], str(out))
            self.assertEqual(count, 1)
            self.assertTrue(out.exists())

            lines = out.read_text(encoding="utf-8").strip().split("\n")
            self.assertEqual(len(lines), 1)
            record = json.loads(lines[0])

            expected_keys = {
                "engine",
                "game_id",
                "file",
                "source_key",
                "original",
                "translated",
                "status",
                "notes",
                "hash",
                "created_at",
                "updated_at",
            }
            self.assertEqual(set(record.keys()), expected_keys)
            self.assertEqual(record["engine"], "renpy")
            self.assertEqual(record["notes"], "nota teste")
            self.assertEqual(record["status"], "tm_hit")
        finally:
            db.close()

    def test_export_jsonl_empty_game(self):
        db = tm_db.TranslationDB(self.tmp_db())
        try:
            out = self.tmp_jsonl("empty_export.jsonl")
            count = db.export_jsonl("NO_SUCH_GAME", str(out))
            self.assertEqual(count, 0)
            self.assertFalse(out.exists())
        finally:
            db.close()


# ======================================================================
# Testes de import_from_tmstore
# ======================================================================


class ImportFromTMStoreTests(TranslationDBTestCase):
    def test_import_populates_db(self):
        records = [
            {"source": "Bonjour", "target": "Hello", "lang": "fr-en",
             "file": "dialogue.txt", "item_id": "D001", "ts": 1.0},
            {"source": "Merci", "target": "Thanks", "lang": "fr-en",
             "file": "dialogue.txt", "item_id": "D002", "ts": 2.0},
        ]
        # JSONL fica em subdir separada para o lazy seed nao pegar.
        jsonl_dir = TMP / "jsonl_store"
        jsonl_dir.mkdir(parents=True)
        jsonl = jsonl_dir / "tm_import.jsonl"
        _make_jsonl(jsonl, records)

        db = tm_db.TranslationDB(self.tmp_db())
        try:
            count = db.import_from_tmstore(
                str(jsonl), game_id="IMPORTED", engine="rpgmaker"
            )
            self.assertEqual(count, 2)

            all_entries = db.lookup_by_game("IMPORTED")
            self.assertEqual(len(all_entries), 2)

            h = tm_db.hash_text("Bonjour")
            results = db.lookup(h)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["translated"], "Hello")
            self.assertEqual(results[0]["status"], "tm_hit")
            self.assertEqual(results[0]["engine"], "rpgmaker")
            self.assertEqual(results[0]["source_key"], "D001")
        finally:
            db.close()

    def test_import_nonexistent_file(self):
        db = tm_db.TranslationDB(self.tmp_db())
        try:
            count = db.import_from_tmstore(
                str(TMP / "nope.jsonl"), game_id="X", engine="y"
            )
            self.assertEqual(count, 0)
        finally:
            db.close()

    def test_import_skips_corrupted_lines(self):
        raw = '{"source": "A", "target": "Alpha"}\nCORRUPTED LINE\n'
        jsonl_dir = TMP / "jsonl_store_bad"
        jsonl_dir.mkdir(parents=True)
        jsonl = jsonl_dir / "bad.tm.jsonl"
        jsonl.write_text(raw, encoding="utf-8")

        db = tm_db.TranslationDB(self.tmp_db())
        try:
            count = db.import_from_tmstore(
                str(jsonl), game_id="G", engine="e"
            )
            self.assertEqual(count, 1)
        finally:
            db.close()


# ======================================================================
# Testes de pending_entries e needs_translation
# ======================================================================


class PendingAndNeedsTranslationTests(TranslationDBTestCase):
    def setUp(self):
        super().setUp()
        self.db = tm_db.TranslationDB(self.tmp_db())
        self.db.upsert(
            _make_entry(source_key="k1", translated=None, status="pending")
        )
        self.db.upsert(
            _make_entry(source_key="k2", translated="OK", status="tm_hit")
        )
        self.db.upsert(
            _make_entry(source_key="k3", translated=None, status="needs_review")
        )
        self.db.upsert(
            _make_entry(source_key="k4", translated=None, status="failed")
        )
        self.db.upsert(
            _make_entry(
                source_key="k5", translated="Done", status="llm"
            )
        )

    def tearDown(self):
        self.db.close()
        super().tearDown()

    def test_pending_entries_only_pending(self):
        pending = self.db.pending_entries("GAME01")
        statuses = [e["status"] for e in pending]
        self.assertEqual(statuses, ["pending"])

    def test_needs_translation_covers_three_statuses(self):
        needs = self.db.needs_translation("GAME01")
        statuses = sorted(e["status"] for e in needs)
        self.assertEqual(
            statuses, ["failed", "needs_review", "pending"]
        )

    def test_needs_translation_empty_for_game_without_entries(self):
        needs = self.db.needs_translation("NO_SUCH_GAME")
        self.assertEqual(needs, [])


# ======================================================================
# Testes de hash_text
# ======================================================================


class HashTextTests(unittest.TestCase):
    def test_hash_deterministic(self):
        h1 = tm_db.hash_text("hello")
        h2 = tm_db.hash_text("hello")
        self.assertEqual(h1, h2)

    def test_hash_differs_for_different_inputs(self):
        h1 = tm_db.hash_text("hello")
        h2 = tm_db.hash_text("world")
        self.assertNotEqual(h1, h2)

    def test_hash_is_sha256_hex(self):
        h = tm_db.hash_text("test")
        self.assertEqual(len(h), 64)
        # SHA-256 de "test" em hex
        self.assertEqual(
            h,
            "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        )


# ======================================================================
# Testes de context manager
# ======================================================================


class ContextManagerTests(TranslationDBTestCase):
    def test_context_manager_closes(self):
        db_path = self.tmp_db()
        with tm_db.TranslationDB(db_path) as db:
            db.upsert(_make_entry())
        # Apos __exit__, conn deve ser None.
        self.assertIsNone(db._conn)


# ======================================================================
# Testes de lazy seed
# ======================================================================


class LazySeedTests(TranslationDBTestCase):
    def test_lazy_seed_imports_jsonl_in_same_dir(self):
        """DB em reports/tm/ com JSONLs existentes -> importa automaticamente."""
        base = TMP / "reports" / "tm"
        base.mkdir(parents=True)

        records = [
            {"source": "テスト", "target": "Test", "lang": "ja-en",
             "file": "script.txt", "item_id": "T001", "ts": 1.0},
        ]
        _make_jsonl(base / "mygame.jsonl", records)
        _make_jsonl(base / "global.jsonl", records)

        db = tm_db.TranslationDB(str(base / "tm.sqlite"))
        try:
            mygame = db.lookup_by_game("mygame")
            self.assertEqual(len(mygame), 1)
            self.assertEqual(mygame[0]["original"], "テスト")

            global_entries = db.lookup_by_game("global")
            self.assertEqual(len(global_entries), 1)
        finally:
            db.close()


# ======================================================================
# Testes de lookup_by_game com ordem
# ======================================================================


class LookupByGameTests(TranslationDBTestCase):
    def test_lookup_by_game_returns_ordered_by_id(self):
        db = tm_db.TranslationDB(self.tmp_db())
        try:
            db.upsert(_make_entry(source_key="k2", original="B"))
            db.upsert(_make_entry(source_key="k1", original="A"))

            entries = db.lookup_by_game("GAME01")
            originals = [e["original"] for e in entries]
            self.assertEqual(originals, ["B", "A"])
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
