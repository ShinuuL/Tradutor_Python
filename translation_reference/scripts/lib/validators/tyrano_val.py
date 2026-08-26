# -*- coding: utf-8 -*-
"""Validador de traducoes para TyranoScript/TyranoBuilder.

Componente da Fase 7 do TradutorDGames.

Valida que tags TyranoScript e variaveis embexp/eval sao preservadas.

Somente biblioteca padrao. Mensagens em pt-BR sem acento.
"""

import re
from typing import List

from .base import (
    TranslationValidator,
    ValidationResult,
    check_encoding,
    check_newlines,
    check_empty_translation,
    check_length_ratio,
)

__all__ = ["TyranoValidator"]

# Regex para extrair nomes de tags TyranoScript (incluindo / para fechamento).
# Captura: "font" de [font ...], "/font" de [/font], "glink" de [glink ...].
_TYRANO_TAG_NAME_RE = re.compile(r"\[([/]?[a-zA-Z_]\w*)")

# Variaveis especiais TyranoScript.
# [embexp ...]  - expressao embutida
# [eval ...]    - avaliacao de expressao
_TYRANO_VAR_RE = re.compile(r"\[(?:embexp|eval)\b[^\]]*\]")

# Tags de controle especificas que devem ser preservadas.
_CONTROL_TAGS = frozenset({
    "[l]", "[p]", "[cm]", "[wt]", "[stop]", "[wait]",
    "[return]", "[s]", "[r]", "[er]", "[er2]", "[hr]",
    "[backlay]", "[next]", "[retry]", "[click]",
    "[font]", "[/font]", "[glink]", "[link]", "[/link]",
})


class TyranoValidator(TranslationValidator):
    """Validador para traducoes TyranoScript.

    Confere:
    - Tags TyranoScript preservadas (por nome, nao conteudo).
    - Variaveis [embexp], [eval] preservadas.
    - Tags de controle especificas preservadas.
    - Checks comuns (encoding, newlines, vazio, ratio).
    """

    def category_tags(self) -> List[str]:
        """Tags TyranoScript que devem ser preservadas."""
        return ["[l]", "[p]", "[cm]", "[font]", "[/font]", "[glink]"]

    def _common_checks(self, source: str, translated: str) -> ValidationResult:
        """Checks comuns sem check_placeholders (tags sao comparadas por nome)."""
        result = ValidationResult()
        result.merge(check_empty_translation(source, translated))
        if not result.ok:
            return result
        result.merge(check_encoding(source, translated))
        result.merge(check_newlines(source, translated))
        result.merge(check_length_ratio(source, translated))
        return result

    def validate(self, source: str, translated: str) -> ValidationResult:
        """Valida traducao TyranoScript contra o source original."""
        result = self._common_checks(source, translated)

        # Confere nomes de tags TyranoScript (por nome, nao conteudo completo).
        src_names = _TYRANO_TAG_NAME_RE.findall(source)
        tgt_names = _TYRANO_TAG_NAME_RE.findall(translated)
        src_counter = {}
        for n in src_names:
            src_counter[n] = src_counter.get(n, 0) + 1
        tgt_counter = {}
        for n in tgt_names:
            tgt_counter[n] = tgt_counter.get(n, 0) + 1

        for name, expected in src_counter.items():
            got = tgt_counter.get(name, 0)
            if got < expected:
                result.add_error(
                    "tag TyranoScript ausente na traducao: [%s] "
                    "(esperado %d, encontrado %d)" % (name, expected, got)
                )

        # Confere variaveis embexp/eval.
        src_vars = _TYRANO_VAR_RE.findall(source)
        tgt_vars = _TYRANO_VAR_RE.findall(translated)
        if len(src_vars) != len(tgt_vars):
            result.add_error(
                "variaveis TyranoScript (embexp/eval) nao preservadas "
                "(source=%d, translated=%d)" % (len(src_vars), len(tgt_vars))
            )

        # Confere tags de controle especificas do _CONTROL_TAGS.
        for ctag in _CONTROL_TAGS:
            sc = source.count(ctag)
            tc = translated.count(ctag)
            if sc > 0 and tc < sc:
                result.add_error(
                    "tag de controle TyranoScript ausente na traducao: %s "
                    "(esperado %d, encontrado %d)" % (ctag, sc, tc)
                )

        return result
