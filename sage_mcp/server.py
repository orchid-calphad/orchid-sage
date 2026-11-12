"""ORCHID-SAGE MCP server.

Uses the official MCP Python SDK (``pip install mcp``; MCPServer in mcp 2.x, FastMCP in 1.x) when it is installed.
Without it, ``--transport stdio`` falls back to a small built-in JSON-RPC 2.0 implementation of the MCP stdio protocol
(tools, resources, prompts), so the server works in a bare Python 3.11+ environment. Same design as orchid-mcp.
"""

from __future__ import annotations

import argparse
import functools
import inspect
import json
import sys
import types
import typing
from pathlib import Path
from typing import Any, Callable, Literal

from . import __version__, backends, fresh, ids, prompts, reproduce
from .repo import SageError, repo_protocols, repo_root

SERVER_NAME = "orchid-sage"
INSTRUCTIONS = (
    "ORCHID-SAGE (Systematic Assessment of Gibbs Energies): machine-executable CALPHAD protocols. Reproduce mode: read a "
    "specific protocol, validate it, verify its inputs by sha256, plan, run one step at a time in a fresh run root, compare "
    "with the published outputs (byte identity for deterministic steps, declared tolerances for numerical ones). Fresh mode: "
    "new_assessment from the general protocol, gather_evidence from ORCHID, next_step / run_step, documented changes "
    "(modify_protocol, propose_general_change, migrate), get_history, package. Judgement steps are never executed or decided "
    "by the server: it returns the recorded decision or a decision request for a person. GPU steps return job specs. Start "
    "with the reproduce_assessment or run_fresh_assessment prompt."
)

Fields = Literal["summary", "full"]


