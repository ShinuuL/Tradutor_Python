# -*- coding: utf-8 -*-
"""CLI worker de traducao do TradutorDGames (Fase 2 do plano aprovado).

Fluxo principal (traducao) -- NUNCA escreve fora da pasta ``--out-dir``::

    python translate_game_text.py <scan.jsonl> --out-dir reports/translated/<jogo>
        [--tm reports/tm/<jogo>.jsonl] [--tm-global reports/tm/global.jsonl]
        [--engine-url URL] [--engine-model M]
        [--chunk-size N] [--dry-run] [--limit N]

Com ``--tm-global`` a consulta usa a cadeia de memorias [global,
por-jogo] (ChainedTM): um texto ja traduzido em qualquer jogo anterior
nao vai ao motor. Pares novos (status llm) gravam nas DUAS memorias; na
global o campo ``file`` recebe o prefixo ``<id_do_jogo>::`` (nome da
pasta de saida) para auditoria. Sem ``--tm-global`` o comportamento e
identico ao anterior (so TM por-jogo).

Carrega o JSONL do extrator de forma tolerante (linha invalida e ignorada e
contada), agrupa textos unicos, consulta a memoria de traducao primeiro,
envia apenas os faltantes ao motor compativel com OpenAI (modo resiliente:
falha isolada de um chunk nao derruba os demais itens), aplica as
traducoes gerando COPIAS dos arquivos do jogo em ``--out-dir`` e grava os
relatorios ``translation_report.csv`` e ``translation_report.md``. Pares
novos traduzidos pelo motor entram na memoria via ``add_many``.

Subcomandos protegidos (escrevem na arvore do JOGO)::

    python translate_game_text.py apply --translated-dir reports/translated/<jogo> \
        --game-root <pasta_do_jogo> --i-approve-write-game-files
    python translate_game_text.py restore --manifest .../applied_manifest.json

Sem a flag de aprovacao o ``apply`` sai com codigo 3 sem escrever nada.
Com a flag, cria ``<original>.bak`` byte-identico antes de sobrescrever e
grava ``applied_manifest.json`` antes da primeira escrita. O ``restore``
copia cada ``.bak`` de volta, valida o sha256 e registra ``restored`` no
mesmo manifesto preservando os backups. Reaplicar sobre ``.bak`` existente
e idempotente quando o jogo segue no estado protegido (hash igual ao
registrado); arquivo alterado externamente e abortado com nota. Se nada
for escrito por causa desses abortos, o apply sai com codigo 4.

Os caminhos ``bak`` sao comparados e gravados em forma ABSOLUTA canonica
(``Path.resolve`` + ``normcase``), entao rodar o apply com ``--game-root``
relativo ou absoluto chega no mesmo registro. Ao abrir um manifesto antigo
com entradas duplicadas (``bak`` relativo e absoluto do mesmo arquivo), ele
e regravado normalizado e deduplicado mantendo a entrada mais recente,
preservando ``created`` e o bloco ``restored`` intocados.

Subcomando retry (re-traduz itens de um relatorio existente)::

    python translate_game_text.py retry --scan <scan.jsonl> \
        --out-dir reports/translated/<jogo> [--statuses failed,needs_review] \
        [--force-engine] [--tm ...] [--tm-global ...]

Le o ``translation_report.csv`` da pasta de saida, seleciona os
``item_id`` cujo status esta no conjunto informado, filtra as linhas do
scan por esses ids e roda o fluxo normal apenas com elas, regravando
CSV/MD ao final. Com ``--force-engine`` a memoria de traducao e
bypassada; sem ele vale a cadeia normal (global antes da por-jogo).
CSV ausente na pasta de saida sai com codigo 2 sem escrever nada.

Subcomando no-tokens (gera pacote sem chamar LLM)::

    python translate_game_text.py no-tokens --scan <scan.jsonl> \
        --out-dir <dir> --engine-name <nome> \
        [--tm <path>] [--tm-global <path>]

Le o scan, consulta a cadeia de TM e grava CSV com status tm_hit ou
pending. Gera ``pendencias.md`` com os textos que precisam de traducao.
Exit code: 0 se todos traduzidos, 1 se ha pendencias.

Subcomando low-cost (traducao seletiva)::

    python translate_game_text.py low-cost --scan <scan.jsonl> \
        --out-dir <dir> [--threshold N] [--chunk-size N] \
        [--engine-url ...] [--tm ...] [--tm-global ...]

Filtra textos: novos, repetidos >= threshold ou CJK denso sao enviados
ao LLM. Hit no TM vai direto. Resto e skip. Gera CSV e MD.

Codigos de saida: 0 ok | 2 entrada invalida | 3 sem aprovacao |
4 nada aplicado (protegido).
Mensagens em pt-BR sem acento. Somente biblioteca padrao.
"""

import argparse
import csv
import hashlib
import inspect
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parent / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

import appliers  # noqa: E402
from global_tm import ChainedTM, with_global_file_prefix  # noqa: E402
from name_repair import strip_spurious_brackets  # noqa: E402
from tm_db import hash_text as tm_hash_text  # noqa: E402
from tm_store import TMStore  # noqa: E402
from translation_engine import (  # noqa: E402
    NOTE_DIVERGENT,
    NOTE_UNAVAILABLE,
    OpenAICompatEngine,
    TranslationError,
)

__all__ = ["main", "run_translate", "classify_lowcost"]

DEFAULT_ENGINE_URL = "http://localhost:11434/v1"
DEFAULT_ENGINE_MODEL = "qwen2.5:7b-instruct"

# Nota curta gravada no relatorio para item cujo chunk unitario falhou apos
# a subdivisao resiliente por divergencia de protocolo (alias da nota do
# engine, para nao duplicar texto). Falha de servidor usa NOTE_UNAVAILABLE.
RESILIENT_FAIL_NOTE = NOTE_DIVERGENT

MIN_CHUNK_SIZE = 1
MAX_CHUNK_SIZE = 50
DEFAULT_CHUNK_SIZE = 10

REPORT_CSV = "translation_report.csv"
REPORT_MD = "translation_report.md"
MANIFEST_NAME = "applied_manifest.json"
NON_GAME_FILES = frozenset({REPORT_CSV, REPORT_MD, MANIFEST_NAME})
STATUS_ORDER = ("tm_hit", "llm", "needs_review", "failed")
CSV_FIELDS = [
    "item_id",
    "status",
    "file",
    "line",
    "source_key",
    "source",
    "translated",
    "notes",
]


class CliError(Exception):
    """Erro de entrada com codigo de saida associado."""

    def __init__(self, message, exit_code=2):
        super().__init__(message)
        self.exit_code = exit_code


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------


def _ascii(text):
    return str(text).encode("ascii", "replace").decode("ascii")


def _now_iso():
    return datetime.now().isoformat(timespec="seconds")


def _make_progress_printer():
    """Cria emissor ``PROGRESS i/N`` incremental, sem repeticoes seguidas.

    O emissor ignora pares ``(done, total)`` identicos ao ultimo emitido
    (o engine e a conclusao do lote podem reportar o mesmo valor) e usa
    ``flush=True`` para o stdout chegar imediato ao consumidor do processo
    (painel Tk), mesmo quando o subprocess roda com stdout em pipe.
    """
    state = {"last": None}

    def emit(done, total):
        marker = (done, total)
        if state["last"] == marker:
            return
        state["last"] = marker
        print("PROGRESS %d/%d" % (done, total), flush=True)

    return emit


def _accepts_kwarg(func, name):
    """True se ``func`` aceita o kwarg opcional ``name``."""
    if not callable(func):
        return False
    try:
        params = inspect.signature(func).parameters
    except (TypeError, ValueError):
        return False
    return name in params


def _supports_on_progress(func):
    """True se ``func`` aceita o kwarg opcional ``on_progress``."""
    return _accepts_kwarg(func, "on_progress")


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_write_text(path, text):
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _safe_game_path(game_root, rel_file):
    parts = [p for p in str(rel_file).replace("\\", "/").split("/") if p not in ("", ".")]
    if not parts or any(p == ".." for p in parts) or ":" in parts[0]:
        return None
    candidate = Path(game_root).joinpath(*parts)
    try:
        candidate.resolve().relative_to(Path(game_root).resolve())
    except ValueError:
        return None
    return candidate


# ---------------------------------------------------------------------------
# Carga tolerante do scan
# ---------------------------------------------------------------------------


