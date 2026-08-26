# -*- coding: utf-8 -*-
"""Adapter de extracao para RPG Maker VX/Ace (.rvdata2).

Componente da Fase 7 (adapters multi-engine) do TradutorDGames.

Detecta jogos RPG Maker VX/Ace pela presenca de arquivos .rvdata2
ou .rvdata no diretorio data/ (busca recursiva limitada a 3 niveis).
Extrai textos semanticamente significativos:

- Database: nomes, descricoes, notas de atores, itens, armas, armaduras,
  habilidades, estados, inimigos, classes.
- System: vocabulary (termos do jogo), nomes de elementos, tipos.
- Mapas: dialogos (code 401/405), escolhas (code 102).
- Common Events: dialogos e escolhas.

Contrato
--------
- ``detect``: True quando existem .rvdata2/.rvdata em ate 3 niveis.
- ``extract``: iterador de ``TextEntry`` com category sendo
  ``rpgmaker_database``, ``rpgmaker_system``, ``rpgmaker_map`` ou
  ``rpgmaker_common``.
- ``metadata``: ``{"engine": "rpgmaker_vxace", "rvdata_count": N}``.

Somente biblioteca padrao. Mensagens em pt-BR sem acento.
"""

import os
import struct
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

try:
    from . import EngineAdapter, TextEntry, register_adapter
except ImportError:
    from __init__ import EngineAdapter, TextEntry, register_adapter

__all__ = ["RubyMarshalReader", "VXAceAdapter"]

# Limite de profundidade para busca em detect().
_MAX_DETECT_DEPTH = 3


# ---------------------------------------------------------------------------
# Ruby Marshal Reader (v4.8)
# ---------------------------------------------------------------------------

