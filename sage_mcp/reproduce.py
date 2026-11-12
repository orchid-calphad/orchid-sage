"""Reproduce mode: read, check, plan, run and compare an existing specific protocol of the repository.

Execution items of a specific protocol, in order:
  stage               protocols/tools/orchid_reproduce.py SPEC --root R --stage-only   (code + evidence by sha256)
  environment_check   reproduce.environment_check of the specific protocol, with the chosen interpreter
  evaluate_states     sage_mcp binding of the general step evaluate_states to the frozen bundle (deterministic)
  tdb_header          sage_mcp binding of the general step tdb_header (deterministic)
  <plan items>        reproduce.plan of the specific protocol (the fits; numerical), run exactly as orchid_reproduce.py does
The two bindings are not in the specific protocols' reproduce.plan; each item says where its command comes from.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from . import backends, runner, safety
from .repo import (
    SageError, assessment_dir, expand, file_refs, find_protocol, general_of, load, localpaths, repo_protocols, repo_root,
    sha256_file, step_table, tilde, tools_dir,
)

LONG_S = float(os.environ.get("SAGE_MCP_LONG_S", "600"))
GPU_ENVS = {"mlip_container"}


# ================================================================== read tools
def list_protocols() -> dict:
    from . import fresh, state  # noqa: PLC0415

    out = []
    for key, (p, d) in sorted(repo_protocols().items()):
        out.append({"ref": key, "type": d["type"], "title": d.get("title"), "status": d.get("status"),
                    "path": str(p.relative_to(repo_root())), "sha256": sha256_file(p),
                    "own_steps": sum(len(s["steps"]) for s in d.get("sections", []) or []),
                    "steps_note": "a specific protocol also has every step of the general protocol it instantiates (get_steps)" if d["type"] == "specific_protocol" else None,
                    "reproduce_plan": [i["id"] for i in (d.get("reproduce") or {}).get("plan", [])] if d["type"] == "specific_protocol" else None,
                    "instantiates": [i["protocol"] for i in d.get("instantiates", [])] or None, "mode": "reproduce" if d["type"] == "specific_protocol" else "general"})
    for f in sorted(state.general_dir().glob("*.json")) if state.general_dir().is_dir() else []:
        d = load(f)
        out.append({"ref": f"{d['id']}@{d['version']}", "type": d["type"], "title": d.get("title"), "status": d.get("status"),
                    "path": tilde(f), "sha256": sha256_file(f), "mode": "proposed general version (not merged into protocols/general)"})
    for aid, root in sorted(state.registry().items()):
        try:
            spec_path, spec = fresh.current_spec(Path(root))
            out.append({"ref": f"{spec['id']}@{spec['version']}", "type": "specific_protocol", "title": spec.get("title"),
                        "status": spec.get("status"), "path": tilde(spec_path), "assessment": aid, "run_root": tilde(root), "mode": "fresh"})
        except (SageError, FileNotFoundError):
            out.append({"assessment": aid, "run_root": root, "mode": "fresh", "error": "run root missing or unreadable"})
    return {"protocols": out, "count": len(out)}


def _summary(d: dict) -> dict:
    keep = ("type", "schema_version", "id", "version", "title", "status", "status_note", "system", "purpose", "created",
            "instantiates", "artifact", "open_questions", "limitations")
    s = {k: d[k] for k in keep if k in d}
    s["sections"] = [{"id": sec["id"], "name": sec.get("name"), "steps": [st["id"] for st in sec["steps"]]} for sec in d.get("sections", []) or []]
    s["inputs"] = [{"id": i["id"], "name": i.get("name"), "storage_class": i.get("storage_class")} for i in d.get("inputs", [])]
    if d.get("run_sequence"):
        s["run_sequence"] = [{k: r.get(k) for k in ("run_id", "step", "status", "pick", "start_from", "summary")} for r in d["run_sequence"]]
    if d.get("reproduce"):
        s["reproduce_plan"] = [{"id": i["id"], "step": i["step"], "kind": i["kind"]} for i in d["reproduce"].get("plan", [])]
    s["n_overrides"] = len(d.get("overrides", []) or [])
    s["n_decisions"] = len(d.get("decisions", []) or [])
    return s


def _resolve_any(protocol: str) -> tuple[Path, dict, Path | None]:
    """A repo protocol ref, or a fresh assessment id/run root. Returns (path, document, run_root or None)."""
    from . import fresh, state  # noqa: PLC0415

    if protocol in state.registry() or (Path(os.path.expanduser(protocol)) / "sage_state.json").is_file():
        root = state.resolve(protocol)
        p, d = fresh.current_spec(root)
        return p, d, root
    p, d = find_protocol(protocol)
    return p, d, None


def get_protocol(protocol: str, fields: str = "summary") -> dict:
    p, d, root = _resolve_any(protocol)
    out = {"path": tilde(p), "sha256": sha256_file(p)}
    if root:
        out["run_root"] = tilde(root)
    if fields == "full":
        out["document"] = d
    else:
        out["summary"] = _summary(d)
    md = p.with_suffix(".md")
    if md.is_file():
        out["rendered_markdown"] = tilde(md) if root else str(md.relative_to(repo_root()))
    return out


def _step_brief(sid: str, ent: dict) -> dict:
    st = ent["step"]
    t = st.get("tool", {})
    return {"id": sid, "section": ent["section"], "name": st.get("name"), "kind": st.get("kind"), "origin": ent["origin"],
            "command": t.get("command"), "environment": t.get("environment"), "compute": compute_class(st)["class"]}


def get_steps(protocol: str, section: str | None = None) -> dict:
    _, d, _ = _resolve_any(protocol)
    tab = step_table(d)
    steps = [_step_brief(k, v) for k, v in tab.items() if section in (None, "", v["section"])]
    out: dict[str, Any] = {"protocol": f"{d['id']}@{d['version']}", "steps": steps, "count": len(steps)}
    if d.get("type") == "specific_protocol" and d.get("reproduce") and not section:
        out["reproduce_items"] = [{k: it.get(k) for k in ("id", "step", "kind", "source")} for it in repro_items(d)]
    if section and not steps:
        out["sections"] = sorted({v["section"] for v in tab.values()})
    return out


def compute_class(st: dict) -> dict:
    env = (st.get("tool") or {}).get("environment")
    if env in GPU_ENVS:
        return {"class": "GPU", "estimate": "2-11 h (general protocol compute.typical_wall: one-shot 2-5 h per potential, liquid 4-11 h)", "long": True}
    if st.get("kind") == "numerical":
        return {"class": "CPU", "estimate": "0.5-1.5 h per fit step (compute.typical_wall); Laplace ~0.5 h", "long": True}
    if st.get("kind") == "judgement":
        return {"class": "human", "estimate": "decision", "long": False}
    return {"class": "CPU", "estimate": "seconds to minutes", "long": False}


def get_step(protocol: str, step_id: str) -> dict:
    _, d, root = _resolve_any(protocol)
    tab = step_table(d)
    items = {it["id"]: it for it in repro_items(d)} if d.get("reproduce") and d["reproduce"].get("plan") else {}
    if step_id not in tab and step_id not in items:
        raise SageError(f"unknown step {step_id!r}; steps: {sorted(tab)}; reproduce items: {sorted(items)}")
    out: dict[str, Any] = {"protocol": f"{d['id']}@{d['version']}"}
    if step_id in tab:
        ent = tab[step_id]
        st = ent["step"]
        t = st.get("tool", {})
        out.update({"id": step_id, "section": ent["section"], "origin": ent["origin"], "name": st["name"], "kind": st["kind"],
                    "text": st["text"], "command": t.get("command"), "tool": t, "inputs": st.get("supply", []),
                    "outputs": st.get("result", []), "decision_rule": st.get("decision_rule"), "decided_by": st.get("decided_by"),
                    "tolerances": st.get("tolerances"), "gates": st.get("gates"), "rationale": st.get("rationale"),
                    "compute": compute_class(st), "placeholders": sorted(set(re.findall(r"<([^<>]+)>", t.get("command") or "")))})
        if d.get("type") == "specific_protocol":
            out["runs"] = [r for r in d.get("run_sequence", []) if r.get("step") == step_id]
            out["executed_by_reproduce_items"] = [i for i, it in items.items() if it["step"] == step_id]
            ovs = [o for o in d.get("overrides", []) if step_id in json.dumps(o)]
            if ovs:
                out["overrides"] = ovs
            if st["kind"] == "judgement":
                out["recorded_decision"] = recorded_decision(d, step_id)
    if step_id in items:
        out["reproduce_item"] = items[step_id]
    return out


def recorded_decision(d: dict, step_id: str) -> dict:
    """For a judgement step: what the specific protocol records about it (never decided here)."""
    tab = step_table(d)
    st = tab[step_id]["step"]
    fed_by = sorted({s.split(".")[0] for s in st.get("supply", []) if "." in s and not s.startswith(("input:", "param:"))})
    runs = [r for r in d.get("run_sequence", []) if r.get("step") in fed_by or r.get("step") == step_id]
    words = {step_id, *fed_by}
    run_ids = {r["run_id"] for r in runs}
    dec = [x for x in d.get("decisions", []) if step_id in (x.get("applies_to") or [])
           or any(w in json.dumps(x) for w in words | run_ids)]
    picks = [{k: r.get(k) for k in ("run_id", "step", "status", "pick", "summary", "run_card")} for r in runs if r.get("pick") or r.get("step") == step_id]
    return {"step": step_id, "decided_by": st.get("decided_by"), "decision_rule": st.get("decision_rule"),
            "picks_in_run_sequence": picks, "decisions": dec,
            "note": (None if dec else "no decisions-log entry names this step or its runs; the outcome is recorded only in run_sequence"
                     + ("" if picks else " (nothing recorded either)")),
            "linkage": "decisions are matched by applies_to when present, else by the step id, the ids of the steps feeding it and their run ids (SCHEMA_GAPS G5)"}


def get_run_cards(protocol: str) -> dict:
    _, d, root = _resolve_any(protocol)
    out = []
    for r in d.get("run_sequence", []):
        ent = {k: r.get(k) for k in ("run_id", "step", "status", "starts", "pick", "start_from", "summary")}
        rc = r.get("run_card")
        if rc:
            p = expand(rc["path"])
            ent["run_card"] = {"path": rc["path"], "sha256": rc["sha256"], "exists": p.is_file()}
            if p.is_file():
                ent["run_card"]["sha256_ok"] = sha256_file(p) == rc["sha256"]
                c = load(p)
                ent["card"] = {k: c.get(k) for k in ("host", "hardware_class", "started", "finished", "interpreter", "command", "threads", "seeds", "packages")}
                ent["card"]["n_inputs"] = len(c.get("inputs", []))
                ent["card"]["n_outputs"] = len(c.get("outputs", []))
                ent["card"]["trajectory"] = c.get("trajectory")
        out.append(ent)
    if root:
        out += [{"run_card": tilde(p), "native": True} for p in sorted((root / "run_cards").glob("*.json"))]
    return {"protocol": f"{d['id']}@{d['version']}", "runs": out, "count": len(out)}


def get_decisions(protocol: str) -> dict:
    _, d, root = _resolve_any(protocol)
    out = {"protocol": f"{d['id']}@{d['version']}", "decisions": d.get("decisions", []), "overrides": d.get("overrides", [])}
    if root:
        from . import fresh  # noqa: PLC0415

        out["decision_requests"] = fresh.load_state(root)["decision_requests"]
    return out


def _assessment_of(name: str) -> Path:
    a = repo_root() / "assessments" / name
    if a.is_dir():
        return a
    try:
        _, d = find_protocol(name)
        return assessment_dir(d)
    except SageError:
        pass
    raise SageError(f"unknown assessment {name!r}; known: {sorted(p.name for p in (repo_root() / 'assessments').iterdir() if p.is_dir())}")


def get_evidence_manifest(assessment: str, kind: str | None = None, limit: int = 50, offset: int = 0) -> dict:
    from . import state  # noqa: PLC0415

    if assessment in state.registry():
        ev = state.resolve(assessment) / "evidence"
    else:
        ev = _assessment_of(assessment) / "evidence"
    man_p = latest_manifest(ev)
    if man_p is None:
        return {"error": f"no evidence bundle at {tilde(ev)} (run gather_evidence for a fresh assessment)"}
    m = json.loads(man_p.read_text())
    files = [f for f in m["files"] if kind in (None, "", f.get("kind"))]
    lines = sorted(f"{f['sha256']}  {f['path']}" for f in m["files"])
    import hashlib  # noqa: PLC0415

    recomputed = hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest()
    bad = [f["path"] for f in files[offset:offset + limit] if not (ev / f["path"]).is_file() or sha256_file(ev / f["path"]) != f["sha256"]]
    return {"manifest": tilde(man_p), "manifest_sha256": sha256_file(man_p), "bundle": m.get("bundle"), "version": m.get("version"),
            "builder": m.get("builder"), "rule": m.get("rule"), "counts": m.get("counts"), "held": m.get("held"),
            "bundle_sha256": m.get("bundle_sha256"), "bundle_sha256_recomputes": recomputed == m.get("bundle_sha256"),
            "kinds": sorted({f.get("kind") for f in m["files"]}), "total": len(files), "offset": offset,
            "link_coverage": {k: v for k, v in (m.get("link_coverage") or {}).items() if k != "orchid_checkout"} or None,
            "files": [{k: f.get(k) for k in ("path", "sha256", "kind", "orchid_ids", "state_ids", "orchid_link", "missing_reason", "intake_ref") if k in f or k in ("orchid_ids", "state_ids")}
                      for f in files[offset:offset + limit]],
            "files_failing_hash_in_page": bad}


def latest_manifest(ev: Path) -> Path | None:
    """The newest evidence bundle version (MANIFEST@<version>.json; bundles are never overwritten), else MANIFEST.json."""
    vs = sorted(ev.glob("MANIFEST@*.json"), key=lambda q: [int(x) if x.isdigit() else x for x in re.split(r"[.@]", q.stem.split("@", 1)[1])])
    if vs:
        return vs[-1]
    return ev / "MANIFEST.json" if (ev / "MANIFEST.json").is_file() else None


def get_evidence_links(assessment: str, link: str | None = None, reason: str | None = None, limit: int = 50, offset: int = 0) -> dict:
    from . import state  # noqa: PLC0415

    ev = (state.resolve(assessment) if assessment in state.registry() else _assessment_of(assessment)) / "evidence"
    man_p = latest_manifest(ev)
    if man_p is None:
        return {"error": f"no evidence bundle at {tilde(ev)}"}
    m = json.loads(man_p.read_text())
    sp = ev / (f"states@{m['version']}.json" if "@" in man_p.name else "states.json")
    S = json.loads(sp.read_text())
    cov = S.get("link_coverage")
    rows = []
    for i, s_ in enumerate(S["states"]):
        lk = s_.get("orchid_link", "missing" if not s_.get("orchid_ids") else None)
        if link and lk != link:
            continue
        if reason and reason not in (s_.get("missing_reason") or ""):
            continue
        rows.append({"index": i, "source_file": s_.get("source_file"), "kind": s_.get("kind"), "T_K": s_.get("T_K"), "x": s_.get("x"),
                     "expected": s_.get("expected"), "orchid_link": lk, "orchid_ids": s_.get("orchid_ids", []), "state_ids": s_.get("state_ids", []),
                     "orchid_release": s_.get("orchid_release"), "links": s_.get("orchid_links", []),
                     "missing_reason": s_.get("missing_reason"), "intake_ref": s_.get("intake_ref")})
    return {"assessment": assessment, "bundle_version": m.get("version"), "bundle_sha256": m.get("bundle_sha256"), "states_file": tilde(sp),
            "link_coverage": cov, "total": len(rows), "offset": offset, "states": rows[offset:offset + limit],
            "resolve": ("record id -> orchid-data-next literature/systems/<SYS>.json `id` (pid, paper_id = DOI, locator page/table/row); "
                        "state_id / state_class_id -> Y25 state registry graph/observations.parquet; missing -> intake_ref in intake/ "
                        "(resolves once v2027.01 is released)"),
            "files_missing_link": [{k: f.get(k) for k in ("path", "kind", "missing_reason", "intake_ref")} for f in m["files"] if f.get("orchid_link") == "missing"][:limit]}


def get_dashboard_data(assessment: str, section: str | None = None, max_items: int = 50) -> dict:
    from . import state  # noqa: PLC0415

    if assessment in state.registry():
        p = state.resolve(assessment) / "dashboard" / "dashboard_data.json"
    else:
        name = _assessment_of(assessment).name
        p = repo_root() / "protocols" / "dashboards" / name / "dashboard_data.json"
    if not p.is_file():
        return {"error": f"no dashboard data at {tilde(p)}"}
    d = json.loads(p.read_text())
    out: dict[str, Any] = {"path": tilde(p), "sha256": sha256_file(p), "id": d.get("id"), "specific_protocol": d.get("specific_protocol")}
    if not section:
        out["sections"] = {k: {"type": type(v).__name__, "items": len(v) if isinstance(v, (list, dict)) else None,
                               "bytes": len(json.dumps(v))} for k, v in d.items()}
        out["pick"] = d.get("pick")
        out["status_banner"] = d.get("status_banner")
        out["note"] = "pass section=<name> for one section (lists truncated to max_items)"
        return out
    if section not in d:
        raise SageError(f"unknown section {section!r}; sections: {sorted(d)}")
    v = d[section]
    if section == "trajectory" and isinstance(v, dict):
        v = {**{k: x for k, x in v.items() if k != "runs"},
             "runs": [{**{k: x for k, x in r.items() if k != "points"}, "n_points": len(r.get("points", [])),
                       "first_last": r.get("points", [])[:1] + r.get("points", [])[-1:]} for r in v.get("runs", [])[:max_items]]}
    elif isinstance(v, list):
        out["total"] = len(v)
        v = v[:max_items]
    out[section] = v
    return out


def get_open_questions(ids: list[str] | None = None) -> dict:
    p = repo_root() / "protocols" / "OPEN_QUESTIONS.md"
    text = p.read_text()
    parts = re.split(r"^###\s+(Q\d+)\s*$", text, flags=re.M)
    qs = []
    group = None
    for i in range(1, len(parts), 2):
        qid, body = parts[i], parts[i + 1]
        prev = parts[i - 1]
        g = re.findall(r"^##\s+(.+)$", prev, flags=re.M)
        if g:
            group = g[-1]
        body_main = re.split(r"^##\s+", body, flags=re.M)[0].strip()
        status = re.search(r"\*\*Status[^*]*\*\*:?\s*([^\n]*)", body_main)
        qs.append({"id": qid, "group": group, "resolved": bool(status and "RESOLVED" in status.group(0)),
                   "status": status.group(0).strip("> ") if status else "open", "text": body_main})
    if ids:
        qs = [q for q in qs if q["id"] in ids]
    return {"path": "protocols/OPEN_QUESTIONS.md", "sha256": sha256_file(p), "questions": qs, "count": len(qs),
            "open": [q["id"] for q in qs if not q["resolved"]]}


# ================================================================== checks
def validate(document: str | None = None) -> dict:
    """validate.py over all repository documents, or the lines of one document; a fresh assessment's protocol is
    checked against the schema directly (validate.py only reads protocols/)."""
    from . import fresh, state  # noqa: PLC0415

    if document and (document in state.registry() or (Path(os.path.expanduser(document)) / "sage_state.json").is_file()):
        return fresh.validate_assessment(document)
    r = subprocess.run([sys.executable, str(tools_dir() / "validate.py"), "--quiet"], capture_output=True, text=True, cwd=repo_root())
    lines = r.stdout.splitlines()
    errs = [ln.strip()[len("ERROR "):] for ln in lines if ln.strip().startswith("ERROR")]
    warns = [ln.strip()[len("WARN "):] for ln in lines if ln.strip().startswith("WARN")]
    head = next((ln for ln in lines if ln.startswith("documents:")), "")
    if document and document != "all":
        try:
            p, d = find_protocol(document)
            keys = {str(p.relative_to(repo_root() / "protocols")), f"{d['id']}@{d['version']}"}
        except SageError:
            keys = {document}
        errs = [e for e in errs if any(k in e for k in keys)]
        warns = [w for w in warns if any(k in w for k in keys)]
    return {"validator": "protocols/tools/validate.py --quiet", "exit_code": r.returncode, "summary": head,
            "document": document or "all", "errors": errs, "warnings": warns, "ok": not errs,
            "note": "errors of other documents are filtered out when a document is named; exit_code is for the whole repository"}


def verify_inputs(protocol: str, detail: bool = False) -> dict:
    """sha256 of every file the protocol references, plus the bundle manifests a rerun stages from."""
    _, d, root = _resolve_any(protocol)
    rows = {"ok": [], "mismatch": [], "missing": [], "restricted_present_ok": [], "restricted_missing": [], "remote_record": [], "no_hash": []}
    for path, r in file_refs(d):
        f = expand(r["path"])
        ent = {"at": path, "path": r["path"], "storage_class": r["storage_class"], "role": r.get("role")}
        sc = r["storage_class"]
        if sc == "remote_record":
            rows["remote_record"].append(ent); continue
        if not r.get("sha256"):
            rows["no_hash"].append(ent); continue
        if not f.is_file():
            rows["restricted_missing" if sc == "restricted" else "missing"].append(ent); continue
        ok = sha256_file(f) == r["sha256"]
        if sc == "restricted":
            (rows["restricted_present_ok"] if ok else rows["mismatch"]).append(ent)
        else:
            (rows["ok"] if ok else rows["mismatch"]).append({**ent, **({} if ok else {"recorded": r["sha256"][:16], "file": sha256_file(f)[:16]})})
    bundles = []
    for m in ((d.get("reproduce") or {}).get("stage") or {}).get("manifests", []):
        mp = repo_root() / m
        mm = json.loads(mp.read_text())
        bad = [f["path"] for f in mm["files"] if not (mp.parent / f["path"]).is_file() or sha256_file(mp.parent / f["path"]) != f["sha256"]]
        bundles.append({"manifest": m, "files": len(mm["files"]), "failing": bad, "ok": not bad})
    lp = localpaths()
    camp = [lp.setting("runs_root").resolve(), lp.setting("restricted_dir").resolve()]

    def _campaign_or_private(path: str) -> bool:
        if str(path).startswith(lp.RECORD_CAMPAIGN_PREFIXES):
            return True
        q = expand(path).resolve()
        return any(q == c or c in q.parents for c in camp)
    needed = [e for e in rows["missing"] + rows["mismatch"] if not _campaign_or_private(e["path"])]
    if not detail:
        rows["ok"] = f"{len(rows['ok'])} files: sha256 matches (detail=true lists them)"
    return {"protocol": f"{d['id']}@{d['version']}", "counts": {k: (len(v) if isinstance(v, list) else int(v.split()[0])) for k, v in rows.items()}, **rows,
            "bundle_manifests": bundles,
            "rerun_ready": all(b["ok"] for b in bundles) if bundles else None,
            "note": ("A rerun stages only from the bundle manifests (code + evidence in the repo). Missing campaign files "
                     "(campaign directories) or restricted files (restricted material) do not block it; they are needed only to rebuild "
                     "the bundles from the sources. Restricted files are hashed, never read out."),
            "missing_outside_campaign_and_private": needed}


# ================================================================== reproduce items
def default_python(d: dict) -> str | None:
    for e in d.get("environment", []):
        if e.get("kind") == "venv" and e.get("path"):
            p = Path(os.path.expanduser(e["path"])) / "bin" / "python"
            if p.exists():
                return str(p)
    fp = localpaths().setting("fit_python")          # ORCHID_FIT_PYTHON or local/config.json (a clean clone elsewhere)
    return str(fp) if fp and Path(fp).exists() else None


def _measured_wall(d: dict) -> dict:
    out = {}
    for rep in sorted((repo_root() / "protocols" / "reproduce").glob("*/run_report.json")):
        try:
            r = json.loads(rep.read_text())
        except json.JSONDecodeError:
            continue
        if r.get("specific_protocol", "").split("@")[0] == d["id"]:
            for it in r.get("items", []):
                if it.get("wall_s") is not None:
                    out[it["id"]] = {"wall_s": it["wall_s"], "host": r.get("host"), "report": str(rep.relative_to(repo_root()))}
    return out


def repro_items(d: dict) -> list[dict]:
    if d.get("type") != "specific_protocol" or not d.get("reproduce"):
        return []
    spec_path = find_protocol(f"{d['id']}@{d['version']}")[0]
    rp = d["reproduce"]
    adir = assessment_dir(d)
    items: list[dict] = [{
        "id": "stage", "step": "stage", "kind": "deterministic", "source": "orchid_reproduce.py --stage-only (reproduce.stage of the specific protocol)",
        "command": f"python3 {tools_dir() / 'orchid_reproduce.py'} {spec_path} --root {{ROOT}} --stage-only",
        "compute": {"class": "CPU", "estimate_s": 5, "long": False}, "expect": [], "internal": "stage",
        "outputs": sorted(set(rp.get("stage", {}).get("copy", {}).values())),
    }, {
        "id": "environment_check", "step": "verify_build", "kind": "deterministic", "source": "reproduce.environment_check",
        "command": f"{{PY}} -I -c {shlex.quote(rp.get('environment_check', {}).get('code', ''))}",
        "expected_stdout": rp.get("environment_check", {}).get("expected"),
        "compute": {"class": "CPU", "estimate_s": 5, "long": False}, "expect": [], "internal": "env",
    }]
    spec_ids = {it["id"] for it in rp.get("plan", [])}   # an item the specific protocol declares wins over a binding
    man_p = adir / "evidence" / "MANIFEST.json"
    if man_p.is_file() and "evaluate_states" not in spec_ids:
        man = {f["path"]: f["sha256"] for f in json.loads(man_p.read_text())["files"]}
        art = [p for p in man if p.startswith("artifact/") and p.endswith(".tdb")]
        if art and "states.json" in man and "states_evaluated.json" in man:
            tdb = Path(art[0]).name
            items.append({
                "id": "evaluate_states", "step": "evaluate_states", "kind": "deterministic",
                "source": ("sage_mcp binding of the general step evaluate_states to the frozen bundle (the specific protocol's "
                           "reproduce.plan has no deterministic items). evaluate_states.py writes its two path arguments into the "
                           "output, so it runs in evaluate/ with bare file names, as the bundle copy was made (SCHEMA_GAPS G1)"),
                "copy": {f"assessments/{d['id']}/evidence/{art[0]}": f"evaluate/{tdb}", f"assessments/{d['id']}/evidence/states.json": "evaluate/states.json"},
                "copy_sha256": {f"evaluate/{tdb}": man[art[0]], "evaluate/states.json": man["states.json"]},
                "cwd": "evaluate", "command": f"{{PY}} -I {tools_dir() / 'evaluate_states.py'} {tdb} states.json states_evaluated.json --nproc {{NPROC}}",
                "compute": {"class": "CPU", "estimate_s": 15, "long": False, "measured": "11 s on a Mac Studio (arm64, macOS; 647 states, 4 workers)"},
                "expect": [{"rule": "byte", "path": "evaluate/states_evaluated.json", "sha256": man["states_evaluated.json"]}],
                "needs": "an interpreter with pycalphad 0.11.3.dev35+g9a6939dd2 (the fit interpreter)",
            })
    rel_dir = adir / "release"
    rels = sorted(rel_dir.glob("*.tdb")) if rel_dir.is_dir() else []
    snap = next((c for c in d.get("code", []) if c.get("id") == "snapshot"), {})
    if rels and "tdb_header" not in spec_ids:
        ref = rels[0]
        m = re.search(r"^\$ orchid release:\s+(.*)$", ref.read_text(errors="replace"), flags=re.M)
        release = m.group(1).strip() if m else "unreleased"
        art_src = expand(d["artifact"]["file"]["path"])
        items.append({
            "id": "tdb_header", "step": "tdb_header", "kind": "deterministic",
            "source": ("sage_mcp binding of the general step tdb_header. The --release value is not recorded in the specific "
                       "protocol; it is read from the reference header (SCHEMA_GAPS G2). tdb_header.py reads the pick from "
                       "artifact.file.path (a campaign path), not from the bundle copy"),
            "command": (f"python3 {tools_dir() / 'tdb_header.py'} {spec_path} release/{ref.name} --code-commit {snap.get('commit', 'unknown')} "
                        f"--release {shlex.quote(release)}"),
            "compute": {"class": "CPU", "estimate_s": 1, "long": False},
            "expect": [{"rule": "byte", "path": f"release/{ref.name}", "sha256": sha256_file(ref), "reference": str(ref.relative_to(repo_root()))}],
            "requires": [{"path": d["artifact"]["file"]["path"], "exists": art_src.is_file()}],
            "mkdirs": ["release"],
        })
    walls = _measured_wall(d)
    for it in rp.get("plan", []):
        w = walls.get(it["id"])
        cp = it.get("copy") or {}
        items.append({
            "id": it["id"], "step": it["step"], "kind": it["kind"], "source": "reproduce.plan of the specific protocol",
            "command": it.get("command"), "env": it.get("env") or {}, "note": it.get("note"), "expect": it.get("expect", []),
            "copy": {src: c["to"] for src, c in cp.items()}, "copy_sha256": {c["to"]: c["sha256"] for c in cp.values()},
            "cwd": it.get("cwd"), "expected": it.get("expected"),
            "mkdirs": sorted({str(Path(it["cwd"]))} if it.get("cwd") else set()),
            # every fit is long: a measured wall time is host-specific (Cr-Ni step 2: 151 s on a DGX Spark, 378 s on the Mac Studio)
            "compute": {"class": "CPU", "workers": "{NPROC}", "estimate_s": w["wall_s"] if w else None, "measured_on": w,
                        "long": it["kind"] == "numerical" or (w is None and it["kind"] != "deterministic") or (w is not None and w["wall_s"] > LONG_S)},
            "tolerances": [e for e in it.get("expect", []) if e["rule"] != "byte"],
        })
    for it in items:
        it["outputs"] = it.get("outputs") or [e["path"] for e in it["expect"]]
    return items


def _default_pfp_pin() -> str:
    """The full-checkout pin list of 6 Nov, named after the DGX Spark node whose copy it lists (machine label spark1; the
    one file *_phaseforgeplus_files.sha256 when the label is not configured)."""
    rel = f"protocols/environment/pins/{localpaths().host('spark1')}_phaseforgeplus_files.sha256"
    if not (repo_root() / rel).is_file():
        c = sorted((repo_root() / "protocols/environment/pins").glob("*_phaseforgeplus_files.sha256"))
        if len(c) == 1:
            return str(c[0].relative_to(repo_root()))
    return rel


def _pfp_default() -> str:
    q = localpaths().setting("phaseforgeplus_src")
    return str(q) if q else "<PhaseForgePlus src: set PHASEFORGEPLUS_SRC or phaseforgeplus_src in local/config.json>"


def pfp_pin(d: dict | None) -> Path:
    """The PhaseForge+ pin list a protocol declares (file id `source_pin` of its `phaseforgeplus` code entry); a protocol that
    declares none keeps the full-checkout list of 6 Nov (_default_pfp_pin). Same rule as protocols/tools/orchid_reproduce.py."""
    for c in (d or {}).get("code", []) or []:
        if c.get("id") != "phaseforgeplus":
            continue
        for f in c.get("files", []) or []:
            if f.get("id") == "source_pin":
                q = Path(os.path.expanduser(f["path"]))
                q = q if q.is_absolute() else repo_root() / q
                if not q.is_file() or sha256_file(q) != f["sha256"]:
                    raise SageError(f"PhaseForge+ pin file {f['path']} missing or its sha256 differs from the protocol")
                return q
    return repo_root() / _default_pfp_pin()


def pfp_mismatch(pfp: str, d: dict | None = None) -> list[str]:
    """Files of the PhaseForge+ source that differ from the pinned list (empty = matches). The pins name files relative to
    the repository root, i.e. the parent of the `src` directory given as pfp; the list is the protocol's own (pfp_pin)."""
    pin = pfp_pin(d)
    if not pin.is_file():
        return ["pin file missing"]
    root = Path(os.path.expanduser(pfp)).resolve().parent
    bad = []
    for line in pin.read_text().splitlines():
        if "  " not in line:
            continue
        h, rel_ = line.split("  ", 1)
        f = root / rel_
        if not f.is_file() or sha256_file(f) != h:
            bad.append(rel_)
    return bad


