"""Mechanical gate: configured commands + ffcode lint, output compressed to what matters.
  check.py [--root DIR] [--changed|--staged] [--only lint,test,...] [--lines N] [--no-lint]
Runs [commands] from .ffcode/config.toml in this order: format_check, lint, typecheck, test, build, then
ffcode lint on the scope. Prints one line per step and the tail of failing steps. Exit 1 on any failure."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

from common import find_root, load_config, run

ORDER = ["format_check", "lint", "typecheck", "test", "build"]
KEY = re.compile(r"(error|fail|exception|traceback|assert|warning:|✗|FAILED|not ok)", re.I)


def squeeze(out: str, n: int) -> str:
    lines = [l for l in out.splitlines() if l.strip()]
    keep = [i for i, l in enumerate(lines) if KEY.search(l)]
    if len(lines) <= n: return "\n".join(lines)
    pick = sorted(set(keep[:n // 2] + list(range(max(0, len(lines) - n // 2), len(lines)))))
    res, prev = [], -1
    for i in pick:
        if prev >= 0 and i != prev + 1: res.append("   ...")
        res.append(lines[i][:200]); prev = i
    return "\n".join(res)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root"); ap.add_argument("--changed", action="store_true"); ap.add_argument("--staged", action="store_true")
    ap.add_argument("--only"); ap.add_argument("--lines", type=int, default=24); ap.add_argument("--no-lint", action="store_true")
    a = ap.parse_args()
    root = find_root(a.root); cfg = load_config(root)
    only = set(a.only.split(",")) if a.only else None
    results = []
    for step in ORDER:
        cmd = cfg["commands"].get(step)
        if not cmd or (only and step not in only): continue
        t = time.time(); rc, out = run(cmd, cwd=root); results.append((step, cmd, rc, time.time() - t, out))
    if not a.no_lint and (not only or "ffcode-lint" in only):
        here = Path(__file__).parent
        args = [sys.executable, str(here / "lint.py"), "--root", str(root), "--summary"]
        args += ["--changed"] if a.changed else (["--staged"] if a.staged else [])
        t = time.time(); rc, out = run(args); results.append(("ffcode-lint", "lint.py", rc, time.time() - t, out))
    bad = 0
    for step, cmd, rc, dt, out in results:
        print(f"{'OK  ' if rc == 0 else 'FAIL'} {step:13} {dt:5.1f}s  {cmd}")
        if rc != 0:
            bad += 1; print("\n".join("    " + l for l in squeeze(out, a.lines).splitlines()))
    skipped = [s for s in ORDER if not cfg["commands"].get(s)]
    if skipped: print(f"skipped (no command in config): {', '.join(skipped)}")
    print("RESULT:", "FAIL" if bad else "OK")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
