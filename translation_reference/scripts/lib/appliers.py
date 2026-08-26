# -*- coding: utf-8 -*-
"""Aplica traducoes gerando COPIAS em ``out_root``; originais nunca mudam.

Componente do design aprovado em 2026-08-22
(docs/superpowers/specs/2026-08-22-tradutor-local-design.md).

Contrato de ``apply_to_copy``
----------------------------
- Recebe ``rows_by_file`` mapeando caminho relativo (barras "/") -> lista de
  rows do extrator (extract_non_english_text.py) com o campo extra
  ``translated`` adicionado pelo chamador.
- Grava somente dentro de ``out_root``. Se ``out_root == src_root`` levanta
  ``ValueError`` para proteger os arquivos originais.
- Arquivos linha-a-linha (.txt/.ks/.rpy/.csv e demais nao-.json): substitui
  apenas a linha indicada pelo campo ``line``; quando o trecho escaneado
  aparece embutido na linha (ex.: literal .rpy dentro de codigo), troca so a
  ocorrencia e preserva o resto da linha. Encoding, BOM e CRLF/LF sao
  preservados byte-a-byte nas regioes nao alteradas.
- JSON (.json RPG Maker MV/MZ): aplica nos caminhos ``source_key`` (ex.
  ``$[1].name`` ou ``$.actors[0].name``), trocando o valor e mantendo chave,
  ordem e estrutura. Dump com ``ensure_ascii=False`` e separadores compactos
  estaveis (",", ":").
- Validacao integrada: ``placeholders.validate_pair`` precisa passar; caso
  contrario a row NAO e aplicada e recebe status ``needs_review``.

Status de auditoria por row:
- ``applied``      traducao gravada na copia.
- ``needs_review`` problema na traducao (placeholder ausente, trecho nao
                   localizado, encoding destino etc.); linha/valor original
                   preservado.
- ``failed``       erro operacional (arquivo ausente, linha fora do intervalo,
                   caminho invalido, verificacao estrutural).
"""

import json
import re
from pathlib import Path, PurePosixPath

try:  # importado como pacote (scripts.lib.appliers)
    from . import placeholders
except ImportError:  # import direto com scripts/lib no sys.path
    import placeholders

__all__ = ["apply_to_copy"]

BOM_UTF8 = b"\xef\xbb\xbf"

# Mesma classe de caracteres usada por verify_translation.py.
JP_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")

SUPPORTED_ENCODINGS = ("utf-8", "utf-8-sig", "cp932", "shift_jis", "latin-1")

ENCODING_ALIASES = {
    "utf8": "utf-8",
    "utf_8": "utf-8",
    "utf8sig": "utf-8-sig",
    "utf_8_sig": "utf-8-sig",
    "ms932": "cp932",
    "shiftjis": "shift_jis",
    "shift-jis": "shift_jis",
    "sjis": "shift_jis",
    "latin1": "latin-1",
    "iso-8859-1": "latin-1",
    "iso8859-1": "latin-1",
}


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------


def _norm_encoding(value):
    """Normaliza o nome do encoding; devolve None se nao suportado."""
    name = str(value or "").strip().lower()
    if not name:
        return None
    name = ENCODING_ALIASES.get(name, name)
    if name in SUPPORTED_ENCODINGS:
        return name
    compact = name.replace("-", "").replace("_", "")
    for supported in SUPPORTED_ENCODINGS:
        if compact == supported.replace("-", ""):
            return supported
    return None


def _safe_join(root_path, rel_path):
    """Junta caminho relativo garantindo que permanece dentro de root."""
    parts = [p for p in str(rel_path).replace("\\", "/").split("/") if p not in ("", ".")]
    if not parts:
        return None
    first = parts[0]
    # Rejeita caminhos absolutos (inclui drive Windows tipo "C:") e "..".
    if ":" in first or str(rel_path).lstrip().startswith(("/", "\\")):
        return None
    if any(part == ".." for part in parts):
        return None
    candidate = Path(root_path).joinpath(*parts)
    try:
        candidate.resolve().relative_to(Path(root_path).resolve())
    except ValueError:
        return None
    return candidate