class RubyMarshalReader:
    """Leitor minimalista de arquivos Ruby Marshal v4.8.

    Suporta os type codes necessarios para ler dados RPG Maker VX/Ace:
    strings, fixnums, arrays, hashes, objects, ivars, symbols, symlinks,
    links (refs), bools e nil.
    """

    def __init__(self, data: bytes):
        self._data = data
        self._pos = 0
        self._symbols: List[str] = []
        self._objects: List[Any] = []

    # -- leitura de bytes brutos ------------------------------------------

    def _read(self, n: int) -> bytes:
        """Le n bytes do buffer. Levanta EOFError se insuficiente."""
        end = self._pos + n
        if end > len(self._data):
            raise EOFError(
                "fim dos dados ao ler %d bytes na posicao %d" % (n, self._pos)
            )
        chunk = self._data[self._pos:end]
        self._pos = end
        return chunk

    def _read_byte(self) -> int:
        """Le 1 byte e devolve como inteiro unsigned."""
        return self._read(1)[0]

    # -- fixnum (inteiro compacto) ----------------------------------------

    def _read_fixnum(self) -> int:
        """Le um fixnum Marshal (type code 'i' ja consumido).

        Codificacao:
        - 0: valor 0, sem bytes adicionais
        - 1 a 4: positivo, N bytes unsigned little-endian seguem
        - -1 a -4: negativo, |N| bytes unsigned LE seguem, resultado = ~raw
        - >= 5: valor = lead - 5 (sem bytes extras)
        - <= -5: valor = lead + 5 (sem bytes extras)
        """
        lead = struct.unpack("b", self._read(1))[0]  # signed byte
        if lead == 0:
            return 0
        if 1 <= lead <= 4:
            raw = int.from_bytes(self._read(lead), byteorder="little")
            return raw
        if -4 <= lead <= -1:
            n = -lead
            raw = int.from_bytes(self._read(n), byteorder="little")
            # reconstrucao negativa: complemento a partir de -1
            # equivalente ao que o Ruby faz: start = -1, clear+set byte a byte
            mask = (1 << (8 * n)) - 1
            return (raw | ~mask) if raw & (1 << (8 * n - 1)) else raw
        # valores fora do range -4..4
        if lead > 0:
            return lead - 5
        return lead + 5

    # -- bignum -----------------------------------------------------------

    def _read_bignum(self) -> int:
        """Le um bignum Marshal (type code 'l' ja consumido)."""
        sign = self._read(1)
        n = self._read_fixnum()  # numero de words de 2 bytes
        raw = int.from_bytes(self._read(n * 2), byteorder="little")
        if sign == b"-":
            raw = -raw
        return raw

    # -- string -----------------------------------------------------------

    def _read_string_raw(self) -> str:
        """Le uma string crua (type code '\"' ja consumido).

        Para strings simples, devolve bytes decodificados.
        """
        size = self._read_fixnum()
        raw = self._read(size)
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("latin-1", errors="replace")

    # -- symbol / symlink -------------------------------------------------

    def _read_symbol(self) -> str:
        """Le um symbol (type code ':' ja consumido) e armazena na tabela."""
        size = self._read_fixnum()
        s = self._read(size).decode("utf-8", errors="replace")
        self._symbols.append(s)
        return s

    def _read_symlink(self) -> str:
        """Le uma referencia a symbol ja lido (type code ';' ja consumido)."""
        idx = self._read_fixnum()
        return self._symbols[idx]

    # -- instance variables dict (usado por I, o, S) ----------------------

    def _read_ivar_dict(self) -> dict:
        """Le o dicionario de instance variables.

        Formato: fixnum(count) + symbol(key) + value pairs.
        Usado por TYPE_IVAR ('I'), TYPE_OBJECT ('o') e TYPE_STRUCT ('S').
        """
        n = self._read_fixnum()
        d = {}
        for _ in range(n):
            key = self._read_value()  # symbol
            val = self._read_value()
            d[key] = val
        return d

    # -- leitura generica de objeto ----------------------------------------

    def read_obj(self) -> Any:
        """Le um objeto Marshal do buffer.

        Devolve o objeto Python equivalente. Tipos suportados:
        - T/F -> bool
        - 0 -> None
        - i -> int
        - l -> int (bignum)
        - " -> str (wrapper de bytes com tamanho)
        - : -> str (symbol, internado)
        - ; -> str (symlink a symbol)
        - [ -> list
        - { -> dict (chaves e valores sao objetos lidos recursivamente)
        - } -> dict com valor padrao
        - I -> str/objeto com instance variables (wrapper para encoding)
        - o -> dict {__class__: ..., __dict__: {...}}
        - S -> dict {__class__: ..., __dict__: {...}} (struct)
        - @ -> referencia a objeto ja lido
        - f -> float
        - d -> dict (Data wrapper)
        - c/m -> dict (ClassRef/ModuleRef)
        - e -> dict (Extended)
        - u -> dict (UserDef)
        - U -> dict (UsrMarshal)
        - / -> dict (Regexp)
        """
        return self._read_value()

    def _read_value(self) -> Any:
        """Le um valor Marshal recursivamente."""
        type_code = bytes([self._read_byte()])

        # -- tipos simples ------------------------------------------------
        if type_code == b"T":
            return True
        if type_code == b"F":
            return False
        if type_code == b"0":
            return None

        # -- inteiros -----------------------------------------------------
        if type_code == b"i":
            return self._read_fixnum()
        if type_code == b"l":
            return self._read_bignum()

        # -- float --------------------------------------------------------
        if type_code == b"f":
            size = self._read_fixnum()
            raw = self._read(size)
            s = raw.split(b"\x00", 1)[0].decode("ascii")
            if s == "inf":
                return float("inf")
            if s == "-inf":
                return float("-inf")
            if s == "nan":
                return float("nan")
            return float(s)

        # -- symbols ------------------------------------------------------
        if type_code == b":":
            return self._read_symbol()
        if type_code == b";":
            return self._read_symlink()

        # -- string crua --------------------------------------------------
        if type_code == b'"':
            return self._read_string_raw()

        # -- array --------------------------------------------------------
        if type_code == b"[":
            n = self._read_fixnum()
            return [self._read_value() for _ in range(n)]

        # -- hash ---------------------------------------------------------
        if type_code == b"{":
            n = self._read_fixnum()
            d = {}
            for _ in range(n):
                k = self._read_value()
                v = self._read_value()
                d[k] = v
            return d

        # -- hash com valor padrao ----------------------------------------
        if type_code == b"}":
            n = self._read_fixnum()
            d = {}
            for _ in range(n):
                k = self._read_value()
                v = self._read_value()
                d[k] = v
            # valor padrao
            _default = self._read_value()
            return d

        # -- referencia a objeto ------------------------------------------
        if type_code == b"@":
            idx = self._read_fixnum()
            return self._objects[idx]

        # -- complexos: salva placeholder, le, atribui --------------------
        idx = len(self._objects)
        self._objects.append(None)  # placeholder para refs circulares

        if type_code == b"I":
            # IVar: wrapper com instance variables
            inner = self._read_value()
            # instance variables: fixnum(count) + symbol(key) + value pairs
            ivars = self._read_ivar_dict()
            # Se for string (ja decodificada por _read_string_raw) com
            # E:true nas ivars, devolve a string diretamente
            if isinstance(inner, str):
                self._objects[idx] = inner
                return inner
            # Se for Object/Struct (dict com __class__), transfere os ivars
            # para o __dict__ do objeto e devolve o objeto diretamente
            if isinstance(inner, dict) and "__class__" in inner:
                inner_dict = inner.get("__dict__", {})
                # Merge ivars no __dict__ (ivars do wrapper IVar
                # normalmente contem encoding E:true, mas tambem pode
                # conter atributos adicionais)
                for k, v in ivars.items():
                    if k != "E":  # ignora tag de encoding
                        inner_dict[k] = v
                self._objects[idx] = inner
                return inner
            # Dict com type=="Bytes" (formato raw do xi reader)
            if isinstance(inner, dict) and inner.get("type") == "Bytes":
                import base64
                raw = base64.b64decode(inner["value"])
                try:
                    result = raw.decode("utf-8")
                except UnicodeDecodeError:
                    result = raw.decode("latin-1", errors="replace")
                self._objects[idx] = result
                return result
            # Caso contrario, retorna dict com instance vars
            result = {"_value": inner, "_ivars": ivars}
            self._objects[idx] = result
            return result

        if type_code == b"o" or type_code == b"S":
            # Object / Struct: symbol(class_name) + ivar_dict
            class_name = self._read_value()
            data = self._read_ivar_dict()
            result = {"__class__": class_name, "__dict__": data}
            self._objects[idx] = result
            return result

        if type_code == b"d":
            # Data wrapper
            class_name = self._read_value()
            data = self._read_value()
            result = {"__class__": class_name, "__data__": data}
            self._objects[idx] = result
            return result

        if type_code in (b"c", b"m"):
            # ClassRef / ModuleRef
            _name = self._read_value()
            result = {"__type__": "ClassRef" if type_code == b"c" else "ModuleRef"}
            self._objects[idx] = result
            return result

        if type_code == b"e":
            # Extended
            obj = self._read_value()
            _mod = self._read_value()
            result = {"__extended__": obj}
            self._objects[idx] = result
            return result

        if type_code == b"u":
            # UserDefined
            name = self._read_value()
            size = self._read_fixnum()
            raw = self._read(size)
            result = {"__userdef__": name, "__bytes__": raw.hex()}
            self._objects[idx] = result
            return result

        if type_code == b"U":
            # UsrMarshal
            name = self._read_value()
            data = self._read_value()
            result = {"__usrmarshal__": name, "__data__": data}
            self._objects[idx] = result
            return result

        if type_code == b"/":
            # Regexp
            size = self._read_fixnum()
            _pattern = self._read(size)
            _opts = self._read_byte()
            result = {"__type__": "Regexp"}
            self._objects[idx] = result
            return result

        raise ValueError(
            "type code desconhecido: %r na posicao %d" % (type_code, self._pos - 1)
        )

    # -- API publica ------------------------------------------------------

    @classmethod
    def loads(cls, data: bytes) -> Any:
        """Deserializa um objeto Marshal de bytes.

        Valida o header (\\x04\\x08) e devolve o objeto raiz.
        """
        reader = cls(data)
        try:
            header = reader._read(2)
        except EOFError:
            raise ValueError("dados insuficientes para header Marshal")
        if len(header) < 2 or header[0] != 4 or header[1] != 8:
            raise ValueError(
                "header Marshal invalido: %r (esperado \\x04\\x08)" % header
            )
        return reader.read_obj()


