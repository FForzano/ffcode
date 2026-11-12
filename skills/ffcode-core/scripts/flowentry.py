"""Entry points for `ff flow`: HTTP routes, CLI commands, jobs, listeners, from the usual ways frameworks declare them.
Four mechanisms, all table-driven so a new framework is one more row, not new code:
  annotation  a decorator / attribute / annotation above a callable  (FastAPI, Flask, Spring, Nest, Symfony, click, Celery, ...)
  callsite    a registration call with a path and a handler          (Express, chi/gin, Laravel, Django, Rails, net/http, ...)
  table       `'METHOD path' => 'module/controller/action'` rows     (Yii2, CodeIgniter, config-driven routers)
  convention  naming/placement of a callable                         (Yii/Symfony console actions, *Job::handle, main, bin/ scripts)
plus manifests (package.json, pyproject, composer.json, Makefile) and OpenAPI specs. Project-specific ones come from
`[[entrypoint]]` in .ffcode/flow.toml (kind, file glob, regex with named groups route/method/handler)."""
from __future__ import annotations

import fnmatch
import json
import re
from pathlib import Path

from common import DIRNAME

VERBS = "get|post|put|patch|delete|head|options|all|any"
# (kind, language filter or None, regex over the annotation text above a callable; named groups: method, route, name)
ANNOTATIONS = [
    ("http", {"python"}, rf"@\w+(?:\.\w+)*\.(?P<method>{VERBS})\(\s*(?:path\s*=\s*)?['\"](?P<route>[^'\"]*)"),
    ("http", {"python"}, r"@\w+(?:\.\w+)*\.route\(\s*['\"](?P<route>[^'\"]*)['\"](?:[^)]*methods\s*=\s*\[(?P<method>[^\]]*)\])?"),
    ("http", {"java", "kotlin"}, r"@(?P<method>Get|Post|Put|Patch|Delete)Mapping(?:\(\s*(?:(?:value|path)\s*=\s*)?\{?\s*['\"](?P<route>[^'\"]*))?"),
    ("http", {"java", "kotlin"}, r"@RequestMapping\(\s*(?:(?:value|path)\s*=\s*)?['\"](?P<route>[^'\"]*)['\"](?:[^)]*method\s*=\s*(?:RequestMethod\.)?(?P<method>\w+))?"),
    ("http", {"typescript", "javascript"}, r"@(?P<method>Get|Post|Put|Patch|Delete|All)\(\s*(?:['\"](?P<route>[^'\"]*)['\"])?"),
    ("http", {"php"}, r"#\[Route\(\s*['\"](?P<route>[^'\"]+)['\"](?:[^\]]*methods:\s*\[(?P<method>[^\]]*)\])?"),
    ("http", {"csharp"}, r"\[(?P<method>Http(?:Get|Post|Put|Patch|Delete))(?:\(\s*\"(?P<route>[^\"]*))?"),
    ("cli", {"python"}, r"@\w+(?:\.\w+)*\.command\(\s*(?:name\s*=\s*)?(?:['\"](?P<name>[\w:-]+)['\"])?"),
    ("cli", {"php"}, r"#\[AsCommand\(\s*(?:name:\s*)?['\"](?P<name>[\w:-]+)"),
    ("job", {"python"}, r"@(?:\w+\.)?(?:task|shared_task|actor|job)\b"),
    ("job", {"typescript", "javascript"}, r"@(?:Process|Processor|Cron|Interval)\(\s*(?:['\"](?P<name>[^'\"]*)['\"])?"),
    ("event", {"java", "kotlin"}, r"@(?:EventListener|KafkaListener|RabbitListener|SqsListener|JmsListener)\b"),
]
CLASS_PREFIX = [re.compile(r"@(?:Controller|RestController|RequestMapping)\(\s*(?:(?:value|path)\s*=\s*)?\{?\s*['\"]([^'\"]*)"),
                re.compile(r"#\[Route\(\s*['\"]([^'\"]+)['\"]")]
