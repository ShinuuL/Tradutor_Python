# -*- coding: utf-8 -*-
"""Testes offline da normalizacao/dedupe do applied_manifest.json (stdlib).

Cobre a correcao autorizada contra duplicacao de entradas no manifesto:
- apply com --game-root RELATIVO sobre manifesto gerado com caminho
  absoluto REAPROVEITA o .bak e NAO duplica entrada;
- manifesto com duplicatas relativas/absolutas misturadas e regravado
  normalizado/deduplicado, com ``created`` e bloco ``restored`` intactos;
- ``sha256_before`` preservado na dedupe (mantida a entrada mais recente);
- restore le entradas legadas com ``bak`` relativo sem alterar entradas.

Temporarios vivem dentro de tests/ e sao removidos no tearDown.
"""
import hashlib
import json
import os
import shutil
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent / "scripts"
LIB_DIR = SCRIPTS_DIR / "lib"
for extra in (str(SCRIPTS_DIR), str(LIB_DIR)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

import translate_game_text as tcli  # noqa: E402

WORK = HERE / "tmp_manifest_fix"


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


class FakeEngine:
    def __init__(self, mapping):
        self.mapping = dict(mapping)

    def translate_batch(self, texts):
        return [self.mapping[t] for t in texts]


def make_row(item_id, rel_file, line, text, source_key=""):
    ext = "." + rel_file.rsplit(".", 1)[-1].lower()
    return {
        "item_id": item_id,
        "batch": "B0001",
        "root": str(WORK / "game"),
        "file": rel_file,
        "line": line,
        "extension": ext,
        "encoding": "utf-8-sig",
        "reason": "kana",
        "category": "generic_text",
        "priority": 50,
        "source_key": source_key,
        "occurrences": 1,
        "text": text,
    }


class ManifestMigrationTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(WORK, ignore_errors=True)
        (WORK / "game" / "txt").mkdir(parents=True)
        self.story_original = "# Titulo\nこれはテストです。\nFim.\n".encode("utf-8")
        (WORK / "game" / "txt" / "story.txt").write_bytes(self.story_original)

        rows = [make_row("T000001", "txt/story.txt", 2, "これはテストです。")]
        scan = WORK / "scan.jsonl"
        with open(scan, "w", encoding="utf-8", newline="\n") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")

        engine = FakeEngine({"これはテストです。": "This is a test."})
        self.out_dir = WORK / "translated"
        tcli.run_translate(
            scan_path=scan,
            out_dir=self.out_dir,
            tm_path=None,
            engine=engine,
            dry_run=False,
        )
        self.assertTrue((self.out_dir / "txt" / "story.txt").exists())

        self.game_root = WORK / "game"
        self.manifest_path = self.out_dir / "applied_manifest.json"
        self.bak_abs = str((self.game_root / "txt" / "story.txt.bak").resolve())

    def tearDown(self):
        shutil.rmtree(WORK, ignore_errors=True)

    # ------------------------------------------------------------------

    def _apply(self, game_root):
        buffer = StringIO()
        with redirect_stdout(buffer):
            code = tcli.main(
                [
                    "apply",
                    "--translated-dir",
                    str(self.out_dir),
                    "--game-root",
                    str(game_root),
                    "--i-approve-write-game-files",
                ]
            )
        return code, buffer.getvalue()

    def _read_manifest(self):
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def _write_manifest(self, doc):
        self.manifest_path.write_text(
            json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    # ------------------------------------------------------------------

    def test_relative_game_root_reuses_backup_without_duplicates(self):
        """Apply relativo sobre manifesto de apply absoluto: 0 duplicatas."""
        code, _ = self._apply(self.game_root)
        self.assertEqual(code, 0)
        tcli.main(["restore", "--manifest", str(self.manifest_path)])
        before = self._read_manifest()
        self.assertEqual(len(before["entries"]), 1)
        self.assertEqual(before["entries"][0]["bak"], self.bak_abs)

        rel_root = os.path.relpath(str(self.game_root), str(Path.cwd()))
        code, output = self._apply(rel_root)

        self.assertEqual(code, 0)
        self.assertIn("Aplicados: 1", output)  # reaproveitou o backup
        after = self._read_manifest()
        self.assertEqual(len(after["entries"]), 1)  # SEM duplicar entrada
        entry = after["entries"][0]
        self.assertEqual(entry["file"], "txt/story.txt")
        self.assertEqual(
            os.path.normcase(entry["bak"]), os.path.normcase(self.bak_abs)
        )
        self.assertEqual(entry["sha256_before"], sha256_bytes(self.story_original))
        self.assertEqual(after["created"], before["created"])
        # .bak original permanece byte-identico.
        self.assertEqual(
            (self.game_root / "txt" / "story.txt.bak").read_bytes(),
            self.story_original,
        )

    def test_mixed_duplicate_entries_deduped_with_restored_intact(self):
        """Duplicatas relativas+absolutas: regrava dedupado, restored intacto."""
        code, _ = self._apply(self.game_root)
        self.assertEqual(code, 0)
        tcli.main(["restore", "--manifest", str(self.manifest_path)])

        good = self._read_manifest()
        base_entry = good["entries"][0]
        bak_rel = os.path.relpath(base_entry["bak"], str(Path.cwd()))
        restored_block = [
            {
                "file": "txt/story.txt",
                "sha256_after": base_entry["sha256_before"],
                "ok": True,
            }
        ]
        crafted = {
            "created": good["created"],
            # Mesmo .bak fisico em duas formas; a mais recente deve vencer.
            "entries": [
                dict(base_entry, ts=float(base_entry["ts"]) - 10.0),
                {
                    "file": "txt/story.txt",
                    "bak": bak_rel,
                    "sha256_before": base_entry["sha256_before"],
                    "ts": float(base_entry["ts"]) + 10.0,
                },
            ],
            "restored": restored_block,
        }
        self._write_manifest(crafted)

        code, output = self._apply(self.game_root)

        self.assertEqual(code, 0)
        self.assertIn("deduplicado", output)
        after = self._read_manifest()
        self.assertEqual(len(after["entries"]), 1)
        kept = after["entries"][0]
        self.assertEqual(float(kept["ts"]), float(base_entry["ts"]) + 10.0)
        self.assertEqual(kept["bak"], base_entry["bak"])  # normalizado
        # hash preservado na dedupe.
        self.assertEqual(kept["sha256_before"], sha256_bytes(self.story_original))
        # created e bloco restored INTACTOS (auditoria).
        self.assertEqual(after["created"], good["created"])
        self.assertEqual(after["restored"], restored_block)

    def test_normalize_keeps_latest_and_preserves_hashes(self):
        """Unidade do migrador: latest vence, hashes preservados, doc intato."""
        doc = {
            "created": "2026-01-01T00:00:00",
            "entries": [
                {
                    "file": "a.txt",
                    "bak": r"D:\Algum\Lugar\a.txt.bak",
                    "sha256_before": "H1",
                    "ts": 5.0,
                },
                {
                    "file": "a.txt",
                    "bak": r"D:\algum\lugar\A.TXT.BAK",
                    "sha256_before": "H1",
                    "ts": 9.0,
                },
                {
                    "file": "b.txt",
                    "bak": "rel/b.txt.bak",
                    "sha256_before": "H2",
                    "ts": 2.0,
                },
            ],
            "restored": [{"file": "a.txt", "ok": True}],
        }
        entries, changed = tcli.normalize_manifest_entries(doc)

        self.assertTrue(changed)
        self.assertEqual(len(entries), 2)
        by_file = {e["file"]: e for e in entries}
        self.assertEqual(float(by_file["a.txt"]["ts"]), 9.0)
        self.assertEqual(by_file["a.txt"]["sha256_before"], "H1")
        self.assertTrue(os.path.isabs(by_file["a.txt"]["bak"]))
        self.assertEqual(by_file["b.txt"]["sha256_before"], "H2")
        self.assertTrue(os.path.isabs(by_file["b.txt"]["bak"]))
        # Entrada do documento original permanece intocada (sem efeitos colaterais).
        self.assertEqual(doc["restored"], [{"file": "a.txt", "ok": True}])
        self.assertEqual(doc["created"], "2026-01-01T00:00:00")

    def test_restore_reads_legacy_relative_bak_without_rewriting_entries(self):
        """Restore tolera ``bak`` legado relativo e nao altera as entradas."""
        code, _ = self._apply(self.game_root)
        self.assertEqual(code, 0)
        doc = self._read_manifest()
        doc["entries"][0]["bak"] = os.path.relpath(
            doc["entries"][0]["bak"], str(Path.cwd())
        )
        self._write_manifest(doc)

        buffer = StringIO()
        with redirect_stdout(buffer):
            code = tcli.main(["restore", "--manifest", str(self.manifest_path)])

        self.assertEqual(code, 0)
        self.assertEqual(
            (self.game_root / "txt" / "story.txt").read_bytes(), self.story_original
        )
        after = self._read_manifest()
        self.assertTrue(after["restored"][0]["ok"])
        # Entradas NAO sao reescritas pelo restore (historico preservado).
        self.assertFalse(os.path.isabs(after["entries"][0]["bak"]))


if __name__ == "__main__":
    unittest.main()
