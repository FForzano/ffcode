"""Design contract tooling. The contract is .ffcode/design.toml (roles and scales); everything else is derived from it.
  ui.py context                      ~40-line digest: product, tokens, conventions, components, lint counts (read this, not the files)
  ui.py init [--stdout] [--force]    draft design.toml from what the code really uses (inferred, to be corrected)
  ui.py palette [--fix]              contrast matrix of the contract per theme; --fix proposes the nearest passing colour
  ui.py sync [--stdout]              generate tokens (CSS custom properties + optional JSON/TS) from the contract
  ui.py components [NAME] [--top N]  inventory of components: uses, props, file (reuse before writing)
  ui.py new NAME [--dir D] [--dry-run]  scaffold a component in the project's detected convention"""
from __future__ import annotations

import argparse
import colorsys
import json
import re
import sys
from collections import Counter
from pathlib import Path

from common import DIRNAME, die, find_root, is_text, load_config, load_contract, run, tracked_files
from uilint import UI, ratio, rgb_of
from uitokens import norm_color, scan

PAIRS = [("text", "surface", 4.5), ("text", "surface-alt", 4.5), ("muted", "surface", 4.5), ("brand-contrast", "brand", 4.5),
         ("brand", "surface", 3.0), ("focus", "surface", 3.0), ("danger", "surface", 4.5)]
SCALE_KEYS = ("type", "space", "radius", "z")


def hexs(c): return "#%02x%02x%02x" % tuple(c)


def px_of(v: str):
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)(px|rem|em)?", v.strip())
    return None if not m else float(m.group(1)) * (16 if m.group(2) in ("rem", "em") else 1)


def themes(contract):
    col = contract.get("color", {})
    flat = {k: v for k, v in col.items() if isinstance(v, str)}
    return {t: {**flat, **v} for t, v in col.items() if isinstance(v, dict)} or {"light": flat}


# ---------------------------------------------------------------- init
def frontmatter(root):
    """Minimal reader of the YAML frontmatter of DESIGN.md: colors/rounded/spacing maps, typography sizes/families."""
    for n in ("DESIGN.md", f"{DIRNAME}/design.md"):
        p = root / n
        if p.is_file() and p.read_text().startswith("---"):
            body = p.read_text().split("---")[1]; break
    else:
        return {}
    fm, top = {}, None
    for l in body.splitlines():
        if not l.strip() or l.lstrip().startswith("#"): continue
        if not l.startswith(" "):
            top = l.split(":")[0].strip(); fm[top] = {} if l.rstrip().endswith(":") else l.split(":", 1)[1].strip(); continue
        m = re.match(r"\s+[\"']?([\w.-]+)[\"']?\s*:\s*[\"']?([^\"']+?)[\"']?\s*$", l)
        if m and isinstance(fm.get(top), dict):
            if top == "typography" and m.group(1) in ("fontSize", "fontFamily"): fm[top].setdefault(m.group(1), []).append(m.group(2))
            elif top != "typography": fm[top][m.group(1)] = m.group(2)
    return fm


