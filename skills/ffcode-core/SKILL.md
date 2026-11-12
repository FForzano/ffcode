---
name: ffcode-core
description: Federico's coding rules and shared toolbox: checklist, per-language notes, the .ffcode/ folder and the ff CLI (orient, map, find, rules, lint, adr). Use for "quali sono le regole", "mappa il repo", "dove si trova X", "annotiamo questa decisione", ADR. Base of the other ffcode-* skills.
allowed-tools: Bash(ff:*)
---

# ffcode-core

Rules in `references/checklist.md` (read through `ff rules --judge`; ids S1, D2, ... are cited in reviews and `.ffcode/rules.toml`), working
principles in `references/principles.md`, language notes in `references/lang/<language>.md` (read only those of the project:
`[project] languages` in `.ffcode/config.toml`). Rules are language-agnostic; the language file only maps them to the idiom.

## Updates and hooks
`ff hooks install` (once per machine; `ff hooks status` checks it; if `ff orient` says they are missing, tell the user to run it; `--project` for one repo) adds two Claude Code hooks: SessionStart (weekly update notice, refreshes a stale map, one status line)
and Stop (`ff lint --changed` on the diff, blocks once per distinct result). On an `UPDATE_AVAILABLE` notice ask the user, then `ff update-check --apply` only on a yes.
Without the hooks run `ff update-check` yourself at session start. `FFCODE_NO_UPDATE_CHECK=1` disables the check.

An older project is upgraded by itself: the first `ff` command (or the SessionStart hook) runs `ff upgrade` without git hooks, prints one line on stderr, and the new files stay uncommitted: mention it to the user once. `FFCODE_NO_AUTO_UPGRADE=1` disables it.

## The CLI (stdlib Python ≥ 3.11, no install)
`ff` is `~/.local/bin/ff` (made by `install.sh`; fallback: `python3 ~/.claude/skills/ffcode-core/scripts/ffcode.py`). `ff --help` lists every command; the ones you use most:
```bash
ff orient                  # context + style + state + rules + architecture + map head, one call: start of every task
ff find NAME               # file:line of a symbol or glossary term (ff refs NAME: all usages)
ff rules [--judge]         # rules that need judgment + project deviations + language notes
ff check [--changed]       # configured commands + ffcode lint, compressed
ff tests-for FILE          # tests covering a file (--run executes);  ff hotspots: where to look first
ff arch [show L|new NAME]  # project architecture;  ff pr | report review|summary | commit-plan: text facts from the diff
ff init | upgrade | map | adr "T" | config --validate | commitmsg "..."   # setup and records
```
All take `--root DIR`; the root is the nearest ancestor with `.ffcode/`, else the git top level. Token sizes of the skills: `ff budget`.

## `.ffcode/` in a project
Committed: `config.toml`, `context.md`, `style.md` (conventions), `rules.toml` (deviations the scripts apply), `architecture.toml` (style, layers, naming, allowed imports, conventions; `ff arch`), `baseline.json` (legacy findings), `decisions/`, `glossary.md`, `design.toml`, `workspace.toml`, `contracts.lock`.
Generated and git-ignored: `map.md`, `workspace-map.md`, `cache/` (symbols, tests-map, hotspots), `repos/`, `state.md`. Details of every file: `references/project-files.md`.

Token rule: `ff orient`, then `ff find` for the rest. Do not list or grep the whole tree first.

To change a rule for all projects, edit `references/` here; for one project, `.ffcode/style.md`.

## Navigating with the map (replaces a tree sweep)
`ff orient` shows the head of `.ffcode/map.md` (`ff map` if missing or stale): directories, entry points, commands, symbols per file. Then `ff find NAME` (substring) → `file:line`, and read only that range. `ff refs NAME` for all usages by file. Symbols may be stale: confirm before editing.

## Decisions
Durable choices go in `.ffcode/decisions/NNNN-title.md` (`ff adr "Title"`; fill Context, Decision, Consequences, Alternatives in 5–10 lines; committed). Before re-opening a topic `ff adr --list --rule ID` / `--grep TEXT` (or `decisions/index.md`) and read the matching record; a settled decision is
not re-litigated unless asked or a stated consequence failed. A standing rule is also one line in `style.md`/`context.md`; a superseding record says "Supersedes NNNN". Choosing between options: 2–3 real ones, a recommendation and why; ask only for business facts.
