"""Mechanical style checks, language-light. Findings: path:line: ID message.
  lint.py [--root DIR] [--changed|--staged] [--base REF] [--rules a,b] [--list]
IDs: LEN long line, FUNC long function, FILE long file, PARAM many params, DEBUG debug leftover,
CODE commented-out code, TODO todo without owner/issue, CATCH empty catch/except, SECRET secret-like string,
CONFLICT merge marker, DUP duplicated block. Exit 1 if any finding."""
from __future__ import annotations

import argparse
import ast
import hashlib
import re
import sys
from collections import defaultdict
from pathlib import Path

from common import find_root, is_text, lang_of, load_config, tracked_files

RULES = {
    "LEN": "line longer than limits.max_line_length", "FUNC": "function longer than limits.max_function_lines",
    "FILE": "file longer than limits.max_file_lines", "PARAM": "more than limits.max_params parameters",
    "DEBUG": "debug leftover (print/console.log/var_dump/dd/debugger)", "CODE": "commented-out code",
    "TODO": "TODO/FIXME without owner or issue: use TODO(name) or TODO(#12)", "CATCH": "empty catch/except swallowing errors",
    "SECRET": "secret-like literal", "CONFLICT": "merge conflict marker", "DUP": "block duplicated elsewhere",
}
DEBUG = {
    "python": r"^\s*(print\(|breakpoint\(|pdb\.set_trace|import pdb)", "php": r"\b(var_dump|print_r|dd|dump)\(|\bxdebug_break",
    "typescript": r"\bconsole\.(log|debug)\(|^\s*debugger\b", "javascript": r"\bconsole\.(log|debug)\(|^\s*debugger\b",
    "matlab": r"^\s*(keyboard|dbstop)\b", "shell": r"^\s*set -x\b",
}
CODELIKE = re.compile(r"^\s*(//|#|%)\s*(if\b.*[:{]\s*$|for\b.*[:{]\s*$|return\b.*;?$|\w+\s*=\s*.+[;)]$|\w+\(.*\);?$|import\s|from\s+\w+\s+import|\}\s*$)")
TODO = re.compile(r"\b(TODO|FIXME|XXX)\b(?!\s*\(\s*[\w#-]+\s*\))")
SECRET = re.compile(r"""(?i)(api[_-]?key|secret|passw(or)?d|token|private[_-]?key)\s*[:=]\s*['"][^'"\s]{12,}['"]|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|sk_(live|test)_[0-9a-zA-Z]{16,}""")
CATCH = {"python": re.compile(r"except[^:]*:\s*(pass|\.\.\.)?\s*$"), "php": re.compile(r"catch\s*\([^)]*\)\s*\{\s*\}"),
         "typescript": re.compile(r"catch\s*(\([^)]*\))?\s*\{\s*\}"), "javascript": re.compile(r"catch\s*(\([^)]*\))?\s*\{\s*\}")}
CODE_LANGS = {"python", "php", "typescript", "javascript", "matlab", "shell", "terraform"}
CODE_COMMENTS = {"python", "php", "typescript", "javascript"}
SKIP_SECRET_PATHS = re.compile(r"(test|spec|fixture|example|\.lock|lock\.json|\.md$)", re.I)


def py_findings(path, text, lim):
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        return [(e.lineno or 1, "FUNC", f"syntax error: {e.msg}")]
    out = []
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            ln = (n.end_lineno or n.lineno) - n.lineno + 1
            if ln > lim["max_function_lines"]: out.append((n.lineno, "FUNC", f"{n.name}: {ln} lines"))
            a = n.args; k = len(a.posonlyargs) + len(a.args) + len(a.kwonlyargs)
            k -= 1 if a.args and a.args[0].arg in ("self", "cls") else 0
            if k > lim["max_params"]: out.append((n.lineno, "PARAM", f"{n.name}: {k} parameters"))
        if isinstance(n, ast.ExceptHandler) and len(n.body) == 1 and isinstance(n.body[0], (ast.Pass, ast.Expr)) \
                and (isinstance(n.body[0], ast.Pass) or isinstance(getattr(n.body[0], "value", None), ast.Constant)):
            out.append((n.lineno, "CATCH", "except body does nothing"))
    return out


def brace_funcs(lines, lang, lim):
    """Approximate function length for brace languages via indentation of the closing brace."""
    rx = re.compile(r"^(\s*)(?:(?:public|protected|private|static|async|export)\s+)*function\s+(\w+)\s*\(([^)]*)")
    out = []
    for i, l in enumerate(lines):
        m = rx.match(l)
        if not m: continue
        ind = m.group(1)
        for j in range(i + 1, len(lines)):
            if lines[j].startswith(ind + "}") and not lines[j].startswith(ind + " "):
                if j - i + 1 > lim["max_function_lines"]: out.append((i + 1, "FUNC", f"{m.group(2)}: {j - i + 1} lines"))
                break
        n = len([p for p in m.group(3).split(",") if p.strip()])
        if n > lim["max_params"]: out.append((i + 1, "PARAM", f"{m.group(2)}: {n} parameters"))
    return out


