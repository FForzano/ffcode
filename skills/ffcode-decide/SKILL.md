---
name: ffcode-decide
description: Record and recall durable decisions of a project in .ffcode/decisions as short numbered records (context, decision, consequences, alternatives), and compare options with a recommendation instead of a survey. Use when the user makes or asks for an architectural/product/technical choice, says "annotiamo questa decisione", "perché avevamo scelto X", "ADR", "scegliamo tra A e B", or when a session produced a rule that must outlive it.
---

# ffcode-decide

`FF="python3 ~/.claude/skills/ffcode-style/scripts/ffcode.py"`

- **Recall:** before re-opening a topic, `ls .ffcode/decisions` and read the matching record; a settled decision is not re-litigated unless the user asks or a stated consequence has failed.
- **Choose:** 2–3 real options max, each in 1–2 lines with its cost; give a recommendation and the reason. Ask the user only when it depends on a business fact you cannot read.
- **Record:** `$FF adr "Short title"` creates `NNNN-title.md`; fill it in 5–10 lines: Context, Decision (imperative), Consequences (including what gets harder), Alternatives rejected (one line each). Facts the code states already are not repeated.
- **Promote:** a standing rule goes also as one line in `.ffcode/style.md` (deviation by rule id) or `context.md` (invariant); a decision that supersedes another says "Supersedes NNNN" and the old one gets "Status: superseded by MMMM".
- Records are committed (not git-ignored) and short; narrative, history and meeting notes do not belong here.
