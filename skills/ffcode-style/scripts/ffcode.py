#!/usr/bin/env python3
"""ffcode: one entry point. ffcode.py {init|map|find|refs|lint|check|untested|commitmsg|workspace|release|debug|adr} [args]"""
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
SUB = {"init": ("init", None), "map": ("mapper", "build"), "find": ("mapper", "find"), "lint": ("lint", None),
       "check": ("check", None), "commitmsg": ("commitmsg", None), "workspace": ("workspace", None),
       "refs": ("refs", None), "untested": ("untested", None), "adr": ("adr", None), "debug": ("debug", None), "release": ("release", None)}

if len(sys.argv) < 2 or sys.argv[1] not in SUB:
    sys.exit(__doc__)
mod, pre = SUB[sys.argv[1]]
sys.argv = [mod, *([pre] if pre else []), *sys.argv[2:]]
m = __import__(mod)
sys.exit(m.main() or 0)