def draft(root):
    files, cnt, where, props = scan(root)
    out = [f"# Design contract for {root.name}: INFERRED from the code on first run. Correct it, then it is the source of truth.",
           "# Scripts read this: `ffcode ui sync|palette|components`, `ffcode uilint` (OFFTOKEN), `ffcode ui context`.", "",
           '[meta]\nmode = "operate"   # persuade | operate | read | experience\nmood = []          # three adjectives\n']
    cols = [(c, n) for c, n in cnt["color"].most_common() if c not in ("#000000", "#ffffff") or n > 3]
    lum = lambda c: sum(rgb_of(c)) / 3
    sat = lambda c: max(rgb_of(c)) - min(rgb_of(c))
    brand = next((c for c, _ in cols if sat(c) > 60), None)
    neutral = [c for c, _ in cols if sat(c) <= 40]
    surface = max(neutral, key=lum) if neutral else "#ffffff"
    text = min(neutral, key=lum) if neutral else "#111111"
    pcol = {k: hexs(rgb_of(v)) for k, (v, _) in props.items() if rgb_of(v) and len(props) < 80}
    fm = frontmatter(root)
    fcol = {k: hexs(rgb_of(v)) for k, v in fm.get("colors", {}).items() if rgb_of(v)}
    out.append("[color.light]  # roles, not hues. Names with a * are guesses." + ("  From DESIGN.md frontmatter: rename to roles (surface, text, muted, border, brand, brand-contrast, focus, danger...) so `ui palette` can check pairs." if fcol else ""))
    if fcol:
        for k, v in fcol.items(): out.append(f'{k} = "{v}"')
    elif pcol:
        for k, v in list(pcol.items())[:30]: out.append(f'{k[2:]} = "{v}"')
    else:
        out += [f'surface = "{surface}"   # *', f'surface-alt = "{surface}"   # *', f'text = "{text}"   # *', f'muted = "{sorted(neutral, key=lum)[len(neutral)//2] if neutral else "#6b7280"}"   # *',
                f'border = "{sorted(neutral, key=lum)[-2] if len(neutral) > 1 else "#e5e7eb"}"   # *', f'brand = "{brand or "#2563eb"}"   # *', 'brand-contrast = "#ffffff"', 'focus = "' + (brand or "#2563eb") + '"',
                'danger = "#b91c1c"', 'success = "#15803d"', 'warning = "#b45309"']
        rest = [c for c, _ in cols if c not in (surface, text, brand)][:8]
        if rest: out.append("# also used in the code, assign a role or remove: " + ", ".join(rest))
    out.append("\n# [color.dark]  # same role names; derive the values, check with `ffcode ui palette`\n")
    fam = [k for k, _ in cnt["font-family"].most_common(2) if "${" not in k and "'+" not in k and "var(" not in k]
    if fm.get("typography", {}).get("fontFamily"): fam = [fm["typography"]["fontFamily"][0]]
    out.append(f'[font]\nsans = "{fam[0] if fam else "system-ui, sans-serif"}"\nmono = "ui-monospace, monospace"\n')
    def scale(kind, conv=px_of, minuse=1, cap=10):
        vals = Counter()
        for v, n in cnt[kind].items():
            for tok in re.findall(r"-?\d+(?:\.\d+)?(?:px|rem|em)?", v if kind != "spacing" else v):
                p = conv(tok)
                if p is not None: vals[p] += n
        return sorted(p for p, n in vals.most_common(cap) if n >= minuse)
    fs = scale("font-size", cap=9); sp = scale("spacing", minuse=2, cap=10); ra = scale("radius", cap=5)
    if fm.get("typography", {}).get("fontSize"): fs = sorted({px_of(x) for x in fm["typography"]["fontSize"] if px_of(x) is not None})
    if fm.get("spacing"): sp = sorted({0.0, *[px_of(x) for x in fm["spacing"].values() if px_of(x) is not None]})
    if fm.get("rounded"): ra = sorted({px_of(x) for x in fm["rounded"].values() if px_of(x) is not None})
    fmt = lambda xs: "[" + ", ".join(str(int(x)) if x == int(x) else str(x) for x in xs) + "]"
    out.append(f"[type]   # px, used for font-size\nscale = {fmt(fs or [12, 14, 16, 20, 24, 32])}\n")
    out.append(f"[space]  # px, margin/padding/gap\nbase = 4\nscale = {fmt(sp or [0, 4, 8, 12, 16, 24, 32, 48])}\n")
    out.append(f"[radius]\nscale = {fmt(ra or [0, 4, 8])}\n")
    out.append('[shadow]\nsm = "0 1px 2px rgba(0,0,0,.08)"\nmd = "0 4px 12px rgba(0,0,0,.12)"\n')
    out.append('[motion]\nfast = "120ms"\nbase = "200ms"\nease = "cubic-bezier(.2,.8,.2,1)"\n')
    out.append('[z]\nscale = [0, 10, 100, 1000]\n')
    comp = [str(d) for d in ("src/components", "components", "app/components", "src/ui") if (root / d).is_dir()]
    out.append(f'[ui]\noutput = "src/styles/tokens.css"   # `ffcode ui sync` writes here\ncomponents = {json.dumps(comp)}\nstrict = false          # true: OFFTOKEN findings fail `check`\n')
    out.append('[rules]\n# one line each: what this product always / never does visually\nnotes = []\n')
    return "\n".join(out)


def cmd_init(a, root):
    p = root / DIRNAME / "design.toml"
    if p.exists() and not a.force and not a.stdout: die(f"{p} exists (use --force)", 1)
    text = draft(root)
    if a.stdout: print(text); return 0
    p.parent.mkdir(exist_ok=True); p.write_text(text); print(f"wrote {p.relative_to(root)} (inferred; review the * guesses)")
    return 0


