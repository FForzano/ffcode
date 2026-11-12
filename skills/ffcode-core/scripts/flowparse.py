"""Language-light source parsing for `ff flow`: callables with their extent, what each one calls, what it touches.
No AST: comments and strings are blanked first (so braces and keywords inside them cannot confuse anything), then
definitions are found per language family and bounded by brace matching or indentation. The result per file is
plain JSON, cached by mtime+size in .ffcode/cache/flow.json, so a query only re-parses what changed."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from common import DIRNAME, is_text, lang_of, tracked_files

EXTRA = {".kt": "kotlin", ".cs": "csharp", ".rb": "ruby"}
LANGS = {"python", "php", "typescript", "javascript", "java", "kotlin", "csharp", "go", "ruby", "shell"}
INDENT = {"python", "ruby"}
KEYWORDS = set("""if else elif for foreach while do switch case catch try finally return new throw raise function def class
fn func lambda use using import from as and or not in is echo print isset empty unset array list match yield await async
static self this parent super with assert elseif endif endfor endforeach endwhile require include require_once include_once
exit die typeof instanceof sizeof defer go select range make len cap append int str float bool string void null None true
false True False public private protected abstract final extends implements interface trait enum struct type var let const
fun val object when unless then end begin puts""".split())


def flang(path) -> str | None:
    l = lang_of(path)
    return l if l in LANGS else EXTRA.get(Path(path).suffix.lower())


# ---- blanking comments and strings -------------------------------------------------------------------------------

_STR = r'"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|`(?:\\.|[^`\\])*`'
_PAT = {
    "python": r'(?P<c>#[^\n]*)|(?P<s>"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\')',
    "ruby": r'(?P<c>#[^\n]*)|(?P<s>"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\')',
    "shell": r'(?P<c>(?<![$\w])#[^\n]*)|(?P<s>"(?:\\.|[^"\\\n])*"|\'[^\'\n]*\')',
    "php": r'(?P<c>//[^\n]*|/\*[\s\S]*?\*/|#(?!\[)[^\n]*)|(?P<s>' + _STR + ')',
}
_DEFAULT = r'(?P<c>//[^\n]*|/\*[\s\S]*?\*/)|(?P<s>' + _STR + ')'
_blank = lambda s: re.sub(r"[^\n]", " ", s)


def mask(text: str, lang: str):
    """(nocomment, nostr): comments blanked; additionally the inside of strings blanked. Same length and line breaks as `text`."""
    rx = re.compile(_PAT.get(lang, _DEFAULT))
    a, b, pos = [], [], 0
    for m in rx.finditer(text):
        a.append(text[pos:m.start()]); b.append(text[pos:m.start()])
        if m.group("c") is not None: a.append(_blank(m.group())); b.append(_blank(m.group()))
        else:
            s = m.group(); a.append(s)
            b.append(s[0] + _blank(s[1:-1]) + s[-1] if len(s) >= 2 and not s.startswith(('"""', "'''")) else _blank(s))
        pos = m.end()
    a.append(text[pos:]); b.append(text[pos:])
    return "".join(a), "".join(b)


# ---- definitions --------------------------------------------------------------------------------------------------

_T = r"[\w\\.]+"
DEFS = {
    "python": [("class", re.compile(r"^(\s*)class\s+(\w+)")), ("def", re.compile(r"^(\s*)(?:async\s+)?def\s+(\w+)"))],
    "ruby": [("class", re.compile(r"^(\s*)(?:class|module)\s+(\w+)")), ("def", re.compile(r"^(\s*)def\s+(?:self\.)?(\w+[?!=]?)"))],
    "php": [("class", re.compile(r"^(\s*)(?:(?:abstract|final|readonly)\s+)*(?:class|interface|trait|enum)\s+(\w+)")),
            ("def", re.compile(r"^(\s*)(?:(?:public|protected|private|static|abstract|final)\s+)*function\s+&?(\w+)\s*\("))],
    "go": [("class", re.compile(r"^()type\s+(\w+)\s+(?:struct|interface)")), ("def", re.compile(r"^()func\s+(?:\(\s*\w*\s*\*?(\w+)[^)]*\)\s*)?(\w+)\s*[\[(]"))],
    "shell": [("def", re.compile(r"^(\s*)(?:function\s+)?(\w[\w-]*)\s*\(\)\s*\{?")), ("def", re.compile(r"^(\s*)function\s+(\w[\w-]*)"))],
}
_JSL = [("class", re.compile(r"^(\s*)(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+(\w+)")),
        ("def", re.compile(r"^(\s*)(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*(\w+)\s*[<(]")),
        ("def", re.compile(r"^(\s*)(?:export\s+)?(?:const|let|var)\s+(\w+)\s*(?::[^=]+)?=\s*(?:async\s*)?(?:\([^)]*\)|\w+)\s*(?::[^=>]+)?=>")),
        ("method", re.compile(r"^(\s*)(?:(?:public|private|protected|static|async|readonly|override|abstract)\s+)*(?:get\s+|set\s+)?(\w+)\s*(?:<[^>]*>)?\s*\([^;{}]*\)\s*(?::\s*[^{;=]+)?\{"))]
