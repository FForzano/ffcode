# PHP (Yii2 / Laravel / Symfony-style layered apps)
- Layers: controller (HTTP only) → request/form model (validation) → service (`services/<domain>/`) → DTO built by an assembler/resource. ORM models only for persistence; no business logic in controllers.
- One definition per business rule (e.g. one query/scope class used by every report). Versioned or time-dependent data: read it through one accessor that takes the as-of date, never straight from the table.
- Unsupported filters/options → 400, never ignored. Console commands: `--dry-run`, idempotent, listed in `context.md`; distinct exit codes for blocked/conflict/failed.
- Migrations: ordered and timestamped, reversible when possible, never edit an applied one. Money in integer cents or decimal.
- API docs (OpenAPI attributes/annotations) change in the same commit as the endpoint; regenerate the spec when they change.
- Style: PSR-12, `camelCase` methods, `PascalCase` classes, `SCREAMING_CASE` constants; type declarations everywhere. Tests: PHPUnit/Codeception/Pest — a test per pinned rule; run inside the container when `vendor/` is not on the host (set it in `[commands] test`).
