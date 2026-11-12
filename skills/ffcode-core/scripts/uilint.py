"""Mechanical UI checks for HTML/CSS/JSX/TSX/Vue/Svelte: accessibility, tokens, motion, i18n. Findings: path:line: ID message.
  uilint.py [--root DIR] [--changed|--staged] [--base REF] [--rules a,b] [--list] [--summary]
Heuristics, not a browser: a finding is a lead to read, not a verdict. Exit 1 if any finding."""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

from common import find_root, is_text, load_config, load_contract, tracked_files

RULES = {
    "IMGALT": "<img> without alt", "FIELDLABEL": "input/select/textarea without id, aria-label or aria-labelledby",
    "CLICKDIV": "click handler on div/span without role and keyboard handler (use <button>/<a>)", "TABINDEX": "tabindex > 0",
    "OUTLINE": "outline removed without a visible focus replacement", "CONTRAST": "text/background contrast below 4.5:1 in one rule (literal or token colours)",
    "TINYFONT": "font-size below 12px", "HARDCOLOR": "literal colour outside the token files (use a variable/token)",
    "IMPORTANT": "!important", "ZINDEX": "z-index above 100 (use a named scale)", "TRANSALL": "transition: all (name the properties)",
    "VIEWPORT": "viewport blocks zoom (user-scalable=no / maximum-scale=1)", "HTMLLANG": "<html> without lang",
    "GRADTEXT": "gradient text (background-clip: text)", "BORDERACCENT": "coloured side border thicker than 1px (accent stripe)",
    "MOTION": "animations in the project but no prefers-reduced-motion anywhere", "I18N": "hard-coded visible text in a project that uses i18n",
    "OFFCOLOR": "colour not in the design contract", "OFFSIZE": "font-size not in the type scale of the contract",
    "OFFSPACE": "spacing not in the contract scale (or a multiple of its base)", "OFFRADIUS": "radius not in the contract scale",
    "INLINESTYLE": "many inline styles in one file (move to the style system)",
}
UI = {".html", ".css", ".scss", ".sass", ".less", ".jsx", ".tsx", ".vue", ".svelte", ".js", ".ts"}
MARKUP = {".html", ".jsx", ".tsx", ".vue", ".svelte"}
STYLE = {".css", ".scss", ".sass", ".less", ".vue", ".svelte", ".html"}
HEX = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
RGB = re.compile(r"rgba?\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)")
TOKENFILE = re.compile(r"(token|theme|variable|palette|colou?rs?|design[-_]?system|:root)", re.I)


def rgb_of(v: str):
    v = v.strip()
    m = HEX.fullmatch(v)
    if m:
        h = v[1:]
        h = "".join(c * 2 for c in h) if len(h) == 3 else h[:6]
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    m = RGB.match(v)
    return tuple(int(x) for x in m.groups()) if m else None


