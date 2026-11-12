"""Create a numbered decision record in .ffcode/decisions/. Usage: adr.py "Title" [--root DIR]"""
from __future__ import annotations

import argparse
import datetime
import re

from common import DIRNAME, find_root


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("title"); ap.add_argument("--root")
    a = ap.parse_args(); d = find_root(a.root) / DIRNAME / "decisions"; d.mkdir(parents=True, exist_ok=True)
    n = 1 + max([int(m.group(1)) for f in d.glob("*.md") if (m := re.match(r"(\d+)-", f.name))] or [0])
    slug = re.sub(r"[^a-z0-9]+", "-", a.title.lower()).strip("-")[:50]
    p = d / f"{n:04d}-{slug}.md"
    p.write_text(f"# {n:04d} {a.title}\n\nDate: {datetime.date.today()}  Status: accepted\n\n## Context\n\n## Decision\n\n## Consequences\n\n## Alternatives rejected\n")
    print(p)


if __name__ == "__main__":
    main()
