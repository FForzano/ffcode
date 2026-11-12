#!/usr/bin/env bash
# Install / update / remove the ffcode skills in ~/.claude/skills.
#   ./install.sh              symlink (edits and git pull apply immediately)
#   ./install.sh --copy       plain copies (re-run after every change)
#   ./install.sh --update     git pull (if a remote exists) and re-install
#   ./install.sh --uninstall  remove the skills installed from this repo
#   ./install.sh --status     show what is installed
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
mode=link; action=install
for a in "$@"; do case "$a" in
  --copy) mode=copy ;; --update) action=update ;; --uninstall) action=uninstall ;; --status) action=status ;;
  -h|--help) sed -n '2,8p' "$0"; exit 0 ;; *) echo "unknown option: $a" >&2; exit 2 ;; esac; done

skills=(); for d in "$REPO"/skills/*/; do skills+=("$(basename "$d")"); done
mkdir -p "$DEST"
BIN="${FFCODE_BIN_DIR:-$HOME/.local/bin}"

state() { local t="$DEST/$1"
  if [ -L "$t" ]; then [ "$(readlink "$t")" = "$REPO/skills/$1" ] && echo linked || echo "linked elsewhere -> $(readlink "$t")"
  elif [ -d "$t" ]; then diff -rq "$REPO/skills/$1" "$t" >/dev/null 2>&1 && echo "copy (up to date)" || echo "copy (DIFFERS)"
  else echo "not installed"; fi; }

install_one() { local s="$1" t="$DEST/$1"
  if [ -e "$t" ] && [ ! -L "$t" ]; then mv "$t" "$t.bak.$(date +%Y%m%d%H%M%S)"; echo "  moved existing $s to backup"; fi
  [ -L "$t" ] && rm "$t"
  if [ "$mode" = link ]; then ln -s "$REPO/skills/$s" "$t"; else cp -R "$REPO/skills/$s" "$t"; fi
  echo "  $s: $(state "$s")"; }

link_cli() { mkdir -p "$BIN"; ln -sfn "$DEST/ffcode-core/scripts/ff" "$BIN/ff"; echo "  ff: $BIN/ff"
  case ":$PATH:" in *":$BIN:"*) ;; *) echo "  warning: $BIN is not in PATH (add it to your shell profile)" ;; esac; }
unlink_cli() { [ -L "$BIN/ff" ] && case "$(readlink "$BIN/ff")" in "$DEST"/*) rm "$BIN/ff"; echo "  removed $BIN/ff" ;; esac; true; }

prune() { for l in "$DEST"/ffcode-*; do [ -L "$l" ] && [ ! -e "$l" ] && rm "$l" && echo "  removed stale $(basename "$l")"; done; true; }
case "$action" in
  update) git -C "$REPO" remote | grep -q . && git -C "$REPO" pull --ff-only || echo "no remote; reinstalling"
          prune
          for s in "${skills[@]}"; do install_one "$s"; done ;;
  install) prune; for s in "${skills[@]}"; do install_one "$s"; done ;;
  uninstall) for s in "${skills[@]}"; do t="$DEST/$s"; if [ -L "$t" ] && [ "$(readlink "$t")" = "$REPO/skills/$s" ]; then rm "$t"; echo "  removed $s"; elif [ -d "$t" ]; then echo "  $s: copy left in place (remove by hand)"; fi; done ;;
  status) for s in "${skills[@]}"; do echo "  $s: $(state "$s")"; done ;;
esac
if [ "$action" = install ] || [ "$action" = update ]; then echo "$REPO $mode" > "$DEST/.ffcode-repo"; link_cli; fi
if [ "$action" = uninstall ]; then rm -f "$DEST/.ffcode-repo"; unlink_cli; fi
if [ "$action" = status ]; then echo "  ff: $([ -x "$BIN/ff" ] && readlink "$BIN/ff" || echo "not installed")"; fi
if [ "$action" != uninstall ]; then
  python3 -c 'import sys,tomllib; assert sys.version_info>=(3,11)' 2>/dev/null && echo "python3 OK (>=3.11)" || echo "WARNING: python3 >= 3.11 required"
  echo "New Claude Code session needed to pick up the skills."
fi
