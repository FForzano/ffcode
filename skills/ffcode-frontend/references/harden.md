# harden - production readiness (also: onboard)

For each screen/flow walk the failure space and make each case designed, not accidental:
- **Data**: empty, one, many (pagination/virtualisation), very long text and unbroken strings, missing optional fields, special characters, numbers/dates/currency in other locales.
- **Network**: loading (skeleton or spinner with a timeout path), slow, offline, retry, partial failure, double submit (disable + idempotency), stale data, race on fast navigation (cancel/ignore old responses).
- **Errors**: say what happened and what to do; keep the user's input; field-level errors beside the field and summarised for screen readers; log with context, never show stack traces.
- **Permissions and states**: unauthorised, expired session (return to where they were), disabled by plan/role with an explanation, destructive actions with confirmation or undo.
- **Input**: validation on blur/submit with clear rules, paste, autofill, IME, mobile keyboards (`inputmode`, `autocomplete`), file size/type limits.
- **i18n/a11y**: strings externalised, 40% expansion, plural rules, focus management after dialogs/route changes, announcements for async results.
**onboard**: first-run = the shortest path to the first success; empty states teach the next action (one primary button, one sentence); progressive disclosure; no tours that block; state that can be resumed.
Pin the important cases with tests (T1, T2): component tests for states, e2e only for the critical path.
