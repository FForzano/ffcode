"""Validate .ffcode/*.toml: parse errors, wrong types, unknown keys (typos), unknown languages, commands that are not on PATH.
  ff config --validate [--root DIR]     exit 1 on errors; warnings (unknown keys, missing executables) do not fail"""
from __future__ import annotations

import argparse
import re
import shutil
import tomllib
from pathlib import Path

from common import DIRNAME, find_root

LANGS = {"python", "php", "typescript", "javascript", "react", "terraform", "shell", "aws", "matlab", "html", "css"}
STEPS = ["format_check", "lint", "typecheck", "test", "build", "coverage"]
SCHEMA = {
    "project": {"name": str, "languages": list},
    "commands": {**{k: str for k in STEPS}, "test_one": str, "test_note": str},
    "limits": {k: int for k in ("max_function_lines", "max_file_lines", "max_params", "max_line_length", "dup_window")},
    "commit": {"style": str, "max_subject": int},
    "check": {"secrets": bool, "base": str, "ui": bool},
    "coverage": {"report": str, "min": int},
    "mutation": {"critical": list, "command": str},
    "frontend": {"product": str, "design": str},
    "infer": {"min_files": int, "strict": float, "purity": float, "name_purity": float, "allow_share": float, "max_questions": int,
              "suffixes": list, "exclude": list, "merge": list},
}
FLOW = {"depth": int, "ignore": list, "entrypoint": list, "effects": dict}
WS_REPO = {"name": str, "self": bool, "role": str, "url": str, "branch": str, "local": str, "contracts": list, "depends_on": list}


def load(f: Path, errors):
    try: return tomllib.loads(f.read_text())
    except tomllib.TOMLDecodeError as e: errors.append(f"{f.name}: {e}"); return None


def typed(where, key, val, typ, errors):
    if not isinstance(val, typ) or (typ is int and isinstance(val, bool)): errors.append(f"{where}.{key}: expected {typ.__name__}, got {type(val).__name__}")


def config_toml(f: Path, errors, warns):
    d = load(f, errors)
    if d is None: return
    for sec, body in d.items():
        if sec not in SCHEMA: warns.append(f"config.toml: unknown section [{sec}]"); continue
        for k, v in body.items():
            if k not in SCHEMA[sec]: warns.append(f"config.toml: unknown key {sec}.{k}"); continue
            typed(f"config.toml {sec}", k, v, SCHEMA[sec][k], errors)
    for l in d.get("project", {}).get("languages", []):
        if str(l).lower() not in LANGS: warns.append(f"config.toml: language '{l}' has no notes in ffcode-core/references/lang")
    if d.get("commit", {}).get("style", "conventional") not in ("conventional", "imperative"): errors.append("config.toml: commit.style must be conventional or imperative")
    for step, cmd in d.get("commands", {}).items():
        if step in ("test_note",) or not isinstance(cmd, str) or not cmd.strip(): continue
        exe = re.split(r"\s+", cmd.strip())[0]
        if not shutil.which(exe) and not Path(f.parent.parent / exe).exists(): warns.append(f"config.toml: commands.{step}: '{exe}' not found on PATH")


def design_toml(f: Path, errors, warns):
    d = load(f, errors)
    if d is None: return
    for mode, colors in d.get("color", {}).items():
        for name, val in colors.items():
            if not re.fullmatch(r"#[0-9a-fA-F]{3,8}", str(val)): errors.append(f"design.toml: color.{mode}.{name} = {val!r} is not a hex colour")
    for sec in ("type", "space", "radius"):
        sc = d.get(sec, {}).get("scale")
        if sc is not None and not (isinstance(sc, list) and all(isinstance(x, (int, float)) for x in sc)): errors.append(f"design.toml: {sec}.scale must be a list of numbers")


