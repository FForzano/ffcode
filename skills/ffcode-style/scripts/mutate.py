"""Optional mutation testing on the changed files that match the project's critical areas.
  mutate.py [--root DIR] [--base REF] [--all-critical] [--list]
Config (.ffcode/config.toml):
  [mutation]
  critical = ["services/pricing*/**", "services/payments/**"]   # globs of code where a surviving mutant costs money/data
  command  = "mutmut run --paths-to-mutate {files}"            # {files} = space-separated changed critical files
Prints the command it runs and its tail; it does not interpret tool-specific output. Slow: run only when asked."""
from __future__ import annotations

import argparse
import fnmatch
import sys

from common import find_root, git, load_config, run, tracked_files


def match(path: str, globs) -> bool:
    return any(fnmatch.fnmatch(path, g) or fnmatch.fnmatch(path, g.replace("**", "*")) for g in globs)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--root"); ap.add_argument("--base"); ap.add_argument("--all-critical", action="store_true")
    ap.add_argument("--list", action="store_true", help="show which files are critical and changed, run nothing")
    a = ap.parse_args(); root = find_root(a.root); cfg = load_config(root); m = cfg.get("mutation", {})
    crit = m.get("critical", [])
    if not crit: print("no [mutation] critical globs in config.toml: nothing is marked as worth mutating"); return 2
    if a.all_critical: files = [str(f) for f in tracked_files(root)]
    else: files = [str(f) for f in tracked_files(root, only_changed=True, base=a.base or cfg["check"].get("base", "main"))]
    files = [f for f in files if match(f, crit) and "test" not in f.lower()]
    if not files: print("no changed file in a critical area"); return 0
    print("critical files in scope:\n  " + "\n  ".join(files))
    if a.list: return 0
    cmd = m.get("command")
    if not cmd: print("no [mutation] command configured"); return 2
    cmd = cmd.replace("{files}", " ".join(files))
    print("running:", cmd)
    rc, out = run(cmd, cwd=root, timeout=3600)
    print("\n".join(out.splitlines()[-30:])); return 0 if rc == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
