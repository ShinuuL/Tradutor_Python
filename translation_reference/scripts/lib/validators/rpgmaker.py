# -*- coding: utf-8 -*-
"""Validador de traducoes para RPG Maker VX/Ace.

Componente da Fase 7 do TradutorDGames.

Valida que escape sequences RPG Maker e placeholders de script sao
preservados na traducao.

Somente biblioteca padrao. Mensagens em pt-BR sem acento.
"""

import re
from typing import List

from .base import TranslationValidator, ValidationResult, check_placeholders

__all__ = ["RPGMakerValidator"]

# Escape sequences RPG Maker que devem ser preservados exatamente.
# \\N[x]  nome de ator/variavel
# \\C[x]  cor
# \\{     aumenta tamanho da fonte
# \\}     diminui tamanho da fonte
# \\<     alinha texto a esquerda
# \\>     alinha texto a direita
_RPGMAKER_ESCAPE_RE = re.compile(
    r"\\[Nn]\[[^\]]*\]"
    r"|\\[Cc]\[[^\]]*\]"
    r"|\\\{|\\\}"
    r"|\\<|\\>"
)

# Placeholders de script: {variable}, {code}, {0}, {1}, etc.
# Usa negative lookbehind para nao confundir com escapes \{ \}.
_SCRIPT_PLACEHOLDER_RE = re.compile(r"(?<!\\)\{[^}]*\}")


class RPGMakerValidator(TranslationValidator):
    """Validador para traducoes RPG Maker VX/Ace.

    Confere:
    - Escape sequences \\N, \\C, \\{, \\}, \\<, \\> preservados.
    - Placeholders de script {variable}, {code} preservados.
    - Checks comuns (encoding, newlines, vazio, ratio).
    """

    def category_tags(self) -> List[str]:
        """Tags da engine RPG Maker que devem ser preservadas."""
        return ["\\N[x]", "\\C[x]", "\\{", "\\}", "\\<", "\\>"]

    def validate(self, source: str, translated: str) -> ValidationResult:
        """Valida traducao RPG Maker contra o source original."""
        result = self._run_common_checks(source, translated)

        # Confere escapes RPG Maker especificos.
        src_escapes = _RPGMAKER_ESCAPE_RE.findall(source)
        tgt_escapes = _RPGMAKER_ESCAPE_RE.findall(translated)
        src_counter = {}
        for e in src_escapes:
            src_counter[e] = src_counter.get(e, 0) + 1
        tgt_counter = {}
        for e in tgt_escapes:
            tgt_counter[e] = tgt_counter.get(e, 0) + 1

        for escape, expected in src_counter.items():
            got = tgt_counter.get(escape, 0)
            if got < expected:
                result.add_error(
                    "escape RPG Maker ausente na traducao: %r "
                    "(esperado %d, encontrado %d)" % (escape, expected, got)
                )
            elif got > expected:
                result.add_warning(
                    "escape RPG Maker em excesso na traducao: %r "
                    "(esperado %d, encontrado %d)" % (escape, expected, got)
                )

        # Confere placeholders de script.
        src_script = _SCRIPT_PLACEHOLDER_RE.findall(source)
        tgt_script = _SCRIPT_PLACEHOLDER_RE.findall(translated)
        src_sc = {}
        for p in src_script:
            src_sc[p] = src_sc.get(p, 0) + 1
        tgt_sc = {}
        for p in tgt_script:
            tgt_sc[p] = tgt_sc.get(p, 0) + 1

        for ph, expected in src_sc.items():
            got = tgt_sc.get(ph, 0)
            if got < expected:
                result.add_error(
                    "placeholder de script ausente na traducao: %r "
                    "(esperado %d, encontrado %d)" % (ph, expected, got)
                )

        return result
