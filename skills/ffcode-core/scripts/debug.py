"""Debug helpers.
  debug.py log [FILE|-] [--root DIR] [--lines N]   compress a log/traceback: error lines, frames inside this repo, tail
  debug.py bisect GOOD [--cmd CMD] [--bad HEAD]    git bisect run with CMD (default: [commands] test); resets afterwards"""
from __future__ import annotations

import argparse
import re
import sys

from common import find_root, git, load_config, run

ERR = re.compile(r"(error|exception|traceback|fatal|failed|assert|panic|undefined|cannot|denied|timeout)", re.I)


def cmd_log(a, root):
    text = sys.stdin.read() if a.file in (None, "-") else open(a.file, errors="replace").read()
    lines = text.splitlines()
    rx = re.compile(r"(?:File \"|at |in |#\d+ )?(?P<p>(?:/|\.\.?/)?[\w./-]+\.(?:py|php|ts|tsx|js|jsx|m|sh)):?(?P<l>\d+)?")
    frames = []
    for l in lines:
        m = rx.search(l)
        if m and (root / m.group("p").lstrip("/")).is_file() or (m and m.group("p").startswith(str(root))):
            frames.append(l.strip()[:160])
    errs = [l.strip()[:200] for l in lines if ERR.search(l)]
    print(f"{len(lines)} lines in, {len(errs)} error lines, {len(frames)} frames in this repo")
    print("-- first errors"); print("\n".join(dict.fromkeys(errs[:6])))
    if len(errs) > 6: print("-- last errors"); print("\n".join(dict.fromkeys(errs[-4:])))
    if frames: print("-- repo frames (outermost first)"); print("\n".join(list(dict.fromkeys(frames))[:a.lines]))
    print("-- tail"); print("\n".join(l[:200] for l in lines[-6:]))


def cmd_bisect(a, root):
    cmd = a.cmd or load_config(root)["commands"].get("test")
    if not cmd: print("no test command: pass --cmd"); return 2
    _, dirty = git(["status", "--porcelain", "--untracked-files=no"], root)
    if dirty.strip(): print("working tree has changes: commit or stash first"); return 2
    git(["bisect", "start", a.bad, a.good], root)
    rc, out = run(["git", "bisect", "run", "sh", "-c", cmd], cwd=root)
    first = next((l for l in out.splitlines() if "is the first bad commit" in l), None)
    idx = out.find("is the first bad commit")
    print(out[max(0, idx - 60): idx + 700] if first else out[-800:])
    git(["bisect", "reset"], root)
    return 0 if first else 1


def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="c", required=True)
    l = sub.add_parser("log"); l.add_argument("file", nargs="?"); l.add_argument("--root"); l.add_argument("--lines", type=int, default=12)
    b = sub.add_parser("bisect"); b.add_argument("good"); b.add_argument("--bad", default="HEAD"); b.add_argument("--cmd"); b.add_argument("--root")
    a = ap.parse_args(); root = find_root(a.root)
    return cmd_log(a, root) if a.c == "log" else cmd_bisect(a, root)


if __name__ == "__main__":
    sys.exit(main() or 0)
