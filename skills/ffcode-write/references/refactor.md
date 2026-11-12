# Refactoring (loaded by ffcode-write for restructuring tasks)

`FF="python3 ~/.claude/skills/ffcode-style/scripts/ffcode.py"`; rules S1–S6, N1–N3 of `checklist.md`.

1. **Scope and goal in one line** (which rule it serves: S2 duplicate, S6 size, S1 mixed responsibilities). Refactor ≠ feature: no behaviour change, no unrelated cleanup; found extras are listed at the end.
2. **Find the target with data:** `$FF lint --rules DUP,FUNC,FILE,PARAM [--changed]`, `$FF find NAME`, `$FF refs NAME` (usages by file = the blast radius; for a public contract also `ffcode-workspace`).
3. **Safety net first.** Run `$FF check --only test`. Code to change not covered → add characterisation tests that pin today's behaviour (also the odd cases), committed separately.
4. **One transformation per step** (extract function, move, rename, replace duplicate by the single definition). After each: narrowest test → continue; full `$FF check --changed` every few steps. A red step is reverted or fixed before moving on, never stacked.
5. **Rename:** `refs` before and after (zero leftovers, including strings, config, docs, other repos' contracts); no compatibility shims unless a published contract requires it.
6. **Dedup:** the surviving definition is the one in the right layer (S1); callers import it; delete the copies, don't leave wrappers. Re-run `lint --rules DUP`.
7. Close: before/after numbers (lint counts, lines), tests green, suggested commit split (`ffcode-commit`: one logical step per commit, "refactor(scope): ...").
