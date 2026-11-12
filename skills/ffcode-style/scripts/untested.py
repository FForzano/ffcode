"""Symbols added in the diff that no test file mentions, and changed sources without a changed test.
  untested.py [--root DIR] [--base REF]"""
from __future__ import annotations

import argparse
import re

from common import find_root, git, lang_of, load_config
from mapper import SYM

TESTP = re.compile(r"(^|/)(tests?|spec|__tests__)/|(_test|Test|\.test|\.spec)\.\w+$")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--root"); ap.add_argument("--base")
    a = ap.parse_args(); root = find_root(a.root); cfg = load_config(root)
    base = a.base or cfg["check"].get("base", "main")
    rc, out = git(["diff", "-U0", base], root)
    if rc != 0: print(out.strip()); return 2
    cur, added = None, {}
    for l in out.splitlines():
        if l.startswith("+++ b/"): cur = l[6:]
        elif l.startswith("+") and cur and not TESTP.search(cur) and lang_of(cur) in SYM:
            m = SYM[lang_of(cur)].match(l[1:])
            if m:
                g = [x for x in m.groups() if x]; n = g[-1]
                if not n.startswith("_"): added.setdefault(cur, []).append(n)
    _, tests = git(["ls-files", "-co", "--exclude-standard"], root)
    tfiles = [t for t in tests.splitlines() if TESTP.search(t)]
    blob = "\n".join((root / t).read_text(errors="replace") for t in tfiles if (root / t).is_file())
    changed_tests = {l[6:] for l in out.splitlines() if l.startswith("+++ b/") and TESTP.search(l)}
    miss = 0
    for f, names in sorted(added.items()):
        un = [n for n in names if not re.search(rf"\b{re.escape(n)}\b", blob)]
        if un: miss += len(un); print(f"{f}: no test mentions {', '.join(un[:8])}")
    if added and not changed_tests: print("note: sources changed but no test file changed in this diff")
    print(f"untested: {miss} added symbol(s) without a test mention (heuristic: name search in test files)")
    return 1 if miss else 0


if __name__ == "__main__":
    import sys; sys.exit(main())
