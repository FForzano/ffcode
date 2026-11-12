# UI work (loaded by ffcode-write when UI files are touched)

UI is recognised, not announced: files like `*.tsx *.jsx *.vue *.svelte *.html *.css *.scss`, or `[check] ui = true` / `.ffcode/design.toml` present.
Engineering rules stay those of `ffcode-core`; this adds a **design contract** (`.ffcode/design.toml`) that keeps the look consistent and scripts that check it.
`ff` (installed in ~/.local/bin by `install.sh`; if `command -v ff` finds nothing, prefix the call with `ff() { python3 ~/.claude/skills/ffcode-core/scripts/ffcode.py "$@"; };`)

## 1. Orient (one call, ~40 lines)
`ff ui context` → stack, product notes, the contract (colour roles, type/space/radius/z scales, fonts, motion, rules), component count and most used, lint counts.
Do not open PRODUCT.md, DESIGN.md, tokens files or the component folder for this. Read source only for the code you change.

## 2. Contract (schema: `ui-contract.md`)
- Missing, and the task is more than a tiny fix → `ff ui init` (from `DESIGN.md` frontmatter, else from values really used; guesses marked `*`). Ask at most: mode
  (persuade / operate / read / experience), three mood words, brand constraints. Colours become **roles**. Then `ff ui sync` and `ff ui palette --fix`.
- Prose files (`PRODUCT.md`, `DESIGN.md`) stay as they are; the contract wins on values. Change it only on purpose: edit → `ui sync` → `uilint` (drift) → record a standing rule with `ff adr`.

## 3. Build
1. Reuse: `ff ui components [NAME]`, `ff find`. Extend with a prop before cloning (S2).
2. New component: `ff ui new Name` (project convention: ts/js, CSS modules / Tailwind / plain CSS).
3. Tokens only: no literal colour, size, spacing, radius, shadow, z-index or duration; a missing value is a new token (edit the contract) or a mistake.
4. Every state (default, hover, focus-visible, active, disabled, loading, empty, error, long/short content), semantic elements, keyboard path, i18n, responsive from 320px.
   Aesthetic rules: `ui-principles.md`; patterns for forms, tables, feedback, motion, failure cases: `ui-build.md`. Read the part you need.
5. The product **mode** decides priorities: operate = scanability/consistency; persuade = hierarchy and one action; read = measure/structure; experience = the work leads.

## 4. Verify (cheap first)
1. `ff check --changed`: includes `uilint` (a11y leads, hard-coded colours, motion, i18n) and `OFFCOLOR OFFSIZE OFFSPACE OFFRADIUS` against the contract (advisory unless `[ui] strict = true`).
2. Tokens changed → `ff ui palette`; drift suspected → `ff uitokens`.
3. One batched visual pass if a browser tool exists (load its skill first): real screen, real content, ~375px and ~1280px (+ dark): overflow, focus order, states. Otherwise say "not visually verified".

Existing system beats taste; the brief beats these defaults. Never invent product facts or meaningful copy. Large restyle: contract first, then migrate file by file with `uilint --changed`, small commits.
