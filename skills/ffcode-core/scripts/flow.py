"""Entry points and the logic behind each one, derived from the code at query time (nothing to keep up to date).
  ff flow                         every entry point (HTTP routes, CLI commands, jobs, listeners), one line each
  ff flow QUERY                   the card of one entry point: chain by layer, data types, access rules, effects, errors
                                  QUERY = a route ("POST api/lesson"), a command, Class::method, file:line, or a symbol
  ff flow --impact FILE|SYMBOL    which entry points reach that file or symbol (what a change can affect)
  ff flow --mermaid QUERY         the same card as a Mermaid sequence diagram
  ff flow --write [DIR]           cards + INDEX.md for humans (default .ffcode/flows, generated); --check DIR fails if DIR is stale
  ff flow --doctor                what was detected, what was not, and why;  --interview / --answer id=value: the few questions only a developer can answer
Options: --kind http|cli|job|event, --depth N, --limit N, --json, --tests (include test files)
It works from a cached, incremental parse (`.ffcode/cache/flow.json`), not from prose: language-light, no AST, so dynamic dispatch
(containers, string-built calls, reflection) shows as `unresolved` instead of being guessed."""
from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from collections import Counter, defaultdict
from fnmatch import fnmatch
from pathlib import Path

import flowentry
import flowparse
from common import DIRNAME, find_root
from report import TEST

ANSWERS = "flow-answers.toml"
KINDS = ("http", "cli", "job", "event")
MAX_NODES = 45
DATA_LAYER = re.compile(r"(?i)form|request|dto|schema|resource|response|input|output|payload|view|serializer|command$|query$")


# ---- build --------------------------------------------------------------------------------------------------------

