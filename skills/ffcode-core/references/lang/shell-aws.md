# Shell, Terraform, AWS/ops
- Bash: `#!/usr/bin/env bash`, `set -euo pipefail`, quote everything, `shellcheck` clean, functions for reusable parts, `usage()` on `-h`, no logic duplicated between subcommands (shared lib).
- Destructive or prod-affecting commands: confirmation in prod, `--yes` for non-interactive, `--dry-run`, print what will happen first. Never print secrets.
- Infra as code: no manual console changes; plan before apply; environments (dev/prod) differ by variables, not by forked code. Secrets via SSM/Secrets Manager.
- Deploy order across repos and rollbacks are documented in `how-to/`; keep README command examples runnable.
- Dockerfiles: pinned base versions, multi-stage, non-root, small context (`.dockerignore`).
