---
name: ffcode-style
description: Federico's coding style and the shared toolbox of the ffcode skills - checklist of rules (structure, single source of truth, errors, comments, tests, git), per-language notes (Python, PHP, TypeScript/React, shell/Terraform/AWS, MATLAB, HTML/CSS), the per-project .ffcode/ folder (config, context, style deviations, map, state, decisions) and the ffcode CLI (init, map, find, lint, check, commitmsg, workspace). Use when the user asks what the coding rules are, how to structure code in this project, what rule applies, or to run ffcode lint/map/find. The other ffcode-* skills build on this one.
---

# ffcode-style

Rules in `references/checklist.md` (read first; ids S1, D2, E3, ... are cited in reviews and in `.ffcode/style.md`), working
principles in `references/principles.md`, language notes in `references/lang/<language>.md` (read only those of the project:
`[project] languages` in `.ffcode/config.toml`). Rules are language-agnostic; the language file only maps them to the idiom.

## The CLI (stdlib Python ≥ 3.11, no install)

```bash
FF="python3 ~/.claude/skills/ffcode-style/scripts/ffcode.py"
$FF init                    # create .ffcode/ (detects stack and commands), never overwrites
$FF map                     # regenerate .ffcode/map.md + symbol index (layout, entry points, symbols)
$FF find NAME               # where is a function/class/component? file:line, instead of grepping the tree
$FF lint [--changed|--staged] [--summary]   # LEN FUNC FILE PARAM DEBUG CODE TODO CATCH SECRET CONFLICT DUP
$FF check [--changed]       # configured format/lint/typecheck/test/build + ffcode lint, compressed output
$FF commitmsg "feat(x): ..."   # validate against [commit] style
$FF refs NAME               # all usages of a name by file (rename/impact)
$FF diffcov [--run] [--min N]   # added lines no test ran (Cobertura/Clover/lcov); `check --coverage` includes it
$FF failwithout [--cmd CMD]     # do the tests fail when the production change is reverted? (restores files)
$FF mutate [--list]             # optional mutation testing, only on changed files in [mutation] critical
$FF untested [--base REF]   # fallback: symbols added in the diff that no test mentions (heuristic)
$FF debug log FILE|-        # compress a log/trace; `debug bisect GOOD` runs git bisect on the test command
$FF adr "Title"             # new decision record in .ffcode/decisions
$FF ui context|init|sync|palette|components|new   # design contract tooling (ffcode-write, references/ui.md)
$FF uilint [--changed]         # UI a11y/tokens/motion/i18n leads + OFF* conformance to the design contract
$FF uitokens                  # inventory of colours/sizes/radii/shadows/spacing in use
$FF workspace status|sync|graph|contracts   # multi-repo, see ffcode-workspace
$FF release [--from B --to M]   # per-repo commits/migrations/contract changes + deploy order
```
All take `--root DIR`; the root is the nearest ancestor with `.ffcode/`, else the git top level.

## `.ffcode/` in a project

| File | Committed | Content |
|---|---|---|
| `config.toml` | yes | languages, `[commands]` (format_check, lint, typecheck, test, coverage, build; wrap docker/ssh here), `[limits]`, `[commit]`, `[check]`, `[coverage]` (report, min), `[mutation]` (critical globs, command) |
| `context.md` | yes | what the project is, architecture, invariants, command list (migrated from CLAUDE.md) |
| `style.md` | yes | deviations from the checklist by rule id + project conventions |
| `decisions/` | yes | one short ADR per durable decision |
| `state.md` | no | personal work in progress |
| `design.toml` | yes | UI projects: machine-readable design contract (colour roles, scales, fonts, motion) |
| `workspace.toml` | yes | other repos of the product, roles, dependencies, contracts |
| `map.md`, `cache/`, `repos/`, `state.md` | no (`.ffcode/.gitignore`) | generated map; caches; clones of the other repos |

Token rule: read `context.md`, `style.md`, `state.md`, then `map.md`; use `find` for the rest. Do not list or grep the whole tree first.

To change a rule for all projects, edit `references/` here; for one project, `.ffcode/style.md`.