# one-line registrations: (language filter, regex; named groups: method, route, rest)
CALLSITES = [
    ({"typescript", "javascript"}, rf"\b\w+\s*\.\s*(?P<method>{VERBS}|use)\(\s*['\"`](?P<route>[^'\"`]*)['\"`]\s*,\s*(?P<rest>.+)"),
    ({"go"}, rf"\b\w+\s*\.\s*(?P<method>Get|Post|Put|Patch|Delete|GET|POST|PUT|PATCH|DELETE|Handle|HandleFunc|Any)\(\s*\"(?P<route>[^\"]*)\"\s*,\s*(?P<rest>.+)"),
    ({"go"}, r"\bhttp\s*\.\s*(?P<method>HandleFunc|Handle)\(\s*\"(?P<route>[^\"]*)\"\s*,\s*(?P<rest>.+)"),
    ({"php"}, rf"\bRoute\s*::\s*(?P<method>{VERBS}|resource|apiResource)\(\s*['\"](?P<route>[^'\"]*)['\"]\s*,\s*(?P<rest>.+)"),
    ({"python"}, r"\b(?P<method>re_path|path|url)\(\s*r?['\"](?P<route>[^'\"]*)['\"]\s*,\s*(?P<rest>.+)"),
    ({"ruby"}, rf"^\s*(?P<method>{VERBS})\s+['\"](?P<route>[^'\"]+)['\"](?:\s*,\s*(?:to:\s*|:to\s*=>\s*)?(?P<rest>['\"][\w/#@:]+['\"]))?"),
    ({"java", "kotlin", "csharp"}, rf"\.\s*(?P<method>{VERBS})\(\s*\"(?P<route>/[^\"]*)\"\s*,\s*(?P<rest>.+)"),
]
# `'POST,OPTIONS api/path' => 'api/controller/action'`
TABLE = re.compile(r"""['"](?:(?P<method>[A-Z]+(?:,[A-Z]+)*)\s+)?(?P<route>[^'"\s=>][^'"]*)['"]\s*=>\s*['"](?P<target>[\w/\-@#:.\\]+)['"]""")
TABLE_FILE = re.compile(r"(?i)(^|/)(routes?|urls?|router|rules)[\w-]*\.(php|py|js|ts|rb)$|(^|/)config/[\w-]*route[\w-]*\.")
# conventions over callables: (kind, language, file-path regex, class-name regex, method-name regex)
CONVENTIONS = [
    ("cli", {"php"}, r"(^|/)(commands?|console)/", r"Controller$|Command$", r"^action[A-Z]|^(?:execute|handle|run)$"),
    ("job", None, r"", r"(Job|Worker|Task|Consumer)$", r"^(?:handle|execute|run|perform|process|consume)$"),
    ("event", None, r"", r"(Listener|Subscriber|Observer)$", r"^(?:handle|__invoke|on[A-Z]\w*)$"),
    ("cli", {"php"}, r"", r"Command$", r"^(?:handle|execute)$"),
]
HANDLER_NOISE = re.compile(r"^(?:function|async|\(|\)|=>|\{|\}|lambda|func|fn|\|)")


def load_config(root: Path) -> dict:
    f = root / DIRNAME / "flow.toml"
    if not f.is_file(): return {}
    import tomllib
    try: return tomllib.loads(f.read_text())
    except tomllib.TOMLDecodeError: return {}


def signature(root: Path) -> str:
    from flowparse import digest
    f = root / DIRNAME / "flow.toml"
    return digest(Path(__file__).read_text(), f.read_text() if f.is_file() else "", Path(__file__).with_name("flowparse.py").read_text())


def _methods(m: str | None) -> str:
    if not m: return ""
    ms = [x.upper().replace("HTTP", "") for x in re.findall(r"[A-Za-z]+", m) if x.upper() != "REQUESTMETHOD"]
    return ",".join([x for x in ms if x != "OPTIONS"] or ms)


