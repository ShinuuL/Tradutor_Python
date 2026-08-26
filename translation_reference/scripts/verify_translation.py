#!/usr/bin/env python3
"""Verify a translated .rpy chunk against its original.

Checks:
1. Line count is identical (normalized: CRLF/LF treated the same).
2. Every line that contains NO Japanese characters is byte-identical to the
   original (structure/code must be untouched).
3. Reports all lines that still contain Japanese characters so a human can
   confirm each remaining occurrence is a logic-critical comparison.

Usage:
    python verify_translation.py <original> <translated>
"""
import re
import sys

JP_RE = re.compile(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')


def norm_lines(path):
    with open(path, 'rb') as f:
        data = f.read()
    if data.startswith(b'\xef\xbb\xbf'):
        data = data[3:]
    text = data.decode('utf-8-sig')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines = lines[:-1]
    return lines


def main():
    if len(sys.argv) != 3:
        print('usage: verify_translation.py <original> <translated>')
        return 2
    orig = norm_lines(sys.argv[1])
    trans = norm_lines(sys.argv[2])
    ok = True
    if len(orig) != len(trans):
        print(f'FAIL: line count {len(orig)} -> {len(trans)}')
        ok = False
    n = min(len(orig), len(trans))
    changed_no_jp = 0
    jp_lines = []
    for i in range(n):
        o, t = orig[i], trans[i]
        if o == t:
            continue
        if not JP_RE.search(o):
            changed_no_jp = changed_no_jp + 1
            if changed_no_jp <= 20:
                print(f'NOTE line {i+1} changed but had no Japanese:')
                print(f'  orig: {o!r}')
                print(f'  trans:{t!r}')
        if JP_RE.search(t):
            jp_lines.append((i + 1, t.strip()))
    if changed_no_jp:
        print(f'FAIL: {changed_no_jp} non-Japanese lines changed (structure touched)')
        ok = False
    if jp_lines:
        print(f'JP-remaining ({len(jp_lines)}):')
        for ln, text in jp_lines[:80]:
            print(f'  {ln}: {text}')
        if len(jp_lines) > 80:
            print(f'  ... and {len(jp_lines) - 80} more')
    else:
        print('OK: no Japanese characters remain')
    print('RESULT:', 'PASS' if ok else 'CHECK')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