def flow_toml(f: Path, errors, warns):
    d = load(f, errors)
    if d is None: return
    for k, v in d.items():
        if k not in FLOW: warns.append(f"flow.toml: unknown key {k}"); continue
        typed("flow.toml", k, v, FLOW[k], errors)
    for i, e in enumerate(d.get("entrypoint", []) if isinstance(d.get("entrypoint"), list) else []):
        where = f"flow.toml: entrypoint[{i}]"
        if e.get("kind", "http") not in ("http", "cli", "job", "event"): errors.append(f"{where}: kind must be http, cli, job or event")
        try: re.compile(e.get("pattern", ""))
        except re.error as ex: errors.append(f"{where}: pattern is not a valid regex ({ex})")
        if not e.get("pattern"): errors.append(f"{where}: pattern is required")
        for k in e:
            if k not in ("kind", "file", "pattern"): warns.append(f"{where}: unknown key {k}")


def rules_toml(f: Path, errors, warns):
    import lint, uilint
    from rules import parse
    d = load(f, errors)
    if d is None: return
    lint_ids = set(lint.RULES) | set(uilint.RULES); checklist = {r[1] for r in parse()}
    for rid, r in d.get("rule", {}).items():
        if rid not in lint_ids | checklist: errors.append(f"rules.toml: unknown rule id {rid}"); continue
        for k, v in r.items():
            if k not in ("off", "ignore", "reason", "adr", "note"): warns.append(f"rules.toml: {rid}: unknown key {k}")
        if (r.get("off") or r.get("ignore")) and rid not in lint_ids: warns.append(f"rules.toml: {rid} is a judgment rule: off/ignore have no effect, use note")
        if not r.get("reason") and not r.get("note"): warns.append(f"rules.toml: {rid}: give a reason")
        adr = r.get("adr")
        if adr and not list((f.parent / "decisions").glob(f"{str(adr).zfill(4)}-*.md")): errors.append(f"rules.toml: {rid}: decision record {adr} not found")


def architecture_toml(f: Path, errors, warns):
    d = load(f, errors)
    if d is None: return
    names = [l.get("name") for l in d.get("layer", [])]
    for l in d.get("layer", []):
        if not l.get("name") or not l.get("paths"): errors.append(f"architecture.toml: a layer needs name and paths ({l.get('name')})"); continue
        if names.count(l["name"]) > 1: errors.append(f"architecture.toml: duplicate layer {l['name']}")
        try: re.compile(l.get("name_pattern", ""))
        except re.error as e: errors.append(f"architecture.toml: {l['name']}: name_pattern: {e}")
        for m in l.get("may_import", []):
            if m not in names: errors.append(f"architecture.toml: {l['name']} may_import unknown layer '{m}'")
        if l.get("example") and not (f.parent.parent / l["example"]).is_file(): warns.append(f"architecture.toml: {l['name']}: example {l['example']} not found")
    if d.get("layer") and not d.get("architecture", {}).get("style"): warns.append("architecture.toml: architecture.style is empty")


def workspace_toml(f: Path, errors, warns):
    d = load(f, errors)
    if d is None: return
    names = [r.get("name") for r in d.get("repo", [])]
    for r in d.get("repo", []):
        for k, v in r.items():
            if k not in WS_REPO: warns.append(f"workspace.toml: {r.get('name')}: unknown key {k}")
            else: typed(f"workspace.toml {r.get('name')}", k, v, WS_REPO[k], errors)
        for dep in r.get("depends_on", []):
            if dep not in names: errors.append(f"workspace.toml: {r.get('name')} depends on unknown repo '{dep}'")
    if sum(1 for r in d.get("repo", []) if r.get("self")) > 1: errors.append("workspace.toml: more than one repo with self = true")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--validate", action="store_true"); ap.add_argument("--root"); a = ap.parse_args()
    root = find_root(a.root); d = root / DIRNAME
    errors, warns, seen = [], [], []
    for name, fn in (("config.toml", config_toml), ("design.toml", design_toml), ("workspace.toml", workspace_toml), ("rules.toml", rules_toml), ("architecture.toml", architecture_toml), ("flow.toml", flow_toml)):
        if (d / name).is_file(): seen.append(name); fn(d / name, errors, warns)
    if not seen: print("no .ffcode/*.toml here"); return 0
    for w in warns: print("warn ", w)
    for e in errors: print("ERROR", e)
    print(f"config: {len(errors)} error(s), {len(warns)} warning(s) in {', '.join(seen)}")
    return 1 if errors else 0