def _bind(cmd: str, root: Path, py: str, nproc: int, pfp: str) -> str:
    return (cmd.replace("{ROOT}", str(root)).replace("{PY}", py).replace("{NPROC}", str(nproc)).replace("{PFP}", pfp)
            .replace("{REPO}", str(repo_root())))


def plan_reproduction(protocol: str, run_root: str | None = None, python: str | None = None, pfp: str | None = None, nproc: int = 4) -> dict:
    p, d = find_protocol(protocol)
    if d.get("type") != "specific_protocol":
        raise SageError(f"{protocol} is a {d.get('type')}; plan_reproduction needs a specific protocol (or use next_step for a fresh assessment)")
    py = python or default_python(d) or "<interpreter matching the lock>"
    pfp = pfp or _pfp_default()
    root = Path(run_root) if run_root else Path("<run_root>")
    items = []
    for it in repro_items(d):
        e = {k: v for k, v in it.items() if k not in ("internal",)}
        e["command"] = _bind(it["command"] or "", root, py, nproc, pfp)
        e["env"] = {k: _bind(str(v), root, py, nproc, pfp) for k, v in (it.get("env") or {}).items()}
        e["needs_allow_long"] = bool(it["compute"].get("long"))
        e["compute"] = {k: (nproc if v == "{NPROC}" else v) for k, v in it["compute"].items()}
        items.append(e)
    jud = [{"step": sid, "recorded_decision": recorded_decision(d, sid)} for sid, ent in step_table(d).items()
           if ent["step"]["kind"] == "judgement" and any(r.get("step") in [s.split(".")[0] for s in ent["step"].get("supply", [])] for r in d.get("run_sequence", []))]
    return {"protocol": f"{d['id']}@{d['version']}", "spec": str(p.relative_to(repo_root())), "run_root": str(root),
            "python": py, "pfp": pfp, "nproc": nproc, "items": items, "order": [i["id"] for i in items],
            "judgement_steps_not_executed": jud,
            "acceptance_target": d.get("acceptance_target"), "not_reproducible": d["reproduce"].get("not_reproducible"),
            "rules": ["run_root must be fresh (absent or empty) at stage, outside the repo, the campaign directories and the restricted material (local config)",
                      f"items with an estimate above {int(LONG_S)} s, or without a measured estimate, need allow_long=true",
                      "judgement steps are never executed: their recorded decisions are returned"],
            "nothing_was_run": True}


