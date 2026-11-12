---
name: ffcode-commit
description: Prepare commits and PRs in the project's convention: staged check, logical split, validated messages, PR description. Use for "committa", "fai il commit", "prepara la PR", "pusha".
allowed-tools: Bash(ff:*)
disable-model-invocation: true
---

# ffcode-commit

`ff` (CLI of ffcode-core). Commit and push only when the user asked; on the main branch, branch first.

1. `git status --short` and `git diff --stat`. Unrelated changes, generated files, `.ffcode/repos/`, `.ffcode/map.md`, secrets or large binaries → leave out and say so (G2).
2. `ff commit-plan` proposes the split (groups, tests paired with their code, files to leave out); correct it if wrong, then stage with explicit paths, never `git add -A`.
3. `ff check --staged`. A FAIL stops the commit; report it.
4. Message: look at the project's style (`[commit] style` in config, else `git log --format=%s -10`). Subject ≤ 72, imperative, what + scope; body only for the why, wrapped. Validate with `ff commitmsg "..."`.
   Add attribution lines when the session instructions require them.
5. PR (only if asked, `gh pr create`): `ff pr --check` fills What, How tested, Cross-repo impact and Migration notes from the diff; you write only the Why (2–3 lines) and the title (like a commit subject). No push or PR without confirmation.