class Model:
    def __init__(self, root: Path, tests: bool = False):
        self.root = root
        self.cfg = flowentry.load_config(root)
        parsed = flowparse.load_all(root, flowentry.signature(root),
                                    lambda rel, lang, text, nc, d: flowentry.scan_file(rel, lang, text, nc, d, self.cfg))
        ign = self.cfg.get("ignore", [])
        self.parsed = {k: v for k, v in parsed.items() if (tests or not TEST.search(k)) and not any(fnmatch(k, g) for g in ign)}
        self.idx = flowentry.Index(self.parsed)
        self.entries = flowentry.entries(root, self.parsed, self.idx)
        import arch
        self.arch = arch.load(root)
        self.depth = int(self.cfg.get("depth", 3))
        self.answers = load_answers(root)

    def layer(self, rel: str) -> str:
        if self.arch:
            import arch
            l = arch.layer_of(self.arch, rel)
            if l: return l["name"]
        parts = Path(rel).parts
        return parts[0] if len(parts) > 1 else "."

    # -- call resolution ------------------------------------------------------------------------------------------
    def callees(self, d: dict):
        """(resolved callables, unresolved call names) of one callable."""
        idx, f = self.idx, self.parsed.get(d["f"], {"ftypes": [], "imports": []})
        body_types = set(d.get("types", []))
        cand_types = [t for t in list(body_types) + list(f.get("ftypes", [])) if t in idx.classes]
        cand_types = list(dict.fromkeys(cand_types))
        out, unresolved, seen = [], [], set()

        def add(m):
            if m and idx.is_iface(m): return False
            if m and (m["f"], m["l"]) not in seen and not (m["f"] == d["f"] and m["l"] == d["l"]):
                seen.add((m["f"], m["l"])); out.append(m)
            return bool(m)

        owner = d.get("o")
        for recv, op, name in d.get("calls", []):
            ok = False
            if not op and not recv:
                fs = sorted(idx.funcs.get(name, []), key=lambda x: x["f"] != d["f"])
                ok = add(fs[0]) if fs else (add(idx.method_of(owner, [name])) if owner and not f.get("lang") == "php" else False)
            elif recv in ("this", "self", "static", "parent", "cls", "base") and owner:
                ok = add(idx.method_of(owner, [name], prefer_file=d["f"]))
                if not ok and recv == "parent":
                    for c in idx.classes.get(owner, []):
                        for p in c.get("ext", []): ok = ok or add(idx.method_of(p, [name]))
            elif recv[:1].isupper() and recv in idx.classes:
                ok = add(idx.method_of(recv, [name]))
            elif recv and recv[:1].islower() and op in (".", "::") and any(Path(k).stem == recv for k in idx.byfile):
                fs = [x for x in idx.funcs.get(name, []) if Path(x["f"]).stem == recv]
                ok = add(fs[0]) if fs else False
            if not ok and (op or recv) and recv not in ("this", "self", "static", "parent", "cls"):
                hits = []
                for t in cand_types:
                    m = idx.method_of(t, [name])
                    if m: hits.append((t in body_types, m))
                if hits:
                    best = [m for inb, m in hits if inb] or [m for _, m in hits]
                    best = [m for m in best if not idx.is_iface(m)]
                    if len({(m["f"], m["l"]) for m in best}) == 1: ok = add(best[0])
                    elif best:
                        near = [m for m in best if len(recv) >= 3 and (recv.lower() in m["o"].lower() or m["o"].lower() in recv.lower())]
                        ok = add(near[0]) if near else False
            if not ok and not (recv in ("this", "self", "static") or name in flowparse.KEYWORDS) and len(recv) >= 3:
                ms = [x for x in idx.meths.get(name, []) if not idx.is_iface(x) and (recv.lower() in x["o"].lower() or x["o"].lower() in recv.lower())]
                if len(ms) == 1: add(ms[0])
        return out, unresolved

    def expand(self, root_def: dict, depth: int | None = None):
        """Tree {d, kids, again}: callees breadth-limited, repeats shown once."""
        depth = self.depth if depth is None else depth
        seen, count = set(), [0]

        def rec(d, lvl):
            node = {"d": d, "kids": [], "again": False}
            key = (d["f"], d["l"])
            if key in seen: node["again"] = True; return node
            seen.add(key); count[0] += 1
            if lvl >= depth or count[0] >= MAX_NODES: return node
            for c in self.callees(d)[0]:
                node["kids"].append(rec(c, lvl + 1))
            return node
        return rec(root_def, 0)

    def nodes(self, tree):
        out, stack, seen = [], [tree], set()
        while stack:
            n = stack.pop(0)
            k = (n["d"]["f"], n["d"]["l"])
            if k not in seen: seen.add(k); out.append(n["d"])
            stack += n["kids"]
        return out

    def inline_def(self, rel: str, line: int):
        """Pseudo callable for an inline handler: the block that starts at `line`."""
        p = self.root / rel
        if not p.is_file(): return None
        text = p.read_text(errors="replace"); lang = flowparse.flang(rel) or "javascript"
        nc, ns = flowparse.mask(text, lang)
        offs = flowparse._line_offsets(ns)
        sp = flowparse._brace_span(ns, offs[line - 1], offs[min(len(offs) - 1, line + 40)]) if lang not in flowparse.INDENT else None
        end = ns.count("\n", 0, sp[1]) + 1 if sp else line
        a = flowparse._analyze("\n".join(ns.split("\n")[line - 1:end]), "\n".join(nc.split("\n")[line - 1:end]), "\n".join(text.split("\n")[line - 1:end]))
        a.update({"k": "def", "n": "(inline handler)", "l": line, "e": end, "f": rel, "o": None, "sig": ""})
        return a


# ---- card ---------------------------------------------------------------------------------------------------------

def qname(d: dict) -> str:
    return f"{d['o']}::{d['n']}" if d.get("o") else d["n"]


def label(e: dict) -> str:
    return f"{e['method'] + ' ' if e['method'] else ''}{e['label']}".strip()


