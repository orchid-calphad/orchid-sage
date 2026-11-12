"""Fresh mode: a new assessment instantiated from the general protocol, run step by step, with documented changes.

Workspace (the run root of the assessment; created fresh, marked with .sage_run_root.json):
  protocol/<id>@<version>.json   every version of the specific protocol (JSON is a YAML subset; never overwritten
                                 by a modification: each documented change writes the next version)
  sage_state.json                step status (pending/done/stale/skipped/job_spec_written), decision requests,
                                 bindings, the event log
  PLAN.md                        the write_plan step (template protocols/templates/PLAN.template.md)
  evidence/                      the bundle (files/<group>, hinge/, states.json, MANIFEST.json) in the format of
                                 protocols/tools/build_evidence_bundle.py
  run_cards/, logs/, jobs/       native run cards, logs, GPU job specs
Steps executed on the protocol record results in the CURRENT version file (run_sequence, evidence_selection,
decisions that answer an open request). Changes to the method (modify_protocol, migrate) bump the version.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from . import backends, runner, safety, state
from .repo import (
    SageError, find_protocol, general_protocols, iter_steps, load_doc, localpaths, orchidproto, repo_root, schema_errors,
    sha256_file, tilde, tools_dir,
)

DEFAULT_GENERAL = "orchid-calphad-fit@2.0.0"
SYSTEM_RE = re.compile(r"^[A-Z][A-Z]?(-[A-Z][A-Z]?)+$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
GPU_ENVS = {"mlip_container"}
# steps the server carries out itself (no campaign script needed)
INTERNAL = {"write_plan", "build_datasets", "exclusions_every_state", "classify_certainty"}
GATHER_STEPS = ("build_datasets", "exclusions_every_state", "classify_certainty")
# protocol errors that are expected while an assessment is a draft in progress (reported as pending, not as errors)
DRAFT_PENDING = (
    ("$.artifact.file.sha256", "the artifact (final TDB) does not exist until final_pick"),
    ("$.run_sequence: fewer than 1 items", "no step has run yet"),
    ("$.evidence_selection.manifest.sha256", "the evidence bundle does not exist until gather_evidence"),
)


def today() -> str:
    return time.strftime("%Y-%m-%d")


# ------------------------------------------------------------------ state
def load_state(root: Path) -> dict:
    return json.loads((root / "sage_state.json").read_text())


def save_state(root: Path, st: dict) -> None:
    (root / "sage_state.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))


def event(st: dict, kind: str, **detail: Any) -> None:
    st["events"].append({"time": runner.now(), "kind": kind, **detail})


def current_spec(root: Path) -> tuple[Path, dict]:
    st = load_state(root)
    p = root / st["current_spec"]
    return p, load_doc(p)


def _write_spec(root: Path, spec: dict, st: dict, reason: str, new_version: bool) -> Path:
    p = root / "protocol" / f"{spec['id']}@{spec['version']}.json"
    if new_version and p.exists():
        raise SageError(f"version {spec['version']} already exists ({p}); versions are never overwritten")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(spec, indent=1, ensure_ascii=False))
    st["current_spec"] = str(p.relative_to(root))
    if new_version:
        st["versions"].append({"version": spec["version"], "path": str(p.relative_to(root)), "created": runner.now(), "reason": reason})
    st["versions"][-1]["sha256"] = sha256_file(p)
    return p


def _root_of(assessment: str) -> Path:
    r = state.resolve(assessment)
    if not (r / safety.MARKER).is_file():
        raise SageError(f"{r} is not a sage_mcp run root")
    return r


def validate_assessment(assessment: str) -> dict:
    root = _root_of(assessment)
    p, spec = current_spec(root)
    errs = schema_errors(spec)
    pending = []
    real = []
    for e in errs:
        hit = next((why for pat, why in DRAFT_PENDING if e.startswith(pat)), None)
        (pending.append({"error": e, "pending_because": hit}) if hit and spec.get("status") == "draft" else real.append(e))
    real += _check_order(spec)
    cards = []
    for c in sorted((root / "run_cards").glob("*.json")):
        ce = schema_errors(json.loads(c.read_text()))
        cards.append({"run_card": c.name, "ok": not ce, "errors": ce[:5]})
        real += [f"run_cards/{c.name}: {x}" for x in ce]
    return {"assessment": assessment, "protocol": tilde(p), "version": spec["version"], "ok": not real, "errors": real,
            "pending_for_draft": pending, "run_cards": cards,
            "validator": "orchidproto.SchemaValidator against protocols/schema/protocol.schema.json (validate.py reads only protocols/)"}


def _check_order(spec: dict) -> list[str]:
    """supply of the specific protocol's own (added) steps must name inputs, parameters or results of known steps."""
    errs = []
    gen = _general(spec)
    produced = {f"{s['id']}.{r['id']}" for _, s in iter_steps(gen) for r in s["result"]}
    params = set(gen.get("parameters", {})) | set(spec.get("parameters", {}) or {})
    inputs = {i["id"] for i in gen.get("inputs", [])} | {i["id"] for i in spec.get("inputs", [])}
    for _, s in iter_steps(spec):
        for x in s.get("supply", []):
            if x.startswith("input:") and x[6:] not in inputs:
                errs.append(f"added step {s['id']}: supply {x} is not a declared input")
            elif x.startswith("param:") and x[6:].split(".")[0] not in params:
                errs.append(f"added step {s['id']}: supply {x} is not a declared parameter")
            elif not x.startswith(("input:", "param:")) and x not in produced:
                errs.append(f"added step {s['id']}: supply {x} is not produced by an earlier step")
        produced |= {f"{s['id']}.{r['id']}" for r in s["result"]}
    return errs


def _general(spec: dict) -> dict:
    return find_protocol(spec["instantiates"][0]["protocol"])[1]


# ------------------------------------------------------------------ effective steps (general + documented changes)
def _overrides(spec: dict, prefix: str) -> dict:
    out = {}
    for o in spec.get("overrides", []):
        if o["parameter"].startswith(prefix):
            out[o["parameter"][len(prefix):]] = o["value"]
    return out


def effective_steps(spec: dict) -> list[dict]:
    """Ordered steps: the general protocol's, plus added steps (spec sections), with documented skips, reorders and
    tool changes applied (overrides 'step:<id>.skip', 'step:<id>.after', 'step:<id>.tool.command')."""
    gen = _general(spec)
    order: list[dict] = [{"section": sec["id"], "step": copy.deepcopy(s), "origin": f"{gen['id']}@{gen['version']}"} for sec, s in iter_steps(gen)]
    for sec, s in iter_steps(spec):
        order.append({"section": sec["id"], "step": copy.deepcopy(s), "origin": f"{spec['id']}@{spec['version']}"})
    ov = _overrides(spec, "step:")
    for key, val in ov.items():
        sid, _, field = key.partition(".")
        if field == "after":
            ent = next((e for e in order if e["step"]["id"] == sid), None)
            if ent:
                order.remove(ent)
                idx = next(i for i, e in enumerate(order) if e["step"]["id"] == val)
                order.insert(idx + 1, ent)
    for e in order:
        sid = e["step"]["id"]
        if ov.get(f"{sid}.skip"):
            e["skipped"] = True
        if f"{sid}.tool.command" in ov:
            e["step"].setdefault("tool", {})["command"] = ov[f"{sid}.tool.command"]
            e["command_overridden"] = True
    return order


def _params(spec: dict) -> dict:
    gen = _general(spec)
    p = {k: v.get("default") for k, v in gen.get("parameters", {}).items()}
    p.update({k: v.get("default") for k, v in (spec.get("parameters") or {}).items()})
    p.update(_overrides(spec, "param:"))
    return p


def _bindings(root: Path, spec: dict, st: dict, nproc: int = 4) -> dict:
    sys_ = spec["system"]
    b = {"campaign": str(root), "artifact": spec["id"], "EL": sys_.split("-")[1], "nproc": str(nproc), "version": spec["version"],
         "system": sys_}
    b.update({k: str(v) for k, v in st.get("bindings", {}).items() if isinstance(v, (str, int, float))})
    b.update({k: str(v) for k, v in _overrides(spec, "binding:").items()})
    if st.get("bindings", {}).get("final_tdb"):
        b.setdefault("final", Path(st["bindings"]["final_tdb"]).stem)
    return b


def bind_command(cmd: str | None, b: dict) -> tuple[str | None, list[str]]:
    if not cmd:
        return None, []
    out = cmd.replace("assessments/<artifact>/evidence/", "evidence/").replace("protocols/tools/", str(tools_dir()) + "/")
    unbound = []
    for name in sorted(set(re.findall(r"<([^<>]+)>", out))):
        if name in b:
            out = out.replace(f"<{name}>", b[name])
        else:
            unbound.append(name)
    return out, unbound


