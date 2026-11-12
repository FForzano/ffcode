---
name: ffcode-release
description: Prepare a release or deploy of a multi-repo product - per repo, what is on the source branch and not yet on the target (commits, new migrations, changed contract files), the deploy order from the dependency graph, risks and a release checklist. Use when the user says "prepara la release", "cosa c'è in develop che non è in main", "ordine di deploy", "cosa devo rilasciare", "changelog", or plans a deploy that spans backend, frontend, docs and infra.
---

# ffcode-release

`FF="python3 ~/.claude/skills/ffcode-style/scripts/ffcode.py"`; needs `.ffcode/workspace.toml` (see `ffcode-workspace`) with the repos cloned (`$FF workspace sync`).

1. `$FF workspace sync` (pulls clean clones), then `$FF release [--from develop] [--to main]`: per repo commits, `MIGRATION` (new migration files), `CONTRACT` (changed contract files) and the deploy order.
2. Read only what the risks need: migrations (destructive? long-running? reversible? before or after the code?), contract changes (breaking for which consumer, per `graph`), config/env additions.
3. Write the release plan (≤ 25 lines): changelog by repo and feat/fix (from the conventional subjects), **order** with reasons (migration → backend → frontend/docs → infra), pre- and post-deploy checks, rollback per step, manual actions (backfills, env vars, docs rebuild after OpenAPI changes).
4. Run `$FF check` in the repos whose commands are configured; report failures, don't hide them.
5. Execution (merge, tag, build, deploy, migrations on shared DBs) is **never done without explicit confirmation of each step**; prod follows the project's own confirmation flow. Offer to save the plan as `.ffcode/decisions/NNNN-release-X.md` (`ffcode-decide`).
