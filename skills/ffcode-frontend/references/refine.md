# refine - motion, colour, type, layout, intensity

Each starts from `design.md` and the actual screen; change the minimum that achieves the goal, through tokens.

**motion** - Purpose first: feedback (press, toggle), orientation (enter/exit, reorder), attention (new, error). 100–200ms feedback, 200–300ms transitions, ease-out for entering, ease-in for leaving; animate transform/opacity (clip-path/filter when smooth);
stagger ≤ 40ms per item and ≤ 5 items; no looping decoration; every animation has a `prefers-reduced-motion` path (remove movement, keep state change). One memorable moment per view at most. Respect interrupts (can be cancelled).
**color** - Neutrals tinted toward the brand hue; one accent for actions and focus; semantic colours only for status; never convey meaning by colour alone; check both themes; use OKLCH/HSL ramps to derive steps; ≤ 10% of the surface in accent.
**type** - Pick scale ratio (1.2–1.333), 1–2 families, self-hosted with `font-display: swap` and fallback metrics; hierarchy through size and weight before colour; tabular numerals in data; balanced headings (`text-wrap: balance`), measure ≤ 75ch; fluid sizes with `clamp()` for display text only.
**layout** - Structure before decoration: group by proximity, align to a grid, vary density deliberately, use whitespace to separate sections rather than boxes; establish one clear reading path; sticky/primary actions where the thumb or cursor is.
**bolder / quieter** - Bolder: bigger scale contrast, stronger accent use, more decisive hierarchy, one distinctive element, keep the system. Quieter: fewer colours, softer contrast between non-essential elements (never below the floor), less motion, more space, remove decoration.