def compute_of(step: dict) -> dict:
    env = (step.get("tool") or {}).get("environment")
    if env in GPU_ENVS:
        return {"class": "GPU", "estimate": "2-11 h (general protocol compute.typical_wall)", "long": True}
    if step.get("kind") == "numerical":
        return {"class": "CPU", "estimate": "0.5-1.5 h per fit step; Laplace ~0.5 h (compute.typical_wall)", "long": True}
    if step.get("kind") == "judgement":
        return {"class": "human", "estimate": "a decision", "long": False}
    return {"class": "CPU", "estimate": "seconds to minutes", "long": False}


def _supply_owners(step: dict) -> list[str]:
    return sorted({s.split(".")[0] for s in step.get("supply", []) if not s.startswith(("input:", "param:"))})


def sequence(root: Path, nproc: int = 4) -> list[dict]:
    _, spec = current_spec(root)
    st = load_state(root)
    b = _bindings(root, spec, st, nproc)
    steps = effective_steps(spec)
    status = {e["step"]["id"]: ("skipped" if e.get("skipped") else st["steps"].get(e["step"]["id"], {}).get("status", "pending")) for e in steps}
    out = []
    for e in steps:
        s = e["step"]
        sid = s["id"]
        blockers = []
        for owner in _supply_owners(s):
            if status.get(owner) not in ("done", "skipped"):
                blockers.append(f"needs {owner} ({status.get(owner, 'unknown')})")
        for rq in st["decision_requests"]:
            if rq["status"] == "open" and sid in rq.get("blocks", []) and rq.get("step") != sid:
                blockers.append(f"open decision request {rq['id']}: {rq['question'][:100]}")
        cmd, unbound = bind_command((s.get("tool") or {}).get("command"), b)
        comp = compute_of(s)
        if status[sid] == "skipped":
            mode = "skipped"
        elif s["kind"] == "judgement":
            mode = "judgement"
        elif comp["class"] == "GPU":
            mode = "job_spec"
        elif sid in INTERNAL:
            mode = "internal"
        else:
            mode = "command"
        exe_problems = []
        if mode == "command":
            if not cmd:
                exe_problems.append("no exact command in the protocol")
            if unbound:
                exe_problems.append(f"unbound placeholders {unbound}: bind them with modify_protocol(change={{'type':'binding',...}})")
            for script in re.findall(r"(?<![\w/.~])((?:scripts|code)/[\w./-]+\.(?:py|sh))", cmd or ""):
                if not (root / script).is_file():
                    exe_problems.append(f"{script} is not in the run root: the fit sequence is campaign code (general protocol limitation 1); "
                                        f"copy and adapt the reference implementation ({(s.get('tool') or {}).get('code')}) and record it with modify_protocol")
            if "written by scripts/" in (cmd or ""):
                exe_problems.append("the protocol says this is written by another step's script (not a command)")
        out.append({"id": sid, "section": e["section"], "name": s["name"], "kind": s["kind"], "origin": e["origin"], "status": status[sid],
                    "mode": mode, "blockers": blockers, "command": cmd, "unbound": unbound, "compute": comp,
                    "executable": mode in ("internal", "command") and not exe_problems and not blockers and status[sid] in ("pending", "stale"),
                    "not_executable_because": exe_problems, "command_overridden": e.get("command_overridden", False),
                    "decided_by": s.get("decided_by"), "decision_rule": s.get("decision_rule"),
                    "inputs": s.get("supply", []), "outputs": [r["id"] for r in s["result"]]})
    return out


def next_step(assessment: str, nproc: int = 4) -> dict:
    root = _root_of(assessment)
    seq = sequence(root, nproc)
    todo = [x for x in seq if x["status"] not in ("done", "skipped")]
    st = load_state(root)
    open_rq = [r for r in st["decision_requests"] if r["status"] == "open"]
    counts = {}
    for x in seq:
        counts[x["status"]] = counts.get(x["status"], 0) + 1
    if not todo:
        return {"assessment": assessment, "done": True, "counts": counts, "next": "package(assessment)"}
    nxt = next((x for x in todo if not x["blockers"]), todo[0])
    what = {"judgement": "run_step creates a decision request (or returns the open one); a person answers it with record_decision",
            "job_spec": "run_step writes the GPU job spec for an executor; record the finished run with record_external_run",
            "internal": "run_step carries it out (server code)", "command": "run_step runs the bound command in the run root"}[nxt["mode"]]
    return {"assessment": assessment, "next": nxt, "how": what, "open_decision_requests": open_rq, "counts": counts,
            "sequence": [{k: x[k] for k in ("id", "kind", "status", "mode")} | {"blocked": bool(x["blockers"])} for x in seq]}


# ------------------------------------------------------------------ new assessment
def _copy_general_entries(gen: dict, key: str, ids: list[str]) -> list[dict]:
    return [copy.deepcopy(x) for x in gen.get(key, []) if x.get("id") in ids]


def new_assessment(system: str, assessment_id: str, run_root: str, phases: list[str] | None = None,
                   T_range: list[float] | None = None, general: str = DEFAULT_GENERAL, title: str | None = None) -> dict:
    system = system.upper().strip()
    if not SYSTEM_RE.match(system) or system.count("-") != 1:
        raise SageError(f"system must be a binary like 'AL-CU' (the general protocol is for binary systems), got {system!r}")
    els = system.split("-")
    if els != sorted(els):
        raise SageError(f"write the system in alphabetical order: {'-'.join(sorted(els))}")
    if not ID_RE.match(assessment_id):
        raise SageError("assessment_id must match ^[a-z0-9][a-z0-9._-]*$ (it becomes the protocol id)")
    if assessment_id in state.registry():
        raise SageError(f"assessment {assessment_id!r} already exists at {state.registry()[assessment_id]}")
    if T_range is not None and (len(T_range) != 2 or not T_range[0] < T_range[1]):
        raise SageError("T_range must be [T_min, T_max] in K with T_min < T_max")
    gpath, gen = find_protocol(general)
    if gen.get("type") != "general_protocol":
        raise SageError(f"{general} is not a general protocol")
    root = safety.create_fresh_root(run_root, "fresh", assessment_id)
    safety.write_marker(root, "fresh", assessment_id)
    for d in ("protocol", "evidence", "run_cards", "logs", "jobs", "tdb", "results", "steps"):
        (root / d).mkdir(exist_ok=True)
    gref = f"{gen['id']}@{gen['version']}"
    ver = "0.1.0"
    spec = {
        "type": "specific_protocol", "schema_version": runner.SCHEMA_VERSION, "id": assessment_id, "version": ver,
        "title": title or f"{system} CALPHAD assessment from the PhaseForge one-shot, liquid down ({gref})",
        "status": "draft", "status_note": "DRAFT created by sage_mcp new_assessment; open decisions are listed in sage_state.json decision_requests",
        "system": system,
        "purpose": f"Build a {system} TDB with {gref}: one-shot, liquidus, thermochemistry, solid state with exclusions, ambiguous structures, checks, ranking, Laplace UQ, package.",
        "licence": "CC-BY-4.0", "created": today(),
        "maintainers": [{"name": "Raymundo Arróyave", "role": "PI", "email": "rarroyave@tamu.edu"}, {"name": "sage_mcp", "role": "recorder"}],
        "instantiates": [{"protocol": gref, "file": {"path": tilde(gpath), "sha256": sha256_file(gpath), "storage_class": "local"}}],
        "artifact": {"kind": "tdb", "file": {"path": tilde(root / "tdb" / f"{assessment_id}.tdb"), "sha256": None, "storage_class": "local",
                                             "role": "final pick (pending: written at final_pick)"},
                     "produced_by": f"{assessment_id}@{ver}"},
        "inputs": [{"id": "orchid_evidence", "name": "ORCHID evidence (espei datasets of the system)", "kind": "orchid_evidence", "storage_class": "public",
                    "files": [], "note": "filled by gather_evidence"}]
                  + [copy.deepcopy(i) for i in gen.get("inputs", []) if i["id"] in ("unaries", "mlip_weights", "structures", "sigma_mlip")],
        "code": _copy_general_entries(gen, "code", ["espei_grad", "phaseforgeplus", "mlipentropy", "reference_oneshot_code", "reference_fit_code", "protocol_tools"]),
        "environment": _copy_general_entries(gen, "environment", ["fit_env", "mlip_container", "sqs_env", "stdlib_tools"]),
        "overrides": [],
        "evidence_selection": {"orchid": {"repository": "pending (gather_evidence)", "commit": "pending", "query": f"espei/<class>/{system}/*.json"},
                               "manifest": {"path": tilde(root / "evidence" / "MANIFEST.json"), "sha256": None, "storage_class": "local"},
                               "exclusions": [], "interpretations": [], "single_reader_flags": []},
        "run_sequence": [],
        "acceptance_target": {"text": "pending: stated in PLAN.md before ranking (R1-R3 thresholds and the accepted topology)",
                              "tolerances": copy.deepcopy(gen.get("tolerances", []))},
        "reproduce": {"command": f"python3 protocols/tools/orchid_reproduce.py <this protocol> --root <new dir> (after packaging)",
                      "byte_identical_expected": [], "not_reproducible": [], "independent_rerun": {"status": "pending", "reason": "not packaged yet"}},
        "decisions": [], "limitations": [], "open_questions": [],
    }
    st = {"assessment": assessment_id, "system": system, "created": runner.now(), "current_spec": "", "versions": [],
          "steps": {}, "decision_requests": [], "bindings": {}, "events": [], "evidence_gaps": []}
    if phases:
        st["bindings"]["phases"] = sorted({p.upper() for p in phases})
    if T_range:
        st["bindings"]["T_range"] = [float(T_range[0]), float(T_range[1])]
    _write_spec(root, spec, st, "created from " + gref, new_version=True)
    state.register(assessment_id, root)
    event(st, "created", general=gref, run_root=str(root))
    # open decisions (the server never decides them)
    _request(st, "read_established_practice", _step_of(gen, "read_established_practice")["text"],
             evidence=["docs/fit_protocol.md (Section 0.0b)"], blocks=["write_plan"])
    if not phases:
        _request(st, "model_phases", "Which phases and models enter the assessment (disordered unless evidence requires ordering; ask the PI before "
                 "adding phases or sublattices)? Answer with bindings={'phases': [...]}.", evidence=[], blocks=["write_plan", "exclusions_every_state"], step=None)
    if not T_range:
        _request(st, "t_range", "Which T-x domain (T_min, T_max in K) does the assessment cover? Answer with bindings={'T_range': [lo, hi]}.",
                 evidence=[], blocks=["write_plan"], step=None)
    _request(st, "unaries", "Which TDB supplies the SGTE unaries of every end-member (sha256 recorded)? Answer with bindings={'unaries_tdb': path}.",
             evidence=[], blocks=["build_oneshot_tdb"], step=None)
    _write_plan_draft(root, spec, st)
    save_state(root, st)
    return {"assessment": assessment_id, "run_root": str(root), "protocol": str(root / st["current_spec"]), "version": ver,
            "open_decision_requests": [r for r in st["decision_requests"] if r["status"] == "open"],
            "plan_draft": str(root / "PLAN.md"), "next": next_step(assessment_id)["next"], "validation": validate_assessment(assessment_id)}


