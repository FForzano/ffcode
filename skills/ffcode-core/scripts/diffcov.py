"""Coverage of the lines added in the diff (diff coverage). Reads Cobertura XML, Clover XML or lcov.
  diffcov.py [--root DIR] [--base REF] [--report FILE] [--min PCT] [--run]
--run executes [commands] coverage first. Report path: --report or [coverage] report in config.toml.
Reports added executable lines that no test ran, grouped by function; exit 1 below --min (default [coverage] min, 0)."""
from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from common import find_root, git, lang_of, load_config, run
from mapper import symbols


def parse_report(path: Path, root: Path) -> dict[str, dict[int, int]]:
    """-> {relative file: {line: hits}} for executable lines."""
    text = path.read_text(errors="replace")
    cov: dict[str, dict[int, int]] = defaultdict(dict)

    def rel(p: str) -> str:
        pp = Path(p)
        try: return str(pp.resolve().relative_to(root)) if pp.is_absolute() else p.lstrip("./")
        except ValueError:
            m = re.search(r"/(?:app|var/www/html|srv/app)/(.*)", p)
            return m.group(1) if m else p
    if text.lstrip().startswith("SF:") or "\nSF:" in text[:200] or text.startswith("TN:"):
        cur = None
        for l in text.splitlines():
            if l.startswith("SF:"): cur = rel(l[3:].strip())
            elif l.startswith("DA:") and cur:
                n, h = l[3:].split(",")[:2]; cov[cur][int(n)] = int(h)
        return cov
    tree = ET.fromstring(text)
    if tree.tag == "coverage" and tree.find(".//project") is not None:            # Clover
        for f in tree.iter("file"):
            name = rel(f.get("name", ""))
            for ln in f.iter("line"):
                if ln.get("type") in ("stmt", "cond", "method"): cov[name][int(ln.get("num"))] = int(ln.get("count") or 0)
        return cov
    srcs = [s.text or "" for s in tree.iter("source")]                              # Cobertura
    for c in tree.iter("class"):
        fn = c.get("filename", "")
        name = rel(fn)
        for s in srcs:
            if not (root / name).is_file() and (Path(s) / fn).is_file(): name = rel(str(Path(s) / fn))
        for ln in c.iter("line"):
            cov[name][int(ln.get("number"))] = int(ln.get("hits") or 0)
    return cov


def added_lines(root: Path, base: str) -> dict[str, set[int]]:
    rc, out = git(["diff", "-U0", "--diff-filter=ACMR", base], root)
    res: dict[str, set[int]] = defaultdict(set); cur = None
    for l in out.splitlines():
        if l.startswith("+++ b/"): cur = l[6:]
        elif l.startswith("@@") and cur:
            m = re.search(r"\+(\d+)(?:,(\d+))?", l)
            s, n = int(m.group(1)), int(m.group(2) or 1)
            res[cur].update(range(s, s + n))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root"); ap.add_argument("--base"); ap.add_argument("--report"); ap.add_argument("--min", type=float)
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args(); root = find_root(a.root); cfg = load_config(root)
    cc = cfg.get("coverage", {}); base = a.base or cfg["check"].get("base", "main")
    if a.run:
        cmd = cfg["commands"].get("coverage")
        if not cmd: print("no [commands] coverage configured"); return 2
        rc, out = run(cmd, cwd=root)
        if rc != 0: print("coverage command failed:\n" + "\n".join(out.splitlines()[-15:])); return 2
    rep = Path(a.report or cc.get("report", "")) if (a.report or cc.get("report")) else None
    if not rep: print("no report: set [coverage] report in config.toml or pass --report"); return 2
    rep = rep if rep.is_absolute() else root / rep
    if not rep.is_file(): print(f"report not found: {rep} (run the coverage command, or use --run)"); return 2
    cov = parse_report(rep, root); added = added_lines(root, base)
    tot = hit = 0; miss_by: dict[str, list[int]] = {}
    ignore = re.compile(cc.get("ignore", r"(^|/)(tests?|spec|migrations?)/|\.test\.|\.spec\.|Test\.php$"))
    for f, lines in sorted(added.items()):
        if ignore.search(f) or f not in cov: continue
        ex = {n for n in lines if n in cov[f]}
        tot += len(ex); hit += sum(1 for n in ex if cov[f][n] > 0)
        m = sorted(n for n in ex if cov[f][n] == 0)
        if m: miss_by[f] = m
    for f, miss in miss_by.items():
        syms = symbols(root / f, lang_of(f)) if lang_of(f) else []
        grp: dict[str, list[int]] = defaultdict(list)
        for n in miss:
            owner = next((nm for i, _, nm in reversed(syms) if i <= n), "(top level)"); grp[owner].append(n)
        print(f"{f}")
        for o, ns in grp.items(): print(f"  {o}: {len(ns)} line(s) not run: {_ranges(ns)}")
    nocov = [f for f in added if f not in cov and not ignore.search(f) and lang_of(f) in ("python", "php", "typescript", "javascript")]
    if nocov: print(f"not in the report (never loaded by a test?): {', '.join(nocov[:8])}")
    pct = 100.0 if not tot else 100.0 * hit / tot
    print(f"diff coverage: {pct:.0f}% ({hit}/{tot} added executable lines) vs {base}")
    mn = a.min if a.min is not None else float(cc.get("min", 0))
    return 1 if pct < mn else 0


def _ranges(ns):
    out, s, p = [], ns[0], ns[0]
    for n in ns[1:] + [None]:
        if n is not None and n == p + 1: p = n; continue
        out.append(f"{s}" if s == p else f"{s}-{p}")
        if n is not None: s = p = n
    return ",".join(out)


if __name__ == "__main__":
    sys.exit(main())
