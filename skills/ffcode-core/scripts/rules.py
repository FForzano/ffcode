"""Print the checklist rules that need judgment (the [auto] ones are run by ff lint/check, not read), plus the language notes.
  ff rules [--judge|--auto|--all] [--lang python,php] [ID ...]
Default: [judge] rules + notes of the project's languages (`[project] languages` in .ffcode/config.toml)."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from common import find_root, load_config
from policy import load_rules

ALIAS = {"typescript": "typescript-react", "javascript": "typescript-react", "react": "typescript-react", "terraform": "shell-aws", "shell": "shell-aws",
         "aws": "shell-aws", "html": "html-css", "css": "html-css"}
REF = Path(__file__).resolve().parent.parent / "references"
RULE = re.compile(r"^- ([A-Z]\d+) \[(auto|judge)\]")


def parse():
    """[(section, id, mode, text)] from checklist.md; continuation lines are indented."""
    out, section = [], ""
    for line in (REF / "checklist.md").read_text().splitlines():
        if line.startswith("## "): section = line[3:].strip()
        m = RULE.match(line)
        if m: out.append([section, m.group(1), m.group(2), line])
        elif out and line.startswith("  "): out[-1][3] += "\n" + line
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("ids", nargs="*")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--judge", action="store_true"); g.add_argument("--auto", action="store_true"); g.add_argument("--all", action="store_true")
    ap.add_argument("--lang", help="comma-separated; default from config")
    ap.add_argument("--root")
    a = ap.parse_args()
    mode = "auto" if a.auto else "all" if a.all else "judge"
    want = {i.upper() for i in a.ids}
    last = None
    for section, rid, m, text in parse():
        if want and rid not in want: continue
        if not want and mode != "all" and m != mode: continue
        if section != last: print(f"\n## {section}"); last = section
        print(text)
    root = find_root(a.root)
    dev = {k: v for k, v in load_rules(root).items() if not want or k in want}
    if dev:
        print("\n## Deviations of this project (.ffcode/rules.toml; they win)")
        for k, v in dev.items():
            how = "off" if v.get("off") else ("ignore " + ", ".join(v.get("ignore", [])) if v.get("ignore") else "")
            print(f"- {k}: " + "; ".join(x for x in (how, v.get("note", ""), v.get("reason", ""), "adr " + v["adr"] if v.get("adr") else "") if x))
    if want: return 0
    langs = a.lang.split(",") if a.lang else load_config(root).get("project", {}).get("languages", [])
    for lang in langs:
        lang = lang.strip().lower(); f = REF / "lang" / f"{ALIAS.get(lang, lang)}.md"
        if f.is_file(): print(f"\n# lang/{f.name}\n{f.read_text().strip()}")
    print("\n[auto] rules: run `ff check --changed`; project deviations: .ffcode/rules.toml and style.md (they win).")
    return 0
