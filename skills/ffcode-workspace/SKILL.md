---
name: ffcode-workspace
description: Multi-repo products (frontend, backend, infra, docs): .ffcode/workspace.toml, clone the other repos, status, contract changes, change and deploy order, release notes. Use for "clona gli altri repo", "ordine di deploy", "prepara la release", "changelog", or when a change may affect another repo.
allowed-tools: Bash(ff:*)
---

# ffcode-workspace

`ff` (CLI of ffcode-core). First `ff sync --quick` (completes `.ffcode/`, refreshes caches); a NEEDS line is for the developer: mention it, don't block. Config `.ffcode/workspace.toml` (template: `ffcode-core/templates/workspace.toml`).

## Set up
1. Create `.ffcode/workspace.toml`: one `[[repo]]` per repository with `name`, `url`, `role`, `depends_on`, `contracts` (paths inside that repo that other repos rely on:
   OpenAPI file, DB schema/migrations dir, env example, shared types), `self = true` on the repo holding this `.ffcode/`, optional `local` = path of an existing checkout.
   Dependencies come from facts: base URLs in frontend config, CI workflows dispatching other repos, deploy scripts. Ask the user only for what you cannot read.
2. `ff workspace sync [--from-local]`: clones missing repos into `.ffcode/repos/<name>` (from `local` when asked, then the origin is reset to `url`) and `pull --ff-only` on clean ones;
   dirty repos are skipped. `.ffcode/.gitignore` already excludes `repos/`; confirm with `git status` that nothing from `repos/` shows.
3. Write a 10–20 line "Product map" in `.ffcode/context.md`: what each repo owns, who calls whom, how it deploys and in which order.

## Use
- `ff workspace status` (branch, dirty, ahead/behind), `graph` (dependencies), `where NAME` (path), `contracts [--changed]` (hash of the contract files against `.ffcode/contracts.lock`: `CHANGED`/`NEW`/`REMOVED`; `--accept` records the versions once repos agree), `map` (writes `.ffcode/workspace-map.md`: roles, dependents, contracts, env keys; `sync` refreshes it).
- **Before changing a contract** (endpoint, DTO, schema, env var, event): list consumers via `graph`, read the consuming code with `ff find` inside `.ffcode/repos/<consumer>` (`--root` that path after the map (`ffcode-core`) there, or plain grep for the specific name),
  and write the cross-repo plan: order of merges/deploys, backward compatibility window, docs to update. Backend-first additive changes; breaking changes only with a documented migration.
- Do **not** edit a cloned repo unless the user asks; if asked, work in its own branch and commit there (it is a separate repository).
- Regenerate the contract hashes after each agreed change so the next session sees a clean baseline.

## Release (multi-repo)

Needs the repos cloned (`ff workspace sync`).

1. `ff workspace sync` (pulls clean clones), then `ff release [--from develop] [--to main]`: per repo commits, `MIGRATION` (new migration files), `CONTRACT` (changed contract files) and the deploy order.
2. Read only what the risks need: migrations (destructive? long-running? reversible? before or after the code?), contract changes (breaking for which consumer, per `graph`), config/env additions.
3. Write the release plan (≤ 25 lines): changelog by repo and feat/fix (from the conventional subjects), **order** with reasons (migration → backend → frontend/docs → infra), pre- and post-deploy checks, rollback per step, manual actions (backfills, env vars, docs rebuild after OpenAPI changes).
4. Run `ff check` in the repos whose commands are configured; report failures, don't hide them.
5. Execution (merge, tag, build, deploy, migrations on shared DBs) is **never done without explicit confirmation of each step**; prod follows the project's own confirmation flow. Offer to save the plan as `.ffcode/decisions/NNNN-release-X.md` (`a decision record`).
