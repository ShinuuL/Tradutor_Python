# -*- coding: utf-8 -*-
"""Testes offline dos appliers de traducao (unittest, somente stdlib).

Cobertura exigida pelo design F1/F4:
- hash dos originais inalterado apos aplicar;
- copias criadas em tests/tmp_out (limpo no tearDown);
- linhas alvo traduzidas e linhas nao-alvo identicas;
- JSON reparsavel com apenas as folhas alvo trocadas (ordem preservada);
- roundtrip cp932 correto byte-a-byte;
- caso needs_review quando validate_pair falha.
"""
import hashlib
import json
import re
import shutil
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIB_DIR = HERE.parent / "scripts" / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

import appliers  # noqa: E402
import placeholders  # noqa: E402

FIXTURES = HERE / "fixtures" / "game"
OUT = HERE / "tmp_out"

JP_DEMO = "これは日本語のテキストです。"
HELLO_DEMO = "{player_name}、こんにちは！"
WORLD_RPY = "こんにちは、世界。"
HOW_ARE_YOU_RPY = "元気ですか？"
SLIME_CSV = "1,スライム,いちばんよわいモンスター"
GOBLIN_CSV = "2,ゴブリン,ちょっとだけつよいモンスター"
ALEX_JSON = "アレックス"
HERO_APPRENTICE = "勇者見習い"
ALEX_PROFILE = "王国の片田舎で育った若者。"
BRIAN_JSON = "ブライアン"


