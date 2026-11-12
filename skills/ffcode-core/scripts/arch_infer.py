"""Draft architecture.toml from the shape of the repo (used by `ff arch infer`).

Three signals, none of them a file name alone:
  1. directories: a layer is the highest directory whose subtree is mostly files with one suffix
     (Service, Controller, ...), so `services/**` wins over `services/user/**`;
  2. imports: the layer graph is measured from the real imports, so `may_import` lists the edges that
     occur and the rare ones are surfaced as probable violations instead of being allowed;
  3. examples: the file whose imports are most typical for its layer, of median size.
Everything is scripted except the answers to the ambiguous cases. `--interview` lists them as closed
questions; the answers are saved in .ffcode/arch-answers.toml and applied by every later run, so
`ff arch infer --write` rebuilds the same file from the repo plus those answers. `--check` reports what
the draft would enforce on the code as it is today. Thresholds, extra suffixes, excluded paths and layer
merges come from `[infer]` in config.toml."""
from __future__ import annotations

import json
import os
import re
import tomllib
from collections import Counter, defaultdict
from pathlib import PurePosixPath

from common import DIRNAME, lang_of, load_config, tracked_files

ANSWERS_FILE = "arch-answers.toml"
SUFFIXES = ("Controller", "Service", "Repository", "Dto", "DTO", "Entity", "Resource", "Handler", "Mapper",
            "Transformer", "Factory", "Middleware", "Provider", "Policy", "Listener", "Job", "Component",
            "Store", "Serializer", "Validator", "Assembler", "Form", "Exception", "Helper")
EXT = {"python", "php", "typescript", "javascript", "matlab", "shell"}
SKIP = re.compile(r"(^|/)(tests?|__tests__|vendor|node_modules|migrations?|dist|build|fixtures?|mocks?|docs?)/")
DEFAULTS = {
    "min_files": 2,         # suffixed files a directory needs to be a layer
    "strict": 0.75,         # share that makes a subtree a layer on its own
    "purity": 0.5,          # looser majority, accepted only to merge same-suffix subdirectories
    "name_purity": 0.95,    # enforce name_pattern only when nearly every file follows it
    "allow_share": 0.05,    # an edge used by fewer files than this is reported, not allowed
    "max_questions": 6,
}
FRAMEWORKS = (("composer.json", "yiisoft/yii2", "yii2"), ("composer.json", "laravel/framework", "laravel"),
              ("package.json", '"next"', "next.js"), ("package.json", '"express"', "express"),
              ("requirements.txt", "django", "django"), ("requirements.txt", "fastapi", "fastapi"))


def options(root, overrides=None) -> dict:
    """Defaults < [infer] in config.toml < overrides. Adds the compiled name matchers."""
    cfg = load_config(root).get("infer", {})
    o = dict(DEFAULTS)
    o.update({k: cfg[k] for k in DEFAULTS if k in cfg})
    o.update(overrides or {})
    names = list(SUFFIXES) + [str(s) for s in cfg.get("suffixes", [])]
    o["canon"] = {}
    for s in names: o["canon"].setdefault(s.lower(), s)
    o["camel"] = re.compile(rf"^.+?({'|'.join(sorted(set(names), key=len, reverse=True))})$")
    o["snake"] = re.compile(rf"^[a-z0-9_]+_({'|'.join(sorted({s.lower() for s in names}, key=len, reverse=True))})$")
    o["exclude"] = [re.compile(x) for x in cfg.get("exclude", [])]
    o["merge"] = dict(x.split("=", 1) for x in cfg.get("merge", []) if "=" in x)   # "job=service": fold a layer into another
    return o


def load_answers(root) -> dict:
    f = root / DIRNAME / ANSWERS_FILE
    return {str(k): str(v) for k, v in tomllib.loads(f.read_text()).items()} if f.is_file() else {}


