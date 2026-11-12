---
name: ffcode-frontend
description: Build and change user interfaces (websites, apps, dashboards, components, design systems) in any web stack with a consistent look and solid engineering - reads a compact design context in one script call, keeps a machine-readable design contract (.ffcode/design.toml) that generates the tokens and is enforced by lint, reuses existing components, scaffolds new ones in the project's convention, and verifies accessibility, contrast and token conformance mechanically. Use whenever the task touches frontend code or visuals - "aggiungi una pagina/componente", "sistema questa schermata", "rendi coerente lo stile", "design system", "tokens", "dark mode", "responsive", "accessibilità", "migliora la UI" - even if the skill is not named.
---

# ffcode-frontend

Programming the frontend well = engineering (`ffcode-style`) + a **design contract** that keeps the look consistent + scripts that check it,
so that tokens and context cost a few lines instead of reading files. Stack-agnostic (React, Vue, Svelte, plain HTML, Tailwind, CSS modules).

`FF="python3 ~/.claude/skills/ffcode-style/scripts/ffcode.py"`

## 1. Orient (one call, ~40 lines)
`$FF ui context` → stack, product notes, the contract (colour roles, type/space/radius/z scales, fonts, motion, rules), component count and most used, lint counts.
Do **not** open PRODUCT.md, DESIGN.md, tokens files or the component folder to get this. Read a source file only for the code you will change.

## 2. Contract (`.ffcode/design.toml`, schema in `references/contract.md`)
- Missing → `$FF ui init` drafts it from `DESIGN.md` frontmatter if present, else from the values the code really uses (inferred, guesses marked `*`).
  Ask the user at most: mode (persuade / operate / read / experience), three mood words, brand constraints; they correct names (colours become **roles**) and scales.
  Then `$FF ui sync` (generates the CSS custom properties, and the Tailwind theme if `[ui] tailwind` is set) and `$FF ui palette --fix` (contrast of every role pair, both themes).
- Existing prose files (`PRODUCT.md`, `DESIGN.md`) stay as they are, read through `ui context`; the contract is the machine-readable part and wins on values.
- The contract changes only on purpose: edit `design.toml` → `$FF ui sync` → `$FF uilint` (shows drift) → note the decision (`ffcode-decide`) if it is a standing rule.

## 3. Build
1. **Reuse first:** `$FF ui components [NAME]` (uses, props, file), `$FF find`. Extend a component with a prop before cloning it (S2).
2. **New component:** `$FF ui new Name` scaffolds in the detected convention (ts/js, CSS modules / Tailwind / plain CSS, tokens-based focus style). Then add its states.
3. **Only tokens:** colours, font sizes, spacing, radii, shadows, z-index, durations come from the contract (`var(--color-text)`, theme keys). Need a value that is not there → decide
   whether it is a new token (edit the contract) or a mistake; never a literal.
4. **Every state** (default, hover, focus-visible, active, disabled, loading, empty, error, long/short content), semantic elements, keyboard path, i18n for text, responsive from 320px.
   Aesthetic and craft rules: `references/principles.md`; how to build forms, tables, feedback, motion, failure cases: `references/build.md`. Read the part you need, not both.
5. Follow the product **mode**: operate = scanability and consistency over expression; persuade = hierarchy and one clear action; read = measure and structure; experience = the work leads.

## 4. Verify (cheap first)
1. `$FF check --changed` → includes `uilint` (a11y leads, hard-coded colours, motion, i18n) and, with a contract, `OFFCOLOR OFFSIZE OFFSPACE OFFRADIUS` on the touched files (advisory unless `[ui] strict = true`).
2. Tokens changed → `$FF ui palette`. Many new literals or drift suspected → `$FF uitokens`.
3. Visual check **once**, batched, only if a browser tool is available (load its skill first): the real screen with real content at ~375px and ~1280px (+ dark theme if present); read computed values, look for overflow, focus order,
   states. No browser → say "not visually verified" rather than guessing.
4. Report (≤ 8 lines): what changed, tokens/components added or reused, lint before → after, what was verified and how, what remains.

## Rules of thumb
Existing system beats taste; the brief beats this skill's defaults. Never invent product facts or meaningful copy. Redesign keeps function and product truth, refinement keeps identity.
Large restyles: do the contract first, then migrate file by file with `uilint --changed` (small commits via `ffcode-commit`), not one giant diff.
