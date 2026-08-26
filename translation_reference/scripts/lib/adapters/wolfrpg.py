# -*- coding: utf-8 -*-
"""Adapter de extracao para a engine Wolf RPG Editor (.mps / .dat).

Componente da Fase 7 (adapters multi-engine) do TradutorDGames.

Detecta jogos Wolf RPG (ja descompactados) pela presenca de arquivos
.mps em scenario/ OU arquivos .dat na raiz (max 3 niveis), desde que
nao se encaixe na estrutura Tyrano/Kirikiri (.ks em data/scenario/).

Extrai textos por heuristica binaria: varredura linear procurando
strings length-prefixed (2 bytes LE + bytes Shift-JIS ou UTF-8).
Filtragem por presenca de caracteres CJK/kana.

Contrato
--------
- ``detect``: True quando existem .mps em scenario/ OU .dat na raiz
  (max 3 niveis), E NAO existe estrutura Tyrano/Kirikiri.
- ``extract``: iterador de ``TextEntry`` com category sendo
  ``wolfrpg_dialogue`` ou ``wolfrpg_system``.
- ``metadata``: ``{"engine": "wolfrpg", "mps_count": N, "dat_count": M}``.

Somente biblioteca padrao. Mensagens em pt-BR sem acento.
"""

import os
import struct
from pathlib import Path
from typing import Iterator, List, Tuple

try:
    from . import EngineAdapter, TextEntry, register_adapter
except ImportError:
    from __init__ import EngineAdapter, TextEntry, register_adapter

__all__ = ["WolfRPGAdapter"]

# Limite de profundidade para busca em detect().
_MAX_DETECT_DEPTH = 3

# Tamanho minimo para considerar um arquivo ao varrer binarios.
_MIN_FILE_SIZE = 16


# ---------------------------------------------------------------------------
# Funcoes auxiliares: leitura de strings binarias
# ---------------------------------------------------------------------------

def _has_cjk_or_kana(text: str) -> bool:
    """Verifica se o texto contem caracteres CJK, hiragana ou katakana."""
    for ch in text:
        cp = ord(ch)
        # Hiragana: U+3040..U+309F
        if 0x3040 <= cp <= 0x309F:
            return True
        # Katakana: U+30A0..U+30FF
        if 0x30A0 <= cp <= 0x30FF:
            return True
        # CJK Unified: U+4E00..U+9FFF
        if 0x4E00 <= cp <= 0x9FFF:
            return True
        # CJK Extension A: U+3400..U+4DBF
        if 0x3400 <= cp <= 0x4DBF:
            return True
    return False


def _read_shiftjis_string(data: bytes, offset: int) -> Tuple[str, int]:
    """Le uma string length-prefixed (2 bytes LE + bytes).

    Tenta decodificar como Shift-JIS (cp932) primeiro, fallback UTF-8.
    Devolve (string, novo_offset) ou ('', offset) se falhar.
    """
    if offset + 2 > len(data):
        return '', offset
    length = struct.unpack_from('<H', data, offset)[0]
    if length == 0 or offset + 2 + length > len(data):
        return '', offset
    raw = data[offset + 2:offset + 2 + length]
    # Tenta cp932 (superset de Shift-JIS) primeiro
    for enc in ('cp932', 'shift_jis', 'utf-8'):
        try:
            s = raw.decode(enc)
            return s, offset + 2 + length
        except (UnicodeDecodeError, LookupError):
            continue
    return '', offset + 2 + length


def _extract_strings_from_binary(data: bytes) -> List[Tuple[str, int]]:
    """Varredura binaria procurando strings length-prefixed.

    Procura padroes [2 bytes LE length][bytes] e devolve lista de
    (string, offset) com strings que contenham CJK/kana e tenham >= 2 chars.
    """
    results = []
    pos = 0
    data_len = len(data)
    while pos < data_len - 2:
        length = struct.unpack_from('<H', data, pos)[0]
        if 2 <= length <= 1000 and pos + 2 + length <= data_len:
            raw = data[pos + 2:pos + 2 + length]
            # Tenta decodificar
            decoded = None
            for enc in ('cp932', 'shift_jis', 'utf-8'):
                try:
                    decoded = raw.decode(enc)
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            if decoded is not None and len(decoded) >= 2:
                if _has_cjk_or_kana(decoded):
                    results.append((decoded, pos))
            pos += 2 + length
        else:
            pos += 1
    return results