def save_answers(root, answers: dict):
    body = "# Answers to the `ff arch infer --interview` questions; every `ff arch infer` run applies them.\n" \
           "# Edit or delete a line to be asked again. Committed: it is what makes the architecture reproducible.\n"
    body += "".join(f"{json.dumps(k)} = {json.dumps(v)}\n" for k, v in sorted(answers.items()))
    (root / DIRNAME / ANSWERS_FILE).write_text(body)


def suffix_of(stem: str, o: dict) -> str | None:
    """Lower-case suffix key ('service'), merged as configured, or None."""
    m = o["camel"].match(stem) or o["snake"].match(stem)
    if not m: return None
    key = m.group(1).lower()
    return o["merge"].get(key, key)


def _ancestors(path: PurePosixPath):
    """'a/b/c.php' -> a/b, a  (the directories, nearest first, never the root)."""
    return [str(p) for p in path.parents if str(p) != "."]


def pick_dirs(files: dict, o: dict) -> dict:
    """{dir: suffix}: the highest directories whose subtree is mostly one suffix. `files` maps path -> suffix|None.
    Pass 1 takes only clearly pure subtrees (strict); pass 2 lets a looser majority (purity) absorb the pure
    subdirectories below it when they all carry the same suffix (services/** over services/a, services/b), but never
    when they carry another one (modules/** would swallow modules/api/controllers)."""
    total, count = Counter(), defaultdict(Counter)
    for f, s in files.items():
        for d in _ancestors(PurePosixPath(f)):
            total[d] += 1
            if s: count[d][s] += 1
    order = sorted(total, key=lambda x: (x.count("/"), x))

    def dominant(d):
        return count[d].most_common(1)[0] if count[d] else (None, 0)

    def covered(d, chosen): return any(d == c or d.startswith(c + "/") for c in chosen)

    chosen = {}
    for d in order:
        if covered(d, chosen): continue
        s, k = dominant(d)
        if s and k >= o["min_files"] and k / total[d] >= o["strict"]: chosen[d] = s
    for d in order:
        if covered(d, chosen): continue
        s, k = dominant(d)
        below = [c for c in chosen if c.startswith(d + "/")]
        if s and k >= o["min_files"] and k / total[d] >= o["purity"] and all(chosen[c] == s for c in below):
            for c in below: del chosen[c]
            chosen[d] = s
    return chosen


def _target(imp: str, src: str, dirs: dict) -> str | None:
    """Directory (from `dirs`) an import points at, trying the longest tail first: app\\services\\X -> services."""
    import os
    if imp.startswith("."): n = os.path.normpath(os.path.join(os.path.dirname(src), imp))
    else: n = re.sub(r"[.\\]+", "/", imp)
    parts = n.strip("/").lower().split("/")
    for k in range(len(parts)):
        cand = "/".join(parts[k:])
        for d in dirs:
            if cand == d.lower() or cand.startswith(d.lower() + "/"): return d
    return None


def _imports(text: str):
    import arch
    for rx in arch.IMPORT:
        for m in rx.finditer(text): yield m.group(1)


def _example(root, members, tgt_of):
    """Median-size file with the most typical imports; Base*/Abstract* classes are poor models."""
    info = []
    for f in members:
        text = (root / f).read_text(errors="replace")
        info.append((f, text.count("\n"), {t for t in tgt_of(f, text) if t}))
    freq = Counter(t for _, _, ts in info for t in ts)
    info.sort(key=lambda x: x[1])
    lo, hi = len(info) // 4, max(len(info) * 3 // 4, len(info) // 4 + 1)
    pool = [x for x in info[lo:hi] if not re.match(r"(Base|Abstract)", PurePosixPath(x[0]).stem)] or info
    best = max(pool, key=lambda x: (sum(freq[t] for t in x[2]) / (len(x[2]) or 1), -x[1], x[0]))
    return best[0]


def framework(root) -> str:
    for fname, needle, name in FRAMEWORKS:
        p = root / fname
        try:
            if p.is_file() and needle in p.read_text(errors="replace"): return name
        except OSError: pass
    return ""


def _top(d: str) -> str: return d.split("/")[0]


