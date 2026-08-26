import argparse
import csv
import json
import os
import re
from pathlib import Path

TEXT_EXTENSIONS = {
    ".asset",
    ".csv",
    ".ini",
    ".json",
    ".ks",
    ".lua",
    ".po",
    ".rpy",
    ".strings",
    ".ts",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
# .js REMOVIDO: arquivos JavaScript sao CODIGO, nao texto traduzivel.
# Traduzi-las quebra o jogo (case strings, nomes de parametros, etc).
# Para escanear .js de forma explicita, usar: --include-ext js

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    "Managed",
    "Library",
    "Temp",
}

NON_ENGLISH_PATTERNS = {
    "cjk": re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]"),
    "kana": re.compile(r"[\u3040-\u30ff]"),
    "hangul": re.compile(r"[\uac00-\ud7af]"),
    "cyrillic": re.compile(r"[\u0400-\u04ff]"),
    "thai": re.compile(r"[\u0e00-\u0e7f]"),
    "arabic": re.compile(r"[\u0600-\u06ff]"),
    "accented_latin": re.compile(r"[À-ÖØ-öø-ÿ]"),
}

STRING_LITERAL = re.compile(r"""(?P<quote>["'])(?P<body>(?:\\.|(?!\1).)*?)(?P=quote)""")
URL_OR_EMAIL = re.compile(r"(https?://|www\.|@[\w.-]+)")
MOSTLY_SYMBOLS = re.compile(r"^[\s\W_]+$", re.UNICODE)

JSON_TRANSLATION_KEYS = {
    "description",
    "displayName",
    "gameTitle",
    "message1",
    "message2",
    "message3",
    "message4",
    "name",
    "nickname",
    "note",
    "profile",
    "currencyUnit",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scan game folders and extract text that is likely not English."
    )
    parser.add_argument("roots", nargs="+", help="Game folders or files to scan.")
    parser.add_argument(
        "--out",
        default="non_english_text_report",
        help="Output path without extension, or a .csv/.jsonl path.",
    )
    parser.add_argument(
        "--include-ext",
        action="append",
        default=[],
        help="Extra file extension to scan, for example --include-ext .dat",
    )
    parser.add_argument("--max-file-mb", type=int, default=25)
    parser.add_argument("--context", type=int, default=180)
    parser.add_argument(
        "--dedupe",
        action="store_true",
        help="Emit only the first occurrence of each repeated text.",
    )
    parser.add_argument(
        "--skip-plugin-js",
        action="store_true",
        help="Skip RPG Maker plugin JavaScript files under www/js/plugins.",
    )
    parser.add_argument(
        "--plugin-js-mode",
        choices=("jp-dense", "all"),
        default="jp-dense",
        help=(
            "Filter for www/js/plugins snippets: jp-dense emits only "
            "Japanese-dense text (kana, CJK ratio >= 0.30 or corner "
            "brackets); all restores the previous behavior."
        ),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Number of emitted rows per agent batch.",
    )
    return parser.parse_args()


def iter_files(root):
    root_path = Path(root)
    if root_path.is_file():
        yield root_path
        return

    for current, dirs, files in os.walk(root_path):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        for name in files:
            yield Path(current) / name


def is_probably_binary(path):
    try:
        chunk = path.read_bytes()[:4096]
    except OSError:
        return True
    return b"\x00" in chunk


def read_text(path):
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "cp932", "shift_jis", "utf-16", "latin-1"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return None, None


def reasons_for(text):
    return [name for name, pattern in NON_ENGLISH_PATTERNS.items() if pattern.search(text)]


def normalize_rel(path):
    return str(path).replace("\\", "/")


def classify_path(path):
    rel = normalize_rel(path)
    lowered = rel.lower()
    is_rpgmaker_data = (
        lowered.startswith("data/")
        or lowered.startswith("www/data/")
        or "/www/data/" in lowered
    )
    if is_rpgmaker_data:
        if "commonevents.json" in lowered:
            return "rpgmaker_common_events", 100
        if "/map" in f"/{lowered}":
            return "rpgmaker_map", 95
        if any(name in lowered for name in ("items.json", "skills.json", "weapons.json", "armors.json", "states.json", "actors.json", "classes.json", "enemies.json")):
            return "rpgmaker_database", 90
        if "system.json" in lowered:
            return "rpgmaker_system", 85
        return "rpgmaker_data", 80
    if (
        lowered.startswith("js/plugins/")
        or lowered.startswith("www/js/plugins/")
        or "/www/js/plugins/" in lowered
    ):
        return "rpgmaker_plugin_js", 25
    if lowered.startswith("img/tilesets/") and lowered.endswith(".txt"):
        return "rpgmaker_tileset_metadata", 20
    if lowered.endswith(".txt"):
        return "documentation", 35
    if lowered.endswith((".rpy", ".ks")):
        return "script", 95
    return "generic_text", 50