DEFS["typescript"] = DEFS["javascript"] = _JSL
_JAVA = [("class", re.compile(r"^(\s*)(?:(?:public|private|protected|static|final|abstract|sealed|data|open|internal|partial)\s+)*(?:class|interface|enum|record|object)\s+(\w+)")),
         ("method", re.compile(r"^(\s*)(?:@\w+(?:\([^)]*\))?\s*)*(?:(?:public|private|protected|static|final|abstract|override|virtual|async|synchronized|internal)\s+)+[\w<>\[\],.?\s]*?\s(\w+)\s*\("))]
DEFS["java"] = DEFS["csharp"] = _JAVA
DEFS["kotlin"] = [_JAVA[0], ("def", re.compile(r"^(\s*)(?:(?:public|private|protected|override|suspend|internal|open|inline)\s+)*fun\s+(?:<[^>]+>\s*)?(?:\w+\.)?(\w+)\s*\("))]
_EXT = {
    "python": re.compile(r"class\s+\w+\s*\(([^)]*)\)"), "ruby": re.compile(r"<\s*([\w:]+)"),
    "kotlin": re.compile(r"class\s+\w+[^:{]*:\s*([^{]*)"), "csharp": re.compile(r"(?:class|interface|struct|record)\s+\w+[^:{]*:\s*([^{]*)"),
}
_EXT_DEFAULT = re.compile(r"(?:extends|implements)\s+([^{]*)")


def _line_offsets(text: str):
    offs, p = [0], 0
    for ln in text.split("\n"):
        p += len(ln) + 1; offs.append(p)
    return offs


def _brace_span(code: str, start: int, limit_lines_pos: int):
    """(open_pos, close_pos) of the first `{...}` after `start` at paren depth 0, or None when a `;` comes first (no body)."""
    depth = 0; i = start; n = min(len(code), limit_lines_pos)
    while i < n:
        c = code[i]
        if c == "(": depth += 1
        elif c == ")": depth = max(0, depth - 1)
        elif c == ";" and depth == 0: return None
        elif c == "{" and depth == 0:
            d = 0; j = i
            while j < len(code):
                if code[j] == "{": d += 1
                elif code[j] == "}":
                    d -= 1
                    if d == 0: return i, j
                j += 1
            return i, len(code) - 1
        i += 1
    return None


def _indent_end(lines, i: int, indent: int, lang: str) -> int:
    """0-based index of the last line of the block that starts at line i."""
    last = i
    for j in range(i + 1, len(lines)):
        ln = lines[j]
        if not ln.strip(): continue
        ind = len(ln) - len(ln.lstrip())
        if ind <= indent:
            if lang == "ruby" and ln.strip().startswith("end"): last = j
            break
        last = j
    return last


def _above(raw_lines, i: int):
    """Annotation / attribute / docblock lines directly above line i (0-based), raw text."""
    out, j = [], i - 1
    while j >= 0 and len(out) < 14:
        s = raw_lines[j].strip()
        if not s or s.endswith(("}", ";", "{")) and not s.startswith(("@", "#[", "*", "/*")): break
        out.append(raw_lines[j]); j -= 1
    return "\n".join(reversed(out))


def _signature(header: str, name: str, lang: str) -> str:
    """`(params) -> return` of a callable header, without its body."""
    i = header.find(name)
    j = header.find("(", i) if i >= 0 else -1
    if j < 0: return ""
    depth, k = 0, j
    while k < len(header):
        depth += header[k] == "("; depth -= header[k] == ")"
        k += 1
        if depth == 0: break
    params = header[j:k]
    rest = header[k:]
    m = re.match(r"\s*(?::|->)\s*([\w\\|?\[\]<>,. ]+?)\s*(?:\{|:|;|$)", rest) if lang in ("php", "python", "typescript", "javascript", "kotlin") else None
    ret = m.group(1).strip() if m else ""
    return (params + (f" -> {ret}" if ret else ""))[:220]


