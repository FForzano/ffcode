# Principles and quality floor

## Modes (choose from the surface, not from the product)
- **Persuade** (landing, marketing, pricing): earn attention and action; strong hierarchy, one clear call to action, real content and imagery, expression allowed.
- **Operate** (app, dashboard, admin, settings, editors): the task comes first; scanability, consistency, native expectations, dense but calm; brand in details.
- **Read** (docs, articles, help, changelog): comprehension first; measure 60–75ch, heading structure, code and table styling; navigation that shows where you are.
- **Experience** (portfolio, gallery): the work leads; the interface recedes.
A product's landing page is persuade even if the product is a tool.

## The floor (verify on the built result)
- Contrast: body text ≥ 4.5:1, large text and UI parts ≥ 3:1, on every surface and theme; secondary text tinted from its surface, not neutral grey on colour.
- Keyboard: every action reachable and operable, visible `:focus-visible`, logical order, no traps, skip link on multi-section pages. Controls are `button`/`a`/native inputs.
- Targets ≥ 44px on touch (24px minimum on dense desktop UI, with spacing). Labels bound to fields, errors tied to fields (`aria-describedby`), live regions for async status.
- Type: a scale with obvious steps (not 14/15/16), body 16px+, line-height 1.4–1.6, measure ≤ 75ch, no body text below 12px, weights that differ enough to carry hierarchy.
- Spacing: a base unit (4 or 8) used throughout; tighter inside groups than between them; more space above a heading than below.
- Colour: roles, not hues (surface, text, muted, border, brand, success, warning, danger, focus) as tokens; one accent doing real work; light and dark derived from the same roles.
- Depth: elevation levels, soft offset shadows; borders or surfaces for separation, not both everywhere.
- Motion: ≤ 300ms for feedback, ease-out; animate transform/opacity; honour `prefers-reduced-motion`; no motion without meaning.
- Responsive: fluid layout, content-driven breakpoints, tested at 320px and wide screens; no horizontal scroll; images sized (no layout shift).
- Performance: lazy-load below-the-fold and route code, explicit image dimensions, fonts with `font-display`, no blocking third-party scripts for the first paint.
- Copy: controls name their action, errors say the problem and the way out, empty states say what to do, one term per concept.
- i18n: no hard-coded text, no concatenated sentences, room for 40% longer strings, locale-aware dates/numbers/currency.

## Defaults to refuse unless the brief earns them (they mark generic work)
Identical icon-heading-text cards as the whole page structure, cards inside cards, a big-number hero metric template, eyebrow labels above every heading, numbered sections without meaning,
gradient text, decorative glass/blur, thick coloured side stripes on cards and alerts, hard offset "brutalist" shadows outside such a design, emoji or glyphs as icons (use one icon set, one stroke),
a modal where inline would do, monospace as decoration, centred everything, uniform entrance animation on every block.
The brief and the existing design file override this list; so does a user's explicit choice. The list is a check on your own habits, not a style.
