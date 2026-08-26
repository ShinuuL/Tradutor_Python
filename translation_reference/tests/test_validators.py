# -*- coding: utf-8 -*-
"""Testes do framework de validadores por adapter.

Cobre:
- ValidationResult: ok/erros/avisos
- check_placeholders: backslash-N[x] preservado vs perdido
- check_encoding: UTF-8 valido vs invalido
- check_newlines: mesma contagem vs diferente
- RPGMakerValidator: backslash-N, backslash-C preservados vs perdidos; backslash-brace preservado
- RenPyValidator: {b} preservado; {{}} preservado
- TyranoValidator: [font] preservado; [glink] preservado
- GodotValidator: percent-s preservado; {name} preservado
- Adapter validator integration: cada adapter tem .validator
- Traducao OK (todos checks passam) vs com erros

Somente biblioteca padrao. Mensagens em pt-BR sem acento.
"""

import sys
import os
import unittest

# Garante que o diretorio pai esta no path para imports.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_LIB_DIR = os.path.join(os.path.dirname(_THIS_DIR), "scripts", "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from validators.base import (
    ValidationResult,
    TranslationValidator,
    check_placeholders,
    check_encoding,
    check_newlines,
    check_empty_translation,
    check_length_ratio,
)
from validators.rpgmaker import RPGMakerValidator
from validators.renpy_val import RenPyValidator
from validators.tyrano_val import TyranoValidator
from validators.godot_val import GodotValidator


# ---------------------------------------------------------------------------
# Testes: ValidationResult
# ---------------------------------------------------------------------------

class TestValidationResult(unittest.TestCase):
    """Testa a classe ValidationResult."""

    def test_ok_default(self):
        r = ValidationResult()
        self.assertTrue(r.ok)
        self.assertEqual(r.errors, [])
        self.assertEqual(r.warnings, [])

    def test_add_error(self):
        r = ValidationResult()
        r.add_error("algo deu errado")
        self.assertFalse(r.ok)
        self.assertEqual(r.errors, ["algo deu errado"])

    def test_add_warning_nao_muda_ok(self):
        r = ValidationResult()
        r.add_warning("atencao")
        self.assertTrue(r.ok)
        self.assertEqual(r.warnings, ["atencao"])

    def test_merge(self):
        r1 = ValidationResult()
        r1.add_warning("aviso 1")
        r2 = ValidationResult()
        r2.add_error("erro 1")
        r1.merge(r2)
        self.assertFalse(r1.ok)
        self.assertEqual(r1.errors, ["erro 1"])
        self.assertEqual(r1.warnings, ["aviso 1"])


# ---------------------------------------------------------------------------
# Testes: check_placeholders
# ---------------------------------------------------------------------------

class TestCheckPlaceholders(unittest.TestCase):
    """Testa a funcao check_placeholders."""

    def test_preservado(self):
        r = check_placeholders(r"Olá \N[1] mundo", r"Hello \N[1] world")
        self.assertTrue(r.ok)

    def test_perdido(self):
        r = check_placeholders(r"Olá \N[1] mundo", r"Hello mundo")
        self.assertFalse(r.ok)
        self.assertTrue(len(r.errors) > 0)

    def test_percent_s_preservado(self):
        r = check_placeholders("Voce tem %s item", "You have %s item")
        self.assertTrue(r.ok)

    def test_percent_s_perdido(self):
        r = check_placeholders("Voce tem %s item", "You have item")
        self.assertFalse(r.ok)


# ---------------------------------------------------------------------------
# Testes: check_encoding
# ---------------------------------------------------------------------------

class TestCheckEncoding(unittest.TestCase):
    """Testa a funcao check_encoding."""

    def test_utf8_valido(self):
        r = check_encoding("Texto com acento: a", "Text with a")
        self.assertTrue(r.ok)

    def test_utf8_valido_unicode(self):
        # Em Python 3 strings ja sao Unicode; teste garante encode/decode.
        r = check_encoding("日本語テスト", "Japanese test")
        self.assertTrue(r.ok)


# ---------------------------------------------------------------------------
# Testes: check_newlines
# ---------------------------------------------------------------------------

