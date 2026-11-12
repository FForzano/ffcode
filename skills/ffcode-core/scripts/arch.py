"""Project architecture from .ffcode/architecture.toml: layers (kinds of unit/object), naming, allowed dependencies, conventions.
  ff arch                      compact summary (style, layers, conventions)
  ff arch show LAYER           one layer in full + existing files to imitate
  ff arch new NAME             the units a new entity NAME needs, one path per layer with a `stem`, and whether each exists
  ff arch infer [--write] [--check] [--interview] [--answer id=value]...   draft architecture.toml from directories, real imports and names (layers, measured may_import, rare edges flagged, typical example)
Lint ids (in ff lint / ff check): ARCHNAME file in a layer path whose name does not match name_pattern; ARCHDEP import of a layer not in may_import."""
from __future__ import annotations

import argparse
import fnmatch
import os
import re
import sys
import tomllib
from collections import Counter, defaultdict
from pathlib import Path

from common import DIRNAME, find_root, lang_of, load_config, tracked_files

SUFFIXES = "Controller|Service|Repository|Dto|DTO|Entity|Model|Resource|Request|Handler|Mapper|Transformer|Factory|Middleware|Provider|Policy|Event|Listener|Job|Command|Component|Hook|Store|Page|View|Schema|Serializer"
STEM_RX = re.compile(rf"^(?:[A-Z][A-Za-z0-9]*?)({SUFFIXES})$|^[a-z0-9_]+_({SUFFIXES.lower()})$|^use[A-Z]\w+$|^(use)[A-Z]")
EXT = {"python": ".py", "php": ".php", "typescript": ".ts", "javascript": ".js", "matlab": ".m", "shell": ".sh"}
_cache: dict = {}


def load(root: Path) -> dict | None:
    key = str(root)
    if key not in _cache:
        f = root / DIRNAME / "architecture.toml"
        _cache[key] = tomllib.loads(f.read_text()) if f.is_file() else None
    return _cache[key]


def prefix(glob: str) -> str:
    return re.split(r"[*?\[]", glob)[0].rstrip("/").lower()


def layer_of(arch: dict, path: str) -> dict | None:
    for l in arch.get("layer", []):
        if any(fnmatch.fnmatch(path, g) for g in l.get("paths", [])): return l
    return None


def layer_of_import(arch: dict, imp: str, file: str) -> dict | None:
    """Layer a module reference points to; longest matching path prefix wins (case-insensitive; dots, backslashes, slashes equal)."""
    n = re.sub(r"[.\\]+", "/", imp) if not imp.startswith(".") else os.path.normpath(os.path.join(os.path.dirname(file), imp))
    n = n.strip("/").lower()
    best, blen = None, 0
    for l in arch.get("layer", []):
        for g in l.get("paths", []):
            p = prefix(g)
            if p and (n == p or n.startswith(p + "/")) and len(p) > blen: best, blen = l, len(p)
    return best


IMPORT = [re.compile(r"^\s*from\s+([\w.]+)\s+import\b", re.M), re.compile(r"^\s*import\s+([\w.]+)", re.M),
          re.compile(r"""(?:from|require\()\s*['"]([^'"]+)['"]"""), re.compile(r"^\s*use\s+([\w\\]+)", re.M)]


def check(root: Path, f, lang: str):
    """[(line, id, message)] for one file."""
    arch = load(root)
    if not arch: return []
    path = str(f); l = layer_of(arch, path)
    if not l or re.search(r"(^|/)(tests?|__tests__)/|__init__|(^|/)index\.", path): return []
    out = []
    pat = l.get("name_pattern")
    if pat and not re.fullmatch(pat, Path(path).stem): out.append((1, "ARCHNAME", f"{Path(path).stem} in layer '{l['name']}' should match {pat}"))
    allowed = l.get("may_import")
    if allowed is not None:
        text = (root / f).read_text(errors="replace")
        for rx in IMPORT:
            for m in rx.finditer(text):
                t = layer_of_import(arch, m.group(1), path)
                if t and t["name"] != l["name"] and t["name"] not in allowed:
                    out.append((text.count("\n", 0, m.start()) + 1, "ARCHDEP", f"layer '{l['name']}' imports '{t['name']}' ({m.group(1)}); allowed: {', '.join(allowed) or 'none'}"))
    return out


