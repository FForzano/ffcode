"""One call instead of four file reads: .ffcode/context.md, style.md, state.md and the head of map.md, each with a header.
  ff orient [--map-lines N] [--no-map]   (default 200 map lines; `ff find` for the rest)
Runs `ff sync` first: creates/upgrades .ffcode/ and refreshes what is stale, then prints NEEDS (what the developer must decide)."""
from __future__ import annotations

import argparse

from common import DIRNAME, SCHEMA, find_root, git


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--map-lines", type=int, default=200); ap.add_argument("--no-map", action="store_true"); ap.add_argument("--root")
    a = ap.parse_args()
    root = find_root(a.root); d = root / DIRNAME
    import sync
    is_repo = (root / ".git").exists()
    log, needs = sync.sync(root, init=is_repo, quick=False)          # creates .ffcode/ in a git repo, upgrades, refreshes, lists NEEDS
    if not d.is_dir():
        print("NO_FFCODE: not a git repository, so .ffcode/ was not created; run `ff init` there if wanted"); return 0
    print(f"# root: {root}")
    out = sync.format_output(log, needs)
    if out: print(out)
    import hooks
    if hooks.hint_due(): print("NOTE: " + hooks.HINT)
    import upgrade
    if upgrade.version(root) < SCHEMA: print(f"NOTE: .ffcode/ is schema {upgrade.version(root)}, current {SCHEMA} (automatic upgrade is disabled): run `ff upgrade`")
    for name in ("context", "style", "state", "rules"):
        f = d / (f"{name}.toml" if name == "rules" else f"{name}.md")
        if name == "rules" and not any(l.strip() and not l.startswith("#") for l in (f.read_text().splitlines() if f.is_file() else [])): continue
        text = f.read_text().strip() if f.is_file() else ""
        print(f"\n## {f.name}" + ("" if text else " (missing or empty)"))
        if text: print(text)
    import arch
    ar = arch.load(root)
    if ar and (ar.get("layer") or ar.get("architecture")): print("\n## architecture.toml\n" + arch.summary(ar))
    if a.no_map: return 0
    f = d / "map.md"
    if not f.is_file():
        print("\n## map.md (missing: run `ff map`)"); return 0
    lines = f.read_text().splitlines()
    rc, ct = git(["log", "-1", "--format=%ct"], root)
    stale = rc == 0 and ct.strip().isdigit() and f.stat().st_mtime < int(ct)
    print(f"\n## map.md ({len(lines)} lines{', STALE: run `ff map`' if stale else ''})")
    print("\n".join(lines[:a.map_lines]))
    if len(lines) > a.map_lines: print(f"... {len(lines) - a.map_lines} more lines: use `ff find NAME`")
    return 0