def _step_of(gen: dict, sid: str) -> dict:
    return next(s for _, s in iter_steps(gen) if s["id"] == sid)


def _request(st: dict, key: str, question: str, evidence: list[str], blocks: list[str], step: str | None = "same") -> dict:
    rid = f"DR-{len(st['decision_requests']) + 1:03d}-{key.replace('_', '-')}"
    rq = {"id": rid, "key": key, "step": key if step == "same" else step, "question": question, "evidence": evidence, "blocks": blocks,
          "status": "open", "created": runner.now()}
    st["decision_requests"].append(rq)
    event(st, "decision_requested", request=rid)
    return rq


def _write_plan_draft(root: Path, spec: dict, st: dict) -> Path:
    tpl = (repo_root() / "protocols" / "templates" / "PLAN.template.md").read_text()
    b = st["bindings"]
    gen_ref = spec["instantiates"][0]["protocol"]
    t = tpl.replace("<System>", spec["system"]).replace("<date>", today()).replace("orchid-calphad-fit@<version>", gen_ref)
    open_rq = [r for r in st["decision_requests"] if r["status"] == "open"]
    extra = ["", "## Assessment (filled by sage_mcp; OPEN = decision request not yet answered)",
             f"- assessment id: {spec['id']}@{spec['version']}; run root {tilde(root)}",
             f"- phases: {b.get('phases', 'OPEN (model_phases)')}",
             f"- T range: {b.get('T_range', 'OPEN (t_range)')} K",
             f"- unaries: {b.get('unaries_tdb', 'OPEN (unaries)')}",
             "- open decision requests: " + (", ".join(r["id"] for r in open_rq) or "none")]
    dec = [f"- {d['date']} {d['who']}: {d['decision']} (why: {d['why']})" for d in spec.get("decisions", [])]
    if dec:
        extra += ["", "## Decisions recorded"] + dec
    p = root / "PLAN.md"
    p.write_text(t + "\n".join(extra) + "\n")
    return p


# ------------------------------------------------------------------ evidence
def _group(d: dict) -> str:
    out = str(d.get("output", ""))
    if out == "ZPF":
        return "liq" if "LIQUID" in d.get("phases", []) else "solid"
    return "thermo"


def _orchid_dir(orchid_data_dir: str | None) -> Path:
    p = Path(orchid_data_dir).expanduser() if orchid_data_dir else localpaths().setting("orchid_data_dir")
    if not (p / "espei").is_dir():
        raise SageError(f"no ORCHID data checkout with espei/ at {p} (set ORCHID_DATA_DIR)")
    return p


def _orchid_context(system: str, odir: Path) -> dict:
    """Best-effort summary from the ORCHID MCP tools (ids and counts only; no quotes copied)."""
    src = localpaths().setting("orchid_mcp_src")
    if src is None or not (src / "orchid_mcp").is_dir():
        return {"status": "pending", "reason": f"orchid_mcp not found at {tilde(src) if src else '(ORCHID_MCP_SRC / orchid_mcp_src not set)'}"}
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    try:
        from orchid_mcp.datasource import DataSource  # noqa: PLC0415
        from orchid_mcp.tools import Orchid  # noqa: PLC0415

        site = localpaths().setting("site_data_dir")
        if not (odir / "literature" / "index.json").is_file() or site is None or not site.is_dir():
            return {"status": "pending", "reason": "local ORCHID literature/site data not found (the server never goes online)"}
        o = Orchid(DataSource(odir), DataSource(site))  # local directories only: no network
        sysname = "-".join(e.capitalize() for e in system.split("-"))
        inv = o.get_invariant_reactions(system=sysname, source="literature", limit=200)
        recs = inv.get("literature", []) if isinstance(inv.get("literature"), list) else []
        pd = o.get_phase_diagram(system=sysname)
        return {"source": "orchid_mcp (local, offline)",
                "invariant_records": [{k: r.get(k) for k in ("id", "T_K", "phases", "reaction", "evidence_class")} for r in recs if isinstance(r, dict)],
                "literature_invariant_total": inv.get("literature_total"),
                "calculated_assessments": [{"tdb": a.get("tdb"), "tdb_sha256": a.get("tdb_sha256"), "phases": a.get("phases"), "T_range_K": a.get("T_range_K"),
                                            "evidence_class": a.get("evidence_class")} for a in pd.get("assessments", [])],
                "phases_in_calculated_assessments": sorted({ph for a in pd.get("assessments", []) for ph in (a.get("phases") or []) if isinstance(ph, str)}),
                "note": "context for the PLAN and the reference-assessment step; these records are not data files of the objective"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "pending", "reason": f"orchid_mcp query failed: {type(exc).__name__}: {str(exc)[:200]}"}


def _scan(odir: Path, system: str, classes: list[str]) -> tuple[list[tuple[str, Path, dict]], list[dict]]:
    found, gaps = [], []
    for cls in classes:
        d = odir / "espei" / cls / system
        if not d.is_dir():
            gaps.append({"what": f"no ORCHID espei/{cls}/{system} directory", "effect": "that evidence class contributes nothing"})
            continue
        for f in sorted(d.glob("*.json")):
            found.append((cls, f, json.loads(f.read_text())))
    return found, gaps