def check_file(root, f, lim, active):
    p = root / f
    text = p.read_text(errors="replace"); lines = text.splitlines(); lang = lang_of(f)
    res = []
    if len(lines) > lim["max_file_lines"] and lang in CODE_LANGS: res.append((1, "FILE", f"{len(lines)} lines"))
    dbg = re.compile(DEBUG[lang]) if lang in DEBUG else None
    ctch = CATCH.get(lang)
    for i, l in enumerate(lines, 1):
        if len(l) > lim["max_line_length"] and lang in CODE_LANGS and "http" not in l: res.append((i, "LEN", f"{len(l)} chars"))
        if dbg and dbg.search(l) and "scripts/" not in str(f) and "cli" not in f.name and "test" not in str(f).lower():
            res.append((i, "DEBUG", l.strip()[:60]))
        if lang in CODE_COMMENTS and CODELIKE.match(l) and not l.lstrip().startswith(("#!", "# type:", "# noqa", "// @")): res.append((i, "CODE", l.strip()[:60]))
        if TODO.search(l) and lang in CODE_LANGS: res.append((i, "TODO", l.strip()[:60]))
        if ctch and lang != "python" and ctch.search(l): res.append((i, "CATCH", "empty catch"))
        if SECRET.search(l) and not SKIP_SECRET_PATHS.search(str(f)): res.append((i, "SECRET", "secret-like literal"))
        if re.match(r"^(<<<<<<<|>>>>>>>) ", l) or l == "=======": res.append((i, "CONFLICT", l[:20]))
    if lang == "python": res += py_findings(f, text, lim)
    elif lang in ("php", "typescript", "javascript"): res += brace_funcs(lines, lang, lim)
    return [(f, i, r, m) for i, r, m in res if r in active]


def dupes(root, files, window):
    seen = defaultdict(list)
    for f in files:
        if lang_of(f) is None or lang_of(f) in ("yaml", "css", "sql", "html") or re.search(r"test|migrations?/|config/", str(f), re.I): continue
        norm = [(i, re.sub(r"\s+", " ", l.strip())) for i, l in enumerate((root / f).read_text(errors="replace").splitlines(), 1)]
        norm = [(i, l) for i, l in norm if len(l) > 3 and not l.startswith(("import ", "from ", "use ", "#", "//", "*", "/*", "}", "{", ")", "]"))]
        for k in range(len(norm) - window + 1):
            h = hashlib.md5("\n".join(l for _, l in norm[k:k + window]).encode()).hexdigest()
            seen[h].append((f, norm[k][0]))
    out, covered = [], set()
    for locs in seen.values():
        if len(locs) < 2: continue
        key = tuple(sorted((str(f), i // 20) for f, i in locs))
        if key in covered: continue
        covered.add(key)
        f0, i0 = locs[0]
        out.append((f0, i0, "DUP", "same %d-line block also at %s" % (window, ", ".join(f"{f}:{i}" for f, i in locs[1:4]))))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root"); ap.add_argument("--changed", action="store_true"); ap.add_argument("--staged", action="store_true")
    ap.add_argument("--base"); ap.add_argument("--rules"); ap.add_argument("--list", action="store_true")
    ap.add_argument("--summary", action="store_true", help="counts per rule only")
    ap.add_argument("--dup-all", action="store_true", help="look for duplicates against the whole repo, not only changed files")
    a = ap.parse_args()
    if a.list:
        for k, v in RULES.items(): print(f"{k:9}{v}")
        return 0
    root = find_root(a.root); cfg = load_config(root); lim = cfg["limits"]
    active = set(a.rules.split(",")) if a.rules else set(RULES)
    scope = [f for f in tracked_files(root, a.changed, a.staged, a.base or (cfg["check"].get("base") if a.changed else None)) if is_text(root / f)]
    findings = []
    for f in scope: findings += check_file(root, f, lim, active)
    if "DUP" in active:
        pool = scope if not (a.changed or a.staged) else [f for f in tracked_files(root) if is_text(root / f)]
        d = dupes(root, pool, lim["dup_window"])
        mine = {str(f) for f in scope}
        findings += [x for x in d if str(x[0]) in mine or not (a.changed or a.staged)]
    by = defaultdict(list)
    for f, i, r, m in findings: by[r].append((f, i, m))
    for r in RULES:
        if r in by:
            print(f"{r} ({len(by[r])}) {RULES[r]}")
            if a.summary: continue
            for f, i, m in by[r][:8]: print(f"  {f}:{i}: {m}")
            if len(by[r]) > 8: print(f"  ... +{len(by[r]) - 8}")
    print(f"lint: {len(findings)} finding(s) in {len(scope)} file(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
