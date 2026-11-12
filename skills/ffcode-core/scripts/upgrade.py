"""Bring an already initialized project up to the current ffcode layout. Idempotent, never overwrites content, never touches your code.
  ff upgrade [--dry-run] [--no-git-hooks]      this project
  ff upgrade --all DIR [--dry-run]             every project with a .ffcode/ under DIR (depth <= 3)
Steps: missing files from the templates (rules.toml, glossary.md, architecture.toml), missing lines in .ffcode/.gitignore, a test_one hint in
config.toml, decision index, map and indexes, git hooks for the map, validation, then .ffcode/version = current schema."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from common import DIRNAME, SCHEMA, find_root, load_config

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
FILES = ["rules.toml", "glossary.md", "architecture.toml"]
IGNORE = ["map.md", "workspace-map.md", "cache/", "repos/", "state.md", "flows/"]


def version(root: Path) -> int:
    f = root / DIRNAME / "version"
    return int(f.read_text().strip()) if f.is_file() and f.read_text().strip().isdigit() else 1


def upgrade(root: Path, dry: bool, git_hooks: bool, quiet: bool = False):
    """Returns (code, log). Prints the report unless quiet."""
    d = root / DIRNAME; log = []
    if not d.is_dir():
        if not quiet: print(f"{root}: no {DIRNAME}/ (run ff init)")
        return 1, log
    have = version(root)
    for name in FILES:
        if not (d / name).exists():
            log.append(f"create {name}")
            if not dry: (d / name).write_text((TEMPLATES / name).read_text())
    gi = d / ".gitignore"; text = gi.read_text() if gi.is_file() else ""
    missing = [l for l in IGNORE if l not in text.split()]
    if missing:
        log.append("gitignore +" + ", ".join(missing))
        if not dry: gi.write_text(text + ("" if not text or text.endswith("\n") else "\n") + "\n".join(missing) + "\n")
    cfg = d / "config.toml"
    if cfg.is_file():
        c = cfg.read_text()
        if "test_one" not in c and re.search(r"^\[commands\]", c, re.M):
            hint = '# test_one = "pytest -q {files}"   # narrowest test: ff tests-for FILE --run substitutes {files}'
            log.append("config.toml: test_one hint")
            if not dry: cfg.write_text(re.sub(r"^(\[commands\][^\n]*\n)", lambda m: m.group(1) + hint + "\n", c, count=1, flags=re.M))
    if (d / "decisions").is_dir() and list((d / "decisions").glob("[0-9]*-*.md")):
        log.append("decisions/index.md")
        if not dry:
            import adr; adr.write_index(d / "decisions")
    if not dry:
        import mapper
        text_, idx = mapper.build(root, 12); (d / "map.md").write_text(text_)
        import json
        (d / "cache").mkdir(exist_ok=True); (d / "cache" / "symbols.json").write_text(json.dumps({f: [[i, k, n] for i, k, n in s] for f, s in idx.items()}))
        import indexes
        from common import is_text, tracked_files
        indexes.build_all(root, [f for f in tracked_files(root) if is_text(root / f)])
    log.append("map, tests-map, hotspots")
    if git_hooks and (root / ".git").exists():
        log.append("git hooks (map refresh)")
        if not dry:
            import hooks, os
            cwd = os.getcwd(); os.chdir(root)
            try: hooks.git_hooks(False)
            finally: os.chdir(cwd)
    if not dry:
        (d / "version").write_text(f"{SCHEMA}\n")
        import config as cfgmod
        errs, warns = [], []
        for name, fn in (("config.toml", cfgmod.config_toml), ("rules.toml", cfgmod.rules_toml), ("architecture.toml", cfgmod.architecture_toml),
                         ("design.toml", cfgmod.design_toml), ("workspace.toml", cfgmod.workspace_toml)):
            if (d / name).is_file(): fn(d / name, errs, warns)
        log += [f"WARN {w}" for w in warns] + [f"ERROR {e}" for e in errs]
    import hooks
    if not hooks.installed() and not quiet: log.append("NOTE ffcode hooks not installed: run `ff hooks install` once per machine")
    if not quiet:
        print(f"{root.name}: schema {have} -> {SCHEMA}" + (" (dry run)" if dry else ""))
        for l in log: print("  " + l)
    return 0, log


def auto(root: Path):
    """Called by the ff dispatcher: if this project is behind, upgrade it now (no git hooks, no prompts) and say so once on stderr.
    FFCODE_NO_AUTO_UPGRADE=1 disables it."""
    import os
    if os.environ.get("FFCODE_NO_AUTO_UPGRADE") or not (root / DIRNAME).is_dir() or version(root) >= SCHEMA: return
    have = version(root)
    try: _, log = upgrade(root, False, False, quiet=True)
    except OSError as e:
        print(f"ffcode: automatic upgrade of {DIRNAME}/ failed ({e}); run `ff upgrade`", file=sys.stderr); return
    done = [l for l in log if l.startswith(("create", "gitignore", "config.toml"))]
    print(f"ffcode: {DIRNAME}/ upgraded from schema {have} to {SCHEMA} automatically ({'; '.join(done) or 'indexes refreshed'}). New files are uncommitted: tell the user once.", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--root"); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--all", metavar="DIR"); ap.add_argument("--no-git-hooks", action="store_true"); a = ap.parse_args()
    if a.all:
        base = Path(a.all).expanduser().resolve()
        roots = sorted({p.parent for p in base.glob("*/" + DIRNAME) } | {p.parent for p in base.glob("*/*/" + DIRNAME)} | {p.parent for p in base.glob("*/*/*/" + DIRNAME)})
        roots = [r for r in roots if DIRNAME not in r.parts]  # skip the clones under .ffcode/repos
        if not roots: print(f"no {DIRNAME}/ under {base}"); return 0
        for r in roots: upgrade(r, a.dry_run, not a.no_git_hooks)
        return 0
    return upgrade(find_root(a.root), a.dry_run, not a.no_git_hooks)[0]
