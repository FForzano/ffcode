"""Create .ffcode/ in a project: detect stack and commands, write config.toml and skeleton files.
Never overwrites an existing file. Usage: init.py [--root DIR] [--dry-run]"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from common import DIRNAME, DEFAULT_LIMITS, find_root, git

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"


def detect(root: Path) -> tuple[list[str], dict[str, str]]:
    langs: list[str] = []
    cmds: dict[str, str] = {}
    if (root / "pyproject.toml").is_file() or (root / "requirements.txt").is_file():
        langs.append("python")
        pp = (root / "pyproject.toml").read_text() if (root / "pyproject.toml").is_file() else ""
        if "[tool.ruff" in pp: cmds["lint"] = "ruff check ."
        if "[tool.black" in pp: cmds["format_check"] = "black --check ."
        elif "[tool.ruff" in pp: cmds["format_check"] = "ruff format --check ."
        if "[tool.mypy" in pp: cmds["typecheck"] = "mypy ."
        if "pytest" in pp or (root / "tests").is_dir(): cmds["test"] = "pytest -q"
    if (root / "composer.json").is_file():
        langs.append("php")
        scripts = json.loads((root / "composer.json").read_text() or "{}").get("scripts", {})
        for k in ("lint", "test", "analyse", "cs"):
            if k in scripts: cmds["typecheck" if k == "analyse" else k] = f"composer run {k}"
        if "test" not in cmds and (root / "codeception.yml").is_file():
            cmds["test"] = "vendor/bin/codecept run unit"
            cmds["test_note"] = "may need to run inside the container (docker compose exec web ...)"
    if (root / "package.json").is_file():
        pkg = json.loads((root / "package.json").read_text() or "{}")
        langs.append("typescript" if (root / "tsconfig.json").is_file() else "javascript")
        s = pkg.get("scripts", {})
        for k in ("lint", "test", "build", "typecheck"):
            if k in s: cmds.setdefault(k, f"npm run {k}" + (" -- --watchAll=false" if k == "test" and "react-scripts" in s[k] else ""))
        if "typecheck" not in cmds and (root / "tsconfig.json").is_file(): cmds["typecheck"] = "npx tsc --noEmit"
    if any(root.rglob("*.tf")) if (root / "infra").exists() or list(root.glob("*.tf")) else False:
        langs.append("terraform"); cmds.setdefault("lint", "terraform fmt -check -recursive")
    if list(root.glob("*.sh")) or list(root.glob("*/*.sh")):
        langs.append("shell"); cmds.setdefault("lint", "shellcheck $(git ls-files '*.sh')")
    if list(root.glob("*.m")) or list(root.glob("*/*.m")): langs.append("matlab")
    if list(root.glob("*.html")) or list(root.glob("*/*.html")): langs.append("html")
    if list(root.glob("*.css")) or list(root.glob("*/*.css")): langs.append("css")
    return langs, cmds


def render_config(name: str, langs: list[str], cmds: dict[str, str], ui: bool = False) -> str:
    q = lambda s: '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    out = [f"[project]\nname = {q(name)}\nlanguages = [{', '.join(q(l) for l in langs)}]\n",
           "[commands]  # run from the project root; empty or missing = skipped. Wrap in docker/ssh here if needed.\n"]
    for k in ("format_check", "lint", "typecheck", "test", "build"):
        out.append(f"{k} = {q(cmds[k])}" if k in cmds else f"# {k} = \"\"")
    out.append("\n[limits]  # used by ffcode lint; project overrides of the defaults")
    out += [f"{k} = {v}" for k, v in DEFAULT_LIMITS.items()]
    out.append('\n[commit]\nstyle = "conventional"  # conventional | imperative\nmax_subject = 72\n')
    out.append('# coverage = ""   # e.g. "pytest --cov=. --cov-report=xml"; then set [coverage] report\n[coverage]\n# report = "coverage.xml"  # Cobertura, Clover or lcov\n# min = 80  # minimum diff coverage in percent\n')
    out.append('# [mutation]  # optional, slow: areas where a surviving mutant costs money or data\n# critical = ["services/payments/**"]\n# command = "mutmut run --paths-to-mutate {files}"\n')
    out.append('[check]\nsecrets = true\nbase = "main"  # branch used for --changed\n')
    if ui: out.append('ui = true  # run ffcode uilint in check (a11y, tokens, motion, i18n)\n\n[frontend]  # design context; empty = PRODUCT.md/DESIGN.md at the root if present, else .ffcode/product.md, design.md\n# product = ""\n# design = ""\n')
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    root = find_root(a.root)
    langs, cmds = detect(root)
    pkg = (root / 'package.json').read_text() if (root / 'package.json').is_file() else ''
    ui = bool(re.search(r'"(react|vue|svelte|@angular/core|next|nuxt|solid-js|preact)"', pkg)) or 'html' in langs or 'css' in langs
    d = root / DIRNAME
    files = {
        "config.toml": render_config(root.name, langs, cmds, ui),
        "style.md": (TEMPLATES / "style.md").read_text(),
        "context.md": (TEMPLATES / "context.md").read_text().replace("{{name}}", root.name),
        "state.md": (TEMPLATES / "state.md").read_text(),
        ".gitignore": "# generated or personal, not shared\nmap.md\ncache/\nrepos/\nstate.md\n",
    }
    print(f"root: {root}\nlanguages: {langs or '-'}\ncommands: {cmds or '-'}")
    for n, body in files.items():
        p = d / n
        if p.exists(): print(f"keep   {p.relative_to(root)}"); continue
        print(f"create {p.relative_to(root)}")
        if not a.dry_run:
            d.mkdir(exist_ok=True); p.write_text(body)
    if not a.dry_run:
        (d / "decisions").mkdir(exist_ok=True)
    legacy = [n for n in ("CLAUDE.md", "AGENTS.md") if (root / n).is_file()]
    if legacy:
        print(f"legacy context found: {legacy} -> migrate into .ffcode/context.md (see ffcode-init skill)")


if __name__ == "__main__":
    main()
