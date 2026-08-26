# -*- coding: utf-8 -*-
"""Adapter de extracao para a engine Kirikiri/NScripter (.ks).

Componente da Fase 7 (adapters multi-engine) do TradutorDGames.

Detecta jogos Kirikiri pela presenca de arquivos .ks em scenario/
na raiz do jogo OU pasta system/ com arquivos .tjs na raiz, E NAO
se encaixa na estrutura TyranoScript (que tem data/scenario/ e
data/system/Config.tjs).

Extrai textos semanticamente significativos:

- Dialogue: linhas sem tags entre comandos.
- Eval strings: [eval exp="text = 'X'"] -> extrai X.
- Dialog command: [dialog text="X"].
- Macros: texto entre [macro] e [endmacro].
- Skip: linhas puramente comandos ([if] [endif] [eval] [jump]
  [return] [wait] [stop] [image] [playbgm]).

Contrato
--------
- ``detect``: True quando existem .ks em scenario/ OU .tjs em system/
  na raiz, E NAO existe a estrutura TyranoScript (data/scenario/).
- ``extract``: iterador de ``TextEntry`` com category sendo
  ``kirikiri_dialogue``, ``kirikiri_eval``, ``kirikiri_dialog``
  ou ``kirikiri_macro``.
- ``metadata``: ``{"engine": "kirikiri", "ks_count": N}``.

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

__all__ = ["KirikiriAdapter"]

# Limite de profundidade para busca em detect().
_MAX_DETECT_DEPTH = 3

# ---------------------------------------------------------------------------
# Padroes de parsing de .ks Kirikiri
# ---------------------------------------------------------------------------

# Tag Kirikiri generica: [tag ...] ou [tag ... /].
_TAG_RE = re.compile(r"^\[([a-zA-Z_]\w*)(?:\s[^]]*)?\]$")

# Tags de controle que devem ser ignoradas (pura controle).
_SKIP_TAGS = frozenset({
    "if", "endif", "else", "elsif",
    "eval", "embexp",
    "jump", "call", "return", "s",
    "wait", "stop", "image", "playbgm",
    "playse", "fadein", "fadeout",
    "bg", "layopt", "click", "autowait",
    "resetfont", "deffont",
    "rclick", "delay",
    "title", "close",
    "pcm", "wfade",
})

# Tag [eval exp="text = 'X'"] ou [eval exp="text='X'"].
# Captura o valor atribuido a 'text' dentro de exp=.
_EVAL_TEXT_RE = re.compile(
    r"""^\[eval\s+exp\s*=\s*["'].*?text\s*=\s*['"](.+?)['"].*?["']\]$"""
)

# Tag [dialog text="X"].
_DIALOG_RE = re.compile(
    r"""^\[dialog\s+text\s*=\s*["'](.+?)["'][^]]*\]$"""
)

# Tag [macro name="X"].
_MACRO_OPEN_RE = re.compile(
    r"""^\[macro\s+name\s*=\s*["'](.+?)["'][^]]*\]$"""
)

# Tag de fechamento [endmacro].
_MACRO_CLOSE_RE = re.compile(r"^\[endmacro\]$", re.IGNORECASE)

# Comentario comeca com ;.
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


def _find_tjs_files(game_path, max_depth=_MAX_DETECT_DEPTH):
    """Busca recursiva por arquivos .tjs com limite de profundidade."""
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
            if name.lower().endswith(".tjs"):
                yield Path(current) / name


def _is_skip_tag(tag_name):
    """Verifica se a tag e de controle (deve ser ignorada)."""
    return tag_name.lower() in _SKIP_TAGS


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class KirikiriAdapter(EngineAdapter):
    """Adapter para jogos Kirikiri/NScripter (.ks)."""

    def detect(self, game_path: str) -> bool:
        """True se game_path contiver .ks em scenario/ ou .tjs em system/,
        e NAO se encaixar na estrutura TyranoScript."""
        game = Path(game_path)
        if not game.is_dir():
            return False

        # Verifica estrutura TyranoScript: data/scenario/ ou data/system/
        # Se existir, NAO e Kirikiri (e Tyrano).
        data_dir = game / "data"
        if data_dir.is_dir():
            tyrano_scenario = data_dir / "scenario"
            tyrano_system = data_dir / "system"
            if tyrano_scenario.is_dir():
                # Tem data/scenario/ -> provavelmente Tyrano
                return False
            if tyrano_system.is_dir():
                # Tem data/system/ -> provavelmente Tyrano
                return False

        # Verifica Kirikiri: scenario/ na raiz com .ks
        scenario_dir = game / "scenario"
        if scenario_dir.is_dir():
            for ks in _find_ks_files(str(scenario_dir), max_depth=1):
                return True

        # Verifica Kirikiri: system/ na raiz com .tjs
        system_dir = game / "system"
        if system_dir.is_dir():
            for tjs in _find_tjs_files(str(system_dir), max_depth=1):
                return True

        # Tambem verifica .ks diretamente na raiz (alguns jogos)
        for ks in _find_ks_files(str(game), max_depth=1):
            rel = str(ks.relative_to(game)).replace("\\", "/").lower()
            if not rel.startswith("data/"):
                return True

        return False

    def extract(self, game_path: str) -> Iterator[TextEntry]:
        """Itera textos semanticos dos arquivos .ks."""
        for ks_path in _find_ks_files(game_path):
            # Pula arquivos dentro de data/ (Tyrano territory)
            rel_to_root = str(ks_path.relative_to(Path(game_path))).replace("\\", "/")
            if rel_to_root.lower().startswith("data/"):
                continue
            yield from self._extract_from_file(ks_path, game_path)

    def metadata(self, game_path: str) -> dict:
        """Devolve contagem de .ks excluindo os de data/ (Tyrano)."""
        ks_count = 0
        game = Path(game_path)
        for ks_path in _find_ks_files(game_path):
            rel_to_root = str(ks_path.relative_to(game)).replace("\\", "/")
            if not rel_to_root.lower().startswith("data/"):
                ks_count += 1
        return {"engine": "kirikiri", "ks_count": ks_count}

    # ------------------------------------------------------------------
    # parsing interno

    def _extract_from_file(self, ks_path, game_root):
        """Extrai textos de um unico arquivo .ks Kirikiri."""
        text, encoding = _read_text(ks_path)
        if text is None:
            return

        rel = str(ks_path.relative_to(Path(game_root))).replace("\\", "/")
        in_macro = False

        for line_no, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()

            # Ignora linhas vazias e comentarios.
            if not stripped or _COMMENT_RE.match(stripped):
                continue

            # Controle de macro: [macro] ... [endmacro]
            macro_close_match = _MACRO_CLOSE_RE.match(stripped)
            if macro_close_match:
                in_macro = False
                continue

            if in_macro:
                # Dentro de macro: extrai como kirikiri_macro
                # Pula tags de controle dentro do macro
                tag_match = _TAG_RE.match(stripped)
                if tag_match:
                    tag_name = tag_match.group(1).lower()
                    if _is_skip_tag(tag_name):
                        continue
                # Texto dentro do macro
                if not _TAG_RE.match(stripped):
                    yield TextEntry(
                        file=rel,
                        line=line_no,
                        source=stripped,
                        source_key="macro.%s.%d" % (rel, line_no),
                        category="kirikiri_macro",
                        context={},
                    )
                continue

            macro_open_match = _MACRO_OPEN_RE.match(stripped)
            if macro_open_match:
                in_macro = True
                continue

            # [eval exp="text = 'X'"] -> extrai X
            eval_match = _EVAL_TEXT_RE.match(stripped)
            if eval_match:
                body = eval_match.group(1).strip()
                if body:
                    yield TextEntry(
                        file=rel,
                        line=line_no,
                        source=body,
                        source_key="eval.%s.%d" % (rel, line_no),
                        category="kirikiri_eval",
                        context={"tag": "eval"},
                    )
                continue

            # [dialog text="X"]
            dialog_match = _DIALOG_RE.match(stripped)
            if dialog_match:
                body = dialog_match.group(1).strip()
                if body:
                    yield TextEntry(
                        file=rel,
                        line=line_no,
                        source=body,
                        source_key="dialog.%s.%d" % (rel, line_no),
                        category="kirikiri_dialog",
                        context={"tag": "dialog"},
                    )
                continue

            # Tags de controle -> skip
            tag_match = _TAG_RE.match(stripped)
            if tag_match:
                tag_name = tag_match.group(1).lower()
                if _is_skip_tag(tag_name):
                    continue
                # Outras tags nao reconhecidas tambem sao skip
                continue

            # Dialogue: qualquer texto que nao comeca com [ e nao e comentario.
            if stripped and not _TAG_RE.match(stripped):
                yield TextEntry(
                    file=rel,
                    line=line_no,
                    source=stripped,
                    source_key="dialogue.%s.%d" % (rel, line_no),
                    category="kirikiri_dialogue",
                    context={},
                )


# Registra o adapter automaticamente ao importar o modulo.
register_adapter("kirikiri", KirikiriAdapter())