def _write_item_card(root: Path, d: dict, it: dict, rec: dict, py: str, outputs: list[Path], inputs: list[Path],
                     pids: list[int] | None = None, extra_notes: list[str] | None = None) -> Path:
    gen = d["instantiates"][0]["protocol"]
    snap = next((c.get("commit") for c in d.get("code", []) if c.get("id") == "snapshot"), None)
    seeds = None
    if "fit_step.py" in (it.get("command") or "") or "fit.py" in (it.get("command") or ""):
        seeds = {"note": "seeds are fixed by the fit scripts (numpy default_rng(1000 + k) per start k; general parameter starts_per_step)"}
    return runner.write_run_card(root, f"{d['id']}-{it['id']}", f"{d['id']}@{d['version']}", gen, it["step"], rec, py,
                                 inputs, outputs, seeds=seeds, code_commit=snap,
                                 notes=[f"reproduce item {it['id']} ({it['source']})"] + (extra_notes or []), pids=pids)


def _job_items(r: Path) -> list[str]:
    j = r / "jobs"
    if not j.is_dir():
        return []
    return sorted(p.name[: -len(".json")] for p in j.glob("*.json")
                  if not p.name.endswith((".started.json", ".done.json", ".recorded.json")))


def _running_jobs(r: Path) -> list[str]:
    return [i for i in _job_items(r) if runner.job_state(r, i)["state"] == "running"]


