# ffcode

Claude Code skills for programming in Federico's style: language-agnostic rules, scripts for everything mechanical (fewer tokens, more
consistency), a per-project `.ffcode/` folder, and multi-repo support.

| Skill | Purpose |
|---|---|
| `ffcode-core` | The shared core, also the repo map (`map`, `find`, `refs`) and decision records (`adr`): `references/checklist.md` (rules with ids, `[auto]`/`[judge]`), `principles.md`, `lang/` (Python, PHP, TS/React, shell/AWS, MATLAB, HTML/CSS), `scripts/ffcode.py` (CLI: `init map find lint check commitmsg workspace`), `templates/`, `tests/run.sh`. Edit the style here only. |
| `ffcode-init` | Adopt a repo: detect stack/commands, create `.ffcode/`, migrate CLAUDE.md into `.ffcode/context.md` (CLAUDE.md becomes `@` imports), generate the first map. |
| `ffcode-write` | Implement/fix/refactor in the style: orient from `.ffcode/`, reuse, test, small steps, `check`. Loads `references/refactor.md` for restructuring and `tests.md` (diff coverage, `failwithout`, optional mutation on critical areas) for tests. UI is detected from the files touched and loads `references/ui*.md`: a machine-readable design contract (`.ffcode/design.toml`) generates the tokens (`ui sync`), is enforced by `uilint` (`OFFCOLOR/SIZE/SPACE/RADIUS`, a11y/motion/i18n leads) and checked (`ui palette`); `ui context` is a ~40-line digest; `ui components`/`ui new` for reuse and scaffolding. |
| `ffcode-check` | Mechanical pass/fail: configured format/lint/typecheck/test/build + ffcode lint, compressed output. No edits. |
| `ffcode-review` | Review a diff as a demanding colleague, ranked findings with rule ids, after the scripts pre-filter. |
| `ffcode-commit` | Logical commits, validated messages, PR description. |
| `ffcode-workspace` | Multi-repo products and their releases (`release`: commits, migrations, contract changes per repo, deploy order): `.ffcode/workspace.toml`, clones under `.ffcode/repos` (git-ignored), dependency graph, contract-change tracking. |
| `ffcode-debug` | Compress logs/traces to repo frames, reproduce with a failing test, `git bisect` on the test command, fix the cause, pin it. |

## Install

```bash
./install.sh            # symlink into ~/.claude/skills   (--copy, --update, --status, --uninstall); then offers the hooks
ff hooks install        # if you skipped it: update check, map refresh, lint at the end of a turn
skills/ffcode-core/tests/run.sh   # smoke tests
```
### Hooks and updates
**After installing, run `ff hooks install`** (`install.sh` asks and does it for you; `--hooks` / `--no-hooks` skip the question). Without them the update check, map refresh and end-of-turn lint do not run on their own. `ff hooks status` tells whether they are installed; until they are, `ff orient` reminds Claude to tell you, at most once a week (`FFCODE_NO_HOOKS_HINT=1` silences it).
`ff hooks install` (run by you, once per machine; `--project` for one repo, `--remove` undoes it) adds two Claude Code hooks so the routine steps do not depend on Claude remembering them:
- **SessionStart**: weekly update check (silent, offline-safe; if there are new commits Claude lists them and **asks**; only on a yes it runs `update-check --apply`), refreshes a stale `.ffcode/map.md`, one status line. Silent outside `.ffcode/` projects.
- **Stop**: `ff lint --changed` on the diff; blocks once, only when the findings differ from the last report.

Without the hooks, `ffcode-core` tells Claude to run `ff update-check` itself. `ff hooks git` (also run by `ffcode-init`) refreshes the map in the background after pull/checkout/rebase. `FFCODE_NO_UPDATE_CHECK=1` disables the update check.
`install.sh` leaves `<skills dir>/.ffcode-repo` so the repository is found after `--copy` installs too.

### Scripted facts
`lint --json` and `check --json` (machine-readable), `ff config --validate`, `ff pr` / `ff report review|summary` (diff facts into `templates/report-*.md`, only the reasoning is left to write), `ff commit-plan` (proposed commit split).
`tests/consistency.py` keeps `checklist.md` and the lint rules in agreement.

### Project files that scripts read
`.ffcode/architecture.toml` (the project's pattern: layers/object kinds with paths, names, allowed imports, API conventions; `ff arch`, `ff arch new NAME`, lint ARCHNAME/ARCHDEP), `.ffcode/rules.toml` (deviations the scripts apply, with reason and optional ADR), `baseline.json` (known legacy findings), `decisions/index.md` (generated from the ADR headers, `ff adr --list --rule ID`), `glossary.md` (searched by `ff find`), `contracts.lock` (agreed contract versions) and the generated, git-ignored `workspace-map.md`, `cache/tests-map.json` (`ff tests-for`) and `cache/hotspots.json` (`ff hotspots`).

### Aligning existing projects
Automatic: the first `ff` command in an older project (or the SessionStart hook) runs the upgrade by itself (no git hooks), prints one line and leaves the new files uncommitted; `FFCODE_NO_AUTO_UPGRADE=1` turns it off. Manually, `ff upgrade` (`--dry-run` first; `--all ~/dev` for every project under a folder) adds the files and `.gitignore` lines introduced since the project was initialized, refreshes map and indexes, installs the map git hooks, validates and records `.ffcode/version`. It never overwrites content. `ff orient` and the SessionStart hook warn when a project is behind.

### Token budget
`ff budget` shows description / SKILL.md / reference sizes; `ff budget --check` (run by the tests) fails when a limit in `skills/ffcode-core/budget.toml` is exceeded.
Judgment rules only: `ff rules --judge`; one-call orientation: `ff orient`. `ffcode-check` runs in a forked haiku subagent, `ffcode-commit` only on explicit request.

`install.sh` also links the CLI as `~/.local/bin/ff` (`FFCODE_BIN_DIR` to change it; keep that directory in your `PATH`); it points into the installed skill, so every update applies at once, and `--uninstall` removes it.

Needs `python3` ≥ 3.11 (stdlib only), `git`. Open a new Claude Code session afterwards.

## In a project

```
.ffcode/
  config.toml      languages, commands (lint/test/...), limits, commit style      (committed)
  context.md       project context, migrated from CLAUDE.md                      (committed)
  style.md         deviations from the checklist, by rule id                      (committed)
  decisions/                                                                      (committed)
  workspace.toml   other repos of the product                                     (committed)
  state.md  map.md  cache/  repos/                                                 (git-ignored)
```
Start with "inizializza ffcode" (`ffcode-init`). Languages are never hard-wired: `config.toml` carries the commands, `lang/*.md` only maps rules to idioms.