def _preview(root: Path, spec: dict, st: dict, classes: list[str], odir: Path) -> dict:
    """Without a decided phase set no exclusion can be written, so nothing is frozen: report what ORCHID holds as evidence
    for the phase decision."""
    found, gaps = _scan(odir, spec["system"], classes)
    rq = next((r for r in st["decision_requests"] if r["key"] == "model_phases" and r["status"] == "open"), None)
    files = [{"class": c, "file": tilde(f), "output": d.get("output"), "phases": d.get("phases"), "group": _group(d)} for c, f, d in found]
    ctx = _orchid_context(spec["system"], odir)
    if rq is not None:
        rq["evidence"] = sorted(set(rq["evidence"]) | {x["file"] for x in files})
        save_state(root, st)
    return {"assessment": st["assessment"], "preview": True, "frozen": False,
            "reason": "the phase set is not decided: excluded phases at every observed state cannot be written (fit_protocol item 8)",
            "decision_request": rq["id"] if rq else None, "files": files, "n_files": len(files),
            "phases_in_data": sorted({ph for x in files for ph in (x["phases"] or [])}),
            "phases_in_calculated_assessments": ctx.get("phases_in_calculated_assessments"), "gaps": gaps,
            "next": "record_decision(assessment, <model_phases request>, decision, who, why, bindings={'phases': [...]}), then gather_evidence again"}


