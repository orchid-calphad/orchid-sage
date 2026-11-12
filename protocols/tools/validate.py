#!/usr/bin/env python3
"""Validate every ORCHID protocol document under protocols/ (standard library only).

  python3 tools/validate.py [--quiet] [--crosscheck PYTHON]

Checks, per document type:
  all        schema (protocol.schema.json or assessment-results.schema.json); every file reference
             ({path, sha256, storage_class}) exists and its sha256 matches (remote_record: hash only, reported);
             no restricted file is stored under protocols/; no personal home path (/Users/<name>) in the text
             in a public copy (PUBLIC_SUBSTITUTES.json at the root): a file of a pinned original is satisfied by its
             sanitized copy, and a file outside this checkout (campaign directories, other checkouts, restricted
             material) that is not present is pinned by sha256 only and counted, not an error
  protocols  every step's `supply` is an input, a parameter, or a result of an EARLIER step; tool.code and
             tool.environment name declared entries; gate and ranking ids exist; open-question ids exist
  specific   `instantiates` resolves to a general protocol with the same id@version and file hash; every
             run_sequence step exists in that general protocol (or in the specific protocol's own sections);
             run cards exist; the evidence digest recomputes
  run_card   `executes` names a specific and a general protocol that exist and a step of the general protocol
  results    trajectory vectors have the declared length; projection basis is d x 2
--crosscheck PYTHON: re-parse every YAML with PyYAML and re-validate every document with the `jsonschema`
package from another interpreter that already has them (no install), and compare.
Exit code 0 when no errors (warnings allowed)."""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import localpaths  # noqa: E402
import orchidproto as op  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import orchid_ids  # noqa: E402  (ORCHID id rules, docs/ID_SCHEME.md)

ROOT = op.ROOT
SCHEMA_OF = {"general_protocol": "protocol.schema.json", "specific_protocol": "protocol.schema.json",
             "run_card": "protocol.schema.json", "assessment_results": "assessment-results.schema.json"}
HOME_RE = re.compile(r"/Users/[A-Za-z0-9._-]+/|/home/[A-Za-z0-9._-]+/")


def documents():
    pats = ["general/*.yaml", "specific/*.yaml", "specific/*.json", "run_cards/*.json", "run_cards/*.yaml", "dashboards/*/dashboard_data.json"]
    for p in pats:
        for f in sorted(ROOT.glob(p)):
            yield f


