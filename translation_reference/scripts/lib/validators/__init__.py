# -*- coding: utf-8 -*-
"""Framework de validadores por adapter para TradutorDGames.

Cada adapter pode ter um validador proprio que confere se uma traducao
preserva integridade tecnica: placeholders, tags, escapes, quebras de
linha e encoding.

Somente biblioteca padrao. Mensagens em pt-BR sem acento.
"""

from .base import TranslationValidator, ValidationResult
from .renpy_val import RenPyValidator
from .rpgmaker import RPGMakerValidator
from .tyrano_val import TyranoValidator
from .godot_val import GodotValidator

__all__ = [
    "TranslationValidator",
    "ValidationResult",
    "RenPyValidator",
    "RPGMakerValidator",
    "TyranoValidator",
    "GodotValidator",
]
