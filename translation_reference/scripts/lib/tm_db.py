# -*- coding: utf-8 -*-
"""Banco local de traducoes indexado em SQLite (Fase 7).

Camada superior ao TMStore (JSONL) e ao ChainedTM (cache global):
indexa traducoes com metadados completos, permite queries por hash
(cross-game reutilizacao), por jogo, por status, e exportacao para JSONL.

Contrato de ``TranslationDB``
-----------------------------
- ``__init__(db_path)``: cria ou abre SQLite em ``db_path``. Quando o DB
  esta vazio e existem TMStores/Global compativeis no diretorio padrao,
  importa automaticamente (lazy seed).
- ``upsert(entry_dict)``: insere ou atualiza por UNIQUE constraint
  ``(engine, game_id, file, source_key)``; atualiza ``updated_at``.
- ``lookup(original_hash)``: busca por hash do original (reutilizacao
  cross-game). Devolve lista de dicts.
- ``lookup_by_game(game_id)``: todas as entradas de um jogo.
- ``count_by_status(game_id)``: contagem agrupada por status.
- ``export_jsonl(game_id, output_path)``: exporta para JSONL legivel.
- ``import_from_tmstore(tmstore_path, game_id, engine)``: importa JSONL
  existente (TMStore) para o DB.
- ``pending_entries(game_id)``: status='pending' (para modo no-tokens).
- ``needs_translation(game_id)``: status IN ('pending','needs_review','failed').

Somente biblioteca padrao (sqlite3 e stdlib). Mensagens em pt-BR sem acento.
"""

import hashlib
import json
import sqlite3
from pathlib import Path

__all__ = ["TranslationDB", "DEFAULT_DB_PATH", "hash_text"]

DEFAULT_DB_PATH = "reports/tm/tm.sqlite"

# Diretorios padrao para lazy seed (TMStore por-jogo e global).
_DEFAULT_TM_DIR = "reports/tm"
_GLOBAL_TM_NAME = "global.jsonl"


