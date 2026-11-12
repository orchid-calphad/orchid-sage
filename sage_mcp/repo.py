"""Repository access: locate the orchid-sage checkout, load protocol documents, hash files.

The protocol tools in protocols/tools/ (yamlmini, orchidproto, validate.py, orchid_reproduce.py, ...) are used as they
are: imported for their parsers and schema validator, or run through their command lines. Nothing here edits a file
under protocols/ or assessments/.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any


class SageError(Exception):
    """An error reported to the MCP caller as {"error": ...}."""


def repo_root() -> Path:
    env = os.environ.get("SAGE_REPO")
    root = Path(env).expanduser().resolve() if env else Path(__file__).resolve().parents[1]
    if not (root / "protocols" / "tools" / "yamlmini.py").is_file():
        raise SageError(f"orchid-sage checkout not found at {root} (set SAGE_REPO to the directory that holds protocols/)")
    return root


def tools_dir() -> Path:
    return repo_root() / "protocols" / "tools"


def _import_tools() -> None:
    td = str(tools_dir())
    if td not in sys.path:
        sys.path.insert(0, td)


def yamlmini():
    _import_tools()
    import yamlmini as ym  # noqa: PLC0415

    return ym


def orchidproto():
    _import_tools()
    import orchidproto as op  # noqa: PLC0415

    return op


def evidence_bundle_module():
    """protocols/tools/build_evidence_bundle.py as a module (its states_from_zpf, classify, long_strings, TIER, RULE)."""
    _import_tools()
    import build_evidence_bundle as beb  # noqa: PLC0415

    return beb


def localpaths():
    """protocols/tools/localpaths.py: every machine-specific location and host name (environment or local/config.json)."""
    _import_tools()
    import localpaths as lp  # noqa: PLC0415

    return lp


def expand(p: str | Path) -> Path:
    """A record or user path: '<orchid-sage>/...', '<home>/...' or a user's '~' through localpaths.expand; a relative path
    is relative to the repository root."""
    s = str(p)
    if s.startswith(("~", "<")):
        return localpaths().expand(s)
    q = Path(s)
    return q if q.is_absolute() else repo_root() / q


def tilde(p: str | Path) -> str:
    s = str(p)
    r = str(repo_root())
    if s.startswith(r + os.sep):                     # this checkout, as the records name it
        return localpaths().REPO_ALIASES[0] + s[len(r):]
    h = str(localpaths().record_home())
    return localpaths().RECORD_HOME + s[len(h):] if s.startswith(h + os.sep) or s == h else s


def sha256_file(p: str | Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_doc(path: str | Path) -> Any:
    path = Path(path)
    if path.suffix in (".yaml", ".yml"):
        return yamlmini().load(path)
    return json.loads(path.read_text(encoding="utf-8"))


def rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(repo_root()))
    except ValueError:
        return tilde(p)


# ------------------------------------------------------------------ documents in the repository
DOC_GLOBS = {
    "general_protocol": "protocols/general/*.yaml",
    "specific_protocol": "protocols/specific/*.yaml",
    "run_card": "protocols/run_cards/*.json",
    "assessment_results": "protocols/dashboards/*/dashboard_data.json",
}


def _key(d: dict) -> str:
    return f"{d.get('id')}@{d.get('version')}"


@lru_cache(maxsize=64)
def _load_cached(path: str, mtime_ns: int) -> Any:
    return load_doc(path)


def load(path: Path) -> Any:
    return _load_cached(str(path), path.stat().st_mtime_ns)


def repo_protocols() -> dict[str, tuple[Path, dict]]:
    """id@version -> (path, document) for every general and specific protocol under protocols/."""
    out: dict[str, tuple[Path, dict]] = {}
    for t in ("general_protocol", "specific_protocol"):
        for f in sorted(repo_root().glob(DOC_GLOBS[t])):
            d = load(f)
            out[_key(d)] = (f, d)
    return out


def extra_general_dirs() -> list[Path]:
    """Directories with proposed (unmerged) general-protocol versions written by propose_general_change."""
    from . import state  # noqa: PLC0415

    d = state.general_dir()
    return [d] if d.is_dir() else []


def general_protocols() -> dict[str, tuple[Path, dict]]:
    out = {k: v for k, v in repo_protocols().items() if v[1].get("type") == "general_protocol"}
    for d in extra_general_dirs():
        for f in sorted(d.glob("*.json")):
            doc = load(f)
            out.setdefault(_key(doc), (f, doc))
    return out


def find_protocol(ref: str) -> tuple[Path, dict]:
    """Resolve 'id@version', bare 'id' (only one version) or a path to a protocol document."""
    allp = {**repo_protocols(), **general_protocols()}
    if ref in allp:
        return allp[ref]
    by_id = [k for k in allp if k.split("@")[0] == ref]
    if len(by_id) == 1:
        return allp[by_id[0]]
    if len(by_id) > 1:
        raise SageError(f"protocol {ref!r} has several versions: {sorted(by_id)}; give id@version")
    p = Path(os.path.expanduser(ref))
    if p.is_file():
        return p, load(p)
    raise SageError(f"unknown protocol {ref!r}; known: {sorted(allp)}")


def general_of(spec: dict) -> tuple[Path, dict]:
    ins = (spec.get("instantiates") or [{}])[0]
    return find_protocol(ins.get("protocol", ""))


def assessment_dir(spec: dict) -> Path:
    return repo_root() / "assessments" / spec["id"]


# ------------------------------------------------------------------ steps
def iter_steps(doc: dict):
    for sec in doc.get("sections", []) or []:
        for st in sec.get("steps", []):
            yield sec, st


def step_table(spec: dict) -> dict[str, dict]:
    """step id -> {section, step, origin} over the general protocol (if any) and the document's own sections."""
    table: dict[str, dict] = {}
    if spec.get("type") == "specific_protocol":
        try:
            _, gen = general_of(spec)
            for sec, st in iter_steps(gen):
                table[st["id"]] = {"section": sec["id"], "step": st, "origin": _key(gen)}
        except SageError:
            pass
    for sec, st in iter_steps(spec):
        table[st["id"]] = {"section": sec["id"], "step": st, "origin": _key(spec)}
    return table


PLACEHOLDER = re.compile(r"<([A-Za-z_][A-Za-z0-9_ .|-]*)>")


def placeholders(cmd: str | None) -> list[str]:
    return sorted(set(PLACEHOLDER.findall(cmd or "")))


def file_refs(node: Any, path: str = "$"):
    if isinstance(node, dict):
        if "path" in node and "sha256" in node and "storage_class" in node:
            yield path, node
        for k, v in node.items():
            yield from file_refs(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from file_refs(v, f"{path}[{i}]")


def schema_errors(doc: dict) -> list[str]:
    op = orchidproto()
    name = "assessment-results.schema.json" if doc.get("type") == "assessment_results" else "protocol.schema.json"
    return op.SchemaValidator().validate(doc, name)