def gather_evidence(assessment: str, evidence_classes: list[str] | None = None, orchid_data_dir: str | None = None) -> dict:
    root = _root_of(assessment)
    p, spec = current_spec(root)
    st = load_state(root)
    sel = _overrides(spec, "data:")
    classes = evidence_classes or sel.get("evidence_classes") or ["experimental", "invariants"]
    odir = _orchid_dir(orchid_data_dir)
    beb = __import__("sage_mcp.repo", fromlist=["evidence_bundle_module"]).evidence_bundle_module()
    system, el = spec["system"], spec["system"].split("-")[1]
    phases = st["bindings"].get("phases")
    if not phases:
        return _preview(root, spec, st, classes, odir)
    build = [st["steps"].get(s, {}).get("status") for s in GATHER_STEPS]
    ev = root / st["bindings"].get("evidence_dir", "evidence")
    if (ev / "MANIFEST.json").exists():
        if "stale" not in build:
            raise SageError(f"the evidence bundle {tilde(ev)} is current; a bundle is never overwritten (a documented data-selection "
                            "change or a new phase set marks it stale, and the next gather writes a new bundle directory)")
        n = 2
        while (root / f"evidence_v{n}").exists():
            n += 1
        ev = root / f"evidence_v{n}"
        st["bindings"]["evidence_dir"] = ev.name
    gaps, man, held, states, data_refs = [], [], [], [], []
    for cls in classes:
        d = odir / "espei" / cls / system
        if not d.is_dir():
            gaps.append({"what": f"no ORCHID espei/{cls}/{system} directory", "effect": "that evidence class contributes nothing"})
            continue
        for f in sorted(d.glob("*.json")):
            obj = json.loads(f.read_text())
            if beb.long_strings(obj):
                held.append({"original": tilde(f), "reason": "contains a source-text field longer than 500 characters"}); continue
            g = _group(obj)
            dst = ev / "files" / g / f"{cls}__{f.name}"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)
            txt = dst.read_text()
            man.append({"path": str(dst.relative_to(ev)), "sha256": sha256_file(dst), "original": tilde(f), "kind": "espei_dataset",
                        "orchid_ids": sorted(set(beb.ORC.findall(txt)))})
            data_refs.append({"path": tilde(dst), "sha256": sha256_file(dst), "storage_class": "public", "role": f"data file read by the objective ({g}; {cls})"})
            if obj.get("output") == "ZPF":
                for s in beb.states_from_zpf(obj, dst.name, g, el):
                    s["source"] = "zpf"
                    s["evidence_class"] = "assessed" if cls == "assessed" else s["evidence_class"]
                    states.append(s)
    if not man:
        raise SageError(f"no ORCHID espei data for {system} in classes {classes} at {odir}")
    # exclusions at every observed state: declared phases minus the measured assemblage (fit_protocol item 8). Tiers are
    # per EXCLUDED PHASE (certainty-tiers@2, PI 6 Nov 2026): states first, then one hinge cell per (state, tier) group, so
    # each penalized phase carries its own energy scale within the sidecar keys of espei/SCHEMA.md (penalize, sigma)
    cells = []
    tau = _params(spec).get("hull_tolerance_tau", 100)
    hstates = []
    if not phases:
        gaps.append({"what": "exclusions not built", "effect": "the phase set is not decided (decision request model_phases)", "blocks": "exclusions_every_state"})
    else:
        seen_ph = sorted({ph for s in states for ph in s["expected"]})
        undeclared = [ph for ph in seen_ph if ph not in phases]
        if undeclared:
            gaps.append({"what": f"observed phases not in the declared phase set: {undeclared}", "effect": "those states get no hinge cell (decision needed)"})
        for s in states:
            if s["x"] is None:
                gaps.append({"what": f"state without composition: {s['source_file']} row {s['row']}", "effect": "no exclusion cell"}); continue
            if any(ph not in phases for ph in s["expected"]):
                continue
            pen = [ph for ph in phases if ph not in s["expected"]]
            if pen:
                s["excluded"] = pen; hstates.append(s)
    # single source = only the datasets the plan designates, each with its reason (fit_protocol item 8, PI 7 Nov 2026);
    # a spec parameter single_source_datasets: [{match, reason}], none by default (no automatic rule)
    beb.classify(states, _params(spec).get("single_source_datasets") or [])
    if phases:
        for s in hstates:
            tl = {ph: xv for ph, xv in s.get("vertices", []) if xv is not None} if s["kind"] != "single_phase" else None
            by_tier = {}
            for e in s.get("exclusions", []):
                by_tier.setdefault(e["certainty_tier"], []).append(e)
            for tier, es in sorted(by_tier.items()):
                cells.append({"T": s["T_K"], "x": s["x"], "expected": s["expected"], **({"tie_line": tl} if tl else {}), "penalize": [e["phase"] for e in es],
                              "sigma": float(es[0]["energy_scale_J_per_mol_atom"]), "confidence": 1.0,
                              "orchid": {"dataset": s["source_file"].split("/", 1)[1], "index": s["row"], "reference": s.get("reference", "")[:200],
                                         "relation": "observed_state", "basis": "observed state: declared phase set minus the measured assemblage (fit_protocol item 8)",
                                         "observation_id": (s["orchid_ids"] or [None])[0], "certainty_tier": tier,
                                         "hull_tolerance_J_per_mol_atom": float(tau), "sigma_T_K": s["sigma_T_K"], "sigma_x": s["sigma_x"]}})
        hinge = {"system": system, "element": el, "margin_J_per_mol_atom": float(tau), "phases": phases,
                 "builder": "sage_mcp gather_evidence (fit_protocol item 8, certainty-tiers@2; sidecar keys of espei/SCHEMA.md)", "cells": cells}
        hp = ev / "hinge" / "exclusions_every_state.json"
        hp.parent.mkdir(parents=True, exist_ok=True)
        hp.write_text(json.dumps(hinge, indent=1))
        man.append({"path": "hinge/exclusions_every_state.json", "sha256": sha256_file(hp), "original": "derived by sage_mcp gather_evidence", "kind": "hinge_sidecar",
                    "orchid_ids": sorted({c["orchid"]["observation_id"] for c in cells if c["orchid"]["observation_id"]})})
    gaps.append({"what": "no Y25 state-id registry read", "effect": "states carry ORC ids, not state ids (state_ids empty)"})
    for s in states:   # ORCHID linkage (PI 6 Nov 2026): ORC ids from the local ORCHID data; no registry -> no state ids
        s["orchid_link"] = "present" if s.get("orchid_ids") else "missing"
        s["orchid_release"] = "unreleased"
        if not s.get("orchid_ids"):
            s["missing_reason"] = "dataset without row-level ORC ids (ESPEI-format data; pending intake)"
            s["intake_ref"] = "intake/intake_manifest.json#items.datasets_without_orchid_ids/" + s["source_file"].split("/")[-1]
    tiers = {"zpf": {k: sum(1 for s in states if (s.get("zpf_certainty") or {}).get("certainty_tier") == k) for k in beb.TIER},
             "exclusions": {k: sum(1 for s in states for e in s.get("exclusions", []) if e["certainty_tier"] == k) for k in beb.TIER}}
    (ev / "states.json").write_text(json.dumps({"artifact": spec["id"], "certainty_rule": beb.RULE2, "tier_energy_J_per_mol_atom": beb.TIER,
                                                 "counts": tiers, "n_states": len(states), "states": states}, indent=1))
    man.append({"path": "states.json", "sha256": sha256_file(ev / "states.json"), "original": "derived by sage_mcp gather_evidence", "kind": "states", "orchid_ids": []})
    ctx = _orchid_context(system, odir)
    (ev / "orchid_context.json").write_text(json.dumps(ctx, indent=1))
    lines = sorted(f"{m['sha256']}  {m['path']}" for m in man)
    bundle = {"bundle": f"{spec['id']}-evidence", "version": "1.0.0", "created": runner.now(),
              "builder": "sage_mcp.fresh.gather_evidence (format of protocols/tools/build_evidence_bundle.py)",
              "registry": {"path": None, "sha256": None}, "rule": "derived facts only; byte-identical copies; files with strings > 500 characters held",
              "files": man, "held": held, "counts": {"files": len(man), "states": len(states), "tiers": tiers,
                                                      "orchid_ids": len({i for m in man for i in m["orchid_ids"]})},
              "bundle_sha256": hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest()}
    (ev / "MANIFEST.json").write_text(json.dumps(bundle, indent=1))
    try:
        commit = subprocess.run(["git", "-C", str(odir), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=20).stdout.strip() or "not a git checkout"
    except Exception:  # noqa: BLE001
        commit = "not a git checkout"
    op = orchidproto()
    spec["inputs"][0]["files"] = data_refs
    spec["inputs"][0]["orchid"] = {"repository": tilde(odir), "commit": commit, "query": f"espei/{{{','.join(classes)}}}/{system}/*.json"}
    es = spec["evidence_selection"]
    es["orchid"] = {"repository": tilde(odir), "commit": commit, "query": f"espei/{{{','.join(classes)}}}/{system}/*.json; groups by content (ZPF with LIQUID -> liq, other ZPF -> solid, else thermo)"}
    es["manifest"] = {"path": tilde(ev / "MANIFEST.json"), "sha256": sha256_file(ev / "MANIFEST.json"), "storage_class": "local"}
    es["data_files"] = data_refs
    es["result_sha256"] = op.evidence_digest(data_refs)
    es["bundle"] = {"manifest": es["manifest"], "states": {"path": tilde(ev / "states.json"), "sha256": sha256_file(ev / "states.json"), "storage_class": "local"},
                    "bundle_sha256": bundle["bundle_sha256"]}
    sr = [{"what": f"{m['path']}", "note": "single-reader ORCHID extraction (tag single_reader_*)", "record_ids": [i for i in m["orchid_ids"] if re.fullmatch(r"ORC-[0-9A-Z]{10}", i)][:20]}
          for m in man if m["kind"] == "espei_dataset" and "single_reader" in (ev / m["path"]).read_text()]
    es["single_reader_flags"] = sr
    st["evidence_gaps"] = gaps
    log = root / "logs" / "gather_evidence.log"
    log.write_text(json.dumps({"classes": classes, "counts": bundle["counts"], "gaps": gaps}, indent=1))
    rec = {"command": f"sage_mcp gather_evidence(assessment={assessment!r}, evidence_classes={classes})", "returncode": 0,
           "started": runner.now(), "finished": runner.now(), "wall_s": None, "log": str(log)}
    done = list(GATHER_STEPS)
    inputs = [Path(os.path.expanduser(r["path"])) for r in data_refs]
    for sid in done:
        k = len(st["steps"].get(sid, {}).get("run_cards", [])) + len(st["steps"].get(sid, {}).get("superseded_run_cards", [])) + 1
        card = runner.write_run_card(root, f"{spec['id']}-{sid}-{k}", f"{spec['id']}@{spec['version']}", spec["instantiates"][0]["protocol"], sid, rec,
                                     sys.executable, inputs, [ev / "MANIFEST.json", ev / "states.json"] + ([ev / "hinge/exclusions_every_state.json"] if phases else []),
                                     notes=["internal step of sage_mcp gather_evidence"])
        _mark_done(root, spec, st, sid, card)
    _write_spec(root, spec, st, "evidence gathered", new_version=False)
    event(st, "evidence_gathered", classes=classes, files=len(man), states=len(states))
    save_state(root, st)
    return {"assessment": assessment, "preview": False, "bundle": tilde(ev / "MANIFEST.json"), "bundle_sha256": bundle["bundle_sha256"], "counts": bundle["counts"],
            "held": held, "gaps": gaps, "steps_done": done, "orchid_context": ctx if "status" in ctx else {k: (len(v) if isinstance(v, list) else v) for k, v in ctx.items()},
            "not_done": {"partial_tielines": "no generic tool: the (i)/(ii) split is part of the system-specific build_data.py; states are labelled "
                                             "partial_tie_line in states.json but the datasets are not split",
                         "weights_from_sigma": "no generic tool (build_data.py writes the weights)", "data_consistency": "no generic tool (data_consistency.py)"}}


def _mark_done(root: Path, spec: dict, st: dict, sid: str, card: Path | None) -> None:
    ent = st["steps"].setdefault(sid, {"status": "pending", "run_cards": [], "superseded_run_cards": []})
    ent["status"] = "done"
    ent["updated"] = runner.now()
    if card:
        ent["run_cards"].append(str(card.relative_to(root)))
        spec["run_sequence"].append({"run_id": card.stem, "step": sid, "status": "accepted",
                                     "run_card": {"path": tilde(card), "sha256": sha256_file(card), "storage_class": "local"}})


# ------------------------------------------------------------------ run one step
def run_fresh_step(assessment: str, step_id: str, confirm: bool = False, allow_long: bool = False, python: str | None = None,
                   nproc: int = 4, backend: str = "local", run_root: str | None = None) -> dict:
    root = _root_of(assessment)
    if run_root and Path(os.path.expanduser(run_root)).resolve() != root.resolve():
        raise SageError(f"refused: assessment {assessment} lives in {root}; run_root {run_root} differs")
    seq = {x["id"]: x for x in sequence(root, nproc)}
    if step_id not in seq:
        raise SageError(f"unknown step {step_id!r}; steps: {list(seq)}")
    x = seq[step_id]
    p, spec = current_spec(root)
    st = load_state(root)
    if x["status"] == "done":
        return {"executed": False, "reason": f"{step_id} is done; it re-runs only when marked stale"}
    if x["mode"] == "skipped":
        return {"executed": False, "reason": f"{step_id} is skipped by a documented override"}
    if x["mode"] == "judgement":
        rq = next((r for r in st["decision_requests"] if r.get("step") == step_id and r["status"] == "open"), None)
        if rq is None:
            ev = []
            for owner in _supply_owners(_step_def(spec, step_id)):
                for c in st["steps"].get(owner, {}).get("run_cards", []):
                    ev += [o["path"] for o in json.loads((root / c).read_text()).get("outputs", [])]
            rq = _request(st, step_id, f"{x['name']}. Rule: {x['decision_rule']}", evidence=ev,
                          blocks=[y for y in seq if step_id in _supply_owners(_step_def(spec, y))] + [step_id])
            save_state(root, st)
        return {"executed": False, "judgement": True, "decision_request": rq, "decided_by": x["decided_by"],
                "how": "a person answers with record_decision(assessment, request_id, decision, who, why); the server never decides",
                "blocked_until_decided": rq["blocks"]}
    if x["blockers"]:
        return {"executed": False, "refused": True, "reason": "blocked", "blockers": x["blockers"]}
    if x["mode"] == "job_spec":
        return _job_spec(root, spec, st, x, backend)
    if x["compute"]["long"] and not allow_long:
        return {"executed": False, "refused": True, "reason": f"{step_id} is a long step ({x['compute']['estimate']}): pass allow_long=true"}
    if not x["executable"]:
        return {"executed": False, "refused": True, "reason": "not executable", "because": x["not_executable_because"]}
    if not confirm:
        return {"executed": False, "dry_run": True, "reason": "confirm=true is required", "command": x["command"], "mode": x["mode"]}
    if backends.get(backend)["kind"] != "local":
        raise SageError("CPU steps run on the local backend only")
    if x["mode"] == "internal":
        if step_id in GATHER_STEPS:
            return gather_evidence(assessment)
        if step_id == "write_plan":
            return _run_write_plan(root, spec, st)
    py = python or sys.executable
    cmd = x["command"].replace(localpaths().RECORD_FIT_PYTHON, python) if python else x["command"]
    rec = runner.run_command(cmd, root, root, root / "logs" / f"{step_id}.log")
    outs = [root / r.get("path") for r in _step_def(spec, step_id)["result"] if r.get("path")]
    card = runner.write_run_card(root, f"{spec['id']}-{step_id}-{len(st['steps'].get(step_id, {}).get('run_cards', [])) + 1}", f"{spec['id']}@{spec['version']}",
                                 spec["instantiates"][0]["protocol"], step_id, rec, py, [], outs)
    if rec["returncode"] == 0:
        _mark_done(root, spec, st, step_id, card)
    else:
        st["steps"].setdefault(step_id, {"status": "pending", "run_cards": [], "superseded_run_cards": []})["run_cards"].append(str(card.relative_to(root)))
        spec["run_sequence"].append({"run_id": card.stem, "step": step_id, "status": "failed",
                                     "run_card": {"path": tilde(card), "sha256": sha256_file(card), "storage_class": "local"}})
    _write_spec(root, spec, st, f"ran {step_id}", new_version=False)
    event(st, "step_run", step=step_id, returncode=rec["returncode"])
    save_state(root, st)
    return {"executed": True, "step": step_id, "returncode": rec["returncode"], "log_tail": rec["log_tail"], "run_card": str(card)}


def _step_def(spec: dict, sid: str) -> dict:
    return next(e["step"] for e in effective_steps(spec) if e["step"]["id"] == sid)


def _run_write_plan(root: Path, spec: dict, st: dict) -> dict:
    p = _write_plan_draft(root, spec, st)
    rec = runner.run_command(f"python3 {tools_dir() / 'check_plan.py'} PLAN.md", root, root, root / "logs" / "write_plan.log")
    card = runner.write_run_card(root, f"{spec['id']}-write_plan", f"{spec['id']}@{spec['version']}", spec["instantiates"][0]["protocol"],
                                 "write_plan", rec, sys.executable, [], [p], notes=["PLAN.md written from the template; sections to be completed by a person"])
    if rec["returncode"] == 0:
        _mark_done(root, spec, st, "write_plan", card)
    _write_spec(root, spec, st, "ran write_plan", new_version=False)
    save_state(root, st)
    return {"executed": True, "step": "write_plan", "returncode": rec["returncode"], "check_plan": rec["log_tail"], "plan": str(p), "run_card": str(card)}


def _job_spec(root: Path, spec: dict, st: dict, x: dict, backend: str) -> dict:
    be = backends.get(backend)
    gen = _general(spec)
    env = next((e for e in spec.get("environment", []) if e["id"] == "mlip_container"), {})
    w = next((i for i in spec.get("inputs", []) if i["id"] == "mlip_weights"), {})
    params = _params(spec)
    job = {"job": f"{spec['id']}-{x['id']}", "step": x["id"], "protocol": f"{spec['id']}@{spec['version']}", "general": spec["instantiates"][0]["protocol"],
           "backend": be["name"], "executes": False,
           "container": {"image": env.get("image"), "digest": env.get("digest"), "packages": env.get("packages")},
           "command": x["command"], "unbound_placeholders": x["unbound"],
           "mlip_weights": {"name": w.get("name"), "files": w.get("files", []), "required_hashes": w.get("required_hashes")},
           "potential": params.get("potential"),
           "seeds": {"sqs_seeds": params.get("sqs_seeds"), "liquid_md": "one seed per run (run_liquid.py --seed); record them in the run card"},
           "parameters": {k: params.get(k) for k in ("relaxation_stages", "relaxation_optimizer", "value_rule", "liquid_md", "sqs_composition_grid") if k in params},
           "mounts": {"run_root": str(root)}, "compute": x["compute"], "hosts": env.get("hosts"),
           "after": "record the finished run with record_external_run(assessment, step, run_card) (schema-valid run card with outputs and hashes)",
           "general_compute": gen.get("compute")}
    jf = root / "jobs" / f"{x['id']}.json"
    jf.write_text(json.dumps(job, indent=1))
    ent = st["steps"].setdefault(x["id"], {"status": "pending", "run_cards": [], "superseded_run_cards": []})
    ent["status"] = "job_spec_written"
    event(st, "job_spec_written", step=x["id"], backend=be["name"])
    save_state(root, st)
    return {"executed": False, "job_spec": job, "job_file": str(jf), "submission": backends.submission_hint(be, jf),
            "reason": "GPU step: the server never runs it; the job spec is for an executor"}


def record_external_run(assessment: str, step_id: str, run_card: str) -> dict:
    root = _root_of(assessment)
    p, spec = current_spec(root)
    st = load_state(root)
    src = Path(os.path.expanduser(run_card))
    card = json.loads(src.read_text())
    errs = schema_errors(card)
    if errs:
        raise SageError(f"refused: the run card is not schema-valid: {errs[:5]}")
    if card["executes"].get("step") != step_id or card["executes"].get("specific_protocol", "").split("@")[0] != spec["id"]:
        raise SageError("refused: the run card does not execute this step of this assessment")
    dst = root / "run_cards" / f"{card['run_id']}.json"
    if dst.exists():
        raise SageError(f"refused: {dst.name} exists")
    shutil.copy2(src, dst)
    _mark_done(root, spec, st, step_id, dst)
    _write_spec(root, spec, st, f"external run {step_id}", new_version=False)
    event(st, "external_run_recorded", step=step_id, run_card=dst.name)
    save_state(root, st)
    return {"recorded": True, "step": step_id, "run_card": str(dst)}


# ------------------------------------------------------------------ decisions
def record_decision(assessment: str, request_id: str, decision: str, who: str, why: str, bindings: dict | None = None,
                    source: str | None = None, quote: str | None = None) -> dict:
    root = _root_of(assessment)
    p, spec = current_spec(root)
    st = load_state(root)
    for name, v in (("decision", decision), ("who", who), ("why", why)):
        if not v or not str(v).strip():
            raise SageError(f"refused: {name} is required (an undocumented decision is not recorded)")
    if who.strip().lower() in ("sage_mcp", "server", "mcp"):
        raise SageError("refused: the server never decides; `who` must name the person (or agent) who decided")
    rq = next((r for r in st["decision_requests"] if r["id"] == request_id), None)
    if rq is None:
        raise SageError(f"unknown decision request {request_id!r}; open: {[r['id'] for r in st['decision_requests'] if r['status'] == 'open']}")
    if rq["status"] != "open":
        raise SageError(f"request {request_id} is already decided ({rq.get('decision_id')})")
    warnings = []
    b = bindings or {}
    if "phases" in b:
        if not isinstance(b["phases"], list) or not all(isinstance(x, str) and x for x in b["phases"]):
            raise SageError("bindings.phases must be a list of phase names")
        b["phases"] = sorted({x.upper() for x in b["phases"]})
    if "T_range" in b and (len(b["T_range"]) != 2 or not float(b["T_range"][0]) < float(b["T_range"][1])):
        raise SageError("bindings.T_range must be [T_min, T_max]")
    if "final_tdb" in b:
        f = Path(os.path.expanduser(str(b["final_tdb"])))
        f = f if f.is_absolute() else root / f
        if not f.is_file():
            raise SageError(f"bindings.final_tdb {f} does not exist")
        b["final_tdb"] = str(f)
    step = rq.get("step")
    tab = {e["step"]["id"]: e["step"] for e in effective_steps(spec)}
    if step in tab and "PI" in str(tab[step].get("decided_by", "")) and not who.upper().startswith("PI"):
        warnings.append(f"step {step} is decided_by {tab[step]['decided_by']!r}; recorded as decided by {who!r}")
    did = f"D-{len(spec.get('decisions', [])) + 1:03d}"
    entry = {"id": did, "date": today(), "who": who, "decision": decision + (f" (bindings: {json.dumps(b, sort_keys=True)})" if b else ""),
             "why": why, "source": source or f"sage_mcp record_decision for {request_id}; evidence: {', '.join(rq['evidence']) or 'none given'}",
             "applies_to": sorted({x for x in [step, *rq.get("blocks", [])] if x})}
    if quote:
        entry["quote"] = quote[:500]
    spec.setdefault("decisions", []).append(entry)
    rq.update(status="decided", decision_id=did, decided=runner.now())
    stale = []
    if b:
        old = dict(st["bindings"])
        st["bindings"].update(b)
        if "phases" in b and old.get("phases") not in (None, b["phases"]):
            stale = _mark_stale(root, spec, st, ["exclusions_every_state"], f"phase set changed by {did}")
    if step in tab:
        ent = st["steps"].setdefault(step, {"status": "pending", "run_cards": [], "superseded_run_cards": []})
        ent.update(status="done", decision=did, updated=runner.now())
        spec["run_sequence"].append({"run_id": f"decision-{request_id}", "step": step, "status": "accepted", "summary": decision[:300]})
    errs = [e for e in schema_errors(spec) if not any(e.startswith(pat) for pat, _ in DRAFT_PENDING)]
    if errs:
        raise SageError(f"refused: the decision would make the protocol schema-invalid: {errs[:5]}")
    _write_spec(root, spec, st, f"decision {did}", new_version=False)
    _write_plan_draft(root, spec, st)
    event(st, "decision_recorded", request=request_id, decision=did, who=who)
    save_state(root, st)
    return {"recorded": True, "decision": entry, "request": rq, "unblocked": rq.get("blocks", []), "stale": stale, "warnings": warnings,
            "next": next_step(assessment)["next"]}


# ------------------------------------------------------------------ documented modification
CHANGE_TYPES = ("parameter_override", "threshold", "skip_step", "add_step", "reorder_step", "tool", "data_selection", "binding")


def _downstream(spec: dict, start: list[str]) -> list[str]:
    steps = effective_steps(spec)
    out = list(dict.fromkeys(start))
    changed = True
    while changed:
        changed = False
        for e in steps:
            sid = e["step"]["id"]
            if sid not in out and any(o in out for o in _supply_owners(e["step"])):
                out.append(sid); changed = True
    return out


def _mark_stale(root: Path, spec: dict, st: dict, start: list[str], why: str) -> list[str]:
    stale = []
    for sid in _downstream(spec, start):
        ent = st["steps"].get(sid)
        if ent and ent.get("status") in ("done", "job_spec_written"):
            ent["superseded_run_cards"] += ent.get("run_cards", [])
            ent["run_cards"] = []
            ent.update(status="stale", stale_because=why, updated=runner.now())
            for r in spec.get("run_sequence", []):
                if r.get("step") == sid and r.get("status") == "accepted":
                    r["status"] = "superseded"
            stale.append(sid)
    if stale:
        event(st, "marked_stale", steps=stale, why=why)
    return stale


def bump(version: str, kind: str = "minor") -> str:
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)", version)
    a, b, c = (int(x) for x in m.groups())
    return {"major": f"{a + 1}.0.0", "minor": f"{a}.{b + 1}.0", "patch": f"{a}.{b}.{c + 1}"}[kind]