def aggregate(m: Model, e: dict, tree) -> dict:
    nodes = m.nodes(tree) if tree else []
    eff, vend, thr, grd, types = defaultdict(dict), {}, {}, [], {}
    for d in nodes:
        for cat, hits in d.get("eff", {}).items():
            eff[cat].setdefault(qname(d), hits)
        for v in d.get("vend", []): vend.setdefault(v, qname(d))
        for t in d.get("thr", []): thr.setdefault(t, qname(d))
        for t in d.get("types", []):
            if t in m.idx.classes: types.setdefault(t, m.idx.classes[t][0])
    for g in (tree["d"].get("grd", []) if tree else []): grd.append(g)
    if tree and tree["d"].get("o"):
        for c in m.idx.classes.get(tree["d"]["o"], []):
            grd += [g for g in c.get("grd", []) if g not in grd]
    ext = [t for t, v in m.answers.items() if t.startswith("effect:") and v == "external"]
    libs = lib_leaf(m)
    used = sorted({lib for d in nodes for t in d.get("types", []) for lib in [libs.get(d["f"], {}).get(t)] if lib and f"effect:{lib}" in ext})
    models = sorted(t for t, c in types.items() if re.search(r"(?i)(^|/)(models?|entities|entity|domain|schemas?|orm)(/|$)", c["f"])
                    and not DATA_LAYER.search(t) and not DATA_LAYER.search(m.layer(c["f"])) and not c.get("iface"))
    data = sorted(t for t, c in types.items() if DATA_LAYER.search(m.layer(c["f"])) or DATA_LAYER.search(t))
    return {"eff": eff, "vend": vend, "thr": thr, "grd": grd, "models": models, "data": data, "libs": used}


def lib_leaf(m: Model) -> dict:
    """{file: {leaf class/alias: library root}} for imports that do not resolve inside the repo."""
    stems = {Path(k).stem.lower() for k in m.parsed}
    out = {}
    for rel, f in m.parsed.items():
        mp = {}
        for imp in f.get("imports", []):
            if imp.startswith("."): continue
            parts = [p for p in re.split(r"[\\./]+", imp) if p]
            if len(parts) < 1: continue
            root_tok = parts[0].lower().lstrip("@")
            if parts[-1].lower() in stems or root_tok in m.top_dirs(): continue
            mp[parts[-1]] = root_tok
        out[rel] = mp
    return out


Model.top_dirs = lambda self: {p.split("/")[0].lower() for p in self.parsed}


def render_tree(m: Model, node, prefix="", last=True, first=True, lines=None):
    """Tree lines; a callable already shown above is not repeated (counted in the caller's note)."""
    lines = [] if lines is None else lines
    d = node["d"]
    here = f"{qname(d)}  [{m.layer(d['f'])}] {d['f']}:{d['l']}"
    lines.append(here if first else f"{prefix}{'└ ' if last else '├ '}{here}")
    kid_prefix = "" if first else prefix + ("  " if last else "│ ")
    kids = [k for k in node["kids"] if not k["again"]]
    for i, k in enumerate(kids):
        render_tree(m, k, kid_prefix, i == len(kids) - 1, False, lines)
    return lines


def signature_line(d: dict) -> str:
    return d.get("sig", "")


