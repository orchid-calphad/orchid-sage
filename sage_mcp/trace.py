"""Record source checks separately from ORCHID's scientific evidence classification.

Imported provenance stays in the frozen evidence bundle. Local checks and their
history live in traces/TRACES.json; missing checks are reported, never a package gate.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Literal

from . import runner
from .repo import SageError, tilde

DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
STATUSES = ("traced", "comparison_only")
RULE = "record and report source checks; retain ORCHID evidence_class and imported provenance"


def _doi(value: str) -> str:
    return re.sub(r"^(?:doi:|https?://(?:dx\.)?doi\.org/)", "", str(value).strip(), flags=re.I).lower()


def label_states(states: list[dict], obj: dict, cls: str) -> None:
    """Attach local review status without interpreting phase-mapping tags as provenance."""
    obs = (obj.get("orchid") or {}).get("observations") or []
    for s in states:
        i = s["row"]
        row = obs[i] if i < len(obs) and isinstance(obs[i], dict) else {}
        paper = row.get("paper") or s.get("paper") or obj.get("paper")
        reasons = ["no local source check recorded; imported provenance retained"]
        if not (s.get("origin") or {}).get("measured_in"):
            reasons.append("origin.measured_in is absent")
        candidates = []
        for c in s.get("cited_sources") or []:
            if isinstance(c, dict) and (c.get("paper") or c.get("doi")):
                candidates.append(c.get("paper") or "doi:" + c["doi"])
        s["trace"] = {"status": "untraced", "reasons": reasons,
                      "reporting_papers": [paper] if paper else [],
                      "candidate_originals": sorted(set(candidates))}


def state_key(s: dict) -> str:
    return f"{s['source_file']}#{s['row']}"


def effective_class(s: dict, rec: dict | None) -> str:
    """A source check does not establish or change the kind of evidence."""
    return s.get("evidence_class") or "unspecified"


def _states_file(root: Path, st: dict) -> Path:
    return root / st.get("bindings", {}).get("evidence_dir", "evidence") / "states.json"


def _load_states(root: Path, st: dict) -> list[dict] | None:
    p = _states_file(root, st)
    return json.loads(p.read_text(encoding="utf-8"))["states"] if p.is_file() else None


def summary(root: Path, st: dict) -> dict:
    states = _load_states(root, st)
    if states is None:
        return {"status": "no_states", "complete": False, "rule": RULE,
                "reason": f"no {tilde(_states_file(root, st))}: traceability cannot be checked"}
    recs = st.get("traces", {})
    rows, classes = [], {}
    counts = {"traced": 0, "comparison_only": 0, "untraced": 0}
    for s in states:
        k = state_key(s)
        rec = recs.get(k) or {}
        status = rec.get("status") if rec.get("status") in STATUSES else "untraced"
        counts[status] += 1
        ec = effective_class(s, rec)
        classes[ec] = classes.get(ec, 0) + 1
        t = s.get("trace") or {}
        rows.append({"key": k, "status": status, "T_K": s.get("T_K"), "phases": s.get("expected"),
                     "orchid_ids": s.get("orchid_ids"), "evidence_class": ec,
                     "origin": copy.deepcopy(rec.get("origin", s.get("origin", {}))),
                     "source_origin": copy.deepcopy(s.get("origin", {})),
                     "cited_sources": copy.deepcopy(s.get("cited_sources", [])),
                     "reasons": t.get("reasons", []) if status == "untraced" else [rec["why"]],
                     "reporting_papers": t.get("reporting_papers", []),
                     "candidate_originals": t.get("candidate_originals", []),
                     **{f: rec[f] for f in ("doi", "page", "locator", "who", "recorded") if f in rec}})
    return {"status": "checked", "complete": counts["untraced"] == 0, "counts": counts,
            "evidence_classes": classes, "states": rows,
            **{k: [r for r in rows if r["status"] == k] for k in counts}, "rule": RULE}


def record(root: Path, st: dict, keys: list[str], status: Literal["traced", "comparison_only"], who: str, why: str,
           doi: str | None = None, page: str | None = None, locator: str | None = None, quote: str | None = None) -> dict:
    if status not in STATUSES:
        raise SageError(f"status must be one of {STATUSES}")
    for name, v in (("who", who), ("why", why)):
        if not v or not str(v).strip():
            raise SageError(f"refused: {name} is required")
    if who.strip().lower() in ("sage_mcp", "server", "mcp"):
        raise SageError("refused: name the reader, not the server")
    states = _load_states(root, st)
    if states is None:
        raise SageError("refused: the assessment has no evidence states.json to trace")
    by_key = {state_key(s): s for s in states}
    unknown = [k for k in keys if k not in by_key]
    if not keys or unknown or len(by_key) != len(states) or len(set(keys)) != len(keys):
        raise SageError(f"refused: unknown or duplicate state keys {unknown or keys}")
    ent = {"status": status, "who": who.strip(), "why": why.strip(), "recorded": runner.now()}
    if status == "traced":
        d = _doi(doi or "")
        if not DOI_RE.match(d):
            raise SageError("refused: a trace needs a source DOI (10.xxxx/...)")
        if not (page and str(page).strip()) or not (locator and str(locator).strip()):
            raise SageError("refused: a trace needs the page and table or figure")
        ent.update({"doi": d, "page": str(page).strip(), "locator": str(locator).strip(),
                    "quote": (quote or "")[:500] or None})
    st.setdefault("traces", {})
    for k in keys:
        s = by_key[k]
        item = copy.deepcopy(ent)
        if status == "traced":
            origin = copy.deepcopy(s.get("origin") or {})
            rep = {_doi(p) for p in (s.get("trace") or {}).get("reporting_papers", [])}
            origin.update(measured_in="doi:" + d, measured_in_basis="local source check recorded by " + who.strip(),
                          own_work_of_paper=(d in rep) if len(rep) == 1 else None)
            item["origin"] = origin
        prev = st["traces"].get(k)
        st["traces"][k] = dict(item, **({"supersedes": prev} if prev else {}))
    out = root / "traces" / "TRACES.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"rule": RULE, "traces": st["traces"]}, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    return {"recorded": len(keys), "status": status, "file": str(out), "summary": summary(root, st)["counts"]}
