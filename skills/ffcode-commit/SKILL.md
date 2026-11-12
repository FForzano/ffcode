---
name: ffcode-commit
description: Prepare commits and pull requests in the project's convention - run the staged check, split the diff into logical commits, write validated messages (conventional or imperative per project config), and draft the PR description. Use when the user says "committa", "fai il commit", "prepara la PR", "scrivi il messaggio di commit", "pusha", or asks to finish and deliver a change.
---

# ffcode-commit

`FF="python3 ~/.claude/skills/ffcode-core/scripts/ffcode.py"`. Commit and push only when the user asked; on the main branch, branch first.

1. `git status --short` and `git diff --stat`. Unrelated changes, generated files, `.ffcode/repos/`, `.ffcode/map.md`, secrets or large binaries → leave out and say so (G2).
2. Several logical changes → propose the split (list of files per commit) and stage with explicit paths, never `git add -A`.
3. `$FF check --staged`. A FAIL stops the commit; report it.
4. Message: look at the project's style (`[commit] style` in config, else `git log --format=%s -10`). Subject ≤ 72, imperative, what + scope; body only for the why, wrapped. Validate with `$FF commitmsg "..."`.
   Add attribution lines when the session instructions require them.
5. PR (only if asked, `gh pr create`): title like a commit subject; body = Why (2–3 lines), What (bullets by area), How tested (commands run + result), Cross-repo impact (from `ffcode-workspace`), Migration/deploy notes. No push or PR without confirmation.
