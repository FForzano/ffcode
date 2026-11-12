"""Inventory of the visual values actually used (colours, font sizes/families, radii, shadows, spacing, z-index) and of the
custom properties defined, to find what to turn into tokens and where the system drifts.
  uitokens.py [--root DIR] [--top N]"""
from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict

from common import find_root, is_text, tracked_files
from uilint import HEX, RGB, UI, rgb_of


def norm_color(v):
    c = rgb_of(v)
    return "#%02x%02x%02x" % c if c else None


def scan(root):
    """-> (files, cnt{kind: Counter}, where{kind: {value: {files}}}, props{--name: (value, file)})"""
    files = [f for f in tracked_files(root) if f.suffix in UI and is_text(root / f) and not {"node_modules", "build", "dist"} & set(f.parts) and ".min." not in f.name]
    cnt = defaultdict(Counter); where = defaultdict(lambda: defaultdict(set)); props = {}
    for f in files:
        t = (root / f).read_text(errors="replace")
        for m in re.finditer(r"(--[\w-]+)\s*:\s*([^;}\n]+)", t): props.setdefault(m.group(1), (m.group(2).strip(), str(f)))
        for l in t.splitlines():
            if l.lstrip().startswith(("//", "/*", "*")): continue
            for x in HEX.findall(l) + [m.group(0) for m in RGB.finditer(l)]:
                c = norm_color(x)
                if c: cnt["color"][c] += 1; where["color"][c].add(str(f))
            for k, rx in (("font-size", r"font-size\s*:\s*([^;}\n]+)"), ("radius", r"border-radius\s*:\s*([^;}\n]+)"), ("shadow", r"box-shadow\s*:\s*([^;}\n]+)"),
                          ("font-family", r"font-family\s*:\s*([^;}\n]+)"), ("z-index", r"z-index\s*:\s*(-?\d+)"), ("gap", r"\bgap\s*:\s*([^;}\n]+)")):
                m = re.search(rx, l)
                if m and "var(" not in m.group(1): cnt[k][m.group(1).strip()[:50]] += 1; where[k][m.group(1).strip()[:50]].add(str(f))
            for m in re.finditer(r"(?:margin|padding)(?:-\w+)?\s*:\s*([^;}\n]+)", l):
                for v in re.findall(r"-?\d+(?:\.\d+)?(?:px|rem)", m.group(1)): cnt["spacing"][v] += 1
    return files, cnt, where, props


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--root"); ap.add_argument("--top", type=int, default=12)
    a = ap.parse_args(); root = find_root(a.root)
    files, cnt, where, props = scan(root)
    print(f"files scanned: {len(files)}; custom properties defined: {len(props)}")
    byval = defaultdict(list)
    for k, (v, f) in props.items():
        c = norm_color(v)
        if c: byval[c].append(k)
    for k in ("color", "font-size", "font-family", "radius", "shadow", "spacing", "z-index", "gap"):
        if not cnt[k]: continue
        print(f"\n## {k}: {len(cnt[k])} distinct, {sum(cnt[k].values())} uses")
        for v, n in cnt[k].most_common(a.top):
            extra = f"  = {', '.join(byval[v])}" if k == "color" and v in byval else ""
            print(f"  {n:4}x {v}  ({len(where[k][v])} file(s)){extra}")
    cols = list(cnt["color"])
    near = [(x, y) for i, x in enumerate(cols) for y in cols[i + 1:] if sum(abs(p - q) for p, q in zip(rgb_of(x), rgb_of(y))) <= 24]
    if near: print("\n## near-duplicate colours (distance <= 24): " + "; ".join(f"{x}~{y}" for x, y in near[:10]))
    off = [v for v in cnt["spacing"] if v.endswith("px") and re.fullmatch(r"-?\d+", v[:-2]) and int(v[:-2]) % 4 and abs(int(v[:-2])) > 1]
    if off: print("\n## spacing off a 4px grid: " + ", ".join(sorted(off, key=lambda s: -cnt["spacing"][s])[:12]))
    lit = [(c, n) for c, n in cnt["color"].most_common() if c in byval and n]
    if lit: print("\n## literals that already equal a token (replace): " + "; ".join(f"{c}={byval[c][0]} ({n}x)" for c, n in lit[:10]))


if __name__ == "__main__":
    main()
