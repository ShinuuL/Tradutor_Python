# -*- coding: utf-8 -*-
"""Integracao entre adapters e o scanner extract_non_english_text.

Componente da Fase 7 (adapters multi-engine) do TradutorDGames.

Quando um adapter e detectado para o jogo, seus textos semanticos
(substituem a saida bruta do scanner regex). Se o adapter nao extrair
nada, o fallback mantem as linhas originais do scanner.

Somente biblioteca padrao. Mensagens em pt-BR sem acento.
"""

from typing import Dict, List, Optional

__all__ = ["filter_by_engine"]


def filter_by_engine(
    scanner_rows: List[dict],
    detected_engine: Optional[str],
    adapter_entries=None,
) -> List[dict]:
    """Filtra linhas do scanner com base no engine detectado.

    Regras:
    - Se ``detected_engine`` e None ou ``adapter_entries`` e vazio/None,
      mantem todas as linhas do scanner (fallback).
    - Caso contrario, converte adapter_entries em rows no formato do
      scanner e devolve apenas essas (adapter vence).

    ``adapter_entries`` e uma lista/iteravel de ``TextEntry``.

    O dict de saida segue o schema do scanner (campos: root, file, line,
    extension, encoding, reason, category, priority, source_key, text)
    para manter compatibilidade com o pipeline existente.
    """
    if not detected_engine or not adapter_entries:
        return list(scanner_rows)

    adapter_rows = []
    for entry in adapter_entries:
        adapter_rows.append({
            "root": "",
            "file": entry.file,
            "line": entry.line,
            "extension": ".rpy",
            "encoding": "utf-8",
            "reason": "adapter:%s" % detected_engine,
            "category": entry.category,
            "priority": 95,
            "source_key": entry.source_key,
            "text": entry.source,
            "occurrences": 1,
            "context": entry.context if hasattr(entry, "context") else {},
        })
    return adapter_rows
