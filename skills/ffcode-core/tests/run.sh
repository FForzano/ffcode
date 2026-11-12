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
# design contract: init, palette, sync, offtoken, components, new
mkdir -p src/components
cat > src/components/Card.tsx <<'TSX'
export interface CardProps { title: string; tone?: string }
export function Card({ title }: CardProps) { return <div className="card">{title}</div>; }
TSX
cat > src/App.tsx <<'TSX'
import { Card } from './components/Card';
export const App = () => <Card title="x" />;
TSX
echo '{"dependencies":{"react":"1"}}' > package.json; touch tsconfig.json
cat > .ffcode/design.toml <<'TOML'
[color.light]
surface = "#ffffff"
text = "#111111"
muted = "#bbbbbb"
brand = "#d10c33"
brand-contrast = "#ffffff"
[type]
scale = [12, 14, 16, 24]
[space]
base = 4
scale = [0, 4, 8, 16]
[radius]
scale = [0, 8]
[ui]
output = "src/styles/tokens.css"
TOML
out=$($FF ui palette || true); grep -q "muted" <<<"$out" || fail palette
out=$($FF ui palette --fix || true); grep -q -- "->" <<<"$out" || fail palette-fix
$FF ui sync >/dev/null; grep -q -- "--color-brand: #d10c33" src/styles/tokens.css || fail sync
cat > src/x.css <<'CSS'
.x { color: #123456; font-size: 15px; padding: 7px; border-radius: 5px; }
CSS
git add -A; out=$($FF uilint || true)
for id in OFFCOLOR OFFSIZE OFFSPACE OFFRADIUS; do grep -q "^$id " <<<"$out" || fail "uilint missing $id"; done
$FF ui components | grep -q "Card" || fail components
$FF ui new Badge --dry-run | grep -q "Badge.tsx" || fail new
$FF ui context | grep -q "components: 1" || fail context
$FF ui init --stdout | grep -q "\[type\]" || fail ui-init
# update-check: asks (prints), throttles, applies only with --apply
R="$(mktemp -d)"; git init -q --bare -b main "$R/remote.git"; git clone -q "$R/remote.git" "$R/work" 2>/dev/null
( cd "$R/work" && git config user.email t@t && git config user.name t && git checkout -q -b main && printf '#!/bin/sh\necho installed > "$CLAUDE_SKILLS_DIR/marker"\n' > install.sh && git add -A && git commit -qm init && git push -q -u origin main )
git clone -q "$R/remote.git" "$R/repo"
( cd "$R/work" && echo x > f && git add -A && git commit -qm "new thing" && git push -q )
mkdir "$R/dest"; export FFCODE_REPO="$R/repo" XDG_CACHE_HOME="$R/cache" CLAUDE_SKILLS_DIR="$R/dest"
out=$($FF update-check --force); grep -q "UPDATE_AVAILABLE: 1" <<<"$out" || fail "update-check detect"
grep -q "new thing" <<<"$out" || fail "update-check subjects"
[ -z "$($FF update-check)" ] || fail "update-check throttle"
[ ! -f "$R/repo/f" ] || fail "update-check must not pull by itself"
$FF update-check --apply | grep -q UPDATED || fail "update-check apply"
[ -f "$R/repo/f" ] && [ -f "$R/dest/marker" ] || fail "update-check apply result"
[ -z "$($FF update-check --force)" ] || fail "update-check up to date is silent"
unset FFCODE_REPO XDG_CACHE_HOME CLAUDE_SKILLS_DIR
echo "all ok"
