"""Is a newer version of the ffcode skills available? Never updates unless --apply (which the skill runs only after the user said yes).
  update_check.py [--force] [--verbose]   silent unless an update exists (checks at most once a week; FFCODE_NO_UPDATE_CHECK=1 disables)
  update_check.py --apply                 git pull --ff-only in the skills repo, then re-run install.sh in the mode it was installed with
Repo location: $FFCODE_REPO, else the git repo this script lives in (symlink install), else the marker <skills dir>/.ffcode-repo (copy install)."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from common import git, run

WEEK = 7 * 24 * 3600
CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "ffcode" / "update-check.json"


def repo_and_mode():
    if os.environ.get("FFCODE_REPO"): return Path(os.environ["FFCODE_REPO"]), "link"
    rc, top = git(["rev-parse", "--show-toplevel"], Path(__file__).resolve().parent)
    if rc == 0 and (Path(top.strip()) / "install.sh").is_file(): return Path(top.strip()), "link"
    marker = Path(os.environ.get("CLAUDE_SKILLS_DIR", Path.home() / ".claude" / "skills")) / ".ffcode-repo"
    if marker.is_file():
        lines = marker.read_text().split()
        if lines and Path(lines[0]).is_dir(): return Path(lines[0]), (lines[1] if len(lines) > 1 else "copy")
    return None, None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--force", action="store_true"); ap.add_argument("--verbose", action="store_true"); ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    if os.environ.get("FFCODE_NO_UPDATE_CHECK") and not a.apply: return 0
    repo, mode = repo_and_mode()
    if not repo:
        if a.verbose or a.apply: print("ffcode repo not found (run ./install.sh from the repository once)")
        return 1 if a.apply else 0
    if a.apply:
        _, dirty = git(["status", "--porcelain", "--untracked-files=no"], repo)
        if dirty.strip(): print("NOT UPDATED: the ffcode repo has local changes; commit or stash them first"); return 1
        rc, out = git(["pull", "--ff-only"], repo)
        if rc != 0: print("NOT UPDATED: pull failed (not a fast-forward?)\n" + out.strip()[-300:]); return 1
        rc, out = run(["bash", str(repo / "install.sh")] + (["--copy"] if mode == "copy" else []), cwd=repo)
        print(("UPDATED and reinstalled (new session needed to load changed skills)" if rc == 0 else "pulled, but install.sh failed:\n" + out[-300:]))
        return 0 if rc == 0 else 1
    last = json.loads(CACHE.read_text()).get("last", 0) if CACHE.is_file() else 0
    if not a.force and time.time() - last < WEEK:
        if a.verbose: print("checked less than a week ago")
        return 0
    CACHE.parent.mkdir(parents=True, exist_ok=True); CACHE.write_text(json.dumps({"last": time.time()}))   # also when the user declines: ask again next week
    if git(["remote"], repo)[1].strip() == "":
        if a.verbose: print("no remote configured")
        return 0
    rc, out = run(["git", "fetch", "-q"], cwd=repo, timeout=15)
    if rc != 0:
        if a.verbose: print("could not reach the remote (offline?)")
        return 0
    _, n = git(["rev-list", "--count", "HEAD..@{u}"], repo)
    if not n.strip().isdigit() or int(n) == 0:
        if a.verbose: print("ffcode is up to date")
        return 0
    _, subj = git(["log", "--format=- %s", "-6", "HEAD..@{u}"], repo)
    print(f"UPDATE_AVAILABLE: {n.strip()} new commit(s) in the ffcode skills ({repo})\n{subj.strip()}\nAsk the user whether to update; if yes run: update-check --apply")
    return 0


if __name__ == "__main__":
    sys.exit(main())
