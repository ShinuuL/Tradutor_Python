# -*- coding: utf-8 -*-
"""Validador de traducoes para Ren'Py.

Componente da Fase 7 do TradutorDGames.

Valida que markup Ren'Py ({b}, {i}, {color}, {a}, {{, }}) e tags
ATL sao preservados na traducao.

Somente biblioteca padrao. Mensagens em pt-BR sem acento.
"""

import re
from typing import List

from .base import TranslationValidator, ValidationResult

__all__ = ["RenPyValidator"]

# Markup Ren'Py que deve ser preservado.
# {b}...{/b}, {i}...{/i}, {color=...}...{/color}, {a=...}...{/a}
# {{ e }} sao escapes de chaves (literal { e }).
_RENPY_TAG_RE = re.compile(
    r"\{/?[bius]"
    r"|\{/?color=[^}]*\}"
    r"|\{/?a=[^}]*\}"
    r"|\{\}"
    r"|\\{"  # escape literal \{
    r"|\\}"  # escape literal \}
)

# Bloco de escape {{ ... }} para literal { }
_RENPY_ESCAPED_BRACE_RE = re.compile(r"\{\{[^}]*\}\}")

# Placeholder de高等 (inline displayable) e imagemap tags.
_RENPY_DISPLAYABLE_RE = re.compile(
    r"\{[a-z_]+=[^}]*\}"
    r"|\{[a-z_]+\}"
)


class RenPyValidator(TranslationValidator):
    """Validador para traducoes Ren'Py.

    Confere:
    - Markup {b}, {i}, {color}, {a} preservado.
    - Escapes {{ e }} preservados.
    - Checks comuns (encoding, newlines, vazio, ratio).
    """

    def category_tags(self) -> List[str]:
        """Tags/markup Ren'Py que devem ser preservados."""
        return ["{b}", "{/b}", "{i}", "{/i}", "{{", "}}", "{a=link}", "{/a}"]

    def validate(self, source: str, translated: str) -> ValidationResult:
        """Valida traducao Ren'Py contra o source original."""
        result = self._run_common_checks(source, translated)

        # Confere markup Ren'Py.
        src_tags = _RENPY_TAG_RE.findall(source)
        tgt_tags = _RENPY_TAG_RE.findall(translated)
        src_counter = {}
        for t in src_tags:
            src_counter[t] = src_counter.get(t, 0) + 1
        tgt_counter = {}
        for t in tgt_tags:
            tgt_counter[t] = tgt_counter.get(t, 0) + 1

        for tag, expected in src_counter.items():
            got = tgt_counter.get(tag, 0)
            if got < expected:
                result.add_error(
                    "markup Ren'Py ausente na traducao: %r "
                    "(esperado %d, encontrado %d)" % (tag, expected, got)
                )
            elif got > expected:
                result.add_warning(
                    "markup Ren'Py em excesso na traducao: %r "
                    "(esperado %d, encontrado %d)" % (tag, expected, got)
                )

        # Confere escapamento de chaves {{ }}.
        src_braces = _RENPY_ESCAPED_BRACE_RE.findall(source)
        tgt_braces = _RENPY_ESCAPED_BRACE_RE.findall(translated)
        if len(src_braces) != len(tgt_braces):
            result.add_warning(
                "quantidade de escapamento {{}} diferente "
                "(source=%d, translated=%d)" % (len(src_braces), len(tgt_braces))
            )

        return result
