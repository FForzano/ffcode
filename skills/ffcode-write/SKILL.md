---
name: ffcode-write
description: Implement a feature, fix a bug or refactor in Federico's coding style, using .ffcode/ context and the repo map to spend few tokens - plan briefly, reuse existing code, small verified steps with tests, then ffcode check. Language-agnostic with per-language notes. Use when the user asks to implement, add, fix, refactor, "scrivi", "aggiungi", "correggi", "implementa", "rifattorizza" code in a project, even without naming the skill.
---

# ffcode-write

`FF="python3 ~/.claude/skills/ffcode-style/scripts/ffcode.py"`; rules: `ffcode-style/references/checklist.md` + `lang/<language>.md` of the files touched.

## Protocol
1. **Orient cheaply.** No `.ffcode/` → offer `ffcode-init` (do not block on it). Else read `context.md`, `style.md`, `state.md`, `map.md`. Multi-repo
   product and the change crosses a repo boundary (API, schema, env var, event) → `ffcode-workspace` first.
2. **Locate, don't sweep.** `$FF find` for the symbols involved; read only the needed ranges. Look for an existing function that does it (S2, S3) before writing.
3. **Plan in ≤ 6 lines** when the change touches more than one file or a public contract: files, the test that will prove it, the risk. Ask the user only
   on a business rule or an irreversible action. Trivial change: skip the plan.
4. **Test first for bugs** (reproduce with a failing test), **test with the code for features** (T1). Run the narrowest test after each step.
5. **Implement in the project's idiom** (neighbouring files win over general taste). Smallest diff; unrelated problems are listed at the end, not fixed.
6. **Close:** `$FF check --changed`; fix what it reports; walk the `[judge]` rules once against your own diff (S1, S2, E1, C1, C6, G4 are the usual misses).
   Docs/OpenAPI/README updated in the same change (G4).
7. Update `.ffcode/state.md` or add a `decisions/NNNN-title.md` (5–10 lines: context, decision, consequences) only for durable facts.
8. Summary to the user: what changed (files), what was verified (commands and result), what was not, follow-ups. Do not commit unless asked (`ffcode-commit`).