# ---------------------------------------------------------------- palette
def fix_color(fg, bg, target):
    h, l, s = colorsys.rgb_to_hls(*(x / 255 for x in fg))
    dark_bg = sum(bg) < 382
    for step in range(0, 101):
        l2 = min(1, l + step / 100) if dark_bg else max(0, l - step / 100)
        c = tuple(round(x * 255) for x in colorsys.hls_to_rgb(h, l2, s))
        if ratio(c, bg) >= target: return hexs(c)
    return None


def cmd_palette(a, root):
    c = load_contract(root) or die("no .ffcode/design.toml (run: ffcode ui init)", 1)
    bad = 0
    for th, cols in themes(c).items():
        for fg, bg, need in PAIRS:
            if fg in cols and bg in cols:
                f, b = rgb_of(cols[fg]), rgb_of(cols[bg])
                if not (f and b): continue
                r = ratio(f, b)
                if r < need:
                    bad += 1; fx = f"  -> {fix_color(f, b, need)}" if a.fix else ""
                    print(f"FAIL [{th}] {fg} {cols[fg]} on {bg} {cols[bg]}: {r:.2f}:1 < {need}{fx}")
    print(f"palette: {bad} failing pair(s)"); return 1 if bad else 0


# ---------------------------------------------------------------- sync
def render_css(c):
    ts = themes(c); out = ["/* Generated by `ffcode ui sync` from .ffcode/design.toml. Do not edit. */"]
    def block(sel, cols): return [f"{sel} {{"] + [f"  --color-{k}: {v};" for k, v in cols.items()] + ["}"]
    out += block(":root", ts.get("light", next(iter(ts.values()))))
    out += ["", ":root {"]
    for k, v in c.get("font", {}).items(): out.append(f"  --font-{k}: {v};")
    for i, v in enumerate(c.get("type", {}).get("scale", [])): out.append(f"  --text-{i}: {v / 16:g}rem;  /* {v:g}px */")
    for v in c.get("space", {}).get("scale", []): out.append(f"  --space-{v:g}: {v / 16:g}rem;  /* {v:g}px */")
    for i, v in enumerate(c.get("radius", {}).get("scale", [])): out.append(f"  --radius-{i}: {v:g}px;")
    for k, v in c.get("shadow", {}).items(): out.append(f"  --shadow-{k}: {v};")
    for k, v in c.get("motion", {}).items(): out.append(f"  --motion-{k}: {v};")
    for v in c.get("z", {}).get("scale", []): out.append(f"  --z-{v}: {v};")
    out.append("}")
    if "dark" in ts:
        out += ["", "@media (prefers-color-scheme: dark) {"] + ["  " + l for l in block(":root:not([data-theme=\"light\"])", ts["dark"])] + ["}"]
        out += [""] + block(':root[data-theme="dark"]', ts["dark"])
    out += ["", "@media (prefers-reduced-motion: reduce) {", "  :root { --motion-fast: 0ms; --motion-base: 0ms; }", "}"]
    return "\n".join(out) + "\n"


def cmd_sync(a, root):
    c = load_contract(root) or die("no .ffcode/design.toml (run: ffcode ui init)", 1)
    css = render_css(c)
    if a.stdout: print(css); return 0
    tw = c.get("ui", {}).get("tailwind")
    if tw:
        cols = themes(c); names = next(iter(cols.values()))
        js = ("// Generated by `ffcode ui sync` from .ffcode/design.toml. Do not edit.\nmodule.exports = {\n  colors: {\n" + "".join(f"    '{k}': 'var(--color-{k})',\n" for k in names) +
              "  },\n  spacing: {\n" + "".join(f"    '{v:g}': 'var(--space-{v:g})',\n" for v in c.get('space', {}).get('scale', [])) +
              "  },\n  borderRadius: {\n" + "".join(f"    '{i}': 'var(--radius-{i})',\n" for i, _ in enumerate(c.get('radius', {}).get('scale', []))) + "  },\n};\n")
        (root / tw).write_text(js); print(f"wrote {tw} (use as theme.extend)")
    out = root / c.get("ui", {}).get("output", "src/styles/tokens.css")
    out.parent.mkdir(parents=True, exist_ok=True)
    old = out.read_text() if out.is_file() else None
    out.write_text(css); print(f"{'unchanged' if old == css else 'wrote'} {out.relative_to(root)} ({len(css.splitlines())} lines); import it once at the app root")
    return 0