def access_rules(m: Model, h: dict) -> list[str]:
    """Config-array access rules that name this action ('actions' => ['single-create', ...], 'roles' => [...]), compacted."""
    cls = next((c for c in m.idx.classes.get(h.get("o") or "", []) if c["f"] == h["f"]), None)
    if not cls: return []
    p = m.root / h["f"]
    try: text = "\n".join(p.read_text(errors="replace").split("\n")[cls["l"] - 1:cls["e"]])
    except OSError: return []
    base = re.sub(r"^action", "", h["n"])
    ids = {re.sub(r"(?<!^)(?=[A-Z])", "-", base).lower(), h["n"], base[:1].lower() + base[1:]} - {""}
    out = []
    for i in ids:
        for mm in re.finditer(r"""['"]""" + re.escape(i) + r"""['"]""", text):
            depth, j = 0, mm.start()
            levels = []
            while j >= 0 and len(levels) < 4:                      # enclosing [...] blocks, innermost first
                c = text[j]
                if c == "]": depth += 1
                elif c == "[":
                    if depth == 0: levels.append(j)
                    else: depth -= 1
                j -= 1
            for st in levels:
                d, k = 0, st
                while k < len(text):
                    d += text[k] == "["; d -= text[k] == "]"
                    k += 1
                    if d == 0: break
                block = text[st:k]
                if re.search(r"""['"](?:allow|roles|permissions?|matchCallback)['"]""", block) and "actions" in block:
                    roles = re.search(r"""['"]roles['"]\s*=>\s*(\[[^\]]*\])""", block)
                    allow = re.search(r"""['"]allow['"]\s*=>\s*(\w+)""", block)
                    checks = list(dict.fromkeys(re.findall(r"->\s*((?:is|has|can|check|require|assert)\w*)\(", block)))
                    line = ("allow" if allow and allow.group(1) == "true" else "deny" if allow else "rule") + (f" roles={roles.group(1)}" if roles else "")
                    if checks: line += " + " + ", ".join(c + "()" for c in checks[:5])
                    if line not in out: out.append(line)
                    break
    return out[:3]


def card(m: Model, e: dict, depth: int | None = None) -> str:
    h = e["handler"]
    if not h and e.get("inline") and isinstance(e["inline"], tuple) and e["inline"][0] not in ("script", "make", "shell"):
        h = m.inline_def(*e["inline"]) if len(e["inline"]) == 2 and isinstance(e["inline"][1], int) else None
    out = [f"{label(e)}   [{e['kind']}]  {e['file']}:{e['line']}"]
    if not h:
        out.append(f"  handler: not resolved ({e.get('why') or 'inline'})")
        if e.get("inline") and e["inline"][0] == "script":
            out += ["  steps:"] + ["    " + l for l in script_steps(m.root, e["inline"][1] if e["inline"][1] != "script" else e["file"], e["file"])]
        elif e.get("inline") and e["inline"][0] == "shell": out.append("  runs: " + str(e["inline"][1])[:140])
        elif e["file"] == "Makefile": out += ["  recipe:"] + ["    " + l for l in make_recipe(m.root, e["line"])]
        return "\n".join(out)
    tree = m.expand(h, depth)
    ag = aggregate(m, e, tree)
    sig = signature_line(h)
    out.append(f"  handler: {qname(h)}{sig}  {h['f']}:{h['l']}")
    if ag["data"]: out.append("  data types: " + ", ".join(ag["data"][:10]))
    acc = access_rules(m, h) + [g for g in ag["grd"] if "'roles'" not in g]
    if acc: out.append("  access: " + " | ".join(acc[:5]))
    out.append("  chain:")
    out += ["    " + l for l in render_tree(m, tree)]
    eff = []
    for cat in ("db write", "db read", "transaction", "queue", "http out", "email", "file/storage", "process", "cache"):
        if cat in ag["eff"]:
            srcs = sorted(ag["eff"][cat])
            eff.append(f"{cat} ({', '.join(srcs[:2])}{f' +{len(srcs) - 2}' if len(srcs) > 2 else ''})")
    if ag["models"]: eff.append("models: " + ", ".join(ag["models"][:10]))
    ext = sorted(set(ag["vend"]) | set(ag["libs"]))
    if ext: eff.append("external: " + ", ".join(ext[:8]))
    if eff: out.append("  effects: " + " · ".join(eff))
    if ag["thr"]: out.append("  errors: " + ", ".join(sorted(ag["thr"])[:10]))
    n = len(m.nodes(tree))
    if n >= MAX_NODES: out.append(f"  (chain cut at {MAX_NODES} nodes; deeper: --depth N)")
    return "\n".join(out)


def script_steps(root: Path, path: str, fallback: str):
    p = root / (path if (root / path).is_file() else fallback)
    if not p.is_file(): return []
    return [l.strip()[:110] for l in p.read_text(errors="replace").splitlines() if l.strip() and not l.strip().startswith("#")][:12]