# ---------------------------------------------------------------------------
# Busca de arquivos
# ---------------------------------------------------------------------------

def _find_mps_files(game_path: str, max_depth: int = _MAX_DETECT_DEPTH) -> List[Path]:
    """Busca recursiva por .mps com limite de profundidade."""
    root = Path(game_path)
    if not root.is_dir():
        return []
    found = []
    root_depth = len(root.parts)
    for current, dirs, files in os.walk(root):
        depth = len(Path(current).parts) - root_depth
        if depth >= max_depth:
            dirs.clear()
            continue
        for name in files:
            if name.lower().endswith('.mps'):
                found.append(Path(current) / name)
    return found


def _find_dat_files(game_path: str, max_depth: int = _MAX_DETECT_DEPTH) -> List[Path]:
    """Busca recursiva por .dat com limite de profundidade."""
    root = Path(game_path)
    if not root.is_dir():
        return []
    found = []
    root_depth = len(root.parts)
    for current, dirs, files in os.walk(root):
        depth = len(Path(current).parts) - root_depth
        if depth >= max_depth:
            dirs.clear()
            continue
        for name in files:
            if name.lower().endswith('.dat'):
                found.append(Path(current) / name)
    return found


def _is_tyrano_or_kirikiri(game_path: str) -> bool:
    """Verifica se game_path tem estrutura Tyrano/Kirikiri (conflito)."""
    game = Path(game_path)
    data_dir = game / "data"
    if data_dir.is_dir():
        if (data_dir / "scenario").is_dir():
            return True
        if (data_dir / "system").is_dir():
            return True
    return False


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class WolfRPGAdapter(EngineAdapter):
    """Adapter para jogos Wolf RPG Editor (.mps / .dat)."""

    def detect(self, game_path: str) -> bool:
        """True se game_path contiver .mps em scenario/ ou .dat na raiz,
        E NAO se encaixar na estrutura Tyrano/Kirikiri."""
        game = Path(game_path)
        if not game.is_dir():
            return False

        # Rejeita estrutura Tyrano/Kirikiri
        if _is_tyrano_or_kirikiri(game_path):
            return False

        # Verifica .mps em scenario/
        scenario_dir = game / "scenario"
        if scenario_dir.is_dir():
            for f in os.listdir(scenario_dir):
                if f.lower().endswith('.mps'):
                    return True

        # Verifica .dat na raiz (max 3 niveis)
        dat_files = _find_dat_files(game_path, max_depth=_MAX_DETECT_DEPTH)
        if dat_files:
            return True

        return False

    def extract(self, game_path: str) -> Iterator[TextEntry]:
        """Itera textos dos arquivos .mps e .dat por heuristica binaria."""
        # .mps files
        for mps_path in _find_mps_files(game_path):
            yield from self._extract_from_binary_file(mps_path, game_path, "wolfrpg_dialogue")
        # .dat files
        for dat_path in _find_dat_files(game_path):
            yield from self._extract_from_binary_file(dat_path, game_path, "wolfrpg_system")

    def metadata(self, game_path: str) -> dict:
        """Devolve contagem de .mps e .dat."""
        mps_count = len(_find_mps_files(game_path))
        dat_count = len(_find_dat_files(game_path))
        return {"engine": "wolfrpg", "mps_count": mps_count, "dat_count": dat_count}

    # ------------------------------------------------------------------
    # parsing interno

    def _extract_from_binary_file(self, file_path: Path, game_root: str, category: str):
        """Extrai textos de um arquivo binario (.mps ou .dat)."""
        try:
            data = file_path.read_bytes()
        except (OSError, IOError):
            return

        if len(data) < _MIN_FILE_SIZE:
            return

        rel = str(file_path.relative_to(Path(game_root))).replace("\\", "/")
        strings = _extract_strings_from_binary(data)

        for idx, (text, offset) in enumerate(strings):
            # source_key usa offset como identificador unico dentro do arquivo
            source_key = "%s.%s.%d" % (category, rel, offset)
            yield TextEntry(
                file=rel,
                line=offset,
                source=text,
                source_key=source_key,
                category=category,
                context={"encoding": "shift_jis", "offset": offset},
            )


# Registra o adapter automaticamente ao importar o modulo.
register_adapter("wolfrpg", WolfRPGAdapter())