def handler_token(rest: str) -> tuple[str | None, str | None]:
    """(owner, method) or (None, name) or (None, None) for an inline function, from the tail of a registration call."""
    rest = rest.strip().rstrip(");,").strip()
    if not rest or HANDLER_NOISE.match(rest): return None, None
    m = re.match(r"\[\s*\\?([\w\\]+)::class\s*,\s*['\"](\w+)['\"]", rest)           # Laravel [Ctl::class, 'm']
    if m: return m.group(1).rsplit("\\", 1)[-1], m.group(2)
    m = re.match(r"['\"]([\w\\/]+)[@#:]+(\w+)['\"]", rest)                           # 'Ctl@m' / 'ctl#a'
    if m: return m.group(1).rsplit("\\", 1)[-1].rsplit("/", 1)[-1], m.group(2)
    m = re.match(r"\\?([\w\\]+)::class\s*$", rest)
    if m: return m.group(1).rsplit("\\", 1)[-1], "__invoke"
    m = re.match(r"((?:\w+\.)+)(\w+)", rest)                                         # views.func / ctl.action / mod.Handler
    if m and not rest.startswith(("function", "async")): return m.group(1).rstrip(".").rsplit(".", 1)[-1], m.group(2)
    m = re.match(r"\*?&?(\w+)\s*[,)]?", rest)
    if m and m.group(1) not in ("function", "async", "func"): return None, m.group(1)
    return None, None


def scan_file(rel: str, lang: str, raw: str, nocomment: str, parsed: dict, cfg: dict | None = None):
    """Adds `parsed["ent"]`: registration-style hits found in this file (resolved later against the whole index), and
    `ent` on definitions carrying an annotation that declares an entry point."""
    ent = []
    lines = nocomment.split("\n")
    rawlines = raw.split("\n")
    for kind, langs, rx in ANNOTATIONS:
        if langs and lang not in langs: continue
        c = re.compile(rx)
        for d in parsed["defs"]:
            if d["k"] != "def" or not d.get("ann"): continue
            m = c.search(d["ann"])
            if m:
                g = m.groupdict()
                d.setdefault("ent", []).append({"kind": kind, "method": _methods(g.get("method")), "route": g.get("route") or "", "name": g.get("name") or ""})
    for d in parsed["defs"]:
        if d["k"] == "class" and d.get("ann"):
            for rx in CLASS_PREFIX:
                m = rx.search(d["ann"])
                if m: d["prefix"] = m.group(1); break
        if d["k"] == "def" and len(d.get("ann", "")) > 1200: d["ann"] = d["ann"][:1200]
        if d["k"] == "class" and len(d.get("ann", "")) > 600: d["ann"] = d["ann"][:600]
    for langs, rx in CALLSITES:
        if lang not in langs: continue
        c = re.compile(rx)
        for i, ln in enumerate(lines):
            m = c.search(ln)
            if not m: continue
            g = m.groupdict(); rest = g.get("rest") or ""
            if g["method"] in ("use", "path", "re_path", "url") and lang != "python" and not g["route"].startswith("/"): continue
            own, name = handler_token(rest) if rest else (None, None)
            if rest and own is None and name is None and "{" not in rest and "=>" not in rest and "function" not in rest and "func" not in rest and "lambda" not in rest:
                continue
            inline = bool(rest) and own is None and name is None
            ent.append({"kind": "http", "method": _methods(g["method"]) if g["method"].lower() not in ("use", "path", "re_path", "url", "handle", "handlefunc") else "",
                        "route": g["route"], "line": i + 1, "owner": own, "name": name, "inline": inline})
    if TABLE_FILE.search(rel):
        for i, ln in enumerate(lines):
            m = TABLE.search(ln)
            if m and not m.group("route").startswith(("http", "$")) and "/" in m.group("target"):
                ent.append({"kind": "http", "method": _methods(m.group("method")), "route": m.group("route"), "line": i + 1, "target": m.group("target")})
    for e in (cfg or {}).get("entrypoint", []):
        if e.get("file") and not fnmatch.fnmatch(rel, e["file"]): continue
        try: c = re.compile(e["pattern"])
        except (re.error, KeyError): continue
        for i, ln in enumerate(lines):
            m = c.search(ln)
            if m:
                g = m.groupdict(); h = g.get("handler") or ""
                own, name = handler_token(h) if h else (None, None)
                ent.append({"kind": e.get("kind", "http"), "method": g.get("method", "").upper(), "route": g.get("route", g.get("name", "")),
                            "line": i + 1, "owner": own, "name": name, "target": h if "/" in h else None, "custom": True})
    if lang == "python" and re.search(r"""^if\s+__name__\s*==\s*['"]__main__['"]""", nocomment, re.M):
        ln = next(i for i, l in enumerate(lines) if re.match(r"""if\s+__name__\s*==""", l))
        ent.append({"kind": "cli", "route": Path(rel).name, "line": ln + 1, "main": True})
    if lang == "go" and re.search(r"^func\s+main\(\)", nocomment, re.M): ent.append({"kind": "cli", "route": Path(rel).parent.name or Path(rel).stem, "main": True, "line": 1})
    if lang in ("java", "kotlin", "csharp") and re.search(r"\b(?:static\s+void\s+main|fun\s+main)\s*\(", nocomment): ent.append({"kind": "cli", "route": Path(rel).stem, "main": True, "line": 1})
    if lang == "shell" and re.search(r"(^|/)(bin|scripts?|tools?|cli)/", rel) and rawlines and rawlines[0].startswith("#!"): ent.append({"kind": "cli", "route": Path(rel).stem, "line": 1, "script": True})
    sig = [m.group(1) for m in re.finditer(r"\$signature\s*=\s*['\"]([\w:-]+)", nocomment)]
    if sig: ent.append({"kind": "cli", "route": sig[0], "line": 1, "laravel": True})
    if ent: parsed["ent"] = ent


