#!/usr/bin/env python3
"""ff - the ffcode CLI. `ff COMMAND --help` for the options of one command.
  orient                 context + style + state + head of the map in one call (start of every task)
  rules [--judge]        checklist rules that need judgment + notes of the project's languages
  map | find NAME | refs NAME     repo map; where is a symbol (file:line); all usages by file
  lint | check [--changed|--staged]   mechanical rules; configured format/lint/typecheck/test/build, compressed
  init                   create .ffcode/ (never overwrites)         adr "Title"   new decision record
  commitmsg "msg"        validate a commit message                  debug log|bisect   compress a log / git bisect
  diffcov | failwithout | mutate | untested   test-quality tools (see ffcode-write/references/tests.md)
  ui ... | uilint | uitokens          design contract and UI lint (ffcode-write/references/ui.md)
  workspace ... | release  multi-repo (ffcode-workspace)
  config --validate      check config.toml / design.toml / workspace.toml (schema, typos, commands on PATH)
  pr | report review|summary   facts for the PR description / review / final summary, Claude fills only the why
  commit-plan            group the changed files into proposed commits, flag what to leave out
  tests-for FILE.. | --changed [--run]   the tests that cover those files (generated tests-map)   hotspots   churn x size ranking
  arch [show L | new NAME | infer]   project architecture (layers, naming, allowed imports) and what a new entity needs
  upgrade [--dry-run] [--all DIR]   bring already initialized projects up to the current .ffcode/ layout
  budget [--check]       token size of the skills               update-check [--apply]   weekly update check
  hooks install|git      Claude Code hooks / git hooks          hook session-start|stop   (called by those hooks)"""
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
SUB = {"init": ("init", None), "map": ("mapper", "build"), "find": ("mapper", "find"), "lint": ("lint", None),
       "check": ("check", None), "commitmsg": ("commitmsg", None), "workspace": ("workspace", None),
       "refs": ("refs", None), "untested": ("untested", None), "adr": ("adr", None), "debug": ("debug", None), "release": ("release", None),
       "diffcov": ("diffcov", None), "failwithout": ("failwithout", None), "mutate": ("mutate", None),
       "uilint": ("uilint", None), "uitokens": ("uitokens", None), "ui": ("ui", None), "update-check": ("update_check", None),
       "rules": ("rules", None), "upgrade": ("upgrade", None), "arch": ("arch", None), "tests-for": ("indexes", "tests-for"), "hotspots": ("indexes", "hotspots"), "config": ("config", None), "pr": ("report", "pr"), "report": ("report", None), "commit-plan": ("commitplan", None), "orient": ("orient", None), "budget": ("budget", None),
       "hook": ("hooks", "hook"), "hooks": ("hooks", "hooks")}

if len(sys.argv) < 2 or sys.argv[1] not in SUB:
    print(__doc__); sys.exit(0 if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help") else 2)
mod, pre = SUB[sys.argv[1]]
if sys.argv[1] not in ("init", "upgrade", "hooks", "budget", "config", "update-check", "adr"):
    import upgrade
    from common import find_root
    _root = sys.argv[sys.argv.index("--root") + 1] if "--root" in sys.argv[:-1] else None
    upgrade.auto(find_root(_root))
sys.argv = [mod, *([pre] if pre else []), *sys.argv[2:]]
m = __import__(mod)
sys.exit(m.main() or 0)