def _call(fn: Callable[..., dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
    try:
        return fn(**kwargs)
    except (SageError, FileNotFoundError, KeyError, ValueError) as exc:
        return {"error": f"{type(exc).__name__}: {exc}" if not isinstance(exc, SageError) else str(exc)}


# ---------------------------------------------------------------- read tools
def list_protocols() -> dict:
    """Every protocol the server knows: general and specific protocols under protocols/ (reproduce mode), proposed
    general-protocol versions, and fresh assessments (with their run roots)."""
    return _call(reproduce.list_protocols)


def get_protocol(protocol: str, fields: Fields = "summary") -> dict:
    """One protocol by id@version (e.g. "crni-paper-fit-step4-s1@0.1.0-draft", "orchid-calphad-fit@2.0.0") or a fresh
    assessment id. fields="summary": header, sections with step ids, inputs, run sequence, reproduce plan; "full": the document."""
    return _call(reproduce.get_protocol, protocol=protocol, fields=fields)


def get_steps(protocol: str, section: str | None = None) -> dict:
    """Steps of a protocol (a specific protocol also lists the general protocol's steps and its reproduce items): id,
    section, kind (deterministic | numerical | judgement), exact command, environment, compute class. section filters."""
    return _call(reproduce.get_steps, protocol=protocol, section=section)


def get_step(protocol: str, step_id: str) -> dict:
    """One step: exact command, inputs (supply), outputs (result with checks), kind, decision rule and decided_by,
    tolerances, gates, compute class and unbound placeholders. Also accepts a reproduce item id (e.g. "step2",
    "evaluate_states"). For a judgement step of a specific protocol: the recorded decision and its source."""
    return _call(reproduce.get_step, protocol=protocol, step_id=step_id)


def get_run_cards(protocol: str) -> dict:
    """The run sequence with each run card (host, interpreter, command, seeds, threads, packages, trajectory record),
    whether the card exists and its sha256 matches."""
    return _call(reproduce.get_run_cards, protocol=protocol)


def get_decisions(protocol: str) -> dict:
    """Decisions log (date, who, decision, why, source) and overrides (conforms=false = departs from the general protocol);
    for a fresh assessment also the decision requests (open or decided)."""
    return _call(reproduce.get_decisions, protocol=protocol)


def get_evidence_manifest(assessment: str, kind: str | None = None, limit: int = 50, offset: int = 0) -> dict:
    """Evidence bundle of an assessment (e.g. "crni-paper-fit-step4-s1"): counts, certainty-tier counts, bundle sha256 and
    whether it recomputes, files (paged; kind filters espei_dataset | hinge_sidecar | oneshot_observations | model_input |
    artifact | reference_output | states) and the files of the page that fail their hash."""
    return _call(reproduce.get_evidence_manifest, assessment=assessment, kind=kind, limit=limit, offset=offset)


def get_evidence_links(assessment: str, link: str | None = None, reason: str | None = None, limit: int = 50, offset: int = 0) -> dict:
    """ORCHID linkage of every evidence state of an assessment (PI 6 Nov 2026): ORC record ids, S-/C- state ids, release
    and the resolvable chain (record -> state -> paper DOI -> page/table locator), or orchid_link "missing" with its reason
    and intake reference. link: "present" | "missing" to filter; reason: substring of missing_reason. Returns link coverage."""
    return _call(reproduce.get_evidence_links, assessment=assessment, link=link, reason=reason, limit=limit, offset=offset)


def get_dashboard_data(assessment: str, section: str | None = None, max_items: int = 50) -> dict:
    """Dashboard data (assessment_results document). Without section: the list of sections with sizes, the pick and the
    status banner. section="steps" | "states_evaluated" | "invariants" | "checks" | "uq" | "trajectory" | ...: that
    section (lists truncated to max_items; trajectory runs reduced to their first and last points)."""
    return _call(reproduce.get_dashboard_data, assessment=assessment, section=section, max_items=max_items)


def get_open_questions(ids: list[str] | None = None) -> dict:
    """protocols/OPEN_QUESTIONS.md parsed: id, group, resolved flag, status line and text. ids filters (e.g. ["Q35","Q36"])."""
    return _call(reproduce.get_open_questions, ids=ids)


# ---------------------------------------------------------------- checks
def validate(document: str | None = None) -> dict:
    """Run protocols/tools/validate.py (schema, file hashes, step order, cross-document links). document: a protocol
    id@version or path fragment to keep only its lines, "all" or omitted for everything; a fresh assessment id checks
    its own protocol and run cards (draft-pending items reported separately)."""
    return _call(reproduce.validate, document=document)


def verify_inputs(protocol: str, detail: bool = False) -> dict:
    """sha256 of every file the protocol references that is on this host (ok, mismatch, missing, restricted present or
    missing, remote_record), plus every file of the bundle manifests a rerun stages from (rerun_ready). detail=true
    lists the matching files too (otherwise only their count)."""
    return _call(reproduce.verify_inputs, protocol=protocol, detail=detail)


# ---------------------------------------------------------------- execution
def plan_reproduction(protocol: str, run_root: str | None = None, python: str | None = None, pfp: str | None = None, nproc: int = 4) -> dict:
    """Ordered reproduce items of a specific protocol (stage, environment_check, deterministic bindings, the fits) with
    bound commands, expected outputs and their checks, kind, compute class with measured estimates, tolerances, and the
    judgement steps with their recorded decisions. Runs nothing."""
    return _call(reproduce.plan_reproduction, protocol=protocol, run_root=run_root, python=python, pfp=pfp, nproc=nproc)


def run_step(protocol: str, step_id: str, run_root: str, confirm: bool = False, allow_long: bool = False, python: str | None = None,
             pfp: str | None = None, nproc: int = 4, backend: str = "local", detach: bool | None = None) -> dict:
    """Run ONE step. protocol: a specific protocol id@version (reproduce mode; step_id = a reproduce item, "stage" first)
    or a fresh assessment id (step_id = a protocol step). Needs confirm=true. Refuses: run roots inside the repository,
    the campaign directories, the restricted material (local config) or not created by this server; commands writing outside the run root; long or GPU
    steps without allow_long=true; a second item while one is running in the run root. GPU steps return a job spec (never
    run). Judgement steps are never run: the recorded decision (reproduce) or a decision request (fresh) is returned.
    Short items run synchronously, write a run card and return the log tail. Long reproduce items (needs_allow_long) are
    started DETACHED by default (detach=null; true/false forces it): the call returns at once with status "running"; then
    call step_status until "finished", which writes the run card. No call stays open while a fit runs."""
    return _call(reproduce.run_step, protocol=protocol, step_id=step_id, run_root=run_root, confirm=confirm, allow_long=allow_long,
                 python=python, pfp=pfp, nproc=nproc, backend=backend, detach=detach)


def start_step(protocol: str, step_id: str, run_root: str, confirm: bool = False, allow_long: bool = False, python: str | None = None,
               pfp: str | None = None, nproc: int = 4) -> dict:
    """Start ONE reproduce item detached (same checks and refusals as run_step) and return at once with its handle (item,
    pids, job file, log). The item keeps running between calls and after the session ends. Follow with step_status."""
    return _call(reproduce.start_step, protocol=protocol, step_id=step_id, run_root=run_root, confirm=confirm, allow_long=allow_long,
                 python=python, pfp=pfp, nproc=nproc)


def step_status(protocol: str, run_root: str, step_id: str | None = None, wait_s: float = 0) -> dict:
    """Status of a detached reproduce item: running (elapsed, log tail) | finished | lost | not started. wait_s blocks
    while the item runs, up to the server's cap (900 s by default), and returns as soon as it ends; use it instead of
    polling quickly. When the item has finished, writes its run card once, exactly as a synchronous run_step would, and
    returns that result (returncode, outputs, run card). Without step_id: every job of the run root."""
    return _call(reproduce.step_status, protocol=protocol, run_root=run_root, step_id=step_id, wait_s=wait_s)


def compare_outputs(protocol: str, run_root: str, python: str | None = None) -> dict:
    """Compare a run root with the published outputs: byte identity for deterministic items, the declared tolerances
    (tdb_abs, json_tol via orchid_reproduce.py --compare-only) for numerical ones. Writes comparison/comparison.json + .md."""
    return _call(reproduce.compare_outputs, protocol=protocol, run_root=run_root, python=python)


# ---------------------------------------------------------------- fresh assessments
def new_assessment(system: str, assessment_id: str, run_root: str, phases: list[str] | None = None, T_range: list[float] | None = None,
                   general: str = "orchid-calphad-fit@2.0.0", title: str | None = None) -> dict:
    """Instantiate a new specific protocol (draft 0.1.0) from the general protocol in a fresh run root: fills what is
    known, opens a decision request for every required decision (established practice, phases if not given, T range if
    not given, unaries), writes the PLAN.md draft. system: binary in alphabetical order, e.g. "AL-CU"."""
    return _call(fresh.new_assessment, system=system, assessment_id=assessment_id, run_root=run_root, phases=phases, T_range=T_range,
                 general=general, title=title)


def gather_evidence(assessment: str, evidence_classes: list[str] | None = None, orchid_data_dir: str | None = None) -> dict:
    """Build the evidence bundle of a fresh assessment from the local ORCHID data (ORCHID_DATA_DIR, espei/<class>/<SYS>):
    byte-identical dataset copies grouped liq/thermo/solid, states with certainty tiers (10/50/100 J/mol-atom), excluded
    phases at every observed state (needs the phase set), MANIFEST.json in the format of build_evidence_bundle.py. Gaps
    are returned as gaps. evidence_classes default: experimental, invariants."""
    return _call(fresh.gather_evidence, assessment=assessment, evidence_classes=evidence_classes, orchid_data_dir=orchid_data_dir)


def next_step(assessment: str, nproc: int = 4) -> dict:
    """The next step of a fresh assessment (one-shot -> liquidus -> thermochemistry -> solid state + exclusions ->
    ambiguous structures -> checks -> ranking -> UQ -> package) with its bound command, inputs, compute class, mode
    (internal | command | judgement | job_spec), blockers and why it is not executable; plus the whole sequence."""
    return _call(fresh.next_step, assessment=assessment, nproc=nproc)


def record_decision(assessment: str, request_id: str, decision: str, who: str, why: str, bindings: dict | None = None,
                    source: str | None = None, quote: str | None = None) -> dict:
    """Record a person's answer to a decision request (the server never decides). who/why required. bindings carries
    values the decision fixes, e.g. {"phases": ["LIQUID","FCC_A1"]}, {"T_range": [300, 2000]}, {"final_tdb": path}.
    Unblocks the dependent steps; a changed phase set marks the exclusions stale."""
    return _call(fresh.record_decision, assessment=assessment, request_id=request_id, decision=decision, who=who, why=why,
                 bindings=bindings, source=source, quote=quote)


def record_external_run(assessment: str, step_id: str, run_card: str) -> dict:
    """Record a step that ran elsewhere (e.g. a GPU job from its job spec): a schema-valid run card for this step."""
    return _call(fresh.record_external_run, assessment=assessment, step_id=step_id, run_card=run_card)


def modify_protocol(assessment: str, change: dict, who: str, why: str, evidence: list[str] | None = None) -> dict:
    """Documented change of a fresh assessment's specific protocol. change.type: parameter_override | threshold
    {parameter, value}; skip_step {step}; add_step {step: HowToStep, after}; reorder_step {step, after}; tool {step, command};
    data_selection {value[, parameter]}; binding {name, value}. Written as an override (conforms=false, naming the general
    step) plus a decisions entry; bumps the version; validated before acceptance; affected steps marked stale (run cards kept).
    Refused without who and why, for unknown steps/parameters, frozen parameters unless who is the PI, or invalid results."""
    return _call(fresh.modify_protocol, assessment=assessment, change=change, who=who, why=why, evidence=evidence)


def propose_general_change(change: dict, who: str, why: str, bump: str | None = None, base: str = "orchid-calphad-fit@2.0.0") -> dict:
    """Write a NEW version of the general protocol (never edits a version in place) with a changelog entry in its
    decisions. change.type: parameter_default {parameter, value} (minor; major if frozen) | add_parameter {parameter,
    definition} | step_command {step, command} | add_step {after, step} (minor) | step_text {step, text} (patch) |
    remove_step {step} | step_kind {step, kind} (major). Saved under the server state dir, not protocols/general."""
    return _call(fresh.propose_general_change, change=change, who=who, why=why, bump_kind=bump, base=base)


def migrate(assessment: str, to_version: str, who: str, why: str) -> dict:
    """Move a fresh assessment to another general-protocol version (recorded as a decision; bumps the specific version;
    steps whose general definition or parameters changed, and their dependents, are marked stale)."""
    return _call(fresh.migrate, assessment=assessment, to_version=to_version, who=who, why=why)


def get_history(assessment: str) -> dict:
    """Full change history of a fresh assessment: versions (with sha256), overrides, decisions, decision requests,
    step status (stale and re-run steps, superseded run cards), run sequence and the event log."""
    return _call(fresh.get_history, assessment=assessment)


def package(assessment: str) -> dict:
    """Package a fresh assessment: pin the final TDB in the protocol and build the RO-Crate (build_crate.py); reports what
    is missing (final pick, stale steps) instead of packaging."""
    return _call(fresh.package, assessment=assessment)


def list_backends() -> dict:
    """Executor backends: local (CPU, enabled) and configured remote ones (disabled unless the user enables them in the
    config file; even enabled, the server only writes job specs)."""
    return _call(backends.describe)


def compute_ids(pid: str | None = None, locator: dict | None = None, state: dict | None = None, observation_key: str | None = None,
                orcid: str | None = None, dataset_uuid: str | None = None, new_namespace: bool = False, check_id: str | None = None,
                orchid_data_dir: str | None = None, rule: str = "coord-rule/3") -> dict:
    """ORCHID ids computed offline, for data ORCHID has not released (PI 6 Nov 2026; docs/ID_SCHEME.md). Record id ORC-
    from the full locator pid ("doi:<doi>/p<page>/tab-<label>/r<nn>#<datum>", a dataset DOI with "supp-<file>/r<nn>",
    or the provisional "local:<ORCID>/<dataset-uuid>/supp-<file>/r<nn>#equilibrium_property") or from locator parts
    {doi | orcid+dataset_uuid, kind: table|figure|text|supplement, page, label, row | series+point, datum_type}.
    State ids C-/S- (coord-rule/2) from state = a literature-form record {system, observation_type, property, phases
    [{label, model_phase}], temperature_K, pressure_Pa, overall_composition, transition_kind}, phases resolved through
    the phase registry of ORCHID_DATA_DIR. orcid (+ dataset_uuid, or new_namespace=true) alone: a new provisional
    namespace. check_id: verify that an id recomputes from its locator. rule: "coord-rule/3" (PI 6 Nov 2026: own
    invariant T in a 5 K cell with the reaction kind, SGTE SER reference state, decimal rounding, pressure unknown
    unless printed) or "coord-rule/2" (the current v2027.01-candidate registry). Reports what keeps an id provisional
    and whether the value must be converted to the SGTE reference."""
    return _call(ids.compute_ids, pid=pid, locator=locator, state=state, observation_key=observation_key, orcid=orcid,
                 dataset_uuid=dataset_uuid, new_namespace=new_namespace, check_id=check_id, orchid_data_dir=orchid_data_dir,
                 rule=rule)


TOOLS: list[Callable[..., dict]] = [
    list_protocols, get_protocol, get_steps, get_step, get_run_cards, get_decisions, get_evidence_manifest, get_evidence_links, get_dashboard_data,
    get_open_questions, validate, verify_inputs, plan_reproduction, run_step, start_step, step_status, compare_outputs,
    new_assessment, gather_evidence, next_step, record_decision, record_external_run, modify_protocol, propose_general_change,
    migrate, get_history, package, list_backends, compute_ids,
]


# ---------------------------------------------------------------- resources
def resources() -> dict[str, tuple[str, str, str, Path]]:
    """uri -> (name, description, mime type, file)."""
    root = repo_root()
    out: dict[str, tuple[str, str, str, Path]] = {}
    for key, (p, d) in sorted(repo_protocols().items()):
        out[f"sage://protocol/{key}.yaml"] = (f"{key}.yaml", f"{d['type']} {key}: {d.get('title', '')}", "application/yaml", p)
        if p.with_suffix(".md").is_file():
            out[f"sage://protocol/{key}.md"] = (f"{key}.md", f"rendered {key}", "text/markdown", p.with_suffix(".md"))
    for f in sorted((root / "protocols" / "run_cards").glob("*.json")):
        out[f"sage://run-card/{f.stem}"] = (f.name, f"run card {f.stem}", "application/json", f)
    for f in sorted((root / "protocols" / "schema").glob("*.json")):
        out[f"sage://schema/{f.name}"] = (f.name, f"schema {f.name} (orchid-assessment-schema 1.0.0-draft)", "application/schema+json", f)
    for f in sorted((root / "protocols" / "dashboards").glob("*/dashboard_data.json")):
        out[f"sage://dashboard/{f.parent.name}/data"] = (f"{f.parent.name} dashboard data", "assessment_results document (large)", "application/json", f)
    for a in sorted((root / "assessments").glob("*/")):
        for kind in ("evidence", "code"):
            m = a / kind / "MANIFEST.json"
            if m.is_file():
                out[f"sage://{kind}/{a.name}/manifest"] = (f"{a.name} {kind} manifest", f"{kind} bundle manifest (sha256 of every file)", "application/json", m)
    for name in ("SCHEMA.md", "REPRODUCE.md", "OPEN_QUESTIONS.md"):
        p = root / "protocols" / name
        if p.is_file():
            out[f"sage://docs/{name}"] = (name, f"protocols/{name}", "text/markdown", p)
    here = Path(__file__).resolve().parent
    for name in ("README.md", "REPRODUCE_WITH_MCP.md", "SCHEMA_GAPS.md"):
        if (here / name).is_file():
            out[f"sage://mcp/{name}"] = (name, f"sage_mcp/{name}", "text/markdown", here / name)
    return out


def read_resource(uri: str) -> tuple[str, str]:
    res = resources()
    if uri not in res:
        raise SageError(f"unknown resource {uri!r}")
    _, _, mime, p = res[uri]
    return p.read_text(encoding="utf-8"), mime


# ------------------------------------------------------------ JSON schema
def _schema_for(tp: Any) -> dict[str, Any]:
    origin = typing.get_origin(tp)
    args = typing.get_args(tp)
    if origin in (typing.Union, types.UnionType):
        non_none = [a for a in args if a is not type(None)]
        inner = _schema_for(non_none[0]) if len(non_none) == 1 else {}
        return {"anyOf": [inner, {"type": "null"}]} if type(None) in args else inner
    if origin is typing.Literal:
        return {"type": "string", "enum": list(args)}
    if origin is list or tp is list:
        return {"type": "array", "items": _schema_for(args[0]) if args else {}}
    if origin is dict or tp is dict:
        return {"type": "object"}
    return {str: {"type": "string"}, int: {"type": "integer"}, float: {"type": "number"}, bool: {"type": "boolean"}}.get(tp, {})


def tool_schema(fn: Callable[..., Any]) -> dict[str, Any]:
    hints = typing.get_type_hints(fn)
    props: dict[str, Any] = {}
    required = []
    for name, p in inspect.signature(fn).parameters.items():
        sch = dict(_schema_for(hints.get(name, str)))
        if p.default is inspect.Parameter.empty:
            required.append(name)
        else:
            sch["default"] = p.default
        props[name] = sch
    return {"type": "object", "properties": props, "required": required}


def tool_descriptions() -> list[dict[str, Any]]:
    return [{"name": fn.__name__, "description": inspect.cleandoc(fn.__doc__ or ""), "inputSchema": tool_schema(fn)} for fn in TOOLS]


# ------------------------------------------------------- official SDK path
def _sdk_server_class() -> tuple[Any, int]:
    try:
        from mcp.server.mcpserver import MCPServer  # mcp >= 2

        return MCPServer, 2
    except ImportError:
        from mcp.server.fastmcp import FastMCP  # mcp 1.x

        return FastMCP, 1


def _raising(fn: Callable[..., dict], gen: int) -> Callable[..., str]:
    if gen >= 2:
        from mcp.server.mcpserver.exceptions import ToolError
    else:
        from mcp.server.fastmcp.exceptions import ToolError

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        result = fn(*args, **kwargs)
        if isinstance(result, dict) and "error" in result:
            raise ToolError(result["error"])
        return json.dumps(result, ensure_ascii=False)

    wrapper.__annotations__ = {**typing.get_type_hints(fn), "return": str}
    return wrapper


def build_fastmcp(host: str = "127.0.0.1", port: int = 8000) -> Any:
    cls, gen = _sdk_server_class()
    server = cls(SERVER_NAME, instructions=INSTRUCTIONS, version=__version__) if gen >= 2 else cls(SERVER_NAME, instructions=INSTRUCTIONS, host=host, port=port)
    server._sage_http = {"host": host, "port": port, "gen": gen}
    for fn in TOOLS:
        server.tool(structured_output=False)(_raising(fn, gen))
    for uri, (name, desc, mime, _p) in resources().items():

        def _make(u: str) -> Callable[[], str]:
            def read() -> str:
                return read_resource(u)[0]

            read.__name__ = "resource_" + "".join(c if c.isalnum() else "_" for c in u)
            return read

        server.resource(uri, name=name, description=desc, mime_type=mime)(_make(uri))
    for pname, (desc, params, _tpl) in prompts.PROMPTS.items():

        def _mk(n: str, ps: list) -> Callable[..., str]:
            def f(**kw: str) -> str:
                return prompts.render(n, kw)

            f.__signature__ = inspect.Signature([inspect.Parameter(p, inspect.Parameter.KEYWORD_ONLY, default="", annotation=str) for p, _, _ in ps])
            f.__annotations__ = {p: str for p, _, _ in ps} | {"return": str}
            f.__name__ = n
            return f

        server.prompt(name=pname, description=desc)(_mk(pname, params))
    return server


def run_sdk(server: Any, transport: str) -> None:
    if transport == "stdio":
        server.run(transport="stdio")
        return
    cfg = server._sage_http
    if cfg["gen"] >= 2:
        server.run(transport="streamable-http", host=cfg["host"], port=cfg["port"])
    else:
        server.run(transport="streamable-http")


# --------------------------------------------------- built-in stdio fallback
PROTOCOL_VERSION = "2025-06-18"


def handle_request(msg: dict[str, Any]) -> dict[str, Any] | None:
    mid = msg.get("id")
    method = msg.get("method", "")
    params = msg.get("params")
    if mid is None:
        return None

    def ok(result: Any) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    def err(code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}

    if params is None:
        params = {}
    elif not isinstance(params, dict):
        return err(-32602, "params must be an object")
    name, arguments = params.get("name"), params.get("arguments")
    if method in ("tools/call", "prompts/get"):
        if not isinstance(name, str):
            return err(-32602, "params.name must be a string")
        if arguments is not None and not isinstance(arguments, dict):
            return err(-32602, "params.arguments must be an object")
    if method == "resources/read" and not isinstance(params.get("uri"), str):
        return err(-32602, "params.uri must be a string")

    if method == "initialize":
        return ok({"protocolVersion": params.get("protocolVersion") or PROTOCOL_VERSION,
                   "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                   "serverInfo": {"name": SERVER_NAME, "version": __version__}, "instructions": INSTRUCTIONS})
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": tool_descriptions()})
    if method == "tools/call":
        fn = {f.__name__: f for f in TOOLS}.get(name)
        if fn is None:
            return err(-32602, f"unknown tool {name!r}")
        args = arguments or {}
        bad = set(args) - set(inspect.signature(fn).parameters)
        if bad:
            return ok({"content": [{"type": "text", "text": f"unknown arguments: {sorted(bad)}"}], "isError": True})
        try:
            result = fn(**args)
        except TypeError as exc:
            return ok({"content": [{"type": "text", "text": f"bad arguments: {exc}"}], "isError": True})
        return ok({"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}], "structuredContent": result,
                   "isError": "error" in result})
    if method == "resources/list":
        return ok({"resources": [{"uri": u, "name": n, "description": d, "mimeType": m} for u, (n, d, m, _p) in resources().items()]})
    if method == "resources/read":
        try:
            text, mime = read_resource(params["uri"])
        except SageError as exc:
            return err(-32602, str(exc))
        return ok({"contents": [{"uri": params["uri"], "mimeType": mime, "text": text}]})
    if method == "prompts/list":
        return ok({"prompts": [{"name": n, "description": d, "arguments": [{"name": p, "description": pd, "required": r} for p, pd, r in ps]}
                               for n, (d, ps, _t) in prompts.PROMPTS.items()]})
    if method == "prompts/get":
        if name not in prompts.PROMPTS:
            return err(-32602, f"unknown prompt {name!r}")
        return ok({"description": prompts.PROMPTS[name][0],
                   "messages": [{"role": "user", "content": {"type": "text", "text": prompts.render(name, arguments or {})}}]})
    return err(-32601, f"method not found: {method}")


def run_fallback_stdio(stdin: Any = None, stdout: Any = None) -> None:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            resp: dict[str, Any] | None = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        else:
            if not isinstance(msg, dict):
                stdout.write(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "invalid request"}}) + "\n")
                stdout.flush()
                continue
            try:
                resp = handle_request(msg)
            except Exception as exc:  # keep the server alive
                resp = {"jsonrpc": "2.0", "id": msg.get("id"), "error": {"code": -32603, "message": str(exc)}}
        if resp is not None:
            stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            stdout.flush()


def sdk_available() -> bool:
    try:
        _sdk_server_class()
    except ImportError:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="orchid-sage-mcp", description="ORCHID-SAGE MCP server (machine-executable CALPHAD protocols)")
    ap.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--fallback", action="store_true", help="use the built-in stdio server even if `mcp` is installed")
    ap.add_argument("--version", action="version", version=f"orchid-sage-mcp {__version__}")
    args = ap.parse_args(argv)
    if args.transport == "http":
        if not sdk_available():
            print("streamable HTTP needs the MCP SDK: pip install mcp", file=sys.stderr)
            return 2
        run_sdk(build_fastmcp(args.host, args.port), "http")
        return 0
    if sdk_available() and not args.fallback:
        run_sdk(build_fastmcp(), "stdio")
    else:
        run_fallback_stdio()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