def _move_job_aside(r: Path, item: str) -> str | None:
    """Move the files of an earlier job of this item to jobs/superseded/<item>-<stamp>/ (moved, never deleted)."""
    files = [p for p in runner.job_files(r, item).values() if p.exists()]
    if not files:
        return None
    dst = r / "jobs" / "superseded" / f"{item}-{runner.now().replace(':', '')}"
    dst.mkdir(parents=True, exist_ok=True)
    for p in files:
        p.rename(dst / p.name)
    return str(dst)


def run_step(protocol: str, step_id: str, run_root: str, confirm: bool = False, allow_long: bool = False,
             python: str | None = None, pfp: str | None = None, nproc: int = 4, backend: str = "local",
             detach: bool | None = None) -> dict:
    from . import fresh, state  # noqa: PLC0415

    if protocol in state.registry() or (Path(os.path.expanduser(protocol)) / "sage_state.json").is_file():
        if detach:
            raise SageError("detached runs (start_step / step_status) are implemented for reproduce items only; fresh-assessment steps run synchronously")
        return fresh.run_fresh_step(protocol, step_id, confirm=confirm, allow_long=allow_long, python=python, nproc=nproc, backend=backend,
                                    run_root=run_root)
    p, d = find_protocol(protocol)
    items = {it["id"]: it for it in repro_items(d)}
    tab = step_table(d)
    if step_id not in items:
        if step_id in tab and tab[step_id]["step"]["kind"] == "judgement":
            return {"executed": False, "reason": "judgement steps are never executed; this is the recorded decision",
                    "recorded_decision": recorded_decision(d, step_id)}
        if step_id in tab:
            return {"executed": False, "reason": (f"step {step_id} has no executable item in this specific protocol's reproduce plan; "
                                                  f"items: {sorted(items)}"), "step": get_step(protocol, step_id)}
        raise SageError(f"unknown step {step_id!r}; reproduce items: {sorted(items)}")
    it = items[step_id]
    be = backends.get(backend)
    if be["kind"] != "local":
        raise SageError("reproduce items run on the local backend only (CPU); remote backends receive job specs for GPU steps of fresh assessments")
    if it["compute"].get("long") and not allow_long:
        est = it["compute"].get("estimate_s")
        why = "a numerical fit (always long: wall time depends on the host)" if it["kind"] == "numerical" else f"estimate {est if est is not None else 'unknown'} s > {int(LONG_S)} s"
        return {"executed": False, "refused": True, "reason": f"item {step_id} is long ({why}; measured {est} s on {(it['compute'].get('measured_on') or {}).get('host', 'no host')}): pass allow_long=true to run it",
                "command": _bind(it["command"] or "", Path(run_root), python or default_python(d) or "<python>", nproc, pfp or _pfp_default()),
                "expect": it["expect"]}
    py = python or default_python(d)
    pfp = pfp or _pfp_default()
    if not confirm:
        return {"executed": False, "dry_run": True, "reason": "confirm=true is required to execute", "item": it,
                "command": _bind(it["command"] or "", Path(run_root), py or "<python>", nproc, pfp)}
    if it.get("internal") == "stage":
        r = safety.create_fresh_root(run_root, "reproduce", f"{d['id']}@{d['version']}")
        cmd = [sys.executable, str(tools_dir() / "orchid_reproduce.py"), str(p), "--root", str(r), "--stage-only"]
        started = runner.now()
        res = subprocess.run(cmd, capture_output=True, text=True)  # the root must be empty here; the log is written after
        if res.returncode != 0:
            raise SageError(f"staging failed: {res.stdout[-500:]} {res.stderr[-500:]}")
        safety.write_marker(r, "reproduce", f"{d['id']}@{d['version']}")
        (r / "logs").mkdir(exist_ok=True)
        (r / "logs" / "stage.log").write_text(res.stdout + res.stderr)
        rec = {"command": " ".join(shlex.quote(c) for c in cmd), "returncode": 0, "started": started, "finished": runner.now(),
               "wall_s": None, "log": str(r / "logs" / "stage.log")}
        card = _write_item_card(r, d, it, rec, sys.executable, [], [])
        return {"executed": True, "item": "stage", "run_root": str(r), "stdout": res.stdout.strip()[-400:], "run_card": str(card)}
    r, marker = safety.require_marked_root(run_root)
    if marker.get("protocol_or_assessment") != f"{d['id']}@{d['version']}":
        raise SageError(f"refused: run root {r} was staged for {marker.get('protocol_or_assessment')}, not {d['id']}@{d['version']}")
    if not py:
        raise SageError("no interpreter: pass python=<path to an interpreter matching the lock>")
    if it.get("internal") == "env":
        res = subprocess.run([py, "-I", "-c", d["reproduce"]["environment_check"]["code"]], capture_output=True, text=True)
        got = res.stdout.strip()
        (r / "logs").mkdir(exist_ok=True)
        (r / "logs" / "environment_check.log").write_text(res.stdout + res.stderr)
        ok = got == it["expected_stdout"]
        rec = {"command": f"{py} -I -c <environment_check.code>", "returncode": 0 if ok else 1, "started": runner.now(), "finished": runner.now(),
               "wall_s": None, "log": str(r / "logs" / "environment_check.log")}
        card = _write_item_card(r, d, it, rec, py, [], [])
        return {"executed": True, "item": "environment_check", "expected": it["expected_stdout"], "got": got, "pass": ok, "run_card": str(card)}
    for req in it.get("requires", []):
        if not req["exists"]:
            raise SageError(f"item {step_id} needs {req['path']}, which is not on this host")
    detach = bool(it["compute"].get("long")) if detach is None else bool(detach)
    own = runner.job_state(r, step_id)
    if own["state"] == "running":
        return {"executed": False, "refused": True, "status": "running",
                "reason": f"item {step_id} is already running (wrapper pid {own['job'].get('wrapper_pid')}); call step_status, never start it twice",
                "next": f"step_status({protocol!r}, {step_id!r}, {str(r)!r}, wait_s={int(runner.MAX_WAIT_S)})"}
    busy = [i for i in _running_jobs(r) if i != step_id]
    if busy:
        return {"executed": False, "refused": True, "status": "busy",
                "reason": f"item(s) {busy} still running in this run root; items run one at a time, in plan order",
                "next": f"step_status({protocol!r}, {busy[0]!r}, {str(r)!r}, wait_s={int(runner.MAX_WAIT_S)})"}
    moved = _move_job_aside(r, step_id)
    for mk in it.get("mkdirs", []):
        (r / mk).mkdir(parents=True, exist_ok=True)
    inputs = []
    for src, dst in (it.get("copy") or {}).items():
        dp = r / dst
        dp.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(repo_root() / src, dp)
        if sha256_file(dp) != it["copy_sha256"][dst]:
            raise SageError(f"hash mismatch while copying {src}")
        inputs.append(dp)
    pin_note = None
    if "{PFP}" in (it["command"] or "") or any("{PFP}" in str(v) for v in (it.get("env") or {}).values()):
        bad = pfp_mismatch(pfp, d)
        if bad:  # a note, never a failure (PI 6 Nov 2026: "this is too strict"); the predictions decide
            pin_note = f"PhaseForge+ source at {pfp} differs from {pfp_pin(d).relative_to(repo_root())} in {len(bad)} file(s): {bad[:5]} (note, not a failure)"
    cmd = _bind(it["command"], r, py, nproc, pfp)
    env = {k: _bind(str(v), r, py, nproc, pfp) for k, v in (it.get("env") or {}).items()}
    cwd = r / it["cwd"] if it.get("cwd") else r
    log = r / "reproduce_logs" / f"{step_id}.log"
    if detach:
        job = runner.start_detached(cmd, r, cwd, log, step_id, env, meta={
            "protocol": f"{d['id']}@{d['version']}", "python": py, "inputs": [str(p) for p in inputs], "pin_note": pin_note,
            **({"superseded_job": moved} if moved else {})})
        return {"executed": True, "detached": True, "status": "running", "item": step_id, "wrapper_pid": job.get("wrapper_pid"),
                "pid": (job.get("started") or {}).get("pid"), "job_file": job["job_file"], "log": str(log), "command": cmd,
                "estimate_s": it["compute"].get("estimate_s"),
                "next": (f"step_status({protocol!r}, {step_id!r}, {str(r)!r}, wait_s={int(runner.MAX_WAIT_S)}) until status is "
                         "'finished'; it then writes the run card exactly as a synchronous run would. Each call returns within "
                         f"{int(runner.MAX_WAIT_S)} s; the item keeps running between calls and if this session ends"),
                **({"note": pin_note} if pin_note else {})}
    rec = runner.run_command(cmd, r, cwd, log, env)
    outs = [r / e["path"] for e in it["expect"]]
    card = _write_item_card(r, d, it, rec, py, outs, inputs)
    return {"executed": True, "item": step_id, "returncode": rec["returncode"], "wall_s": rec["wall_s"], "log": rec["log"],
            "log_tail": rec["log_tail"], "outputs": [{"path": str(o.relative_to(r)), "exists": o.is_file()} for o in outs],
            "run_card": str(card), "next": "compare_outputs(protocol, run_root)", **({"note": pin_note} if pin_note else {})}