class TestCheckNewlines(unittest.TestCase):
    """Testa a funcao check_newlines."""

    def test_mesma_contagem(self):
        r = check_newlines("linha1\nlinha2", "line1\nline2")
        self.assertTrue(r.ok)

    def test_contagem_diferente(self):
        r = check_newlines("linha1\nlinha2\nlinha3", "line1\nline2")
        # Aviso, nao erro.
        self.assertTrue(r.ok)
        self.assertTrue(len(r.warnings) > 0)


# ---------------------------------------------------------------------------
# Testes: check_empty_translation
# ---------------------------------------------------------------------------

class TestCheckEmptyTranslation(unittest.TestCase):
    """Testa a funcao check_empty_translation."""

    def test_traducao_ok(self):
        r = check_empty_translation("Hello", "Ola")
        self.assertTrue(r.ok)

    def test_traducao_vazia(self):
        r = check_empty_translation("Hello", "")
        self.assertFalse(r.ok)


# ---------------------------------------------------------------------------
# Testes: check_length_ratio
# ---------------------------------------------------------------------------

class TestCheckLengthRatio(unittest.TestCase):
    """Testa a funcao check_length_ratio."""

    def test_ratio_normal(self):
        r = check_length_ratio("Hi", "Ola")
        self.assertTrue(r.ok)

    def test_ratio_grande(self):
        r = check_length_ratio("Hi", "A" * 100)
        self.assertTrue(r.ok)  # aviso, nao erro
        self.assertTrue(len(r.warnings) > 0)


# ---------------------------------------------------------------------------
# Testes: RPGMakerValidator
# ---------------------------------------------------------------------------

class TestRPGMakerValidator(unittest.TestCase):
    """Testa o validador RPGMakerValidator."""

    def setUp(self):
        self.v = RPGMakerValidator()

    def test_category_tags(self):
        tags = self.v.category_tags()
        self.assertIn("\\N[x]", tags)
        self.assertIn("\\C[x]", tags)

    def test_n_preservado(self):
        src = r"Olá \N[1] mundo"
        tgt = r"Hello \N[1] world"
        r = self.v.validate(src, tgt)
        self.assertTrue(r.ok)

    def test_n_perdido(self):
        src = r"Olá \N[1] mundo"
        tgt = r"Hello mundo"
        r = self.v.validate(src, tgt)
        self.assertFalse(r.ok)

    def test_c_preservado(self):
        src = r"Texto \C[4] colorido"
        tgt = r"Text \C[4] colored"
        r = self.v.validate(src, tgt)
        self.assertTrue(r.ok)

    def test_c_perdido(self):
        src = r"Texto \C[4] colorido"
        tgt = r"Text colored"
        r = self.v.validate(src, tgt)
        self.assertFalse(r.ok)

    def test_brace_preservado(self):
        src = r"Texto \{ grande \} fim"
        tgt = r"Text \{ big \} end"
        r = self.v.validate(src, tgt)
        self.assertTrue(r.ok)

    def test_brace_perdido(self):
        src = r"Texto \{ grande \} fim"
        tgt = r"Text big end"
        r = self.v.validate(src, tgt)
        self.assertFalse(r.ok)

    def test_placeholder_script(self):
        src = r"Ola {player_name}!"
        tgt = r"Hello {player_name}!"
        r = self.v.validate(src, tgt)
        self.assertTrue(r.ok)

    def test_placeholder_script_perdido(self):
        src = r"Ola {player_name}!"
        tgt = r"Hello!"
        r = self.v.validate(src, tgt)
        self.assertFalse(r.ok)


# ---------------------------------------------------------------------------
# Testes: RenPyValidator
# ---------------------------------------------------------------------------

