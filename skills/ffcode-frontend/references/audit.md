# audit - technical quality

Scripts first, reading second. Report, don't fix (unless asked).
1. `$FF uilint [--changed]`: a11y leads (alt, field labels, click-on-div, tabindex, outline, contrast of literal pairs, viewport zoom), tokens (HARDCOLOR), motion, i18n.
2. `$FF uitokens`: drift = many distinct sizes/colours/radii/shadows, near-duplicate colours, spacing off the grid, literals equal to an existing token.
3. Read only what the scripts cannot see, in this order: keyboard/focus flow of the main path, semantic structure (landmarks, heading order), forms (labels, errors, autocomplete), dynamic content (live regions, focus after route change),
   responsive (320px, 768px, wide; text zoom 200%), images/fonts/bundle (sizes, lazy, `font-display`, route splitting), theming (dark mode / high contrast parity), i18n (hard-coded strings, expansion, RTL if required).
4. Browser pass if available: computed contrast on real rendering, tab order, layout at the widths above, console errors, network waterfall of the first load.
Report ≤ 25 lines: score per area (A11y, Responsive, Performance, Theming, System consistency, i18n) 0–4; findings ranked blocker/major/minor with `file:line`; the 3 fixes with the best return; what was not checked.