def hash_text(text):
    """Devolve hash SHA-256 do texto como string hex."""
    if not isinstance(text, str):
        text = str(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class TranslationDB:
    """Banco local de traducoes indexado em SQLite."""

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = DEFAULT_DB_PATH
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()
        # Lazy seed: se o DB esta vazio, tenta importar TMStores existentes.
        if self._is_empty():
            self._lazy_seed()

    # ------------------------------------------------------------------
    # DDL

    def _create_tables(self):
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                engine      TEXT    NOT NULL,
                game_id     TEXT    NOT NULL,
                file        TEXT    NOT NULL,
                source_key  TEXT    NOT NULL,
                original    TEXT    NOT NULL,
                translated  TEXT,
                status      TEXT    NOT NULL DEFAULT 'pending',
                notes       TEXT,
                hash        TEXT    NOT NULL,
                created_at  TEXT    DEFAULT CURRENT_TIMESTAMP,
                updated_at  TEXT    DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(engine, game_id, file, source_key)
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_entries_hash ON entries(hash)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_entries_game ON entries(game_id)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_entries_status ON entries(status)"
        )
        self._conn.commit()

    def _is_empty(self):
        row = self._conn.execute("SELECT COUNT(*) FROM entries").fetchone()
        return row[0] == 0

    # ------------------------------------------------------------------
    # Lazy seed

    def _lazy_seed(self):
        """Importa TMStores existentes no diretorio padrao quando DB vazio.

        Procura por ``reports/tm/<game_id>.jsonl`` e
        ``reports/tm/global.jsonl``. Silencioso: se nao encontrar nada,
        apenas retorna.
        """
        base = self.db_path.parent  # reports/tm/
        if not base.is_dir():
            return
        for jsonl_path in sorted(base.glob("*.jsonl")):
            if jsonl_path.name == _GLOBAL_TM_NAME:
                # Global: game_id derivado do nome do arquivo.
                self.import_from_tmstore(
                    str(jsonl_path), game_id="global", engine="unknown"
                )
            else:
                # Por jogo: game_id e o stem do arquivo.
                game_id = jsonl_path.stem
                self.import_from_tmstore(
                    str(jsonl_path), game_id=game_id, engine="unknown"
                )

    # ------------------------------------------------------------------
    # CRUD

    def upsert(self, entry):
        """Insere ou atualiza uma entrada de traducao.

        ``entry`` e um dict com chaves obrigatorias: engine, game_id, file,
        source_key, original. Chaves opcionais: translated, status, notes.
        O campo ``hash`` e calculado automaticamente se ausente.
        """
        engine = entry["engine"]
        game_id = entry["game_id"]
        file = entry["file"]
        source_key = entry["source_key"]
        original = entry["original"]
        translated = entry.get("translated")
        status = entry.get("status", "pending")
        notes = entry.get("notes")
        h = entry.get("hash") or hash_text(original)

        self._conn.execute(
            """
            INSERT INTO entries
                (engine, game_id, file, source_key, original, translated,
                 status, notes, hash, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(engine, game_id, file, source_key) DO UPDATE SET
                original   = excluded.original,
                translated = excluded.translated,
                status     = excluded.status,
                notes      = excluded.notes,
                hash       = excluded.hash,
                updated_at = CURRENT_TIMESTAMP
            """,
            (engine, game_id, file, source_key, original,
             translated, status, notes, h),
        )
        self._conn.commit()

    def lookup(self, original_hash):
        """Busca entradas pelo hash do original (reutilizacao cross-game)."""
        rows = self._conn.execute(
            "SELECT * FROM entries WHERE hash = ?", (original_hash,)
        ).fetchall()
        return [dict(r) for r in rows]

    def lookup_by_game(self, game_id):
        """Todas as entradas de um jogo especifico."""
        rows = self._conn.execute(
            "SELECT * FROM entries WHERE game_id = ? ORDER BY id", (game_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def count_by_status(self, game_id):
        """Contagem de entradas agrupadas por status para um jogo."""
        rows = self._conn.execute(
            "SELECT status, COUNT(*) as cnt FROM entries "
            "WHERE game_id = ? GROUP BY status",
            (game_id,),
        ).fetchall()
        return {r["status"]: r["cnt"] for r in rows}

    def pending_entries(self, game_id):
        """Entradas com status='pending' (modo no-tokens)."""
        rows = self._conn.execute(
            "SELECT * FROM entries WHERE game_id = ? AND status = 'pending' "
            "ORDER BY id",
            (game_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def needs_translation(self, game_id):
        """Entradas que precisam de traducao (pending|needs_review|failed)."""
        rows = self._conn.execute(
            "SELECT * FROM entries WHERE game_id = ? "
            "AND status IN ('pending', 'needs_review', 'failed') "
            "ORDER BY id",
            (game_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Import / Export

    def import_from_tmstore(self, tmstore_path, game_id, engine):
        """Importa um arquivo JSONL (TMStore) existente para o DB.

        Cada linha do JSONL e mapeada para uma entrada com status='tm_hit'
        (ja traduzido). Campos: source->original, target->translated,
        file->file, item_id->source_key.
        """
        tm_path = Path(tmstore_path)
        if not tm_path.exists():
            return 0

        count = 0
        with open(tm_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue  # linha corrompida: ignora
                if not isinstance(record, dict):
                    continue

                source = record.get("source", "")
                target = record.get("target", "")
                if not isinstance(source, str) or not source.strip():
                    continue

                source_key = record.get("item_id") or ""
                file_field = record.get("file") or ""

                self.upsert(
                    {
                        "engine": engine,
                        "game_id": game_id,
                        "file": file_field,
                        "source_key": source_key,
                        "original": source,
                        "translated": target if target else None,
                        "status": "tm_hit" if target else "pending",
                        "notes": None,
                    }
                )
                count += 1

        return count

    def export_jsonl(self, game_id, output_path):
        """Exporta todas as entradas de um jogo para JSONL legivel.

        Cada linha e um dict com todos os campos da tabela, sem o campo
        ``id`` interno. Se nao houver entradas, nenhum arquivo e criado.
        """
        out = Path(output_path)

        rows = self._conn.execute(
            "SELECT * FROM entries WHERE game_id = ? ORDER BY id", (game_id,)
        ).fetchall()

        if not rows:
            return 0

        out.parent.mkdir(parents=True, exist_ok=True)

        with open(out, "w", encoding="utf-8", newline="\n") as fh:
            for row in rows:
                record = {
                    "engine": row["engine"],
                    "game_id": row["game_id"],
                    "file": row["file"],
                    "source_key": row["source_key"],
                    "original": row["original"],
                    "translated": row["translated"],
                    "status": row["status"],
                    "notes": row["notes"],
                    "hash": row["hash"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                fh.write(
                    json.dumps(record, ensure_ascii=False, sort_keys=True)
                    + "\n"
                )

        return len(rows)

    # ------------------------------------------------------------------
    # Lifecycle

    def close(self):
        """Fecha a conexao com o banco."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
