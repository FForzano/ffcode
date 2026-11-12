"""Propose how to split the working changes into commits; Claude reviews the proposal instead of reading the diff to invent it.
  ff commit-plan [--root DIR]
Groups changed files (staged, unstaged, untracked) by area, pairs each test with the code of the same stem, puts docs, build/CI,
dependencies and migrations in their own group, and lists what to leave out (generated, caches, large binaries, secrets leads)."""
from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

from common import DIRNAME, find_root, git
from report import TEST, area

LEAVE = re.compile(rf"(^|/)({DIRNAME}/(map\.md|cache|repos)|node_modules|__pycache__|\.venv|dist|build)(/|$)|\.(pyc|log|DS_Store)$|(^|/)\.env$")
KIND = [("docs", r"\.(md|rst|txt)$|(^|/)docs/"), ("ci", r"(^|/)(\.github|\.gitlab-ci|Dockerfile|docker-compose|Makefile)"),
        ("build", r"(^|/)(package(-lock)?\.json|composer\.(json|lock)|pyproject\.toml|requirements.*\.txt|yarn\.lock|poetry\.lock)$"),
        ("feat/fix", r"migrat|\.sql$")]
SECRET = re.compile(r"(^|/)(\.env[^/]*|.*\.pem|.*id_rsa.*|credentials.*)$")


def stem(p: str) -> str:
    return re.sub(r"^test_|_test$|\.(test|spec)$|Test$", "", Path(p).stem)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--root"); a = ap.parse_args()
    root = find_root(a.root)
    _, out = git(["status", "--porcelain", "-uall"], root)
    files = [l[3:].split(" -> ")[-1] for l in out.splitlines() if l.strip()]
    if not files: print("nothing to commit"); return 0
    leave, groups = [], defaultdict(list)
    for p in files:
        full = root / p
        if SECRET.search(p): leave.append((p, "possible secret")); continue
        if LEAVE.search(p): leave.append((p, "generated/cache")); continue
        if full.is_file() and full.stat().st_size > 1_000_000: leave.append((p, "large file")); continue
        kind = next((k for k, rx in KIND if re.search(rx, p, re.I)), None)
        groups[kind or area(p)].append(p)
    stems = {stem(p): k for k, v in groups.items() for p in v if not TEST.search(p)}
    for k in list(groups):
        for p in [p for p in groups[k] if TEST.search(p)]:
            tgt = stems.get(stem(p))
            if tgt and tgt != k: groups[k].remove(p); groups[tgt].append(p)
    groups = {k: v for k, v in groups.items() if v}
    print(f"{len(files)} changed file(s) -> {len(groups)} proposed commit(s) (stage by explicit path, never `git add -A`):")
    for n, (k, v) in enumerate(sorted(groups.items()), 1):
        hint = k if k in ("docs", "ci", "build", "feat/fix") else "feat|fix|refactor"
        print(f"\n{n}. [{hint}] {k}  ({len(v)})")
        for p in v: print(f"   {p}")
    if leave:
        print("\nleave out:")
        for p, why in leave: print(f"   {p}  ({why})")
    return 0
