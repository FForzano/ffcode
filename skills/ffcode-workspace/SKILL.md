---
name: ffcode-workspace
description: Manage a product made of several repositories (e.g. frontend, backend, infrastructure, docs) from inside one of them - record the repos, roles and dependencies in .ffcode/workspace.toml, clone the others under .ffcode/repos (git-ignored), check status, track contract files (OpenAPI, schemas, env examples) for cross-repo changes, and plan the order of changes and deploys. Use when a change may affect another repo, when the user says "clona gli altri repo", "dipendenze tra repo", "workspace", "ordine di deploy", "il frontend dipende dal backend", or asks about the full product.
---

# ffcode-workspace

`FF="python3 ~/.claude/skills/ffcode-style/scripts/ffcode.py"`; config `.ffcode/workspace.toml` (template: `ffcode-style/templates/workspace.toml`).

## Set up
1. Create `.ffcode/workspace.toml`: one `[[repo]]` per repository with `name`, `url`, `role`, `depends_on`, `contracts` (paths inside that repo that other repos rely on:
   OpenAPI file, DB schema/migrations dir, env example, shared types), `self = true` on the repo holding this `.ffcode/`, optional `local` = path of an existing checkout.
   Dependencies come from facts: base URLs in frontend config, CI workflows dispatching other repos, deploy scripts. Ask the user only for what you cannot read.
2. `$FF workspace sync [--from-local]`: clones missing repos into `.ffcode/repos/<name>` (from `local` when asked, then the origin is reset to `url`) and `pull --ff-only` on clean ones;
   dirty repos are skipped. `.ffcode/.gitignore` already excludes `repos/`; confirm with `git status` that nothing from `repos/` shows.
3. Write a 10–20 line "Product map" in `.ffcode/context.md`: what each repo owns, who calls whom, how it deploys and in which order.

## Use
- `$FF workspace status` (branch, dirty, ahead/behind), `graph` (dependencies), `where NAME` (path), `contracts [--changed]` (hash of the contract files; `CHANGED` since last run).
- **Before changing a contract** (endpoint, DTO, schema, env var, event): list consumers via `graph`, read the consuming code with `$FF find` inside `.ffcode/repos/<consumer>` (`--root` that path after `ffcode-map` there, or plain grep for the specific name),
  and write the cross-repo plan: order of merges/deploys, backward compatibility window, docs to update. Backend-first additive changes; breaking changes only with a documented migration.
- Do **not** edit a cloned repo unless the user asks; if asked, work in its own branch and commit there (it is a separate repository).
- Regenerate the contract hashes after each agreed change so the next session sees a clean baseline.