# ---- resolution ---------------------------------------------------------------------------------------------------

def _variants_method(a: str) -> list[str]:
    camel = re.sub(r"[-_ ]+(\w)", lambda m: m.group(1).upper(), a)
    snake = re.sub(r"[-\s]+", "_", re.sub(r"(?<!^)(?=[A-Z])", "_", a)).lower()
    cap = camel[:1].upper() + camel[1:]
    return list(dict.fromkeys([a, camel, "action" + cap, "action_" + snake, snake, camel + "Action", cap]))


def _variants_class(a: str) -> list[str]:
    cap = "".join(p[:1].upper() + p[1:] for p in re.split(r"[-_ ]+", a))
    return list(dict.fromkeys([cap + "Controller", cap, cap + "Handler", cap + "View", cap + "Resource", a]))


class Index:
    """Lookup tables over the parsed files."""

    def __init__(self, parsed: dict):
        self.p = parsed
        self.classes, self.funcs, self.meths, self.byfile = {}, {}, {}, {}
        for rel, f in parsed.items():
            self.byfile[rel] = f
            for d in f["defs"]:
                d["f"] = rel
                if d["k"] == "class": self.classes.setdefault(d["n"], []).append(d)
                elif d.get("o"): self.meths.setdefault(d["n"], []).append(d)
                else: self.funcs.setdefault(d["n"], []).append(d)
        self.lower = {}
        for n in list(self.classes): self.lower.setdefault(n.lower(), []).append(n)

    def is_iface(self, d: dict) -> bool:
        return bool(d.get("o")) and any(c.get("iface") for c in self.classes.get(d["o"], []) if c["f"] == d["f"])

    def method_of(self, cls: str, names, seen=None, prefer_file=None):
        """First callable `names` (any variant) on class `cls` or its ancestors."""
        seen = seen or set()
        if cls in seen: return None
        seen.add(cls)
        for c in self.classes.get(cls, []) if not prefer_file else sorted(self.classes.get(cls, []), key=lambda c: c["f"] != prefer_file):
            for n in names:
                for m in self.meths.get(n, []):
                    if m["o"] == cls and m["f"] == c["f"]: return m
        for c in self.classes.get(cls, []):
            for parent in c.get("ext", []):
                r = self.method_of(parent, names, seen)
                if r: return r
        return None

    def resolve_target(self, owner: str | None, name: str | None, target: str | None = None, near: str | None = None):
        """Callable for a handler reference. Returns (def, reason)."""
        if target:
            segs = [s for s in re.split(r"[/@#:.\\]+", target) if s]
            if len(segs) >= 2:
                action, ctl = segs[-1], segs[-2]
                for cn in _variants_class(ctl):
                    for real in self.lower.get(cn.lower(), []):
                        m = self.method_of(real, _variants_method(action))
                        if m: return m, None
                return None, f"no class like {ctl!r} with an action {action!r}"
            name = segs[0] if segs else name
        if owner:
            for cn in [owner] + [x for x in _variants_class(owner)]:
                for real in self.lower.get(cn.lower(), []):
                    m = self.method_of(real, _variants_method(name or "__invoke"))
                    if m: return m, None
            for m in self.meths.get(name or "", []):
                if m["o"].lower().startswith(owner.lower()): return m, None
            for f in self.funcs.get(name or "", []):
                if Path(f["f"]).stem.lower() == owner.lower(): return f, None
            return None, f"{owner}.{name} not found"
        if name:
            fs = self.funcs.get(name, [])
            if near: fs = sorted(fs, key=lambda d: d["f"] != near)
            if fs: return fs[0], None
            ms = self.meths.get(name, [])
            if len(ms) == 1: return ms[0], None
            return None, f"{name} not found"
        return None, "inline or unrecognised handler"