def _owner_ext(header: str, lang: str):
    m = _EXT.get(lang, _EXT_DEFAULT).search(header)
    if not m: return []
    return [t.rsplit("\\", 1)[-1].rsplit(".", 1)[-1] for t in re.findall(r"[A-Za-z_][\w\\.]*", m.group(1)) if t[0].isupper() or lang == "python"][:6]


CALL = re.compile(r"(?:(?:(?P<recv>[$\w\\]+)\s*)?(?P<op>->|::|\.|\?->|\?\.)\s*)?(?P<name>[A-Za-z_]\w*)\s*\(")
NEW = re.compile(r"\bnew\s+\\?([\w\\]+)")
CAMEL = re.compile(r"(?<![\w$])\\?([A-Z][A-Za-z0-9_]*)\b")
THROW = re.compile(r"\b(?:throw\s+new|throw|raise)\s+\\?([\w\\.]+)")
GUARD = re.compile(r"""(@(?:PreAuthorize|Secured|RolesAllowed|UseGuards|login_required|permission_required|requires_auth|Authenticated|IsGranted|Authorize)\b[^\n]*|#\[(?:IsGranted|Security)[^\n]*|->middleware\([^)]*\)|\bmiddleware\(\s*['"][^)]*\)|Depends\([^)]*\)|\b(?:authorize|can|authenticate|requireAuth|require_auth|ensure_authenticated|checkRole|hasRole|isAdmin|is_admin|check_permission)\s*\([^)]*\)|'roles'\s*=>\s*\[[^\]]*\]|\bpermission_classes\s*=\s*\[[^\]]*\])""")
EFFECTS = {
    "db write": r"(?:->|\.|::)\s*(?:save|saveAll|insert|insertMany|insert_one|update|updateAll|updateOne|updateMany|upsert|delete|deleteAll|destroy|remove|create|bulkCreate|batchInsert|persist|flush|executeUpdate|session\.add|bulk_create)\s*\(|\b(?:INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|REPLACE\s+INTO)\b|\b(?:db|conn|connection|session|cursor)\s*\.\s*(?:execute|commit)\s*\(",
    "db read": r"(?:->|\.|::)\s*(?:find|findOne|findAll|findBy\w*|first|firstOrFail|get|where|filter|select|query|fetch\w*|all|count|exists|createCommand)\s*\(|\bSELECT\s+[\w*,\s.]+\s+FROM\b",
    "transaction": r"\b(?:beginTransaction|begin_transaction|BEGIN\s+TRANSACTION)\b|@Transactional|\btransaction\s*\(|\batomic\s*\(|\.transaction\b|\bwith\s+transaction",
    "http out": r"\bcurl_exec\b|\brequests\s*\.\s*(?:get|post|put|patch|delete|request)\b|\bhttpx\s*\.|\bfetch\s*\(|\baxios\b|\burllib\b|\bHttp::(?:get|post|put|patch|delete|withHeaders)|\bHttpClient\b|\bhttp\.(?:Get|Post|NewRequest)\b|\bRestTemplate\b|\bWebClient\b|\bguzzle\b|\bGuzzle\b",
    "queue": r"(?:->|\.|::)\s*(?:dispatch|dispatchSync|enqueue|enqueueAt|perform_later|perform_async|apply_async|delay|sendMessage|send_message|publish|push)\s*\(|\bdispatch\s*\(|\bqueue\s*(?:->|\.)\s*push\b",
    "email": r"\b(?:sendEmail|send_email|send_mail|sendMail|sendmail)\b|\bMail::|\bmailer\b|\bsmtp\b|\bSendGrid\b|\bMailgun\b|\bnodemailer\b|\bmail\s*\(",
    "file/storage": r"\b(?:file_put_contents|fwrite|unlink|rename|copy|move_uploaded_file|writeFile\w*|appendFile\w*|os\.remove|shutil\.\w+|putObject|put_object|upload_file|uploadFile|storage\s*(?:->|\.)\s*(?:put|write|delete))\b|\bopen\s*\([^)]*['\"][wax]b?['\"]",
    "process": r"\b(?:exec|shell_exec|passthru|proc_open|popen|system)\s*\(|\bsubprocess\s*\.|\bchild_process\b|\bos\.system\b|\bRuntime\.getRuntime\b|\bexec\.Command\b",
    "cache": r"\b(?:cache|Cache|redis|Redis)\s*(?:->|\.|::)\s*(?:set|put|get|delete|forget|remember|flush)\b",
}
_EFFECT_RX = {k: re.compile(v) for k, v in EFFECTS.items()}
VENDOR_NAMES = """stripe paypal braintree twilio sendgrid mailgun postmark firebase fcm onesignal s3 sns sqs dynamodb lambda cloudwatch
redis kafka rabbitmq amqp elasticsearch elastic algolia slack github gitlab jira openai anthropic gcs bigquery azure aws whatsapp
telegram zoom mapbox sentry datadog auth0 okta cognito keycloak salesforce hubspot shopify acube docusign google""".split()
VENDORS = re.compile(r"(?i)^(?:" + "|".join(VENDOR_NAMES) + r")$")


