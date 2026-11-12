#!/usr/bin/env bash
# Smoke tests of the ffcode CLI on a throwaway repo. Usage: tests/run.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
FF="python3 $HERE/../scripts/ffcode.py"
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
# rules / orient / budget / hooks
$FF rules | grep -q "^- S1 \[judge\]" || fail rules-judge
! $FF rules | grep -q "^- E2 \[auto\]" || fail rules-no-auto
$FF rules E2 | grep -q "^- E2 \[auto\]" || fail rules-id
$FF orient | grep -q "## context.md" || fail orient
$FF budget --check >/dev/null || fail budget
H="$(mktemp -d)"; HOME="$H" $FF hooks install | grep -q installed || fail hooks-install
HOME="$H" $FF hooks install >/dev/null; [ "$(grep -c 'hook stop' "$H/.claude/settings.json")" = 1 ] || fail hooks-idempotent
HOME="$H" $FF hooks install --remove >/dev/null; ! grep -q "hook stop" "$H/.claude/settings.json" || fail hooks-remove
printf 'print(1)\n' > pkg/dbg.py; git add pkg/dbg.py
out=$(echo '{"session_id":"t"}' | XDG_CACHE_HOME="$H/c" $FF hook stop); grep -q '"decision": "block"' <<<"$out" || fail hook-stop-block
[ -z "$(echo '{"session_id":"t"}' | XDG_CACHE_HOME="$H/c" $FF hook stop)" ] || fail hook-stop-once
$FF hooks git >/dev/null; grep -q "ffcode map" .git/hooks/post-merge || fail hooks-git
$FF hooks git --remove >/dev/null; [ ! -f .git/hooks/post-merge ] || fail hooks-git-remove
git rm -qf --cached pkg/dbg.py; rm pkg/dbg.py
python3 "$HERE/consistency.py" >/dev/null || fail "checklist/lint consistency"
# json outputs, config, commit-plan, pr/report
{ $FF lint --json || true; } | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['count']>0 and 'rules' in d" || fail lint-json
{ $FF check --no-lint --json || true; } | python3 -c "import json,sys; assert json.load(sys.stdin)['result'] in ('OK','FAIL')" || fail check-json
$FF config --validate | grep -q "0 error" || fail config-validate
cp .ffcode/config.toml "$H/cfg.bak"; printf '[commit]\nstyle = "bad"\n' > .ffcode/config.toml
$FF config --validate >/dev/null && fail config-validate-bad; cp "$H/cfg.bak" .ffcode/config.toml
printf 'x\n' > .env; $FF commit-plan | grep -q "possible secret" || fail commit-plan; rm .env
$FF pr | grep -q "## Why" || fail pr
$FF report review | grep -q "Mechanical" || fail report-review
# rules.toml, baseline, adr index, tests-for, hotspots, workspace lock/map, glossary
[ -f .ffcode/rules.toml ] && [ -f .ffcode/glossary.md ] || fail init-new-files
{ $FF lint --json || true; } | python3 -c "import json,sys; assert json.load(sys.stdin)['count']>0" || fail pre-baseline
$FF lint --baseline >/dev/null; $FF lint | grep -q "^lint: 0 finding" || fail baseline-hides
printf 'print(9)\n' >> pkg/a.py; { $FF lint || true; } | grep -q "^lint: 1 finding" || fail baseline-new-only
{ $FF lint --no-baseline || true; } | grep -q "finding" || fail no-baseline
git checkout -q pkg/a.py; rm .ffcode/baseline.json
printf '[rule.DEBUG]\nignore = ["pkg/*"]\nreason = "t"\n' > .ffcode/rules.toml
{ $FF lint || true; } | grep -q "^DEBUG" && fail rules-toml-ignore; $FF rules DEBUG | grep -q "Deviations" || fail rules-deviations
printf '[rule.NOPE]\noff = true\n' > .ffcode/rules.toml; $FF config --validate >/dev/null && fail rules-toml-validate; rm .ffcode/rules.toml
$FF adr "First" --rules S6 >/dev/null; $FF adr "Second" --supersedes 1 >/dev/null
$FF adr --list --all | grep -q "superseded by" || fail adr-supersede
$FF adr --list --rule s6 --all | grep -q First || fail adr-list-rule; grep -q "0002" .ffcode/decisions/index.md || fail adr-index
$FF map >/dev/null; $FF tests-for pkg/b.py | grep -q "tests/test_b.py" || fail tests-for
$FF tests-for pkg/a.py | grep -q "no test found" || fail tests-for-missing
$FF hotspots >/dev/null || fail hotspots
printf '[[repo]]\nname="me"\nself=true\nrole="backend"\ncontracts=["pyproject.toml"]\n' > .ffcode/workspace.toml
$FF workspace contracts --accept >/dev/null; [ -f .ffcode/contracts.lock ] || fail lock
echo "# x" >> pyproject.toml; $FF workspace contracts --changed | grep -q CHANGED || fail contracts-changed
$FF workspace map >/dev/null; grep -q "contract" .ffcode/workspace-map.md || fail workspace-map
git checkout -q pyproject.toml; rm .ffcode/workspace.toml .ffcode/contracts.lock
printf '| Widget | a thing | pkg/b.py |\n' >> .ffcode/glossary.md; $FF find widget | grep -q "glossary:" || fail glossary
# architecture
mkdir -p app/controllers app/services; printf 'x=1\n' > app/services/OrderService.py; printf 'x=1\n' > app/services/OtherService.py
printf 'from app.services.order_service import S\nfrom app.repos.x import R\n' > app/controllers/OrderController.py; printf 'x=1\n' > app/services/helpers.py
git add -A; $FF arch infer | grep -q 'name = "service"' || fail arch-infer
# infer: highest pure directory wins, migrations are not a layer, rare edges are flagged and not allowed
mkdir -p app/services/sub app/migrations; printf 'x=1\n' > app/services/sub/ThirdService.py; printf 'x=1\n' > app/services/sub/FourthService.py
printf 'x=1\n' > app/migrations/m240101_create_request.py; printf 'x=1\n' > app/migrations/m240102_other_request.py
printf 'from app.services.order_service import S\n' > app/controllers/SecondController.py
git add -A; inf=$($FF arch infer)
grep -q 'paths = \["app/services/\*\*"\]' <<<"$inf" || fail arch-infer-ancestor
grep -q 'migrations' <<<"$inf" && fail arch-infer-migrations
grep -q 'may_import = \["service"\]' <<<"$inf" || fail arch-infer-edges
$FF arch infer --check | grep -q "ff arch infer --check" || fail arch-check
$FF arch infer --interview | grep -q '"id": "names:service"' || fail arch-interview
$FF arch infer --answer names:service=yes --write | grep -q "answers saved" || fail arch-answer-save
grep -q '^name_pattern = "(?i).\*Service"' .ffcode/architecture.toml || fail arch-answer-applied
grep -q '"names:service" = "yes"' .ffcode/arch-answers.toml || fail arch-answers-file
$FF arch infer --interview | grep -q 'names:service' && fail arch-answered-not-asked
rm .ffcode/architecture.toml; $FF arch infer --write >/dev/null; grep -q '^name_pattern = "(?i).\*Service"' .ffcode/architecture.toml || fail arch-answers-reproduce
out=$($FF arch infer --write || true); grep -q "not overwritten" <<<"$out" || fail arch-no-overwrite
rm -f .ffcode/arch-answers.toml .ffcode/architecture.toml
rm -rf app/services/sub app/migrations app/controllers/SecondController.py; git add -A
printf '[architecture]\nstyle = "t"\n[[layer]]\nname = "controller"\npaths = ["app/controllers/**"]\nmay_import = ["service"]\n[[layer]]\nname = "repository"\npaths = ["app/repos/**"]\n[[layer]]\nname = "service"\npaths = ["app/services/**"]\nname_pattern = ".*Service"\nstem = "{Name}Service"\n' > .ffcode/architecture.toml
out=$({ $FF lint || true; }); grep -q "app/services/helpers.py:1: helpers" <<<"$out" || fail arch-name; grep -q "ARCHDEP" <<<"$out" || fail arch-dep
$FF arch new Foo | grep -q "app/services/FooService.py  missing" || fail arch-new; $FF arch | grep -q "controller" || fail arch-summary
$FF config --validate | grep -q "0 error" || fail arch-validate; $FF orient --no-map | grep -q "## architecture.toml" || fail arch-orient
rm -rf app .ffcode/architecture.toml; git add -A
# upgrade of an older project
U="$(mktemp -d)"; git -C "$U" init -q -b main; ( cd "$U" && printf 'x=1\n' > a.py && $FF init >/dev/null && rm .ffcode/rules.toml .ffcode/version && printf 'map.md\n' > .ffcode/.gitignore )
$FF upgrade --root "$U" --dry-run | grep -q "create rules.toml" && [ ! -f "$U/.ffcode/rules.toml" ] || fail upgrade-dry
$FF upgrade --root "$U" >/dev/null; [ -f "$U/.ffcode/rules.toml" ] && grep -q workspace-map "$U/.ffcode/.gitignore" && [ "$(cat "$U/.ffcode/version")" = 2 ] || fail upgrade
[ "$($FF upgrade --root "$U" | grep -c create)" = 0 ] || fail upgrade-idempotent
HOME="$H" $FF hooks status >/dev/null && fail hooks-status-before; HOME="$H" $FF hooks install >/dev/null; HOME="$H" $FF hooks status | grep -q "installed (user)" || fail hooks-status
out=$(HOME="$H" XDG_CACHE_HOME="$H/c2" $FF orient --no-map); grep -q "hooks are not installed" <<<"$out" && fail hint-when-installed
HOME="$H" $FF hooks install --remove >/dev/null; out=$(HOME="$H" XDG_CACHE_HOME="$H/c2" $FF orient --no-map); grep -q "hooks are not installed" <<<"$out" || fail hint
out=$(HOME="$H" XDG_CACHE_HOME="$H/c2" $FF orient --no-map); ! grep -q "hooks are not installed" <<<"$out" || fail hint-once
A="$(mktemp -d)"; git -C "$A" init -q -b main; ( cd "$A" && printf 'x=1\n' > a.py && $FF init >/dev/null && rm .ffcode/rules.toml .ffcode/version )
err=$($FF lint --root "$A" 2>&1 >/dev/null || true); grep -q "upgraded from schema 1 to 2 automatically" <<<"$err" || fail auto-upgrade
[ -f "$A/.ffcode/rules.toml" ] && [ "$(cat "$A/.ffcode/version")" = 2 ] || fail auto-upgrade-result
[ -z "$($FF lint --root "$A" 2>&1 >/dev/null || true)" ] || fail auto-upgrade-once
rm "$A/.ffcode/version" "$A/.ffcode/rules.toml"; FFCODE_NO_AUTO_UPGRADE=1 $FF lint --root "$A" >/dev/null 2>&1 || true; [ ! -f "$A/.ffcode/rules.toml" ] || fail auto-upgrade-optout
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
# flow: entry points, chains, effects, impact, generated cards; sync: self-configuration. A throwaway HOME keeps the user's Claude settings out of it.
OLDHOME="$HOME"; FH="$(mktemp -d)"; export HOME="$FH"
FL="$(mktemp -d)"; git -C "$FL" init -q -b main; git -C "$FL" config user.email t@t; git -C "$FL" config user.name t
mkdir -p "$FL/app"
cat > "$FL/app/api.py" <<'PY'
from fastapi import FastAPI
from app.services import OrderService

