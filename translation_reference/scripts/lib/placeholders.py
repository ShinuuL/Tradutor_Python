# -*- coding: utf-8 -*-
"""Extracao e validacao de placeholders e markup em textos de jogos.

Componente F1 do design aprovado em 2026-08-22
(docs/superpowers/specs/2026-08-22-tradutor-local-design.md).

Reconhece quatro familias de tokens que precisam sobreviver a traducao:

- ``escape``  sequencias com barra invertida: ``\\n``, ``\\t``, ``\\N``.
- ``brace``   grupos entre chaves: ``{}``, ``{name}``, ``{i}``, ``{/i}``.
- ``tag``     grupos entre colchetes: ``[p]``, ``[0]``, ``[f.1]``.
- ``percent`` estilo printf: ``%s``, ``%d``, ``%1$s``, ``%(nome)s``.

Somente biblioteca padrao. Mensagens em pt-BR sem acento.
"""
import re

TOKEN_RE = re.compile(
    r"(?P<escape>\\.)"
    r"|(?P<brace>\{[^{}]*\})"
    r"|(?P<tag>\[[^\[\]]*\])"
    r"|(?P<percent>%(?:\(\w+\))?(?:\d+\$)?[#0\- +']*\d*(?:\.\d+)?[a-zA-Z%])"
)

KIND_LABELS = {
    "escape": "sequencia de escape",
    "brace": "grupo de chaves",
    "tag": "tag entre colchetes",
    "percent": "placeholder printf",
}


def extract_typed(text):
    """Percorre o texto uma vez e devolve lista de pares (tipo, token)."""
    if not text:
        return []
    found = []
    for match in TOKEN_RE.finditer(text):
        kind = match.lastgroup
        found.append((kind, match.group(0)))
    return found


def extract_tokens(text):
    """Devolve apenas os tokens encontrados, na ordem em que aparecem."""
    return [token for _kind, token in extract_typed(text)]


def count_by_kind(text):
    """Conta tokens por familia. Util para diagnosticos rapidos."""
    totals = {"escape": 0, "brace": 0, "tag": 0, "percent": 0}
    for kind, _token in extract_typed(text):
        totals[kind] += 1
    return totals


def validate_pair(source, translated):
    """Confere se a traducao preserva os placeholders/markup do original.

    Retorna ``(ok, notes)``. ``ok`` so e verdadeiro quando a contagem de
    cada token coincide entre original e traducao e a traducao nao fica
    vazia com texto original preenchido.
    """
    notes = []
    source_counts = {}
    for kind, token in extract_typed(source):
        key = (kind, token)
        source_counts[key] = source_counts.get(key, 0) + 1

    translated_counts = {}
    for kind, token in extract_typed(translated):
        key = (kind, token)
        translated_counts[key] = translated_counts.get(key, 0) + 1

    for key in sorted(set(source_counts) | set(translated_counts)):
        expected = source_counts.get(key, 0)
        got = translated_counts.get(key, 0)
        if expected == got:
            continue
        kind, token = key
        label = KIND_LABELS.get(kind, kind)
        if got < expected:
            notes.append(
                "%s ausente na traducao: %r (esperado %d, encontrado %d)"
                % (label, token, expected, got)
            )
        else:
            notes.append(
                "%s inesperado na traducao: %r (esperado %d, encontrado %d)"
                % (label, token, expected, got)
            )

    if source.strip() and not translated.strip():
        notes.append("traducao vazia para texto original nao vazio")

    return (not notes, notes)