def looks_like_noise(text):
    clean = text.strip()
    if len(clean) < 2:
        return True
    if URL_OR_EMAIL.search(clean):
        return True
    if clean in {"・URL", "URL", "url"}:
        return True
    if MOSTLY_SYMBOLS.match(clean):
        return True
    return False


KANA_PATTERN = NON_ENGLISH_PATTERNS["kana"]
CJK_PATTERN = NON_ENGLISH_PATTERNS["cjk"]
CORNER_BRACKETS = ("\u300c", "\u300d")


def is_jp_dense(snippet):
    """True when a plugin JS snippet is dense enough to be real dialogue.

    Dense means: contains kana, contains Japanese corner brackets, or
    CJK ideographs make up at least 30% of the non-space characters.
    """
    if KANA_PATTERN.search(snippet):
        return True
    if any(bracket in snippet for bracket in CORNER_BRACKETS):
        return True
    visible = [char for char in snippet if not char.isspace()]
    if not visible:
        return False
    cjk_count = sum(1 for char in visible if CJK_PATTERN.search(char))
    return cjk_count / len(visible) >= 0.30


def apply_plugin_js_mode(rows, mode):
    """Filter rpgmaker_plugin_js rows according to --plugin-js-mode.

    Returns (kept_rows, technical_ignored_count). Only this category is
    affected; every other category passes through unchanged.
    """
    if mode == "all":
        return rows, 0
    kept = []
    ignored = 0
    for row in rows:
        if row["category"] == "rpgmaker_plugin_js" and not is_jp_dense(row["text"]):
            ignored += 1
            continue
        kept.append(row)
    return kept, ignored


def snippets_from_line(line, extension):
    if extension in {".rpy", ".py", ".js", ".ts", ".json", ".lua"}:
        literals = [match.group("body") for match in STRING_LITERAL.finditer(line)]
        return literals or [line]
    return [line]


