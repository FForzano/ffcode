---
name: ffcode-init
description: Adopt a repo into ffcode: detect stack and commands, create .ffcode/, migrate CLAUDE.md into context.md, first map. Use for "inizializza ffcode", "adotta questo repo", "migra il CLAUDE.md", or a repo without .ffcode/.
allowed-tools: Bash(ff:*)
---

# ffcode-init

`ff` (CLI of ffcode-core)

0. `ff sync` already ran and may have created `.ffcode/`; this is the guided version (confirmations, CLAUDE.md migration, commands).
1. `ff init --dry-run`, show the detected languages and commands in two lines, then `ff init`.
2. Fix `config.toml` with the user only where detection is wrong or silent: commands that run in a container (`docker compose exec web ...`),
   line length to the formatter's, `[commit] style` (look at `git log --format=%s -20`: `feat(scope):` → conventional, plain sentences → imperative).
   Run each configured command once to make sure it works; a command that cannot run is commented out, not left broken.
3. **Context migration** (CLAUDE.md / AGENTS.md exist): ask for confirmation, then
   - move the file to `.ffcode/context.md` verbatim (`git mv`), nothing summarised or dropped;
   - write a new `CLAUDE.md` that only imports: `@.ffcode/context.md`, `@.ffcode/style.md`, `@.ffcode/state.md`;
   - if the content mixes project facts with general style rules already in `ffcode-core/references/checklist.md`, list those
     passages as proposals for `style.md`/removal; do not cut them without a yes.
4. Seed `style.md` with deviations that the existing files state explicitly (e.g. "comments in Italian", "no ABC outside plugin seams"), citing rule ids.
5. If the product spans several repos, hand over to `ffcode-workspace`.
5a. Layered code or packages (library, pipeline, science code: packages are the layers, observed imports are allowed, `--packages` forces it): `ff arch infer --interview` prints the ambiguous cases as closed questions (JSON: id, question, default, options). Ask them with AskUserQuestion (at most four per call, default first, Recommended), then `ff arch infer --answer id=value ... --write`: answers go in `.ffcode/arch-answers.toml` (committed), later `--write --force` rebuilds the same file. `--check` shows what the draft flags today (and cycles). Tune `suffixes`, `exclude`, `merge`, `mode` under `[infer]` in config.toml; add `style`, `summary`, `[conventions]` by hand.
5b. Legacy repo with many lint findings: offer `ff lint --baseline` (and `ff uilint --baseline`) so only new problems show; project-specific rule exceptions go in `rules.toml` with a reason.
6. `ff config --validate`, `ff map`, `ff hooks git` (refreshes the map after pull/checkout/rebase), then report: files created, commands detected, what was migrated, what needs the user. Do not commit.
