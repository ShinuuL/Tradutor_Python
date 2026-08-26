# -*- coding: utf-8 -*-
"""Testes offline do cache global entre jogos (unittest, somente stdlib).

Cobertura exigida pelo passo B1 do plano aprovado:
- hit na global VENCE a TM por-jogo (mesmo texto nas duas, alvo diferente);
- fallback para a por-jogo quando a global erra;
- dupla gravacao: pares novos gravam nas DUAS stores e, na global, o
  campo ``file`` sai prefixado com o id do jogo;
- tolerancia a corrupcao: linha corrompida na global nao derruba a carga;
- ausencia de ``--tm-global`` mantem o comportamento atual (so por-jogo).

Arquivos temporarios ficam em tests/tmp_global_tm (limpo no tearDown).
Nenhum teste grava em fixtures; o jogo de teste e o snapshot de
tests/fixtures/game, apenas lido pelos appliers.
"""
import json
import shutil
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent / "scripts"
LIB_DIR = SCRIPTS_DIR / "lib"
for extra in (str(SCRIPTS_DIR), str(LIB_DIR)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

import translate_game_text as tcli  # noqa: E402
from global_tm import (  # noqa: E402
    GLOBAL_FILE_SEPARATOR,
    ChainedTM,
    with_global_file_prefix,
)
from tm_store import TMStore  # noqa: E402

FIXTURES_GAME = HERE / "fixtures" / "game"
TMP = HERE / "tmp_global_tm"

JP_DEMO = "これは日本語のテキストです。"  # fixtures/game/txt/demo.txt linha 2
JP_GREETING = "{player_name}、こんにちは！"  # fixtures/game/txt/demo.txt linha 4
HELLO_WORLD = "こんにちは、世界。"  # fixtures/game/txt/script.rpy linha 3


def make_pair(source, target, rel_file="txt/demo.txt", item_id="T000099"):
    return {
        "source": source,
        "target": target,
        "lang": "ja-en",
        "file": rel_file,
        "item_id": item_id,
    }


def make_row(item_id, rel_file, line, text):
    ext = "." + rel_file.rsplit(".", 1)[-1].lower()
    return {
        "item_id": item_id,
        "batch": "B0001",
        "root": str(FIXTURES_GAME),
        "file": rel_file,
        "line": line,
        "extension": ext,
        "encoding": "utf-8-sig",
        "reason": "kana",
        "category": "documentation",
        "priority": 35,
        "source_key": "",
        "occurrences": 1,
        "text": text,
    }


def write_scan(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def read_csv_rows(path):
    import csv

    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def read_jsonl(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class FakeEngine:
    """Engine injetavel que registra os lotes recebidos."""

    def __init__(self, mapping=None):
        self.calls = []
        self.mapping = dict(mapping or {})

    def translate_batch(self, texts):
        self.calls.append(list(texts))
        return [self.mapping.get(t, "EN:" + t) for t in texts]

    def translate_batch_resilient(self, texts):
        self.calls.append(list(texts))
        return [self.mapping.get(t, "EN:" + t) for t in texts], []


class GlobalTmCase(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(TMP, ignore_errors=True)
        TMP.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(TMP, ignore_errors=True)

    def tmp_file(self, name):
        return TMP / name

    def out_dir(self):
        # Nome da pasta define o id do jogo na auditoria da global.
        return TMP / "reports" / "translated" / "jogoteste"


class ChainedTmUnitTests(GlobalTmCase):
    def test_global_hit_wins_and_index_reports_the_store(self):
        global_path = self.tmp_file("global.jsonl")
        game_path = self.tmp_file("jogo.jsonl")
        TMStore(global_path).add_many([make_pair(JP_DEMO, "ALVO DA GLOBAL")])
        game_store = TMStore(game_path)
        game_store.add_many(
            [make_pair(JP_DEMO, "alvo do jogo"), make_pair(HELLO_WORLD, "Hello, world.")]
        )
        chain = ChainedTM([TMStore(global_path), game_store])

        self.assertEqual(chain.lookup(JP_DEMO), ("ALVO DA GLOBAL", 0))
        # Global errou: cai para a por-jogo com o indice dela.
        self.assertEqual(chain.lookup(HELLO_WORLD), ("Hello, world.", 1))
        self.assertEqual(chain.lookup("存在しないテキスト"), (None, -1))

    def test_add_many_writes_to_all_stores_append_only(self):
        global_path = self.tmp_file("global.jsonl")
        game_path = self.tmp_file("jogo.jsonl")
        chain = ChainedTM([TMStore(global_path), TMStore(game_path)])
        self.assertFalse(global_path.exists())
        self.assertFalse(game_path.exists())

        chain.add_many([make_pair(JP_DEMO, "First"), make_pair(HELLO_WORLD, "Second")])
        self.assertTrue(global_path.exists(), "global recebe a gravacao")
        self.assertTrue(game_path.exists(), "por-jogo recebe a gravacao")
        global_raw_first = global_path.read_bytes()
        game_raw_first = game_path.read_bytes()
        self.assertEqual(len(read_jsonl(global_path)), 2)
        self.assertEqual(len(read_jsonl(game_path)), 2)

        chain.add_many([make_pair(JP_GREETING, "Third")])
        self.assertTrue(global_path.read_bytes().startswith(global_raw_first),
                        "append-only: bytes antigos da global intactos")
        self.assertTrue(game_path.read_bytes().startswith(game_raw_first),
                        "append-only: bytes antigos da por-jogo intactos")
        self.assertEqual(len(read_jsonl(global_path)), 3)
        self.assertEqual(len(read_jsonl(game_path)), 3)
        self.assertEqual(chain.lookup(JP_GREETING), ("Third", 0))

    def test_empty_add_many_writes_nothing(self):
        global_path = self.tmp_file("global.jsonl")
        chain = ChainedTM([TMStore(global_path)])
        chain.add_many([])
        self.assertFalse(global_path.exists())

    def test_invalid_store_is_rejected(self):
        with self.assertRaises(TypeError):
            ChainedTM(["nao sou uma store"])

    def test_corrupted_lines_do_not_break_chain_load(self):
        global_path = self.tmp_file("global_quebrada.jsonl")
        lines = [
            json.dumps(make_pair(JP_DEMO, "ALVO DA GLOBAL"), ensure_ascii=False),
            "{json truncado de proposito",
            "",
            "nao-e-json",
            json.dumps(make_pair(HELLO_WORLD, "Hello, world."), ensure_ascii=False),
        ]
        global_path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
        chain = ChainedTM([TMStore(global_path)])

        self.assertEqual(chain.lookup(JP_DEMO), ("ALVO DA GLOBAL", 0))
        self.assertEqual(chain.lookup(HELLO_WORLD), ("Hello, world.", 0))
        self.assertEqual(chain.lookup(JP_GREETING), (None, -1))


class GlobalFilePrefixTests(GlobalTmCase):
    def test_prefix_returns_copies_and_keeps_originals_intact(self):
        original = make_pair(JP_GREETING, "EN:greeting", rel_file="txt/demo.txt")
        snapshot = dict(original)

        decorated = with_global_file_prefix([original], "jogoteste")

        self.assertEqual(original, snapshot, "par de entrada nao pode mudar")
        self.assertEqual(len(decorated), 1)
        self.assertIsNot(decorated[0], original)
        self.assertEqual(
            decorated[0]["file"],
            "jogoteste" + GLOBAL_FILE_SEPARATOR + "txt/demo.txt",
        )
        self.assertEqual(decorated[0]["source"], original["source"])
        self.assertEqual(decorated[0]["target"], original["target"])


class RunTranslateGlobalChainTests(GlobalTmCase):
    def run_translate(self, rows, engine, tm_path=None, global_path=None):
        scan = write_scan(self.tmp_file("scan.jsonl"), rows)
        return tcli.run_translate(
            scan_path=scan,
            out_dir=self.out_dir(),
            tm_path=tm_path,
            engine=engine,
            dry_run=False,
            tm_global_path=global_path,
        )

    def test_global_hit_beats_game_tm_and_engine_is_not_called(self):
        global_path = self.tmp_file("global.jsonl")
        game_path = self.tmp_file("jogo.jsonl")
        TMStore(global_path).add_many([make_pair(JP_DEMO, "ALVO DA GLOBAL")])
        TMStore(game_path).add_many([make_pair(JP_DEMO, "alvo do jogo")])
        engine = FakeEngine()

        result = self.run_translate(
            [make_row("T000001", "txt/demo.txt", 2, JP_DEMO)],
            engine,
            tm_path=game_path,
            global_path=global_path,
        )

        self.assertEqual(engine.calls, [], "hit na cadeia nao pode chamar o motor")
        records = read_csv_rows(result["csv_path"])
        self.assertEqual(records[0]["status"], "tm_hit")
        self.assertEqual(records[0]["translated"], "ALVO DA GLOBAL")

    def test_fallback_to_game_tm_when_global_misses(self):
        global_path = self.tmp_file("global.jsonl")
        game_path = self.tmp_file("jogo.jsonl")
        # Global so conhece o hello world; a por-jogo so conhece o demo.
        # Textos sem markup para nao envolver validacao de placeholder.
        TMStore(global_path).add_many(
            [make_pair(HELLO_WORLD, "ALVO DA GLOBAL", rel_file="txt/script.rpy")]
        )
        TMStore(game_path).add_many([make_pair(JP_DEMO, "alvo do jogo")])
        engine = FakeEngine()

        result = self.run_translate(
            [
                make_row("T000001", "txt/script.rpy", 3, HELLO_WORLD),
                make_row("T000002", "txt/demo.txt", 2, JP_DEMO),
            ],
            engine,
            tm_path=game_path,
            global_path=global_path,
        )

        self.assertEqual(engine.calls, [])
        records = {r["item_id"]: r for r in read_csv_rows(result["csv_path"])}
        self.assertEqual(records["T000001"]["translated"], "ALVO DA GLOBAL")
        self.assertEqual(records["T000001"]["status"], "tm_hit")
        self.assertEqual(records["T000002"]["translated"], "alvo do jogo")
        self.assertEqual(records["T000002"]["status"], "tm_hit")

    def test_new_llm_pairs_are_written_to_both_stores_with_prefixed_file(self):
        global_path = self.tmp_file("global_nova.jsonl")
        game_path = self.tmp_file("jogo_novo.jsonl")
        engine = FakeEngine()

        result = self.run_translate(
            [make_row("T000001", "txt/demo.txt", 4, JP_GREETING)],
            engine,
            tm_path=game_path,
            global_path=global_path,
        )

        self.assertEqual(result["statuses"].get("llm"), 1)
        game_records = read_jsonl(game_path)
        global_records = read_jsonl(global_path)
        self.assertEqual(len(game_records), 1, "por-jogo recebe exatamente 1 par")
        self.assertEqual(len(global_records), 1, "global recebe exatamente 1 par")
        # Por-jogo mantem o caminho cru (comportamento atual).
        self.assertEqual(game_records[0]["file"], "txt/demo.txt")
        self.assertEqual(game_records[0]["target"], "EN:" + JP_GREETING)
        # Na global, campo file vem prefixado com o id do jogo.
        self.assertEqual(
            global_records[0]["file"],
            "jogoteste" + GLOBAL_FILE_SEPARATOR + "txt/demo.txt",
        )
        self.assertEqual(global_records[0]["target"], "EN:" + JP_GREETING)
        self.assertEqual(global_records[0]["source"], JP_GREETING)

    def test_without_global_flag_keeps_previous_behavior(self):
        game_path = self.tmp_file("jogo_sem_global.jsonl")
        engine = FakeEngine()

        result = self.run_translate(
            [make_row("T000001", "txt/demo.txt", 4, JP_GREETING)],
            engine,
            tm_path=game_path,
            global_path=None,
        )

        self.assertEqual(result["statuses"].get("llm"), 1)
        records = read_jsonl(game_path)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["file"], "txt/demo.txt")

    def test_corrupted_global_line_does_not_crash_run(self):
        global_path = self.tmp_file("global_corrompida.jsonl")
        lines = [
            json.dumps(make_pair(JP_DEMO, "ALVO DA GLOBAL"), ensure_ascii=False),
            "{linha corrompida de proposito",
            "nao-e-json",
        ]
        global_path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
        game_path = self.tmp_file("jogo_vazio.jsonl")
        engine = FakeEngine()

        result = self.run_translate(
            [make_row("T000001", "txt/demo.txt", 2, JP_DEMO)],
            engine,
            tm_path=game_path,
            global_path=global_path,
        )

        self.assertEqual(engine.calls, [])
        records = read_csv_rows(result["csv_path"])
        self.assertEqual(records[0]["status"], "tm_hit")
        self.assertEqual(records[0]["translated"], "ALVO DA GLOBAL")


if __name__ == "__main__":
    unittest.main()