def summary(arch: dict) -> str:
    a = arch.get("architecture", {})
    lines = [f"architecture: {a.get('style', '?')}" + (f" - {a['summary']}" if a.get("summary") else "")]
    for l in arch.get("layer", []):
        dep = f" -> {', '.join(l['may_import']) or '(nothing)'}" if l.get("may_import") is not None else ""
        lines.append(f"- {l['name']}: {', '.join(l.get('paths', []))}" + (f"  /{l['name_pattern']}/" if l.get("name_pattern") else "") + dep + (f"  ({l['role']})" if l.get("role") else ""))
    for k, v in arch.get("conventions", {}).items(): lines.append(f"* {k}: {v}")
    return "\n".join(lines)


def cmd_show(root, arch, name):
    l = next((x for x in arch.get("layer", []) if x["name"] == name), None)
    if not l: print(f"no layer '{name}'; layers: {', '.join(x['name'] for x in arch.get('layer', []))}"); return 1
    for k, v in l.items(): print(f"{k}: {v}")
    files = [str(f) for f in tracked_files(root) if layer_of(arch, str(f)) is l][:3]
    if files: print("existing, to imitate: " + ", ".join(files))
    return 0


def cmd_new(root, arch, name):
    langs = load_config(root).get("project", {}).get("languages", [])
    default_ext = next((EXT[x] for x in langs if x in EXT), ".py")
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
    for l in arch.get("layer", []):
        if not l.get("stem"): continue
        d = prefix(l["paths"][0]) if l.get("paths") else "."
        real = next((str(f.parent) for f in tracked_files(root) if layer_of(arch, str(f)) is l), None)
        ext = Path(l["example"]).suffix if l.get("example") else default_ext
        p = Path(real or d) / (l["stem"].format(Name=name, name=snake) + ext)
        print(f"{l['name']:<12}{p}  {'exists' if (root / p).exists() else 'missing'}" + (f"  base {l['base']}" if l.get("base") else ""))
    return 0


def cmd_infer(root, write, check=False, interview=False, answer=(), force=False):
    import arch_infer as ai
    answers, given = ai.load_answers(root), dict(x.split("=", 1) for x in answer if "=" in x)
    answers.update(given)
    o = ai.options(root)
    model = ai.analyze(root, o, answers)
    if model is None:
        print("no directory with a recurring Controller/Service/Repository/... pattern found: write architecture.toml by hand (templates/architecture.toml)"); return 0
    if interview: print(ai.interview(model, answers, o["max_questions"])); return 0
    if check: print(ai.check(model)); return 0
    text = ai.render(model)
    if not write: print(text); return 0
    dest = root / DIRNAME / "architecture.toml"
    if not force and dest.is_file() and any(l.strip() and not l.startswith("#") for l in dest.read_text().splitlines()):
        print("architecture.toml already has content: not overwritten (--force rebuilds it from the repo and the saved answers)"); return 1
    if given: ai.save_answers(root, answers)
    dest.write_text(text); print(f"wrote {dest}: review it, set style and summary" + (f"; answers saved in {DIRNAME}/{ai.ANSWERS_FILE}" if given else "")); return 0


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", nargs="?", default="summary"); ap.add_argument("name", nargs="?")
    ap.add_argument("--write", action="store_true"); ap.add_argument("--root"); ap.add_argument("--check", action="store_true")
    ap.add_argument("--interview", action="store_true"); ap.add_argument("--answer", action="append", default=[]); ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    root = find_root(a.root)
    if a.cmd == "infer": return cmd_infer(root, a.write, a.check, a.interview, a.answer, a.force)
    arch = load(root)
    if not arch or not arch.get("layer") and not arch.get("architecture"):
        print("no architecture.toml (or empty): `ff arch infer` drafts one from the repo"); return 0
    if a.cmd == "show" and a.name: return cmd_show(root, arch, a.name)
    if a.cmd == "new" and a.name: return cmd_new(root, arch, a.name)
    print(summary(arch)); return 0
