"""Token budget of the skills (1 token ~ 4 chars): description (always in context), SKILL.md (loaded on use), references.
  ff budget [--check]    --check exits 1 when a limit of ffcode-core/budget.toml is exceeded (used by tests/run.sh)"""
from __future__ import annotations

import argparse
import re
import tomllib
from pathlib import Path

SKILLS = Path(__file__).resolve().parent.parent.parent
tok = lambda n: -(-n // 4)


def description(md: str) -> str:
    m = re.search(r"^description:\s*(.+)$", md, re.M)
    return m.group(1).strip() if m else ""


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    lim = tomllib.loads((SKILLS / "ffcode-core" / "budget.toml").read_text())
    rows, bad, total_desc = [], [], 0
    for d in sorted(SKILLS.glob("ffcode-*/")):
        md = (d / "SKILL.md").read_text(); desc = len(description(md)); body = len(md)
        refs = sum(f.stat().st_size for f in (d / "references").rglob("*.md")) if (d / "references").is_dir() else 0
        total_desc += desc; rows.append((d.name, desc, body, refs))
        if desc > lim["max_description_chars"]: bad.append(f"{d.name}: description {desc} > {lim['max_description_chars']} chars")
        cap = lim.get("max_skill_md_chars", {}).get(d.name, lim["max_skill_md_chars"]["default"])
        if body > cap: bad.append(f"{d.name}: SKILL.md {body} > {cap} chars")
    print(f"{'skill':<20}{'descr':>7}{'SKILL.md':>10}{'refs':>8}   (chars; ~tokens: descr/SKILL.md)")
    for n, de, b, r in rows: print(f"{n:<20}{de:>7}{b:>10}{r:>8}   ~{tok(de)}/{tok(b)}")
    print(f"always in context: {total_desc} chars of descriptions (~{tok(total_desc)} tokens)")
    if total_desc > lim["max_descriptions_total_chars"]: bad.append(f"descriptions total {total_desc} > {lim['max_descriptions_total_chars']} chars")
    for b in bad: print("OVER:", b)
    return 1 if a.check and bad else 0