def file_refs(node, path="$"):
    if isinstance(node, dict):
        if "path" in node and "sha256" in node and "storage_class" in node:
            yield path, node
        for k, v in node.items():
            yield from file_refs(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from file_refs(v, f"{path}[{i}]")


_PUB = None


def public_copies():
    """PUBLIC_SUBSTITUTES.json of a public export (protocols/tools/public_sanitize.py export): path -> (original, copy) sha256."""
    global _PUB
    if _PUB is None:
        m = ROOT.parent / "PUBLIC_SUBSTITUTES.json"
        _PUB = {r["path"]: (r["original_sha256"], r["sanitized_sha256"]) for r in json.loads(m.read_text())["files"]} if m.is_file() else {}
    return _PUB


def frozen_version(f, sha):
    """A living document (docs/fit_protocol.md) changes after a protocol pins it; the exact pinned text is then kept beside
    it as a frozen version <name>@<version>.<ext> (e.g. docs/fit_protocol@2.0.0.md, recovered byte for byte from git history;
    index in docs/fit_protocol.versions.json). Returns the frozen version whose sha256 is the pinned one, else None. The
    protocol YAMLs are not edited: the pin stays on the living path and is resolved by hash."""
    for q in sorted(f.parent.glob(f"{f.stem}@*{f.suffix}")):
        if not q.is_file():
            continue
        h = op.sha256_file(q)
        if h == sha or (inside_checkout(q) and public_copies().get(str(q.resolve().relative_to(ROOT.parent.resolve()))) == (sha, h)):
            return q                                          # the frozen version, or (public export) its public copy
    return None


def inside_checkout(f):
    try:
        Path(f).resolve().relative_to(ROOT.parent.resolve())
        return True
    except ValueError:
        return False


def check_refs(doc, rel, errs, warns, stats):
    for p, r in file_refs(doc):
        stats["refs"] += 1
        if r["storage_class"] == "remote_record":
            stats["remote"] += 1
            continue
        if r.get("sha256") in (None, ""):
            errs.append(f"{rel} {p}: sha256 missing for {r['path']}")
            continue
        f = op.expand(r["path"])
        if not f.exists() and public_copies() and not inside_checkout(f):
            # a public copy holds this repository only: campaign directories, other checkouts and restricted material
            # stay on the machines that ran the records, so their files are pinned by sha256 only here (counted, not errors)
            stats["outside_copy"] = stats.get("outside_copy", 0) + 1
            continue
        if not f.exists():
            errs.append(f"{rel} {p}: file not found {r['path']}")
            continue
        if f.is_dir():
            errs.append(f"{rel} {p}: is a directory {r['path']}")
            continue
        h = op.sha256_file(f)
        try:
            pc = public_copies().get(str(f.resolve().relative_to(ROOT.parent.resolve())))
        except ValueError:
            pc = None
        fv = frozen_version(f, r["sha256"]) if h != r["sha256"] else None
        if h != r["sha256"] and pc == (r["sha256"], h):      # the public copy of the pinned original (public export)
            stats["public_copy"] = stats.get("public_copy", 0) + 1
        elif fv is not None:                                  # a living document; the pinned text is kept as a frozen version
            stats["frozen_version"] = stats.get("frozen_version", 0) + 1
            if "--quiet" not in sys.argv:
                print(f"  {rel} {p}: pinned text of {r['path']} resolved by hash to {fv.relative_to(ROOT.parent)}")
        elif h != r["sha256"]:
            errs.append(f"{rel} {p}: sha256 mismatch for {r['path']} (file {h[:12]}, recorded {r['sha256'][:12]})")
        else:
            stats["hash_ok"] += 1
        if r["storage_class"] == "restricted":
            stats["restricted"] += 1
            try:
                f.resolve().relative_to(ROOT.resolve())
                errs.append(f"{rel} {p}: restricted file stored under protocols/: {r['path']}")
            except ValueError:
                pass


def check_steps(doc, rel, errs, warns, general=None):
    inputs = {i["id"] for i in doc.get("inputs", [])}
    params = set(doc.get("parameters", {}) or {})
    if general is not None:
        params |= set(general.get("parameters", {}) or {})
        inputs |= {i["id"] for i in general.get("inputs", [])}
    codes = {c["id"] for c in doc.get("code", [])} | ({c["id"] for c in general.get("code", [])} if general else set())
    envs = {e["id"] for e in doc.get("environment", [])} | ({e["id"] for e in general.get("environment", [])} if general else set())
    gates = {g["id"] for g in doc.get("gates", [])} | ({g["id"] for g in general.get("gates", [])} if general else set())
    ranks = {g["id"] for g in doc.get("ranking_criteria", [])} | ({g["id"] for g in general.get("ranking_criteria", [])} if general else set())
    produced, seen_steps = set(), set()
    nsteps = 0
    for sec in doc.get("sections", []) or []:
        for st in sec["steps"]:
            nsteps += 1
            sid = st["id"]
            if sid in seen_steps:
                errs.append(f"{rel}: duplicate step id {sid}")
            for s in st.get("supply", []):
                if s.startswith("input:"):
                    if s[6:] not in inputs:
                        errs.append(f"{rel} step {sid}: supply {s} is not a declared input")
                elif s.startswith("param:"):
                    if s[6:].split(".")[0] not in params:
                        errs.append(f"{rel} step {sid}: supply {s} is not a declared parameter")
                elif s not in produced:
                    owner = s.split(".")[0]
                    if owner in seen_steps:
                        errs.append(f"{rel} step {sid}: supply {s}: step {owner} has no result '{s.split('.')[1]}'")
                    else:
                        errs.append(f"{rel} step {sid}: supply {s} is not produced by an EARLIER step")
            t = st.get("tool", {})
            if t.get("code") and t["code"] not in codes:
                errs.append(f"{rel} step {sid}: tool.code {t['code']} not declared")
            if t.get("environment") and t["environment"] not in envs:
                errs.append(f"{rel} step {sid}: tool.environment {t['environment']} not declared")
            for g in st.get("gates", []):
                if g not in gates:
                    errs.append(f"{rel} step {sid}: gate {g} not declared")
            for g in st.get("ranking_criteria", []):
                if g not in ranks:
                    errs.append(f"{rel} step {sid}: ranking criterion {g} not declared")
            if st["kind"] in ("deterministic", "numerical") and not t.get("command"):
                warns.append(f"{rel} step {sid}: no exact command line (tool: {t.get('name')})")
            for r in st["result"]:
                produced.add(f"{sid}.{r['id']}")
            seen_steps.add(sid)
    return seen_steps, nsteps


def open_question_ids():
    f = ROOT / "OPEN_QUESTIONS.md"
    if not f.exists():
        return set()
    return set(re.findall(r"^##+\s+(Q\d+)\b", f.read_text(), flags=re.M))


def main():
    quiet = "--quiet" in sys.argv
    cross = sys.argv[sys.argv.index("--crosscheck") + 1] if "--crosscheck" in sys.argv else None
    V = op.SchemaValidator()
    errs, warns = [], []
    stats = {"docs": 0, "refs": 0, "hash_ok": 0, "remote": 0, "restricted": 0, "steps": 0}
    docs = {}
    oq = open_question_ids()
    for f in documents():
        rel = str(f.relative_to(ROOT))
        try:
            d = op.load_doc(f)
        except Exception as e:  # noqa: BLE001
            errs.append(f"{rel}: cannot parse: {e}"); continue
        docs[rel] = d
        stats["docs"] += 1
        t = d.get("type")
        if t not in SCHEMA_OF:
            errs.append(f"{rel}: unknown type {t!r}"); continue
        for e in V.validate(d, SCHEMA_OF[t]):
            errs.append(f"{rel}: schema: {e}")
        check_refs(d, rel, errs, warns, stats)
        text = f.read_text()
        if HOME_RE.search(text):
            warns.append(f"{rel}: contains an absolute home path ({HOME_RE.search(text).group(0)}...); write ~ instead")
        for q in d.get("open_questions", []) if isinstance(d, dict) else []:
            if q not in oq:
                errs.append(f"{rel}: open question {q} not in OPEN_QUESTIONS.md")
    # cross-document checks
    generals = {f"{d['id']}@{d['version']}": (rel, d) for rel, d in docs.items() if d.get("type") == "general_protocol"}
    specifics = {f"{d['id']}@{d['version']}": (rel, d) for rel, d in docs.items() if d.get("type") == "specific_protocol"}
    gsteps = {}
    for key, (rel, d) in generals.items():
        gsteps[key], n = check_steps(d, rel, errs, warns)
        stats["steps"] += n
    for key, (rel, d) in specifics.items():
        own = set()
        gen = None
        for ins in d.get("instantiates", []):
            g = generals.get(ins["protocol"])
            if g is None:
                errs.append(f"{rel}: instantiates {ins['protocol']}, not found under general/")
                continue
            gen = g[1]
            hg = op.sha256_file(ROOT / g[0])
            if hg != ins["file"]["sha256"] and public_copies().get(f"protocols/{g[0]}") != (ins["file"]["sha256"], hg):
                errs.append(f"{rel}: instantiates {ins['protocol']}: file hash differs from {g[0]}")
        if d.get("sections"):
            own, n = check_steps(d, rel, errs, warns, general=gen)
            stats["steps"] += n
        allsteps = own | set().union(*[gsteps.get(i["protocol"], set()) for i in d.get("instantiates", [])])
        for r in d.get("run_sequence", []):
            if r["step"] not in allsteps:
                errs.append(f"{rel}: run {r['run_id']} executes unknown step {r['step']}")
        ev = d.get("evidence_selection", {})
        if ev.get("digest_source") and ev.get("result_sha256"):
            rc = op.load_doc(ev["digest_source"]["path"])
            refs = [r for r in rc.get("inputs", []) if str(r.get("role", "")).startswith("data file")]
            if op.evidence_digest(refs) != ev["result_sha256"]:
                errs.append(f"{rel}: evidence digest from {ev['digest_source']['path']} does not recompute")
        if ev.get("data_files") and ev.get("result_sha256"):
            if op.evidence_digest(ev["data_files"]) != ev["result_sha256"]:
                errs.append(f"{rel}: evidence digest does not recompute")
        if d.get("artifact", {}).get("produced_by") != key:
            errs.append(f"{rel}: artifact.produced_by should be {key}")
    for rel, d in docs.items():
        if d.get("type") == "run_card":
            ex = d.get("executes", {})
            if ex.get("specific_protocol") not in specifics:
                errs.append(f"{rel}: executes unknown specific protocol {ex.get('specific_protocol')}")
            if ex.get("general_protocol") not in generals:
                errs.append(f"{rel}: executes unknown general protocol {ex.get('general_protocol')}")
            else:
                sp = specifics.get(ex.get("specific_protocol"), (None, {}))[1]
                own = {s["id"] for sec in sp.get("sections", []) or [] for s in sec["steps"]}
                if ex.get("step") not in gsteps[ex["general_protocol"]] | own:
                    errs.append(f"{rel}: executes unknown step {ex.get('step')}")
        if d.get("type") == "assessment_results":
            tr = d.get("trajectory", {})
            n = len(tr.get("parameter_names", []))
            for run in tr.get("runs", []):
                for pt in run["points"]:
                    if "theta" in pt and len(pt["theta"]) != n:
                        errs.append(f"{rel}: trajectory {run['step']}/{run['start']} eval {pt['eval']}: theta length {len(pt['theta'])} != {n}")
                        break
            pr = d.get("projection", {})
            if isinstance(pr, dict) and "basis" in pr:
                if len(pr["basis"]) != n or any(len(r) != 2 for r in pr["basis"]):
                    errs.append(f"{rel}: projection basis is not {n} x 2")
            if d.get("specific_protocol") not in specifics:
                errs.append(f"{rel}: specific_protocol {d.get('specific_protocol')} not found")
    # ORCHID linkage (PI 6 Nov 2026): every evidence state links to ORCHID records/states, or is flagged with a reason and an
    # intake reference; a claimed link must resolve in the local orchid-data-next literature checkout
    stats["links"] = {}
    for rel, d in docs.items():
        if d.get("type") != "specific_protocol":
            continue
        b_ = (d.get("evidence_selection") or {}).get("bundle") or {}
        stp = op.expand(b_["states"]["path"]) if b_.get("states") else None
        if not stp or not stp.exists():
            continue
        S = json.loads(stp.read_text()); cov = S.get("link_coverage") or {}
        chk = op.expand((cov.get("orchid_checkout") or {}).get("path") or localpaths.setting("orchid_data_next"))
        lit = set()
        for f in (chk / "literature/systems").glob("*.json") if chk.exists() else []:
            if any(f.name.startswith(sy) for sy in {d.get("system", "")}):
                try:
                    lit |= {r["id"] for r in json.loads(f.read_text()).get("records", [])}
                except Exception:  # noqa: BLE001
                    pass
        n_present = n_missing = n_provisional = 0
        for i, st in enumerate(S["states"]):
            lk = st.get("orchid_link")
            if lk is None:
                errs.append(f"{rel}: {stp.name} state {i} has no orchid_link"); continue
            if lk == "present":
                n_present += 1
                ok = [l for l in st.get("orchid_links", []) if l["id"] in lit or l.get("state_id")]
                if lit and not ok:
                    errs.append(f"{rel}: {stp.name} state {i} claims ORC ids {st.get('orchid_ids')} that do not resolve in {op.tilde(chk)}")
                for l in st.get("orchid_links", []):
                    if l.get("in_literature_checkout") and lit and l["id"] not in lit:
                        errs.append(f"{rel}: {stp.name} state {i}: {l['id']} marked in_literature_checkout but absent")
            elif lk == "provisional":
                # ids computed offline for data ORCHID has not released (PI 6 Nov 2026): each link carries its locator
                # (pid) in the local:<ORCID>/<uuid> namespace or under a dataset DOI, and the id recomputes from it
                n_provisional += 1
                if not st.get("orchid_links"):
                    errs.append(f"{rel}: {stp.name} state {i} is provisional without orchid_links")
                for l in st.get("orchid_links", []):
                    for e in orchid_ids.check_provisional_link(l):
                        errs.append(f"{rel}: {stp.name} state {i}: provisional link {l.get('id')}: {e}")
            else:
                n_missing += 1
                ir = st.get("intake_ref", "")
                if not st.get("missing_reason") or not ir:
                    errs.append(f"{rel}: {stp.name} state {i} missing link without reason or intake_ref")
                elif not op.expand(ir.split("#")[0]).exists():
                    errs.append(f"{rel}: {stp.name} state {i} intake_ref does not resolve: {ir}")
        stats["links"][d["id"]] = {"present": n_present, "missing_with_reason": n_missing, "provisional": n_provisional, "checkout_records": len(lit)}

    # optional cross-check with PyYAML + jsonschema from another interpreter
    if cross:
        code = r'''
import json, sys, yaml, jsonschema, pathlib
from referencing import Registry, Resource
root = pathlib.Path(sys.argv[1]); out = {}
reg = Registry()
for f in (root / "schema").glob("*.json"):
    s = json.loads(f.read_text()); reg = reg.with_resource(s["$id"], Resource.from_contents(s))
SCH = {"general_protocol": "protocol.schema.json", "specific_protocol": "protocol.schema.json", "run_card": "protocol.schema.json", "assessment_results": "assessment-results.schema.json"}
for rel in sys.argv[2:]:
    f = root / rel
    d = yaml.safe_load(f.read_text()) if f.suffix == ".yaml" else json.loads(f.read_text())
    s = json.loads((root / "schema" / SCH[d["type"]]).read_text())
    v = jsonschema.Draft202012Validator(s, registry=reg)
    out[rel] = {"n_errors": sum(1 for _ in v.iter_errors(d)), "first": [e.message[:160] for e in list(v.iter_errors(d))[:3]],
                "doc": json.loads(json.dumps(d, default=str)) if f.suffix == ".yaml" else None}
print(json.dumps(out))
'''
        rels = list(docs)
        res = subprocess.run([cross, "-I", "-c", code, str(ROOT)] + rels, capture_output=True, text=True)
        if res.returncode != 0:
            errs.append("crosscheck failed to run: " + res.stderr.strip()[-400:])
        else:
            out = json.loads(res.stdout)
            for rel, r in out.items():
                if r["n_errors"]:
                    errs.append(f"{rel}: jsonschema (reference implementation) reports {r['n_errors']} errors: {r['first']}")
                if r["doc"] is not None and json.loads(json.dumps(docs[rel], default=str)) != r["doc"]:
                    errs.append(f"{rel}: yamlmini and PyYAML parse differently")
            stats["crosschecked"] = len(out)
    print("ORCHID protocol validator (orchid-assessment-schema 1.0.0-draft.2)")
    print("documents: %(docs)d | file references: %(refs)d (sha256 verified %(hash_ok)d, remote-record only %(remote)d, restricted by hash %(restricted)d) | steps: %(steps)d" % stats
          + (f" | pinned text resolved to a frozen version: {stats['frozen_version']}" if stats.get("frozen_version") else "")
          + (f" | public copies of pinned originals: {stats['public_copy']}" if stats.get("public_copy") else "")
          + (f" | outside this public copy (pinned by sha256 only): {stats['outside_copy']}" if stats.get("outside_copy") else "")
          + (f" | cross-checked with PyYAML + jsonschema: {stats.get('crosschecked', 0)}" if cross else ""))
    for rel, d in docs.items():
        print(f"  {rel}: {d.get('type')} {d.get('id', '')}@{d.get('version', '')}" if d.get("type") != "assessment_results" else f"  {rel}: assessment_results {d.get('id')}")
    for k, v in stats.get("links", {}).items():
        print(f"  ORCHID links {k}: {v['present']} states linked, {v['missing_with_reason']} flagged missing (reason + intake ref), {v.get('provisional', 0)} provisional (ids recomputed); {v['checkout_records']} records in the local checkout")
    print(f"errors: {len(errs)}")
    for e in errs:
        print("  ERROR", e)
    print(f"warnings: {len(warns)}")
    if not quiet:
        for w in warns:
            print("  warn", w)
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