# ---------------------------------------------------------------- components
CEXT = {".tsx", ".jsx", ".vue", ".svelte"}


def inventory(root, c):
    dirs = (c or {}).get("ui", {}).get("components") or [d for d in ("src/components", "components", "app/components", "src/ui") if (root / d).is_dir()]
    files = [f for f in tracked_files(root) if f.suffix in UI and is_text(root / f)]
    texts = {f: (root / f).read_text(errors="replace") for f in files}
    comps = {}
    for f in files:
        if f.suffix not in CEXT or not any(str(f).startswith(d.rstrip("/") + "/") for d in dirs): continue
        t = texts[f]
        names = re.findall(r"export\s+(?:default\s+)?(?:function|const|class)\s+([A-Z]\w*)", t) or ([f.stem.split(".")[0]] if f.stem[:1].isupper() else [])
        for n in names:
            props = []
            m = re.search(rf"(?:interface|type)\s+{n}Props\b[^{{]*\{{([^}}]*)\}}", t) or re.search(r"(?:interface|type)\s+\w*Props\b[^{]*\{([^}]*)\}", t)
            if m: props = re.findall(r"^\s*(\w+)\??\s*:", m.group(1), re.M)
            uses = sum(len(re.findall(rf"<{n}\b", tx)) for g, tx in texts.items() if g != f)
            comps[n] = {"file": str(f), "uses": uses, "props": props}
    return comps


def cmd_components(a, root):
    c = load_contract(root); comps = inventory(root, c)
    if not comps: print("no components found (set [ui] components in design.toml)"); return 0
    if a.name:
        for n, d in comps.items():
            if a.name.lower() in n.lower(): print(f"{n}  {d['file']}  used {d['uses']}x\n  props: {', '.join(d['props']) or '-'}")
        return 0
    print(f"{len(comps)} components (name  uses  file  props)")
    for n, d in sorted(comps.items(), key=lambda x: -x[1]["uses"])[:a.top]:
        print(f"  {n:24}{d['uses']:4}  {d['file']}  {', '.join(d['props'][:6])}")
    unused = [n for n, d in comps.items() if d["uses"] == 0]
    if unused: print(f"unused: {', '.join(unused[:12])}")
    (root / DIRNAME / "cache").mkdir(parents=True, exist_ok=True); (root / DIRNAME / "cache" / "components.json").write_text(json.dumps(comps))
    return 0


# ---------------------------------------------------------------- new
def cmd_new(a, root):
    if not re.fullmatch(r"[A-Z]\w+", a.name): die("NAME must be PascalCase")
    c = load_contract(root); comps = inventory(root, c)
    if a.name in comps: die(f"{a.name} already exists: {comps[a.name]['file']} (reuse it)", 1)
    ts = (root / "tsconfig.json").is_file(); ext = "tsx" if ts else "jsx"
    d = Path(a.dir) if a.dir else Path(((c or {}).get("ui", {}).get("components") or ["src/components"])[0])
    module = any(f.name.endswith((".module.css", ".module.scss")) for f in tracked_files(root))
    tw = any((root / n).is_file() for n in ("tailwind.config.js", "tailwind.config.ts", "tailwind.config.cjs"))
    style = "module" if module else "tailwind" if tw else "css"
    cls = {"module": "styles.root", "tailwind": '"' + '"', "css": f'"{a.name}"'}[style]
    imp = {"module": f"import styles from './{a.name}.module.css';\n", "tailwind": "", "css": f"import './{a.name}.css';\n"}[style]
    tsprops = f"export interface {a.name}Props {{\n  children?: React.ReactNode;\n  className?: string;\n}}\n\n" if ts else ""
    sig = f"{{ children, className }}: {a.name}Props" if ts else "{ children, className }"
    cn = "className={[" + cls + ", className].filter(Boolean).join(' ')}" if style != "tailwind" else "className={className}"
    body = f"import React from 'react';\n{imp}\n{tsprops}export function {a.name}({sig}) {{\n  return <div {cn}>{{children}}</div>;\n}}\n\nexport default {a.name};\n"
    files = {f"{a.name}.{ext}": body}
    if style == "module": files[f"{a.name}.module.css"] = ".root {\n  display: block;\n}\n\n.root:focus-visible {\n  outline: 2px solid var(--color-focus);\n  outline-offset: 2px;\n}\n"
    if style == "css": files[f"{a.name}.css"] = f".{a.name} {{\n  display: block;\n}}\n"
    for n, t in files.items():
        p = root / d / n; print(("would create " if a.dry_run else "create ") + str(p.relative_to(root)))
        if not a.dry_run: p.parent.mkdir(parents=True, exist_ok=True); p.write_text(t)
    print(f"convention: {ext}, styles={style}. Add: states (hover/focus/disabled/loading/empty/error), a test, an entry in design.toml components if it is a primitive")
    return 0