def analyze(root, o: dict, answers: dict | None = None) -> dict | None:
    """The inferred architecture as data: layers, edges, unplaced files and the open questions."""
    answers = answers or {}
    files = {}
    for f in tracked_files(root):
        s = str(f)
        if lang_of(f) not in EXT or SKIP.search(s) or re.match(r"m?\d{6,}", PurePosixPath(s).stem): continue
        if any(rx.search(s) for rx in o["exclude"]): continue
        files[s] = suffix_of(PurePosixPath(s).stem, o)
    dirs = pick_dirs(files, o)
    if not dirs: return None
    layer_of_dir = dict(dirs)
    for layer in sorted(set(dirs.values())):                 # a layer the user asked to split by top-level directory
        if answers.get(f"split:{layer}") != "split": continue
        ds = [d for d, l in dirs.items() if l == layer]
        main = Counter(_top(d) for d in ds).most_common(1)[0][0]
        for d in ds:
            if _top(d) != main: layer_of_dir[d] = f"{layer}_{_top(d)}"
    members, placed = defaultdict(list), set()
    for f in files:
        for d in _ancestors(PurePosixPath(f)):
            if d in layer_of_dir: members[layer_of_dir[d]].append(f); placed.add(f); break
    cache = {}

    def targets(f, text=None):
        if f not in cache:
            text = text if text is not None else (root / f).read_text(errors="replace")
            cache[f] = [(_target(i, f, layer_of_dir), i) for i in _imports(text)]
        return [layer_of_dir.get(t) for t, _ in cache[f]]

    edges = defaultdict(Counter)                              # layer -> other layer -> files using it
    for layer, fs in members.items():
        for f in fs:
            targets(f)
            for lt in {layer_of_dir.get(t) for t, _ in cache[f]} - {None, layer}: edges[layer][lt] += 1
    incoming = Counter()
    for row in edges.values():
        for b, n in row.items(): incoming[b] += n
    order = sorted(members, key=lambda l: (incoming[l], l))  # outside first: nobody imports it
    layers, questions = [], []
    for layer in order:
        fs = members[layer]
        base = layer.split("_")[0] if layer.split("_")[0] in set(dirs.values()) and layer not in set(dirs.values()) else layer
        suffix = o["canon"].get(base, base.capitalize())
        pure = sum(1 for f in fs if files[f] == base) / len(fs)
        row = edges.get(layer, Counter())
        share = {b: n / len(fs) for b, n in row.items()}
        default_ok = {b for b, n in row.items() if share[b] >= o["allow_share"] and n >= 2}
        allowed = {b for b in row if answers.get(f"edge:{layer}>{b}") == "allow" or
                   (b in default_ok and answers.get(f"edge:{layer}>{b}") != "forbid")}
        pattern = {"yes": True, "no": False}.get(answers.get(f"names:{layer}"), pure >= o["name_purity"])
        paths = sorted(d for d, l in layer_of_dir.items() if l == layer)
        layers.append({"name": layer, "paths": paths, "n": len(fs), "pure": pure, "suffix": suffix, "pattern": pattern,
                       "mismatch": [f for f in fs if files[f] != base], "edges": row, "allowed": sorted(allowed),
                       "rare": sorted((b, n) for b, n in row.items() if b not in allowed),
                       "example": _example(root, fs, lambda f, t: targets(f, t))})
        where = ", ".join(paths[:3]) + ("…" if len(paths) > 3 else "")
        if o["name_purity"] * 0.5 <= pure < o["name_purity"]:
            questions.append((0.5, f"names:{layer}", f"{round((1 - pure) * len(fs))} of {len(fs)} files in layer '{layer}' ({where}) "
                              f"are not named *{suffix}. Enforce the *{suffix} name anyway (they would be flagged)?",
                              "no", [("no", "No, leave names free"), ("yes", f"Yes, enforce *{suffix}")]))
        for b, n in row.items():
            if n >= 2 and share[b] <= o["allow_share"] * 3:
                questions.append((1 + abs(share[b] - o["allow_share"]), f"edge:{layer}>{b}",
                                  f"{n} of {len(fs)} files in '{layer}' import '{b}'. Does the architecture allow that dependency?",
                                  "allow" if b in default_ok else "forbid",
                                  [("allow", f"Allow {layer} -> {b}"), ("forbid", "Forbid it (existing files get flagged)")]))
        big = [t for t in {_top(p) for p in paths} if sum(1 for f in fs if f.startswith(t + "/")) >= 5]
        if layer in set(dirs.values()) and len(big) >= 2:
            questions.append((0, f"split:{layer}", f"Layer '{layer}' spans {', '.join(sorted(big))}. One layer or one per directory?",
                              "keep", [("keep", "One layer"), ("split", "Split by top-level directory")]))
    questions = [q[1:] for q in sorted(questions, key=lambda q: q[0])]
    names = {l["name"] for l in layers}
    return {"framework": framework(root), "style": "rest-layered" if {"controller", "service"} <= names else "",
            "layers": layers, "unplaced": [f for f in files if f not in placed], "questions": questions}


