---
name: ffcode-check
description: Mechanical pass/fail check of code changes, no judgment and no edits - runs the project's configured format, lint, typecheck, test and build commands plus ffcode lint (function/file size, debug leftovers, commented-out code, TODOs, empty catch, secrets, merge markers, duplicated blocks) and returns a short compressed report. Use when the user says "controlla", "check", "lancia i test", "è tutto a posto?", "prima del commit", "verifica il diff", without asking for a review or for code to be written.
---

# ffcode-check

`FF="python3 ~/.claude/skills/ffcode-style/scripts/ffcode.py"`

1. Scope: default is the diff against the base (`--changed`, base from `[check] base`); `--staged` before a commit; no flag = the whole repo
   (expect legacy noise; report counts only, `lint --summary`).
2. Run `$FF check --changed` (add `--only test` or `--only lint,typecheck` to narrow). Tool output is compressed to error lines and the tail.
3. If a configured command cannot run (container down, missing tool), report that in one line and continue; never substitute a guess.
4. Report (≤ 12 lines): **OK/FAIL**, one line per failing step with the first relevant error lines, lint findings grouped by rule id with
   counts and first locations, skipped steps. Close with: "This covers the [auto] rules of the checklist; run ffcode-review for the rest."
5. Do not fix anything here. If the user asks to fix, hand over to `ffcode-write`.

Findings on lines the diff did not touch are legacy: mention the count, do not list them.