class TestRenPyValidator(unittest.TestCase):
    """Testa o validador RenPyValidator."""

    def setUp(self):
        self.v = RenPyValidator()

    def test_category_tags(self):
        tags = self.v.category_tags()
        self.assertIn("{b}", tags)
        self.assertIn("{{", tags)

    def test_b_preservado(self):
        src = "{b}Negrito{/b} normal"
        tgt = "{b}Bold{/b} normal"
        r = self.v.validate(src, tgt)
        self.assertTrue(r.ok)

    def test_b_perdido(self):
        src = "{b}Negrito{/b}"
        tgt = "Bold"
        r = self.v.validate(src, tgt)
        self.assertFalse(r.ok)

    def test_escapado_preservado(self):
        src = "Use {{ para literal"
        tgt = "Use {{ for literal"
        r = self.v.validate(src, tgt)
        self.assertTrue(r.ok)

    def test_i_preservado(self):
        src = "Texto {i}italico{/i}"
        tgt = "Text {i}italic{/i}"
        r = self.v.validate(src, tgt)
        self.assertTrue(r.ok)

    def test_color_preservado(self):
        src = "{color=#ff0000}vermelho{/color}"
        tgt = "{color=#ff0000}red{/color}"
        r = self.v.validate(src, tgt)
        self.assertTrue(r.ok)


# ---------------------------------------------------------------------------
# Testes: TyranoValidator
# ---------------------------------------------------------------------------

class TestTyranoValidator(unittest.TestCase):
    """Testa o validador TyranoValidator."""

    def setUp(self):
        self.v = TyranoValidator()

    def test_category_tags(self):
        tags = self.v.category_tags()
        self.assertIn("[font]", tags)
        self.assertIn("[glink]", tags)

    def test_font_preservado(self):
        src = "[font size=20]Ola[/font]"
        tgt = "[font size=20]Hello[/font]"
        r = self.v.validate(src, tgt)
        self.assertTrue(r.ok)

    def test_font_perdido(self):
        src = "[font size=20]Ola[/font]"
        tgt = "Hello"
        r = self.v.validate(src, tgt)
        self.assertFalse(r.ok)

    def test_glink_preservado(self):
        src = "[glink text=\"Sim\" ...]"
        tgt = "[glink text=\"Yes\" ...]"
        r = self.v.validate(src, tgt)
        self.assertTrue(r.ok)

    def test_glink_perdido(self):
        src = "[glink text=\"Sim\" ...]"
        tgt = "Yes"
        r = self.v.validate(src, tgt)
        self.assertFalse(r.ok)

    def test_embexp_preservado(self):
        src = "Valor: [embexp exp=\"f_var\"]"
        tgt = "Value: [embexp exp=\"f_var\"]"
        r = self.v.validate(src, tgt)
        self.assertTrue(r.ok)

    def test_embexp_perdido(self):
        src = "Valor: [embexp exp=\"f_var\"]"
        tgt = "Value:"
        r = self.v.validate(src, tgt)
        self.assertFalse(r.ok)

    def test_controle_preservado(self):
        src = "Texto[l]proximo"
        tgt = "Text[l]next"
        r = self.v.validate(src, tgt)
        self.assertTrue(r.ok)


# ---------------------------------------------------------------------------
# Testes: GodotValidator
# ---------------------------------------------------------------------------

class TestGodotValidator(unittest.TestCase):
    """Testa o validador GodotValidator."""

    def setUp(self = None):
        pass

    def setUp(self):
        self.v = GodotValidator()

    def test_category_tags(self):
        tags = self.v.category_tags()
        self.assertIn("%s", tags)
        self.assertIn("{name}", tags)

    def test_percent_s_preservado(self):
        src = "Voce tem %s moedas"
        tgt = "You have %s coins"
        r = self.v.validate(src, tgt)
        self.assertTrue(r.ok)

    def test_percent_s_perdido(self):
        src = "Voce tem %s moedas"
        tgt = "You have coins"
        r = self.v.validate(src, tgt)
        self.assertFalse(r.ok)

    def test_name_preservado(self):
        src = "Ola {name}, bem vindo!"
        tgt = "Hello {name}, welcome!"
        r = self.v.validate(src, tgt)
        self.assertTrue(r.ok)

    def test_name_perdido(self):
        src = "Ola {name}, bem vindo!"
        tgt = "Hello, welcome!"
        r = self.v.validate(src, tgt)
        self.assertFalse(r.ok)

    def test_bbcode_preservado(self):
        src = "[b]Negrito[/b] [i]Italico[/i]"
        tgt = "[b]Bold[/b] [i]Italic[/i]"
        r = self.v.validate(src, tgt)
        self.assertTrue(r.ok)

    def test_percent_d_preservado(self):
        src = "Restam %d dias"
        tgt = "%d days left"
        r = self.v.validate(src, tgt)
        self.assertTrue(r.ok)