def sha256_of(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixtures_snapshot():
    return {
        str(p.relative_to(FIXTURES)).replace("\\", "/"): sha256_of(p)
        for p in sorted(FIXTURES.rglob("*"))
        if p.is_file()
    }


def make_row(
    rel_file,
    line=0,
    text="",
    translated=None,
    encoding="utf-8-sig",
    source_key="",
    item_id="T000001",
):
    """Row no formato do extrator + campo ``translated`` do chamador."""
    ext = "." + rel_file.rsplit(".", 1)[-1].lower()
    return {
        "item_id": item_id,
        "batch": "B0001",
        "root": str(FIXTURES),
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
        "translated": translated,
    }


def split_norm(path, codec):
    text = path.read_bytes().decode(codec)
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


class AppliersCase(unittest.TestCase):
    def setUp(self):
        self.snapshot = fixtures_snapshot()
        shutil.rmtree(OUT, ignore_errors=True)
        OUT.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(OUT, ignore_errors=True)

    def assert_originals_intact(self):
        self.assertEqual(fixtures_snapshot(), self.snapshot)


class LineApplierTests(AppliersCase):
    def test_txt_lines_translated_with_crlf_preserved(self):
        rows = [
            make_row("txt/demo.txt", 2, JP_DEMO, "This is Japanese text.", item_id="T000001"),
            make_row("txt/demo.txt", 4, HELLO_DEMO, "Hello, {player_name}!", item_id="T000002"),
        ]
        results = appliers.apply_to_copy({"txt/demo.txt": rows}, FIXTURES, OUT)

        self.assert_originals_intact()
        self.assertEqual([r["status"] for r in results], ["applied", "applied"])
        expected = (
            b"# Cena de demonstracao\r\n"
            + b"This is Japanese text.\r\n"
            + b"Esta linha permanece em ingles.\r\n"
            + b"Hello, {player_name}!\r\n"
        )
        self.assertEqual((OUT / "txt" / "demo.txt").read_bytes(), expected)

    def test_non_target_lines_stay_byte_identical(self):
        rows = [make_row("txt/demo.txt", 2, JP_DEMO, "This is Japanese text.")]
        appliers.apply_to_copy({"txt/demo.txt": rows}, FIXTURES, OUT)

        orig_lines = split_norm(FIXTURES / "txt" / "demo.txt", "utf-8")
        copy_lines = split_norm(OUT / "txt" / "demo.txt", "utf-8")
        self.assertEqual(len(orig_lines), len(copy_lines))
        for idx, (before, after) in enumerate(zip(orig_lines, copy_lines), 1):
            if idx != 2:
                self.assertEqual(before, after, "linha %d foi alterada" % idx)
        self.assertNotEqual(orig_lines[1], copy_lines[1])

    def test_cp932_roundtrip_byte_exact(self):
        rows = [
            make_row("txt/demo_cp932.txt", 1, "やあ、世界。", "Ola, mundo.", encoding="cp932"),
            make_row("txt/demo_cp932.txt", 3, "おやすみなさい。", "Boa noite.", encoding="cp932", item_id="T000002"),
        ]
        results = appliers.apply_to_copy({"txt/demo_cp932.txt": rows}, FIXTURES, OUT)

        self.assert_originals_intact()
        self.assertTrue(all(r["status"] == "applied" for r in results))
        copy = (OUT / "txt" / "demo_cp932.txt").read_bytes()
        source_bytes = (FIXTURES / "txt" / "demo_cp932.txt").read_bytes()
        terminators = re.findall(rb"\r\n|\r|\n", source_bytes)
        self.assertEqual(len(terminators), 3)
        expected_lines = [
            "Ola, mundo.".encode("cp932"),
            "剣を手に入れた。".encode("cp932"),
            "Boa noite.".encode("cp932"),
        ]
        expected = b"".join(
            line + terminator for line, terminator in zip(expected_lines, terminators)
        )
        self.assertEqual(copy, expected)
        self.assertEqual(copy.decode("cp932").splitlines()[1], "剣を手に入れた。")

    def test_rpy_literal_replaced_inside_code_line(self):
        rows = [
            make_row("txt/script.rpy", 3, WORLD_RPY, "Hello, world."),
            make_row("txt/script.rpy", 4, HOW_ARE_YOU_RPY, "How are you?", item_id="T000002"),
        ]
        results = appliers.apply_to_copy({"txt/script.rpy": rows}, FIXTURES, OUT)

        self.assertTrue(all(r["status"] == "applied" for r in results))
        lines = (OUT / "txt" / "script.rpy").read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0], 'define h = Character("ヒロイン")')
        self.assertEqual(lines[1], "label start:")
        self.assertEqual(lines[2], '    h "Hello, world."')
        self.assertEqual(lines[3], '    h "How are you?"')
        self.assertEqual(lines[4], "    return")

    def test_ks_lines_keep_kirikiri_syntax_and_tags(self):
        rows = [
            make_row("txt/dialogue.ks", 1, "*start|冒険のはじまり", "*start|The adventure begins"),
            make_row("txt/dialogue.ks", 2, "ようこそ、旅の人。[p]", "Welcome, traveler.[p]", item_id="T000002"),
            make_row("txt/dialogue.ks", 3, "ごきげんよう[l][r]", "Greetings.[l][r]", item_id="T000003"),
        ]
        results = appliers.apply_to_copy({"txt/dialogue.ks": rows}, FIXTURES, OUT)

        self.assertTrue(all(r["status"] == "applied" for r in results))
        lines = (OUT / "txt" / "dialogue.ks").read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0], "*start|The adventure begins")
        self.assertEqual(lines[1], "Welcome, traveler.[p]")
        self.assertEqual(lines[2], "Greetings.[l][r]")

    def test_csv_bom_preserved_and_rows_replaced(self):
        rows = [
            make_row("txt/data.csv", 2, SLIME_CSV, "1,Slime,Weakest monster"),
            make_row("txt/data.csv", 3, GOBLIN_CSV, "2,Goblin,A bit stronger", item_id="T000002"),
        ]
        results = appliers.apply_to_copy({"txt/data.csv": rows}, FIXTURES, OUT)

        self.assert_originals_intact()
        self.assertTrue(all(r["status"] == "applied" for r in results))
        raw = (OUT / "txt" / "data.csv").read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"), "BOM deve ser preservado")
        lines = raw.decode("utf-8-sig").splitlines()
        self.assertEqual(lines[0], "id,nome,descricao")
        self.assertEqual(lines[1], "1,Slime,Weakest monster")
        self.assertEqual(lines[2], "2,Goblin,A bit stronger")

    def test_snippet_not_found_is_needs_review(self):
        rows = [make_row("txt/demo.txt", 2, JP_DEMO[:5] + "trecho diferente", "Anything")]
        results = appliers.apply_to_copy({"txt/demo.txt": rows}, FIXTURES, OUT)
        self.assertEqual(results[0]["status"], "needs_review")
        self.assertFalse((OUT / "txt" / "demo.txt").exists())


