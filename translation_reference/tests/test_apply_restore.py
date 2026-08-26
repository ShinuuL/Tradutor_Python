# -*- coding: utf-8 -*-
"""Testes offline dos subcomandos protegidos apply/restore (unittest, stdlib).

Cobertura exigida pela Fase 2 + endurecimento autorizado:
- apply sem --i-approve-write-game-files => exit 3 e nenhuma escrita;
- apply com a flag => .bak byte-identico ao original + applied_manifest.json
  valido gravado ANTES da primeira escrita no jogo;
- restore devolve o sha256 original e preserva o .bak;
- reaplicacao IDEMPOTENTE com .bak orfao e jogo intacto: reaplica mantendo
  o .bak original byte-identico, written > 0, manifesto sem duplicar entrada;
- PROTECAO: jogo modificado externamente desde o backup => aquele arquivo
  e abortado com nota clara, sem escrita nele, .bak preservado;
- exit code 4 quando written == 0 e houve abortos por protecao;
- .bak orfao sem manifesto: registro recriado com o hash do proprio .bak.
"""
import hashlib
import json
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

WORK = HERE / "tmp_apply"


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


class FakeEngine:
    def __init__(self, mapping):
        self.mapping = dict(mapping)
        self.calls = []

    def translate_batch(self, texts):
        self.calls.append(list(texts))
        return [self.mapping[t] for t in texts]


def make_row(item_id, rel_file, line, text, encoding="utf-8-sig", source_key=""):
    ext = "." + rel_file.rsplit(".", 1)[-1].lower()
    return {
        "item_id": item_id,
        "batch": "B0001",
        "root": str(WORK / "game"),
        "file": rel_file,
        "line": line,
        "extension": ext,
        "encoding": encoding,
        "reason": "kana",
        "category": "generic_text",
        "priority": 50,
        "source_key": source_key,
        "occurrences": 1,
        "text": text,
    }


class ApplyRestoreTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(WORK, ignore_errors=True)
        (WORK / "game" / "txt").mkdir(parents=True)
        (WORK / "game" / "data").mkdir(parents=True)
        self.story_original = "# Titulo\nこれはテストです。\nFim.\n".encode("utf-8")
        (WORK / "game" / "txt" / "story.txt").write_bytes(self.story_original)
        self.items_original = (
            '[{"id":1,"name":"やくそう"}]\n'.encode("utf-8")
        )
        (WORK / "game" / "data" / "Items.json").write_bytes(self.items_original)

        rows = [
            make_row("T000001", "txt/story.txt", 2, "これはテストです。"),
            make_row("T000002", "data/Items.json", 0, "やくそう", source_key="$[0].name"),
        ]
        scan = WORK / "scan.jsonl"
        with open(scan, "w", encoding="utf-8", newline="\n") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")

        engine = FakeEngine(
            {"これはテストです。": "This is a test.", "やくそう": "Herb"}
        )
        self.out_dir = WORK / "translated"
        tcli.run_translate(
            scan_path=scan,
            out_dir=self.out_dir,
            tm_path=None,
            engine=engine,
            dry_run=False,
        )
        self.assertTrue((self.out_dir / "txt" / "story.txt").exists())
        self.assertTrue((self.out_dir / "data" / "Items.json").exists())

        self.game_root = WORK / "game"
        self.manifest_path = self.out_dir / "applied_manifest.json"
        self.pristine_snapshot = snapshot(self.game_root)

    def tearDown(self):
        shutil.rmtree(WORK, ignore_errors=True)

    # ------------------------------------------------------------------

    def test_apply_without_flag_writes_nothing(self):
        before_out = snapshot(self.out_dir)
        code = tcli.main(
            [
                "apply",
                "--translated-dir",
                str(self.out_dir),
                "--game-root",
                str(self.game_root),
            ]
        )
        self.assertEqual(code, 3)
        self.assertEqual(snapshot(self.game_root), self.pristine_snapshot)
        self.assertEqual(snapshot(self.out_dir), before_out)
        self.assertFalse(self.manifest_path.exists())

    def test_apply_creates_identical_bak_and_valid_manifest_before_write(self):
        buffer = StringIO()
        with redirect_stdout(buffer):
            code = tcli.main(
                [
                    "apply",
                    "--translated-dir",
                    str(self.out_dir),
                    "--game-root",
                    str(self.game_root),
                    "--i-approve-write-game-files",
                ]
            )
        self.assertEqual(code, 0)

        bak_story = self.game_root / "txt" / "story.txt.bak"
        bak_items = self.game_root / "data" / "Items.json.bak"
        self.assertTrue(bak_story.is_file())
        self.assertTrue(bak_items.is_file())
        self.assertEqual(bak_story.read_bytes(), self.story_original)
        self.assertEqual(bak_items.read_bytes(), self.items_original)

        # originais agora contem o conteudo traduzido
        self.assertEqual(
            (self.game_root / "txt" / "story.txt").read_bytes(),
            (self.out_dir / "txt" / "story.txt").read_bytes(),
        )

        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self.assertIn("created", manifest)
        entries = {e["file"]: e for e in manifest["entries"]}
        self.assertEqual(sorted(entries), ["data/Items.json", "txt/story.txt"])
        for rel, entry in entries.items():
            self.assertTrue(entry["bak"].endswith(".bak"))
            self.assertIn("ts", entry)
            original_pristine = {
                "txt/story.txt": self.story_original,
                "data/Items.json": self.items_original,
            }[rel]
            self.assertEqual(entry["sha256_before"], hashlib.sha256(original_pristine).hexdigest())
            self.assertEqual(entry["bak"], str(self.game_root.joinpath(*rel.split("/"))) + ".bak")

    def test_restore_returns_original_sha256_and_keeps_bak(self):
        tcli.main(
            [
                "apply",
                "--translated-dir",
                str(self.out_dir),
                "--game-root",
                str(self.game_root),
                "--i-approve-write-game-files",
            ]
        )
        manifest_before = json.loads(self.manifest_path.read_text(encoding="utf-8"))

        buffer = StringIO()
        with redirect_stdout(buffer):
            code = tcli.main(["restore", "--manifest", str(self.manifest_path)])
        self.assertEqual(code, 0)

        self.assertEqual((self.game_root / "txt" / "story.txt").read_bytes(), self.story_original)
        self.assertEqual((self.game_root / "data" / "Items.json").read_bytes(), self.items_original)

        manifest_after = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        restored = {r["file"]: r for r in manifest_after["restored"]}
        self.assertEqual(sorted(restored), ["data/Items.json", "txt/story.txt"])
        for rel, record in restored.items():
            self.assertTrue(record["ok"])
        self.assertEqual(manifest_after["entries"], manifest_before["entries"])
        self.assertEqual(manifest_after["created"], manifest_before["created"])

        # .bak preservado apos o restore
        self.assertTrue((self.game_root / "txt" / "story.txt.bak").is_file())
        self.assertTrue((self.game_root / "data" / "Items.json.bak").is_file())

    def test_second_apply_is_idempotent_and_keeps_original_bak(self):
        """Cenario obrigatorio: .bak orfao + jogo intacto => reaplica.

        Fluxo: apply cria os .bak; restore devolve o jogo ao estado original
        (.bak permanecem como orfaos); novo apply com hash atual igual ao
        sha256_before registrado REAPLICA mantendo cada .bak byte-identico.
        """
        tcli.main(
            [
                "apply",
                "--translated-dir",
                str(self.out_dir),
                "--game-root",
                str(self.game_root),
                "--i-approve-write-game-files",
            ]
        )
        tcli.main(["restore", "--manifest", str(self.manifest_path)])
        bak_story = self.game_root / "txt" / "story.txt.bak"
        bak_items = self.game_root / "data" / "Items.json.bak"
        bak_story_bytes = bak_story.read_bytes()
        bak_items_bytes = bak_items.read_bytes()
        manifest_before = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        translated_story = (self.out_dir / "txt" / "story.txt").read_bytes()

        buffer = StringIO()
        with redirect_stdout(buffer):
            code = tcli.main(
                [
                    "apply",
                    "--translated-dir",
                    str(self.out_dir),
                    "--game-root",
                    str(self.game_root),
                    "--i-approve-write-game-files",
                ]
            )
        output = buffer.getvalue()

        self.assertEqual(code, 0)
        # Reaplicou: written > 0 e nota explicita de backup reaproveitado.
        self.assertIn("Aplicados: 2", output)
        self.assertIn("reaplicado", output)
        self.assertIn("backup original mantido", output)
        # Jogo continua com a versao traduzida aplicada.
        self.assertEqual(
            (self.game_root / "txt" / "story.txt").read_bytes(), translated_story
        )
        # .bak originais permanecem byte-identicos (nao regenerados).
        self.assertEqual(bak_story.read_bytes(), bak_story_bytes)
        self.assertEqual(bak_items.read_bytes(), bak_items_bytes)
        # Manifesto nao duplica entradas nem altera o registro original.
        manifest_after = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(len(manifest_after["entries"]), len(manifest_before["entries"]))
        self.assertEqual(manifest_after["entries"], manifest_before["entries"])

    def test_reapply_aborts_only_files_changed_since_backup(self):
        """Protecao: jogo modificado externamente => aborta com nota clara."""
        tcli.main(
            [
                "apply",
                "--translated-dir",
                str(self.out_dir),
                "--game-root",
                str(self.game_root),
                "--i-approve-write-game-files",
            ]
        )
        tcli.main(["restore", "--manifest", str(self.manifest_path)])
        story_path = self.game_root / "txt" / "story.txt"
        external_edit = self.story_original + b"EDIT EXTERNA\n"
        story_path.write_bytes(external_edit)

        buffer = StringIO()
        with redirect_stdout(buffer):
            code = tcli.main(
                [
                    "apply",
                    "--translated-dir",
                    str(self.out_dir),
                    "--game-root",
                    str(self.game_root),
                    "--i-approve-write-game-files",
                ]
            )
        output = buffer.getvalue()

        # Items.json segue no estado protegido => foi reaplicado;
        # story.txt mudou externamente => abortado sem escrita nele.
        self.assertEqual(code, 0)
        self.assertIn("Aplicados: 1", output)
        self.assertIn("abortado", output.lower())
        self.assertIn("jogo mudou desde o backup", output)
        self.assertIn("txt/story.txt", output)
        self.assertEqual(story_path.read_bytes(), external_edit)
        # .bak do arquivo protegido permanece intacto.
        bak_story = self.game_root / "txt" / "story.txt.bak"
        self.assertEqual(bak_story.read_bytes(), self.story_original)

    def test_apply_without_restore_protects_already_translated_state(self):
        """Regra literal: hash atual != sha256_before => aborta com nota."""
        tcli.main(
            [
                "apply",
                "--translated-dir",
                str(self.out_dir),
                "--game-root",
                str(self.game_root),
                "--i-approve-write-game-files",
            ]
        )
        bak_before = {
            p.read_bytes()
            for p in self.game_root.rglob("*.bak")
        }

        buffer = StringIO()
        with redirect_stdout(buffer):
            code = tcli.main(
                [
                    "apply",
                    "--translated-dir",
                    str(self.out_dir),
                    "--game-root",
                    str(self.game_root),
                    "--i-approve-write-game-files",
                ]
            )
        output = buffer.getvalue()

        # Jogo traduzido difere do estado protegido (original): nada escrito.
        self.assertEqual(code, 4)
        self.assertIn("Aplicados: 0", output)
        self.assertIn("protegidos (jogo mudou): 2", output)
        self.assertIn("jogo mudou desde o backup", output)
        for path in self.game_root.rglob("*.bak"):
            self.assertIn(path.read_bytes(), bak_before)

    def test_exit_code_4_when_nothing_written_due_to_protection(self):
        """Exit 4: written == 0 e todos os arquivos abortados por protecao."""
        tcli.main(
            [
                "apply",
                "--translated-dir",
                str(self.out_dir),
                "--game-root",
                str(self.game_root),
                "--i-approve-write-game-files",
            ]
        )
        tcli.main(["restore", "--manifest", str(self.manifest_path)])
        # Modificacao externa em TODOS os arquivos protegidos.
        (self.game_root / "txt" / "story.txt").write_bytes(
            self.story_original + b"X"
        )
        (self.game_root / "data" / "Items.json").write_bytes(
            self.items_original + b" "
        )

        buffer = StringIO()
        with redirect_stdout(buffer):
            code = tcli.main(
                [
                    "apply",
                    "--translated-dir",
                    str(self.out_dir),
                    "--game-root",
                    str(self.game_root),
                    "--i-approve-write-game-files",
                ]
            )
        output = buffer.getvalue()

        self.assertEqual(code, 4)
        self.assertIn("Aplicados: 0", output)
        self.assertIn("protegidos (jogo mudou): 2", output)
        # Nada foi escrito: jogo continua nas versoes editadas externamente.
        self.assertEqual(
            (self.game_root / "txt" / "story.txt").read_bytes(),
            self.story_original + b"X",
        )
        self.assertEqual(
            (self.game_root / "data" / "Items.json").read_bytes(),
            self.items_original + b" ",
        )

    def test_orphan_bak_without_manifest_registers_bak_hash(self):
        """.bak orfao e manifesto perdido: hash do proprio .bak vira origem."""
        tcli.main(
            [
                "apply",
                "--translated-dir",
                str(self.out_dir),
                "--game-root",
                str(self.game_root),
                "--i-approve-write-game-files",
            ]
        )
        tcli.main(["restore", "--manifest", str(self.manifest_path)])
        self.manifest_path.unlink()  # manifesto perdido; .baks continuam

        buffer = StringIO()
        with redirect_stdout(buffer):
            code = tcli.main(
                [
                    "apply",
                    "--translated-dir",
                    str(self.out_dir),
                    "--game-root",
                    str(self.game_root),
                    "--i-approve-write-game-files",
                ]
            )
        output = buffer.getvalue()

        self.assertEqual(code, 0)
        self.assertIn("Aplicados: 2", output)
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        entries = {e["file"]: e for e in manifest["entries"]}
        self.assertEqual(sorted(entries), ["data/Items.json", "txt/story.txt"])
        for rel, entry in entries.items():
            original_pristine = {
                "txt/story.txt": self.story_original,
                "data/Items.json": self.items_original,
            }[rel]
            self.assertEqual(
                entry["sha256_before"],
                hashlib.sha256(original_pristine).hexdigest(),
            )
        # Jogo terminou traduzido e .baks preservados.
        self.assertEqual(
            (self.game_root / "txt" / "story.txt").read_bytes(),
            (self.out_dir / "txt" / "story.txt").read_bytes(),
        )
        self.assertTrue((self.game_root / "txt" / "story.txt.bak").is_file())


if __name__ == "__main__":
    unittest.main()
