# ffcode

Claude Code skills for programming in Federico's style: language-agnostic rules, scripts for everything mechanical (fewer tokens, more
consistency), a per-project `.ffcode/` folder, and multi-repo support.

| Skill | Purpose |
|---|---|
| `ffcode-style` | The shared core, also the repo map (`map`, `find`, `refs`) and decision records (`adr`): `references/checklist.md` (rules with ids, `[auto]`/`[judge]`), `principles.md`, `lang/` (Python, PHP, TS/React, shell/AWS, MATLAB, HTML/CSS), `scripts/ffcode.py` (CLI: `init map find lint check commitmsg workspace`), `templates/`, `tests/run.sh`. Edit the style here only. |
| `ffcode-init` | Adopt a repo: detect stack/commands, create `.ffcode/`, migrate CLAUDE.md into `.ffcode/context.md` (CLAUDE.md becomes `@` imports), generate the first map. |
| `ffcode-write` | Implement/fix/refactor in the style: orient from `.ffcode/`, reuse, test, small steps, `check`. Loads `references/refactor.md` for restructuring and `tests.md` (diff coverage, `failwithout`, optional mutation on critical areas) for tests. UI is detected from the files touched and loads `references/ui*.md`: a machine-readable design contract (`.ffcode/design.toml`) generates the tokens (`ui sync`), is enforced by `uilint` (`OFFCOLOR/SIZE/SPACE/RADIUS`, a11y/motion/i18n leads) and checked (`ui palette`); `ui context` is a ~40-line digest; `ui components`/`ui new` for reuse and scaffolding. |
| `ffcode-check` | Mechanical pass/fail: configured format/lint/typecheck/test/build + ffcode lint, compressed output. No edits. |
| `ffcode-review` | Review a diff as a demanding colleague, ranked findings with rule ids, after the scripts pre-filter. |
| `ffcode-commit` | Logical commits, validated messages, PR description. |
| `ffcode-workspace` | Multi-repo products and their releases (`release`: commits, migrations, contract changes per repo, deploy order): `.ffcode/workspace.toml`, clones under `.ffcode/repos` (git-ignored), dependency graph, contract-change tracking. |
| `ffcode-debug` | Compress logs/traces to repo frames, reproduce with a failing test, `git bisect` on the test command, fix the cause, pin it. |

## Install

```bash
./install.sh            # symlink into ~/.claude/skills   (--copy, --update, --status, --uninstall)
skills/ffcode-style/tests/run.sh   # smoke tests
```
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