def make_recipe(root: Path, line: int):
    ls = (root / "Makefile").read_text(errors="replace").splitlines()
    out = []
    for l in ls[line:line + 12]:
        if l.startswith("\t"): out.append(l.strip()[:110])
        elif l.strip(): break
    return out


def mermaid(m: Model, e: dict) -> str:
    h = e["handler"]
    if not h: return "sequenceDiagram\n  Note over Caller: handler not resolved"
    tree = m.expand(h)
    ids, lines = {}, ["sequenceDiagram", f"  participant Client as {'Client' if e['kind'] == 'http' else 'Caller'}"]

    def pid(d):
        n = d.get("o") or Path(d["f"]).stem
        if n not in ids: ids[n] = f"P{len(ids)}"; lines.append(f"  participant {ids[n]} as {n}")
        return ids[n]
    body = [f"  Client->>{pid(h)}: {re.sub(r'[;:#]', ' ', label(e))}"]

    def rec(node):
        a = pid(node["d"])
        for k in node["kids"]:
            b = pid(k["d"])
            body.append(f"  {a}->>{b}: {k['d']['n']}()")
            if not k["again"]: rec(k)
        d = node["d"]
        fx = [c for c in ("db write", "queue", "http out", "email", "file/storage", "process") if c in d.get("eff", {})]
        if fx: body.append(f"  Note over {a}: {', '.join(fx)}")
    rec(tree)
    return "\n".join(lines + body)


# ---- queries ------------------------------------------------------------------------------------------------------

def find_entries(m: Model, q: str):
    ql = q.lower().strip()
    norm = re.sub(r"\s+", " ", ql)
    exact = [e for e in m.entries if norm in (label(e).lower(), e["label"].lower(), (qname(e["handler"]).lower() if e["handler"] else ""))]
    if exact: return exact
    toks = norm.replace("/", " / ").split()
    def hay(e): return " ".join([label(e), e["file"], qname(e["handler"]) if e["handler"] else ""]).lower().replace("/", " / ")
    return [e for e in m.entries if all(t in hay(e) for t in toks)]


def find_callable(m: Model, q: str):
    mm = re.match(r"^(.+?):(\d+)$", q)
    if mm and mm.group(1) in m.parsed:
        rel, ln = mm.group(1), int(mm.group(2))
        c = [d for d in m.parsed[rel]["defs"] if d["k"] == "def" and d["l"] <= ln <= d["e"]]
        return [max(c, key=lambda d: d["l"])] if c else []
    if "::" in q or "." in q and q.count(".") == 1 and not q.endswith(tuple(".py .php .ts .js".split())):
        o, _, n = q.replace("::", ".").rpartition(".")
        return [d for d in m.idx.meths.get(n, []) if d["o"].lower() == o.lower()]
    return m.idx.funcs.get(q, []) + m.idx.meths.get(q, [])


def impact(m: Model, target: str):
    tl = target.lower()
    hits = []
    for e in m.entries:
        if not e["handler"]: continue
        for d in m.nodes(m.expand(e["handler"], 8)):
            if d["f"].lower() == tl or d["f"].lower().endswith("/" + tl) or qname(d).lower() == tl or d["n"].lower() == tl or (d.get("o") or "").lower() == tl:
                hits.append((e, d)); break
    return hits


def list_lines(m: Model, kind: str | None, limit: int):
    es = [e for e in m.entries if not kind or e["kind"] == kind]
    out = []
    for k in KINDS:
        sel = [e for e in es if e["kind"] == k]
        if not sel: continue
        out.append(f"{k} ({len(sel)})")
        w = max(len(label(e)) for e in sel[:limit]) if sel else 0
        for e in sel[:limit]:
            h = f"{qname(e['handler'])}  {e['handler']['f']}:{e['handler']['l']}" if e["handler"] else f"? {e.get('why') or 'inline'}  {e['file']}:{e['line']}"
            out.append(f"  {label(e):<{min(w, 60)}}  -> {h}")
        if len(sel) > limit: out.append(f"  ... +{len(sel) - limit} (--limit, --kind, or a QUERY)")
    return out