def lum(c):
    f = lambda x: (x / 255 / 12.92) if x / 255 <= 0.03928 else (((x / 255) + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def css_vars(texts):
    vs = {}
    for t in texts:
        for m in re.finditer(r"(--[\w-]+)\s*:\s*([^;}\n]+)", t): vs.setdefault(m.group(1), m.group(2).strip())
    return vs


def resolve(v, vs, depth=0):
    v = v.strip().rstrip(";")
    m = re.match(r"var\((--[\w-]+)(?:\s*,\s*([^)]+))?\)", v)
    if m and depth < 4: return resolve(vs.get(m.group(1), m.group(2) or ""), vs, depth + 1)
    return v


def lines_of(text):
    return text.splitlines()


def check_markup(f, lines, i18n, out):
    for n, l in enumerate(lines, 1):
        if re.search(r"<img\b", l) and not re.search(r"\balt\s*=|\{\.\.\.", l) and ">" in l: out.append((n, "IMGALT", l.strip()[:70]))
        if re.search(r"<(input|select|textarea)\b", l) and not re.search(r"type=[\"'](hidden|submit|button|reset)|\bid\s*=|aria-label|\{\.\.\.|aria-labelledby", l) and ">" in l:
            out.append((n, "FIELDLABEL", l.strip()[:70]))
        if re.search(r"<(div|span|li|td)\b[^>]*\b(onClick|@click|on:click)\b", l) and not re.search(r"role\s*=|onKey|@key|on:key", l):
            out.append((n, "CLICKDIV", l.strip()[:70]))
        if re.search(r"tabindex\s*=\s*[\"'{]?[1-9]", l, re.I): out.append((n, "TABINDEX", l.strip()[:70]))
        if re.search(r"<html\b(?![^>]*\blang\b)", l, re.I): out.append((n, "HTMLLANG", l.strip()[:70]))
        if re.search(r"user-scalable\s*=\s*no|maximum-scale\s*=\s*1(\.0)?\b", l): out.append((n, "VIEWPORT", l.strip()[:70]))
        if i18n and f.suffix in (".tsx", ".jsx", ".vue") and not re.search(r"^\s*(//|\*|import)", l):
            m = re.search(r">\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'’ ,.!?:-]{8,}[A-Za-zÀ-ÿ.!?])\s*<", l)
            if m and " " in m.group(1): out.append((n, "I18N", m.group(1)[:60]))
    inl = sum(1 for l in lines if re.search(r"style=\{\{|style=\"[^\"]{12,}", l))
    if inl >= 6: out.append((1, "INLINESTYLE", f"{inl} inline styles"))


def check_style(f, text, vs, token_file, out):
    base = text[:0]
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", text):
        body, start = m.group(2), text[:m.start(2)].count("\n") + 1
        decl = {k.strip().lower(): v.strip() for k, v in re.findall(r"([\w-]+)\s*:\s*([^;]+)", body)}
        col = decl.get("color"); bg = decl.get("background-color") or (decl.get("background") if decl.get("background") and "gradient" not in decl["background"] else None)
        if col and bg:
            a, b = rgb_of(resolve(col, vs)), rgb_of(resolve(bg.split()[0] if bg else "", vs))
            if a and b and ratio(a, b) < 4.5: out.append((start, "CONTRAST", f"{ratio(a, b):.1f}:1 ({col} on {bg})"))
        if re.match(r"(none|0)\b", decl.get("outline", "")) or re.match(r"(none|0)\b", decl.get("outline-style", "")):
            if not any(k in decl for k in ("box-shadow", "border", "border-color", "outline-offset")): out.append((start, "OUTLINE", m.group(1).strip()[:50]))
        if decl.get("-webkit-background-clip") == "text" or decl.get("background-clip") == "text": out.append((start, "GRADTEXT", m.group(1).strip()[:50]))
        for k in ("border-left", "border-right"):
            mm = re.match(r"(\d+)px", decl.get(k, ""))
            if mm and int(mm.group(1)) > 1: out.append((start, "BORDERACCENT", f"{k}: {decl[k]}"))
    for n, l in enumerate(lines_of(text), 1):
        if "!important" in l: out.append((n, "IMPORTANT", l.strip()[:60]))
        m = re.search(r"z-index\s*:\s*(\d+)", l)
        if m and int(m.group(1)) > 100: out.append((n, "ZINDEX", m.group(1)))
        if re.search(r"transition\s*:\s*all\b", l): out.append((n, "TRANSALL", l.strip()[:60]))
        m = re.search(r"font-size\s*:\s*(\d+(?:\.\d+)?)px", l)
        if m and float(m.group(1)) < 12: out.append((n, "TINYFONT", f"{m.group(1)}px"))
        if not token_file and not l.lstrip().startswith(("//", "/*", "*", "--")) and (HEX.search(l) or RGB.search(l)) and ":" in l and "var(" not in l:
            out.append((n, "HARDCOLOR", l.strip()[:60]))


def nearest(v, options):
    return min(options, key=lambda o: abs(o - v)) if options else None


def check_contract(f, text, contract, out):
    """Values in styles, inline styles and Tailwind arbitrary values that the design contract does not know. Only changed files in practice."""
    cols = {c.lower() for th in contract.get("color", {}).values() for c in (th.values() if isinstance(th, dict) else [th]) if isinstance(c, str)}
    cols = {"#%02x%02x%02x" % rgb_of(c) for c in cols if rgb_of(c)} | {"#000000", "#ffffff"}
    sizes = {float(x) for x in contract.get("type", {}).get("scale", [])}
    space = {float(x) for x in contract.get("space", {}).get("scale", [])}; base = contract.get("space", {}).get("base", 4)
    rad = {float(x) for x in contract.get("radius", {}).get("scale", [])} | {9999.0}
    pxv = lambda x: float(x[:-2]) if x.endswith("px") else float(x[:-3]) * 16 if x.endswith("rem") else None
    for n, l in enumerate(text.splitlines(), 1):
        if l.lstrip().startswith(("//", "/*", "*")) or "var(" in l and not re.search(r"#[0-9a-fA-F]{3,8}\b", l): continue
        for m in list(HEX.finditer(l)) + list(RGB.finditer(l)):
            c = rgb_of(m.group(0))
            if c and "#%02x%02x%02x" % c not in cols and cols:
                near = min(cols, key=lambda k: sum(abs(p - q) for p, q in zip(rgb_of(k), c)))
                out.append((n, "OFFCOLOR", f"{m.group(0)} (nearest token {near})"))
        for m in re.finditer(r"font-?[sS]ize\s*[:=]\s*[\"'{]?\s*(-?\d+(?:\.\d+)?(?:px|rem))|text-\[(\d+(?:\.\d+)?(?:px|rem))\]", l):
            v = pxv(m.group(1) or m.group(2))
            if v is not None and sizes and v not in sizes: out.append((n, "OFFSIZE", f"{v:g}px (nearest {nearest(v, sizes):g})"))
        for m in re.finditer(r"(?:margin|padding|gap)[\w-]*\s*[:=]\s*[\"'{]?\s*([^;\"'}\n]+)|\b(?:[mp][trblxy]?|gap)-\[(\d+(?:\.\d+)?px)\]", l):
            for tok in re.findall(r"-?\d+(?:\.\d+)?(?:px|rem)", m.group(1) or m.group(2)):
                v = abs(pxv(tok))
                if space and v not in space and (not base or v % base) and v > 1: out.append((n, "OFFSPACE", f"{v:g}px (nearest {nearest(v, space):g})"))
        for m in re.finditer(r"border-?[rR]adius\s*[:=]\s*[\"'{]?\s*(\d+(?:\.\d+)?(?:px|rem))|rounded-\[(\d+(?:\.\d+)?px)\]", l):
            v = pxv(m.group(1) or m.group(2))
            if v is not None and rad and v not in rad: out.append((n, "OFFRADIUS", f"{v:g}px (nearest {nearest(v, rad):g})"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root"); ap.add_argument("--changed", action="store_true"); ap.add_argument("--staged", action="store_true")
    ap.add_argument("--base"); ap.add_argument("--rules"); ap.add_argument("--list", action="store_true"); ap.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    if a.list:
        for k, v in RULES.items(): print(f"{k:13}{v}")
        return 0
    root = find_root(a.root); cfg = load_config(root); active = set(a.rules.split(",")) if a.rules else set(RULES)
    allf = [f for f in tracked_files(root) if f.suffix in UI and is_text(root / f) and "node_modules" not in f.parts and "build" not in f.parts and "dist" not in f.parts and ".min." not in f.name]
    scope = set(tracked_files(root, a.changed, a.staged, a.base or (cfg["check"].get("base") if a.changed else None))) if (a.changed or a.staged) else set(allf)
    texts = {f: (root / f).read_text(errors="replace") for f in allf}
    vs = css_vars(t for f, t in texts.items() if f.suffix in STYLE or ":root" in t)
    pkg = (root / "package.json").read_text() if (root / "package.json").is_file() else ""
    i18n = bool(re.search(r"i18next|react-intl|vue-i18n|formatjs|lingui", pkg))
    motion_used = any(re.search(r"@keyframes|animation\s*:|transition\s*:|framer-motion", t) for t in texts.values()) or "framer-motion" in pkg
    reduced = any("prefers-reduced-motion" in t or "useReducedMotion" in t or "reducedMotion" in t for t in texts.values())
    contract = load_contract(root)
    tokenfile_of = lambda f, t: bool(TOKENFILE.search(str(f)) or re.search(r"^\s*:root\b", t, re.M))
    findings = []
    for f in sorted(scope):
        if f not in texts: continue
        t, out = texts[f], []
        if f.suffix in MARKUP: check_markup(f, lines_of(t), i18n, out)
        if f.suffix in STYLE: check_style(f, t, vs, bool(TOKENFILE.search(str(f)) or re.search(r"^\s*:root\b", t, re.M)), out)
        if contract and not tokenfile_of(f, t): check_contract(f, t, contract, out)
        findings += [(f, n, r, m) for n, r, m in out if r in active]
    if motion_used and not reduced and "MOTION" in active and not (a.changed or a.staged): findings.append((Path("(project)"), 0, "MOTION", "no prefers-reduced-motion / useReducedMotion found"))
    by = defaultdict(list)
    for f, n, r, m in findings: by[r].append((f, n, m))
    for r in RULES:
        if r in by:
            print(f"{r} ({len(by[r])}) {RULES[r]}")
            if a.summary: continue
            for f, n, m in by[r][:8]: print(f"  {f}:{n}: {m}")
            if len(by[r]) > 8: print(f"  ... +{len(by[r]) - 8}")
    strict = bool((contract or {}).get("ui", {}).get("strict"))
    hard = [x for x in findings if strict or not x[2].startswith("OFF")]
    adv = len(findings) - len(hard)
    print(f"uilint: {len(findings)} finding(s) in {len(scope)} file(s)" + (f" ({adv} OFF* advisory: [ui] strict = false)" if adv else ""))
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
