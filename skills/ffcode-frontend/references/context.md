# Design context (product + design)

Two small files give every UI task its constants. Resolution order for each (first that exists wins):
1. paths in `.ffcode/config.toml` `[frontend] product = "..."`, `design = "..."`;
2. root `PRODUCT.md` / `DESIGN.md` (kept as they are if another tool already owns them: never migrated or renamed);
3. `.ffcode/product.md` / `.ffcode/design.md` (created from `templates/` by `init`).
Read them once per session; they are short by design. Update them in the same commit as the change that makes them stale (G4).

**product** = who uses it, what for, the situation of use (device, light, stress, frequency), tone of voice, platform, language(s), hard constraints (brand, legal, accessibility level).
**design** = tokens (colour roles, type scale, spacing, radii, elevation, motion), component inventory with when-to-use, layout rules, do/don't, where tokens live in code.

## init (when missing)
Ask only what the code cannot tell (max 5, one message): audience and primary tasks, tone in three adjectives, brand constraints (logo, colours, fonts), supported devices/languages, accessibility target.
Infer the rest with `$FF uitokens` (palette, type, spacing really in use) and the dependency list (framework, UI kit, i18n). Write both files from the templates; mark inferred items `(inferred)`.
Show the user the diff; they correct it. Commit nothing unasked.