# ---------------------------------------------------------------------------
# Helpers: leitura de arquivos .rvdata2
# ---------------------------------------------------------------------------

def _read_rvdata2(path: Path) -> Any:
    """Le um arquivo .rvdata2 e devolve o objeto Marshal deserializado."""
    data = path.read_bytes()
    return RubyMarshalReader.loads(data)


# ---------------------------------------------------------------------------
# Helpers: extracao de textos de objetos Ruby RPG Maker
# ---------------------------------------------------------------------------

# Campos que contem texto traduzivel em objects RPG Maker.
_TEXT_FIELDS = frozenset({
    "name", "description", "note", "nickname",
    "message1", "message2", "message3", "message4",
})

# Arquivos de database (array de objetos com campos de texto).
_DATABASE_FILES = {
    "Actors.rvdata2", "Items.rvdata2", "Weapons.rvdata2",
    "Armors.rvdata2", "Skills.rvdata2", "States.rvdata2",
    "Enemies.rvdata2", "Classes.rvdata2",
}

# Codigos de evento que contem texto dialogo/dialogo.
_DIALOGUE_CODES = {401, 405}  # Show Text, Scroll Text
_CHOICE_CODES = {102}  # Show Choices
_PLUGIN_CODES = {356}  # Plugin Command


def _extract_text_from_value(val: Any) -> Optional[str]:
    """Extrai texto de um valor Marshal.

    Strings diretas sao retornadas. IVar wrapper com E:true
    ja foram resolvidos pelo reader como str.
    """
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        # IVar wrapper
        if "_value" in val:
            inner = val["_value"]
            if isinstance(inner, dict) and inner.get("type") == "Bytes":
                import base64
                raw = base64.b64decode(inner["value"])
                try:
                    return raw.decode("utf-8")
                except UnicodeDecodeError:
                    return raw.decode("latin-1", errors="replace")
    return None