def modify_protocol(assessment: str, change: dict, who: str, why: str, evidence: list[str] | None = None) -> dict:
    root = _root_of(assessment)
    p, spec = current_spec(root)
    st = load_state(root)
    if not who or not str(who).strip() or not why or not str(why).strip():
        raise SageError("refused: undocumented change (who and why are required)")
    if who.strip().lower() in ("sage_mcp", "server", "mcp"):
        raise SageError("refused: the server never changes a protocol on its own; `who` must name the person (or agent)")
    if not isinstance(change, dict) or change.get("type") not in CHANGE_TYPES:
        raise SageError(f"refused: change.type must be one of {CHANGE_TYPES}")
    gen = _general(spec)
    params = gen.get("parameters", {})
    steps = {e["step"]["id"]: e for e in effective_steps(spec)}
    t = change["type"]
    new = copy.deepcopy(spec)
    affected: list[str] = []
    ov: dict[str, Any]

    def need(*keys):
        miss = [k for k in keys if k not in change]
        if miss:
            raise SageError(f"refused: change of type {t} needs {miss}")

    if t in ("parameter_override", "threshold"):
        need("parameter", "value")
        name = change["parameter"]
        if name not in params:
            raise SageError(f"refused: {name!r} is not a parameter of {gen['id']}@{gen['version']} (to add one, propose_general_change)")
        if params[name].get("frozen") and not who.upper().startswith("PI"):
            raise SageError(f"refused: parameter {name} is frozen (fit_protocol 0.0a): it may change only by an explicit PI decision (who='PI ...')")
        ov = {"parameter": f"param:{name}", "value": change["value"], "general_default": params[name].get("default")}
        affected = [sid for sid, e in steps.items() if f"param:{name}" in e["step"].get("supply", [])]
    elif t == "skip_step":
        need("step")
        if change["step"] not in steps:
            raise SageError(f"refused: unknown step {change['step']!r}")
        ov = {"parameter": f"step:{change['step']}.skip", "value": True, "general_default": False}
        affected = _downstream(new, [change["step"]])[1:]
    elif t == "reorder_step":
        need("step", "after")
        if change["step"] not in steps or change["after"] not in steps:
            raise SageError("refused: unknown step in reorder")
        ov = {"parameter": f"step:{change['step']}.after", "value": change["after"], "general_default": "general protocol order"}
        affected = [change["step"]]
    elif t == "tool":
        need("step", "command")
        if change["step"] not in steps:
            raise SageError(f"refused: unknown step {change['step']!r}")
        if steps[change["step"]]["step"]["kind"] == "judgement":
            raise SageError("refused: a judgement step has no command to change (its decision is recorded with record_decision)")
        ov = {"parameter": f"step:{change['step']}.tool.command", "value": change["command"],
              "general_default": (steps[change["step"]]["step"].get("tool") or {}).get("command")}
        affected = [change["step"]]
    elif t == "data_selection":
        need("value")
        key = change.get("parameter", "evidence_classes")
        ov = {"parameter": f"data:{key}", "value": change["value"], "general_default": "experimental + invariants (sage_mcp default)"}
        affected = ["build_datasets"]
    elif t == "binding":
        need("name", "value")
        ov = {"parameter": f"binding:{change['name']}", "value": change["value"], "general_default": f"<{change['name']}> unbound"}
        affected = [sid for sid, e in steps.items() if f"<{change['name']}>" in ((e["step"].get("tool") or {}).get("command") or "")]
    else:  # add_step
        need("step", "after")
        sdef = change["step"]
        if not isinstance(sdef, dict) or sdef.get("id") in steps:
            raise SageError("refused: step must be a new HowToStep object with an unused id")
        if change["after"] not in steps:
            raise SageError(f"refused: unknown step {change['after']!r}")
        sec = next((s for s in new.setdefault("sections", []) if s["id"] == "sage_added_steps"), None)
        if sec is None:
            sec = {"id": "sage_added_steps", "name": "Steps added to the general protocol (documented changes)", "steps": []}
            new["sections"].append(sec)
        sec["steps"].append(sdef)
        ov = {"parameter": f"step:{sdef['id']}.after", "value": change["after"], "general_default": "not in the general protocol"}
        affected = [sdef["id"]]
    gstep = change.get("step") if isinstance(change.get("step"), str) else None
    did = f"D-{len(spec.get('decisions', [])) + 1:03d}"
    ov.update({"reason": why, "conforms": False,
               "source": f"modify_protocol by {who}, decision {did}" + (f"; departs from general step {gstep}" if gstep else "")
               + (f" ({steps[gstep]['origin']})" if gstep in steps else "")})
    new["overrides"] = [o for o in new.get("overrides", []) if o["parameter"] != ov["parameter"]] + [ov]
    new["version"] = bump(spec["version"], "minor")
    new["artifact"]["produced_by"] = f"{new['id']}@{new['version']}"
    new.setdefault("decisions", []).append({"id": did, "date": today(), "who": who,
                                            "decision": f"documented change ({t}): {json.dumps(change, ensure_ascii=False)[:400]}", "why": why,
                                            "source": "evidence: " + (", ".join(evidence) if evidence else "none given"),
                                            "applies_to": sorted(set(affected + ([gstep] if gstep else [])))})
    errs = [e for e in schema_errors(new) if not any(e.startswith(pat) for pat, _ in DRAFT_PENDING)] + _check_order(new)
    if errs:  # an added step is checked by the schema of `sections` (HowToStep) and by _check_order
        raise SageError(f"refused: the changed protocol is not valid: {errs[:6]}")
    stale = _mark_stale(root, new, st, affected, f"{did}: {t}")
    _write_spec(root, new, st, f"{did}: {t} by {who}", new_version=True)
    event(st, "modified", decision=did, change=change, who=who, version=new["version"], stale=stale)
    save_state(root, st)
    return {"accepted": True, "version": new["version"], "previous_version": spec["version"], "override": ov, "decision": new["decisions"][-1],
            "stale": stale, "protocol": str(root / st["current_spec"])}


