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
$FF refs f | grep -q "usage" || fail refs
$FF adr "Use X" | grep -q "0001-use-x" || fail adr
echo "boom at pkg/a.py:4" | $FF debug log - | grep -q "frames" || fail debug
$FF untested --base HEAD >/dev/null || true
# diffcov (Cobertura + lcov), failwithout, mutate
git checkout -q -b feat
cat > pkg/b.py <<'PY'
def used():
    return 1


def unused():
    return 2
PY
cat > tests/test_b.py <<'PY'
from pkg.b import used
assert used() == 1
PY
cat > cov.xml <<'XML'
<coverage><sources><source>.</source></sources><packages><package><classes>
<class filename="pkg/b.py"><lines><line number="2" hits="1"/><line number="6" hits="0"/></lines></class>
</classes></package></packages></coverage>
XML
printf 'SF:%s/pkg/b.py\nDA:2,1\nDA:6,0\nend_of_record\n' "$PWD" > cov.info
git add -A; git -c core.hooksPath=/dev/null commit -qm "feat: b"
$FF diffcov --base main --report cov.xml | grep -q "unused: 1 line" || fail diffcov-cobertura
$FF diffcov --base main --report cov.info | grep -q "50%" || fail diffcov-lcov
$FF diffcov --base main --report cov.xml --min 90 >/dev/null && fail diffcov-min
printf '[commands]\ntest = "python3 tests/test_b.py"\n[check]\nbase = "main"\n' > .ffcode/config.toml
$FF failwithout | grep -q "FAIL without" || fail failwithout
[ -f pkg/b.py ] || fail restore
printf '[mutation]\ncritical = ["pkg/*.py"]\ncommand = "echo mutating {files}"\n[check]\nbase = "main"\n' > .ffcode/config.toml
$FF mutate | grep -q "mutating pkg/b.py" || fail mutate
# uilint / uitokens
mkdir -p ui; cat > ui/a.html <<'HTML'
<html><body><img src="x.png"><input type="text"><div onClick="go()">x</div></body></html>
HTML
cat > ui/a.css <<'CSS'
.a { color: #777777; background-color: #ffffff; outline: none; font-size: 10px; transition: all .2s; z-index: 999; }
CSS
git add -A; out=$($FF uilint || true)
for id in IMGALT FIELDLABEL CLICKDIV HTMLLANG CONTRAST OUTLINE TINYFONT TRANSALL ZINDEX HARDCOLOR; do grep -q "^$id " <<<"$out" || fail "uilint missing $id"; done
$FF uitokens | grep -q "#777777" || fail uitokens
echo "all ok"