def _obj_get(obj: Any, key: str) -> Any:
    """Busca um atributo em um objeto Marshal (dict com __dict__)."""
    if not isinstance(obj, dict):
        return None
    # Objeto direto com chave no dict
    if key in obj:
        return obj[key]
    # Objeto com __dict__
    inner = obj.get("__dict__")
    if isinstance(inner, dict) and key in inner:
        return inner[key]
    return None


def _extract_database_texts(
    data: Any, file_rel: str, filename: str
) -> Iterator[TextEntry]:
    """Extrai textos de arquivos de database (array de objetos)."""
    if not isinstance(data, list):
        return
    for idx, obj in enumerate(data):
        if not isinstance(obj, dict):
            continue
        for field in _TEXT_FIELDS:
            val = _obj_get(obj, field)
            text = _extract_text_from_value(val)
            if text and text.strip():
                yield TextEntry(
                    file=file_rel,
                    line=idx + 1,
                    source=text.strip(),
                    source_key="%s.%s.%d" % (filename, field, idx + 1),
                    category="rpgmaker_database",
                    context={"field": field, "filename": filename},
                )


def _extract_system_texts(data: Any, file_rel: str) -> Iterator[TextEntry]:
    """Extrai textos do arquivo System.rvdata2 (vocabulary)."""
    if not isinstance(data, dict):
        return
    # vocabulary: dict de categorias -> lista de strings
    terms = _obj_get(data, "terms")
    if isinstance(terms, dict):
        for category, entries in terms.items():
            if isinstance(entries, dict):
                for key, val in entries.items():
                    text = _extract_text_from_value(val)
                    if text and text.strip():
                        yield TextEntry(
                            file=file_rel,
                            line=0,
                            source=text.strip(),
                            source_key="system.terms.%s.%s" % (category, key),
                            category="rpgmaker_system",
                            context={"section": "terms", "category": category},
                        )
            elif isinstance(entries, list):
                for i, val in enumerate(entries):
                    text = _extract_text_from_value(val)
                    if text and text.strip():
                        yield TextEntry(
                            file=file_rel,
                            line=0,
                            source=text.strip(),
                            source_key="system.terms.%s.%d" % (category, i),
                            category="rpgmaker_system",
                            context={"section": "terms", "category": category},
                        )
    # listas de nomes: elements, weapon_types, armor_types, etc.
    for list_name in ("elements", "weapon_types", "armor_types", "skill_types"):
        items = _obj_get(data, list_name)
        if isinstance(items, list):
            for i, val in enumerate(items):
                text = _extract_text_from_value(val)
                if text and text.strip():
                    yield TextEntry(
                        file=file_rel,
                        line=0,
                        source=text.strip(),
                        source_key="system.%s.%d" % (list_name, i),
                        category="rpgmaker_system",
                        context={"section": list_name},
                    )


