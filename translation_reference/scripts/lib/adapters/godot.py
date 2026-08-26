# -*- coding: utf-8 -*-
"""Adapter de extracao para a engine Godot (.tscn/.tres/.csv/.po/.json).

Componente da Fase 7 (adapters multi-engine) do TradutorDGames.

Detecta jogos Godot pela presenca de project.godot OU pasta translations/
com arquivos .po/.csv (max 3 niveis). Extrai textos semanticamente
significativos:

- TSCN/TRES: propriedades textuais em nos (text=, tooltip_text=, etc).
- CSV: colunas de idioma nao-inglesas em arquivos .csv de traducao.
- PO: pares msgid/msgstr de arquivos .po (gettext).
- JSON: strings com caracteres CJK/kana em .json.

Contrato
--------
- ``detect``: True quando game_path contem project.godot OU pasta
  translations/ com .po/.csv (busca limitada a 3 niveis).
- ``extract``: iterador de ``TextEntry`` com category sendo
  ``godot_tscn``, ``godot_csv``, ``godot_po`` ou ``godot_json``.
- ``metadata``: ``{"engine": "godot", "tscn_count": N, "csv_count": M,
  "po_count": K}``.

Somente biblioteca padrao. Mensagens em pt-BR sem acento.
"""

import json
import os
import re
from pathlib import Path
from typing import Iterator

try:
    from . import EngineAdapter, TextEntry, register_adapter
except ImportError:
    from __init__ import EngineAdapter, TextEntry, register_adapter

__all__ = ["GodotAdapter"]

# Limite de profundidade para busca em detect().
_MAX_DETECT_DEPTH = 3

# ---------------------------------------------------------------------------
# Padroes de parsing
# ---------------------------------------------------------------------------

# Propriedades textuais em .tscn/.tres.
# Captura: propriedade="valor" dentro de blocos [node ...].
_TSCN_TEXT_PROPS = re.compile(
    r"""(?P<prop>text|placeholder_text|tooltip_text|dialog_text|title)\s*=\s*(?P<quote>["'])(?P<body>(?:\\.|(?!\1).)*?)(?P=quote)"""
)

# Cabecalho de node em .tscn/.tres: [node name="X" type="Y" ...].
_NODE_HEADER_RE = re.compile(r"^\[node\b")

# Cabecalho de secao em .tscn/.tres: [section].
_SECTION_HEADER_RE = re.compile(r"^\[([^\]]+)\]")

# Comentario Godot comeca com ;.
_COMMENT_RE = re.compile(r"^\s*;")

# Para detectar CJK/kana em strings JSON.
_CJK_KANA_RE = re.compile(
    r"[\u2E80-\u9FFF\uF900-\uFAFF\uFE30-\uFE4F"
    r"\u3040-\u309F\u30A0-\u30FF\u31F0-\u31FF"
    r"\uAC00-\uD7AF\uFF00-\uFFEF]"
)


# ---------------------------------------------------------------------------
# Funcoes auxiliares
# ---------------------------------------------------------------------------

def _read_text(path):
    """Le arquivo tentando encoding comum; devolve (texto, encoding) ou (None, None)."""
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return None, None


def _find_files_by_ext(game_path, extensions, max_depth=_MAX_DETECT_DEPTH):
    """Busca recursiva por arquivos com extensoes dadas, com limite de profundidade."""
    root = Path(game_path)
    if not root.is_dir():
        return
    root_depth = len(root.parts)
    ext_lower = {e.lower() for e in extensions}
    for current, dirs, files in os.walk(root):
        depth = len(Path(current).parts) - root_depth
        if depth >= max_depth:
            dirs.clear()
            continue
        for name in files:
            if Path(name).suffix.lower() in ext_lower:
                yield Path(current) / name


def _find_tscn_files(game_path, max_depth=_MAX_DETECT_DEPTH):
    """Busca recursiva por .tscn/.tres com limite de profundidade."""
    return _find_files_by_ext(game_path, (".tscn", ".tres"), max_depth)


def _find_csv_files(game_path, max_depth=_MAX_DETECT_DEPTH):
    """Busca recursiva por .csv com limite de profundidade."""
    return _find_files_by_ext(game_path, (".csv",), max_depth)


def _find_po_files(game_path, max_depth=_MAX_DETECT_DEPTH):
    """Busca recursiva por .po com limite de profundidade."""
    return _find_files_by_ext(game_path, (".po",), max_depth)


def _find_json_files(game_path, max_depth=_MAX_DETECT_DEPTH):
    """Busca recursiva por .json com limite de profundidade."""
    return _find_files_by_ext(game_path, (".json",), max_depth)


