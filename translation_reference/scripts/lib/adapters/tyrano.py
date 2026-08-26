# -*- coding: utf-8 -*-
"""Adapter de extracao para a engine TyranoScript/TyranoBuilder (.ks).

Componente da Fase 7 (adapters multi-engine) do TradutorDGames.

Detecta jogos TyranoScript pela presenca de arquivos .ks em data/scenario/
ou Config.tjs em data/system/. Extrai textos semanticamente significativos:

- Dialogue: linhas que nao comecam com [ nem ; e nao estao dentro de tags.
- Character names: atributo name= em tags [char] ou [chara].
- Menu items: atributo text= em [glink] e textos de [link].
- Font-styled text: conteudo entre [font] e [/font].
- Skip: linhas puramente tags ([stop] [wait] [return] etc.) ou comentarios.

Contrato
--------
- ``detect``: True quando existem .ks em data/scenario/ OU Config.tjs em
  data/system/ (busca recursiva limitada a 3 niveis).
- ``extract``: iterador de ``TextEntry`` com category sendo
  ``tyrano_dialogue``, ``tyrano_name``, ``tyrano_menu`` ou ``tyrano_font``.
- ``metadata``: ``{"engine": "tyrano", "ks_count": N}``.

Somente biblioteca padrao. Mensagens em pt-BR sem acento.
"""

import os
import re
from pathlib import Path
from typing import Iterator

try:
    from . import EngineAdapter, TextEntry, register_adapter
except ImportError:
    from __init__ import EngineAdapter, TextEntry, register_adapter

__all__ = ["TyranoAdapter"]

# Limite de profundidade para busca em detect().
_MAX_DETECT_DEPTH = 3

# ---------------------------------------------------------------------------
# Padroes de parsing de .ks
# ---------------------------------------------------------------------------

# Tag TyranoScript generica: [tag ...] ou [tag ... /].
_TAG_RE = re.compile(r"^\[([a-zA-Z_]\w*)(?:\s[^]]*)?\]$")

# Tags que indicam que a linha e puramente controle (nao dialogue).
_SKIP_TAGS = frozenset({
    "l", "p", "cm", "wt", "stop", "wait", "return", "s", "r",
    "er", "er2", "hr", "backlay", "next", "retry",
    "clearsysconfig", "clearstorage",
    "click", "glyph", "commit",
})

# Tag [char name="X"] ou [chara name="X"].
_CHAR_NAME_RE = re.compile(
    r"^\[(?:char|chara)\b[^]]*\bname\s*=\s*[\"']?([^\"'\s\]]+)[\"']?[^]]*\]$"
)

# Tag [glink text="X" ...].
_GLINK_RE = re.compile(
    r"^\[glink\b[^]]*\btext\s*=\s*[\"'](.+?)[\"'][^]]*\]$"
)

# Tag [link ...]text[/link]  ou  [link ...]text (sem fechamento).
_LINK_RE = re.compile(
    r"^\[link\b[^]]*\](.+?)(?:\[/link\])?$"
)

# Tag [font ...]texto[/font]  (texto inline).
_FONT_INLINE_RE = re.compile(
    r"^\[font\b[^]]*\](.+?)\[/font\]$"
)

# Tag [font ...]  so abre (texto na proxima linha ou no resto da linha).
_FONT_OPEN_RE = re.compile(r"^\[font\b[^]]*\]")

# Tag de fechamento [/font].
_FONT_CLOSE_RE = re.compile(r"^\[/font\]$")

# Tag generica com conteudo entre abertura e fechamento: [tag]text[/tag].
_WRAPPED_TAG_RE = re.compile(
    r"^\[([a-zA-Z_]\w*)(?:\s[^]]*)?\].+\[/\1\]$"
)

# Comentario TyranoScript comeca com ;.
_COMMENT_RE = re.compile(r"^\s*;")


# ---------------------------------------------------------------------------
# Funcoes auxiliares
# ---------------------------------------------------------------------------

def _read_text(path):
    """Le arquivo tentando encoding comum; devolve (texto, encoding) ou (None, None)."""
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "cp932", "shift_jis", "utf-16", "latin-1"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return None, None


def _find_ks_files(game_path, max_depth=_MAX_DETECT_DEPTH):
    """Busca recursiva por .ks com limite de profundidade."""
    root = Path(game_path)
    if not root.is_dir():
        return
    root_depth = len(root.parts)
    for current, dirs, files in os.walk(root):
        depth = len(Path(current).parts) - root_depth
        if depth >= max_depth:
            dirs.clear()
            continue
        for name in files:
            if name.lower().endswith(".ks"):
                yield Path(current) / name


def _find_config_tjs(game_path, max_depth=_MAX_DETECT_DEPTH):
    """Busca recursiva por Config.tjs com limite de profundidade."""
    root = Path(game_path)
    if not root.is_dir():
        return
    root_depth = len(root.parts)
    for current, dirs, files in os.walk(root):
        depth = len(Path(current).parts) - root_depth
        if depth >= max_depth:
            dirs.clear()
            continue
        for name in files:
            if name == "Config.tjs":
                yield Path(current) / name


def _is_pure_tag_line(stripped):
    """Verifica se a linha e puramente uma tag TyranoScript (ou comentario)."""
    if not stripped:
        return True
    if _COMMENT_RE.match(stripped):
        return True
    tag_match = _TAG_RE.match(stripped)
    if tag_match:
        tag_name = tag_match.group(1).lower()
        return True  # qualquer tag pura e skip
    if _WRAPPED_TAG_RE.match(stripped):
        return True  # [tag]text[/tag] e controle, nao dialogue
    return False


