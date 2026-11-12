# ffcode checklist

Rules of the code style, deduced from real projects (web backends and frontends, infrastructure, numerical/scientific code) plus general good practice.
`[auto]` = `ffcode lint` / `ffcode check` catches it (rule id in brackets). `[judge]` = needs reading. A project may deviate in
`.ffcode/style.md`; the deviation wins and is cited by rule id. Language details: `lang/<language>.md`.

## 1. Structure and responsibility
- S1 [judge] **One responsibility per unit.** Thin entry layer (controller, router, CLI script, React page) → validation → service/domain
  logic → persistence/serialization. Never parsing, DB access and response shaping in one function.
- S2 [judge] **One copy of each definition.** A formula, a status list, a business rule, a CSS block exists once, and everything else imports it.
  Before writing, grep for an existing one (`ffcode find NAME`). Found a duplicate: flag it, fix once agreed, never add a third. [DUP]
- S3 [judge] **Reuse order:** existing code in the repo → library already a dependency → new maintained library, only if nothing covers it.
- S4 [judge] **Core general, specialise where a study/feature needs it.** No parallel code path for a special case that is a parameter of the general one.
- S5 [judge] **No speculative abstraction.** ABCs/interfaces only at real plugin seams; otherwise a function or a plain data type. No half-finished work, no flags for hypothetical futures.
- S6 [auto] Size: functions ≤ `max_function_lines`, files ≤ `max_file_lines`, ≤ `max_params` parameters; beyond that split or pass a typed object. [FUNC FILE PARAM]

## 2. Data, config, state
- D1 [judge] Configuration is explicit and validated at the edge (frozen dataclass, typed config object); passed as an argument, not read from globals or the environment deep in the code.
- D2 [judge] No global mutable state or hidden singletons. Never mutate an input; return new values.
- D3 [judge] Magic numbers become named constants with the reason of the value in a comment (unit, source, physical/business justification).
- D4 [judge] Types at every public boundary (hints, DTOs, TS types, array shapes documented where relevant).

## 3. Errors and boundaries
- E1 [judge] **Refuse, don't ignore.** Unsupported input or option → explicit error (HTTP 400, exception, CLI exit code), never silently dropped or defaulted: ignored filters return numbers that look filtered.
- E2 [auto] No empty `catch`/`except`; catch the narrowest type, add context, re-raise or handle. [CATCH]
- E3 [judge] Validate at system boundaries (user input, external APIs, files); trust internal callers.
- E4 [judge] Operations that change data in bulk or irreversibly have `--dry-run`, are idempotent or resumable, and say what they did. Distinct exit codes where scripts are chained.
- E5 [auto] No secrets in code or in committed config; credentials from env/secret store. [SECRET]

## 4. Comments and docs
- C1 [judge] Comments say a non-obvious **why** or an assumption that would break the code, never *what*, never history. One line per function, a few per module.
- C2 [judge] Long explanations, derivations, design rationale go to `docs/` (or `.ffcode/decisions/`), linked from the code.
- C3 [judge] Code derived from a source (paper equation, API doc, spec) cites it with its exact tag/section at the function.
- C4 [auto] No commented-out code, no `TODO` without owner or issue: `TODO(name)` / `TODO(#12)`. [CODE TODO]
- C5 [auto] No debug leftovers (`print`, `console.log`, `var_dump`, `debugger`) outside CLI/scripts. [DEBUG]
- C6 [judge] A rule that is easy to get wrong later is pinned by a test **named after the rule**, and the comment says which test.

## 5. Naming and readability
- N1 [judge] Simple and readable over clever: the next reader, not the shortest code. Names state role and unit (`delay_s`, `price_cents`); avoid abbreviations unknown to the domain.
- N2 [judge] One naming scheme per language (see `lang/`), consistent with the neighbours in the same directory.
- N3 [judge] Early return over deep nesting (> 3 levels is a smell); no boolean flag parameters that switch behaviour: two functions.
- N4 [auto] Line length ≤ `max_line_length` (project value, usually the formatter's). [LEN]

## 6. Tests
- T1 [judge] New behaviour and every bug fix come with a test that fails without the change. Test the behaviour and the invariants, not the implementation.
- T2 [judge] Unit tests for rules/calculations, integration/functional tests for endpoints and pipelines; one assertion idea per test; names say the rule.
- T3 [judge] Deterministic: seeded randomness, injected clocks, no network. Fixtures small and local.
- T5 [auto] Added lines are executed by tests (diff coverage ≥ `[coverage] min`), and a test added for a fix fails without the fix. [`ffcode diffcov`, `ffcode failwithout`]
- T6 [judge] Code in `[mutation] critical` (money, data) has assertions strong enough to kill mutants: run `ffcode mutate` when it changes.
- T4 [auto] The configured `test`, `typecheck`, `lint`, `format_check` commands pass. [`ffcode check`]

## 7. Performance and security
- P1 [judge] Measure before optimising; but no N+1 queries, no unbounded loads, no work inside loops that can be hoisted.
- P2 [judge] SQL parameterised, output escaped, authz checked in the service layer not only the UI, uploads and paths validated.
- P3 [judge] Money, time, units: explicit types (integer cents or decimal; UTC at rest; unit in the name).

## 8. Git and delivery
- G1 [auto] Commit message follows `[commit] style` of the project; subject ≤ 72 chars, imperative, no period. [`ffcode commitmsg`]
- G2 [judge] One logical change per commit; no unrelated reformatting in a feature diff; generated files and `.ffcode/repos/` never committed.
- G3 [judge] Migrations are forward-safe and ordered; deploy order across repos is written down (`ffcode-workspace`).
- G4 [judge] Docs, OpenAPI and README change in the same commit as the behaviour.

## 9. Frontend/UX (when UI is touched)
- U1 [judge] Shared UI patterns are components, shared CSS is one module/class; feature-scoped styles live next to the component. Check `DESIGN.md` / `PRODUCT.md` before adding a pattern.
- U3 [auto] Accessibility and token hygiene leads from `ffcode uilint` (alt, labels, click-on-div, outline, contrast, hard-coded colours, reduced-motion, i18n). [IMGALT FIELDLABEL CLICKDIV OUTLINE CONTRAST HARDCOLOR MOTION I18N]
- U4 [judge] Design context (`product`/`design`) read before UI work and updated with the change; see `ffcode-frontend`.
- U2 [judge] Texts via i18n, loading/empty/error states handled, keyboard and contrast basics.