# ------------------------------------------------------------------ general protocol versions
GENERAL_CHANGES = {"parameter_default": "minor", "add_parameter": "minor", "step_command": "minor", "add_step": "minor",
                   "step_text": "patch", "remove_step": "major", "step_kind": "major"}


def propose_general_change(change: dict, who: str, why: str, bump_kind: str | None = None, base: str = DEFAULT_GENERAL) -> dict:
    if not who or not why:
        raise SageError("refused: undocumented change (who and why are required)")
    t = (change or {}).get("type")
    if t not in GENERAL_CHANGES:
        raise SageError(f"refused: change.type must be one of {sorted(GENERAL_CHANGES)}")
    bp, g = find_protocol(base)
    if g.get("type") != "general_protocol":
        raise SageError(f"{base} is not a general protocol")
    need = GENERAL_CHANGES[t]
    params = g.get("parameters", {})
    if t == "parameter_default" and params.get(change.get("parameter"), {}).get("frozen"):
        need = "major"
    order = ["patch", "minor", "major"]
    kind = bump_kind or need
    if order.index(kind) < order.index(need):
        raise SageError(f"refused: a {t} change needs at least a {need} version bump (asked {kind})")
    new = copy.deepcopy(g)
    allsteps = {s["id"]: (sec, s) for sec, s in iter_steps(new)}
    if t == "parameter_default":
        if change.get("parameter") not in params:
            raise SageError(f"unknown parameter {change.get('parameter')!r}")
        new["parameters"][change["parameter"]]["default"] = change["value"]
    elif t == "add_parameter":
        if change.get("parameter") in params:
            raise SageError("parameter exists")
        new["parameters"][change["parameter"]] = change["definition"]
    elif t in ("step_command", "step_text", "remove_step", "step_kind"):
        sid = change.get("step")
        if sid not in allsteps:
            raise SageError(f"unknown step {sid!r}")
        sec, s = allsteps[sid]
        if t == "step_command":
            s.setdefault("tool", {})["command"] = change["command"]
        elif t == "step_text":
            s["text"] = change["text"]
        elif t == "step_kind":
            s["kind"] = change["kind"]
        else:
            sec["steps"].remove(s)
    elif t == "add_step":
        sid_after = change.get("after")
        if sid_after not in allsteps:
            raise SageError(f"unknown step {sid_after!r}")
        sec, s = allsteps[sid_after]
        sec["steps"].insert(sec["steps"].index(s) + 1, change["step"])
    new["version"] = bump(g["version"], kind)
    key = f"{g['id']}@{new['version']}"
    if key in general_protocols():
        raise SageError(f"refused: {key} exists; a released or proposed version is never edited in place")
    new["status"] = "draft"
    new["status_note"] = f"PROPOSED {key} (from {g['id']}@{g['version']}): {t} — {why}. Not merged into protocols/general; for the coordinator."
    new["supersedes"] = [{"path": tilde(bp), "sha256": sha256_file(bp), "relation": f"next version of {g['id']}@{g['version']} ({kind}: {t})", "storage_class": "local"}]
    new.setdefault("decisions", []).append({"date": today(), "who": who, "decision": f"{kind} version {new['version']}: {t} {json.dumps(change, ensure_ascii=False)[:300]}",
                                            "why": why, "source": "sage_mcp propose_general_change (changelog entry; SCHEMA_GAPS G6)"})
    errs = schema_errors(new)
    if errs:
        raise SageError(f"refused: the proposed general protocol is not schema-valid: {errs[:6]}")
    d = state.general_dir()
    d.mkdir(parents=True, exist_ok=True)
    out = d / f"{key}.json"
    out.write_text(json.dumps(new, indent=1, ensure_ascii=False))
    return {"proposed": key, "path": str(out), "bump": kind, "from": f"{g['id']}@{g['version']}", "changelog": new["decisions"][-1],
            "note": "specific protocols keep their version until migrate(assessment, to_version)"}