def _extract_map_texts(data: Any, file_rel: str) -> Iterator[TextEntry]:
    """Extrai textos de eventos de mapa (comandos 401/102)."""
    if not isinstance(data, dict):
        return
    pages = data.get("pages")
    if not isinstance(pages, list):
        return
    for page_idx, page in enumerate(pages):
        if not isinstance(page, dict):
            continue
        commands = page.get("list")
        if not isinstance(commands, list):
            continue
        for cmd_idx, cmd in enumerate(commands):
            if not isinstance(cmd, dict):
                continue
            code = cmd.get("code", 0)
            parameters = cmd.get("parameters", [])
            if code in _DIALOGUE_CODES and parameters:
                # parameters[0] e o texto
                text = _extract_text_from_value(parameters[0])
                if text and text.strip():
                    yield TextEntry(
                        file=file_rel,
                        line=cmd_idx + 1,
                        source=text.strip(),
                        source_key="map.page%d.cmd%d" % (page_idx, cmd_idx),
                        category="rpgmaker_map",
                        context={
                            "page": page_idx,
                            "code": code,
                            "command_index": cmd_idx,
                        },
                    )
            elif code in _CHOICE_CODES and parameters:
                # parameters[0] e lista de strings (escolhas)
                choices = parameters[0]
                if isinstance(choices, list):
                    for ci, choice_val in enumerate(choices):
                        text = _extract_text_from_value(choice_val)
                        if text and text.strip():
                            yield TextEntry(
                                file=file_rel,
                                line=cmd_idx + 1,
                                source=text.strip(),
                                source_key="map.page%d.cmd%d.choice%d" % (
                                    page_idx, cmd_idx, ci
                                ),
                                category="rpgmaker_map",
                                context={
                                    "page": page_idx,
                                    "code": code,
                                    "choice_index": ci,
                                },
                            )


def _extract_common_event_texts(
    data: Any, file_rel: str
) -> Iterator[TextEntry]:
    """Extrai textos de eventos comuns (dialogo e escolhas)."""
    if not isinstance(data, list):
        return
    for evt_idx, event in enumerate(data):
        if not isinstance(event, dict):
            continue
        commands = event.get("list")
        if not isinstance(commands, list):
            continue
        for cmd_idx, cmd in enumerate(commands):
            if not isinstance(cmd, dict):
                continue
            code = cmd.get("code", 0)
            parameters = cmd.get("parameters", [])
            if code in _DIALOGUE_CODES and parameters:
                text = _extract_text_from_value(parameters[0])
                if text and text.strip():
                    yield TextEntry(
                        file=file_rel,
                        line=cmd_idx + 1,
                        source=text.strip(),
                        source_key="common.%d.cmd%d" % (evt_idx, cmd_idx),
                        category="rpgmaker_common",
                        context={
                            "event_index": evt_idx,
                            "code": code,
                        },
                    )
            elif code in _CHOICE_CODES and parameters:
                choices = parameters[0]
                if isinstance(choices, list):
                    for ci, choice_val in enumerate(choices):
                        text = _extract_text_from_value(choice_val)
                        if text and text.strip():
                            yield TextEntry(
                                file=file_rel,
                                line=cmd_idx + 1,
                                source=text.strip(),
                                source_key="common.%d.cmd%d.choice%d" % (
                                    evt_idx, cmd_idx, ci
                                ),
                                category="rpgmaker_common",
                                context={
                                    "event_index": evt_idx,
                                    "code": code,
                                    "choice_index": ci,
                                },
                            )


