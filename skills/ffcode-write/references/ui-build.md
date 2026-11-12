# Building UI: patterns that work (read only the part you need)

## Structure and layout
- Semantics first: landmarks (`header nav main aside footer`), one `h1`, headings in order, lists for lists, `button` for actions, `a` for navigation, `table` for tabular data.
- Layout with CSS grid/flex and `gap`, not margins on children; container with max-width and a fluid gutter; sections separated by space or a hairline, not by boxes; content-driven breakpoints.
- Hierarchy: one primary action per view; group by proximity; size + weight carry rank before colour; align to the grid; a clear reading path. Cards only for discrete, tappable entities.
- Density follows mode: operate = compact rows, tabular numerals, sticky headers and actions; read = generous measure/line-height; persuade = large type contrast and decisive spacing.

## Forms
- Visible label per field (not placeholder), hint under it, error under it tied by `aria-describedby`, `required` + `aria-invalid`; correct `type`, `inputmode`, `autocomplete`.
- Validate on blur/submit with rules shown up front; keep input on error; disable submit only while pending (and make the request idempotent); focus the first error on submit; success feedback where the eye is.
- Group related fields (`fieldset/legend`); one column on narrow screens; destructive or irreversible actions apart from the primary one and confirmed (or undoable).

## Data, tables, lists
- Decide the empty, one, many, and huge cases: empty text + next action; pagination/virtualisation beyond ~100 rows; truncation with title/tooltip and a way to read the whole value; sort/filter state in the URL.
- Numbers right-aligned, tabular figures, units and locale-aware formats; dates relative only when absolute is available on demand.
- Narrow screens: priority columns, or rows → stacked cards; never a clipped table without scroll affordance.

## Feedback and async
- Loading: skeleton matching the final layout for >300ms, spinner for short actions; keep previous content during refresh; cancel or ignore stale responses (race on fast navigation).
- Errors: what happened, what to do, retry; keep user input; no raw codes or stack traces; global errors in a live region.
- Success: inline confirmation or toast (`role="status"`), never only a colour change. Optimistic updates only when rollback is designed.

## Navigation and overlays
- Current location visible (`aria-current`); focus moves to the new page heading after route change; preserve scroll/back behaviour.
- Dialogs only when the task needs interruption: focus trap, `Esc`, return focus, labelled; prefer inline expansion, popovers or a page for the rest.

## Style system
- One source of values (tokens); components own their styles (module/scoped/utility classes per project convention); global CSS only for resets, tokens and true primitives.
- No `!important` (fix specificity), no magic z-index (use the scale), no fixed pixel heights on text containers, no `transition: all`.
- Dark mode = same roles, different values; never invert; check images/shadows/borders; honour `prefers-color-scheme` and a manual `data-theme`.
- Fonts: self-host, `font-display: swap`, limit weights, size-adjusted fallback; icons from one set, `aria-hidden` when decorative, labelled when alone.

## Motion
- Meaning only: feedback (press, toggle), orientation (enter/exit, reorder), attention (error, new). 100–200ms feedback, 200–300ms transitions, ease-out in / ease-in out; transform + opacity.
- No looping decoration; stagger ≤ 40ms and ≤ 5 items; cancellable; `prefers-reduced-motion` removes movement and keeps the state change.

## Copy and i18n
- Buttons name the result ("Save changes"); errors = problem + way out; empty states = purpose + next action; one term per concept; sentence case unless the system says otherwise.
- All text through the i18n catalogue (stable keys, ICU plurals, no concatenation); allow +40% length; locale-aware dates/numbers/currency; `lang` on the document and on foreign passages.

## Performance and robustness
- Route-level code splitting; lazy images below the fold with `width/height` (no layout shift); memoise only after measuring; avoid layout thrash in scroll/resize handlers; third-party scripts deferred.
- Test the states (component tests for empty/error/loading, one e2e for the critical path); accessibility check in the test suite when a tool is present (axe).