def start_step(protocol: str, step_id: str, run_root: str, confirm: bool = False, allow_long: bool = False,
               python: str | None = None, pfp: str | None = None, nproc: int = 4) -> dict:
    """run_step with detach=True: the item starts in its own session and the call returns at once."""
    return run_step(protocol, step_id, run_root, confirm=confirm, allow_long=allow_long, python=python, pfp=pfp, nproc=nproc, detach=True)


def _finalize_job(r: Path, d: dict, it: dict, st: dict) -> dict:
    """Write the run card of a finished detached job (once) and return the result a synchronous run_step returns."""
    if st.get("recorded"):
        return st["recorded"]
    job, started, done = st["job"], st["started"] or {}, st["done"]
    log = Path(job["log"])
    rec = {"command": job["command"], "cwd": job["cwd"], "returncode": done["returncode"],
           "started": started.get("started") or job["launched"], "finished": done["finished"], "wall_s": done["wall_s"],
           "log": str(log), "log_tail": runner.tail(log)}
    outs = [r / e["path"] for e in it["expect"]]
    py = job.get("python") or sys.executable
    pids = [x for x in (job.get("wrapper_pid"), started.get("pid")) if x]
    card = _write_item_card(r, d, it, rec, py, outs, [Path(p) for p in job.get("inputs", [])], pids=pids,
                            extra_notes=["run detached by sage_mcp (start_step / step_status); pids = [job wrapper, command shell]"])
    res = {"executed": True, "item": it["id"], "returncode": rec["returncode"], "wall_s": rec["wall_s"], "log": rec["log"],
           "log_tail": rec["log_tail"], "outputs": [{"path": str(o.relative_to(r)), "exists": o.is_file()} for o in outs],
           "run_card": str(card), "detached": True, "next": "compare_outputs(protocol, run_root)",
           **({"note": job["pin_note"]} if job.get("pin_note") else {})}
    runner.job_files(r, it["id"])["recorded"].write_text(json.dumps({**res, "recorded": runner.now()}, indent=1))
    return res


