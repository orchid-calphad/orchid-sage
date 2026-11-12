"""Shared helpers for the ORCHID protocol tools (standard library only).

  load_doc(path)            YAML (yamlmini subset) or JSON document
  sha256_file(path)         hex digest of a file (paths may start with ~)
  SchemaValidator           a JSON Schema 2020-12 validator for the keywords this schema family uses
  evidence_digest(refs)     sha256 over the sorted lines "<sha256>  <path>" of the data files an objective read
"""
import hashlib
import json
import os
import re
from pathlib import Path

import localpaths
import yamlmini

ROOT = Path(__file__).resolve().parents[1]          # protocols/
SCHEMA_DIR = ROOT / "schema"
SCHEMA_VERSION = "orchid-assessment-schema@1.0.0-draft.2"


def expand(p):
    """A path as written in a record: '<orchid-sage>/...', '<home>/...' (or a user's '~') through localpaths.expand (this
    checkout for the repository's own paths, the record home otherwise); a relative path is relative to the repository
    root (the directory that holds protocols/)."""
    if str(p).startswith(("~", "<")):
        return localpaths.expand(p)
    q = Path(str(p))
    if q.is_absolute() or q.exists():
        return q
    return ROOT.parent / q


def sha256_file(p, _cache={}):
    p = expand(p)
    key = (str(p), p.stat().st_mtime_ns, p.stat().st_size)
    if key not in _cache:
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        _cache[key] = h.hexdigest()
    return _cache[key]


def load_doc(path):
    path = expand(path)
    if path.suffix in (".yaml", ".yml"):
        return yamlmini.load(path)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _digest_path(p):
    """The digest is defined over the paths in the form the records were written in, where the home directory is a
    tilde; a public copy writes it as <home> (public_sanitize.py), so <home> is read back as the tilde here."""
    h = localpaths.RECORD_HOME
    return "~" + p[len(h):] if p == h or p.startswith(h + "/") else p


def evidence_digest(refs):
    lines = sorted(f"{r['sha256']}  {_digest_path(r['path'])}" for r in refs)
    return hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest()


def tilde(p):
    """Write a path with <orchid-sage> for this checkout and <home> for the home directory (no user name in documents)."""
    s = str(p)
    if s.startswith(str(localpaths.REPO) + os.sep):          # this checkout, wherever it is, as the records name it
        return localpaths.REPO_ALIASES[0] + s[len(str(localpaths.REPO)):]
    h = str(localpaths.record_home())
    return localpaths.RECORD_HOME + s[len(h):] if s.startswith(h) else s


# ----------------------------------------------------------------------------------------------------------------
class SchemaValidator:
    """Subset of JSON Schema 2020-12: $ref (local and relative-file), type, enum, const, pattern, minLength,
    maxLength, minimum, maximum, required, properties, additionalProperties, items, minItems, maxItems, allOf,
    anyOf, oneOf, if/then/else. Unknown keywords are ignored (as the specification allows for annotations)."""

    def __init__(self, schema_dir=SCHEMA_DIR):
        self.dir = Path(schema_dir)
        self.cache = {}

    def _file(self, name):
        if name not in self.cache:
            self.cache[name] = json.loads((self.dir / name).read_text())
        return self.cache[name]

    def _resolve(self, ref, base):
        file, _, frag = ref.partition("#")
        doc_name = file or base
        node = self._file(doc_name)
        for part in [p for p in frag.split("/") if p]:
            node = node[part.replace("~1", "/").replace("~0", "~")]
        return node, doc_name

    def validate(self, inst, schema_name):
        errs = []
        self._v(inst, self._file(schema_name), schema_name, "$", errs)
        return errs

    @staticmethod
    def _type_ok(inst, t):
        if isinstance(t, list):
            return any(SchemaValidator._type_ok(inst, x) for x in t)
        return {"object": isinstance(inst, dict), "array": isinstance(inst, list), "string": isinstance(inst, str),
                "number": isinstance(inst, (int, float)) and not isinstance(inst, bool),
                "integer": isinstance(inst, int) and not isinstance(inst, bool), "boolean": isinstance(inst, bool),
                "null": inst is None}[t]

    def _v(self, inst, s, base, path, errs):
        if s is True or s == {}:
            return
        if s is False:
            errs.append(f"{path}: not allowed"); return
        if "$ref" in s:
            sub, b2 = self._resolve(s["$ref"], base)
            self._v(inst, sub, b2, path, errs)
        if "type" in s and not self._type_ok(inst, s["type"]):
            errs.append(f"{path}: expected {s['type']}, got {type(inst).__name__} ({str(inst)[:60]!r})"); return
        if "const" in s and inst != s["const"]:
            errs.append(f"{path}: must equal {s['const']!r}")
        if "enum" in s and inst not in s["enum"]:
            errs.append(f"{path}: {inst!r} not in {s['enum']}")
        if isinstance(inst, str):
            if "pattern" in s and not re.search(s["pattern"], inst):
                errs.append(f"{path}: {inst[:80]!r} does not match {s['pattern']}")
            if "minLength" in s and len(inst) < s["minLength"]:
                errs.append(f"{path}: shorter than {s['minLength']}")
            if "maxLength" in s and len(inst) > s["maxLength"]:
                errs.append(f"{path}: longer than {s['maxLength']} characters")
        if isinstance(inst, (int, float)) and not isinstance(inst, bool):
            if "minimum" in s and inst < s["minimum"]:
                errs.append(f"{path}: below {s['minimum']}")
            if "maximum" in s and inst > s["maximum"]:
                errs.append(f"{path}: above {s['maximum']}")
        if isinstance(inst, dict):
            for k in s.get("required", []):
                if k not in inst:
                    errs.append(f"{path}: missing required '{k}'")
            props = s.get("properties", {})
            for k, v in inst.items():
                if k in props:
                    self._v(v, props[k], base, f"{path}.{k}", errs)
                elif "additionalProperties" in s:
                    ap = s["additionalProperties"]
                    if ap is False:
                        errs.append(f"{path}: unexpected property '{k}'")
                    elif isinstance(ap, dict):
                        self._v(v, ap, base, f"{path}.{k}", errs)
        if isinstance(inst, list):
            if "minItems" in s and len(inst) < s["minItems"]:
                errs.append(f"{path}: fewer than {s['minItems']} items")
            if "maxItems" in s and len(inst) > s["maxItems"]:
                errs.append(f"{path}: more than {s['maxItems']} items")
            if "items" in s:
                for i, x in enumerate(inst):
                    self._v(x, s["items"], base, f"{path}[{i}]", errs)
        for sub in s.get("allOf", []):
            self._v(inst, sub, base, path, errs)
        if "anyOf" in s:
            if not any(not self._try(inst, sub, base, path) for sub in s["anyOf"]):
                errs.append(f"{path}: matches none of anyOf")
        if "oneOf" in s:
            n = sum(1 for sub in s["oneOf"] if not self._try(inst, sub, base, path))
            if n != 1:
                best = min((self._try(inst, sub, base, path) for sub in s["oneOf"]), key=len)
                errs.append(f"{path}: matches {n} of oneOf (expected 1)" + (f"; closest: {best[0]}" if best else ""))
        if "if" in s:
            if not self._try(inst, s["if"], base, path):
                if "then" in s:
                    self._v(inst, s["then"], base, path, errs)
            elif "else" in s:
                self._v(inst, s["else"], base, path, errs)

    def _try(self, inst, s, base, path):
        e = []
        self._v(inst, s, base, path, e)
        return e
