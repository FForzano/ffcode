---
name: ffcode-map
description: Build and use the compact repository map (.ffcode/map.md) and the symbol index to navigate a codebase with few tokens - layout, entry points, commands, symbols per file, and "where is X defined". Use when starting work in an unfamiliar or large repo, when the user says "mappa il repo", "dove si trova X", "aggiorna la mappa", or before any search that would otherwise sweep the whole tree.
---

# ffcode-map

`FF="python3 ~/.claude/skills/ffcode-style/scripts/ffcode.py"`

- **Orient:** read `.ffcode/map.md` (create it with `$FF map` if missing or older than the last pulls). It lists directories (files, lines),
  entry points/manifests, configured commands and top-level symbols per file with line numbers.
- **Locate:** `$FF find NAME` (substring, case-insensitive) → `file:line`. Then read only that range (`Read` with offset/limit).
- **Refresh** after structural changes (new modules, moves): `$FF map`. Stale symbols are a hint, not a truth: confirm before editing.
- Symbols are extracted for Python, PHP, TypeScript/JS, MATLAB, shell, Terraform; other files appear in the layout only.
- Big repos: the map is capped at 400 lines; use `find` and per-directory reads instead of raising the cap.
- Beyond symbols (architecture, why), the map does not replace `context.md`; if you find a durable fact the map cannot hold, add one line to `context.md`.
