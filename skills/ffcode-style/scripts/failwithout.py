"""Do the tests fail without the production change? Reverts the non-test files of the diff to BASE (added ones are moved away),
runs the test command, restores everything (try/finally), reports. A test that stays green proves nothing.
  failwithout.py [--root DIR] [--base REF] [--cmd CMD]
Needs the production change and the tests in the working tree (committed or not); refuses if a non-test file is untracked and unreadable."""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
from pathlib import Path

from common import find_root, git, load_config, run

TESTP = re.compile(r"(^|/)(tests?|spec|__tests__)/|(_test|Test|\.test|\.spec)\.\w+$")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--root"); ap.add_argument("--base"); ap.add_argument("--cmd")
    a = ap.parse_args(); root = find_root(a.root); cfg = load_config(root)
    base = a.base or cfg["check"].get("base", "main"); cmd = a.cmd or cfg["commands"].get("test")
    if not cmd: print("no test command: pass --cmd or set [commands] test"); return 2
    rc, out = git(["diff", "--name-status", "--diff-filter=AM", base], root)
    _, un = git(["ls-files", "--others", "--exclude-standard"], root)
    prod = [(s, p) for s, p in (l.split("\t", 1) for l in out.splitlines() if "\t" in l)
            if not TESTP.search(p) and not p.startswith(".ffcode/") and p != "composer.lock"]
    prod += [("A", p) for p in un.splitlines() if p and not TESTP.search(p) and not p.startswith(".ffcode/")]
    if not prod: print("no production files changed vs " + base); return 2
    tmp = Path(tempfile.mkdtemp(prefix="ffcode-fw-"))
    saved = []
    try:
        for st, p in prod:
            src = root / p; (tmp / p).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, tmp / p); saved.append((st, p))
        for st, p in saved:
            if st == "A": (root / p).unlink()
            else:
                rc, o = git(["checkout", base, "--", p], root)
                if rc != 0: raise RuntimeError(o)
        print(f"reverted {len(saved)} production file(s) to {base}; running: {cmd}")
        rc, o = run(cmd, cwd=root)
    finally:
        for st, p in saved:
            (root / p).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(tmp / p, root / p)
        shutil.rmtree(tmp, ignore_errors=True)
    print("production files restored")
    tail = "\n".join(o.splitlines()[-8:])
    if rc != 0: print("OK: tests FAIL without the change (as they should)\n" + tail); return 0
    print("PROBLEM: tests PASS without the change - they do not pin it"); return 1


if __name__ == "__main__":
    sys.exit(main())
