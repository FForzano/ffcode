---
name: ffcode-debug
description: Systematic debugging: compress logs/traces, reproduce with a failing test, git bisect, fix the cause, pin it with a regression test. Use for bugs, errors, failing tests or CI, "prima funzionava", "debugga", "analizza questo log".
allowed-tools: Bash(ff:*)
---

# ffcode-debug

`ff` (CLI of ffcode-core). First `ff sync --quick` (completes `.ffcode/`, refreshes caches); a NEEDS line is for the developer: mention it, don't block. `ff flow QUERY` shows the chain behind an endpoint or command; `ff flow --impact FILE` what a change reaches.

1. **Compress the evidence, don't paste it.** `ff debug log FILE` (or `cmd 2>&1 | ff debug log -`): error lines, frames inside this repo, tail. Work from that.
2. **Reproduce first.** Smallest failing test or command (`[commands] test` narrowed to one test). No reproduction → say what is missing; ask for the input/env, don't guess a fix.
3. **Localise.** `ff find` / `ff refs NAME` to the code in the frames; read those ranges only. Regression with a known good commit → `ff debug bisect GOOD [--cmd "<narrow test>"]` (needs a clean tree; resets afterwards).
4. **State the cause** in one or two sentences with `file:line` before touching code; check the hypothesis (a log line, an assertion), not just plausibility.
5. **Fix the cause** with the smallest diff (E1/E3 often: a silently ignored input). Look with `refs` for the same pattern elsewhere and list, don't fix, other occurrences.
6. **Pin it:** the reproducing test stays as a regression test named after the rule (C6, T1). `ff check --changed`.
7. Report: cause, fix, test added, what was verified, similar spots found. Durable lessons → `.ffcode/context.md` (one line) or an ADR (`ff adr`).