def entries(root: Path, parsed: dict, idx: Index) -> list[dict]:
    """Every entry point: {kind, label, method, file, line, handler (def or None), why (when unresolved)}."""
    out, seen = [], set()

    def add(kind, label, method, f, line, h, why=None, inline=None):
        key = (kind, label, method, h["f"] if h else f, h["l"] if h else line)
        if key in seen: return
        seen.add(key)
        out.append({"kind": kind, "label": label, "method": method, "file": f, "line": line, "handler": h, "why": why, "inline": inline})

    for rel, f in parsed.items():
        classes = {c["n"]: c for c in f["defs"] if c["k"] == "class"}
        for d in f["defs"]:
            for e in d.get("ent", []):
                pre = classes.get(d.get("o") or "", {}).get("prefix", "")
                route = e["route"] if e["route"].startswith("/") or not pre else pre.rstrip("/") + "/" + e["route"].lstrip("/")
                if e["kind"] == "http" and not route and not e["method"]: route = d["n"]
                add(e["kind"], route or e["name"] or ("/" if e["kind"] == "http" else d["n"]), e["method"], rel, d["l"], d)
        for e in f.get("ent", []):
            if e.get("main"):
                mains = [d for d in f["defs"] if d["k"] == "def" and d["n"] in ("main", "run", "cli") and not d.get("o")]
                add("cli", e["route"], "", rel, e["line"], mains[0] if mains else None, None if mains else "no main() function: the module body is the command")
            elif e.get("script"): add("cli", e["route"], "", rel, 1, None, "shell script: see its steps below", inline="script")
            elif e.get("laravel"):
                cl = next((c for c in f["defs"] if c["k"] == "class"), None); h = idx.method_of(cl["n"], ["handle"]) if cl else None
                add("cli", e["route"], "", rel, e["line"], h, None if h else "handle() not found")
            elif e.get("inline"): add(e["kind"], e["route"], e.get("method", ""), rel, e["line"], None, inline=(rel, e["line"]))
            else:
                h, why = idx.resolve_target(e.get("owner"), e.get("name"), e.get("target"), near=rel)
                add(e["kind"], e["route"], e.get("method", ""), rel, e["line"], h, why)
        classes_here = [c for c in f["defs"] if c["k"] == "class"]
        for kind, langs, pathrx, clsrx, methrx in CONVENTIONS:
            if langs and f["lang"] not in langs: continue
            if pathrx and not re.search(pathrx, rel): continue
            for c in classes_here:
                if not re.search(clsrx, c["n"]): continue
                for d in f["defs"]:
                    if d["k"] == "def" and d.get("o") == c["n"] and re.search(methrx, d["n"]):
                        base = re.sub(r"(Controller|Command|Job|Worker|Task|Consumer|Listener|Subscriber|Observer)$", "", c["n"])
                        cid = re.sub(r"(?<!^)(?=[A-Z])", "-", base).lower()
                        act = re.sub(r"(?<!^)(?=[A-Z])", "-", re.sub(r"^action", "", d["n"])).lower() or d["n"]
                        label = f"{cid}/{act}" if d["n"].startswith("action") else (f"{cid}" if kind == "cli" else f"{c['n']}::{d['n']}")
                        add(kind, label, "", rel, d["l"], d)
    manifest_entries(root, idx, add)
    return sorted(out, key=lambda e: (e["kind"], e["label"], e["method"]))


