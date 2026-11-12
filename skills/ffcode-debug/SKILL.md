---
name: ffcode-debug
description: Systematic debugging and triage - compress a log or stack trace to the frames in this repo, reproduce with a failing test, narrow down with git bisect on the project's test command, fix the cause not the symptom, and pin it with a regression test. Use when the user reports a bug, an error message, a failing test or CI run, a regression ("prima funzionava"), or says "debugga", "perché fallisce", "trova il commit che l'ha rotto", "analizza questo log".
---

# ffcode-debug

`FF="python3 ~/.claude/skills/ffcode-style/scripts/ffcode.py"`

1. **Compress the evidence, don't paste it.** `$FF debug log FILE` (or `cmd 2>&1 | $FF debug log -`): error lines, frames inside this repo, tail. Work from that.
2. **Reproduce first.** Smallest failing test or command (`[commands] test` narrowed to one test). No reproduction → say what is missing; ask for the input/env, don't guess a fix.
3. **Localise.** `$FF find` / `$FF refs NAME` to the code in the frames; read those ranges only. Regression with a known good commit → `$FF debug bisect GOOD [--cmd "<narrow test>"]` (needs a clean tree; resets afterwards).
4. **State the cause** in one or two sentences with `file:line` before touching code; check the hypothesis (a log line, an assertion), not just plausibility.
5. **Fix the cause** with the smallest diff (E1/E3 often: a silently ignored input). Look with `refs` for the same pattern elsewhere and list, don't fix, other occurrences.
6. **Pin it:** the reproducing test stays as a regression test named after the rule (C6, T1). `$FF check --changed`.
7. Report: cause, fix, test added, what was verified, similar spots found. Durable lessons → `.ffcode/context.md` (one line) or an ADR (`$FF adr`).
