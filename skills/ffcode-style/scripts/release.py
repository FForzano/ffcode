"""Cross-repo release view from .ffcode/workspace.toml: what is in `from_ref` but not yet in `to_ref`, per repo.
  release.py [--root DIR] [--from develop] [--to main]
Per repo (self + clones): commit subjects, added migrations, changed contract files, and the dependency order to deploy in."""
from __future__ import annotations

import argparse

from common import find_root, git
from workspace import load


def order(repos):
    done, out = set(), []
    names = {r["name"] for r in repos}
    while len(out) < len(repos):
        prog = False
        for r in repos:
            if r["name"] not in done and all(d in done or d not in names for d in r["depends_on"]):
                out.append(r["name"]); done.add(r["name"]); prog = True
        if not prog: out += [r["name"] for r in repos if r["name"] not in done]; break
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--root"); ap.add_argument("--from", dest="frm"); ap.add_argument("--to", default=None)
    a = ap.parse_args(); root = find_root(a.root); repos = load(root)
    for r in repos:
        p = r["path"]
        if not (p / ".git").exists(): print(f"== {r['name']}: not cloned"); continue
        frm = a.frm or r["branch"]; to = a.to or ("main" if frm != "main" else "master")
        refs = [x for x in (to, f"origin/{to}", "master", "origin/master") if git(["rev-parse", "--verify", "-q", x], p)[0] == 0]
        if not refs: print(f"== {r['name']}: no target ref"); continue
        to = refs[0]
        _, log = git(["log", "--no-merges", "--format=%h %s", f"{to}..{frm}"], p)
        _, files = git(["diff", "--name-status", f"{to}...{frm}"], p)
        mig = [l for l in files.splitlines() if l.startswith("A") and "migration" in l.lower()]
        con = [l for l in files.splitlines() if any(l.endswith(c) for c in r["contracts"])]
        n = len(log.splitlines())
        print(f"== {r['name']} [{r.get('role', '')}] {frm} vs {to}: {n} commit(s)")
        for l in log.splitlines()[:15]: print("   " + l[:110])
        if n > 15: print(f"   ... +{n - 15}")
        for l in mig: print("   MIGRATION " + l.split("\t", 1)[1])
        for l in con: print("   CONTRACT  " + l.split("\t", 1)[1])
    print("deploy order (dependencies first):", " -> ".join(order(repos)))


if __name__ == "__main__":
    main()