def _has_project_godot(game_path, max_depth=_MAX_DETECT_DEPTH):
    """Verifica se project.godot existe em game_path ou subpastas (max 3 niveis)."""
    root = Path(game_path)
    if not root.is_dir():
        return False
    root_depth = len(root.parts)
    for current, dirs, files in os.walk(root):
        depth = len(Path(current).parts) - root_depth
        if depth >= max_depth:
            dirs.clear()
            continue
        if "project.godot" in files:
            return True
    return False


def _has_translations_dir(game_path, max_depth=_MAX_DETECT_DEPTH):
    """Verifica se existe pasta translations/ com .po/.csv (max 3 niveis)."""
    root = Path(game_path)
    if not root.is_dir():
        return False
    root_depth = len(root.parts)
    for current, dirs, files in os.walk(root):
        depth = len(Path(current).parts) - root_depth
        if depth >= max_depth:
            dirs.clear()
            continue
        dir_name = Path(current).name.lower()
        if dir_name == "translations":
            for f in files:
                if f.lower().endswith((".po", ".csv")):
                    return True
    return False


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class GodotAdapter(EngineAdapter):
    """Adapter para jogos Godot (.tscn/.tres/.csv/.po/.json)."""

    @property
    def validator(self):
        """Devolve o validador GodotValidator para esta engine."""
        try:
            from ..validators.godot_val import GodotValidator
        except ImportError:
            from validators.godot_val import GodotValidator
        return GodotValidator()

    def detect(self, game_path: str) -> bool:
        """True se game_path contiver project.godot OU translations/ com .po/.csv."""
        if _has_project_godot(game_path):
            return True
        return _has_translations_dir(game_path)

    def extract(self, game_path: str) -> Iterator[TextEntry]:
        """Itera textos semanticos dos arquivos Godot."""
        yield from self._extract_tscn(game_path)
        yield from self._extract_csv(game_path)
        yield from self._extract_po(game_path)
        yield from self._extract_json(game_path)

    def metadata(self, game_path: str) -> dict:
        """Devolve contagem de arquivos por tipo."""
        tscn_count = sum(1 for _ in _find_tscn_files(game_path))
        csv_count = sum(1 for _ in _find_csv_files(game_path))
        po_count = sum(1 for _ in _find_po_files(game_path))
        return {
            "engine": "godot",
            "tscn_count": tscn_count,
            "csv_count": csv_count,
            "po_count": po_count,
        }

    # ------------------------------------------------------------------
    # Sub-extractors
    # ------------------------------------------------------------------

    def _extract_tscn(self, game_path):
        """Extrai propriedades textuais de .tscn/.tres."""
        for tscn_path in _find_tscn_files(game_path):
            text, encoding = _read_text(tscn_path)
            if text is None:
                continue
            rel = str(tscn_path.relative_to(Path(game_path))).replace("\\", "/")
            in_node = False
            for line_no, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                # Ignora comentarios e linhas vazias.
                if not stripped or _COMMENT_RE.match(stripped):
                    continue
                # Detecta cabecalho de node.
                if _NODE_HEADER_RE.match(stripped):
                    in_node = True
                    continue
                # Detecta nova secao que nao e node.
                sec_match = _SECTION_HEADER_RE.match(stripped)
                if sec_match:
                    in_node = False
                    continue
                # Extrai propriedades textuais dentro de nodes.
                if in_node:
                    for m in _TSCN_TEXT_PROPS.finditer(stripped):
                        body = m.group("body")
                        if not body.strip():
                            continue
                        prop = m.group("prop")
                        yield TextEntry(
                            file=rel,
                            line=line_no,
                            source=body,
                            source_key="%s.%s.%d" % (prop, rel, line_no),
                            category="godot_tscn",
                            context={"property": prop, "node_file": rel},
                        )

    def _extract_csv(self, game_path):
        """Extrai textos de arquivos .csv de traducao Godot.

        Formato CSV do Godot:
        - Primeira linha: cabecalho com 'key' + colunas de idioma.
        - Colunas de idioma sao todas exceto 'key'.
        - Valores em colunas nao-inglesas sao extraidos.
        """
        for csv_path in _find_csv_files(game_path):
            text, encoding = _read_text(csv_path)
            if text is None:
                continue
            rel = str(csv_path.relative_to(Path(game_path))).replace("\\", "/")
            lines = text.splitlines()
            if not lines:
                continue
            # Parse cabecalho.
            header = self._parse_csv_line(lines[0])
            if not header:
                continue
            # Identifica colunas de idioma (todas exceto 'key').
            lang_cols = []
            for i, col in enumerate(header):
                col_stripped = col.strip().lower()
                if col_stripped != "key" and col_stripped != "":
                    lang_cols.append((i, col.strip()))
            # Itera linhas de dados.
            for line_no, line in enumerate(lines[1:], 2):
                if not line.strip() or _COMMENT_RE.match(line):
                    continue
                cells = self._parse_csv_line(line)
                if not cells:
                    continue
                key_val = cells[0].strip() if cells else ""
                for col_idx, lang_name in lang_cols:
                    if col_idx < len(cells):
                        val = cells[col_idx].strip()
                        if val and not self._is_english_only(val):
                            yield TextEntry(
                                file=rel,
                                line=line_no,
                                source=val,
                                source_key="csv.%s.%s" % (key_val, lang_name),
                                category="godot_csv",
                                context={
                                    "key": key_val,
                                    "language": lang_name,
                                },
                            )

    def _extract_po(self, game_path):
        """Extrai pares msgid/msgstr de arquivos .po.

        Parsing minimo: le bloco msgid/msgstr e emite quando msgstr
        contem texto traduzivel (nao vazio e diferente de msgid).
        """
        for po_path in _find_po_files(game_path):
            text, encoding = _read_text(po_path)
            if text is None:
                continue
            rel = str(po_path.relative_to(Path(game_path))).replace("\\", "/")
            lines = text.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                # Procura msgid.
                if line.startswith("msgid "):
                    msgid_val = self._extract_po_string(lines, i)
                    # Procura msgstr na proxima linha ou mais abaixo.
                    msgstr_val = ""
                    j = i + 1
                    while j < len(lines):
                        sline = lines[j].strip()
                        if sline.startswith("msgstr "):
                            msgstr_val = self._extract_po_string(lines, j)
                            break
                        if sline.startswith("msgid ") or sline.startswith("#"):
                            break
                        j += 1
                    # Emite se msgstr tem texto e e diferente de msgid.
                    if (
                        msgstr_val
                        and msgstr_val != msgid_val
                        and msgid_val
                    ):
                        yield TextEntry(
                            file=rel,
                            line=i + 1,
                            source=msgstr_val,
                            source_key="po.%s.%d" % (rel, i + 1),
                            category="godot_po",
                            context={"msgid": msgid_val},
                        )
                i += 1

    def _extract_json(self, game_path):
        """Extrai strings com CJK/kana de arquivos .json."""
        for json_path in _find_json_files(game_path):
            text, encoding = _read_text(json_path)
            if text is None:
                continue
            rel = str(json_path.relative_to(Path(game_path))).replace("\\", "/")
            try:
                data = json.loads(text)
            except (json.JSONDecodeError, ValueError):
                continue
            yield from self._walk_json(data, rel, "")

    def _walk_json(self, obj, rel, path_prefix):
        """Caminha recursivamente em objetos JSON buscando strings CJK/kana."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = "%s.%s" % (path_prefix, key) if path_prefix else key
                yield from self._walk_json(value, rel, new_path)
        elif isinstance(obj, list):
            for idx, value in enumerate(obj):
                new_path = "%s[%d]" % (path_prefix, idx)
                yield from self._walk_json(value, rel, new_path)
        elif isinstance(obj, str) and obj.strip() and _CJK_KANA_RE.search(obj):
            yield TextEntry(
                file=rel,
                line=0,  # JSON nao tem numero de linha preciso.
                source=obj,
                source_key="json.%s" % path_prefix,
                category="godot_json",
                context={"json_path": path_prefix},
            )

    # ------------------------------------------------------------------
    # Utilitarios
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_csv_line(line):
        """Parse simples de linha CSV (sem aspas complexas)."""
        result = []
        current = []
        in_quotes = False
        for ch in line:
            if ch == '"':
                in_quotes = not in_quotes
            elif ch == "," and not in_quotes:
                result.append("".join(current))
                current = []
            else:
                current.append(ch)
        result.append("".join(current))
        return result

    @staticmethod
    def _extract_po_string(lines, line_idx):
        """Extrai o valor de uma linha msgid/msgstr, incluindo continuacoes."""
        line = lines[line_idx].strip()
        # Separa prefixo e valor entre aspas.
        if " " in line:
            prefix_end = line.index(" ")
            value_part = line[prefix_end + 1 :]
        else:
            value_part = ""
        # Remove aspas.
        val = value_part.strip().strip('"')
        # Verifica continuacoes: linhas seguintes com "...".
        j = line_idx + 1
        while j < len(lines):
            cont = lines[j].strip()
            if cont.startswith('"') and cont.endswith('"'):
                val += cont[1:-1]
                j += 1
            else:
                break
        return val

    @staticmethod
    def _is_english_only(text):
        """Verifica se o texto e puramente ASCII/ingles (sem caracteres exoticos)."""
        # Se contem apenas ASCII imprimivel, tratamos como ingles.
        try:
            text.encode("ascii")
            return True
        except UnicodeEncodeError:
            return False


# Registra o adapter automaticamente ao importar o modulo.
register_adapter("godot", GodotAdapter())