# ---------------------------------------------------------------- context
def cmd_context(a, root):
    cfg = load_config(root); c = load_contract(root); fe = cfg.get("frontend", {})
    def first(*names):
        for n in names:
            if n and (root / n).is_file(): return root / n
    prod = first(fe.get("product"), "PRODUCT.md", f"{DIRNAME}/product.md"); des = first(fe.get("design"), "DESIGN.md", f"{DIRNAME}/design.md")
    pkg = (root / "package.json").read_text() if (root / "package.json").is_file() else ""
    stack = [n for n, rx in (("react", r'"react"'), ("vue", r'"vue"'), ("svelte", r'"svelte"'), ("tailwind", r"tailwindcss"), ("i18n", r"i18next|react-intl|vue-i18n"),
                             ("framer-motion", r"framer-motion"), ("testing-library", r"testing-library")) if re.search(rx, pkg)]
    print(f"# UI context: {root.name}\nstack: {', '.join(stack) or '?'}; typescript={'yes' if (root / 'tsconfig.json').is_file() else 'no'}")
    for label, p in (("product", prod), ("design notes", des)):
        if p:
            lines = [l.strip() for l in p.read_text().splitlines() if l.strip() and not l.startswith(("<!--", "#"))][:6]
            print(f"{label} ({p.relative_to(root)}): " + " | ".join(l[:110] for l in lines))
        else: print(f"{label}: missing")
    if c:
        ts = themes(c); first_t = next(iter(ts.values()))
        print(f"mode: {c.get('meta', {}).get('mode', '?')}; mood: {', '.join(c.get('meta', {}).get('mood', [])) or '?'}; themes: {', '.join(ts)}")
        print("colors: " + ", ".join(f"{k} {v}" for k, v in first_t.items()))
        for k in ("type", "space", "radius", "z"): print(f"{k}: {c.get(k, {}).get('scale')}")
        print(f"font: {c.get('font')}; motion: {c.get('motion')}; tokens file: {c.get('ui', {}).get('output')}")
        for r in c.get("rules", {}).get("notes", []): print(f"rule: {r}")
    else:
        print("design contract: MISSING -> `ffcode ui init` (infers it from the code), then correct it")
    comps = inventory(root, c)
    print(f"components: {len(comps)}; most used: " + ", ".join(f"{n}({d['uses']})" for n, d in sorted(comps.items(), key=lambda x: -x[1]['uses'])[:8]))
    rc, out = run([sys.executable, str(Path(__file__).parent / "uilint.py"), "--root", str(root), "--summary"])
    print("uilint (whole project): " + "; ".join(l.split(")")[0].replace(" (", " ") for l in out.splitlines() if re.match(r"[A-Z0-9]+ \(", l)) or "clean")
    return 0


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--root"); sub = ap.add_subparsers(dest="c", required=True)
    sub.add_parser("context")
    i = sub.add_parser("init"); i.add_argument("--stdout", action="store_true"); i.add_argument("--force", action="store_true")
    p = sub.add_parser("palette"); p.add_argument("--fix", action="store_true")
    s = sub.add_parser("sync"); s.add_argument("--stdout", action="store_true")
    k = sub.add_parser("components"); k.add_argument("name", nargs="?"); k.add_argument("--top", type=int, default=25)
    n = sub.add_parser("new"); n.add_argument("name"); n.add_argument("--dir"); n.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(); root = find_root(a.root)
    return {"context": cmd_context, "init": cmd_init, "palette": cmd_palette, "sync": cmd_sync, "components": cmd_components, "new": cmd_new}[a.c](a, root)


if __name__ == "__main__":
    sys.exit(main() or 0)