def step_status(protocol: str, run_root: str, step_id: str | None = None, wait_s: float = 0) -> dict:
    """Status of a detached reproduce item; blocks up to min(wait_s, MAX_WAIT_S) s while it runs. When the item has
    finished, writes its run card (once) and returns the synchronous run_step result. Without step_id: every job."""
    p, d = find_protocol(protocol)
    r, marker = safety.require_marked_root(run_root)
    if marker.get("protocol_or_assessment") != f"{d['id']}@{d['version']}":
        raise SageError(f"refused: run root {r} was staged for {marker.get('protocol_or_assessment')}, not {d['id']}@{d['version']}")
    items = {it["id"]: it for it in repro_items(d)}
    if step_id is None:
        jobs = []
        for i in _job_items(r):
            st = runner.job_state(r, i)
            if st["state"] == "finished" and i in items:
                _finalize_job(r, d, items[i], st)
                st = runner.job_state(r, i)
            jobs.append({"item": i, "status": st["state"], "run_card_written": bool(st.get("recorded")),
                         "returncode": (st.get("done") or {}).get("returncode")})
        return {"run_root": str(r), "jobs": jobs, "running": [j["item"] for j in jobs if j["status"] == "running"]}
    if step_id not in items:
        raise SageError(f"unknown reproduce item {step_id!r}; items: {sorted(items)}")
    st = runner.wait_job(r, step_id, wait_s)
    card = r / "run_cards" / f"{d['id']}-{step_id}.json"
    if st["state"] == "none":
        if card.is_file():
            return {"status": "finished", "item": step_id, "detached": False, "run_card": str(card),
                    "note": "ran synchronously (run_step without detach); no job record"}
        return {"status": "not started", "item": step_id, "next": f"start_step({protocol!r}, {step_id!r}, {str(r)!r}, confirm=true, allow_long=true)"}
    job = st["job"]
    if st["state"] == "running":
        t0 = (st.get("started") or {}).get("started") or job["launched"]
        try:
            elapsed = round(time.time() - time.mktime(time.strptime(t0, "%Y-%m-%dT%H:%M:%S%z")), 0)
        except ValueError:
            elapsed = None
        return {"status": "running", "item": step_id, "wrapper_pid": job.get("wrapper_pid"), "pid": (st.get("started") or {}).get("pid"),
                "started": t0, "elapsed_s": elapsed, "estimate_s": items[step_id]["compute"].get("estimate_s"), "log": job["log"],
                "log_tail": runner.tail(Path(job["log"]), 15),
                "next": f"step_status({protocol!r}, {step_id!r}, {str(r)!r}, wait_s={int(runner.MAX_WAIT_S)})"}
    if st["state"] == "lost":
        return {"status": "lost", "item": step_id, "wrapper_pid": job.get("wrapper_pid"), "log": job["log"],
                "log_tail": runner.tail(Path(job["log"]), 15),
                "reason": ("the job wrapper ended without a done record (killed, or the host restarted); no run card was written. "
                           "Starting the item again moves this job record aside (jobs/superseded/)")}
    return {"status": "finished", **_finalize_job(r, d, items[step_id], st)}


