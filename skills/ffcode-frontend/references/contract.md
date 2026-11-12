# design.toml (the design contract)

Machine-readable; `ffcode ui sync|palette|components|context` and `ffcode uilint` read it. Keep it small.

```toml
[meta]
mode = "operate"            # persuade | operate | read | experience
mood = ["calm", "precise", "warm"]

[color.light]               # ROLES, not hues. Same names in [color.dark].
surface = "#ffffff"         # page background
surface-alt = "#f6f6f6"     # cards, zebra, side panels
text = "#111827"            # body text (on surface, surface-alt)
muted = "#4b5563"           # secondary text (>= 4.5:1 on surface)
border = "#d1d5db"
brand = "#d10c33"           # the one accent: actions, links, key emphasis
brand-contrast = "#ffffff"  # text on brand
focus = "#d10c33"           # focus ring (>= 3:1 on surface)
danger = "#b91c1c"          # + success, warning, info as needed
[color.dark]                # derive; verify with `ffcode ui palette`

[font]    sans = "..."  mono = "..."
[type]    scale = [12, 14, 16, 18, 24, 36, 48]      # px, steps must be visibly different
[space]   base = 4  scale = [0, 4, 8, 12, 16, 24, 32, 48, 64]
[radius]  scale = [0, 6, 12, 9999]
[shadow]  sm = "..."  md = "..."
[motion]  fast = "120ms"  base = "200ms"  ease = "cubic-bezier(.2,.8,.2,1)"
[z]       scale = [0, 10, 100, 1000]

[ui]
output = "src/styles/tokens.css"   # generated custom properties (--color-*, --text-N, --space-N, --radius-N, --shadow-*, --motion-*, --z-*)
tailwind = "tailwind.tokens.js"    # optional: theme.extend object that points at those variables
components = ["src/components"]    # where `ui components` and `ui new` work
strict = false                     # true: OFF* findings fail `check`

[rules]
notes = ["Buttons: one primary per view", "Icons: one set, 20px, 1.5 stroke"]   # always/never statements, shown by `ui context`
```

## What each script does with it
- `ui init`: drafts it (DESIGN.md frontmatter first, then values counted in the code). `--force` overwrites, `--stdout` previews.
- `ui sync`: tokens file (light, dark via `prefers-color-scheme` and `[data-theme]`, reduced-motion zeroes durations) + optional Tailwind theme. Never edit the output by hand.
- `ui palette [--fix]`: contrast of text/muted/brand/focus/danger pairs per theme (4.5:1 text, 3:1 UI parts); `--fix` proposes the nearest lightness that passes.
- `uilint`: `OFFCOLOR` colour not in the contract (nearest shown), `OFFSIZE` font-size not in `[type]`, `OFFSPACE` spacing not in `[space]` nor a multiple of `base`, `OFFRADIUS`. Also in inline styles and Tailwind arbitrary values (`text-[13px]`). Token files themselves are skipped.
- `ui components`: reuse inventory; `ui new`: scaffold in the project convention; `ui context`: digest of all of it.

Legacy code will show many OFF* hits: use `--changed`; migrate when touching a file, or in a dedicated pass.