app = FastAPI()


@app.post("/orders")
def create_order(payload: OrderIn) -> OrderOut:
    svc = OrderService()
    return svc.place(payload)
PY
cat > "$FL/app/services.py" <<'PY'
import requests


class OrderService:
    def place(self, p):
        self.audit(p)
        requests.post("https://x.example/y")
        raise ValueError("no")

    def audit(self, p):
        db.session.add(p)
PY
cat > "$FL/app/cli.py" <<'PY'
import click
from app.services import OrderService


@click.command("sync-orders")
def sync_orders():
    OrderService().audit(1)
PY
cat > "$FL/server.js" <<'JS'
const express = require('express');
const app = express();
function listUsers(req, res) { res.json([]); }
app.get('/users', listUsers);
app.post('/users', (req, res) => { fetch('http://x.example'); res.send('ok'); });
JS
git -C "$FL" add -A; git -C "$FL" commit -qm init
out=$($FF flow --root "$FL"); for k in "POST /orders" "GET /users" "sync-orders"; do grep -q "$k" <<<"$out" || fail "flow-list $k"; done
out=$($FF flow --root "$FL" "POST /orders"); grep -q "OrderService::place" <<<"$out" || fail flow-chain
grep -q "http out" <<<"$out" || fail flow-effect-http; grep -q "db write" <<<"$out" || fail flow-effect-db; grep -q "ValueError" <<<"$out" || fail flow-errors
grep -q "(payload: OrderIn) -> OrderOut" <<<"$out" || fail flow-signature
$FF flow --root "$FL" "POST /users" | grep -q "http out" || fail flow-inline-handler
$FF flow --root "$FL" "GET /users" | grep -q "listUsers" || fail flow-named-handler
out=$($FF flow --root "$FL" --impact app/services.py); grep -q "POST /orders" <<<"$out" && grep -q "sync-orders" <<<"$out" || fail flow-impact
$FF flow --root "$FL" --mermaid "POST /orders" | grep -q "sequenceDiagram" || fail flow-mermaid
$FF flow --root "$FL" --write .ffcode/flows >/dev/null; $FF flow --root "$FL" --check .ffcode/flows | grep -q "up to date" || fail flow-check
echo "def extra(): pass" >> "$FL/app/services.py"; sed -i.bak 's/audit(p)/audit2(p)/' "$FL/app/services.py"; rm -f "$FL/app/services.py.bak"
! $FF flow --root "$FL" --check .ffcode/flows >/dev/null || fail flow-check-stale
$FF flow --root "$FL" --doctor | grep -q "entry points: 4" || fail flow-doctor
# sync: a skill used in a repo without .ffcode creates it; a plain prompt does not; the prompt hook adds NEEDS once per session
SY="$(mktemp -d)"; git -C "$SY" init -q -b main; printf 'x=1\n' > "$SY/a.py"
echo '{"prompt":"fix the typo","cwd":"'$SY'","session_id":"s1"}' | $FF hook prompt >/dev/null; [ ! -d "$SY/.ffcode" ] || fail sync-plain-prompt
echo '{"prompt":"/ffcode-write add a thing","cwd":"'$SY'","session_id":"s1"}' | $FF hook prompt | grep -q "created" || fail sync-skill-prompt
[ -f "$SY/.ffcode/config.toml" ] || fail sync-created
out=$(echo '{"prompt":"again","cwd":"'$SY'","session_id":"s1"}' | $FF hook prompt); ! grep -q "created" <<<"$out" || fail sync-idempotent
$FF orient --root "$SY" --no-map | grep -q "^# root" || fail sync-orient
$FF sync --root "$SY" --json | grep -q '"needs"' || fail sync-json
rm -rf "$FL" "$SY" "$FH"; export HOME="$OLDHOME"
echo "all ok"