class JsonApplierTests(AppliersCase):
    @staticmethod
    def actor_rows():
        return [
            make_row("data/Actors.json", 0, ALEX_JSON, "Alex", source_key="$[1].name"),
            make_row("data/Actors.json", 0, HERO_APPRENTICE, "Hero Apprentice", source_key="$[1].nickname", item_id="T000002"),
            make_row("data/Actors.json", 0, ALEX_PROFILE, "A young man raised in the countryside.", source_key="$[1].profile[0]", item_id="T000003"),
            make_row("data/Actors.json", 0, BRIAN_JSON, "Brian", source_key="$[2].name", item_id="T000004"),
        ]

    def test_json_only_target_leaves_changed(self):
        results = appliers.apply_to_copy({"data/Actors.json": self.actor_rows()}, FIXTURES, OUT)

        self.assert_originals_intact()
        self.assertTrue(all(r["status"] == "applied" for r in results))

        orig_raw = (FIXTURES / "data" / "Actors.json").read_bytes()
        new_raw = (OUT / "data" / "Actors.json").read_bytes()
        self.assertTrue(new_raw.startswith(b"\xef\xbb\xbf"), "BOM do JSON deve ser preservado")
        self.assertNotIn(b"\\u", new_raw, "dump deve usar ensure_ascii=False")

        orig = json.loads(orig_raw.decode("utf-8-sig"))
        new = json.loads(new_raw.decode("utf-8-sig"))
        self.assertIsNone(new[0])
        self.assertEqual(new[1]["name"], "Alex")
        self.assertEqual(new[1]["nickname"], "Hero Apprentice")
        self.assertEqual(new[1]["profile"][0], "A young man raised in the countryside.")
        self.assertEqual(new[2]["name"], "Brian")
        self.assertEqual(new[1]["id"], orig[1]["id"])
        self.assertEqual(new[1]["note"], orig[1]["note"])
        self.assertEqual(new[2]["profile"], orig[2]["profile"])
        self.assertEqual(list(orig[1].keys()), list(new[1].keys()), "ordem das chaves mudou")

    def test_json_missing_path_is_failed(self):
        row = make_row("data/Actors.json", 0, ALEX_JSON, "Alex", source_key="$[99].name")
        results = appliers.apply_to_copy({"data/Actors.json": [row]}, FIXTURES, OUT)

        self.assertEqual(results[0]["status"], "failed")
        self.assertFalse((OUT / "data" / "Actors.json").exists())
        self.assert_originals_intact()

    def test_json_content_mismatch_is_needs_review(self):
        row = make_row("data/Actors.json", 0, "texto que nao existe no arquivo", "Whatever", source_key="$[1].name")
        results = appliers.apply_to_copy({"data/Actors.json": [row]}, FIXTURES, OUT)
        self.assertEqual(results[0]["status"], "needs_review")
        self.assertFalse((OUT / "data" / "Actors.json").exists())


class NeedsReviewAndFailureTests(AppliersCase):
    def test_needs_review_when_placeholder_dropped(self):
        row = make_row("txt/demo.txt", 4, HELLO_DEMO, "Hello!")
        results = appliers.apply_to_copy({"txt/demo.txt": [row]}, FIXTURES, OUT)

        self.assertEqual(results[0]["status"], "needs_review")
        self.assertTrue(any("chaves" in note or "{" in note for note in results[0]["notes"]))
        self.assertFalse((OUT / "txt" / "demo.txt").exists())
        self.assert_originals_intact()

    def test_needs_review_keeps_bad_line_when_sibling_applies(self):
        rows = [
            make_row("txt/demo.txt", 2, JP_DEMO, "This is Japanese text."),
            make_row("txt/demo.txt", 4, HELLO_DEMO, "Hello!", item_id="T000002"),
        ]
        results = appliers.apply_to_copy({"txt/demo.txt": rows}, FIXTURES, OUT)

        self.assertEqual([r["status"] for r in results], ["applied", "needs_review"])
        lines = (OUT / "txt" / "demo.txt").read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[1], "This is Japanese text.")
        self.assertEqual(lines[3], HELLO_DEMO, "linha reprovada deveria ficar intocada")

    def test_missing_translated_field_is_needs_review(self):
        row = make_row("txt/demo.txt", 2, JP_DEMO, None)
        results = appliers.apply_to_copy({"txt/demo.txt": [row]}, FIXTURES, OUT)
        self.assertEqual(results[0]["status"], "needs_review")
        self.assertTrue(any("translated" in note for note in results[0]["notes"]))
        self.assertFalse((OUT / "txt" / "demo.txt").exists())

    def test_unencodable_translation_is_needs_review(self):
        row = make_row("txt/demo_cp932.txt", 1, "やあ、世界。", "emoji 🌚 nao existe em cp932", encoding="cp932")
        results = appliers.apply_to_copy({"txt/demo_cp932.txt": [row]}, FIXTURES, OUT)
        self.assertEqual(results[0]["status"], "needs_review")
        self.assertFalse((OUT / "txt" / "demo_cp932.txt").exists())

    def test_missing_source_file_is_failed(self):
        row = make_row("txt/inexistente.txt", 1, "algo", "something")
        results = appliers.apply_to_copy({"txt/inexistente.txt": [row]}, FIXTURES, OUT)
        self.assertEqual(results[0]["status"], "failed")
        self.assertFalse((OUT / "txt" / "inexistente.txt").exists())

    def test_line_out_of_range_is_failed(self):
        row = make_row("txt/demo.txt", 99, JP_DEMO, "This is Japanese text.")
        results = appliers.apply_to_copy({"txt/demo.txt": [row]}, FIXTURES, OUT)
        self.assertEqual(results[0]["status"], "failed")
        self.assertFalse((OUT / "txt" / "demo.txt").exists())

    def test_duplicate_target_line_second_entry_is_needs_review(self):
        rows = [
            make_row("txt/demo.txt", 2, JP_DEMO, "First translation."),
            make_row("txt/demo.txt", 2, JP_DEMO, "Second translation.", item_id="T000002"),
        ]
        results = appliers.apply_to_copy({"txt/demo.txt": rows}, FIXTURES, OUT)
        self.assertEqual([r["status"] for r in results], ["applied", "needs_review"])

    def test_path_escape_is_blocked_without_writes(self):
        row = make_row("../fuga.txt", 1, "jp", "en")
        results = appliers.apply_to_copy({"../fuga.txt": [row]}, FIXTURES, OUT)
        self.assertEqual(results[0]["status"], "failed")
        self.assertFalse((HERE / "fuga.txt").exists(), "nenhum arquivo fora de tmp_out pode nascer")
        self.assert_originals_intact()

    def test_same_root_for_src_and_out_raises(self):
        with self.assertRaises(ValueError):
            appliers.apply_to_copy({}, FIXTURES, FIXTURES)