def _make_audit(rel_file, row, status, notes):
    try:
        line_no = int(row.get("line") or 0)
    except (TypeError, ValueError):
        line_no = 0
    return {
        "file": rel_file,
        "item_id": str(row.get("item_id") or ""),
        "line": line_no,
        "source_key": str(row.get("source_key") or ""),
        "status": status,
        "notes": [str(note) for note in notes],
    }


def _split_byte_lines(raw):
    """Divide bytes em pares (conteudo, final_de_linha).

    Seguro para utf-8/cp932/shift_jis/latin-1: em nenhum desses encodings os
    bytes 0x0A/0x0D aparecem dentro de caracteres multibyte.
    """
    chunks = []
    start = 0
    i = 0
    n = len(raw)
    while i < n:
        byte = raw[i]
        if byte == 10:
            end, eol, i = i, b"\n", i + 1
        elif byte == 13:
            end, eol = i, b"\r"
            i += 1
            if i < n and raw[i] == 10:
                eol, i = b"\r\n", i + 1
        else:
            i += 1
            continue
        chunks.append((raw[start:end], eol))
        start = i
    if start < n:
        chunks.append((raw[start:], b""))
    return chunks


def _norm_lines(text):
    """Espelha verify_translation.norm_lines (CRLF/LF normalizados)."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _verify_line_structure(orig_body, new_body, codec):
    """Replica as checagens de verify_translation.py sobre o corpo decodificado."""
    problems = []
    before = _norm_lines(orig_body.decode(codec, errors="replace"))
    after = _norm_lines(new_body.decode(codec, errors="replace"))
    if len(before) != len(after):
        problems.append(
            "contagem de linhas diverge do original (%d -> %d)" % (len(before), len(after))
        )
    for idx, (old_line, new_line) in enumerate(zip(before, after), 1):
        if old_line != new_line and not JP_RE.search(old_line):
            problems.append("linha %d sem japones foi alterada" % idx)
    return problems


def _translated_or_review(row):
    translated = row.get("translated")
    if translated is None:
        return None, ["campo translated ausente"]
    return str(translated), []


# ---------------------------------------------------------------------------
# Applier linha-a-linha (.txt/.ks/.rpy/.csv e demais nao-.json)
# ---------------------------------------------------------------------------


def _apply_lines(src_path, out_path, rel_file, rows):
    raw = src_path.read_bytes()

    encoding = _norm_encoding(rows[0].get("encoding"))
    if encoding is None:
        return [
            _make_audit(rel_file, r, "failed", ["encoding nao suportado: %r" % (rows[0].get("encoding"),)])
            for r in rows
        ]

    bom_present = encoding in ("utf-8", "utf-8-sig") and raw.startswith(BOM_UTF8)
    body = raw[len(BOM_UTF8):] if bom_present else raw
    codec = "utf-8" if encoding == "utf-8-sig" else encoding

    try:
        full_text = body.decode(codec)
    except UnicodeDecodeError as exc:
        return [_make_audit(rel_file, r, "failed", ["falha ao decodificar arquivo (%s)" % exc]) for r in rows]

    chunks = _split_byte_lines(body)
    if len(chunks) != len(full_text.splitlines()):
        # A numeracao do scanner usa splitlines(); se divergir da divisao por
        # bytes, o arquivo tem separadores exoticos: nao mexer.
        return [
            _make_audit(rel_file, r, "failed", ["numeracao de linhas diverge do scanner; nada alterado"])
            for r in rows
        ]

    decisions = []  # {"row", "status"(None=pendente), "notes"}
    replacements = {}  # numero da linha (1-based) -> novos bytes do conteudo
    used_lines = set()

    for row in rows:
        entry = {"row": row, "status": None, "notes": []}
        decisions.append(entry)

        try:
            line_no = int(row.get("line") or 0)
        except (TypeError, ValueError):
            entry["status"] = "failed"
            entry["notes"] = ["campo line invalido"]
            continue
        if line_no < 1 or line_no > len(chunks):
            entry["status"] = "failed"
            entry["notes"] = ["linha %r fora do intervalo (arquivo tem %d linhas)" % (row.get("line"), len(chunks))]
            continue
        if line_no in used_lines:
            entry["status"] = "needs_review"
            entry["notes"] = ["linha %d ja substituida por outra entrada" % line_no]
            continue

        translated, missing = _translated_or_review(row)
        if translated is None:
            entry["status"] = "needs_review"
            entry["notes"] = missing
            continue

        text_src = str(row.get("text") or "")
        ok, problems = placeholders.validate_pair(text_src, translated)
        if not ok:
            entry["status"] = "needs_review"
            entry["notes"] = problems
            continue

        content_bytes, _eol = chunks[line_no - 1]
        try:
            content = content_bytes.decode(codec)
        except UnicodeDecodeError as exc:
            entry["status"] = "failed"
            entry["notes"] = ["falha ao decodificar a linha alvo (%s)" % exc]
            continue

        pos = content.find(text_src)
        if pos < 0:
            entry["status"] = "needs_review"
            entry["notes"] = ["trecho original nao encontrado na linha (possivel truncamento no scan)"]
            continue

        new_content = content[:pos] + translated + content[pos + len(text_src):]
        try:
            replacements[line_no] = new_content.encode(codec)
        except UnicodeEncodeError as exc:
            entry["status"] = "needs_review"
            entry["notes"] = ["traducao contem caracteres fora do encoding %s (%s)" % (encoding, exc)]
            continue

        used_lines.add(line_no)

    audits = [_make_audit(rel_file, d["row"], d["status"], d["notes"]) for d in decisions]

    if not replacements:
        return audits  # nada a gravar: copia nem chega a existir

    new_parts = []
    for idx, (content_bytes, eol_bytes) in enumerate(chunks, 1):
        new_parts.append(replacements[idx] + eol_bytes if idx in replacements else content_bytes + eol_bytes)
    new_body = b"".join(new_parts)

    problems = _verify_line_structure(body, new_body, codec)
    if problems:
        for audit in audits:
            if audit["status"] is None:
                audit["status"] = "failed"
                audit["notes"] = list(problems)
        return audits

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes((BOM_UTF8 if bom_present else b"") + new_body)

    for audit in audits:
        if audit["status"] is None:
            audit["status"] = "applied"
            audit["notes"] = []
    return audits


# ---------------------------------------------------------------------------
# Applier JSON (RPG Maker MV/MZ via source_key)
# ---------------------------------------------------------------------------


def parse_source_key(source_key):
    """Converte ``$[1].profile[0]`` / ``$.actors[0].name`` em tokens."""
    key = str(source_key or "").strip()
    if not key.startswith("$"):
        raise ValueError("source_key deve comecar com '$'")
    tokens = []
    i = 1
    n = len(key)
    while i < n:
        ch = key[i]
        if ch == ".":
            j = i + 1
            while j < n and key[j] not in ".[":
                j += 1
            name = key[i + 1:j]
            if not name:
                raise ValueError("nome vazio em %r" % key)
            tokens.append(("key", name))
            i = j
        elif ch == "[":
            j = key.find("]", i)
            if j < 0:
                raise ValueError("colchete sem fechamento em %r" % key)
            index = key[i + 1:j]
            if not index.isdigit():
                raise ValueError("indice nao numerico em %r" % key)
            tokens.append(("index", int(index)))
            i = j + 1
        else:
            raise ValueError("caractere inesperado %r em %r" % (ch, key))
    if not tokens:
        raise ValueError("source_key sem caminho")
    return tokens


def _walk(node, tokens):
    for kind, value in tokens:
        if kind == "key":
            if not isinstance(node, dict) or value not in node:
                raise KeyError(value)
            node = node[value]
        else:
            if not isinstance(node, list) or value >= len(node):
                raise IndexError(value)
            node = node[value]
    return node


def _collect_leaves(node, path="$", out=None):
    if out is None:
        out = {}
    if isinstance(node, dict):
        for key, child in node.items():
            _collect_leaves(child, "%s.%s" % (path, key), out)
    elif isinstance(node, list):
        for index, child in enumerate(node):
            _collect_leaves(child, "%s[%d]" % (path, index), out)
    else:
        out[path] = node
    return out


def _shape(node):
    """Assinatura estrutural: captura tipos, ordem de chaves e tamanhos."""
    if isinstance(node, dict):
        return ("dict", tuple(node.keys()), tuple(_shape(child) for child in node.values()))
    if isinstance(node, list):
        return ("list", tuple(_shape(child) for child in node))
    return ("scalar", type(node).__name__)


_MISSING = object()


def _verify_json_structure(orig_data, new_data, expected_changed):
    """So as folhas aplicadas podem diferir; ordem/estrutura devem ser iguais."""
    old_leaves = _collect_leaves(orig_data)
    new_leaves = _collect_leaves(new_data)
    problems = []
    for path in sorted(set(old_leaves) | set(new_leaves)):
        old_value = old_leaves.get(path, _MISSING)
        new_value = new_leaves.get(path, _MISSING)
        changed = old_value != new_value
        should_change = path in expected_changed
        if changed and not should_change:
            problems.append("folha %s foi alterada sem autorizacao" % path)
        elif should_change and not changed:
            problems.append("folha %s deveria ter sido traduzida mas permaneceu igual" % path)
    if _shape(orig_data) != _shape(new_data):
        problems.append("estrutura ou ordem de chaves do JSON foi alterada")
    return problems


def _apply_json(src_path, out_path, rel_file, rows):
    raw = src_path.read_bytes()

    encoding = _norm_encoding(rows[0].get("encoding"))
    if encoding not in ("utf-8", "utf-8-sig"):
        return [
            _make_audit(rel_file, r, "failed", ["JSON requer encoding utf-8/utf-8-sig (recebido %r)" % (rows[0].get("encoding"),)])
            for r in rows
        ]

    bom_present = raw.startswith(BOM_UTF8)
    body = raw[len(BOM_UTF8):] if bom_present else raw
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        return [_make_audit(rel_file, r, "failed", ["falha ao decodificar arquivo (%s)" % exc]) for r in rows]

    try:
        pristine = json.loads(text)
    except json.JSONDecodeError as exc:
        return [_make_audit(rel_file, r, "failed", ["json invalido (%s)" % exc]) for r in rows]

    data = json.loads(text)
    had_trailing_newline = text.endswith("\n")

    decisions = []
    expected_changed = set()

    for row in rows:
        entry = {"row": row, "status": None, "notes": []}
        decisions.append(entry)

        translated, missing = _translated_or_review(row)
        if translated is None:
            entry["status"] = "needs_review"
            entry["notes"] = missing
            continue

        try:
            tokens = parse_source_key(row.get("source_key"))
        except ValueError as exc:
            entry["status"] = "failed"
            entry["notes"] = [str(exc)]
            continue

        try:
            current = _walk(data, tokens)
        except (KeyError, IndexError, TypeError):
            entry["status"] = "failed"
            entry["notes"] = ["caminho %r nao encontrado no JSON" % (row.get("source_key"),)]
            continue
        if not isinstance(current, str):
            entry["status"] = "failed"
            entry["notes"] = ["folha em %r nao e texto" % (row.get("source_key"),)]
            continue

        text_src = str(row.get("text") or "")
        stripped_current = current.strip()
        if stripped_current != text_src and not stripped_current.startswith(text_src):
            entry["status"] = "needs_review"
            entry["notes"] = ["conteudo atual difere do texto escaneado"]
            continue

        ok, problems = placeholders.validate_pair(text_src, translated)
        if not ok:
            entry["status"] = "needs_review"
            entry["notes"] = problems
            continue

        parent_kind, last = tokens[-1]
        try:
            parent = _walk(data, tokens[:-1])
            if parent_kind == "key":
                if not isinstance(parent, dict):
                    raise TypeError
                parent[last] = translated
            else:
                if not isinstance(parent, list) or last >= len(parent):
                    raise IndexError
                parent[last] = translated
        except (KeyError, IndexError, TypeError):
            entry["status"] = "failed"
            entry["notes"] = ["nao foi possivel atribuir valor em %r" % (row.get("source_key"),)]
            continue

        expected_changed.add(str(row.get("source_key")).strip())

    dumped = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if had_trailing_newline:
        dumped += "\n"

    problems = []
    try:
        reparsed = json.loads(dumped)
    except json.JSONDecodeError as exc:
        reparsed = None
        problems.append("dump nao reparseia (%s)" % exc)
    if reparsed is not None:
        problems.extend(_verify_json_structure(pristine, reparsed, expected_changed))

    audits = [_make_audit(rel_file, d["row"], d["status"], d["notes"]) for d in decisions]

    if not expected_changed or problems:
        for audit in audits:
            if audit["status"] is None:
                audit["status"] = "failed"
                audit["notes"] = list(problems) or ["nenhuma traducao aplicavel"]
        return audits

    payload = dumped.encode("utf-8")
    if bom_present:
        payload = BOM_UTF8 + payload
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(payload)

    for audit in audits:
        if audit["status"] is None:
            audit["status"] = "applied"
            audit["notes"] = []
    return audits


# ---------------------------------------------------------------------------
# Entrada principal
# ---------------------------------------------------------------------------


def apply_to_copy(rows_by_file, src_root, out_root):
    """Aplica traducoes gerando copias em ``out_root``.

    - ``rows_by_file``: dict de caminho relativo ("txt/demo.txt") -> lista de
      rows do extrator com campo ``translated``.
    - ``src_root``: pasta original do jogo (somente leitura).
    - ``out_root``: pasta de saida das copias (unica area escrita).

    Devolve lista de auditorias ``{file, item_id, line, source_key, status,
    notes}`` na mesma ordem de entrada dos arquivos/rows.
    """
    src_root_path = Path(src_root)
    out_root_path = Path(out_root)
    if src_root_path.resolve() == out_root_path.resolve():
        raise ValueError("out_root deve ser diferente de src_root para proteger os originais")

    results = []
    for rel_file, rows in rows_by_file.items():
        rows = list(rows or [])
        if not rows:
            continue
        rel_norm = str(rel_file).replace("\\", "/")

        dest = _safe_join(out_root_path, rel_norm)
        source = _safe_join(src_root_path, rel_norm)
        if dest is None or source is None:
            results.extend(
                _make_audit(rel_norm, r, "failed", ["caminho invalido ou fora da raiz permitida"])
                for r in rows
            )
            continue
        if not source.is_file():
            results.extend(
                _make_audit(rel_norm, r, "failed", ["arquivo origem ausente"]) for r in rows
            )
            continue

        ext = PurePosixPath(rel_norm).suffix.lower()
        # Protecao: nao traduzir codigo JavaScript (quebra o jogo)
        if ext == ".js" and "/www/js/" in f"/{rel_norm.lower()}":
            results.extend(
                _make_audit(rel_norm, r, "skipped", ["arquivo JS de engine/plugin - nao traduzir codigo"])
                for r in rows
            )
            continue
        if ext == ".json":
            results.extend(_apply_json(source, dest, rel_norm, rows))
        else:
            results.extend(_apply_lines(source, dest, rel_norm, rows))
    return results