# ---- doctor, interview, answers -----------------------------------------------------------------------------------

def load_answers(root: Path) -> dict:
    f = root / DIRNAME / ANSWERS
    return {str(k): str(v) for k, v in tomllib.loads(f.read_text()).items()} if f.is_file() else {}


def save_answers(root: Path, answers: dict):
    body = ("# Answers to the `ff flow --interview` questions, applied by every `ff flow` run. Edit or delete a line to be asked again.\n"
            + "".join(f"{json.dumps(k)} = {json.dumps(v)}\n" for k, v in sorted(answers.items())))
    (root / DIRNAME / ANSWERS).write_text(body)


BUILTIN = set("""datetime datetimezone datetimeimmutable dateinterval exception closure generator arrayobject pdo reflectionclass stdclass
jsonserializable countable iterator throwable error date map set promise buffer json math url path os fs""".split())


def declared_deps(root: Path) -> set[str]:
    """Names of the third-party dependencies the project declares (composer, npm, pip, pyproject, go.mod); empty if it declares none."""
    out = set()
    for name in ("composer.json", "package.json"):
        p = root / name
        if p.is_file():
            try: data = json.loads(p.read_text())
            except ValueError: continue
            for k in ("require", "require-dev", "dependencies", "devDependencies"): out |= {x.lower() for x in (data.get(k) or {})}
    for p in list(root.glob("requirements*.txt")) + [root / "pyproject.toml", root / "go.mod", root / "Gemfile", root / "pom.xml"]:
        if p.is_file(): out |= {x.lower() for x in re.findall(r"[A-Za-z][\w.@/-]{2,}", p.read_text(errors="replace"))}
    return out


def questions(m: Model):
    """Only what the code cannot say: which declared third-party libraries are side effects."""
    import sys as _sys
    libs = lib_leaf(m)
    deps = declared_deps(m.root)
    import flowentry
    fw = (__import__("arch_infer").framework(m.root) or "").lower().replace(".js", "")
    count = Counter()
    known = flowparse.VENDORS
    for rel, f in m.parsed.items():
        for d in f["defs"]:
            if d["k"] != "def": continue
            for t in set(d.get("types", [])) & set(libs.get(rel, {})): count[libs[rel][t]] += 1
    qs = []
    for lib, n in count.most_common(12):
        if known.fullmatch(lib) or f"effect:{lib}" in m.answers or n < 3 or lib in BUILTIN or lib in _sys.stdlib_module_names: continue
        if fw and (lib.startswith(fw.rstrip("0123456789")) or fw.startswith(lib)): continue
        if deps and not any(lib in d for d in deps): continue
        qs.append({"id": f"effect:{lib}", "question": f"'{lib}' is an external library used in {n} places and is not recognised as a known service. "
                   f"Does it perform side effects (network, payments, storage...) that a flow card should list?",
                   "default": "ignore", "options": [{"value": "external", "label": f"Yes, show '{lib}' as an external effect"},
                                                    {"value": "ignore", "label": "No, framework or utility"}]})
    return qs[:5]


def doctor(m: Model) -> str:
    kinds = Counter(e["kind"] for e in m.entries)
    unres = [e for e in m.entries if not e["handler"] and not e.get("inline")]
    langs = Counter(f["lang"] for f in m.parsed.values())
    hit_files = {e["file"] for e in m.entries} | {e["handler"]["f"] for e in m.entries if e["handler"]}
    out = [f"ff flow --doctor: {len(m.parsed)} source files ({', '.join(f'{l} {n}' for l, n in langs.most_common())})",
           f"entry points: {len(m.entries)} (" + ", ".join(f"{k} {n}" for k, n in kinds.most_common()) + ")" if m.entries else "entry points: none detected"]
    if unres:
        out.append(f"handler not resolved for {len(unres)} of {len(m.entries)}:")
        out += [f"  {label(e)}  {e['file']}:{e['line']}  ({e['why']})" for e in unres[:8]]
    cand = flowentry.candidate_files(m.root, m.parsed, hit_files)
    if cand:
        out.append("files that look like they declare routes or commands but matched no detector:")
        for rel, sample in cand:
            out.append(f"  {rel}"); out += [f"    {s}" for s in sample]
        out.append("  -> add a rule to .ffcode/flow.toml:  [[entrypoint]]  kind = \"http\"  file = \"<glob>\"  pattern = '<regex with (?P<method>..) (?P<route>..) (?P<handler>..)>'")
    return "\n".join(out)