def _extract_tag_name(stripped):
    """Extrai o nome da tag de uma linha que comeca com [. Devolve lowercase ou None."""
    tag_match = _TAG_RE.match(stripped)
    if tag_match:
        return tag_match.group(1).lower()
    return None


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class TyranoAdapter(EngineAdapter):
    """Adapter para jogos TyranoScript/TyranoBuilder (.ks)."""

    @property
    def validator(self):
        """Devolve o validador TyranoValidator para esta engine."""
        try:
            from ..validators.tyrano_val import TyranoValidator
        except ImportError:
            from validators.tyrano_val import TyranoValidator
        return TyranoValidator()

    def detect(self, game_path: str) -> bool:
        """True se game_path contiver .ks em data/scenario/ ou Config.tjs em data/system/."""
        # Verifica .ks em data/scenario/
        for ks in _find_ks_files(game_path):
            rel = str(ks.relative_to(Path(game_path))).replace("\\", "/").lower()
            if rel.startswith("data/scenario/"):
                return True
        # Verifica Config.tjs em data/system/
        for cfg in _find_config_tjs(game_path):
            rel = str(cfg.relative_to(Path(game_path))).replace("\\", "/").lower()
            if rel.startswith("data/system/"):
                return True
        return False

    def extract(self, game_path: str) -> Iterator[TextEntry]:
        """Itera textos semanticos dos arquivos .ks."""
        for ks_path in _find_ks_files(game_path):
            yield from self._extract_from_file(ks_path, game_path)

    def metadata(self, game_path: str) -> dict:
        """Devolve contagem de .ks."""
        ks_count = sum(1 for _ in _find_ks_files(game_path))
        return {"engine": "tyrano", "ks_count": ks_count}

    # ------------------------------------------------------------------
    # parsing interno

    def _extract_from_file(self, ks_path, game_root):
        """Extrai textos de um unico arquivo .ks."""
        text, encoding = _read_text(ks_path)
        if text is None:
            return

        rel = str(ks_path.relative_to(Path(game_root))).replace("\\", "/")
        in_font_block = False

        for line_no, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()

            # Ignora linhas vazias e comentarios.
            if not stripped or _COMMENT_RE.match(stripped):
                continue

            tag_name = _extract_tag_name(stripped)

            # Controle de bloco [font]...[/font].
            if _FONT_CLOSE_RE.match(stripped):
                in_font_block = False
                continue
            if _FONT_OPEN_RE.match(stripped) and not _FONT_INLINE_RE.match(stripped):
                in_font_block = True
                # Verifica se ha texto apos a tag de abertura na mesma linha.
                remainder = _FONT_OPEN_RE.sub("", stripped).strip()
                if remainder and not _TAG_RE.match(remainder):
                    yield TextEntry(
                        file=rel,
                        line=line_no,
                        source=remainder,
                        source_key="font.%s.%d" % (rel, line_no),
                        category="tyrano_font",
                        context={"tag": "font"},
                    )
                continue

            # Texto dentro de bloco font (que nao e tag nem comentario).
            if in_font_block and not _TAG_RE.match(stripped):
                yield TextEntry(
                    file=rel,
                    line=line_no,
                    source=stripped,
                    source_key="font.%s.%d" % (rel, line_no),
                    category="tyrano_font",
                    context={"tag": "font"},
                )
                continue

            # [font ...]texto[/font] inline.
            font_match = _FONT_INLINE_RE.match(stripped)
            if font_match:
                body = font_match.group(1).strip()
                if body:
                    yield TextEntry(
                        file=rel,
                        line=line_no,
                        source=body,
                        source_key="font.%s.%d" % (rel, line_no),
                        category="tyrano_font",
                        context={"tag": "font"},
                    )
                continue

            # [char name="X"] ou [chara name="X"].
            char_match = _CHAR_NAME_RE.match(stripped)
            if char_match:
                name_val = char_match.group(1)
                if name_val:
                    yield TextEntry(
                        file=rel,
                        line=line_no,
                        source=name_val,
                        source_key="name.%s.%d" % (rel, line_no),
                        category="tyrano_name",
                        context={"tag": tag_name or "char"},
                    )
                continue

            # [glink text="X" ...].
            glink_match = _GLINK_RE.match(stripped)
            if glink_match:
                body = glink_match.group(1).strip()
                if body:
                    yield TextEntry(
                        file=rel,
                        line=line_no,
                        source=body,
                        source_key="menu.%s.%d" % (rel, line_no),
                        category="tyrano_menu",
                        context={"tag": "glink"},
                    )
                continue

            # [link ...]text[/link] ou [link ...]text.
            link_match = _LINK_RE.match(stripped)
            if link_match:
                body = link_match.group(1).strip()
                if body and not _TAG_RE.match(body):
                    yield TextEntry(
                        file=rel,
                        line=line_no,
                        source=body,
                        source_key="menu.%s.%d" % (rel, line_no),
                        category="tyrano_menu",
                        context={"tag": "link"},
                    )
                continue

            # Linha puramente tag -> skip (nao emite nada).
            if tag_name is not None:
                continue

            # Tag com conteudo entre abertura e fechamento -> skip.
            if _WRAPPED_TAG_RE.match(stripped):
                continue

            # Dialogue: qualquer texto que nao comeca com [ e nao e comentario.
            if stripped and not _TAG_RE.match(stripped):
                yield TextEntry(
                    file=rel,
                    line=line_no,
                    source=stripped,
                    source_key="dialogue.%s.%d" % (rel, line_no),
                    category="tyrano_dialogue",
                    context={},
                )


# Registra o adapter automaticamente ao importar o modulo.
register_adapter("tyrano", TyranoAdapter())