def vendors_in(code: str) -> list[str]:
    """Known external services named by an identifier: `stripe`, `StripeClient`, `$stripeAccountId`; not `session`."""
    out = set()
    for tok in set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", code)):
        low = tok.lower()
        for v in VENDOR_NAMES:
            if low == v or (low.startswith(v) and len(tok) > len(v) and (tok[len(v)].isupper() or tok[len(v)] == "_")): out.add(v); break
    return sorted(out)[:8]


def _chain_receiver(code: str, pos: int) -> str:
    """`Foo(...)->bar(` or `new Foo()->bar(`: the class when what precedes the operator is a constructor-like call."""
    i = pos - 1
    while i >= 0 and code[i].isspace(): i -= 1
    if i < 0 or code[i] != ")": return ""
    depth = 0
    while i >= 0:
        depth += code[i] == ")"; depth -= code[i] == "("
        if depth == 0: break
        i -= 1
    j = i - 1
    while j >= 0 and code[j].isspace(): j -= 1
    k = j
    while k >= 0 and (code[k].isalnum() or code[k] in "_\\"): k -= 1
    ident = code[k + 1:j + 1].rsplit("\\", 1)[-1]
    return ident if ident[:1].isupper() else ""


def _analyze(nostr: str, nocomment: str, raw: str):
    types = sorted({m.group(1) for m in CAMEL.finditer(nostr)} | {m.group(1).rsplit("\\", 1)[-1] for m in NEW.finditer(nostr)})
    calls, seen = [], set()
    for m in CALL.finditer(nostr):
        name, recv, op = m.group("name"), m.group("recv"), m.group("op")
        if name in KEYWORDS and not op: continue
        pre = nostr[max(0, m.start() - 4):m.start()]
        if re.search(r"\bnew\s*$", pre) and not op: continue
        if re.search(r"\b(?:function|def|fn|func)\s+$", nostr[max(0, m.start() - 12):m.start()]): continue
        if op and not recv: recv = _chain_receiver(nostr, m.start())
        recv = (recv or "").lstrip("$\\").rsplit("\\", 1)[-1] if recv else ""
        key = (recv, op or "", name)
        if key not in seen: seen.add(key); calls.append(list(key))
    eff = {}
    for cat, rx in _EFFECT_RX.items():
        hits = sorted({re.sub(r"\s+", "", m.group(0))[:40] for m in rx.finditer(nocomment)})
        if hits: eff[cat] = hits[:6]
    vend = vendors_in(nostr)
    thr = sorted({m.group(1).rsplit("\\", 1)[-1] for m in THROW.finditer(nostr) if m.group(1)[:1].isupper()})
    grd = [re.sub(r"\s+", " ", g.group(0))[:120] for g in GUARD.finditer(raw)][:8]
    return {"types": types[:80], "calls": calls[:120], "eff": eff, "vend": vend, "thr": thr[:8], "grd": grd}