def needs(root: Path) -> list[dict]:
    """Pending developer input for `ff sync`: [{id, msg, cmd}]."""
    try: m = Model(root)
    except Exception as ex:                                              # never let a parser problem break a session start
        return [{"id": "flow-error", "msg": f"ff flow could not index the repo ({type(ex).__name__}: {ex})", "cmd": "ff flow --doctor"}]
    out = []
    code = [f for f, v in m.parsed.items() if v["defs"]]
    unres = [e for e in m.entries if not e["handler"] and not e.get("inline")]
    cand = flowentry.candidate_files(root, m.parsed, {e["file"] for e in m.entries} | {e["handler"]["f"] for e in m.entries if e["handler"]})
    if len(code) >= 5 and not m.entries:
        out.append({"id": "flow-entries", "msg": "ff flow found no entry points (routes/commands/jobs) in this repo", "cmd": "ff flow --doctor"})
    elif cand or (len(m.entries) >= 5 and len(unres) / len(m.entries) > 0.25):
        out.append({"id": "flow-entries", "msg": "ff flow: " + ", ".join(x for x in (f"{len(unres)} handler(s) unresolved" if unres else "", f"{len(cand)} file(s) look like route/command declarations but matched no detector" if cand else "") if x),
                    "cmd": "ff flow --doctor"})
    if questions(m): out.append({"id": "flow-effects", "msg": "ff flow: libraries whose side effects are unknown", "cmd": "ff flow --interview"})
    return out


# ---- write / check ------------------------------------------------------------------------------------------------

def slug(e: dict) -> str:
    return re.sub(r"[^a-z0-9]+", "-", f"{e['kind']}-{label(e)}".lower()).strip("-")[:80]