def manifest_entries(root: Path, idx: Index, add):
    pj = root / "package.json"
    if pj.is_file():
        try: data = json.loads(pj.read_text())
        except ValueError: data = {}
        b = data.get("bin") or {}
        for name, path in ({data.get("name", "bin"): b} if isinstance(b, str) else b).items():
            p = str(path).lstrip("./")
            add("cli", name, "", "package.json", 1, None, None, inline=("script", p)) if not _main_of(idx, p) else add("cli", name, "", "package.json", 1, _main_of(idx, p))
        for name, cmd in (data.get("scripts") or {}).items():
            m = re.search(r"(?:node|ts-node|tsx|python3?|bash|sh)\s+([\w./-]+)", cmd)
            h = _main_of(idx, m.group(1).lstrip("./")) if m else None
            add("cli", f"npm run {name}", "", "package.json", 1, h, None if h else cmd[:80], inline=None if h else ("shell", cmd))
    pp = root / "pyproject.toml"
    if pp.is_file():
        import tomllib
        try: data = tomllib.loads(pp.read_text())
        except tomllib.TOMLDecodeError: data = {}
        for name, ref in (data.get("project", {}).get("scripts") or {}).items():
            mod, _, fn = str(ref).partition(":")
            h, why = idx.resolve_target(mod.rsplit(".", 1)[-1], fn or "main")
            add("cli", name, "", "pyproject.toml", 1, h, why)
    cj = root / "composer.json"
    if cj.is_file():
        try: data = json.loads(cj.read_text())
        except ValueError: data = {}
        for path in data.get("bin") or []:
            add("cli", Path(path).name, "", "composer.json", 1, None, "script", inline=("script", path))
    mk = root / "Makefile"
    if mk.is_file():
        for i, ln in enumerate(mk.read_text(errors="replace").splitlines(), 1):
            m = re.match(r"^([A-Za-z][\w.-]*)\s*:(?!=)", ln)
            if m and not m.group(1).startswith("."): add("cli", f"make {m.group(1)}", "", "Makefile", i, None, None, inline=("make", i))


def _main_of(idx: Index, path: str):
    f = idx.byfile.get(path)
    if not f: return None
    for d in f["defs"]:
        if d["k"] == "def" and d["n"] in ("main", "run", "cli", "handler") and not d.get("o"): d["f"] = path; return d
    return None


def candidate_files(root: Path, parsed: dict, hit_files: set[str]) -> list[tuple[str, list[str]]]:
    """Files that look like they declare routes or commands but produced no entry point: (path, sample lines)."""
    out = []
    for rel in parsed:
        if rel in hit_files: continue
        if not re.search(r"(?i)(^|/)(routes?|urls?|router|routing|endpoints?|commands?|cli)[\w-]*\.", rel): continue
        try: lines = (root / rel).read_text(errors="replace").splitlines()
        except OSError: continue
        sample = [l.strip()[:110] for l in lines if re.search(r"""['"]/[\w/{}:<>-]+['"]|\.(?:get|post|put|delete|route|command)\(\s*['"]""", l)][:4]
        if len(sample) >= 3: out.append((rel, sample))
    return out[:8]
