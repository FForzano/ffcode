---
name: ffcode-check
description: Mechanical pass/fail of code changes, no edits: runs the project's format, lint, typecheck, test, build and ffcode lint and returns a short report. Use for "controlla", "check", "lancia i test", "è tutto a posto?", "prima del commit".
allowed-tools: Bash(ff:*)
context: fork
model: haiku
---

# ffcode-check

`ff` (CLI of ffcode-core). First `ff sync --quick` (completes `.ffcode/`, refreshes caches); a NEEDS line is for the developer: mention it, don't block.

1. Scope: default is the diff against the base (`--changed`, base from `[check] base`); `--staged` before a commit; no flag = the whole repo
   (expect legacy noise; report counts only, `lint --summary`).
2. Run `ff check --changed` (add `--only test` or `--only lint,typecheck` to narrow). Tool output is compressed to error lines and the tail.
   With `--changed`/`--staged` the test step runs only the tests covering the diff (`[commands] test_one`); without `test_one` it runs the whole suite and prints a `note:` saying so: pass that note on, it tells the developer to configure `test_one`.
   Exit codes: 0 OK, 1 FAIL, 3 UNVERIFIED (a step timed out). Timeouts are `[check] test_timeout` (whole suite, 900 s) and `scoped_test_timeout` (scoped run, 300 s).
3. If a configured command cannot run (container down, missing tool), report that in one line and continue; never substitute a guess.
4. Report (≤ 12 lines): **OK/FAIL/UNVERIFIED**; a `TIMEOUT` step is UNVERIFIED, never FAIL (nothing was verified, no test failed): name the step, say what was not covered and do not call the change tested; one line per failing step with the first relevant error lines, lint findings grouped by rule id with
   counts and first locations, skipped steps. Close with: "This covers the [auto] rules of the checklist; run ffcode-review for the rest."
5. Do not fix anything here. If the user asks to fix, hand over to `ffcode-write`.

Findings recorded in `.ffcode/baseline.json` or waived in `.ffcode/rules.toml` are already hidden (the lint line says how many). Findings on lines the diff did not touch are legacy: mention the count, do not list them.