class FullPipelineTests(AppliersCase):
    def test_all_fixtures_in_one_call_pass_verify_rules(self):
        rows_by_file = {
            "txt/demo.txt": [
                make_row("txt/demo.txt", 2, JP_DEMO, "This is Japanese text.", item_id="T000001"),
                make_row("txt/demo.txt", 4, HELLO_DEMO, "Hello, {player_name}!", item_id="T000002"),
            ],
            "txt/demo_cp932.txt": [
                make_row("txt/demo_cp932.txt", 1, "やあ、世界。", "Ola, mundo.", encoding="cp932", item_id="T000003"),
                make_row("txt/demo_cp932.txt", 3, "おやすみなさい。", "Boa noite.", encoding="cp932", item_id="T000004"),
            ],
            "txt/script.rpy": [
                make_row("txt/script.rpy", 3, WORLD_RPY, "Hello, world.", item_id="T000005"),
                make_row("txt/script.rpy", 4, HOW_ARE_YOU_RPY, "How are you?", item_id="T000006"),
            ],
            "txt/dialogue.ks": [
                make_row("txt/dialogue.ks", 1, "*start|冒険のはじまり", "*start|The adventure begins", item_id="T000007"),
                make_row("txt/dialogue.ks", 2, "ようこそ、旅の人。[p]", "Welcome, traveler.[p]", item_id="T000008"),
            ],
            "txt/data.csv": [
                make_row("txt/data.csv", 2, SLIME_CSV, "1,Slime,Weakest monster", item_id="T000009"),
                make_row("txt/data.csv", 3, GOBLIN_CSV, "2,Goblin,A bit stronger", item_id="T000010"),
            ],
            "data/Actors.json": JsonApplierTests.actor_rows(),
        }

        results = appliers.apply_to_copy(rows_by_file, FIXTURES, OUT)

        self.assert_originals_intact()
        self.assertEqual(len(results), 14)
        bad = [r for r in results if r["status"] != "applied"]
        self.assertEqual(bad, [])

        codecs_map = {
            "txt/demo_cp932.txt": "cp932",
        }
        for rel in (
            "txt/demo.txt",
            "txt/demo_cp932.txt",
            "txt/script.rpy",
            "txt/dialogue.ks",
            "txt/data.csv",
        ):
            codec = codecs_map.get(rel, "utf-8-sig")
            orig_lines = split_norm(FIXTURES / rel, codec)
            copy_lines = split_norm(OUT / rel, codec)
            self.assertEqual(len(orig_lines), len(copy_lines), "contagem de linhas difere em %s" % rel)
            for idx, (before, after) in enumerate(zip(orig_lines, copy_lines), 1):
                if not appliers.JP_RE.search(before):
                    self.assertEqual(before, after, "linha %d de %s mudou sem motivo" % (idx, rel))


class ValidatePairUnitTests(unittest.TestCase):
    def test_matching_tokens_pass(self):
        ok, notes = placeholders.validate_pair("{name}さん、待って[p]\\n", "{name} wait[p]\\n")
        self.assertTrue(ok, notes)

    def test_missing_tag_fails(self):
        ok, notes = placeholders.validate_pair("[l][r]テキスト", "[l]texto")
        self.assertFalse(ok)
        self.assertTrue(any("colchetes" in note for note in notes))

    def test_missing_percent_fails(self):
        ok, notes = placeholders.validate_pair("%d個のアイテム", "items")
        self.assertFalse(ok)
        self.assertTrue(any("printf" in note for note in notes))

    def test_extra_brace_fails(self):
        ok, notes = placeholders.validate_pair("texto simples", "texto com {extra}")
        self.assertFalse(ok)

    def test_empty_translation_fails(self):
        ok, notes = placeholders.validate_pair("テキスト", "   ")
        self.assertFalse(ok)
        self.assertTrue(any("vazia" in note for note in notes))


if __name__ == "__main__":
    unittest.main()
