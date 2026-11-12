"""Hooks that make the skills' routine steps deterministic.
  ff hook session-start     Claude Code SessionStart: update notice, refresh a stale map, one status line (silent outside .ffcode/ projects)
  ff hook stop              Claude Code Stop: lint of the diff, blocks once only when the findings changed since the last report
  ff hooks install [--project] [--remove]   add/remove the two hooks in ~/.claude/settings.json (or ./.claude/settings.json)
  ff hooks status           are the Claude Code hooks installed (user or project)?
  ff hooks git [--remove]   git hooks post-merge/post-checkout/post-rewrite that refresh .ffcode/map.md in the background"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import sys
from pathlib import Path

from common import DIRNAME, find_root, git, run

FF = Path(__file__).resolve().parent / "ff"
EVENTS = {"SessionStart": "hook session-start", "Stop": "hook stop"}
MARK = ("# >>> ffcode map", "# <<< ffcode map")
CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "ffcode"


def _stdin():
    try: return json.loads(sys.stdin.read() or "{}")
    except (ValueError, OSError): return {}


def _ff(*args, cwd=None):
    return run([str(FF), *args], cwd=cwd)


def session_start():
    _stdin(); root = find_root()
    if not (root / DIRNAME).is_dir(): return 0
    _, upd = _ff("update-check", cwd=root)
    if upd.strip(): print(upd.strip() + "\nAsk the user whether to update; only on a yes run `ff update-check --apply`.")
    m = root / DIRNAME / "map.md"
    rc, ct = git(["log", "-1", "--format=%ct"], root)
    if rc == 0 and ct.strip().isdigit() and (not m.is_file() or m.stat().st_mtime < int(ct)): _ff("map", cwd=root)
    if hint_due(): print(HINT)
    import upgrade
    upgrade.auto(root)
    print(f"ffcode: {DIRNAME}/ present in {root.name}; `ff orient` loads context, style, state and map in one call.")
    return 0


def stop():
    d = _stdin()
    root = find_root()
    if d.get("stop_hook_active") or not (root / DIRNAME).is_dir(): return 0
    _, raw = _ff("lint", "--changed", "--summary", cwd=root)
    _, js = _ff("lint", "--changed", "--json", cwd=root)
    try: counts = json.loads(js)
    except ValueError: return 0
    out = raw.strip()
    if not counts.get("count"): return 0
    key = CACHE / "stop" / hashlib.sha1(f"{root}:{d.get('session_id', '')}".encode()).hexdigest()
    digest = hashlib.sha1(out.encode()).hexdigest()
    if key.is_file() and key.read_text() == digest: return 0
    key.parent.mkdir(parents=True, exist_ok=True); key.write_text(digest)
    print(json.dumps({"decision": "block", "reason": f"ffcode lint on your diff; fix what is yours, mention legacy:\n{out}"}))
    return 0


def _settings_path(project):
    return (Path.cwd() / ".claude" / "settings.json") if project else Path.home() / ".claude" / "settings.json"


def _ours(entry):
    return any(str(FF) in h.get("command", "") and (" hook " in h.get("command", "")) for h in entry.get("hooks", []))


def installed():
    """'user', 'project' or None: where the ffcode hooks are registered."""
    for scope, p in (("user", _settings_path(False)), ("project", _settings_path(True))):
        try: data = json.loads(p.read_text())
        except (OSError, ValueError): continue
        if any(_ours(e) for ev in EVENTS for e in data.get("hooks", {}).get(ev, [])): return scope
    return None


def hint_due():
    """True at most once a week, unless hooks are installed or FFCODE_NO_HOOKS_HINT is set."""
    if os.environ.get("FFCODE_NO_HOOKS_HINT") or installed(): return False
    f = CACHE / "hooks-hint"
    import time
    if f.is_file() and time.time() - f.stat().st_mtime < 7 * 24 * 3600: return False
    f.parent.mkdir(parents=True, exist_ok=True); f.write_text("1")
    return True


HINT = "ffcode hooks are not installed: tell the user to run `ff hooks install` once (or `! ff hooks install` in this prompt), then open a new session. It makes the update check, map refresh and the lint at the end of each turn automatic."


def install(project, remove):
    p = _settings_path(project)
    data = json.loads(p.read_text()) if p.is_file() else {}
    if p.is_file(): shutil.copy(p, str(p) + ".bak")
    hooks = data.setdefault("hooks", {})
    for ev, sub in EVENTS.items():
        kept = [e for e in hooks.get(ev, []) if not _ours(e)]
        if not remove: kept.append({"hooks": [{"type": "command", "command": f"{FF} {sub}", "timeout": 60}]})
        if kept: hooks[ev] = kept
        else: hooks.pop(ev, None)
    if not hooks: data.pop("hooks")
    p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(data, indent=2) + "\n")
    print(f"{'removed from' if remove else 'installed in'} {p}" + ("" if remove else " (new session needed)")); return 0


def git_hooks(remove):
    root = find_root()
    rc, out = git(["rev-parse", "--git-path", "hooks"], root)
    if rc: print("not a git repository"); return 1
    hdir = (root / out.strip()) if not Path(out.strip()).is_absolute() else Path(out.strip())
    block = f"{MARK[0]}\ncommand -v ff >/dev/null 2>&1 && [ -d {DIRNAME} ] && (ff map >/dev/null 2>&1 &)\n{MARK[1]}\n"
    for name in ("post-merge", "post-checkout", "post-rewrite"):
        f = hdir / name; text = f.read_text() if f.is_file() else ""
        if MARK[0] in text:
            a, b = text.index(MARK[0]), text.index(MARK[1]) + len(MARK[1]) + 1
            text = text[:a] + text[b:]
        if not remove: text = (text if text else "#!/bin/sh\n") + ("" if not text or text.endswith("\n") else "\n") + block
        if remove and text.strip() in ("", "#!/bin/sh"): f.unlink(missing_ok=True); continue
        hdir.mkdir(parents=True, exist_ok=True); f.write_text(text); f.chmod(f.stat().st_mode | stat.S_IXUSR)
    print(f"map refresh {'removed from' if remove else 'installed in'} {hdir}"); return 0


def main():
    kind, a = sys.argv[1], sys.argv[2:]
    if kind == "hook" and a[:1] == ["session-start"]: return session_start()
    if kind == "hook" and a[:1] == ["stop"]: return stop()
    if kind == "hooks" and a[:1] == ["install"]: return install("--project" in a, "--remove" in a)
    if kind == "hooks" and a[:1] == ["status"]:
        s = installed(); print(f"hooks: installed ({s})" if s else "hooks: not installed (ff hooks install)"); return 0 if s else 1
    if kind == "hooks" and a[:1] == ["git"]: return git_hooks("--remove" in a)
    print(__doc__); return 2
