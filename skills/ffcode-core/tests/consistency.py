"""Checklist and lint must agree: every bracketed lead in checklist.md names rules that exist in lint/uilint, and every lint rule is cited."""
import re, sys
from pathlib import Path
S = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(S / "scripts"))
import lint, uilint  # noqa: E402
text = (S / "references" / "checklist.md").read_text()
cited = set(re.findall(r"\[([A-Z][A-Z ]+)\]", text))
known = set(lint.RULES) | set(getattr(uilint, "RULES", {}))
cited -= {"CHECK"}
bad = [f"cited in checklist but no rule: {r}" for r in cited if not any(x in known for x in r.split())]
tokens = {t for c in cited for t in c.split()}
bad += [f"lint rule not cited in the checklist: {r}" for r in lint.RULES if r not in tokens]
print("\n".join(bad) or "checklist/lint consistent"); sys.exit(1 if bad else 0)
