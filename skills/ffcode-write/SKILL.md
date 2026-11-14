---
name: ffcode-write
description: Implement, fix, refactor or test code (backend, scripts, infra, UI) in Federico's style at low token cost: .ffcode/ context and map, reuse, small verified steps, then ff check. Use for "scrivi", "aggiungi", "correggi", "implementa", "rifattorizza", tests, even without naming the skill.
allowed-tools: Bash(ff:*)
---

# ffcode-write

`ff` (CLI of ffcode-core); rules: `ff rules --judge` (judgment rules + notes of the project's languages; the `[auto]` ones are run by `ff check`).

## Protocol
1. **Orient cheaply.** `ff orient` runs `ff sync` (creates/upgrades `.ffcode/`, refreshes caches) and prints NEEDS: ask the developer first (AskUserQuestion, then the command shown). Multi-repo
   product and the change crosses a repo boundary (API, schema, env var, event) → `ffcode-workspace` first.
2. **Locate, don't sweep.** `ff find` for the symbols involved; `ff flow QUERY` (logic of an endpoint/command), `--impact FILE` (what a change reaches); read only the needed ranges. Look for an existing function that does it (S2, S3) before writing.
3. **Plan in ≤ 6 lines** when the change touches more than one file or a public contract: files, the test that will prove it, the risk. Ask the user only
   on a business rule or an irreversible action. Trivial change: skip the plan.
4. **Tests:** `ff tests-for FILE` names its tests (`--run` executes them); see `references/tests.md` (diff coverage, `failwithout`, optional mutation on critical areas) when tests are requested or the change lacks them. Many similar tests: optional `llmx run test-draft` drafts them; review and run like your own. **Test first for bugs** (reproduce with a failing test), **test with the code for features** (T1). Narrowest test after each step.
5. **UI files involved** (components, pages, styles; or `[check] ui`/`design.toml`): read `references/ui.md` and follow it for those parts (`ui context`, design contract tokens, reuse, states, verification). Backend-only change: skip it.
5b. **Refactor / restructure** (no behaviour change): follow `references/refactor.md` (safety net first, one transformation per step, one commit per step).
6. **Implement in the project's idiom** (new entity: `ff arch new NAME`; imitate `ff arch show LAYER`) (neighbouring files win over general taste). Smallest diff; unrelated problems are listed at the end, not fixed.
7. **Close:** `ff check --changed`; fix what it reports; walk the `[judge]` rules once against your own diff (S1, S2, E1, C1, C6, G4 are the usual misses).
   Docs/OpenAPI/README updated in the same change (G4).
8. Update `.ffcode/state.md` or add a `decisions/NNNN-title.md` (5–10 lines: context, decision, consequences) only for durable facts.
9. Summary to the user (`ff report summary --check` gives the facts; add the not-verified and follow-ups): what changed (files), what was verified (commands and result), what was not, follow-ups. Do not commit unless asked (`ffcode-commit`).