def migrate(assessment: str, to_version: str, who: str, why: str) -> dict:
    root = _root_of(assessment)
    p, spec = current_spec(root)
    st = load_state(root)
    if not who or not why:
        raise SageError("refused: undocumented migration (who and why are required)")
    old_ref = spec["instantiates"][0]["protocol"]
    gid = old_ref.split("@")[0]
    tp, tg = find_protocol(f"{gid}@{to_version}")
    og = _general(spec)
    if old_ref == f"{gid}@{to_version}":
        raise SageError("already on that version")
    osteps = {s["id"]: s for _, s in iter_steps(og)}
    nsteps = {s["id"]: s for _, s in iter_steps(tg)}
    changed_steps = sorted(k for k in set(osteps) | set(nsteps) if osteps.get(k) != nsteps.get(k))
    op_, np_ = og.get("parameters", {}), tg.get("parameters", {})
    changed_params = sorted(k for k in set(op_) | set(np_) if op_.get(k) != np_.get(k))
    affected = changed_steps + [sid for sid, s in nsteps.items() if any(f"param:{k}" in s.get("supply", []) for k in changed_params)]
    new = copy.deepcopy(spec)
    new["instantiates"] = [{"protocol": f"{gid}@{to_version}", "file": {"path": tilde(tp), "sha256": sha256_file(tp), "storage_class": "local"}}]
    new["version"] = bump(spec["version"], "minor")
    new["artifact"]["produced_by"] = f"{new['id']}@{new['version']}"
    did = f"D-{len(spec.get('decisions', [])) + 1:03d}"
    new["decisions"].append({"id": did, "date": today(), "who": who, "decision": f"migrate from {old_ref} to {gid}@{to_version}",
                             "why": why, "source": f"sage_mcp migrate; changed steps {changed_steps}; changed parameters {changed_params}",
                             "applies_to": sorted(set(affected))})
    errs = [e for e in schema_errors(new) if not any(e.startswith(pat) for pat, _ in DRAFT_PENDING)]
    if errs:
        raise SageError(f"refused: the migrated protocol is not valid: {errs[:6]}")
    stale = _mark_stale(root, new, st, [a for a in affected if a in nsteps], f"{did}: migration to {gid}@{to_version}")
    _write_spec(root, new, st, f"{did}: migrated to {gid}@{to_version}", new_version=True)
    event(st, "migrated", decision=did, to=f"{gid}@{to_version}", stale=stale)
    save_state(root, st)
    return {"migrated": True, "from": old_ref, "to": f"{gid}@{to_version}", "version": new["version"], "changed_steps": changed_steps,
            "changed_parameters": changed_params, "stale": stale, "decision": new["decisions"][-1]}


def get_history(assessment: str) -> dict:
    root = _root_of(assessment)
    p, spec = current_spec(root)
    st = load_state(root)
    versions = []
    for v in st["versions"]:
        f = root / v["path"]
        d = load_doc(f)
        versions.append({**v, "sha256_now": sha256_file(f), "instantiates": d["instantiates"][0]["protocol"], "n_overrides": len(d.get("overrides", [])),
                         "n_decisions": len(d.get("decisions", []))})
    steps = {k: {kk: vv for kk, vv in v.items()} for k, v in st["steps"].items()}
    return {"assessment": assessment, "current": f"{spec['id']}@{spec['version']}", "instantiates": spec["instantiates"][0]["protocol"],
            "versions": versions, "overrides": spec.get("overrides", []), "decisions": spec.get("decisions", []),
            "decision_requests": st["decision_requests"], "steps": steps,
            "stale": [k for k, v in st["steps"].items() if v.get("status") == "stale"],
            "rerun_after_stale": [k for k, v in st["steps"].items() if v.get("superseded_run_cards") and v.get("status") == "done"],
            "run_sequence": spec.get("run_sequence", []), "events": st["events"], "evidence_gaps": st.get("evidence_gaps", [])}


def compare_fresh(assessment: str) -> dict:
    return {"assessment": assessment, "note": ("a fresh assessment has no reference outputs; compare_outputs applies once it is packaged "
                                               "and rerun from its own specific protocol (independent_rerun)"), "pass": None}


# ------------------------------------------------------------------ package
def package(assessment: str) -> dict:
    root = _root_of(assessment)
    p, spec = current_spec(root)
    st = load_state(root)
    final = st["bindings"].get("final_tdb")
    missing = []
    if not final or not Path(final).is_file():
        missing.append("final pick TDB (record_decision on final_pick with bindings={'final_tdb': path})")
    stale = [k for k, v in st["steps"].items() if v.get("status") == "stale"]
    if stale:
        missing.append(f"stale steps must be re-run first: {stale}")
    if missing:
        return {"packaged": False, "missing": missing}
    f = Path(final)
    spec["artifact"]["file"] = {"path": tilde(f), "sha256": sha256_file(f), "storage_class": "local", "role": "final pick"}
    _write_spec(root, spec, st, "artifact pinned", new_version=False)
    save_state(root, st)
    out = {"packaged": True, "artifact": spec["artifact"]["file"]}
    res = subprocess.run([sys.executable, str(tools_dir() / "build_crate.py"), str(root / st["current_spec"]), str(root / "crate")],
                         capture_output=True, text=True, cwd=root)
    out["crate"] = {"returncode": res.returncode, "dir": str(root / "crate"), "log_tail": (res.stdout + res.stderr)[-800:]}
    out["dashboard"] = {"status": "pending", "reason": ("extract_dashboard_data.py knows only the cuzr and crni campaigns; an assessment_results "
                                                        "document for a fresh assessment needs its step results (SCHEMA_GAPS G7)")}
    return out
