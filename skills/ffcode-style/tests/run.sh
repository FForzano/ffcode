#!/usr/bin/env bash
# Smoke tests of the ffcode CLI on a throwaway repo. Usage: tests/run.sh
set -euo pipefail
FF="python3 $(cd "$(dirname "$0")/../scripts" && pwd)/ffcode.py"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT; cd "$T"
git init -q -b main; git config user.email t@t; git config user.name t
mkdir pkg tests
cat > pkg/a.py <<'PY'
import os


def f(a, b, c, d, e, g):
    try:
        print("x")
    except Exception:
        pass
    # x = compute(1)
    key = "AKIAABCDEFGHIJKLMNOP"  # TODO
    return a
PY
printf '[project]\nname="t"\n' > pyproject.toml
git add . && git commit -qm init
fail() { echo "FAIL: $1"; exit 1; }
$FF init >/dev/null; [ -f .ffcode/config.toml ] || fail init
out=$($FF lint || true)
for id in PARAM DEBUG CATCH CODE TODO SECRET; do grep -q "^$id " <<<"$out" || fail "lint missing $id"; done
$FF map >/dev/null; $FF find f | grep -q "pkg/a.py:4" || fail find
$FF commitmsg "feat(x): add y" >/dev/null || fail commitmsg-ok
$FF commitmsg "Added y." >/dev/null && fail commitmsg-bad
$FF check --changed >/dev/null || true
echo "all ok"
