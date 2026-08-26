# -*- coding: utf-8 -*-
"""Memoria de traducao persistente em JSONL com gravacao append-only.

Componente do objetivo "memoria de traducao": reaproveita traducoes ja
feitas entre execucoes do pipeline, sem depender de bibliotecas externas
(somente stdlib do Python 3).

Contrato de ``TMStore``
----------------------
- Carga preguicosa (lazy): o arquivo JSONL so e lido na primeira chamada
  de ``lookup`` ou ``add_many``. Construtor nao toca no disco.
- ``lookup(text)``: devolve a traducao para o texto exato apos ``strip()``
  ou ``None`` quando o par ainda nao existe na memoria.
- ``add_many(pairs)``: acrescenta os pares ao fim do arquivo e faz flush
  imediato a cada linha. Nada existente e reescrito ou removido.
- Dedupe na carga: se o mesmo ``source`` aparece mais de uma vez, vence a
  ocorrencia MAIS RECENTE (ultima linha do arquivo). Como a gravacao e
  append-only, a ultima linha e sempre a mais nova.
- Campos gravados por linha: ``source``, ``target``, ``lang`` (padrao
  ``"ja-en"``), ``file``, ``item_id`` e ``ts`` (epoch em segundos; gerado
  na hora quando ausente).
- Encoding UTF-8 sempre. Linha corrompida ou JSON invalido e ignorada na
  carga sem interromper as demais. O diretorio pai do arquivo e criado
  automaticamente quando nao existe.
"""

import json
import time
from pathlib import Path

__all__ = ["TMStore"]

DEFAULT_LANG = "ja-en"


class TMStore:
    """Memoria de traducao (translation memory) em arquivo JSONL."""

    def __init__(self, path):
        self.path = Path(path)
        # None = ainda nao carregado; dict vazio = carregado sem entradas.
        self._entries = None

    # ------------------------------------------------------------------
    # consulta

    def lookup(self, text):
        """Devolve a traducao mais recente para ``text`` ou ``None``.

        A chave e o texto exato apos ``strip()``.
        """
        entries = self._ensure_loaded()
        if not isinstance(text, str):
            return None
        record = entries.get(text.strip())
        if record is None:
            return None
        return record["target"]

    # ------------------------------------------------------------------
    # gravacao

    def add_many(self, pairs):
        """Acrescenta ``pairs`` ao JSONL com flush imediato por linha.

        Cada par precisa ser um dict com ``source`` e ``target`` nao vazios;
        ``lang``, ``file``, ``item_id`` e ``ts`` recebem padrao quando
        ausentes. Levanta ``TypeError``/``ValueError`` para pares invalidos,
        antes de escrever qualquer coisa no disco.
        """
        records = [self._as_record(pair) for pair in pairs]
        if not records:
            return
        entries = self._ensure_loaded()
        parent = self.path.parent
        if str(parent):
            parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8", newline="\n") as fh:
            for record in records:
                line = json.dumps(record, ensure_ascii=False, sort_keys=True)
                fh.write(line + "\n")
                fh.flush()
                # Cache acompanha o disco: ultima ocorrencia vence tambem.
                entries[record["source"].strip()] = record

    # ------------------------------------------------------------------
    # carga interna

    def _ensure_loaded(self):
        if self._entries is None:
            self._entries = self._load()
        return self._entries

    def _load(self):
        """Le o JSONL ignorando linhas corrompidas; ultima ocorrencia vence."""
        entries = {}
        if not self.path.exists():
            return entries
        raw = self.path.read_bytes()
        for chunk in raw.split(b"\n"):
            if not chunk.strip():
                continue
            try:
                line = chunk.decode("utf-8")
            except UnicodeDecodeError:
                continue  # bytes invalidos fora de UTF-8: ignora a linha
            line = line.lstrip("\ufeff").strip()  # BOM eventual na 1a linha
            if not line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue  # linha corrompida/JSON invalido: ignora e segue
            if not isinstance(record, dict):
                continue
            source = record.get("source")
            target = record.get("target")
            if not isinstance(source, str) or not source.strip():
                continue
            if not isinstance(target, str) or not target.strip():
                continue
            entries[source.strip()] = record
        return entries

    @staticmethod
    def _as_record(pair):
        if not isinstance(pair, dict):
            raise TypeError(
                "par invalido: esperado dict, recebido %s" % type(pair).__name__
            )
        source = pair.get("source")
        target = pair.get("target")
        if not isinstance(source, str) or not source.strip():
            raise ValueError("campo 'source' ausente ou vazio no par da memoria")
        if not isinstance(target, str) or not target.strip():
            raise ValueError("campo 'target' ausente ou vazio no par da memoria")
        ts = pair.get("ts")
        if ts is None:
            ts = time.time()
        elif not isinstance(ts, (int, float)) or isinstance(ts, bool):
            raise ValueError("campo 'ts' deve ser numero ou ausente")
        return {
            "source": source,
            "target": target,
            "lang": pair.get("lang") or DEFAULT_LANG,
            "file": pair.get("file") or "",
            "item_id": pair.get("item_id") or "",
            "ts": float(ts),
        }
