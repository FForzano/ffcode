"""Facts for the texts Claude writes, from the git diff, so only the reasoning is left to write (templates/report-*.md).
  ff pr [--base B] [--check]            PR description skeleton (Why left as a marker)
  ff report review|summary [--base B] [--check]
Scope: changes since the merge-base with [check] base (default main), uncommitted ones included.
--check also runs `ff check --changed --json` and reports the result under 'How tested'/'Verified'."""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

from common import DIRNAME, find_root, git, load_config, run

TPL = Path(__file__).resolve().parent.parent / "templates"
HERE = Path(__file__).resolve().parent
TEST = re.compile(r"(^|/)(tests?|spec|__tests__)/|(_test|\.test|\.spec|Test)\.\w+$|(^|/)test_[^/]*$")


def area(p: str) -> str:
    parts = p.split("/")
    return parts[0] if len(parts) == 1 or parts[0] not in ("src", "app", "lib", "packages") else "/".join(parts[:2])


def contract_globs(root: Path) -> list[str]:
    f = root / DIRNAME / "workspace.toml"
    if not f.is_file(): return []
    return [g for r in tomllib.loads(f.read_text()).get("repo", []) if r.get("self") for g in r.get("contracts", [])]


def collect(root: Path, base: str):
    rc, mb = git(["merge-base", base, "HEAD"], root)
    ref = mb.strip() if rc == 0 and mb.strip() else "HEAD"
    _, out = git(["diff", "--numstat", ref], root)
    files = []
    for l in out.splitlines():
        a, d, p = l.split("\t", 2)
        files.append((p, int(a) if a.isdigit() else 0, int(d) if d.isdigit() else 0))
    _, new = git(["ls-files", "--others", "--exclude-standard"], root)
    files += [(p, 0, 0) for p in new.splitlines() if p and not p.startswith(DIRNAME + "/")]
    _, log = git(["log", "--format=%h %s", f"{ref}..HEAD"], root)
    return ref, files, [l for l in log.splitlines() if l]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("kind", nargs="?", default="pr", choices=["pr", "review", "summary"])
    ap.add_argument("--base"); ap.add_argument("--check", action="store_true"); ap.add_argument("--root")
    a = ap.parse_args()
    root = find_root(a.root); cfg = load_config(root); base = a.base or cfg["check"].get("base", "main")
    ref, files, commits = collect(root, base)
    if not files: print("no changes against " + base); return 0
    by = defaultdict(list)
    for p, ad, de in files: by[area(p)].append((p, ad, de))
    areas = "\n".join(f"- `{k}`: {len(v)} file(s), +{sum(x[1] for x in v)} -{sum(x[2] for x in v)}" for k, v in sorted(by.items(), key=lambda kv: -sum(x[1] + x[2] for x in kv[1])))
    tests = [p for p, _, _ in files if TEST.search(p)]
    mig = [p for p, _, _ in files if re.search(r"migrat|schema\.sql|\.sql$", p, re.I)]
    globs = contract_globs(root)
    con = [p for p, _, _ in files if any(fnmatch.fnmatch(p, g) for g in globs)]
    _, lj = run([sys.executable, str(HERE / "lint.py"), "--root", str(root), "--changed", "--json"])
    try: rules = json.loads(lj)["rules"]; lint = ", ".join(f"{k} {len(v)}" for k, v in rules.items()) or "clean"
    except (ValueError, KeyError): lint = "not run"
    tested = f"tests touched: {', '.join(tests[:6]) or 'none'}"
    if a.check:
        _, cj = run([sys.executable, str(HERE / "check.py"), "--root", str(root), "--changed", "--json"])
        try:
            c = json.loads(cj); tested += "\nff check: " + c["result"] + " (" + ", ".join(f"{s['step']} {'ok' if s['ok'] else 'FAIL'}" for s in c["steps"]) + ")"
        except ValueError: tested += "\nff check: could not run"
    else: tested += "\nff check: not run here (add --check)"
    hs = root / DIRNAME / "cache" / "hotspots.json"
    hot = {r["file"] for r in json.loads(hs.read_text())[:30]} if hs.is_file() else set()
    top = sorted(files, key=lambda f: -(f[1] + f[2]))[:5]
    vals = {"areas": areas, "tested": tested, "scope": f"{base}...HEAD" + (f" ({len(commits)} commit(s))" if commits else " (uncommitted)"),
            "nfiles": len(files), "add": sum(f[1] for f in files), "del": sum(f[2] for f in files), "tests": "yes" if tests else "NO",
            "lint": lint, "hotspots": ", ".join(f"{p} (+{x}/-{y}{', hotspot' if p in hot else ''})" for p, x, y in top),
            "contracts": ", ".join(con) or "none (no contract file touched)" if globs else "none declared in workspace.toml",
            "migrations": ", ".join(mig) or "none"}
    text = (TPL / f"report-{a.kind}.md").read_text()
    for k, v in vals.items(): text = text.replace("{{" + k + "}}", str(v))
    print(text.rstrip())
    return 0
