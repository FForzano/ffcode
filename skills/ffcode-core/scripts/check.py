"""Mechanical gate: configured commands + ffcode lint, output compressed to what matters.
  check.py [--root DIR] [--changed|--staged] [--only lint,test,...] [--lines N] [--no-lint]
Runs [commands] from .ffcode/config.toml in this order: format_check, lint, typecheck, test, build, then
ffcode lint on the scope. Prints one line per step and the tail of failing steps. Exit 1 on any failure.
With --changed/--staged the test step runs [commands] test_one on the tests covering the diff (ff tests-for);
without test_one it falls back to the whole suite and says so. A step that exceeds its timeout is TIMEOUT, not FAIL:
it verified nothing, the result is UNVERIFIED and the exit code is 3 (0 OK, 1 FAIL): never a false OK.
[check] test_timeout (default 900 s) bounds the whole suite, scoped_test_timeout (default 300 s) a scoped run."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

from common import find_root, load_config, run, tracked_files
from indexes import covering_tests

ORDER = ["format_check", "lint", "typecheck", "test", "build"]
TIMEOUT_RC = 124
EXIT_UNVERIFIED = 3
DEFAULT_TIMEOUT, DEFAULT_SCOPED_TIMEOUT = 900, 300
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


def test_command(root, cfg, scoped, staged):
    """(command, timeout, note) for the test step; command None = nothing to run."""
    chk = cfg["check"]; full = chk.get("test_timeout", DEFAULT_TIMEOUT)
    cmd = cfg["commands"].get("test")
    one = cfg["commands"].get("test_one")
    if not scoped: return cmd, full, ""
    if not one:
        return cmd, full, "no [commands] test_one: running the whole suite for a scoped check (slow); set test_one to run only the tests covering the diff"
    files = [str(f) for f in tracked_files(root, not staged, staged, chk.get("base"))]
    found, missing = covering_tests(root, files)
    note = "; ".join(f"no test for {m}" for m in missing[:5])
    if not found: return None, 0, "no test covers the diff" + (f" ({note})" if note else "")
    return one.replace("{files}", " ".join(sorted(found))), chk.get("scoped_test_timeout", DEFAULT_SCOPED_TIMEOUT), note


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root"); ap.add_argument("--changed", action="store_true"); ap.add_argument("--staged", action="store_true")
    ap.add_argument("--only"); ap.add_argument("--lines", type=int, default=24); ap.add_argument("--no-lint", action="store_true")
    ap.add_argument("--json", action="store_true", help="machine-readable result")
    ap.add_argument("--coverage", action="store_true", help="run [commands] coverage and report diff coverage")
    a = ap.parse_args()
    root = find_root(a.root); cfg = load_config(root)
    only = set(a.only.split(",")) if a.only else None
    results, notes = [], []
    for step in ORDER:
        cmd, timeout = cfg["commands"].get(step), 900
        if step == "test" and (not only or step in only):
            cmd, timeout, note = test_command(root, cfg, a.changed or a.staged, a.staged)
            if note: notes.append(note)
        if not cmd or (only and step not in only): continue
        t = time.time(); rc, out = run(cmd, cwd=root, timeout=timeout); results.append((step, cmd, rc, time.time() - t, out))
    if not a.no_lint and (not only or "ffcode-lint" in only):
        here = Path(__file__).parent
        args = [sys.executable, str(here / "lint.py"), "--root", str(root), "--summary"]
        args += ["--changed"] if a.changed else (["--staged"] if a.staged else [])
        t = time.time(); rc, out = run(args); results.append(("ffcode-lint", "lint.py", rc, time.time() - t, out))
    if cfg["check"].get("ui") and not a.no_lint and (not only or "uilint" in only):
        here = Path(__file__).parent
        args = [sys.executable, str(here / "uilint.py"), "--root", str(root), "--summary"] + (["--changed"] if a.changed else (["--staged"] if a.staged else []))
        t = time.time(); rc, out = run(args); results.append(("uilint", "uilint.py", rc, time.time() - t, out))
    if a.coverage:
        here = Path(__file__).parent
        t = time.time(); rc, out = run([sys.executable, str(here / "diffcov.py"), "--root", str(root), "--run"])
        results.append(("diffcov", "diffcov.py --run", rc, time.time() - t, out))
    if a.json:
        import json
        steps = [{"step": s, "cmd": c, "ok": rc == 0, "timeout": rc == TIMEOUT_RC, "seconds": round(dt, 1),
                  "tail": squeeze(out, a.lines) if rc else ""} for s, c, rc, dt, out in results]
        failed = [x for x in steps if not x["ok"] and not x["timeout"]]; unverified = [x["step"] for x in steps if x["timeout"]]
        print(json.dumps({"result": "FAIL" if failed else ("UNVERIFIED" if unverified else "OK"), "unverified": unverified, "notes": notes,
                          "steps": steps, "skipped": [s for s in ORDER if not cfg["commands"].get(s)]}))
        return 1 if failed else (EXIT_UNVERIFIED if unverified else 0)
    bad, unverified = 0, []
    for step, cmd, rc, dt, out in results:
        label = "OK  " if rc == 0 else ("TIMEOUT" if rc == TIMEOUT_RC else "FAIL")
        print(f"{label:7} {step:13} {dt:5.1f}s  {cmd[:120] if isinstance(cmd, str) else cmd}")
        if rc == TIMEOUT_RC: unverified.append(step); print(f"    {out.strip()}: nothing was verified by this step (not a test failure)")
        elif rc != 0:
            bad += 1; print("\n".join("    " + l for l in squeeze(out, a.lines).splitlines()))
    for n in notes: print(f"note: {n}")
    skipped = [s for s in ORDER if not cfg["commands"].get(s)]
    if skipped: print(f"skipped (no command in config): {', '.join(skipped)}")
    print("RESULT:", "FAIL" if bad else (f"UNVERIFIED ({', '.join(unverified)})" if unverified else "OK"))
    return 1 if bad else (EXIT_UNVERIFIED if unverified else 0)


if __name__ == "__main__":
    sys.exit(main())
