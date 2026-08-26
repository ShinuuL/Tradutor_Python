# -*- coding: utf-8 -*-
"""Classe base abstrata para validadores de traducao por adapter.

Componente da Fase 7 do TradutorDGames.

Um validador confere se uma traducao preserva a integridade tecnica
do texto original: placeholders, tags da engine, escapes, quebras de
linha e encoding.

Somente biblioteca padrao. Mensagens em pt-BR sem acento.
"""

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

# Importa modulo de placeholders existente.
import os as _os

def _import_validate_pair():
    """Importa validate_pair do placeholders.py com fallback robusto."""
    try:
        from ..placeholders import validate_pair as fn
        return fn
    except ImportError:
        pass
    # Fallback: tenta via caminho absoluto relativo a este arquivo.
    _here = _os.path.dirname(_os.path.abspath(__file__))
    _lib_dir = _os.path.dirname(_here)
    if _lib_dir not in sys.path:
        sys.path.insert(0, _lib_dir)
    from placeholders import validate_pair as fn
    return fn

_placeholders_validate = _import_validate_pair()


__all__ = [
    "TranslationValidator",
    "ValidationResult",
    "check_placeholders",
    "check_encoding",
    "check_newlines",
    "check_empty_translation",
    "check_length_ratio",
]


# ---------------------------------------------------------------------------
# Resultado de validacao
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """Resultado de uma validacao de traducao.

    Attributes:
        ok: True se nao houve erros (avisos nao invalidam).
        errors: motivos de falha (traducao rejeitada).
        warnings: avisos nao-fatais (traducao aceita com ressalva).
    """

    ok: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        """Adiciona um erro e marca ok=False."""
        self.errors.append(msg)
        self.ok = False

    def add_warning(self, msg: str) -> None:
        """Adiciona um aviso (nao altera ok)."""
        self.warnings.append(msg)

    def merge(self, other: "ValidationResult") -> None:
        """Mescla outro resultado neste. Erros de other viram erros aqui."""
        for e in other.errors:
            self.add_error(e)
        for w in other.warnings:
            self.add_warning(w)


# ---------------------------------------------------------------------------
# Validacoes comuns reutilizaveis
# ---------------------------------------------------------------------------

def check_placeholders(source: str, translated: str) -> ValidationResult:
    """Confere se placeholders/markup do source estao preservados em translated.

    Usa o modulo placeholders.py existente (validate_pair).
    """
    result = ValidationResult()
    ok, notes = _placeholders_validate(source, translated)
    if not ok:
        for note in notes:
            result.add_error(note)
    return result


def check_encoding(source: str, translated: str) -> ValidationResult:
    """Confere se ambos os textos sao UTF-8 valido.

    Strings Python ja sao Unicode, mas testamos se os bytes
    originais decodificam como UTF-8 sem erros.
    """
    result = ValidationResult()
    for label, text in [("source", source), ("translated", translated)]:
        try:
            text.encode("utf-8")
        except UnicodeEncodeError as exc:
            result.add_error(
                "%s contem caracteres invalidos em UTF-8: %s" % (label, exc)
            )
    return result


def check_newlines(source: str, translated: str) -> ValidationResult:
    """Confere se source e translated tem a mesma contagem de quebras de linha."""
    result = ValidationResult()
    src_count = source.count("\n")
    tgt_count = translated.count("\n")
    if src_count != tgt_count:
        result.add_warning(
            "quantidade de quebras de linha diferente "
            "(source=%d, translated=%d)" % (src_count, tgt_count)
        )
    return result


def check_empty_translation(source: str, translated: str) -> ValidationResult:
    """Confere se a traducao nao e vazia quando source nao e vazio."""
    result = ValidationResult()
    if source.strip() and not translated.strip():
        result.add_error("traducao vazia para texto original nao vazio")
    return result


def check_length_ratio(
    source: str, translated: str, max_ratio: float = 3.0
) -> ValidationResult:
    """Confere se a traducao nao excede max_ratio vezes o tamanho do source.

    Avisa quando a traducao e suspeitamente longa.
    """
    result = ValidationResult()
    if not source.strip():
        return result
    ratio = len(translated) / len(source)
    if ratio > max_ratio:
        result.add_warning(
            "traducao %.1fx maior que source (max permitido: %.1fx)"
            % (ratio, max_ratio)
        )
    return result


# ---------------------------------------------------------------------------
# Classe base abstrata
# ---------------------------------------------------------------------------

class TranslationValidator(ABC):
    """Classe abstrata base para validadores por adapter.

    Cada adapter deve implementar ``validate`` e ``category_tags``.
    """

    @abstractmethod
    def validate(self, source: str, translated: str) -> ValidationResult:
        """Valida se translated preserva integridade tecnica de source.

        Devolve ValidationResult com erros (rejeicao) e/ou avisos.
        """

    @abstractmethod
    def category_tags(self) -> List[str]:
        """Devolve lista de tags/markup especificos da engine.

        Essas tags devem ser preservadas na traducao.
        """

    # ------------------------------------------------------------------
    # Helpers que validadores filhos podem reaproveitar
    # ------------------------------------------------------------------

    def _run_common_checks(
        self, source: str, translated: str
    ) -> ValidationResult:
        """Executa todas as validacoes comuns e devolve resultado mesclado."""
        result = ValidationResult()
        result.merge(check_empty_translation(source, translated))
        if not result.ok:
            # Se ja esta vazio, nao tem sentido checar o resto.
            return result
        result.merge(check_placeholders(source, translated))
        result.merge(check_encoding(source, translated))
        result.merge(check_newlines(source, translated))
        result.merge(check_length_ratio(source, translated))
        return result
