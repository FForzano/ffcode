"""All usages of a name, whole word, grouped by file - for safe renames and impact analysis.
  refs.py NAME [--root DIR] [--defs] [--max N]"""
from __future__ import annotations

import argparse
from collections import Counter

from common import find_root, git


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("name"); ap.add_argument("--root"); ap.add_argument("--max", type=int, default=40)
    a = ap.parse_args(); root = find_root(a.root)
    rc, out = git(["grep", "-nIw", "--untracked", "-e", a.name, "--", ".", ":!.ffcode"], root)
    lines = [l for l in out.splitlines() if l.strip()]
    if not lines: print("no usages"); return 0
    per = Counter(l.split(":", 1)[0] for l in lines)
    print(f"{len(lines)} usage(s) in {len(per)} file(s)")
    for f, n in per.most_common(): print(f"  {n:4} {f}")
    print("first lines:")
    for l in lines[:a.max]: print("  " + l[:160])
    if len(lines) > a.max: print(f"  ... +{len(lines) - a.max}")
    return 0


if __name__ == "__main__":
    main()
