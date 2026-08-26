# -*- coding: utf-8 -*-
"""Cadeia de memorias de traducao com cache global entre jogos (Fase 8).

Componente do objetivo "cache global entre jogos": consulta mais de uma
memoria de traducao em ordem de prioridade, evitando chamar o LLM para
textos ja traduzidos em qualquer jogo anterior. Reutiliza ``TMStore`` tal
qual ele e (append-only, carga tolerante a linha corrompida); somente
stdlib do Python 3.

Contrato de ``ChainedTM``
------------------------
- ``__init__(stores)``: lista de ``TMStore`` na ordem de prioridade; o
  indice 0 e consultado primeiro. Quando usada pelo CLI a ordem fixa e:
  cache global (``reports/tm/global.jsonl``) ANTES da TM por-jogo.
- ``lookup(text)``: consulta cada store na ordem e para no primeiro
  acerto. Devolve a tupla ``(target, indice_da_store)``; sem nenhum
  acerto devolve ``(None, -1)``. A chave continua sendo o texto exato
  apos ``strip()``, herdado do TMStore.
- ``add_many(pairs)``: grava os MESMOS pares em TODAS as stores, na
  ordem da cadeia. Append-only herdado: nada existente e reescrito.
- Tolerancia a corrupcao vem do TMStore: linha corrompida ou JSON
  invalido em qualquer store nao derruba a carga das demais.

Prefixo de auditoria
--------------------
Na cache global o campo ``file`` dos pares novos sai prefixado com o id
do jogo (``<id_do_jogo>::<arquivo>``) para manter auditavel a origem de
cada par quando varios jogos alimentam o mesmo arquivo. A TM por-jogo
continua guardando o caminho cru. Use ``with_global_file_prefix`` para
montar essas copias decoradas sem alterar os pares originais.
"""

__all__ = ["ChainedTM", "GLOBAL_FILE_SEPARATOR", "with_global_file_prefix"]

# Separador entre id do jogo e caminho relativo no campo ``file`` da
# cache global (ex.: ``RJ01696894::data/Actors.json``).
GLOBAL_FILE_SEPARATOR = "::"


def with_global_file_prefix(pairs, game_id):
    """Devolve COPIAS dos pares com ``file`` prefixado pelo id do jogo.

    Usado na gravacao da cache global para auditoria. Os pares de entrada
    NAO sao alterados; cada copia recebe ``file`` = ``<id>::<arquivo>``.
    """
    prefix = str(game_id or "").strip() + GLOBAL_FILE_SEPARATOR
    decorated = []
    for pair in pairs:
        item = dict(pair)
        item["file"] = prefix + str(item.get("file") or "")
        decorated.append(item)
    return decorated


class ChainedTM:
    """Consulta varias ``TMStore`` em ordem de prioridade."""

    def __init__(self, stores):
        stores = list(stores or [])
        for store in stores:
            if not callable(getattr(store, "lookup", None)) or not callable(
                getattr(store, "add_many", None)
            ):
                raise TypeError(
                    "store invalida na cadeia: %r nao implementa lookup/add_many"
                    % type(store).__name__
                )
        self.stores = stores

    def lookup(self, text):
        """Devolve ``(target, indice_da_store)`` do primeiro acerto.

        Consulta as stores na ordem de prioridade e para no primeiro hit;
        sem nenhum acerto devolve ``(None, -1)``.
        """
        for index, store in enumerate(self.stores):
            target = store.lookup(text)
            if target:
                return target, index
        return None, -1

    def add_many(self, pairs):
        """Grava os mesmos pares em TODAS as stores, na ordem da cadeia.

        Cada store valida os pares ANTES de escrever (contrato herdado),
        entao um par invalido nao deixa gravacao parcial em nenhuma delas.
        """
        pairs = list(pairs or [])
        if not pairs:
            return
        for store in self.stores:
            store.add_many(pairs)
