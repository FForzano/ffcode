"""Keep a project's ffcode setup complete and current without anyone asking for it.
  ff sync [--init] [--quick] [--refresh] [--json] [--dismiss ID]
Runs at the start of every skill (`ff orient`), on every prompt (UserPromptSubmit hook) and at session start. Idempotent and cheap:
a fingerprint (HEAD + dirty files and their mtimes) decides whether anything is stale.
  creates .ffcode/ when a skill is used in a repo without it (--init; the hook only does it when the prompt names an ffcode skill),
  upgrades an older layout, installs the git hooks and adds Claude Code hooks missing from an installation the user already made,
  refreshes the map and indexes when the code changed (quick mode: in the background, so a prompt never waits for it),
  and lists NEEDS: what only the developer can decide (architecture layers, entry points, side-effect libraries, CLAUDE.md migration,
  test command). The skill asks the developer, runs the command shown, and the need disappears because it is derived from the files.
`--dismiss ID` hides a need for this machine."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from common import DIRNAME, find_root, git, load_config, run

FF = Path(__file__).resolve().parent / "ff"
BG_LOCK_SECONDS = 180


def _state_path(root: Path) -> Path:
    return root / DIRNAME / "cache" / "sync.json"


def _load(root: Path) -> dict:
    try: return json.loads(_state_path(root).read_text())
    except (OSError, ValueError): return {}


def _save(root: Path, st: dict):
    p = _state_path(root)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp"); tmp.write_text(json.dumps(st)); tmp.replace(p)
    except OSError: pass


def fingerprint(root: Path) -> str:
    """HEAD + the dirty files with their mtimes: changes on a commit, a pull, a checkout and on every uncommitted edit."""
    _, head = git(["rev-parse", "HEAD"], root)
    rc, status = git(["status", "--porcelain", "-z", "--untracked-files=all"], root)
    code = "".join(f"{p.name}{p.stat().st_mtime_ns}" for p in sorted(Path(__file__).resolve().parent.glob("*.py")))   # the skill itself changed
    parts = [head.strip(), status, code]
    if rc == 0:
        for ent in status.split("\0"):
            path = ent[3:] if len(ent) > 3 else ""
            if path and not path.startswith(DIRNAME + "/"):
                try: parts.append(f"{path}:{(root / path).stat().st_mtime_ns}")
                except OSError: pass
    else:
        from common import tracked_files
        for f in tracked_files(root):
            try: parts.append(f"{f}:{(root / f).stat().st_mtime_ns}")
            except OSError: pass
    return hashlib.sha1("\n".join(parts).encode()).hexdigest()[:16]


# ---- needs: derived from files, so answering them is what makes them go away -----------------------------------------

def compute_needs(root: Path) -> list[dict]:
    needs = []
    d = root / DIRNAME
    for legacy in ("CLAUDE.md", "AGENTS.md"):
        f = root / legacy
        if f.is_file():
            lines = [x.strip() for x in f.read_text(errors="replace").splitlines() if x.strip()]
            if lines and not all(x.startswith("@.ffcode/") for x in lines):
                needs.append({"id": "migrate-context", "msg": f"{legacy} holds project context that is not in .ffcode/context.md",
                              "cmd": "follow ffcode-init step 3 (ask the user to confirm the move)"})
                break
    try:
        import arch
        import arch_infer
        ar = arch.load(root)
        o, ans = arch_infer.options(root), arch_infer.load_answers(root)
        model = arch_infer.analyze(root, o, ans)
        if model and not (ar and ar.get("layer")):
            needs.append({"id": "architecture", "msg": f"the code has {len(model['layers'])} {'packages' if model['style'] == 'packages' else 'recurring layers'} but .ffcode/architecture.toml is empty",
                          "cmd": "ff arch infer --interview, ask the questions, then ff arch infer --answer id=value ... --write"})
        elif model and json.loads(arch_infer.interview(model, ans, o["max_questions"]))["questions"]:
            needs.append({"id": "architecture-questions", "msg": "the architecture draft has open questions", "cmd": "ff arch infer --interview"})
    except Exception:
        pass
    try:
        import flow
        needs += flow.needs(root)
    except Exception:
        pass
    cmds = load_config(root).get("commands", {}) if (d / "config.toml").is_file() else {}
    if not any(cmds.get(k) for k in ("test", "lint", "format_check", "typecheck", "build")):
        needs.append({"id": "commands", "msg": "no format/lint/typecheck/test/build command is configured in .ffcode/config.toml",
                      "cmd": "ffcode-init step 2: find the real commands with the user, run each once"})
    return needs


# ---- steps --------------------------------------------------------------------------------------------------------

def _ensure_layout(root: Path, log: list):
    import upgrade
    from common import SCHEMA
    if upgrade.version(root) < SCHEMA and not os.environ.get("FFCODE_NO_AUTO_UPGRADE"):
        _, lg = upgrade.upgrade(root, False, False, quiet=True)
        log.append(f".ffcode/ upgraded to schema {SCHEMA}")


def _ensure_git_hooks(root: Path, log: list):
    rc, out = git(["rev-parse", "--git-path", "hooks"], root)
    if rc: return
    hdir = Path(out.strip()) if Path(out.strip()).is_absolute() else root / out.strip()
    import hooks
    f = hdir / "post-merge"
    if f.is_file() and hooks.MARK[0] in f.read_text(): return
    cwd = os.getcwd()
    try:
        os.chdir(root); hooks.git_hooks(False)
        log.append("git hooks installed (map refresh after pull/checkout/rebase)")
    except OSError: pass
    finally: os.chdir(cwd)


def _ensure_claude_hooks(log: list):
    """Only completes an installation the user already made (a new hook event shipped after they installed)."""
    import hooks
    scope = hooks.installed()
    if not scope: return
    p = hooks._settings_path(scope == "project")
    try: data = json.loads(p.read_text())
    except (OSError, ValueError): return
    missing = [ev for ev in hooks.EVENTS if not any(hooks._ours(e) for e in data.get("hooks", {}).get(ev, []))]
    if missing:
        hooks.install(scope == "project", False)
        log.append(f"Claude Code hooks completed ({', '.join(missing)}): active from the next session")


def _spawn_refresh(root: Path, st: dict):
    if time.time() - st.get("refreshing", 0) < BG_LOCK_SECONDS: return
    st["refreshing"] = time.time(); _save(root, st)
    try: subprocess.Popen([str(FF), "sync", "--refresh", "--root", str(root)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError: pass


def refresh(root: Path, st: dict, fp: str):
    """The slow part: map + indexes + needs, then record the fingerprint."""
    _ff = lambda *a: run([str(FF), *a, "--root", str(root)], cwd=root)
    _ff("map")
    st["needs"] = compute_needs(root)
    st["fp"] = fp; st["refreshing"] = 0; st["t"] = time.time()
    _save(root, st)


def sync(root: Path, init: bool = False, quick: bool = False, session: str | None = None, force: bool = False):
    """-> (log lines, needs to show). `quick` never blocks on the slow refresh."""
    log = []
    d = root / DIRNAME
    if not d.is_dir():
        if not init: return log, []
        rc, out = run([str(FF), "init", "--root", str(root)], cwd=root)
        if rc != 0: return [f"could not create {DIRNAME}/: {out.strip()[:120]}"], []
        log.append(f"{DIRNAME}/ created for {root.name} (new files are uncommitted: tell the user once)")
    _ensure_layout(root, log)
    if (root / ".git").exists(): _ensure_git_hooks(root, log)
    _ensure_claude_hooks(log)
    st = _load(root)
    fp = fingerprint(root)
    stale = force or st.get("fp") != fp or not (d / "map.md").is_file()
    if stale:
        if quick and not force and (d / "map.md").is_file(): _spawn_refresh(root, st)
        else: refresh(root, st, fp)
    st = _load(root)
    needs = [n for n in st.get("needs", []) if n["id"] not in st.get("dismissed", [])]
    if session is not None:                                               # a hook: say each set of needs once per session
        key = hashlib.sha1(json.dumps([n["id"] for n in needs]).encode()).hexdigest()[:10]
        seen = st.setdefault("announced", {})
        if seen.get(session) == key: needs = []
        else:
            seen[session] = key
            for k in list(seen)[:-20]: seen.pop(k, None)
            _save(root, st)
    return log, needs


def format_output(log: list, needs: list) -> str:
    out = []
    if log: out.append("ffcode sync: " + "; ".join(log))
    if needs:
        out.append("ffcode NEEDS (ask the developer, run the command shown; skip with `ff sync --dismiss ID`):")
        out += [f"  - [{n['id']}] {n['msg']} -> {n['cmd']}" for n in needs]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--root"); ap.add_argument("--init", action="store_true"); ap.add_argument("--quick", action="store_true")
    ap.add_argument("--refresh", action="store_true"); ap.add_argument("--json", action="store_true"); ap.add_argument("--dismiss")
    a = ap.parse_args()
    root = find_root(a.root)
    if a.dismiss:
        st = _load(root); st.setdefault("dismissed", []); st["dismissed"] = sorted(set(st["dismissed"]) | {a.dismiss}); _save(root, st)
        print(f"dismissed {a.dismiss}"); return 0
    if a.refresh:
        refresh(root, _load(root), fingerprint(root)); return 0
    log, needs = sync(root, a.init, a.quick, None, force=False)
    if a.json: print(json.dumps({"log": log, "needs": needs})); return 0
    text = format_output(log, needs)
    print(text or "ffcode sync: up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
