# -*- coding: utf-8 -*-
"""Adapter de extracao para a engine Ren'Py (.rpy).

Componente da Fase 7 (adapters multi-engine) do TradutorDGames.

Detecta jogos Ren'Py pela presenca de arquivos .rpy e extrai textos
semanticamente significativos:

- Dialogue: blocos ``label`` com strings entre aspas simples ou duplas.
- Menu items: itens de ``menu:`` com texto seguido de ``:``.
- Strings em variaveis: ``$ var = "texto"``.
- Translate blocks: ``translate ... blocks`` com pares old/new.

Contrato
--------
- ``detect``: True quando existem .rpy no maximo 3 niveis abaixo de
  game_path (busca recursiva limitada).
- ``extract``: iterador de ``TextEntry`` com category sendo
  ``renpy_dialogue``, ``renpy_menu``, ``renpy_variable`` ou
  ``renpy_translate``.
- ``metadata``: ``{"engine": "renpy", "rpy_count": N, "label_count": M}``.

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

__all__ = ["RenPyAdapter"]

# Limite de profundidade para busca de .rpy em detect().
_MAX_DETECT_DEPTH = 3

# Padroes de parsing de .rpy ------------------------------------------------

# Label: "label start:" ou "label chapter1:"
_LABEL_RE = re.compile(r"^\s*label\s+(\w+)\s*:")

# Dialogue entre aspas: "texto" ou 'texto' (fora de comentarios/imports).
# Captura strings que comecam no inicio do conteudo da linha ou apos espaco.
_QUOTED_STRING_RE = re.compile(r"""(?P<quote>["'])(?P<body>(?:\\.|(?!\1).)*?)(?P=quote)""")

# Menu item: texto seguido de ":" dentro de um bloco menu.
_MENU_ITEM_RE = re.compile(r"^\s+(?!\w+:)(?!\$)(?!\"|\')(.+?)\s*:\s*$")

# Variavel com string: $ var = "texto" ou $ var = 'texto'.
_VARIABLE_RE = re.compile(r"^\s*\$\s*\w+\s*=\s*(?P<quote>[\"'])(?P<body>(?:\\.|(?!\1).)*?)(?P=quote)")

# Translate block: "translate portuguese start:" ou "translate english label start:".
_TRANSLATE_HEADER_RE = re.compile(r"^\s*translate\s+(\S+)\s+(.+?)\s*:")

# Pares old/new dentro de translate.
_OLD_NEW_RE = re.compile(r"^\s*(?:old|new)\s+(?P<quote>[\"'])(?P<body>(?:\\.|(?!\1).)*?)(?P=quote)")

# Identificador de linhas de comentario.
_COMMENT_RE = re.compile(r"^\s*#")


def _read_text(path):
    """Le arquivo tentando encoding comum; devolve (texto, encoding) ou (None, None)."""
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "cp932", "shift_jis", "utf-16", "latin-1"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return None, None


def _find_rpy_files(game_path, max_depth=_MAX_DETECT_DEPTH):
    """Busca recursiva por .rpy com limite de profundidade."""
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
            if name.lower().endswith(".rpy"):
                yield Path(current) / name


class RenPyAdapter(EngineAdapter):
    """Adapter para jogos Ren'Py (.rpy)."""

    @property
    def validator(self):
        """Devolve o validador RenPyValidator para esta engine."""
        try:
            from ..validators.renpy_val import RenPyValidator
        except ImportError:
            from validators.renpy_val import RenPyValidator
        return RenPyValidator()

    def detect(self, game_path: str) -> bool:
        """True se game_path contiver .rpy files (max 3 niveis)."""
        count = 0
        for _rpy in _find_rpy_files(game_path):
            count += 1
            if count >= 1:
                return True
        return False

    def extract(self, game_path: str) -> Iterator[TextEntry]:
        """Itera textos semanticos dos arquivos .rpy."""
        for rpy_path in _find_rpy_files(game_path):
            yield from self._extract_from_file(rpy_path, game_path)

    def metadata(self, game_path: str) -> dict:
        """Devolve contagem de .rpy e labels."""
        rpy_count = 0
        label_count = 0
        for rpy_path in _find_rpy_files(game_path):
            rpy_count += 1
            text, _enc = _read_text(rpy_path)
            if text:
                for line in text.splitlines():
                    if _LABEL_RE.match(line):
                        label_count += 1
        return {"engine": "renpy", "rpy_count": rpy_count, "label_count": label_count}

    # ------------------------------------------------------------------
    # parsing interno

    def _extract_from_file(self, rpy_path, game_root):
        """Extrai textos de um unico arquivo .rpy."""
        text, encoding = _read_text(rpy_path)
        if text is None:
            return

        rel = str(rpy_path.relative_to(Path(game_root))).replace("\\", "/")
        current_label = None
        in_translate = False
        translate_lang = None

        for line_no, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()

            # Ignora linhas vazias e comentarios.
            if not stripped or _COMMENT_RE.match(stripped):
                continue

            # Detecta inicio de label.
            label_match = _LABEL_RE.match(line)
            if label_match:
                current_label = label_match.group(1)
                in_translate = False
                continue

            # Detecta translate block.
            tr_match = _TRANSLATE_HEADER_RE.match(line)
            if tr_match:
                in_translate = True
                translate_lang = tr_match.group(1)
                current_label = tr_match.group(2)
                continue

            # Pares old/new dentro de translate.
            if in_translate:
                on_match = _OLD_NEW_RE.match(stripped)
                if on_match:
                    body = on_match.group("body")
                    is_old = stripped.startswith("old")
                    yield TextEntry(
                        file=rel,
                        line=line_no,
                        source=body,
                        source_key="translate.%s.%s.%s" % (
                            translate_lang, current_label, "old" if is_old else "new"
                        ),
                        category="renpy_translate",
                        context={"label": current_label, "lang": translate_lang},
                    )
                # Translate block termina quando encontramos uma nova label
                # ou outro construct de nivel superior.
                if not stripped.startswith(("old", "new")) and _LABEL_RE.match(line):
                    in_translate = False
                continue

            # Strings em variaveis: $ var = "texto".
            var_match = _VARIABLE_RE.match(line)
            if var_match:
                body = var_match.group("body")
                if body.strip():
                    yield TextEntry(
                        file=rel,
                        line=line_no,
                        source=body,
                        source_key="var.%s" % current_label,
                        category="renpy_variable",
                        context={"label": current_label},
                    )
                continue

            # Menu items: "  Opcao um:" -> texto = "Opcao um".
            menu_match = _MENU_ITEM_RE.match(line)
            if menu_match and current_label:
                body = menu_match.group(1).strip()
                if body:
                    yield TextEntry(
                        file=rel,
                        line=line_no,
                        source=body,
                        source_key="menu.%s.%d" % (current_label, line_no),
                        category="renpy_menu",
                        context={"label": current_label},
                    )
                continue

            # Dialogue: "Bom dia, mundo!" ou 'Olá'.
            quote_match = _QUOTED_STRING_RE.search(stripped)
            if quote_match and current_label:
                body = quote_match.group("body")
                # Filtra strings que sao puramente codigo/marcacao.
                if body.strip() and not body.strip().startswith(("{", "[", "//")):
                    yield TextEntry(
                        file=rel,
                        line=line_no,
                        source=body,
                        source_key="dialogue.%s.%d" % (current_label, line_no),
                        category="renpy_dialogue",
                        context={"label": current_label},
                    )


# Registra o adapter automaticamente ao importar o modulo.
register_adapter("renpy", RenPyAdapter())
