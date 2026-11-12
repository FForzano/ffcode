"""Generated indexes in .ffcode/cache/ (rebuilt by `ff map`): tests-map.json (source -> tests) and hotspots.json (churn x size).
  ff tests-for FILE.. | --changed [--run]   tests that cover those files; --run executes [commands] test_one with {files}
  ff hotspots [-n N]                        most-changed large files of the last 12 months (where bugs and review effort concentrate)"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from common import DIRNAME, find_root, git, is_text, lang_of, load_config, tracked_files
from report import TEST

IMPORTS = [re.compile(r"^\s*from\s+([\w.]+)\s+import\s+([\w, ]+)", re.M), re.compile(r"^\s*import\s+([\w.]+)", re.M),
           re.compile(r"""(?:from|require\(|import\()\s*['"]([^'"]+)['"]"""), re.compile(r"^\s*use\s+[\w\\]+\\(\w+)", re.M)]


def stem(p: str) -> str:
    return re.sub(r"^test_|_test$|\.(test|spec)$|Test$", "", Path(p).stem)


def import_stems(text: str) -> set[str]:
    out = set()
    for rx in IMPORTS:
        for m in rx.finditer(text):
            for g in m.groups():
                for part in re.split(r"[,\s]+", g or ""):
                    if part: out.add(re.split(r"[./\\]", part.rstrip("./\\"))[-1])
    return {s for s in out if len(s) >= 3}


def build_tests_map(root: Path, files) -> dict:
    code = [f for f in files if lang_of(f) in ("python", "php", "typescript", "javascript", "matlab", "shell")]
    tests = [str(f) for f in code if TEST.search(str(f))]
    by_stem = defaultdict(list)
    for f in code:
        if not TEST.search(str(f)): by_stem[Path(f).stem].append(str(f))
    out = defaultdict(set)
    for t in tests:
        cands = {stem(t)} | import_stems((root / t).read_text(errors="replace"))
        for s in cands:
            for src in by_stem.get(s, []): out[src].add(t)
    return {k: sorted(v) for k, v in sorted(out.items())}


def build_hotspots(root: Path, files, top=50) -> list:
    rc, log = git(["log", "--since=12 months ago", "--name-only", "--format="], root)
    if rc: return []
    counts = Counter(l for l in log.splitlines() if l)
    rows = []
    for f in files:
        c = counts.get(str(f), 0)
        if c < 2 or TEST.search(str(f)) or not is_text(root / f): continue
        n = sum(1 for _ in (root / f).open(errors="replace"))
        rows.append({"file": str(f), "commits": c, "lines": n, "score": round(c * math.sqrt(n), 1)})
    return sorted(rows, key=lambda r: -r["score"])[:top]


def build_all(root: Path, files):
    d = root / DIRNAME / "cache"; d.mkdir(parents=True, exist_ok=True)
    tm = build_tests_map(root, files); (d / "tests-map.json").write_text(json.dumps(tm, indent=0))
    hs = build_hotspots(root, files); (d / "hotspots.json").write_text(json.dumps(hs, indent=0))
    return len(tm), len(hs)


def _load(root: Path, name: str, builder):
    f = root / DIRNAME / "cache" / name
    if not f.is_file(): build_all(root, [x for x in tracked_files(root) if is_text(root / x)])
    return json.loads(f.read_text()) if f.is_file() else builder


def tests_for():
    ap = argparse.ArgumentParser(); ap.add_argument("files", nargs="*"); ap.add_argument("--changed", action="store_true")
    ap.add_argument("--run", action="store_true"); ap.add_argument("--root")
    a = ap.parse_args(); root = find_root(a.root); cfg = load_config(root)
    files = [str(f) for f in tracked_files(root, True, False, cfg["check"].get("base"))] if a.changed else a.files
    tm = _load(root, "tests-map.json", {}); found, missing = set(), []
    for f in files:
        f = str(Path(f))
        if TEST.search(f): found.add(f)
        elif f in tm: found.update(tm[f])
        elif lang_of(Path(f)) in ("python", "php", "typescript", "javascript", "matlab"): missing.append(f)
    for t in sorted(found): print(t)
    for f in missing: print(f"no test found for {f}  (T1: add one, or run `ff map` if tests were just added)")
    if a.run and found:
        cmd = cfg["commands"].get("test_one")
        if not cmd: print("set [commands] test_one in .ffcode/config.toml, e.g. \"pytest -q {files}\""); return 2
        return subprocess.call(cmd.replace("{files}", " ".join(sorted(found))), shell=True, cwd=root)
    return 0


def hotspots():
    ap = argparse.ArgumentParser(); ap.add_argument("-n", type=int, default=10); ap.add_argument("--root"); a = ap.parse_args()
    root = find_root(a.root)
    for r in _load(root, "hotspots.json", [])[:a.n]: print(f"{r['file']}  {r['commits']} commits, {r['lines']} lines")
    return 0


def main():
    import sys
    return {"tests-for": tests_for, "hotspots": hotspots}[sys.argv.pop(1)]()
