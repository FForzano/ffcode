# Tests (loaded by ffcode-write when tests are requested or a change lacks them)

`FF="python3 ~/.claude/skills/ffcode-style/scripts/ffcode.py"`; rules T1–T4, C6.

1. **Find what is not exercised, best signal first:**
   - `$FF diffcov --run` (or `$FF check --changed --coverage`): added executable lines that no test ran, per function, from the real coverage report
     (Cobertura/Clover/lcov; `[commands] coverage` and `[coverage] report`, `min` in `config.toml`). "Not in the report" = file never loaded by a test.
   - No coverage configured (or it cannot run here) → `$FF untested [--base REF]`: added symbols no test file mentions. A name-based heuristic: false "tested" and
     "untested" both happen; decide by reading. Say which of the two you used.
2. Per item, decide the **rule** it implements (business rule, invariant, boundary, error case), not the lines. Test list first, short: happy path, each boundary, each refused input (E1), one regression per fixed bug.
3. Follow the neighbours: framework, helper/fixture style, folder mirroring (`lang/<language>.md`). Read one similar test file before writing. Deterministic: seeded randomness, injected time, no network. Name = the rule in words.
4. **Prove the test pins the change:** `$FF failwithout [--cmd "<narrow test>"]` reverts the production files of the diff to the base, runs the tests, restores everything. Tests must FAIL there; a pass means they pin nothing (rewrite). Needs the tests in the working tree.
5. **Critical areas, optional:** `$FF mutate --list` shows changed files inside `[mutation] critical` (money, data: prices, payouts, invoices...). When the user asks, or the change touches them and a tool is configured, `$FF mutate` runs the mutation tool on those files only; each surviving mutant is a missing assertion, fix it or justify it. Never run it on the whole project (slow). No `command` configured → say so, do not install tools unasked.
6. Container/DB-bound suites: use `[commands] test`; if it cannot run here, write the tests and say they are unrun.
7. `$FF check --changed`; report: diff coverage %, tests added (names) and what each pins, the `failwithout` result, mutation result if run, items left untested with the reason.
