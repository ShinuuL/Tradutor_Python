# -*- coding: utf-8 -*-
"""Base abstrata para adapters de engine e registro global.

Componente da Fase 7 (adapters multi-engine) do TradutorDGames.

Um adapter encapsula a deteccao de engine, extracao semantica de textos,
aplicacao de TM e geracao de patch/pacote para um tipo de engine de jogo.

Contrato de ``EngineAdapter``
-----------------------------
- ``detect(game_path)``: devolve True se o diretorio contiver arquivos
  daquela engine (busca recursiva com limite de profundidade).
- ``extract(game_path)``: iterador de ``TextEntry`` com textos
  semanticamente significativos (dialogue, menus, strings traduziveis).
- ``metadata(game_path)``: dict com informacoes diagnosticas (contagem
  de arquivos, labels, etc).

Somente biblioteca padrao. Mensagens em pt-BR sem acento.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Iterator, Optional, Tuple

__all__ = [
    "EngineAdapter",
    "TextEntry",
    "REGISTRY",
    "detect_engine",
    "get_adapter",
    "register_adapter",
]


@dataclass(frozen=True)
class TextEntry:
    """Entrada de texto extraida por um adapter."""

    file: str
    line: int
    source: str
    source_key: str
    category: str
    context: dict = field(default_factory=dict)


class EngineAdapter(ABC):
    """Classe abstrata base para todos os adapters de engine."""

    @abstractmethod
    def detect(self, game_path: str) -> bool:
        """Devolve True se game_path contiver arquivos desta engine."""

    @abstractmethod
    def extract(self, game_path: str) -> Iterator[TextEntry]:
        """Itera textos semanticamente significativos do jogo."""

    @abstractmethod
    def metadata(self, game_path: str) -> dict:
        """Devolve dict com informacoes diagnosticas do jogo."""


# Registro global de adapters: nome -> instancia.
REGISTRY: Dict[str, EngineAdapter] = {}

# Flag para evitar imports duplicados dos built-ins.
_builtin_loaded = False


def _ensure_builtin_adapters():
    """Importa os adapters built-ins uma unica vez (lazy)."""
    global _builtin_loaded
    if _builtin_loaded:
        return
    _builtin_loaded = True
    try:
        from . import renpy  # noqa: F401,F811
    except ImportError:
        pass
    try:
        from . import tyrano  # noqa: F401,F811
    except ImportError:
        pass
    try:
        from . import godot  # noqa: F401,F811
    except ImportError:
        pass
    try:
        from . import rpgmaker_vxace  # noqa: F401,F811
    except ImportError:
        pass
    try:
        from . import kirikiri  # noqa: F401,F811
    except ImportError:
        pass
    try:
        from . import wolfrpg  # noqa: F401,F811
    except ImportError:
        pass


def register_adapter(name: str, adapter: EngineAdapter) -> None:
    """Registra um adapter no REGISTRY. nome deve ser lower-case ASCII."""
    if not isinstance(name, str) or not name.isascii() or not name.islower():
        raise ValueError(
            "nome do adapter deve ser lower-case ASCII sem espacos: %r" % name
        )
    if not isinstance(adapter, EngineAdapter):
        raise TypeError(
            "adapter deve ser instancia de EngineAdapter, recebeu %r"
            % type(adapter).__name__
        )
    REGISTRY[name] = adapter


def get_adapter(name: str) -> EngineAdapter:
    """Devolve o adapter registrado com o nome dado.

    Levanta KeyError se nenhum adapter com aquele nome estiver registrado.
    """
    _ensure_builtin_adapters()
    if name not in REGISTRY:
        raise KeyError("nenhum adapter registrado com nome: %r" % name)
    return REGISTRY[name]


def detect_engine(game_path: str) -> Tuple[Optional[str], dict]:
    """Itera o REGISTRY e devolve o primeiro adapter que detectar o jogo.

    Devolve (nome_do_adapter, metadata) ou (None, {}) quando nenhum
    adapter reconhece o diretorio.
    """
    _ensure_builtin_adapters()
    for name, adapter in REGISTRY.items():
        try:
            if adapter.detect(game_path):
                return name, adapter.metadata(game_path)
        except Exception:
            # Adapter com falha e ignorado; segue o proximo.
            continue
    return None, {}
