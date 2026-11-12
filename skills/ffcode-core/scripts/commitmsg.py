"""Validate a commit message against [commit] in .ffcode/config.toml. Usage: commitmsg.py [--root DIR] "message" | -f FILE"""
from __future__ import annotations

import argparse
import re
import sys

from common import find_root, load_config

CONV = re.compile(r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([\w./-]+\))?!?: \S")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("msg", nargs="?"); ap.add_argument("-f"); ap.add_argument("--root")
    a = ap.parse_args()
    msg = open(a.f).read() if a.f else (a.msg or sys.stdin.read())
    cfg = load_config(find_root(a.root))["commit"]; style = cfg.get("style", "conventional"); mx = cfg.get("max_subject", 72)
    subj = msg.strip().splitlines()[0] if msg.strip() else ""
    errs = []
    if not subj: errs.append("empty subject")
    if len(subj) > mx: errs.append(f"subject {len(subj)} > {mx} chars")
    if subj.endswith("."): errs.append("subject ends with a period")
    if style == "conventional" and not CONV.match(subj): errs.append("expected 'type(scope): summary' (feat, fix, refactor, docs, test, chore, ...)")
    if style == "imperative" and re.match(r"(?i)^(added|fixed|updated|removed|changed)\b", subj): errs.append("use the imperative: 'Add', not 'Added'")
    if len(msg.strip().splitlines()) > 1 and msg.strip().splitlines()[1].strip(): errs.append("blank line required after subject")
    print("\n".join(errs) if errs else "commit message OK")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
