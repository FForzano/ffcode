"""Shared helpers: project root, .ffcode/ config, git, subprocess. Stdlib only (Python >= 3.11)."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

DIRNAME = ".ffcode"
SCHEMA = 2   # layout of .ffcode/ written by this version; `ff upgrade` brings older projects up to it

DEFAULT_LIMITS = {
    "max_function_lines": 50,
    "max_file_lines": 500,
    "max_params": 5,
    "max_line_length": 100,
    "dup_window": 10,
}


def run(cmd, cwd=None, timeout=900):
    """Run a command (list or shell string). Returns (returncode, combined output)."""
    try:
        p = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True,
                           text=True, timeout=timeout)
    except FileNotFoundError as e:
        return 127, str(e)
    except subprocess.TimeoutExpired:
        return 124, f"timeout after {timeout}s"
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def git(args, cwd):
    return run(["git", *args], cwd=cwd)


def find_root(start=None):
    """Nearest ancestor holding .ffcode/, else the git toplevel, else the start dir."""
    p = Path(start or os.getcwd()).resolve()
    for d in [p, *p.parents]:
        if (d / DIRNAME).is_dir():
            return d
    rc, out = git(["rev-parse", "--show-toplevel"], p)
    return Path(out.strip()) if rc == 0 and out.strip() else p


def load_config(root: Path) -> dict:
    cfg = {"project": {}, "commands": {}, "limits": dict(DEFAULT_LIMITS), "commit": {}, "check": {}}
    f = root / DIRNAME / "config.toml"
    if f.is_file():
        data = tomllib.loads(f.read_text())
        for k, v in data.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    return cfg


def load_contract(root: Path) -> dict | None:
    """.ffcode/design.toml (machine-readable design contract) or None."""
    f = root / DIRNAME / "design.toml"
    return tomllib.loads(f.read_text()) if f.is_file() else None


def tracked_files(root: Path, only_changed=False, staged=False, base=None):
    """Files to look at: tracked + untracked-not-ignored; or changed vs HEAD/base; or staged."""
    if staged:
        rc, out = git(["diff", "--cached", "--name-only", "--diff-filter=ACMR"], root)
    elif only_changed:
        ref = base or "HEAD"
        rc, a = git(["diff", "--name-only", "--diff-filter=ACMR", ref], root)
        _, b = git(["ls-files", "--others", "--exclude-standard"], root)
        out = a + "\n" + b
    else:
        rc, out = git(["ls-files", "-co", "--exclude-standard"], root)
    if rc != 0:
        return [p.relative_to(root) for p in root.rglob("*") if p.is_file()
                and not any(x in p.parts for x in (".git", "node_modules", "venv", ".venv", "vendor", DIRNAME))]
    skip = (DIRNAME + "/",)
    return [Path(x) for x in sorted(set(out.split("\n"))) if x and not x.startswith(skip) and (root / x).is_file()]


def is_text(path: Path, limit=2_000_000):
    try:
        if path.stat().st_size > limit:
            return False
        return b"\0" not in path.read_bytes()[:4096]
    except OSError:
        return False


LANG_BY_EXT = {
    ".py": "python", ".php": "php", ".ts": "typescript", ".tsx": "typescript", ".js": "javascript",
    ".jsx": "javascript", ".m": "matlab", ".html": "html", ".css": "css", ".scss": "css",
    ".sh": "shell", ".tf": "terraform", ".sql": "sql", ".yml": "yaml", ".yaml": "yaml",
    ".java": "java", ".go": "go", ".rs": "rust", ".c": "c", ".cpp": "cpp", ".h": "c",
}


def lang_of(path) -> str | None:
    return LANG_BY_EXT.get(Path(path).suffix.lower())


def die(msg, code=2):
    print(msg, file=sys.stderr)
    sys.exit(code)


def changed_lines(root: Path, only_staged=False, base=None):
    """{path: set(line numbers) | None}: lines added or modified vs HEAD/base (or the index);
    None means the whole file is new (untracked), so every line counts."""
    args = ["diff", "-U0", "--no-color", "--diff-filter=ACMR"] + (["--cached"] if only_staged else [base or "HEAD"])
    _, out = git(args, root)
    res, cur = {}, None
    for ln in out.split("\n"):
        if ln.startswith("+++ "):
            cur = ln[6:] if ln.startswith("+++ b/") else None
            if cur is not None: res.setdefault(cur, set())
        elif ln.startswith("@@") and cur is not None:
            m = re.match(r"@@ -\S+ \+(\d+)(?:,(\d+))? @@", ln)
            if m:
                start, n = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1)
                res[cur].update(range(start, start + n))
    if not only_staged:
        _, new = git(["ls-files", "--others", "--exclude-standard"], root)
        for x in new.split("\n"):
            if x: res[x] = None
    return res