def json_leaf_strings(value, path="$"):
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            yield from json_leaf_strings(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            yield from json_leaf_strings(child, child_path)
    elif isinstance(value, str):
        yield path, value


def json_key_priority(source_key, base_priority):
    key = source_key.rsplit(".", 1)[-1]
    key = key.split("[", 1)[0]
    if key in JSON_TRANSLATION_KEYS:
        return min(100, base_priority + 8)
    if ".parameters[" in source_key:
        return base_priority
    return max(5, base_priority - 20)


def find_line_number(text, snippet):
    if not snippet:
        return 0
    index = text.find(snippet)
    if index == -1:
        return 0
    return text.count("\n", 0, index) + 1


def scan_json_file(path, root, context, category, base_priority):
    text, encoding = read_text(path)
    if text is None:
        return

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        yield from scan_text_file(path, root, context, category, base_priority)
        return

    rel_path = path.relative_to(root) if path.is_relative_to(root) else path
    for source_key, snippet in json_leaf_strings(data):
        found = reasons_for(snippet)
        if not found:
            continue
        clean = snippet.strip()
        if looks_like_noise(clean):
            continue
        yield {
            "root": str(root),
            "file": str(rel_path),
            "line": 0,
            "extension": path.suffix.lower(),
            "encoding": encoding,
            "reason": ",".join(found),
            "category": category,
            "priority": json_key_priority(source_key, base_priority),
            "source_key": source_key,
            "text": clean[:context],
        }


def scan_text_file(path, root, context, category, base_priority):
    text, encoding = read_text(path)
    if text is None:
        return

    rel_path = path.relative_to(root) if path.is_relative_to(root) else path
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        for snippet in snippets_from_line(line, path.suffix.lower()):
            found = reasons_for(snippet)
            if not found:
                continue
            clean = snippet.strip()
            if not clean or looks_like_noise(clean):
                continue
            yield {
                "root": str(root),
                "file": str(rel_path),
                "line": line_no,
                "extension": path.suffix.lower(),
                "encoding": encoding,
                "reason": ",".join(found),
                "category": category,
                "priority": base_priority,
                "source_key": "",
                "text": clean[:context],
            }


def scan_file(path, root, context):
    category, base_priority = classify_path(path.relative_to(root) if path.is_relative_to(root) else path)
    if path.suffix.lower() == ".json":
        yield from scan_json_file(path, root, context, category, base_priority)
    else:
        yield from scan_text_file(path, root, context, category, base_priority)


def output_paths(base):
    out = Path(base)
    if out.suffix == ".csv":
        return out, out.with_suffix(".jsonl"), out.with_suffix(".summary.md")
    if out.suffix == ".jsonl":
        return out.with_suffix(".csv"), out, out.with_suffix(".summary.md")
    return out.with_suffix(".csv"), out.with_suffix(".jsonl"), out.with_suffix(".summary.md")


def dedupe_rows(rows):
    seen = {}
    deduped = []
    for row in rows:
        key = row["text"]
        if key not in seen:
            seen[key] = row
            row["occurrences"] = 1
            deduped.append(row)
        else:
            seen[key]["occurrences"] += 1
            seen[key]["priority"] = max(int(seen[key]["priority"]), int(row["priority"]))
    return deduped


def write_summary(path, rows, original_count, plugin_js_ignored=0):
    from collections import Counter

    by_category = Counter(row["category"] for row in rows)
    by_file = Counter(row["file"] for row in rows)
    by_reason = Counter(row["reason"] for row in rows)
    high_priority = sum(1 for row in rows if int(row["priority"]) >= 90)

    lines = [
        "# Non-English Text Scan Summary",
        "",
        f"- Entries emitted: {len(rows)}",
        f"- Raw entries before dedupe: {original_count}",
        f"- High priority entries: {high_priority}",
        f"- plugin_js_tecnico_ignorado: {plugin_js_ignored}",
        "",
        "## Categories",
        "",
    ]
    lines.extend(f"- {name}: {count}" for name, count in by_category.most_common())
    lines.extend(["", "## Detection Reasons", ""])
    lines.extend(f"- {name}: {count}" for name, count in by_reason.most_common())
    lines.extend(["", "## Top Files", ""])
    lines.extend(f"- {count}: `{name}`" for name, count in by_file.most_common(20))
    lines.extend(
        [
            "",
            "## Agent Guidance",
            "",
            "- Start with rows where `priority >= 90`.",
            "- Assign one agent batch at a time using the `batch` column.",
            "- Keep `item_id` unchanged in any translated output.",
            "- Prefer `rpgmaker_common_events`, `rpgmaker_map`, and `rpgmaker_database` before plugin JS or documentation.",
            "- Use `source_key` to locate JSON values without relying only on line numbers.",
            "- Treat repeated rows with high `occurrences` as glossary candidates.",
            "- Do not write translations back to game files without a separate approval.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    args = parse_args()
    extensions = TEXT_EXTENSIONS | {ext.lower() for ext in args.include_ext}
    csv_path, jsonl_path, summary_path = output_paths(args.out)
    rows = []

    for root_arg in args.roots:
        root = Path(root_arg).resolve()
        for path in iter_files(root):
            if path.suffix.lower() not in extensions:
                continue
            rel = normalize_rel(path.relative_to(root) if root.is_dir() and path.is_relative_to(root) else path)
            lowered_rel = f"/{rel.lower()}"
            if args.skip_plugin_js and (
                "/www/js/plugins/" in lowered_rel or "/js/plugins/" in lowered_rel
            ):
                continue
            if path.stat().st_size > args.max_file_mb * 1024 * 1024:
                continue
            if is_probably_binary(path):
                continue
            rows.extend(scan_file(path, root if root.is_dir() else path.parent, args.context))

    rows, plugin_js_ignored = apply_plugin_js_mode(rows, args.plugin_js_mode)
    original_count = len(rows)
    if args.dedupe:
        rows = dedupe_rows(rows)
    else:
        for row in rows:
            row["occurrences"] = 1

    rows.sort(key=lambda row: (-int(row["priority"]), row["file"], int(row["line"]), row["source_key"]))
    batch_size = max(1, args.batch_size)
    for index, row in enumerate(rows, 1):
        row["item_id"] = f"T{index:06d}"
        row["batch"] = f"B{((index - 1) // batch_size) + 1:04d}"

    fields = [
        "item_id",
        "batch",
        "root",
        "file",
        "line",
        "extension",
        "encoding",
        "reason",
        "category",
        "priority",
        "source_key",
        "occurrences",
        "text",
    ]
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    write_summary(summary_path, rows, original_count, plugin_js_ignored)

    print(f"Found {len(rows)} candidate text entries.")
    print(f"Raw entries before dedupe: {original_count}")
    print(f"CSV: {csv_path}")
    print(f"JSONL: {jsonl_path}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
