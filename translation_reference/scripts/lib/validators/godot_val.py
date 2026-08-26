# -*- coding: utf-8 -*-
"""Validador de traducoes para Godot Engine.

Componente da Fase 7 do TradutorDGames.

Valida que placeholders Godot (%s, %d, {name}, tr()) e BBCodes
do RichTextLabel sao preservados.

Somente biblioteca padrao. Mensagens em pt-BR sem acento.
"""

import re
from typing import List

from .base import TranslationValidator, ValidationResult

__all__ = ["GodotValidator"]

# Placeholders printf Godot: %s, %d, %02d, %1$s, %(name)s, etc.
_GODOT_PRINTF_RE = re.compile(
    r"%(?:\(\w+\))?(?:\d+\$)?[#0\- +']*\d*(?:\.\d+)?[a-zA-Z%]"
)

# Placeholders nomeados Godot: {name}, {value}, etc.
_GODOT_BRACE_PH_RE = re.compile(r"\{[a-zA-Z_]\w*\}")

# BBCodes RichTextLabel: [b], [i], [u], [s], [url], [img], etc.
_GODOT_BBCODE_RE = re.compile(
    r"\[/?(?:b|i|u|s|url|img|color|font|indent|list|table|cell"
    r"|center|right|left|fill|shake|wave|rainbow|fade|sparkle"
    r"|hint|lb|lb2|lb3|lb4)\]"
    r"|\[(?:url|img|color|font|table|cell|hint|lb|lb2|lb3|lb4)=[^\]]*\]"
)


class GodotValidator(TranslationValidator):
    """Validador para traducoes Godot Engine.

    Confere:
    - Placeholders %s, %d, {name} preservados.
    - BBCodes do RichTextLabel preservados.
    - Checks comuns (encoding, newlines, vazio, ratio).
    """

    def category_tags(self) -> List[str]:
        """Tags/placeholders Godot que devem ser preservados."""
        return ["%s", "{name}", "[node]", "tr()"]

    def validate(self, source: str, translated: str) -> ValidationResult:
        """Valida traducao Godot contra o source original."""
        result = self._run_common_checks(source, translated)

        # Confere placeholders printf.
        src_printf = _GODOT_PRINTF_RE.findall(source)
        tgt_printf = _GODOT_PRINTF_RE.findall(translated)
        src_counter = {}
        for p in src_printf:
            src_counter[p] = src_counter.get(p, 0) + 1
        tgt_counter = {}
        for p in tgt_printf:
            tgt_counter[p] = tgt_counter.get(p, 0) + 1

        for ph, expected in src_counter.items():
            got = tgt_counter.get(ph, 0)
            if got < expected:
                result.add_error(
                    "placeholder Godot ausente na traducao: %r "
                    "(esperado %d, encontrado %d)" % (ph, expected, got)
                )

        # Confere placeholders nomeados {name}.
        src_brace = _GODOT_BRACE_PH_RE.findall(source)
        tgt_brace = _GODOT_BRACE_PH_RE.findall(translated)
        src_bc = {}
        for p in src_brace:
            src_bc[p] = src_bc.get(p, 0) + 1
        tgt_bc = {}
        for p in tgt_brace:
            tgt_bc[p] = tgt_bc.get(p, 0) + 1

        for ph, expected in src_bc.items():
            got = tgt_bc.get(ph, 0)
            if got < expected:
                result.add_error(
                    "placeholder nomeado Godot ausente na traducao: %r "
                    "(esperado %d, encontrado %d)" % (ph, expected, got)
                )

        # Confere BBCodes RichTextLabel.
        src_bb = _GODOT_BBCODE_RE.findall(source)
        tgt_bb = _GODOT_BBCODE_RE.findall(translated)
        if len(src_bb) != len(tgt_bb):
            result.add_warning(
                "quantidade de BBCodes diferente "
                "(source=%d, translated=%d)" % (len(src_bb), len(tgt_bb))
            )

        return result
