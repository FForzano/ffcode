# `.ffcode/` in a project

| File | Committed | Content |
|---|---|---|
| `config.toml` | yes | languages, `[commands]` (format_check, lint, typecheck, test, test_one, coverage, build; wrap docker/ssh here; `test_one` with `{files}` makes `ff check --changed/--staged` run only the tests covering the diff), `[limits]`, `[commit]`, `[check]` (secrets, base, ui, `test_timeout` 900 s, `scoped_test_timeout` 300 s; a timed-out step is TIMEOUT/UNVERIFIED, not FAIL: exit code 3), `[coverage]` (report, min), `[mutation]` (critical globs, command) |
| `context.md` | yes | what the project is, architecture, invariants, command list (migrated from CLAUDE.md) |
| `style.md` | yes | discursive conventions of the project (naming, layering, language of comments) |
| `rules.toml` | yes | deviations the scripts apply and `ff rules` shows: `[rule.ID] ignore/off/note/reason/adr` (see `templates/rules.toml`); they win over the checklist |
| `architecture.toml` | yes | project pattern (REST layered, MVC, hexagonal, components...): `[[layer]]` per kind of unit/object with `paths`, `name_pattern`, `may_import`, `role`, `base`, `stem`, `example`, plus `[conventions]` (URLs, errors, pagination, ids, dates). Drives `ff arch`, lint ARCHNAME/ARCHDEP, `ff orient`. Draft: `ff arch infer` (`--interview`, `--answer`, `--check`, `--packages`: packages as layers with levels, observed imports allowed, cycles and single-file dependencies reported; `ff arch graph`: Mermaid diagram) |
| `arch-answers.toml` | yes | answers to the `ff arch infer --interview` questions (`"names:service" = "no"`); applied by every infer run so the architecture is reproducible. Thresholds live under `[infer]` in `config.toml` |
| `baseline.json` | yes | known legacy findings (`ff lint --baseline`); lint and uilint hide them, so only new problems show |
| `decisions/` | yes | one short ADR per durable decision, header `Rules:`/`Supersedes:`, generated `index.md` |
| `glossary.md` | yes | domain terms and names; `ff find TERM` searches it |
| `state.md` | no | personal work in progress |
| `design.toml` | yes | UI projects: machine-readable design contract (colour roles, scales, fonts, motion) |
| `workspace.toml`, `contracts.lock` | yes | other repos of the product, roles, dependencies, contracts; the contract versions last agreed on (`ff workspace contracts --accept`) |
| `map.md`, `workspace-map.md`, `cache/` (symbols, tests-map, hotspots), `repos/` | no (`.ffcode/.gitignore`) | generated: repo map, cross-repo map, indexes, clones of the other repos |