def parse(text: str, lang: str) -> dict:
    """Everything `ff flow` needs from one file."""
    nocomment, nostr = mask(text, lang)
    raw_lines, ncl, nsl = text.split("\n"), nocomment.split("\n"), nostr.split("\n")
    offs = _line_offsets(nostr)
    found = []                                   # (line index, kind, indent, name, receiver type for go)
    for i, ln in enumerate(nsl):
        if not ln.strip(): continue
        for kind, rx in DEFS.get(lang, []):
            m = rx.match(ln)
            if not m: continue
            g = m.groups()
            name = g[-1]; owner = g[1] if lang == "go" and len(g) == 3 and kind == "def" else None
            if not name or name in KEYWORDS or (kind == "method" and name in KEYWORDS): continue
            found.append((i, kind, len(g[0]), name, owner)); break
    defs = []
    for i, kind, indent, name, rcv in found:
        if lang in INDENT: end = _indent_end(nsl, i, indent, lang)
        else:
            sp = _brace_span(nostr, offs[i], offs[min(len(nsl), i + 40)])
            if sp is None: end = i
            else: end = nostr.count("\n", 0, sp[1])
        defs.append({"k": "class" if kind == "class" else "def", "n": name, "l": i + 1, "e": end + 1, "i": indent, "o": rcv, "kind0": kind})
    # drop JS/Java "method" matches that are really control flow (if/for/while headers): keywords already filtered; keep only inside classes
    classes = [d for d in defs if d["k"] == "class"]
    out = []
    for d in defs:
        if d["kind0"] == "method" and not any(c["l"] < d["l"] <= c["e"] for c in classes): continue
        cont = [c for c in classes if c is not d and c["l"] <= d["l"] and d["e"] <= c["e"] and (c["l"], -c["e"]) != (d["l"], -d["e"])]
        if cont and not d["o"]: d["o"] = max(cont, key=lambda c: c["l"])["n"]
        out.append(d)
    for d in out:
        a, b = d["l"] - 1, d["e"]
        body_nostr, body_nc, body_raw = "\n".join(nsl[a:b]), "\n".join(ncl[a:b]), "\n".join(raw_lines[a:b])
        header = " ".join(" ".join(raw_lines[a:min(b, a + 6)]).split())
        d["sig"] = _signature(header, d["n"], lang)
        d["ann"] = _above(raw_lines, a)
        if d["k"] == "class":
            d["ext"] = _owner_ext(header, lang)
            d["iface"] = bool(re.match(r"\s*(?:export\s+)?(?:abstract\s+)?interface\b|\s*(?:public\s+)?(?:partial\s+)?interface\b|\s*(?:abstract|trait|interface)\b", header))
            own = _analyze(body_nostr, body_nc, body_raw) if b - a < 400 else {}
            d.update({"types": own.get("types", [])[:40]})
            d["grd"] = [re.sub(r"\s+", " ", g.group(0))[:120] for g in GUARD.finditer(d["ann"] + "\n" + body_raw[:600])][:6]
        else:
            d.update(_analyze(body_nostr, body_nc, body_raw))
        d["kind0"] = d.pop("kind0")
    import arch
    imports = sorted({m.group(1) for rx in arch.IMPORT for m in rx.finditer(nocomment)})[:120]
    ftypes = sorted({m.group(1) for m in CAMEL.finditer(nostr)})[:200]
    return {"lang": lang, "imports": imports, "ftypes": ftypes, "defs": out, "n": len(raw_lines)}


# ---- cache --------------------------------------------------------------------------------------------------------

def load_all(root: Path, signature: str, extra_scan=None) -> dict:
    """{relpath: parsed} for every supported tracked file; re-parses only files whose mtime or size changed.
    `extra_scan(rel, lang, text, nocomment, parsed)` may add entry-point hits to `parsed` (it is part of the signature)."""
    cache_f = root / DIRNAME / "cache" / "flow.json"
    persist = (root / DIRNAME).is_dir()                      # no .ffcode/: parse in memory, leave no trace in the repo
    cache = {}
    if persist and cache_f.is_file():
        try: cache = json.loads(cache_f.read_text())
        except (ValueError, OSError): cache = {}
    if cache.get("sig") != signature: cache = {"sig": signature, "files": {}}
    files, out, dirty = cache["files"], {}, False
    live = set()
    for f in tracked_files(root):
        lang = flang(f)
        if not lang: continue
        rel = str(f); p = root / rel
        try: st = p.stat()
        except OSError: continue
        live.add(rel)
        ent = files.get(rel)
        if ent and ent["m"] == st.st_mtime_ns and ent["z"] == st.st_size: out[rel] = ent["d"]; continue
        if not is_text(p) or st.st_size > 1_500_000: continue
        text = p.read_text(errors="replace")
        d = parse(text, lang)
        if extra_scan: extra_scan(rel, lang, text, mask(text, lang)[0], d)
        files[rel] = {"m": st.st_mtime_ns, "z": st.st_size, "d": d}; out[rel] = d; dirty = True
    for gone in set(files) - live: del files[gone]; dirty = True
    if dirty and persist:
        cache_f.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache_f.with_suffix(".tmp"); tmp.write_text(json.dumps(cache, separators=(",", ":"))); tmp.replace(cache_f)
    return out


def digest(*parts: str) -> str:
    return hashlib.sha1("\x00".join(parts).encode()).hexdigest()[:16]
