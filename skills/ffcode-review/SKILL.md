---
name: ffcode-review
description: Review a diff, branch, PR or set of files as a demanding colleague applying Federico's checklist - structure, duplicated logic, error handling, comments, tests, naming, security, cross-repo contracts - after the mechanical scripts have pre-filtered the obvious. Output is a ranked findings list with rule ids, in the terminal or as a file. Use when the user says "fai una review", "rivedi il diff", "controlla come un collega", "review this PR", "cosa non va in questo codice", beyond a simple run of the checks.
---

# ffcode-review

`FF="python3 ~/.claude/skills/ffcode-style/scripts/ffcode.py"`

1. Scope: the diff vs base (`git diff <base>...HEAD`), a PR (`gh pr diff N`), or the files named. Start with `git diff --stat`; read hunks, not whole files, unless a hunk cannot be judged without its function.
2. Run `$FF check --changed` first. Its findings are not repeated in prose; cite them by rule id and count. Read `.ffcode/context.md` and `style.md` (deviations are not findings).
3. Judge against `checklist.md` `[judge]` rules, in this order of value: wrong behaviour/edge cases and security (P2, E1, E3) → duplicated or misplaced logic (S1, S2, S4) →
   tests missing or not pinning the rule (T1, C6) → cross-repo contract and docs drift (G3, G4; use `ffcode-workspace contracts`) → naming, comments, size (N, C, S6).
   For each suspected defect, check it in the code before reporting: no finding without a file:line you read.
4. Report, ranked, max ~15 items: `[severity] rule-id file:line — problem — suggested fix (one line)`. Severity: **blocker** (wrong/insecure/data-loss), **major** (rule S/E/T broken),
   **minor** (style). Then "Good" in ≤ 3 lines only if something is worth keeping. No praise padding, no restating the diff.
5. UI in the diff: add the UI view after `uilint`/OFF* hits: contract conformance, reuse of existing components (`ui components`), states, a11y, copy (`ffcode-frontend/references/build.md`).
6. Do not edit. If the user wants the fixes applied, hand over to `ffcode-write` with the findings list.