# ---------------------------------------------------------------------------
# Testes: Integracao adapter.validator
# ---------------------------------------------------------------------------

class TestAdapterValidatorIntegration(unittest.TestCase):
    """Testa que cada adapter tem a propriedade .validator."""

    def test_renpy_adapter_validator(self):
        from adapters.renpy import RenPyAdapter
        adapter = RenPyAdapter()
        v = adapter.validator
        self.assertIsInstance(v, RenPyValidator)

    def test_tyrano_adapter_validator(self):
        from adapters.tyrano import TyranoAdapter
        adapter = TyranoAdapter()
        v = adapter.validator
        self.assertIsInstance(v, TyranoValidator)

    def test_godot_adapter_validator(self):
        from adapters.godot import GodotAdapter
        adapter = GodotAdapter()
        v = adapter.validator
        self.assertIsInstance(v, GodotValidator)

    def test_rpgmaker_adapter_validator(self):
        from adapters.rpgmaker_vxace import VXAceAdapter
        adapter = VXAceAdapter()
        v = adapter.validator
        self.assertIsInstance(v, RPGMakerValidator)


# ---------------------------------------------------------------------------
# Testes: Traducao OK vs com erros (cenario completo)
# ---------------------------------------------------------------------------

class TestTraducaoCompleta(unittest.TestCase):
    """Cenarios completos: traducao OK (todos passam) vs com erros."""

    def test_rpgmaker_traducao_ok(self):
        v = RPGMakerValidator()
        src = r"Bem-vindo \N[1] ao \C[4]mundo\}!"
        tgt = r"Welcome \N[1] to \C[4]world\}!"
        r = v.validate(src, tgt)
        self.assertTrue(r.ok)
        self.assertEqual(r.errors, [])

    def test_rpgmaker_traducao_com_erros(self):
        v = RPGMakerValidator()
        src = r"Bem-vindo \N[1] ao \C[4]mundo!"
        tgt = r"Welcome to world!"
        r = v.validate(src, tgt)
        self.assertFalse(r.ok)
        self.assertTrue(len(r.errors) >= 2)

    def test_renpy_traducao_ok(self):
        v = RenPyValidator()
        src = "{b}Oi{/b} {i}mundo{/i}"
        tgt = "{b}Hi{/b} {i}world{/i}"
        r = v.validate(src, tgt)
        self.assertTrue(r.ok)

    def test_renpy_traducao_com_erros(self):
        v = RenPyValidator()
        src = "{b}Oi{/b} {i}mundo{/i}"
        tgt = "Hi world"
        r = v.validate(src, tgt)
        self.assertFalse(r.ok)

    def test_tyrano_traducao_ok(self):
        v = TyranoValidator()
        src = "[font size=20]Ola[/font] [glink text=\"Sim\"]"
        tgt = "[font size=20]Hello[/font] [glink text=\"Yes\"]"
        r = v.validate(src, tgt)
        self.assertTrue(r.ok)

    def test_tyrano_traducao_com_erros(self):
        v = TyranoValidator()
        src = "[font size=20]Ola[/font]"
        tgt = "Hello"
        r = v.validate(src, tgt)
        self.assertFalse(r.ok)

    def test_godot_traducao_ok(self):
        v = GodotValidator()
        src = "Ola %s, voce tem %d moedas {name}"
        tgt = "Hello %s, you have %d coins {name}"
        r = v.validate(src, tgt)
        self.assertTrue(r.ok)

    def test_godot_traducao_com_erros(self):
        v = GodotValidator()
        src = "Ola %s, voce tem {name}"
        tgt = "Hello!"
        r = v.validate(src, tgt)
        self.assertFalse(r.ok)

    def test_traducao_vazia_sempre_erro(self):
        """Traducao vazia sempre gera erro mesmo se checks ok."""
        for v_cls in (RPGMakerValidator, RenPyValidator, TyranoValidator, GodotValidator):
            v = v_cls()
            r = v.validate("Hello", "")
            self.assertFalse(r.ok, msg="%s deveria rejeitar traducao vazia" % v_cls.__name__)


if __name__ == "__main__":
    unittest.main()
