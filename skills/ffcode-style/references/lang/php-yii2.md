# PHP (Yii2, FPC backend)
- Layers: Controller (REST action only) → Form model (`BaseForm`, validation) → Service (`services/<domain>/`) → DTO via Assembler. ActiveRecord only for persistence; no business logic in controllers or models' getters of other domains.
- One definition per business rule (e.g. a query/scope class used by every report); reports never read versioned tables directly: go through the `inForce($asOf)`-style accessor.
- Unsupported filters/options → 400, never ignored. Console commands: `--dryRun=1`, idempotent, documented in CLAUDE/`context.md` commands list; distinct exit codes for blocked/conflict/failed.
- Migrations: `m<yymmdd>_<hhmmss>_name`, reversible when possible, never edit an applied one. Money in integer cents or decimal.
- OpenAPI via `#[OA\...]` attributes in the same commit; regenerate docs when annotations change.
- Style: PSR-12, `camelCase` methods, `PascalCase` classes, `SCREAMING_CASE` constants; type declarations everywhere. Tests: Codeception (`unit`, `functional`), a test per pinned rule, run inside the container when `vendor/` is not on the host.
