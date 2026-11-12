---
name: ffcode-review
description: Review a diff, branch or PR as a demanding colleague using Federico's checklist (structure, duplication, errors, tests, security, cross-repo contracts); ranked findings with rule ids. Use for "fai una review", "rivedi il diff", "review this PR".
allowed-tools: Bash(ff:*)
---

# ffcode-review

`ff` (CLI of ffcode-core)

1. Scope: the diff vs base (`git diff <base>...HEAD`), a PR (`gh pr diff N`), or the files named. Start with `git diff --stat`; read hunks, not whole files, unless a hunk cannot be judged without its function.
2. Run `ff report review --check` first (scope, hotspots, lint counts, contract files; use its skeleton for the output). Its findings are not repeated in prose; cite them by rule id and count. Run `ff orient --no-map` (deviations in `rules.toml`/`style.md` are not findings; `ff rules --judge` lists them). `ff hotspots` says where problems concentrate; ARCHNAME/ARCHDEP findings (S7) are architecture drift.
3. Judge against `ff rules --judge`, in this order of value: wrong behaviour/edge cases and security (P2, E1, E3) → duplicated or misplaced logic (S1, S2, S4) →
   tests missing or not pinning the rule (T1, C6) → cross-repo contract and docs drift (G3, G4; use `ffcode-workspace contracts`) → naming, comments, size (N, C, S6).
   For each suspected defect, check it in the code before reporting: no finding without a file:line you read.
4. Report, ranked, max ~15 items: `[severity] rule-id file:line — problem — suggested fix (one line)`. Severity: **blocker** (wrong/insecure/data-loss), **major** (rule S/E/T broken),
   **minor** (style). Then "Good" in ≤ 3 lines only if something is worth keeping. No praise padding, no restating the diff.
5. UI in the diff: add the UI view after `uilint`/OFF* hits: contract conformance, reuse of existing components (`ui components`), states, a11y, copy (`ffcode-write/references/ui-build.md`).
6. Do not edit. If the user wants the fixes applied, hand over to `ffcode-write` with the findings list.