def render_all(m: Model) -> dict:
    files, idx = {}, ["# Entry points (generated by `ff flow --write`; do not edit)", ""]
    used = Counter()
    for e in m.entries:
        s = slug(e); used[s] += 1
        if used[s] > 1: s += f"-{used[s]}"
        h = f"{qname(e['handler'])}" if e["handler"] else "unresolved"
        idx.append(f"- [{label(e)}]({s}.md) [{e['kind']}] -> {h}")
        files[f"{s}.md"] = f"# {label(e)}\n\n```\n{card(m, e)}\n```\n\n```mermaid\n{mermaid(m, e)}\n```\n"
    files["INDEX.md"] = "\n".join(idx) + "\n"
    return files


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("query", nargs="*"); ap.add_argument("--root")
    ap.add_argument("--kind", choices=KINDS); ap.add_argument("--depth", type=int); ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--json", action="store_true"); ap.add_argument("--tests", action="store_true")
    ap.add_argument("--impact"); ap.add_argument("--mermaid", action="store_true"); ap.add_argument("--doctor", action="store_true")
    ap.add_argument("--write", nargs="?", const=f"{DIRNAME}/flows"); ap.add_argument("--check"); ap.add_argument("--interview", action="store_true")
    ap.add_argument("--answer", action="append", default=[]); ap.add_argument("--needs", action="store_true")
    a = ap.parse_args()
    root = find_root(a.root)
    if a.needs:
        print(json.dumps(needs(root))); return 0
    if a.answer:
        ans = load_answers(root); ans.update(dict(x.split("=", 1) for x in a.answer if "=" in x)); save_answers(root, ans)
        print(f"answers saved in {DIRNAME}/{ANSWERS}"); return 0
    m = Model(root, a.tests)
    if a.depth: m.depth = a.depth
    if a.interview: print(json.dumps({"questions": questions(m)}, indent=1, ensure_ascii=False)); return 0
    if a.doctor: print(doctor(m)); return 0
    if a.write or a.check:
        files = render_all(m)
        out = root / (a.write or a.check)
        if a.check:
            bad = [n for n, t in files.items() if not (out / n).is_file() or (out / n).read_text() != t]
            bad += [p.name for p in out.glob("*.md") if p.name not in files] if out.is_dir() else []
            print("flows up to date" if not bad else f"{len(bad)} stale file(s) in {out}: " + ", ".join(sorted(bad)[:8]) + "  (run: ff flow --write " + (a.check) + ")")
            return 1 if bad else 0
        out.mkdir(parents=True, exist_ok=True)
        for p in out.glob("*.md"):
            if p.name not in files: p.unlink()
        for n, t in files.items(): (out / n).write_text(t)
        print(f"wrote {len(files)} files in {out}"); return 0
    if a.impact:
        hits = impact(m, a.impact)
        if a.json: print(json.dumps([{"entry": label(e), "kind": e["kind"], "via": qname(d)} for e, d in hits])); return 0
        print(f"{len(hits)} entry point(s) reach {a.impact}:" if hits else f"no entry point reaches {a.impact} (unreferenced, or reached only through dynamic calls)")
        for e, d in hits: print(f"  [{e['kind']}] {label(e)}  -> {qname(e['handler'])}  (via {qname(d)}:{d['l']})")
        return 0
    if not a.query:
        if a.json: print(json.dumps([{"kind": e["kind"], "label": label(e), "handler": qname(e["handler"]) if e["handler"] else None, "file": e["file"], "line": e["line"]} for e in m.entries if not a.kind or e["kind"] == a.kind])); return 0
        if not m.entries: print("no entry points detected. `ff flow --doctor` says why."); return 0
        print("\n".join(list_lines(m, a.kind, a.limit))); return 0
    q = " ".join(a.query)
    es = [e for e in find_entries(m, q) if not a.kind or e["kind"] == a.kind]
    if len(es) > 1 and not a.mermaid and len({label(e) for e in es}) > 1:
        print(f"{len(es)} entry points match {q!r}; be more specific:")
        for e in es[:25]: print(f"  {label(e)}  -> {qname(e['handler']) if e['handler'] else '?'}")
        return 0
    if not es:
        cs = find_callable(m, q)
        if not cs: print(f"nothing matches {q!r} (entry points: `ff flow`; symbols: `ff find`)"); return 1
        es = [{"kind": "function", "label": qname(c), "method": "", "file": c["f"], "line": c["l"], "handler": c, "why": None, "inline": None} for c in cs[:3]]
    for e in es[:3]:
        print(mermaid(m, e) if a.mermaid else json.dumps(card_json(m, e)) if a.json else card(m, e), end="\n\n")
    return 0


def card_json(m: Model, e: dict) -> dict:
    h = e["handler"]
    tree = m.expand(h) if h else None
    ag = aggregate(m, e, tree) if tree else {}

    def ser(n): return {"call": qname(n["d"]), "file": n["d"]["f"], "line": n["d"]["l"], "layer": m.layer(n["d"]["f"]), "again": n["again"], "calls": [ser(k) for k in n["kids"]]}
    return {"entry": label(e), "kind": e["kind"], "file": e["file"], "line": e["line"], "handler": qname(h) if h else None, "why": e.get("why"),
            "chain": ser(tree) if tree else None, "access": ag.get("grd", []), "effects": {k: sorted(v) for k, v in ag.get("eff", {}).items()},
            "models": ag.get("models", []), "errors": sorted(ag.get("thr", {})), "external": sorted(set(ag.get("vend", {})) | set(ag.get("libs", [])))}


if __name__ == "__main__":
    sys.exit(main())
