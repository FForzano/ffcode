"""Project policy read by the scripts: .ffcode/rules.toml (deviations from the rules) and .ffcode/baseline.json (known legacy findings).
rules.toml:
  [rule.FUNC]                     # a lint/uilint id (FUNC, TODO, OFFCOLOR, ...) or a checklist id (S4, D1, ...)
  ignore = ["migrations/**"]      # lint ids: findings in these paths are dropped
  off = true                      # lint ids: rule disabled for the whole project
  reason = "generated code"       # required: why
  adr = "0003"                    # optional: the decision record behind it
  note = "..."                    # checklist ids: how the rule is applied here (printed by `ff rules`, read by review)
baseline.json: {fingerprint: count}, written by `ff lint --baseline`; fingerprints are rule + file + the text of the line, so they survive line shifts."""
from __future__ import annotations

import fnmatch
import hashlib
import json
import tomllib
from collections import Counter
from pathlib import Path

from common import DIRNAME


def load_rules(root: Path) -> dict:
    f = root / DIRNAME / "rules.toml"
    return tomllib.loads(f.read_text()).get("rule", {}) if f.is_file() else {}


def suppressed(rules: dict, rule: str, path) -> bool:
    r = rules.get(rule)
    if not r: return False
    return bool(r.get("off")) or any(fnmatch.fnmatch(str(path), g) for g in r.get("ignore", []))


def fingerprint(root: Path, f, line: int, rule: str) -> str:
    p = root / f
    try: text = p.read_text(errors="replace").splitlines()[line - 1].strip() if line > 0 and p.is_file() else ""
    except IndexError: text = ""
    return hashlib.sha1(f"{rule}|{f}|{text}".encode()).hexdigest()[:12]


def baseline_path(root: Path) -> Path:
    return root / DIRNAME / "baseline.json"


def apply(root: Path, findings, use_baseline=True):
    """-> (kept, n_hidden_by_rules, n_hidden_by_baseline)"""
    rules = load_rules(root)
    kept = [x for x in findings if not suppressed(rules, x[2], x[0])]
    hid_rules = len(findings) - len(kept)
    hid_base = 0
    bp = baseline_path(root)
    if use_baseline and bp.is_file():
        left = Counter(json.loads(bp.read_text()))
        out = []
        for x in kept:
            fp = fingerprint(root, x[0], x[1], x[2])
            if left[fp] > 0: left[fp] -= 1; hid_base += 1
            else: out.append(x)
        kept = out
    return kept, hid_rules, hid_base


def write_baseline(root: Path, findings, merge=False) -> int:
    kept, _, _ = apply(root, findings, use_baseline=False)
    c = Counter(fingerprint(root, x[0], x[1], x[2]) for x in kept)
    bp = baseline_path(root); bp.parent.mkdir(exist_ok=True)
    if merge and bp.is_file(): c = Counter(json.loads(bp.read_text())) + c
    bp.write_text(json.dumps(dict(sorted(c.items())), indent=0) + "\n")
    return sum(c.values())
