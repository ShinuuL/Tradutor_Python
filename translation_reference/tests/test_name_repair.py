# -*- coding: utf-8 -*-
"""Testes do reparo conservador de colchetes de nomes (passo A1).

Cobertura exigida pelo plano A1:

- ``strip_spurious_brackets``: desembrulha token tipo nome presente na
  traducao mas ausente no source, SOMENTE quando o source nao tem nenhum
  colchete e o conteudo parece nome latinizado; caso contrario mantem
  intocado (fail-closed);
- nota unica possivel: "colchetes de nome proprio removidos";
- ``resolve_translations`` aplica o reparo SOMENTE na saida do motor
  (hit de memoria de traducao nunca e alterado) e coleta notas por chave;
- as notas chegam aos registros (build_records + finalize_records);
- ``SYSTEM_PROMPT`` instrui o motor a nao embrulhar nomes proprios em
  colchetes.

Somente biblioteca padrao. Mensagens em pt-BR sem acento.
"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent / "scripts"
LIB_DIR = SCRIPTS_DIR / "lib"
for extra in (str(SCRIPTS_DIR), str(LIB_DIR)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

import name_repair  # noqa: E402
from name_repair import NOTE_NAME_BRACKETS, strip_spurious_brackets  # noqa: E402
import translate_game_text as tcli  # noqa: E402
from translation_engine import SYSTEM_PROMPT  # noqa: E402


class StripSpuriousBracketsTests(unittest.TestCase):
    """Contrato puro de strip_spurious_brackets (regra conservadora)."""

    def test_mandated_case_unwraps_latinized_name_absent_in_source(self):
        # Caso minimo obricatorio do plano A1.
        texto, notes = strip_spurious_brackets("おはよう、ハルト", "[Hal] Bom dia")
        self.assertEqual(texto, "Hal Bom dia")
        self.assertEqual(notes, [NOTE_NAME_BRACKETS])

    def test_mandated_case_source_with_bracket_keeps_everything(self):
        # Source contem '[': nada e tocado, nem o token legitimo [p].
        texto, notes = strip_spurious_brackets("[p]待って", "[p] Espera [Hal]")
        self.assertEqual(texto, "[p] Espera [Hal]")
        self.assertEqual(notes, [])

    def test_mandated_case_command_like_token_untouched(self):
        # Conteudo parece comando/tag curta ([f.1]): intocado, sem nota.
        texto, notes = strip_spurious_brackets("こんにちは", "[f.1] Oi")
        self.assertEqual(texto, "[f.1] Oi")
        self.assertEqual(notes, [])

    def test_short_tag_codes_from_placeholders_family_untouched(self):
        # Familia de tags documentada em placeholders.py: [p], [0].
        for translated in ("[p] Oi", "[0] Vamos", "[w2] Espere"):
            texto, notes = strip_spurious_brackets("こんにちは", translated)
            self.assertEqual(texto, translated)
            self.assertEqual(notes, [])

    def test_name_with_apostrophe_and_period_is_unwrapped(self):
        texto, notes = strip_spurious_brackets("ダレン", "[O'Brien Jr.] Ola")
        self.assertEqual(texto, "O'Brien Jr. Ola")
        self.assertEqual(notes, [NOTE_NAME_BRACKETS])

    def test_hyphenated_name_is_unwrapped(self):
        texto, notes = strip_spurious_brackets("ジーン", "Aqui vem [Jean-Luc]")
        self.assertEqual(texto, "Aqui vem Jean-Luc")
        self.assertEqual(notes, [NOTE_NAME_BRACKETS])

    def test_multiple_names_yield_single_note(self):
        texto, notes = strip_spurious_brackets(
            "ハルトとレンが来た", "[Hal] e [Ren] chegaram"
        )
        self.assertEqual(texto, "Hal e Ren chegaram")
        self.assertEqual(notes, [NOTE_NAME_BRACKETS])

    def test_translation_without_brackets_has_no_note(self):
        texto, notes = strip_spurious_brackets("おはよう", "Bom dia")
        self.assertEqual(texto, "Bom dia")
        self.assertEqual(notes, [])

    def test_empty_token_is_untouched(self):
        texto, notes = strip_spurious_brackets("こんにちは", "Oi [] mundo")
        self.assertEqual(texto, "Oi [] mundo")
        self.assertEqual(notes, [])

    def test_non_latinized_content_is_untouched(self):
        texto, notes = strip_spurious_brackets("こんにちは", "Oi [ハルト]")
        self.assertEqual(texto, "Oi [ハルト]")
        self.assertEqual(notes, [])

    def test_mixed_tokens_repair_only_names(self):
        texto, notes = strip_spurious_brackets("こんにちは", "[f.1] Oi [Hal]")
        self.assertEqual(texto, "[f.1] Oi Hal")
        self.assertEqual(notes, [NOTE_NAME_BRACKETS])

    def test_unclosed_bracket_is_untouched(self):
        texto, notes = strip_spurious_brackets("こんにちは", "Oi [Hal mundo")
        self.assertEqual(texto, "Oi [Hal mundo")
        self.assertEqual(notes, [])

    def test_nested_brackets_are_untouched(self):
        texto, notes = strip_spurious_brackets("こんにちは", "Oi [[Hal]] mundo")
        self.assertEqual(texto, "Oi [[Hal]] mundo")
        self.assertEqual(notes, [])

    def test_non_string_input_fails_closed(self):
        texto, notes = strip_spurious_brackets("おはよう", None)
        self.assertIsNone(texto)
        self.assertEqual(notes, [])


class FakeTM:
    """Memoria de traducao injetavel com hits fixos."""

    def __init__(self, hits=None):
        self.hits = dict(hits or {})

    def lookup(self, key):
        return self.hits.get(key)


class FakeResilientEngine:
    """Motor fake seguindo o contrato resiliente basico do CLI."""

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def translate_batch_resilient(self, texts):
        self.calls.append(list(texts))
        outputs = []
        for index, text in enumerate(texts):
            fallback = "EN:" + text
            outputs.append(
                self.outputs[index] if index < len(self.outputs) else fallback
            )
        return outputs, []


class ResolveTranslationsRepairTests(unittest.TestCase):
    """Reparo aplicado somente na saida do motor; TM hit fica intacto."""

    KEY_HIT = "おはよう、ハルト"
    KEY_MISS = "こんにちは、レン"

    def test_repair_applies_only_to_engine_output(self):
        tm = FakeTM({self.KEY_HIT: "[Hal] Bom dia"})
        engine = FakeResilientEngine(["[Ren] Ola"])
        repairs = {}
        result = tcli.resolve_translations(
            [self.KEY_HIT, self.KEY_MISS], tm, engine, repairs=repairs
        )
        translations, tm_keys, engine_error, failed_keys = result
        self.assertEqual(len(result), 4)
        # Hit de TM NUNCA e alterado, mesmo com colchetes espurios.
        self.assertEqual(translations[self.KEY_HIT], "[Hal] Bom dia")
        self.assertIn(self.KEY_HIT, tm_keys)
        # Saida do motor e reparada e ganha entrada de nota por chave.
        self.assertEqual(translations[self.KEY_MISS], "Ren Ola")
        self.assertNotIn(self.KEY_MISS, tm_keys)
        self.assertEqual(repairs, {self.KEY_MISS: [NOTE_NAME_BRACKETS]})
        self.assertIsNone(engine_error)
        self.assertEqual(failed_keys, {})

    def test_legacy_signature_still_returns_four_tuple_and_repairs(self):
        engine = FakeResilientEngine(["[Hal] Bom dia"])
        result = tcli.resolve_translations(["おはよう、ハルト"], None, engine)
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0]["おはよう、ハルト"], "Hal Bom dia")

    def test_failed_item_gets_no_repair_entry(self):
        class FailFirstEngine(FakeResilientEngine):
            def translate_batch_resilient(self, texts):
                self.calls.append(list(texts))
                return [""], [0]

        engine = FailFirstEngine([])
        repairs = {}
        translations, _tm, _err, failed = tcli.resolve_translations(
            [self.KEY_MISS], None, engine, repairs=repairs
        )
        self.assertEqual(failed, {self.KEY_MISS: tcli.RESILIENT_FAIL_NOTE})
        self.assertNotIn(self.KEY_MISS, translations)
        self.assertEqual(repairs, {})


class RepairNotesRecordsTests(unittest.TestCase):
    """Notas do reparo chegam aos registros e ao campo notes."""

    def test_build_and_finalize_attach_repair_note(self):
        rows = [
            {"item_id": "i1", "file": "data/a.json", "text": "おはよう"},
            {"item_id": "i2", "file": "data/a.json", "text": "こんにちは"},
        ]
        translations = {"おはよう": "Hal Bom dia", "こんにちは": "[f.1] Oi"}
        repairs = {"おはよう": [NOTE_NAME_BRACKETS]}
        records = tcli.build_records(rows, translations, set(), {}, repairs)
        self.assertEqual(records[0]["origin"], "llm")
        self.assertEqual(records[0]["translated"], "Hal Bom dia")
        self.assertEqual(records[0]["repair_notes"], [NOTE_NAME_BRACKETS])
        self.assertEqual(records[1]["repair_notes"], [])
        for record in records:
            record["_audit_index"] = 0
        audits = [{"status": "applied", "notes": []}]
        tcli.finalize_records(records, audits, None)
        self.assertEqual(records[0]["notes"], [NOTE_NAME_BRACKETS])
        self.assertEqual(records[1]["notes"], [])

    def test_default_arguments_keep_old_behavior(self):
        rows = [{"item_id": "i1", "file": "data/a.json", "text": "おはよう"}]
        records = tcli.build_records(rows, {"おはよう": "Bom dia"}, set())
        self.assertEqual(records[0]["repair_notes"], [])
        records[0]["_audit_index"] = 0
        tcli.finalize_records(records, [{"status": "applied", "notes": []}], None)
        self.assertEqual(records[0]["notes"], [])


class SystemPromptAntiBracketsTests(unittest.TestCase):
    """SYSTEM_PROMPT proibe embrulhar nomes proprios em colchetes."""

    def test_prompt_has_anti_bracket_instruction(self):
        self.assertIn("Do NOT wrap proper nouns in square brackets.", SYSTEM_PROMPT)
        self.assertIn(
            "Render names in romaji/English without any brackets.", SYSTEM_PROMPT
        )


if __name__ == "__main__":
    unittest.main()