def load_rows(scan_path):
    """Le o JSONL do extrator; linha invalida e ignorada e contada.

    Linha valida = objeto JSON com ``item_id``, ``file`` e ``text`` nao
    vazios apos strip(). Linhas em branco sao puladas sem contagem.
    """
    rows = []
    skipped = 0
    with open(scan_path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                skipped += 1
                continue
            if not isinstance(row, dict):
                skipped += 1
                continue
            valid = True
            for field in ("item_id", "file", "text"):
                value = row.get(field)
                if not isinstance(value, str) or not value.strip():
                    valid = False
                    break
            if valid:
                rows.append(row)
            else:
                skipped += 1
    return rows, skipped


def derive_root(rows):
    """Deriva a raiz do jogo a partir do campo ``root`` mais comum."""
    counter = Counter(
        str(row.get("root")).strip()
        for row in rows
        if isinstance(row.get("root"), str) and str(row.get("root")).strip()
    )
    if not counter:
        return None
    return Path(counter.most_common(1)[0][0])


# ---------------------------------------------------------------------------
# Modo low-cost: classificacao de textos
# ---------------------------------------------------------------------------

# Ranges Unicode para CJK Unified Ideographs, extensoes e kana.
_CJK_RANGES = (
    (0x4E00, 0x9FFF),    # CJK Unified Ideographs
    (0x3400, 0x4DBF),    # CJK Extension A
    (0xF900, 0xFAFF),    # CJK Compatibility Ideographs
    (0x20000, 0x2A6DF),  # CJK Extension B
    (0x2A700, 0x2B73F),  # CJK Extension C
    (0x2B740, 0x2B81F),  # CJK Extension D
    (0x2B820, 0x2CEAF),  # CJK Extension E
    (0x2CEB0, 0x2EBEF),  # CJK Extension F
    (0x30000, 0x3134F),  # CJK Extension G
    (0x31350, 0x323AF),  # CJK Extension H
    (0x3040, 0x309F),    # Hiragana
    (0x30A0, 0x30FF),    # Katakana
    (0x31F0, 0x31FF),    # Katakana Phonetic Extensions
    (0xFF65, 0xFF9F),    # Halfwidth Katakana
)


def _cjk_dense_ratio(text):
    """Razao de caracteres CJK em relacao ao total de caracteres visiveis.

    Ignora espacos e pontuacao ASCII comum (, . ! ? ; :). Valor de 0.0
    (nenhum CJK) a 1.0 (todos os caracteres sao CJK).
    """
    if not isinstance(text, str) or not text:
        return 0.0
    cjk_count = 0
    visible_count = 0
    for ch in text:
        cp = ord(ch)
        is_cjk = any(lo <= cp <= hi for lo, hi in _CJK_RANGES)
        if is_cjk:
            cjk_count += 1
            visible_count += 1
        elif ch.strip():  # nao-espaco
            visible_count += 1
    if visible_count == 0:
        return 0.0
    return cjk_count / visible_count


def classify_lowcost(rows, tm_store_or_chained, threshold=3):
    """Classifica textos para modo low-cost (sem enviar tudo ao LLM).

    Devolve ``(to_translate, skip, tm_hits)``:
    - ``to_translate``: textos novos OU repetidos >= threshold OU CJK denso
      (> 0.5); precisam de traducao via LLM.
    - ``skip``: textos com hit no TM mas que NAO atendem criterios de alto
      impacto (traducao opcional, baixa prioridade); mantem o TM hit.
    - ``tm_hits``: textos com hit que ja tem traducao pronta.

    ``tm_store_or_chained`` pode ser ``TMStore``, ``ChainedTM`` ou ``None``.
    ``threshold`` e o numero minimo de ocorrencias no scan para considerar
    um texto "repetido de alto impacto".
    """
    # Contagem de ocorrencias por texto normalizado (strip)
    text_counter = Counter()
    for row in rows:
        key = str(row.get("text") or "").strip()
        if key:
            text_counter[key] += 1

    to_translate = []  # dicts com row + motivo
    skip = []          # dicts com row
    tm_hits = []       # dicts com row + translated

    seen_keys = set()
    for row in rows:
        key = str(row.get("text") or "").strip()
        if not key:
            continue
        # Dedupe por chave: processa so a primeira ocorrencia
        if key in seen_keys:
            continue
        seen_keys.add(key)

        # Consulta TM
        hit = None
        if tm_store_or_chained is not None:
            raw_hit = tm_store_or_chained.lookup(key)
            if isinstance(raw_hit, tuple):
                hit = raw_hit[0] if raw_hit[0] else None
            else:
                hit = raw_hit

        if hit:
            tm_hits.append({"row": row, "translated": hit, "key": key})
            continue

        # Sem hit: criterios para enviar ao LLM
        repeat_count = text_counter.get(key, 0)
        cjk_ratio = _cjk_dense_ratio(key)
        reasons = []
        if repeat_count >= threshold:
            reasons.append("repetido_%d" % repeat_count)
        if cjk_ratio > 0.5:
            reasons.append("cjk_denso_%.2f" % cjk_ratio)
        if not reasons:
            reasons.append("texto_novo")

        to_translate.append({
            "row": row,
            "key": key,
            "reasons": reasons,
        })

    return to_translate, skip, tm_hits


# ---------------------------------------------------------------------------
# Fluxo de traducao (engine injetavel para testes offline)
# ---------------------------------------------------------------------------


def resolve_translations(keys, tm, engine, on_progress=None, repairs=None):
    """TM primeiro; so misses vao ao motor (modo resiliente quando suportado).

    ``on_progress(done, total)`` e chamado a medida que itens unicos ficam
    resolvidos: apos a consulta a TM e apos CADA chunk do motor (quando o
    engine suporta ``on_progress``), garantindo progresso incremental em
    vez de um unico estouro no final. Engines sem suporte ao kwarg sao
    chamados da forma antiga e recebem apenas uma linha de conclusao.

    ``repairs`` (dict opcional) recebe chave -> notas do reparo conservador
    de nomes (passo A1), aplicado SOMENTE a saidas do motor; hits de TM
    nunca sao alterados.

    Devolve ``(translations, tm_keys, engine_error, failed_keys)``:
    ``translations`` mapeia chave -> traducao, ``tm_keys`` e o conjunto de
    chaves vindas da memoria, ``engine_error`` guarda a mensagem quando o
    motor falhou POR INTEIRO e ``failed_keys`` mapeia chave -> nota curta
    dos itens que falharam individualmente no modo resiliente (divergencia
    de protocolo ou servidor indisponivel; os demais itens do mesmo lote
    prosseguem normalmente).
    """
    translations = {}
    tm_keys = set()
    engine_error = None
    failed_keys = {}
    if tm is not None:
        for key in keys:
            hit = tm.lookup(key)
            if isinstance(hit, tuple):
                # ChainedTM (cache global entre jogos): tupla (target,
                # indice da store que acertou); o alvo e o primeiro campo.
                hit = hit[0]
            if hit:
                translations[key] = hit
                tm_keys.add(key)
    if on_progress is not None and tm_keys:
        on_progress(len(tm_keys), len(keys))
    misses = [key for key in keys if key not in translations]
    if misses and engine is not None:
        outputs = None
        reasons = {}
        resilient = getattr(engine, "translate_batch_resilient", None)
        if resilient is not None:
            try:
                call_kwargs = {}
                if _supports_on_progress(resilient) and on_progress is not None:
                    base_done = len(tm_keys)

                    def report(rel_done, rel_total):
                        on_progress(base_done + rel_done, len(keys))

                    call_kwargs["on_progress"] = report
                # Motivo por item falho (quando o engine suporta): distingue
                # divergencia de protocolo de servidor indisponivel, para o
                # CSV mostrar a causa real em vez de nota generica.
                if _accepts_kwarg(resilient, "collect_reasons"):
                    call_kwargs["collect_reasons"] = reasons
                outputs, failed_indices = resilient(misses, **call_kwargs)
            except TranslationError as exc:
                engine_error = _ascii(exc)
                outputs = None
        else:
            # Compatibilidade: engines antigos/fakes sem o metodo resiliente.
            try:
                outputs = engine.translate_batch(misses)
            except TranslationError as exc:
                engine_error = _ascii(exc)
                outputs = None
        if on_progress is not None:
            # Conclusao: garante o valor final mesmo sem callbacks por chunk.
            done = len(tm_keys) + (len(outputs) if outputs is not None else 0)
            on_progress(done, len(keys))
        if outputs is not None:
            if resilient is not None:
                failed_set = set(failed_indices or [])
                for index, key in enumerate(misses):
                    if index in failed_set:
                        failed_keys[key] = reasons.get(index) or RESILIENT_FAIL_NOTE
            for index, (key, target) in enumerate(zip(misses, outputs)):
                if key in failed_keys:
                    continue
                # Passo A1: reparo conservador SOMENTE na saida do motor;
                # hits de TM nunca passam por aqui. Notas ficam auditaveis.
                texto, notas = strip_spurious_brackets(key, target)
                translations[key] = texto
                if repairs is not None and notas:
                    repairs[key] = list(notas)
    return translations, tm_keys, engine_error, failed_keys


def build_records(rows, translations, tm_keys, failed_keys=None, repairs=None):
    """Associa cada row a sua traducao/origem (progresso ja foi emitido).

    ``repairs`` (dict opcional) traz chave -> notas do reparo de nomes do
    passo A1 (so saidas do motor); cada record ganha ``repair_notes``.
    """
    failed_keys = failed_keys or {}
    repairs = repairs or {}
    records = []
    for row in rows:
        key = row["text"].strip()
        translated = translations.get(key)
        if translated is None:
            origin = None
        elif key in tm_keys:
            origin = "tm"
        else:
            origin = "llm"
        records.append(
            {
                "row": row,
                "key": key,
                "translated": translated,
                "origin": origin,
                "fail_note": failed_keys.get(key),
                "repair_notes": list(repairs.get(key) or []),
            }
        )
    return records


def build_rows_by_file(records):
    """Agrupa rows por arquivo e marca a posicao da auditoria de cada row.

    ``apply_to_copy`` devolve auditorias agrupadas por arquivo, na ordem de
    insercao dos grupos; a marcacao permite casar cada auditoria com a sua
    row mesmo quando os arquivos se alternam na entrada.
    """
    grouped = {}
    members = {}
    for record in records:
        rel = str(record["row"]["file"]).replace("\\", "/")
        payload = dict(record["row"])
        payload["translated"] = record["translated"]
        grouped.setdefault(rel, []).append(payload)
        members.setdefault(rel, []).append(record)
    position = 0
    for rel in grouped:
        for _payload, record in zip(grouped[rel], members[rel]):
            record["_audit_index"] = position
            position += 1
    return grouped


def finalize_records(records, audits, engine_error):
    """Combina auditorias do applier com a origem da traducao por item."""
    total_audits = len(audits)
    for record in records:
        notes = []
        translated = record.get("translated")
        if translated is None:
            status = "failed"
            notes.append("sem traducao disponivel")
            if record.get("fail_note"):
                # Falha individual do modo resiliente: motivo curto do item.
                notes.append(record["fail_note"])
            elif engine_error:
                notes.append(engine_error)
        else:
            index = record.get("_audit_index")
            audit = audits[index] if isinstance(index, int) and index < total_audits else None
            if audit is None:
                status = "failed"
                notes.append("auditoria ausente do applier")
            else:
                notes.extend(audit.get("notes") or [])
                # Notas do reparo de nomes (passo A1): auditoria do que o
                # motor produziu e foi ajustado antes do applier.
                notes.extend(record.get("repair_notes") or [])
                applied_status = audit.get("status")
                if applied_status == "applied":
                    status = "tm_hit" if record.get("origin") == "tm" else "llm"
                elif applied_status == "needs_review":
                    status = "needs_review"
                else:
                    status = "failed"
        record["status"] = status
        record["notes"] = notes
    return records


def collect_new_pairs(records):
    pairs = []
    seen = set()
    for record in records:
        if record["status"] != "llm":
            continue
        key = record["key"]
        if key in seen:
            continue
        seen.add(key)
        pairs.append(
            {
                "source": key,
                "target": record["translated"],
                "file": str(record["row"]["file"]),
                "item_id": str(record["row"]["item_id"]),
            }
        )
    return pairs


def _line_number(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def write_csv_report(out_dir, records):
    csv_path = Path(out_dir) / REPORT_CSV
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for record in records:
            row = record["row"]
            writer.writerow(
                {
                    "item_id": str(row.get("item_id") or ""),
                    "status": record["status"],
                    "file": str(row.get("file") or ""),
                    "line": _line_number(row.get("line")),
                    "source_key": str(row.get("source_key") or ""),
                    "source": str(row.get("text") or ""),
                    "translated": record.get("translated") or "",
                    "notes": "; ".join(record.get("notes") or []),
                }
            )
    return csv_path


def write_md_report(out_dir, records, statuses, scan_path, src_root, created):
    md_path = Path(out_dir) / REPORT_MD
    lines = [
        "# Relatorio de traducao",
        "",
        "- Gerado em: %s" % created,
        "- Origem: %s" % scan_path,
        "- Raiz do jogo: %s" % src_root,
        "",
        "## Resumo por status",
        "",
    ]
    lines.extend("- %s: %d" % (name, statuses.get(name, 0)) for name in STATUS_ORDER)
    problems = [r for r in records if r["status"] in ("needs_review", "failed")]
    lines.extend(["", "## Itens para revisao ou falhos (%d)" % len(problems), ""])
    if not problems:
        lines.append("- Nenhum.")
    else:
        for record in problems:
            lines.append(
                "- %s | %s | linha %s | %s"
                % (
                    record["row"].get("item_id"),
                    record["row"].get("file"),
                    record["row"].get("line"),
                    "; ".join(record["notes"]) or "sem detalhes",
                )
            )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path


# ---------------------------------------------------------------------------
# Subcomando retry: selecao de itens pelo relatorio existente
# ---------------------------------------------------------------------------


def select_ids_from_report(csv_path, statuses):
    """Le o relatorio CSV e devolve os item_ids com status no conjunto.

    Funcao pura: nenhum arquivo e alterado. O CSV e lido como utf-8-sig
    (mesmo padrao com que este CLI grava, incluindo BOM); a comparacao de
    status ignora caixa e espacos extras; item_id vazio e descartado.
    """
    wanted = {
        str(status).strip().lower() for status in statuses if str(status).strip()
    }
    selected = set()
    with open(csv_path, "r", newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            item_id = str(row.get("item_id") or "").strip()
            status = str(row.get("status") or "").strip().lower()
            if item_id and status in wanted:
                selected.add(item_id)
    return selected


def read_csv_ordered(csv_path):
    """Le o CSV e devolve ``(header, dict_item_id_para_row, list_item_id_order)``.

    Preserva a ordem de insercao (Python 3.7+ dicts sao ordered).
    Se houver item_id duplicado, a ultima ocorrencia vence.
    Cabecalho preservado exatamente como escrito no arquivo.
    """
    with open(csv_path, "r", newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
        rows_by_id = {}
        row_order = []
        for row in reader:
            item_id = str(row.get("item_id") or "").strip()
            if item_id:
                rows_by_id[item_id] = row
                if item_id not in row_order:
                    row_order.append(item_id)
    return header, rows_by_id, row_order


def merge_csv_after_retry(orig_by_id, orig_order, retried_csv_path, out_path):
    """Merge o CSV original (em memoria) com o resultado do retry e reescreve.

    ``orig_by_id`` e ``orig_order`` sao o CSV original ANTES de run_translate
    sobrescreve-lo. ``retried_csv_path`` e o CSV escrito pelo retry.
    Para cada item_id no resultado do retry:
    - Se o status mudou em relacao ao original, substitui a linha;
    - Se o item_id nao existia no original, adiciona.
    Mantem todas as linhas do original que NAO foram re-traduzidas.
    Ordena por (file, line) para consistencia.
    """
    _header_new, new_by_id, new_order = read_csv_ordered(retried_csv_path)

    merged = {}
    order = []
    for item_id in orig_order:
        merged[item_id] = orig_by_id[item_id]
        order.append(item_id)
    for item_id in new_order:
        if item_id not in merged:
            order.append(item_id)
        merged[item_id] = new_by_id[item_id]

    def _sort_key(item_id):
        row = merged[item_id]
        return (str(row.get("file") or ""), int(row.get("line") or 0))

    order.sort(key=_sort_key)

    header = list(CSV_FIELDS)
    with open(out_path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=header)
        writer.writeheader()
        for item_id in order:
            writer.writerow(merged[item_id])


def _parse_statuses(raw):
    """Converte 'failed,needs_review' em conjunto valido; invalido => CliError."""
    statuses = {
        part.strip().lower() for part in str(raw or "").split(",") if part.strip()
    }
    unknown = sorted(statuses - set(STATUS_ORDER))
    if unknown:
        raise CliError(
            "Status desconhecido(s): %s. Validos: %s."
            % (", ".join(unknown), ", ".join(STATUS_ORDER))
        )
    if not statuses:
        raise CliError("Nenhum status valido informado em --statuses.")
    return statuses


def run_translate(
    scan_path,
    out_dir,
    tm_path=None,
    engine=None,
    dry_run=False,
    limit=None,
    tm_global_path=None,
    rows_override=None,
):
    """Executa o fluxo completo de traducao. Engine e injetavel.

    ``tm_global_path`` (opcional) liga o cache global entre jogos: a
    consulta segue a cadeia [global, por-jogo] e os pares novos gravam
    nas DUAS memorias; na global o campo ``file`` sai prefixado com o id
    do jogo (nome da pasta de saida) para auditoria. Sem ele, o fluxo e
    identico ao anterior.

    ``rows_override`` (opcional, usado pelo subcomando retry): linhas ja
    filtradas do scan; quando fornecidas, substituem a carga do JSONL
    (``scan_path`` continua sendo a origem citada nos relatorios).
    """
    scan_path = Path(scan_path)
    out_dir = Path(out_dir)
    if not scan_path.is_file():
        raise CliError("Arquivo de scan nao encontrado: %s" % scan_path)

    if rows_override is None:
        rows, skipped = load_rows(scan_path)
    else:
        # Retry: linhas ja selecionadas pelo relatorio; nada e relido do
        # JSONL nem contado como ignorado. Copia rasa para nao aliasar
        # os dicts do chamador.
        rows = [dict(row) for row in rows_override]
        skipped = 0
    if limit is not None and limit > 0:
        rows = rows[:limit]
    total = len(rows)
    if total == 0:
        raise CliError("Nenhuma linha valida no arquivo de scan: %s" % scan_path)

    print("Linhas validas: %d | ignoradas: %d" % (total, skipped))

    src_root = derive_root(rows)
    if src_root is None or not src_root.is_dir():
        raise CliError("Raiz do jogo nao encontrada nas linhas do scan.")
    try:
        same = src_root.resolve() == out_dir.resolve()
    except OSError:
        same = False
    if same:
        raise CliError("A pasta de saida deve ser diferente da raiz do jogo.")

    game_tm = TMStore(tm_path) if tm_path else None
    global_tm = TMStore(tm_global_path) if tm_global_path else None
    # Ordem fixa da cadeia quando ha as duas memorias: global primeiro,
    # TM por-jogo depois (primeiro acerto vence).
    stores = [store for store in (global_tm, game_tm) if store is not None]
    if len(stores) > 1:
        tm = ChainedTM(stores)
    elif stores:
        tm = stores[0]
    else:
        tm = None
    keys = []
    seen = set()
    for row in rows:
        key = row["text"].strip()
        if key not in seen:
            seen.add(key)
            keys.append(key)

    # Progresso incremental para consumidores do stdout (painel Tk):
    # 0/N logo apos a carga/dedup, depois i/N a cada chunk resolvido.
    progress = _make_progress_printer()
    progress(0, len(keys))

    repairs = {}
    translations, tm_keys, engine_error, failed_keys = resolve_translations(
        keys, tm, engine, on_progress=progress, repairs=repairs
    )
    # Sinal agregado: se TODOS os itens novos falharam individualmente, o
    # problema e sistematico (servidor fora do ar, modelo errado ou resposta
    # sempre malformada) e precisa ficar visivel no log, nao escondida em
    # 940 linhas de CSV com a mesma nota.
    misses_total = sum(1 for key in keys if key not in translations)
    if misses_total and len(failed_keys) >= misses_total:
        print(
            "AVISO: o motor falhou para todos os %d itens novos; verifique "
            "URL/modelo/servidor de traducao." % misses_total
        )
    records = build_records(rows, translations, tm_keys, failed_keys, repairs)

    statuses = Counter()
    result = {
        "loaded": total,
        "skipped": skipped,
        "statuses": statuses,
        "csv_path": None,
        "md_path": None,
        "new_tm_pairs": [],
    }

    if dry_run:
        for record in records:
            if record["translated"] is None:
                record["status"] = "failed"
                notes = ["sem traducao disponivel"]
                if record.get("fail_note"):
                    notes.append(record["fail_note"])
                elif engine_error:
                    notes.append(engine_error)
                record["notes"] = notes
            else:
                record["status"] = "tm_hit" if record["origin"] == "tm" else "llm"
                record["notes"] = list(record.get("repair_notes") or [])
            statuses[record["status"]] += 1
        print("Resumo: " + _summary_line(statuses))
        print("dry-run: nada foi gravado em disco.")
        return result

    rows_by_file = build_rows_by_file(records)
    audits = appliers.apply_to_copy(rows_by_file, src_root, out_dir)
    finalize_records(records, audits, engine_error)
    for record in records:
        statuses[record["status"]] += 1

    out_dir.mkdir(parents=True, exist_ok=True)
    created = _now_iso()
    csv_path = write_csv_report(out_dir, records)
    md_path = write_md_report(out_dir, records, statuses, scan_path, src_root, created)

    new_pairs = collect_new_pairs(records)
    if new_pairs and game_tm is not None:
        game_tm.add_many(new_pairs)
    if new_pairs and global_tm is not None:
        # Cache global auditavel: campo file prefixado com o id do jogo
        # (nome da pasta de saida); a TM por-jogo guarda o caminho cru.
        game_id = str(out_dir.name or "").strip() or "jogo"
        global_tm.add_many(with_global_file_prefix(new_pairs, game_id))

    result.update(csv_path=csv_path, md_path=md_path, new_tm_pairs=new_pairs)
    print("Resumo: " + _summary_line(statuses))
    print("Relatorio CSV: %s" % csv_path)
    print("Relatorio MD: %s" % md_path)
    if game_tm is not None:
        print("Memoria de traducao: %s | novos pares: %d" % (tm_path, len(new_pairs)))
    if global_tm is not None:
        print("Memoria global: %s | novos pares: %d" % (tm_global_path, len(new_pairs)))
    return result


def _summary_line(statuses):
    return " ".join(
        "%s=%d" % (name, statuses.get(name, 0)) for name in STATUS_ORDER
    )


# ---------------------------------------------------------------------------
# Subcomandos protegidos: apply / restore (escrevem na arvore do JOGO)
# ---------------------------------------------------------------------------


def load_manifest(path):
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    return doc if isinstance(doc, dict) else None


def _canonical_path(value):
    """Caminho ABSOLUTO canonico (resolve) para comparar e gravar.

    Aceita caminho relativo ou absoluto; caminho inexistente ainda vira
    absoluto normalizado ancorado no cwd. Nunca lanca para uso interno.
    """
    raw = str(value)
    try:
        return str(Path(raw).resolve())
    except OSError:
        return os.path.abspath(raw)


def _same_path(a, b):
    """Igualdade canonica de caminhos (resolve + normcase; Windows safe)."""
    if a is None or b is None:
        return False
    return os.path.normcase(_canonical_path(a)) == os.path.normcase(_canonical_path(b))


def normalize_manifest_entries(doc):
    """Normaliza e deduplica entradas do manifesto (migrador leve).

    Toda entrada com ``bak`` e regravada com caminho ABSOLUTO canonico.
    Entradas que apontam para o MESMO ``.bak`` fisico (formas relativas e
    absolutas misturadas) sao colapsadas em uma so, mantendo a de ``ts``
    mais recente (com ``file``/``sha256_before``/``ts`` da escolhida).
    Nao altera ``created`` nem o bloco ``restored`` (historico de
    auditoria). Retorna ``(entradas_normalizadas, houve_mudanca)``.
    """
    result = []
    by_key = {}
    changed = False
    for entry in doc.get("entries") or []:
        if not isinstance(entry, dict) or not entry.get("file"):
            changed = True  # entrada corrompida/sem arquivo: descartada
            continue
        bak_raw = str(entry.get("bak") or "")
        if not bak_raw:
            result.append(dict(entry))
            continue
        norm = dict(entry)
        norm["bak"] = _canonical_path(bak_raw)
        key = os.path.normcase(norm["bak"])
        idx = by_key.get(key)
        if idx is None:
            by_key[key] = len(result)
            result.append(norm)
            if norm != entry:
                changed = True
            continue
        changed = True  # duplicata canonica: manter somente a mais recente
        try:
            prev_ts = float(result[idx].get("ts") or 0.0)
            cur_ts = float(norm.get("ts") or 0.0)
        except (TypeError, ValueError):
            prev_ts, cur_ts = 0.0, -1.0
        if cur_ts >= prev_ts:
            result[idx] = norm
    return result, changed


def cmd_apply(translated_dir, game_root, approve):
    """Copia traduzidos sobre o jogo com backup .bak e manifesto.

    Sem aprovacao: nenhuma escrita, exit 3.

    Idempotente: se o arquivo ja possui ``.bak`` e o conteudo atual do jogo
    continua identico ao estado protegido (``sha256_before`` registrado no
    manifesto ou, na falta deste, o hash do proprio ``.bak``), o apply
    REAPLICA a copia traduzida MANTENDO o ``.bak`` original byte-identico
    (nao regenera backup nem duplica entrada no manifesto). Se o arquivo do
    jogo mudou desde entao (modificacao externa), aquele arquivo e ABORTADO
    com nota clara e nada e escrito nele.

    Codigos de saida: 0 ok | 2 entrada invalida ou falha de gravacao |
    3 sem aprovacao | 4 nada aplicado (arquivo(s) protegido(s)).
    """
    if not approve:
        print("ERRO: escrita nos arquivos do jogo exige --i-approve-write-game-files.")
        print("Nada foi gravado.")
        return 3

    translated_dir = Path(translated_dir)
    game_root = Path(game_root)
    if not translated_dir.is_dir():
        print("ERRO: pasta traduzida nao encontrada: %s" % translated_dir)
        return 2
    if not game_root.is_dir():
        print("ERRO: raiz do jogo nao encontrada: %s" % game_root)
        return 2

    candidates = []
    for path in sorted(translated_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(translated_dir).as_posix()
        if rel in NON_GAME_FILES or rel.endswith(".tmp"):
            continue
        candidates.append((rel, path))

    manifest_path = translated_dir / MANIFEST_NAME
    old_doc = load_manifest(manifest_path)
    old_total = 0
    old_entries = []
    migrated = False
    if old_doc is not None:
        manifest_root = str(old_doc.get("game_root") or "")
        if manifest_root and not _same_path(manifest_root, game_root):
            print(
                "ERRO: manifesto pertence a outra raiz de jogo: %s"
                % manifest_root
            )
            print("Nada foi gravado.")
            return 2
        # Migrador leve: manifesto antigo com entradas relativas/absolutas
        # duplicadas e normalizado+dedupado na carga; ``created`` e o bloco
        # ``restored`` permanecem intactos (o regravamento acontece junto da
        # escrita unica do manifesto, antes de qualquer escrita no jogo).
        old_total = len(old_doc.get("entries") or [])
        old_entries, migrated = normalize_manifest_entries(old_doc)
        if migrated:
            print(
                "Nota: manifesto anterior regravado normalizado/deduplicado"
                " (%d -> %d entradas)." % (old_total, len(old_entries))
            )
    registered_by_file = {}
    for entry in old_entries:
        registered_by_file[str(entry.get("file"))] = entry

    plan = []       # tudo que sera escrito (backup novo ou reaproveitado)
    protected = []  # (rel, motivo): jogo mudou desde o backup; nao escrever
    missing = []
    for rel, source_path in candidates:
        original = _safe_game_path(game_root, rel)
        if original is None or not original.is_file():
            missing.append(rel)
            continue
        bak = Path(str(original) + ".bak")
        if not bak.exists():
            plan.append(
                {
                    "file": rel,
                    "bak": _canonical_path(bak),
                    "sha256_before": sha256_of(original),
                    "ts": time.time(),
                    "_orig": original,
                    "_src": source_path,
                    "_keep_bak": False,
                    "_registered": False,
                }
            )
            continue
        # .bak ja existe: reaplicar so se o jogo ainda estiver no estado
        # protegido; caso contrario aborta aquele arquivo com nota clara.
        current_hash = sha256_of(original)
        registered = registered_by_file.get(rel)
        trusted_hash = None
        if registered is not None and _same_path(registered.get("bak"), str(bak)):
            # Comparacao canonica: manifesto antigo pode ter gravado o .bak
            # em forma relativa ou absoluta; o arquivo fisico e o mesmo.
            trusted_hash = str(registered.get("sha256_before") or "") or None
        reference_hash = trusted_hash
        if reference_hash is None:
            # .bak orfao (manifesto ausente/perdido): o proprio .bak define
            # o estado original conhecido.
            try:
                reference_hash = sha256_of(bak)
            except OSError:
                reference_hash = None
        if reference_hash is None or current_hash != reference_hash:
            protected.append(
                (
                    rel,
                    "jogo mudou desde o backup; .bak preservado",
                )
            )
            continue
        plan.append(
            {
                "file": rel,
                "bak": _canonical_path(bak),
                "sha256_before": reference_hash,
                "ts": (
                    float(registered.get("ts"))
                    if trusted_hash is not None and registered.get("ts")
                    else time.time()
                ),
                "_orig": original,
                "_src": source_path,
                "_keep_bak": True,
                # Entrada ja registrada no manifesto nao pode duplicar;
                # orfaos ganham registro novo com o hash do proprio .bak.
                "_registered": trusted_hash is not None,
            }
        )

    doc = old_doc or {"created": _now_iso(), "entries": []}
    doc["game_root"] = _canonical_path(game_root)
    doc["entries"] = old_entries + [
        {key: entry[key] for key in ("file", "bak", "sha256_before", "ts")}
        for entry in plan
        if not entry["_registered"]
    ]
    # Manifesto gravado ANTES da primeira escrita no jogo.
    _atomic_write_text(
        manifest_path, json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    )

    written = 0
    reused = 0
    failures = []
    for entry in plan:
        original = entry["_orig"]
        bak = Path(entry["bak"])
        if entry["_keep_bak"]:
            # Reaplicacao idempotente: o .bak original permanece intocado;
            # apenas confirma que segue legivel antes de sobrescrever o jogo.
            reused += 1
            try:
                bak.read_bytes()
            except OSError as exc:
                failures.append((entry["file"], _ascii(exc)))
                continue
        else:
            data = original.read_bytes()
            try:
                bak.write_bytes(data)
                if bak.read_bytes() != data:
                    raise OSError("backup divergente apos gravar")
            except OSError as exc:
                failures.append((entry["file"], _ascii(exc)))
                continue
        try:
            original.write_bytes(entry["_src"].read_bytes())
        except OSError as exc:
            failures.append((entry["file"], _ascii(exc)))
            continue
        written += 1

    print(
        "Aplicados: %d | backup reaproveitado: %d | protegidos (jogo mudou): %d"
        " | sem original: %d"
        % (written, reused, len(protected), len(missing))
    )
    for entry in plan:
        if entry["_keep_bak"]:
            print("  reaplicado, backup original mantido: %s" % entry["file"])
    for rel, motivo in protected:
        print("  abortado, %s: %s" % (motivo, rel))
    for rel in missing:
        print("  ignorado, original ausente no jogo: %s" % rel)
    for rel, detail in failures:
        print("  falha ao gravar: %s (%s)" % (rel, detail))

    if failures:
        return 2
    if written == 0 and protected:
        return 4
    return 0


def cmd_restore(manifest_path):
    """Copia cada .bak de volta e valida o sha256; registra ``restored``."""
    manifest_path = Path(manifest_path)
    if not manifest_path.is_file():
        print("ERRO: manifesto nao encontrado: %s" % manifest_path)
        return 2
    doc = load_manifest(manifest_path)
    if doc is None:
        print("ERRO: manifesto invalido (JSON): %s" % manifest_path)
        return 2

    entries = doc.get("entries") or []
    restored = []
    ok_count = 0
    failures = 0
    for entry in entries:
        rel = str(entry.get("file") or "")
        bak_str = str(entry.get("bak") or "")
        expected = str(entry.get("sha256_before") or "")
        record = {"file": rel}
        # Leitura canonica: manifestos antigos podem ter ``bak`` relativo
        # (gravado com --game-root relativo); resolve contra o cwd atual,
        # mesma ancoragem usada quando foi gravado. Entrada nao e alterada.
        bak_canon = _canonical_path(bak_str) if bak_str else ""
        bak = Path(bak_canon) if bak_canon else None
        original = (
            Path(bak_canon[: -len(".bak")]) if bak_canon.endswith(".bak") else None
        )
        if bak is None or original is None or not bak.is_file():
            record["ok"] = False
            record["motivo"] = "backup ausente"
            failures += 1
        else:
            try:
                original.parent.mkdir(parents=True, exist_ok=True)
                data = bak.read_bytes()
                original.write_bytes(data)
            except OSError as exc:
                record["ok"] = False
                record["motivo"] = _ascii(exc)
                failures += 1
            else:
                actual = sha256_of(original)
                record["sha256_after"] = actual
                record["ok"] = bool(expected) and actual == expected
                if record["ok"]:
                    ok_count += 1
                else:
                    failures += 1
        restored.append(record)

    # APPEND da lista ``restored`` no mesmo manifesto (backups preservados).
    doc["restored"] = restored
    _atomic_write_text(
        manifest_path, json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    )
    print("Restaurados: %d | falhas: %d" % (ok_count, failures))
    return 0 if failures == 0 else 2


# ---------------------------------------------------------------------------
# Interface de linha de comando
# ---------------------------------------------------------------------------


def _build_engine(chunk_size, engine_url, engine_model):
    """Valida --chunk-size e constroi o motor; entrada invalida => CliError."""
    if not MIN_CHUNK_SIZE <= chunk_size <= MAX_CHUNK_SIZE:
        raise CliError(
            "--chunk-size deve estar entre %d e %d (recebido %d)."
            % (MIN_CHUNK_SIZE, MAX_CHUNK_SIZE, chunk_size)
        )
    return OpenAICompatEngine(
        base_url=engine_url or DEFAULT_ENGINE_URL,
        model=engine_model or DEFAULT_ENGINE_MODEL,
        timeout=60,
        retries=1,
        chunk_size=chunk_size,
    )


def cmd_translate_cli(argv):
    parser = argparse.ArgumentParser(
        prog="translate_game_text.py",
        description="Traduz textos de um scan JSONL gerando copias seguras e relatorios.",
    )
    parser.add_argument("scan", help="Arquivo JSONL produzido pelo extrator.")
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Pasta de saida das copias traduzidas (unica area escrita).",
    )
    parser.add_argument(
        "--tm", default=None, help="Arquivo JSONL da memoria de traducao (opcional)."
    )
    parser.add_argument(
        "--tm-global",
        default=None,
        help=(
            "Arquivo JSONL do cache global entre jogos (consultado ANTES da "
            "TM por-jogo; pares novos gravam nas duas memorias)."
        ),
    )
    parser.add_argument(
        "--engine-url",
        default=None,
        help="URL base compativel com OpenAI (padrao Ollama local).",
    )
    parser.add_argument(
        "--engine-model", default=None, help="Modelo usado pelo motor de traducao."
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=(
            "Textos por requisicao ao motor (de %d a %d; padrao %d)."
            % (MIN_CHUNK_SIZE, MAX_CHUNK_SIZE, DEFAULT_CHUNK_SIZE)
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nao grava nada em disco; apenas mostra o resultado.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Processa apenas os N primeiros itens validos.",
    )
    args = parser.parse_args(argv)

    try:
        engine = _build_engine(args.chunk_size, args.engine_url, args.engine_model)
    except CliError as exc:
        print("ERRO: %s" % exc)
        return exc.exit_code
    try:
        run_translate(
            scan_path=args.scan,
            out_dir=args.out_dir,
            tm_path=args.tm,
            engine=engine,
            dry_run=args.dry_run,
            limit=args.limit,
            tm_global_path=args.tm_global,
        )
    except CliError as exc:
        print("ERRO: %s" % exc)
        return exc.exit_code
    return 0


def cmd_apply_cli(argv):
    parser = argparse.ArgumentParser(
        prog="translate_game_text.py apply",
        description=(
            "Copia os arquivos traduzidos por cima do jogo, criando backup "
            ".bak byte-identico e applied_manifest.json."
        ),
    )
    parser.add_argument(
        "--translated-dir", required=True, help="Pasta com os arquivos traduzidos."
    )
    parser.add_argument(
        "--game-root", required=True, help="Raiz do jogo que recebera as traducoes."
    )
    parser.add_argument(
        "--i-approve-write-game-files",
        action="store_true",
        help="Aprovacao obrigatoria para escrever nos arquivos do jogo.",
    )
    args = parser.parse_args(argv)
    return cmd_apply(args.translated_dir, args.game_root, args.i_approve_write_game_files)


def cmd_restore_cli(argv):
    parser = argparse.ArgumentParser(
        prog="translate_game_text.py restore",
        description="Restaura os originais do jogo a partir dos .bak do manifesto.",
    )
    parser.add_argument(
        "--manifest", required=True, help="Caminho do applied_manifest.json."
    )
    args = parser.parse_args(argv)
    return cmd_restore(args.manifest)


def cmd_retry(args, engine, statuses=None):
    """Re-traduz apenas os itens selecionados do relatorio existente.

    Le o ``translation_report.csv`` da pasta de saida, filtra as linhas
    do scan pelos item_ids com status escolhido e roda ``run_translate``
    com esse subconjunto; CSV/MD sao regravados normalmente ao final.
    Com ``--force-engine`` toda memoria de traducao e bypassada; sem ele
    vale a cadeia normal (global antes da por-jogo).
    """
    if statuses is None:
        statuses = _parse_statuses(args.statuses)
    out_dir = Path(args.out_dir)
    csv_path = out_dir / REPORT_CSV
    if not csv_path.is_file():
        raise CliError(
            "Relatorio CSV nao encontrado: %s. Rode a traducao antes do retry."
            % csv_path
        )

    label = ", ".join(sorted(statuses))
    selected_ids = select_ids_from_report(csv_path, statuses)
    if not selected_ids:
        print("Nenhum item com status %s no relatorio; nada a re-traduzir." % label)
        return 0

    scan_path = Path(args.scan)
    if not scan_path.is_file():
        raise CliError("Arquivo de scan nao encontrado: %s" % scan_path)
    rows, _skipped = load_rows(scan_path)
    chosen_rows = [row for row in rows if str(row.get("item_id")) in selected_ids]
    print(
        "Retry: %d item(ns) com status %s no relatorio; %d presente(s) no scan."
        % (len(selected_ids), label, len(chosen_rows))
    )
    if not chosen_rows:
        print("ERRO: nenhum item selecionado foi encontrado no scan informado.")
        return 2

    tm_path = None
    tm_global_path = None
    if args.force_engine:
        print(
            "retry --force-engine: memoria de traducao bypassada; "
            "itens selecionados vao direto ao motor."
        )
    else:
        tm_path = args.tm
        tm_global_path = args.tm_global

    # Backup do CSV original em memoria ANTES de run_translate sobrescreve-lo
    _orig_header, orig_by_id, orig_order = read_csv_ordered(csv_path)

    result = run_translate(
        scan_path=scan_path,
        out_dir=out_dir,
        tm_path=tm_path,
        engine=engine,
        dry_run=False,
        limit=None,
        tm_global_path=tm_global_path,
        rows_override=chosen_rows,
    )

    # --- merge: preservar linhas originais nao re-traduzidas ---
    retried_csv = result["csv_path"]
    if retried_csv is not None and retried_csv.is_file():
        merge_csv_after_retry(orig_by_id, orig_order, retried_csv, retried_csv)
        # Regenerar MD a partir do CSV mergesado (contagens completas)
        merged_header, merged_by_id, merged_order = read_csv_ordered(retried_csv)
        merged_records = []
        statuses = Counter()
        for item_id in merged_order:
            row = merged_by_id[item_id]
            merged_records.append(
                {
                    "row": row,
                    "status": str(row.get("status") or "failed"),
                }
            )
            statuses[str(row.get("status") or "failed")] += 1
        # Reconstruir records no formato esperado por write_md_report
        md_records = []
        for rec in merged_records:
            r = rec["row"]
            md_records.append(
                {
                    "row": {
                        "item_id": r.get("item_id", ""),
                        "file": r.get("file", ""),
                        "line": r.get("line", ""),
                    },
                    "status": rec["status"],
                    "notes": [n.strip() for n in r.get("notes", "").split(";") if n.strip()],
                }
            )
        write_md_report(out_dir, md_records, statuses, scan_path,
                        derive_root(chosen_rows) or out_dir, _now_iso())

    return 0


def cmd_retry_cli(argv):
    parser = argparse.ArgumentParser(
        prog="translate_game_text.py retry",
        description=(
            "Re-traduz apenas os itens failed/needs_review de um relatorio "
            "existente, regravando o CSV/MD ao final."
        ),
    )
    parser.add_argument(
        "--scan", required=True, help="Arquivo JSONL original do extrator."
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Pasta da copia traduzida que ja contem translation_report.csv.",
    )
    parser.add_argument(
        "--statuses",
        default="failed,needs_review",
        help=(
            "Status que serao re-traduzidos, separados por virgula "
            "(padrao: failed,needs_review; validos: %s)." % ", ".join(STATUS_ORDER)
        ),
    )
    parser.add_argument(
        "--force-engine",
        action="store_true",
        help="Ignora toda memoria de traducao e envia os itens ao motor.",
    )
    parser.add_argument(
        "--tm", default=None, help="Memoria por-jogo usada na cadeia normal."
    )
    parser.add_argument(
        "--tm-global", default=None, help="Cache global usado na cadeia normal."
    )
    parser.add_argument(
        "--engine-url",
        default=None,
        help="URL base compativel com OpenAI (padrao Ollama local).",
    )
    parser.add_argument(
        "--engine-model", default=None, help="Modelo usado pelo motor de traducao."
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=(
            "Textos por requisicao ao motor (de %d a %d; padrao %d)."
            % (MIN_CHUNK_SIZE, MAX_CHUNK_SIZE, DEFAULT_CHUNK_SIZE)
        ),
    )
    args = parser.parse_args(argv)
    try:
        # Status invalido precisa falhar ANTES de construir o motor
        # (mesma filosofia do --chunk-size fora de faixa).
        statuses = _parse_statuses(args.statuses)
        engine = _build_engine(args.chunk_size, args.engine_url, args.engine_model)
        return cmd_retry(args, engine, statuses)
    except CliError as exc:
        print("ERRO: %s" % exc)
        return exc.exit_code


# ---------------------------------------------------------------------------
# Subcomando no-tokens: traducao apenas com memoria/glossario
# ---------------------------------------------------------------------------

NO_TOKENS_CSV = "no_tokens_report.csv"
NO_TOKENS_MD = "pendencias.md"
NO_TOKENS_STATUS_ORDER = ("tm_hit", "pending")


def cmd_no_tokens(scan_path, out_dir, engine_name, tm_path=None, tm_global_path=None):
    """Gera pacote usando apenas memoria/glossario existente, sem chamar LLM.

    Le o scan JSONL e, para cada row, consulta o TranslationDB (por hash) e
    o ChainedTM. Textos com HIT: status=tm_hit. Textos NOVOS: status=pending.
    Gera CSV ``no_tokens_report.csv`` e relatorio ``pendencias.md``.

    Exit code: 0 se todos traduzidos, 1 se ha pendencias.
    """
    scan_path = Path(scan_path)
    out_dir = Path(out_dir)
    if not scan_path.is_file():
        raise CliError("Arquivo de scan nao encontrado: %s" % scan_path)

    rows, skipped = load_rows(scan_path)
    if not rows:
        raise CliError("Nenhuma linha valida no arquivo de scan: %s" % scan_path)

    # Monta a cadeia de TM (por-jogo + global, mesma logica do translate)
    game_tm = TMStore(tm_path) if tm_path else None
    global_tm = TMStore(tm_global_path) if tm_global_path else None
    stores = [store for store in (global_tm, game_tm) if store is not None]
    if len(stores) > 1:
        tm = ChainedTM(stores)
    elif stores:
        tm = stores[0]
    else:
        tm = None

    # Classifica cada row
    records = []
    seen_keys = set()
    for row in rows:
        key = str(row.get("text") or "").strip()
        if not key:
            continue

        hit = None
        if tm is not None:
            raw_hit = tm.lookup(key)
            if isinstance(raw_hit, tuple):
                hit = raw_hit[0] if raw_hit[0] else None
            else:
                hit = raw_hit

        if hit:
            status = "tm_hit"
            translated = hit
            notes = "traducao encontrada na memoria"
        else:
            status = "pending"
            translated = ""
            notes = "precisa de traducao externa"

        records.append({
            "row": row,
            "key": key,
            "status": status,
            "translated": translated,
            "notes": notes,
        })

    # Grava CSV
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / NO_TOKENS_CSV
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["item_id", "status", "file", "line", "source_key",
                        "source", "translated", "notes"],
        )
        writer.writeheader()
        for rec in records:
            row = rec["row"]
            writer.writerow({
                "item_id": str(row.get("item_id") or ""),
                "status": rec["status"],
                "file": str(row.get("file") or ""),
                "line": _line_number(row.get("line")),
                "source_key": str(row.get("source_key") or ""),
                "source": rec["key"],
                "translated": rec["translated"],
                "notes": rec["notes"],
            })

    # Contagens
    total = len(records)
    translated_count = sum(1 for r in records if r["status"] == "tm_hit")
    pending_count = sum(1 for r in records if r["status"] == "pending")

    # Gera pendencias.md
    md_path = out_dir / NO_TOKENS_MD
    created = _now_iso()
    md_lines = [
        "# Relatorio de pendencias (no-tokens)",
        "",
        "- Gerado em: %s" % created,
        "- Origem: %s" % scan_path,
        "- Engine name: %s" % engine_name,
        "",
        "## Resumo",
        "",
        "- Total de textos: %d" % total,
        "- Traduzidos por TM/DB: %d" % translated_count,
        "- Pendentes de traducao: %d" % pending_count,
        "",
    ]

    if pending_count > 0:
        md_lines.append("## Pendentes (top 50)")
        md_lines.append("")
        # Agrupa pendentes por arquivo
        pending_by_file = {}
        for rec in records:
            if rec["status"] == "pending":
                file_key = str(rec["row"].get("file") or "desconhecido")
                pending_by_file.setdefault(file_key, []).append(rec)

        shown = 0
        for file_key in sorted(pending_by_file.keys()):
            if shown >= 50:
                break
            md_lines.append("### %s" % file_key)
            md_lines.append("")
            for rec in pending_by_file[file_key]:
                if shown >= 50:
                    break
                line_num = rec["row"].get("line", "?")
                md_lines.append(
                    "- Linha %s: %s" % (line_num, rec["key"][:200])
                )
                shown += 1
            md_lines.append("")
    else:
        md_lines.append("Nenhum texto pendente. Todos ja possuem traducao na memoria.")
        md_lines.append("")

    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print("Resumo: tm_hit=%d pending=%d" % (translated_count, pending_count))
    print("CSV: %s" % csv_path)
    print("Relatorio: %s" % md_path)

    if pending_count > 0:
        return 1
    return 0


def cmd_no_tokens_cli(argv):
    parser = argparse.ArgumentParser(
        prog="translate_game_text.py no-tokens",
        description=(
            "Gera pacote de traducao usando apenas memoria/glossario "
            "existente, sem chamar LLM. Lista pendencias."
        ),
    )
    parser.add_argument(
        "--scan", required=True, help="Arquivo JSONL produzido pelo extrator."
    )
    parser.add_argument(
        "--out-dir", required=True,
        help="Pasta de saida do relatorio e CSV.",
    )
    parser.add_argument(
        "--engine-name", required=True,
        help="Nome identificador do engine/jogo (usado no relatorio).",
    )
    parser.add_argument(
        "--tm", default=None, help="Arquivo JSONL da memoria de traducao (opcional)."
    )
    parser.add_argument(
        "--tm-global", default=None,
        help="Arquivo JSONL do cache global entre jogos (opcional).",
    )
    args = parser.parse_args(argv)
    try:
        return cmd_no_tokens(
            scan_path=args.scan,
            out_dir=args.out_dir,
            engine_name=args.engine_name,
            tm_path=args.tm,
            tm_global_path=args.tm_global,
        )
    except CliError as exc:
        print("ERRO: %s" % exc)
        return exc.exit_code


# ---------------------------------------------------------------------------
# Subcomando low-cost: traducao seletiva com filtros
# ---------------------------------------------------------------------------

LOW_COST_CSV = "low_cost_report.csv"
LOW_COST_MD = "low_cost_report.md"


def cmd_low_cost(
    scan_path,
    out_dir,
    chunk_size=DEFAULT_CHUNK_SIZE,
    threshold=3,
    engine_url=None,
    engine_model=None,
    engine=None,
    tm_path=None,
    tm_global_path=None,
):
    """Traduz apenas textos novos, repetidos de alto impacto ou ambiguo.

    Filtra o scan usando ``classify_lowcost`` e envia ao LLM somente o
    subconjunto filtrado. Textos com hit no TM sao gravados direto.
    Textos que nao atendem criterios sao marcados como skip.

    Gera CSV ``low_cost_report.csv`` e relatorio ``low_cost_report.md``.
    """
    scan_path = Path(scan_path)
    out_dir = Path(out_dir)
    if not scan_path.is_file():
        raise CliError("Arquivo de scan nao encontrado: %s" % scan_path)

    rows, skipped = load_rows(scan_path)
    if not rows:
        raise CliError("Nenhuma linha valida no arquivo de scan: %s" % scan_path)

    # Monta TM
    game_tm = TMStore(tm_path) if tm_path else None
    global_tm = TMStore(tm_global_path) if tm_global_path else None
    stores = [store for store in (global_tm, game_tm) if store is not None]
    if len(stores) > 1:
        tm = ChainedTM(stores)
    elif stores:
        tm = stores[0]
    else:
        tm = None

    # Classifica
    to_translate, skip_items, tm_hits = classify_lowcost(rows, tm, threshold)

    # Constroi records para CSV (tm_hits direto)
    records = []
    for rec in tm_hits:
        records.append({
            "row": rec["row"],
            "key": rec["key"],
            "translated": rec["translated"],
            "origin": "tm",
            "status": "tm_hit",
            "notes": "traducao encontrada na memoria",
        })

    # Registros de skip
    for rec in skip_items:
        records.append({
            "row": rec["row"],
            "key": rec["key"],
            "translated": "",
            "origin": None,
            "status": "skip",
            "notes": "texto nao atende criterios de alto impacto",
        })

    # Traduzir: envia ao LLM se houver engine e itens
    llm_translations = {}
    if to_translate and engine is not None:
        keys_to_send = [item["key"] for item in to_translate]
        if keys_to_send:
            try:
                resilient = getattr(engine, "translate_batch_resilient", None)
                if resilient is not None:
                    outputs, failed_indices = resilient(keys_to_send)
                    failed_set = set(failed_indices or [])
                    for idx, key in enumerate(keys_to_send):
                        if idx not in failed_set:
                            llm_translations[key] = outputs[idx]
                else:
                    outputs = engine.translate_batch(keys_to_send)
                    for key, target in zip(keys_to_send, outputs):
                        llm_translations[key] = target
            except TranslationError as exc:
                print("AVISO: motor falhou: %s" % _ascii(exc))

    # Adiciona registros LLM
    for item in to_translate:
        translated = llm_translations.get(item["key"], "")
        if translated:
            status = "llm"
            origin = "llm"
            notes = "traduzido por LLM (%s)" % ", ".join(item["reasons"])
        else:
            status = "failed"
            origin = None
            reasons_str = ", ".join(item.get("reasons", []))
            notes = "falha na traducao ou motor indisponivel"
            if reasons_str:
                notes += " [%s]" % reasons_str
        records.append({
            "row": item["row"],
            "key": item["key"],
            "translated": translated,
            "origin": origin,
            "status": status,
            "notes": notes,
        })

    # Ordena por (file, line)
    def _sort_key(rec):
        row = rec["row"]
        return (str(row.get("file") or ""), _line_number(row.get("line")))

    records.sort(key=_sort_key)

    # Grava CSV
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / LOW_COST_CSV
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["item_id", "status", "file", "line", "source_key",
                        "source", "translated", "notes"],
        )
        writer.writeheader()
        for rec in records:
            row = rec["row"]
            writer.writerow({
                "item_id": str(row.get("item_id") or ""),
                "status": rec["status"],
                "file": str(row.get("file") or ""),
                "line": _line_number(row.get("line")),
                "source_key": str(row.get("source_key") or ""),
                "source": rec["key"],
                "translated": rec.get("translated", ""),
                "notes": rec.get("notes", ""),
            })

    # Contagens
    status_counts = Counter(r["status"] for r in records)
    created = _now_iso()

    # Grava MD
    md_path = out_dir / LOW_COST_MD
    md_lines = [
        "# Relatorio low-cost",
        "",
        "- Gerado em: %s" % created,
        "- Origem: %s" % scan_path,
        "- Threshold de repeticao: %d" % threshold,
        "",
        "## Resumo por status",
        "",
    ]
    for name in ("tm_hit", "llm", "skip", "failed"):
        md_lines.append("- %s: %d" % (name, status_counts.get(name, 0)))
    md_lines.extend([
        "",
        "## Detalhamento",
        "",
        "- Textos com hit no TM (sem tokens): %d" % status_counts.get("tm_hit", 0),
        "- Textos enviados ao LLM: %d" % len(to_translate),
        "- Textos skippados (baixa prioridade): %d" % len(skip_items),
        "",
    ])

    if status_counts.get("failed", 0) > 0:
        md_lines.append("## Falhas na traducao")
        md_lines.append("")
        for rec in records:
            if rec["status"] == "failed":
                md_lines.append(
                    "- %s | %s | linha %s | %s"
                    % (
                        rec["row"].get("item_id"),
                        rec["row"].get("file"),
                        rec["row"].get("line"),
                        rec.get("notes", "sem detalhes"),
                    )
                )
        md_lines.append("")

    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    # Grava novos pares na TM
    new_pairs = []
    for rec in records:
        if rec["status"] == "llm" and rec.get("translated"):
            new_pairs.append({
                "source": rec["key"],
                "target": rec["translated"],
                "file": str(rec["row"].get("file") or ""),
                "item_id": str(rec["row"].get("item_id") or ""),
            })
    if new_pairs and game_tm is not None:
        game_tm.add_many(new_pairs)
    if new_pairs and global_tm is not None:
        game_id = str(out_dir.name or "").strip() or "jogo"
        global_tm.add_many(with_global_file_prefix(new_pairs, game_id))

    print(
        "Resumo: tm_hit=%d llm=%d skip=%d failed=%d"
        % (
            status_counts.get("tm_hit", 0),
            status_counts.get("llm", 0),
            status_counts.get("skip", 0),
            status_counts.get("failed", 0),
        )
    )
    print("CSV: %s" % csv_path)
    print("Relatorio: %s" % md_path)
    if game_tm is not None:
        print("Memoria de traducao: %s | novos pares: %d" % (tm_path, len(new_pairs)))
    if global_tm is not None:
        print("Memoria global: %s | novos pares: %d" % (tm_global_path, len(new_pairs)))

    return 0


def cmd_low_cost_cli(argv):
    parser = argparse.ArgumentParser(
        prog="translate_game_text.py low-cost",
        description=(
            "Traduz apenas textos novos, repetidos de alto impacto ou "
            "ambiguo (CJK denso). Textos com hit no TM sao gravados direto."
        ),
    )
    parser.add_argument(
        "--scan", required=True, help="Arquivo JSONL produzido pelo extrator."
    )
    parser.add_argument(
        "--out-dir", required=True,
        help="Pasta de saida do relatorio e CSV.",
    )
    parser.add_argument(
        "--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE,
        help="Textos por requisicao ao motor (de %d a %d; padrao %d)."
        % (MIN_CHUNK_SIZE, MAX_CHUNK_SIZE, DEFAULT_CHUNK_SIZE),
    )
    parser.add_argument(
        "--threshold", type=int, default=3,
        help="Ocorrencias minimas para considerar texto repetido (padrao 3).",
    )
    parser.add_argument(
        "--engine-url", default=None,
        help="URL base compativel com OpenAI (padrao Ollama local).",
    )
    parser.add_argument(
        "--engine-model", default=None,
        help="Modelo usado pelo motor de traducao.",
    )
    parser.add_argument(
        "--tm", default=None, help="Arquivo JSONL da memoria de traducao (opcional)."
    )
    parser.add_argument(
        "--tm-global", default=None,
        help="Arquivo JSONL do cache global entre jogos (opcional).",
    )
    args = parser.parse_args(argv)
    try:
        engine = None
        if args.engine_url or args.engine_model:
            engine = _build_engine(args.chunk_size, args.engine_url, args.engine_model)
        return cmd_low_cost(
            scan_path=args.scan,
            out_dir=args.out_dir,
            chunk_size=args.chunk_size,
            threshold=args.threshold,
            engine_url=args.engine_url,
            engine_model=args.engine_model,
            engine=engine,
            tm_path=args.tm,
            tm_global_path=args.tm_global,
        )
    except CliError as exc:
        print("ERRO: %s" % exc)
        return exc.exit_code


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "apply":
        return cmd_apply_cli(argv[1:])
    if argv and argv[0] == "restore":
        return cmd_restore_cli(argv[1:])
    if argv and argv[0] == "retry":
        return cmd_retry_cli(argv[1:])
    if argv and argv[0] == "no-tokens":
        return cmd_no_tokens_cli(argv[1:])
    if argv and argv[0] == "low-cost":
        return cmd_low_cost_cli(argv[1:])
    return cmd_translate_cli(argv)


if __name__ == "__main__":
    sys.exit(main())
