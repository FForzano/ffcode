---
name: ffcode-test
description: Find and write the missing tests for a change - lists symbols added in the diff that no test mentions, designs tests that pin the rule (not the implementation), writes them in the project's test framework and checks they fail without the change. Use when the user asks for tests, coverage of a diff, "scrivi i test", "cosa manca da testare", "pinna questa regola con un test", or before delivering a change without tests.
---

# ffcode-test

`FF="python3 ~/.claude/skills/ffcode-style/scripts/ffcode.py"`; rules T1–T4, C6.

1. `$FF untested [--base REF]`: added functions/classes with no mention in any test file (name-based heuristic: a hit can be a false "tested", a miss a false "untested" for dynamically named code; decide by reading).
2. Per item, decide the **rule** it implements (business rule, invariant, boundary, error case), not the lines. Test list first, short: happy path, each boundary, each refused input (E1), one regression per fixed bug.
3. Follow the neighbours: framework, helper/fixture style, folder mirroring (`lang/<language>.md`). Read one similar test file before writing. Deterministic: seeded randomness, injected time, no network. Name = the rule in words.
4. Run each new test; for a bug fix or a rule change confirm it **fails without the production change** (stash or revert that hunk), then passes with it.
5. Container/DB-bound suites: use `[commands] test`; if it cannot run here, write the tests and say they are unrun.
6. `$FF check --changed`; report: tests added (names), what each pins, results, items deliberately left untested with the reason.
