---
name: ffcode-init
description: Adopt a repository into ffcode - detect languages and commands, create the .ffcode/ folder (config, context, style, state, gitignore), migrate the existing CLAUDE.md/AGENTS.md into .ffcode/context.md leaving a pointer, and generate the first map. Use when the user says "inizializza ffcode", "adotta questo repo", "setup .ffcode", "migra il CLAUDE.md", or starts the ffcode skills in a repo that has no .ffcode/.
---

# ffcode-init

`FF="python3 ~/.claude/skills/ffcode-style/scripts/ffcode.py"`

1. `$FF init --dry-run`, show the detected languages and commands in two lines, then `$FF init`.
2. Fix `config.toml` with the user only where detection is wrong or silent: commands that run in a container (`docker compose exec web ...`),
   line length to the formatter's, `[commit] style` (look at `git log --format=%s -20`: `feat(scope):` → conventional, plain sentences → imperative).
   Run each configured command once to make sure it works; a command that cannot run is commented out, not left broken.
3. **Context migration** (CLAUDE.md / AGENTS.md exist): ask for confirmation, then
   - move the file to `.ffcode/context.md` verbatim (`git mv`), nothing summarised or dropped;
   - write a new `CLAUDE.md` that only imports: `@.ffcode/context.md`, `@.ffcode/style.md`, `@.ffcode/state.md`;
   - if the content mixes project facts with general style rules already in `ffcode-style/references/checklist.md`, list those
     passages as proposals for `style.md`/removal; do not cut them without a yes.
4. Seed `style.md` with deviations that the existing files state explicitly (e.g. "comments in Italian", "no ABC outside plugin seams"), citing rule ids.
5. If the product spans several repos, hand over to `ffcode-workspace`.
6. `$FF map`, then report: files created, commands detected, what was migrated, what needs the user. Do not commit.
