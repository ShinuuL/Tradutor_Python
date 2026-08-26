# -*- coding: utf-8 -*-
"""Testes offline do parse/classificacao do resultado do apply na UI.

Cobertura do endurecimento autorizado (painel Tk, sem GUI real):
- parse_applied_count: extrai N da linha "Aplicados: N ..." do stdout;
- classify_apply_result: exit 0 com N > 0 => success; exit 0 com N == 0 ou
  contagem ausente => WARNING (nunca sucesso); exit 3 => sem aprovacao;
  outros codigos => erro.

Funcoes puras de modulo: nao instancia Tk nem abre janela.
"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP_DIR = HERE.parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from text_scanner_app import classify_apply_result, parse_applied_count  # noqa: E402


class ParseAppliedCountTests(unittest.TestCase):
    def test_parses_count_from_applied_line(self):
        lines = [
            "Aplicados: 7 | backup reaproveitado: 2 | protegidos (jogo mudou): 0 | sem original: 0",
            "  reaplicado, backup original mantido: txt/story.txt",
        ]
        self.assertEqual(parse_applied_count(lines), 7)

    def test_parses_zero_when_nothing_written(self):
        lines = [
            "Aplicados: 0 | backup reaproveitado: 0 | protegidos (jogo mudou): 43 | sem original: 0",
            "  abortado, jogo mudou desde o backup; .bak preservado: readme.txt",
        ]
        self.assertEqual(parse_applied_count(lines), 0)

    def test_returns_none_without_applied_line(self):
        self.assertIsNone(parse_applied_count(["linha qualquer", "PROGRESS 1/9"]))
        self.assertIsNone(parse_applied_count([]))
        self.assertIsNone(parse_applied_count(None))

    def test_first_applied_line_wins(self):
        lines = ["Aplicados: 5 | x", "Aplicados: 9 | y"]
        self.assertEqual(parse_applied_count(lines), 5)


class ClassifyApplyResultTests(unittest.TestCase):
    def test_success_requires_positive_count(self):
        self.assertEqual(classify_apply_result(0, 1), "success")
        self.assertEqual(classify_apply_result(0, 43), "success")

    def test_zero_or_missing_count_is_warning_not_success(self):
        self.assertEqual(classify_apply_result(0, 0), "warning")
        self.assertEqual(classify_apply_result(0, None), "warning")

    def test_exit_3_is_no_approval(self):
        self.assertEqual(classify_apply_result(3, None), "no_approval")
        self.assertEqual(classify_apply_result(3, 0), "no_approval")

    def test_other_nonzero_codes_are_error(self):
        self.assertEqual(classify_apply_result(2, None), "error")
        self.assertEqual(classify_apply_result(4, 0), "error")
        self.assertEqual(classify_apply_result(1, None), "error")


if __name__ == "__main__":
    unittest.main()
