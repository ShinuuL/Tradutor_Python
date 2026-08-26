# -*- coding: utf-8 -*-
"""Reparo conservador de nomes proprios embrulhados em colchetes (A1).

Modelos locais as vezes devolvem nomes latinizados entre colchetes
(``"[Hal] Bom dia"``) mesmo quando o texto original NAO tem marcacao
alguma. Este modulo desfaz esse embrulho de forma conservadora e
fail-closed:

- so age quando o source NAO contem nenhum ``[`` (se o original usa
  tags/colchetes, nada e tocado);
- so desembrulha tokens ``[...]`` cujo conteudo pareca nome latinizado
  (letras, numeros, espaco, apostrofo, ponto, hifen, reticencias) e nao
  seja vazio;
- conteudo que parece comando/tag curta do jogo (segmentos minusculo-
  numericos ligados por pontos, ex.: ``p``, ``0``, ``f.1`` -- familia
  documentada em placeholders.py) e preservado intacto;
- colchetes aninhados (``[[Hal]]``) indicam markup especial: intocado;
- qualquer duvida: mantem intocado (fail-closed).

Devolve ``(texto, notas)``; nota unica possivel:
``colchetes de nome proprio removidos``.

Somente biblioteca padrao. Mensagens em pt-BR sem acento.
"""
import re

__all__ = ["NOTE_NAME_BRACKETS", "strip_spurious_brackets"]

# Nota unica possivel gravada nos registros/relatorios.
NOTE_NAME_BRACKETS = "colchetes de nome proprio removidos"

# Conteudo candidato a nome latinizado (regra (b) do plano A1).
_NAME_CONTENT_RE = re.compile(r"^[A-Za-z0-9 '\.\-…]+$")

# Forma de comando/tag curta do projeto ([p], [0], [f.1]): segmentos
# minusculo-numericos opcionalmente ligados por pontos. Nao e nome.
_COMMAND_LIKE_RE = re.compile(r"^[a-z0-9]+(?:\.[a-z0-9]+)*$")

# Token [...] simples, sem colchetes aninhados (mesmo recorte de tag).
_TAG_RE = re.compile(r"\[([^\[\]]*)\]")


def strip_spurious_brackets(source, translated):
    """Remove colchetes espurios de nomes na saida do motor de traducao.

    ``source`` e o texto original do jogo e ``translated`` a traducao do
    motor. Devolve ``(texto, notas)``: texto possivelmente reparado e a
    lista de notas (vazia ou com ``NOTE_NAME_BRACKETS``). Entrada nao
    string ou source com qualquer ``[`` devolve a traducao intocada
    (fail-closed).
    """
    if not isinstance(translated, str):
        return translated, []
    notes = []
    if not isinstance(source, str) or "[" in source:
        return translated, notes

    changed = False

    def _unwrap(match):
        nonlocal changed
        token = match.group(0)
        content = match.group(1)
        # Colchetes aninhados ([[Hal]]): markup especial, intocado.
        start, end = match.span()
        before = translated[start - 1] if start > 0 else ""
        after = translated[end] if end < len(translated) else ""
        if "[" in (before, after):
            return token
        # (c) token nao vazio.
        if not content:
            return token
        # (b) conteudo parece nome latinizado.
        if not _NAME_CONTENT_RE.fullmatch(content):
            return token
        # Parece comando/tag curta do jogo ([p], [0], [f.1]): intocado.
        if _COMMAND_LIKE_RE.fullmatch(content):
            return token
        changed = True
        return content

    texto = _TAG_RE.sub(_unwrap, translated)
    if changed:
        notes.append(NOTE_NAME_BRACKETS)
    return texto, notes
