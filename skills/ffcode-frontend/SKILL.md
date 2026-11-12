---
name: ffcode-frontend
description: Design and quality work on user interfaces (websites, landing pages, dashboards, app UI, components, design systems) in any web stack - shape a feature before coding, build, critique, audit (accessibility, responsive, performance, tokens), polish, harden (errors, empty states, i18n), adapt to devices, clarify copy, distill, extract tokens/components, document the design system, add motion, tune colour/type/layout - kept consistent through a per-project product and design context. Uses ffcode uilint and uitokens for the mechanical part. Use when the user touches a frontend or says "disegna", "migliora la UI", "rendi coerente lo stile", "audit di accessibilità", "polish", "responsive", "design system", "tokens", "critica questa schermata", or names one of the commands below.
---

# ffcode-frontend

Language- and framework-agnostic (React, Vue, Svelte, plain HTML/CSS, Tailwind). Rules of the code itself stay in `ffcode-style`;
this skill adds the design layer. Inspired by the command set of Impeccable (Apache-2.0), rewritten, compact and wired to `.ffcode/`.
If Impeccable is installed, keep using it for browser-driven variant exploration (`live`, `generate`); everything else is covered here.

`FF="python3 ~/.claude/skills/ffcode-style/scripts/ffcode.py"`

## Setup (once per session, cheap)
1. Read the design context (`references/context.md`): product file (who, purpose, tone, platform) and design file (tokens, type, components, rules). If neither
   exists and the task is new UI or a restyle, run **init** first (3–5 questions max, then write `product.md`/`design.md` from `templates/`); for a small fix on
   existing code, skip init and infer from the code (`$FF uitokens`).
2. For a task on existing UI: `$FF uitokens --top 8` (what values are really used) and `$FF uilint --changed --summary` (known issues) before editing.
3. Pick the **mode** of the surface (`references/principles.md`): persuade (landing, marketing), operate (app, dashboard, admin), read (docs, content), experience (portfolio, showcase).

## Commands (say it or imply it; ask once if two fit)
| Command | Does | Reference |
|---|---|---|
| `init` | Capture product + design context | `context.md` |
| `shape [feature]` | Plan UX/UI before code: users, tasks, states, layout, copy | `shape.md` |
| (build) | New screen/component in the existing system | `principles.md` + `shape.md` |
| `critique [target]` | UX/design review with heuristic scores, ranked fixes | `critique.md` |
| `audit [target]` | Technical quality: a11y, responsive, performance, tokens, theming (scripts first) | `audit.md` |
| `polish [target]` | Final pass before shipping | `polish.md` |
| `harden [target]` | Errors, loading, empty, long text, i18n, permissions, offline | `harden.md` |
| `adapt [target]` | Other devices/sizes/input methods | `adapt.md` |
| `clarify [target]` | Labels, errors, empty states, microcopy | `clarify.md` |
| `distill [target]` | Remove what does not earn its place | `distill.md` |
| `extract [target]` | Repeated values/patterns → tokens and components | `system.md` |
| `document` | Write/refresh `design.md` from the code | `system.md` |
| `motion [target]` | Purposeful animation, reduced-motion | `refine.md` |
| `color` / `type` / `layout` | Tune one axis | `refine.md` |
| `bolder` / `quieter` | Raise or lower visual intensity | `refine.md` |
| `onboard [target]` | First-run, empty states, activation | `harden.md` |

## Protocol for any change to UI
1. Locate with `$FF find` / `$FF refs`; read the component, its styles and one neighbour that does the same job. The existing system wins over taste;
   a new pattern needs a reason written in `design.md`.
2. Implement through tokens and shared components (S2/U1): no new literal colour, size or shadow if a token fits; if none fits, add the token, not the literal.
3. States are part of the job: default, hover, focus-visible, active, disabled, loading, empty, error, long/short/RTL-safe content.
4. Verify in **one batched round**: `$FF check --changed` (includes uilint), then, if a browser tool is available (Chrome extension or built-in browser, load its skill first),
   one desktop and one mobile pass of the real screen with real content; read computed values, don't just look. Without a browser, say what was not visually verified.
5. Report: what changed, tokens/components added or reused, uilint before/after, what was verified and how, what is left (≤ 10 lines).

Never invent product facts, claims or copy that carries meaning; ask or mark as placeholder. Redesign keeps product truth and function; refinement keeps identity.