def interview(model: dict, answered: dict, limit: int) -> str:
    """Open questions as JSON [{id, question, default, options: [{value, label}]}], those not answered yet."""
    qs = [{"id": i, "question": q, "default": d, "options": [{"value": v, "label": lb} for v, lb in opts]}
          for i, q, d, opts in model["questions"] if i not in answered][:limit]
    return json.dumps({"questions": qs}, indent=2, ensure_ascii=False)


def check(model: dict) -> str:
    """What the draft would enforce on the repo as it is today, and what it leaves out."""
    out, flagged = ["ff arch infer --check: the draft against the current code"], 0
    for l in model["layers"]:
        if l["pattern"] and l["mismatch"]:
            flagged += len(l["mismatch"])
            out.append(f"  ARCHNAME {l['name']}: {len(l['mismatch'])} existing file(s) would be flagged, e.g. {', '.join(l['mismatch'][:3])}")
        for b, n in l["rare"]:
            flagged += n
            out.append(f"  ARCHDEP  {l['name']} -> {b}: {n} existing file(s) would be flagged")
    out.append(f"{flagged} existing finding(s) in total" if flagged else "no existing finding: the draft agrees with the code")
    un = Counter("/".join(PurePosixPath(f).parts[:2]) for f in model["unplaced"])
    if un:
        out.append(f"{len(model['unplaced'])} source file(s) belong to no layer; largest groups:")
        out += [f"  {n:4} {d}" for d, n in un.most_common(8)]
    return "\n".join(out)


def render(model: dict) -> str:
    fw = model["framework"]
    out = [f'# Inferred by `ff arch infer` from directories, imports, names and .ffcode/{ANSWERS_FILE}'
           f'{f" (framework: {fw})" if fw else ""}. Review before trusting.\n'
           f'[architecture]\nstyle = "{model["style"]}"      # rest-layered | mvc | hexagonal | components ...\nsummary = ""\n']
    for l in model["layers"]:
        ev = ", ".join(f"{b} {n}/{l['n']}" for b, n in l["edges"].most_common()) or "no imports of other layers seen"
        block = [f'[[layer]]\n# {l["n"]} files, {l["pure"]:.0%} *{l["suffix"]}; imports: {ev}',
                 f'name = "{l["name"]}"', "paths = [" + ", ".join(json.dumps(p + "/**") for p in l["paths"]) + "]"]
        pat = f'name_pattern = "(?i).*{l["suffix"]}"'
        block.append(pat if l["pattern"] else f'# {pat}   # {l["pure"]:.0%} of the files match: set it if you want it enforced')
        if l["edges"]: block.append("may_import = [" + ", ".join(json.dumps(b) for b in l["allowed"]) + "]")
        else: block.append("# may_import = []   # nothing observed: decide")
        for b, n in l["rare"]: block.append(f"#   rare: {n} file(s) import '{b}' — probable violation, not allowed above")
        block.append(f'example = "{l["example"]}"')
        if l["pattern"]: block.append(f'stem = "{{Name}}{l["suffix"]}"')
        out.append("\n".join(block) + "\n")
    return "\n".join(out)