def compare_outputs(protocol: str, run_root: str, python: str | None = None) -> dict:
    from . import fresh, state  # noqa: PLC0415

    if protocol in state.registry():
        return fresh.compare_fresh(protocol)
    p, d = find_protocol(protocol)
    r, _ = safety.require_marked_root(run_root)
    items = repro_items(d)
    ran = {json.loads(c.read_text())["run_id"].split(f"{d['id']}-", 1)[-1] for c in (r / "run_cards").glob("*.json")}
    checks = []
    plan_ids = []
    for it in items:
        if it["id"] not in ran:
            js = runner.job_state(r, it["id"])["state"]
            checks.append({"item": it["id"], "status": {"running": "running (detached; step_status)", "finished": "finished, run card not yet written (call step_status)",
                                                         "lost": "lost (detached job ended without a done record)"}.get(js, "not run")}); continue
        if it.get("source", "").startswith("reproduce.plan"):
            plan_ids.append(it["id"]); continue
        for e in it["expect"]:
            f = r / e["path"]
            got = sha256_file(f) if f.is_file() else None
            checks.append({"item": it["id"], "rule": "byte", "path": e["path"], "reference": e["sha256"], "rerun": got,
                           "pass": got == e["sha256"], "note": None if f.is_file() else "not produced"})
        if not it["expect"]:
            checks.append({"item": it["id"], "status": "ran (no output to compare)"})
    plan_report = None
    if plan_ids:
        py = python or default_python(d) or sys.executable
        (r / "comparison").mkdir(exist_ok=True)
        rep = r / "comparison" / "plan_compare.json"
        res = subprocess.run([sys.executable, str(tools_dir() / "orchid_reproduce.py"), str(p), "--root", str(r), "--compare-only",
                              "--only", ",".join(plan_ids), "--python", py, "--report", str(rep)], capture_output=True, text=True)
        if rep.is_file():
            plan_report = json.loads(rep.read_text())
            for itr in plan_report.get("items", []):
                for c in itr.get("checks", []):
                    checks.append({"item": itr["id"], "rule": c.get("check"), "path": c.get("path"), "pass": c.get("pass"),
                                   **{k: c.get(k) for k in ("reference", "rerun", "diff", "abs_tol", "worst_diff_over_tol", "byte_identical", "note") if k in c}})
        else:
            checks.append({"item": ",".join(plan_ids), "pass": False, "note": f"orchid_reproduce.py --compare-only failed: {res.stderr[-400:]}"})
    compared = [c for c in checks if "pass" in c]
    report = {"protocol": f"{d['id']}@{d['version']}", "run_root": str(r), "created": runner.now(), "checks": checks,
              "pass": bool(compared) and all(c["pass"] for c in compared),
              "scope": "pass covers the compared checks only; items listed in not_run were not reproduced",
              "compared": len(compared), "not_run": [c["item"] for c in checks if c.get("status") == "not run"],
              "running_or_unrecorded": [c["item"] for c in checks if c.get("status", "").startswith(("running", "finished", "lost"))],
              "plan_compare_report": str(r / "comparison" / "plan_compare.json") if plan_report else None,
              "environment": (plan_report or {}).get("environment")}
    (r / "comparison").mkdir(exist_ok=True)
    (r / "comparison" / "comparison.json").write_text(json.dumps(report, indent=1))
    md = [f"# Comparison: {report['protocol']}", "", f"run root `{r}`, {report['created']}", "",
          "| item | rule | path | result |", "|---|---|---|---|"]
    for c in checks:
        md.append(f"| {c['item']} | {c.get('rule', '')} | {c.get('path', '')} | {('PASS' if c['pass'] else 'FAIL') if 'pass' in c else c.get('status')} |")
    md += ["", f"**Overall ({len(compared)} compared): {'PASS' if report['pass'] else 'FAIL'}**"]
    (r / "comparison" / "comparison.md").write_text("\n".join(md) + "\n")
    report["report"] = str(r / "comparison" / "comparison.json")
    return report