# ---------------------------------------------------------------------------
# Busca de arquivos .rvdata2/.rvdata
# ---------------------------------------------------------------------------

_RVDATA_EXTS = (".rvdata2", ".rvdata")


def _find_rvdata_files(game_path: str, max_depth: int = _MAX_DETECT_DEPTH):
    """Busca recursiva por .rvdata2/.rvdata com limite de profundidade."""
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
            if name.lower().endswith(_RVDATA_EXTS):
                yield Path(current) / name


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class VXAceAdapter(EngineAdapter):
    """Adapter para jogos RPG Maker VX/Ace (.rvdata2/.rvdata)."""

    @property
    def validator(self):
        """Devolve o validador RPGMakerValidator para esta engine."""
        try:
            from ..validators.rpgmaker import RPGMakerValidator
        except ImportError:
            from validators.rpgmaker import RPGMakerValidator
        return RPGMakerValidator()

    def detect(self, game_path: str) -> bool:
        """True se game_path contiver .rvdata2/.rvdata (max 3 niveis)."""
        for _path in _find_rvdata_files(game_path):
            return True
        return False

    def extract(self, game_path: str) -> Iterator[TextEntry]:
        """Extrai textos semanticos dos arquivos .rvdata2/.rvdata."""
        for rv_path in _find_rvdata_files(game_path):
            yield from self._extract_from_file(rv_path, game_path)

    def metadata(self, game_path: str) -> dict:
        """Devolve contagem de arquivos .rvdata2/.rvdata."""
        count = sum(1 for _ in _find_rvdata_files(game_path))
        return {"engine": "rpgmaker_vxace", "rvdata_count": count}

    # ------------------------------------------------------------------
    # extracao interna

    def _extract_from_file(self, rv_path: Path, game_root: str):
        """Extrai textos de um unico arquivo .rvdata2."""
        rel = str(rv_path.relative_to(Path(game_root))).replace("\\", "/")
        filename = rv_path.name

        try:
            data = _read_rvdata2(rv_path)
        except (ValueError, EOFError, OSError):
            return  # arquivo corrompido ou ilegivel

        if filename in _DATABASE_FILES:
            yield from _extract_database_texts(data, rel, filename)
        elif filename == "System.rvdata2":
            yield from _extract_system_texts(data, rel)
        elif filename == "MapInfos.rvdata2":
            yield from self._extract_map_infos(data, rel)
        elif filename.startswith("Map") and filename.endswith(
            (".rvdata2", ".rvdata")
        ):
            yield from _extract_map_texts(data, rel)
        elif filename == "CommonEvents.rvdata2":
            yield from _extract_common_event_texts(data, rel)
        # Scripts.rvdata2 e ignorado (requer descompressao zlib + Ruby)

    def _extract_map_infos(self, data: Any, file_rel: str) -> Iterator[TextEntry]:
        """Extrai nomes dos mapas de MapInfos.rvdata2."""
        if not isinstance(data, dict):
            return
        for key, val in data.items():
            text = _extract_text_from_value(val)
            if text and text.strip():
                yield TextEntry(
                    file=file_rel,
                    line=0,
                    source=text.strip(),
                    source_key="mapinfos.%s" % key,
                    category="rpgmaker_database",
                    context={"filename": "MapInfos.rvdata2", "field": "name"},
                )


# Registra o adapter automaticamente ao importar o modulo.
register_adapter("rpgmaker_vxace", VXAceAdapter())
