# extract and document - the design system

**extract [target]**
1. `$FF uitokens --top 20`: used colours, sizes, radii, shadows, spacing, near-duplicates, literals equal to a token.
2. Decide the token set (roles, not hues): colour roles with light/dark values, type scale (6–8 steps), spacing scale on a 4px base, radii (2–3), elevation (2–3), z-index scale, motion durations/easings.
   Where they live follows the stack: CSS custom properties in one file, Tailwind `theme.extend`, a TS tokens module, or the UI kit's theme. One source, imported everywhere.
3. Replace literals by tokens file by file (small commits); map near-duplicates to the nearest token and say which visuals shift (screenshots before/after); delete dead CSS afterwards.
4. Repeated markup/behaviour used ≥ 3 times with the same shape → a component with a typed prop API (variants as props, not copies); two uses → leave. Colocate styles with the component.
5. Re-run `uitokens`/`uilint`: distinct values down, `HARDCOLOR` down. Report numbers.

**document**
Write/refresh `design.md` from the code, short: tokens table (name → value → role), type scale, spacing, components (name, purpose, variants, when not to use, file), layout and responsive rules, motion, accessibility commitments, do/don't, where things live.
Derive from what is shipped (`uitokens`, component directory), not from intentions; mark gaps `(missing)`. Keep under ~150 lines; link instead of copying code.
