"""Multi-repo workspace: several repositories that make up one product. Config: .ffcode/workspace.toml
  workspace.py status | sync [NAME..] [--from-local] | graph | where NAME | contracts [--changed]
workspace.toml:
  [[repo]]  name, url, role (frontend|backend|infra|docs|...), branch (default main),
            local (optional path of an existing checkout, used by --from-local),
            depends_on (list of names), contracts (list of paths inside that repo: OpenAPI, schemas, env examples)
Clones go to .ffcode/repos/<name> (git-ignored by .ffcode/.gitignore). 'self' marks the repo holding .ffcode/."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tomllib
from pathlib import Path

from common import DIRNAME, die, find_root, git


def load(root: Path):
    f = root / DIRNAME / "workspace.toml"
    if not f.is_file(): die(f"no {f}; copy templates/workspace.toml from ffcode-style")
    repos = tomllib.loads(f.read_text()).get("repo", [])
    for r in repos:
        r.setdefault("branch", "main"); r.setdefault("depends_on", []); r.setdefault("contracts", [])
        r["path"] = root if r.get("self") else root / DIRNAME / "repos" / r["name"]
    return repos


def info(r):
    p = r["path"]
    if not (p / ".git").exists(): return "missing", ""
    _, br = git(["rev-parse", "--abbrev-ref", "HEAD"], p)
    _, dirty = git(["status", "--porcelain"], p)
    _, ab = git(["rev-list", "--left-right", "--count", f"HEAD...@{{u}}"], p)
    ahead, behind = (ab.split() + ["?", "?"])[:2] if ab.strip() and "fatal" not in ab else ("?", "?")
    return br.strip(), f"{'dirty ' if dirty.strip() else 'clean '}ahead {ahead} behind {behind}"


def cmd_status(repos):
    for r in repos:
        br, st = info(r)
        flag = "" if br in ("missing", r["branch"]) else f"  (expected {r['branch']})"
        print(f"{r['name']:28}{r.get('role', ''):10}{br:16}{st}{flag}")


def cmd_sync(repos, names, from_local):
    for r in repos:
        if names and r["name"] not in names or r.get("self"): continue
        p = r["path"]
        if not (p / ".git").exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            src = r.get("local") if from_local and r.get("local") and Path(r["local"]).expanduser().is_dir() else r["url"]
            rc, out = git(["clone", str(Path(src).expanduser()) if src != r["url"] else src, str(p)], p.parent)
            if rc == 0 and src != r["url"]: git(["remote", "set-url", "origin", r["url"]], p)
            if rc == 0: git(["checkout", r["branch"]], p)
            print(f"clone {r['name']}: {'ok' if rc == 0 else 'FAILED ' + out.strip()[-200:]}")
        else:
            _, dirty = git(["status", "--porcelain"], p)
            if dirty.strip(): print(f"skip  {r['name']}: local changes"); continue
            rc, out = git(["pull", "--ff-only"], p)
            print(f"pull  {r['name']}: {'ok' if rc == 0 else 'FAILED ' + out.strip()[-200:]}")


def cmd_graph(repos):
    names = {r["name"] for r in repos}
    for r in repos:
        deps = ", ".join(d if d in names else f"{d}?" for d in r["depends_on"]) or "-"
        print(f"{r['name']} [{r.get('role', '')}] -> {deps}")


def cmd_contracts(root, repos, changed):
    snap = root / DIRNAME / "cache" / "contracts.json"
    old = json.loads(snap.read_text()) if snap.is_file() else {}
    new = {}
    for r in repos:
        for c in r["contracts"]:
            f = r["path"] / c
            new[f"{r['name']}:{c}"] = hashlib.sha1(f.read_bytes()).hexdigest()[:12] if f.is_file() else "missing"
    for k, v in new.items():
        mark = "" if old.get(k) in (None, v) else "  CHANGED"
        if not changed or mark or k not in old: print(f"{v}  {k}{mark if old else ''}")
    snap.parent.mkdir(parents=True, exist_ok=True); snap.write_text(json.dumps(new, indent=1))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["status", "sync", "graph", "where", "contracts"])
    ap.add_argument("names", nargs="*"); ap.add_argument("--root"); ap.add_argument("--from-local", action="store_true")
    ap.add_argument("--changed", action="store_true")
    a = ap.parse_args(); root = find_root(a.root); repos = load(root)
    if a.cmd == "status": cmd_status(repos)
    elif a.cmd == "sync": cmd_sync(repos, a.names, a.from_local)
    elif a.cmd == "graph": cmd_graph(repos)
    elif a.cmd == "contracts": cmd_contracts(root, repos, a.changed)
    elif a.cmd == "where":
        for r in repos:
            if r["name"] in a.names: print(r["path"])


if __name__ == "__main__":
    sys.exit(main())
