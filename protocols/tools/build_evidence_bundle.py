#!/usr/bin/env python3
"""Freeze a pick's evidence as a versioned, hashed bundle in the repo:  assessments/<artifact>/evidence/

  FIT_PYTHON -I protocols/tools/build_evidence_bundle.py cuzr|crni [--registry Y25_OBSERVATIONS.parquet]
  ... build_evidence_bundle.py generic --art NAME --element EL --run-card RUN_CARD.json [--hinge H.json] [--oneshot F] [--pick TDB] [--registry ...]
      (any campaign: the data files are those listed in the run card; the campaign's own run_card.json with data_files works too)

Contents (derived facts only; sources are only read):
  files/<group>/*.json   the exact ESPEI dataset files the pick's objective read, byte-identical (run card data_files)
  hinge/*.json           the hinge (excluded-phase) sidecars, byte-identical
  oneshot/*              the one-shot observations (and liquid S_ex) the fits anchored to
  model_inputs/          start TDB(s), step configs and extra-start vectors needed to rerun the sequence
  states.json            one record per observed state: T, x, expected phases, excluded phases, ORC ids, state ids
                         (Y25 registry), sigma_T / sigma_x and the CERTAINTY TIER of its ZPF/hinge energy scale
  MANIFEST.json          every file: sha256, original path, ORC ids found in it, mapped state ids, release flags
A file with a source-text field (quote, excerpt, ...) longer than 500 characters is not copied (held) and listed, so no
long quote enters the repo; ORCHID-authored comments and notes are kept.

Certainty tiers (PI rule, fit_protocol item 8, 6 Nov 2026; the 3x reading is the coordinator's, PENDING PI confirmation):
  certain       10 J/mol-atom   state more than 3x its own T/x uncertainty from the nearest observed boundary, and no
                                contradicting source at that state
  less_certain  50 J/mol-atom   between 1x and 3x
  uncertain    100 J/mol-atom   on a boundary (tie-line vertices, invariants, <= 1x), diagram-assumed, or conflicting
Distance: d = min over observed boundary points b of sqrt(((T-T_b)/sigma_T)^2 + ((x-x_b)/sigma_x)^2), boundary points =
the known-composition vertices of every two- and three-phase observation in the bundle. Conflict: another observation
within 1 sigma (same metric) whose expected phase set differs. sigma_T, sigma_x: the record's own ORCHID budget when present,
else the ORCHID 2026-10-24 calibration 'unknown' class (T 16 K, x 0.011), as used in crni-paper-fit build_zpf_sigma.py.

Fixes of 7 Nov 2026 (first used for crni-paper-fit-step4c-b bundle 1.1.0; earlier versions stay as built):
  - every ZPF vertex is converted to x(bundle element): x = value if the vertex is given in that element, else 1 - value;
    a vertex of unknown composition stays null and is never filled from another vertex or from the record's composition;
  - exclusion tiers are copied from the hinge sidecar the fit read (cells[].orchid.tiers of each penalised phase), with the
    basis prefixed "tier used by the fit (...)"; the classifier grades only phases for which the sidecar records no tier;
  - a versioned states@V.json is never overwritten with different content; --previous NAME sets the manifest's "previous".
Record fixes of 7 Nov 2026 (crni-paper-fit-step4c-b bundle 1.2.0, for crni-paper-fit-step4c-b@1.0.4; see crni4cb_120): hinge
labels from a relabelled hinge version (observed states), ZPF tiers copied from the fit's build record, <home>/ versions of files with a
home path, the re-recorded modes file, a versioned intake reference. Earlier versions (1.1.0 and before) build exactly as before.
Single source (fit_protocol item 8, PI 7 Nov 2026): only datasets designated single source in the plan before fitting, with
their reason (plan "single_sources"; generic: --single-source MATCH=REASON); the 3-sigma-neighbour reading used until then
(frozen bundles 2.0.0 of cuzr and crni step4-s1) is gone. The classifier runs only where the hinge file records no tier.
"""
import hashlib
import json
import math
import re
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import localpaths  # noqa: E402
import frozen  # noqa: E402

REPO = Path(__file__).resolve().parents[2]; RUNS = localpaths.setting("runs_root")   # campaign directories (local/config.json)
ORC = re.compile(r"ORC-[0-9A-Z]{10}(?:\.[0-9a-f]{6})?")
TIER = {"certain": 10.0, "less_certain": 50.0, "uncertain": 100.0}
SIG_T_DEF, SIG_X_DEF = 16.0, 0.011
RULE = "certainty-tiers@0.1 (fit_protocol item 8, PI 6 Nov 2026; 3x operational reading pending PI confirmation)"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tl(p):
    return localpaths.tilde(p)


SOURCE_TEXT_KEYS = ("quote", "excerpt", "source_text", "printed_text", "caption_text", "raw_text", "text")


def long_strings(o, n=500, key=""):
    """True if a SOURCE-TEXT field (quote, excerpt, ...) is longer than n characters. ORCHID-authored notes and comments
    (provenance descriptions written by us) are not source text and are allowed at any length."""
    if isinstance(o, str):
        return len(o) > n and any(k in key.lower() for k in SOURCE_TEXT_KEYS)
    if isinstance(o, dict):
        return any(long_strings(v, n, k) for k, v in o.items())
    if isinstance(o, list):
        return any(long_strings(v, n, key) for v in o)
    return False


def _version_at_least(v):
    """True when --version is given and >= v (semver compare of the numeric parts)."""
    if "--version" not in sys.argv:
        return False
    num = lambda s: tuple(int(p) for p in s.split("-")[0].split("."))  # noqa: E731
    return num(sys.argv[sys.argv.index("--version") + 1]) >= num(v)


def crni4cb_120(C):
    """Bundle 1.2.0 of crni-paper-fit-step4c-b (7 Nov 2026, crni-paper-fit-step4c-b@1.0.4; record fixes only, every file the fit
    reads unchanged):
      - hinge states take their basis from the relabelled hinge version (evidence/hinge_labels/step4c_hinge_floor@1.1.0.json,
        addendum-1.0.4 relabel_hinge_observed.py): the 366 cells are observed states (observed_state true), not "assumed from a
        diagram (option C)"; the fit-read numbers of that file are checked equal to the hinge file the fit read;
      - ZPF tiers of the 329 ZPF records are COPIED from the fit's input (results/step4c_build.json zpf_rows: tier, sigma_used;
        results/tiers3.json zpf_rows: replicated_by), never re-derived, and each record's fitted weight is checked = 1000/sigma_used;
        hinge states are not ZPF records of the fit and carry no ZPF tier;
      - the two files with a personal home path are replaced by their <home>/ versions (addendum-1.0.4 redact_home_paths.py);
      - the modes file re-recorded under the names of the orchid-calphad-fit@2.1.2 modes command is added;
      - states link to the versioned intake manifest intake_manifest@1.1.0.json."""
    E = REPO / "assessments/crni-paper-fit-step4c-b/evidence"
    return {"hinge_labels": {C / "data/hinge/step4c_hinge_floor.json": E / "hinge_labels/step4c_hinge_floor@1.1.0.json"},
            "zpf_fit_tiers": {"build": C / "results/step4c_build.json", "tiers3": C / "results/tiers3.json"},
            "replace": {"oneshot/oneshot_parameters.json": ("oneshot_redacted/oneshot_parameters@1.1.0.json", E / "oneshot_redacted/oneshot_parameters@1.1.0.json"),
                        "model_inputs/results/data_consistency.json": ("model_inputs_redacted/results/data_consistency@1.1.0.json",
                                                                       E / "model_inputs_redacted/results/data_consistency@1.1.0.json")},
            "extra_references": {"results/uq/modes_step4c_b@1.1.0.json": E / "reference_outputs/results/uq/modes_step4c_b@1.1.0.json"},
            "intake": "assessments/crni-paper-fit-step4c-b/intake/intake_manifest@1.1.0.json"}


def plan(which):
    if which == "generic":
        # FIT_PYTHON -I build_evidence_bundle.py generic --art NAME --element EL --run-card RC.json
        #     [--hinge H.json,...] [--oneshot F,...] [--pick TDB] [--registry Y25.parquet]
        a = sys.argv; g = lambda k, d=None: a[a.index(k) + 1] if k in a else d
        rc = json.loads(Path(g("--run-card")).read_text())
        data = [localpaths.expand(r["path"]) for r in rc["inputs"] if str(r.get("role", "")).startswith("data file")] if "inputs" in rc else \
               [Path(r["path"]) for r in rc.get("data_files", [])]
        return {"art": g("--art"), "element": g("--element"), "system_file": g("--system", ""), "data": {p: p.parent.name for p in data if "/steps/" not in str(p)},
                "hinge": [Path(x) for x in (g("--hinge", "") or "").split(",") if x], "oneshot": [Path(x) for x in (g("--oneshot", "") or "").split(",") if x],
                "model_inputs": {}, "pick_tdb": Path(g("--pick")) if g("--pick") else None, "references": {},
                # --single-source MATCH=REASON (repeatable): datasets designated single source in the plan (fit_protocol item 8)
                "single_sources": [dict(zip(("match", "reason"), v.split("=", 1))) for k, v in zip(a, a[1:]) if k == "--single-source"]}
    if which == "cuzr":
        C = RUNS / "cuzr-protocol-oneshot-20261106"; A = C / "attic/run1_s2value_20261106"
        rc = json.loads((REPO / "protocols/run_cards/cuzr-r1-stepH2_hinge_thermo.json").read_text())
        data = [localpaths.expand(r["path"]) for r in rc["inputs"] if str(r.get("role", "")).startswith("data file")]
        # per-start anchors and thermo_adj copies are generated by fit_step.py at run time; the thermo_adj files are weight-floored
        # copies of work/datasets/thermo/<same name>, so the ORIGINAL thermo file is what the bundle must hold (bug found by the
        # 6 Nov independent rerun: without them the H2 objective lacked the 11 calorimetric HM_FORM files)
        adj = [C / "work/datasets/thermo" / p.name for p in data if "/thermo_adj/" in str(p)]
        data = [p for p in data if "/steps/" not in str(p)] + adj
        groups = {p: p.parent.name for p in data}
        return {"art": "cuzr-oneshot-h2-s7", "element": "ZR", "system_file": "CU-ZR", "data": groups,
                "hinge": [A / "cuzr_cells_from_step2.json"],
                "oneshot": [A / "results/oneshot_observations.json", C / "work/ref/cuzr_excess_entropy_hongliu.json"],
                "model_inputs": {"tdb/step1_oneshot.tdb": A / "tdb/step1_oneshot.tdb", "tdb/CuZr-94Zen-LB.tdb": C / "tdb/CuZr-94Zen-LB.tdb",
                                 "tdb/previous/step1_oneshot_staged20261105.tdb": C / "tdb/previous/step1_oneshot_staged20261105.tdb",
                                 "work/unary_tables_300_3000.npz": C / "work/unary_tables_300_3000.npz",
                                 "work/ref/printed_invariants_paper.json": C / "work/ref/printed_invariants_paper.json",
                                 "work/ref/wang2006_table1_mapped.json": C / "work/ref/wang2006_table1_mapped.json",
                                 "work/datasets/manifest.json": C / "work/datasets/manifest.json",
                                 **{f"steps/configs/{p.name}": p for p in sorted((A / "steps/configs").glob("*.json"))}},
                "pick_tdb": A / "tdb/stepH2_hinge_thermo_PICK_s7.tdb",
                "references": {**{f"tdb/{n}": A / "tdb" / n for n in ("step2_liquidus.tdb", "stepH1_topology_hinge.tdb", "stepH2_hinge_thermo_PICK_s7.tdb")},
                               **{f"steps/{st}/s{k}/result.json": A / f"steps/{st}/s{k}/result.json" for st, k in (("step2_liquidus", 1), ("stepH1_topology_hinge", 1), ("stepH2_hinge_thermo", 7))},
                               **{f"steps/{st}/ranking_protocol.json": A / f"steps/{st}/ranking_protocol.json" for st in ("step2_liquidus", "stepH1_topology_hinge", "stepH2_hinge_thermo")}}}
    if which == "crni4cb":
        # Cr-Ni step-4 pick step4c-b (hinge floor; PI decision 6 Nov 2026): the data files are those of the step-4c-b run card;
        # start = the step-3b pick (steps 1-3b unchanged; their inputs are in the crni-paper-fit-step4-s1 bundle)
        C = RUNS / "crni-paper-fit-20261106"
        rc = json.loads((REPO / "protocols/run_cards/crni-step4c_b_hingefloor.json").read_text())
        data = [localpaths.expand(r["path"]) for r in rc["inputs"] if str(r.get("role", "")).startswith("data file")]
        return {"art": "crni-paper-fit-step4c-b", "element": "NI", "system_file": "CR-NI", "data": {p: p.parent.name for p in data},
                # the one dataset the plan designated single source (scripts/build_tiers3.py; PI 7 Nov 2026: "only Pugliese, as
                # the fit used"); bundle 1.1.0 copies the fit's tiers, so this applies only to phases the hinge file leaves untiered
                "single_sources": [{"match": "pugliese", "reason": "Pugliese & Fitterer: phases from the paper's own Table III limits, the only report of these states (scripts/build_tiers3.py)"}],
                "hinge": [C / "data/hinge/step4c_hinge_floor.json"],
                "oneshot": [C / "results/oneshot_observations.json", C / "results/data_build.json", C / "results/oneshot_parameters.json"],
                "model_inputs": {"tdb/step3b_thermo_crni2free_pick.tdb": C / "tdb/step3b_thermo_crni2free_pick.tdb",
                                 "steps/configs/step4c_b_hingefloor.json": C / "steps/configs/step4c_b_hingefloor.json",
                                 **{f"results/{n}": C / "results" / n for n in ("step4c_build.json", "tiers3.json", "zpf_sigma_conversion.json", "hinge_observed_sigma.json",
                                                                               "step4c_b_hinge_floor.json", "exclusion_audit.json", "data_consistency.json")},
                                 "data/hinge/step4c_hinge.json": C / "data/hinge/step4c_hinge.json",
                                 "cr-ni-coherent/results.json": RUNS / "cr-ni-coherent-20261105/results.json"},
                "pick_tdb": C / "tdb/step4c_b_hingefloor_pick.tdb",
                "references": {"tdb/step4c_b_hingefloor_pick.tdb": C / "tdb/step4c_b_hingefloor_pick.tdb",
                               **{f"steps/step4c_b_hingefloor/{f}": C / f"steps/step4c_b_hingefloor/{f}" for f in ("multistart.json", "evaluation.json", "trajectories_manifest.json")},
                               "results/uq/modes_step4c_b.json": C / "results/uq/modes_step4c_b.json", "results/uq/laplace_step4c_b.json": C / "results/uq/laplace_step4c_b.json",
                               "results/uq/classified_mixture_draws_step4c_b.json": C / "results/uq/classified_mixture_draws_step4c_b.json",
                               "results/physics_step4c_b.json": C / "results/physics_step4c_b.json", "results/per_dataset_step4c_b_hingefloor.json": C / "results/per_dataset_step4c_b_hingefloor.json",
                               "results/step4_tests_comparison.json": C / "results/step4_tests_comparison.json"},
                **(crni4cb_120(C) if _version_at_least("1.2.0") else {})}
    C = RUNS / "crni-paper-fit-20261106"
    rc = json.loads((REPO / "protocols/run_cards/crni-step4_solid.json").read_text())
    data = [localpaths.expand(r["path"]) for r in rc["inputs"] if str(r.get("role", "")).startswith("data file")]
    return {"art": "crni-paper-fit-step4-s1", "element": "NI", "system_file": "CR-NI", "data": {p: p.parent.name for p in data},
            "hinge": [C / "data/hinge/step4_hinge.json"],
            "oneshot": [C / "results/oneshot_observations.json", C / "results/data_build.json", C / "results/oneshot_parameters.json"],
            "model_inputs": {"tdb/step1_oneshot.tdb": C / "tdb/step1_oneshot.tdb", "tdb/step1_oneshot_noSex.tdb": C / "tdb/step1_oneshot_noSex.tdb",
                             **{f"steps/configs/{n}.json": C / f"steps/configs/{n}.json" for n in ("step1_oneshot", "step2_liquidus", "step3_thermo", "step3b_thermo_crni2free", "step4_solid", "extra_step2")},
                             "cr-ni-coherent/results.json": RUNS / "cr-ni-coherent-20261105/results.json"},
            "pick_tdb": C / "tdb/CrNi_paper_fit_FINAL_step4_s1.tdb",
            "references": {**{f"tdb/{n}": C / "tdb" / n for n in ("step2_liquidus_pick.tdb", "step3b_thermo_crni2free_pick.tdb", "step4_solid_pick.tdb")},
                           **{f"steps/{st}/{f}": C / f"steps/{st}/{f}" for st in ("step2_liquidus", "step3b_thermo_crni2free", "step4_solid") for f in ("multistart.json", "evaluation.json")},
                           "results/uq/modes_step4.json": C / "results/uq/modes_step4.json", "results/uq/laplace_step4.json": C / "results/uq/laplace_step4.json",
                           "results/physics_final.json": C / "results/physics_final.json"}}


def vertex_x(v, elem):
    """Mole fraction of the bundle element `elem` at one ESPEI ZPF vertex [phase, [component], [value]] of a binary.
    The vertex gives its composition in the component it names (v[1]); a vertex given in the other component is converted
    (x = 1 - value). An unknown composition (null) stays unknown (None): it is never filled from another vertex or state.
    (Bug in 1.0.0 bundles: v[2][0] was taken raw, so a vertex given in x(CR) was labelled x(NI).)"""
    val = v[2][0] if v[2] else None
    if val is None:
        return None
    comp = [str(c).upper() for c in (v[1] or [])]
    if comp == [elem.upper()]:
        return float(val)
    if len(comp) == 1:
        return round(1.0 - float(val), 12)   # 1 - 0.912 -> 0.088, not 0.08799999999999997
    raise ValueError(f"ZPF vertex {v!r}: expected one component, cannot convert to x({elem})")


def states_from_zpf(d, fname, group, elem):
    out = []
    T = d["conditions"]["T"]; T = T if isinstance(T, list) else [T]
    vals = d["values"]
    if len(T) == 1 and len(vals) > 1:
        T = T * len(vals)
    obs = (d.get("orchid") or {}).get("observations") or []
    unc = (d.get("orchid_uncertainty") or {}).get("values") or []
    file_ids = sorted(set(ORC.findall(json.dumps(d)) + ORC.findall(fname)))
    for i, (t, reg) in enumerate(zip(T, vals)):
        verts = [[v[0], vertex_x(v, elem)] for v in reg if v[0] != "__HYPERPLANE__"]
        hyp = [x for x in (vertex_x(v, elem) for v in reg if v[0] == "__HYPERPLANE__") if x is not None]
        known = [vx for _, vx in verts if vx is not None]
        x = (sum(hyp) / len(hyp)) if hyp else (sum(known) / len(known) if known else None)
        rid = [obs[i]["id"]] if i < len(obs) and isinstance(obs[i], dict) and obs[i].get("id") else file_ids
        sT, sx = SIG_T_DEF, SIG_X_DEF; basis = "ORCHID calibration 2026-10-24 'unknown' class defaults"
        if i < len(unc):
            b = unc[i].get("budget", {})
            try:
                sT = float(b["temperature_K"]["sigma_effective"]) or sT; basis = "record's own uncertainty_budget"
            except Exception:
                pass
            try:
                sx = float(b["composition_mole_fraction"]["sigma_effective"]) or sx
            except Exception:
                pass
        kind = "single_phase" if len(verts) == 1 else ("partial_tie_line" if len(known) < len(verts) else ("tie_line" if len(verts) == 2 else f"{len(verts)}-phase"))
        out.append({"source_file": f"{group}/{fname}", "row": i, "kind": kind, "T_K": float(t), "x": x, "element": elem,
                    "expected": sorted(v[0] for v in verts), "vertices": verts,
                    "orchid_ids": rid, "sigma_T_K": sT, "sigma_x": sx, "sigma_basis": basis, "evidence_class": "assessed" if "assessed" in fname else ("derived" if "derived" in fname else "experimental"),
                    "reference": str(d.get("reference", ""))[:200]})
    return out


RULE2 = "certainty-tiers@2 (fit_protocol item 8, PI 6 Nov 2026: tiers per excluded phase; ZPF 100 / 50 replicated)"
# from bundle 1.1.0 of crni-paper-fit-step4c-b (7 Nov 2026): exclusion tiers are those the fit read from its hinge sidecar
RULE3 = RULE2[:-1] + "; exclusion tiers copied from the hinge sidecar the fit read when it records them, else classified)"


# from bundle 1.2.0 of crni-paper-fit-step4c-b (7 Nov 2026): ZPF tiers copied from the fit's input too
RULE4 = RULE3[:-1] + "; ZPF tiers copied from the fit's build record (step4c_build.json / tiers3.json zpf_rows), never re-derived)"


def copy_zpf_tiers(states, src, root):
    """ZPF tier of every ZPF record = the tier the fit used, copied from its build record (crni step4c: results/step4c_build.json
    zpf_rows gives file, row, tier, sigma_conv, sigma_used = max(sigma_conv, tier), weight = 1000/sigma_used, floor_active and
    suspended_CRNI2; results/tiers3.json zpf_rows gives replicated_by). Bundle file <g>_c/<stem>__rNNN.json (or zpf_susp/...) is row
    NNN of <g>/<stem>.json. The weight of the bundle's copy of the data file must equal 1000/sigma_used (exact), or the bundle is
    not built. States that are not ZPF records of the fit (hinge cells) carry no ZPF tier."""
    import re as _re
    b = json.loads(Path(src["build"]).read_text()); t3 = json.loads(Path(src["tiers3"]).read_text())
    rows = {(r["file"], int(r["row"])): r for r in b["zpf_rows"]}
    rep = {(z["file"], int(z["row"])): z for z in t3["zpf_rows"]}
    susp = {}
    for (f, i), r in rows.items():
        if r.get("suspended_CRNI2"):
            susp.setdefault((Path(f).stem, i), []).append((f, i))
    for s in states:
        if s.get("source") != "zpf":
            s["zpf_certainty"] = {"certainty_tier": None, "energy_scale_J_per_mol_atom": None,
                                  "certainty_basis": "not a ZPF record of the fit: the objective reads this state as a hinge cell (excluded phases only; see exclusions)"}
            continue
        g, name = s["source_file"].split("/", 1)
        m = _re.fullmatch(r"(.+)__r(\d{3})\.json", name)
        if not m:
            raise SystemExit(f"ZPF file {s['source_file']}: not a per-row file of the fit build")
        stem, i = m.group(1), int(m.group(2))
        if g == "zpf_susp":
            k = susp.get((stem, i)) or []
            if len(k) != 1:
                raise SystemExit(f"{s['source_file']}: {len(k)} suspended build rows match")
            key = k[0]
        else:
            key = (f"{g[:-2] if g.endswith('_c') else g}/{stem}.json", i)
        r, z = rows.get(key), rep.get(key)
        if r is None or z is None or r["tier"] != z["tier"]:
            raise SystemExit(f"{s['source_file']}: no build/tiers3 row {key} or the two disagree")
        w = json.loads((root / "files" / s["source_file"]).read_text()).get("weight")
        if w != 1000.0 / r["sigma_used"]:
            raise SystemExit(f"{s['source_file']}: fitted weight {w} != 1000/sigma_used {1000.0 / r['sigma_used']}")
        s["zpf_certainty"] = {"certainty_tier": r["tier"], "energy_scale_J_per_mol_atom": TIER[r["tier"]],
                              "sigma_DF_used_J_per_mol_atom": r["sigma_used"], "sigma_DF_converted_J_per_mol_atom": r["sigma_conv"],
                              "tier_floor_active": r["floor_active"], "fitted_weight": w, "replicated_by": z.get("replicated_by", []),
                              "suspended_CRNI2": r.get("suspended_CRNI2", False),
                              "certainty_basis": f"tier used by the fit (results/step4c_build.json zpf_rows {key[0]}#{key[1]}; results/tiers3.json zpf_rows)"}
        s["certainty_rule"] = RULE4
    return states


def _d(s, t, x):
    return math.hypot((s["T_K"] - t) / s["sigma_T_K"], (s["x"] - x) / s["sigma_x"])


def single_source_reason(s, single_sources):
    """The plan's reason when the state belongs to a dataset designated single source, else None (fit_protocol item 8,
    PI 7 Nov 2026: single source = the only report of that measurement, designated so in the plan before fitting, with its
    reason; no automatic rule). A designation is {"match": text, "reason": text}; it applies when `match` occurs (case
    ignored) in the state's reference or source file."""
    for d in single_sources or []:
        m, why = str(d.get("match") or "").lower(), str(d.get("reason") or "").strip()
        if not m or not why:
            raise ValueError(f"single-source designation {d!r}: needs a non-empty match and its reason (fit_protocol item 8)")
        if m in str(s.get("reference") or "").lower() or m in str(s.get("source_file") or "").lower():
            return why
    return None


def classify(states, single_sources=None):
    """PI rule of 6 Nov (fit_protocol item 8), per EXCLUDED PHASE, not per state.
    Exclusions: for each phase p excluded at a state, d_p = distance (in the state's own sigma_T, sigma_x) to the nearest
    observed field or boundary point of p (any state whose expected assemblage contains p; at p's own vertex composition
    when known). 100 J/mol-atom when d_p <= 1 (adjacent), when the exclusion is assumed from a diagram (the state is an
    assessed-diagram point) or contested (a state within 1 sigma reports p); 50 when 1 < d_p <= 3 or when the state belongs
    to a dataset designated single source in the plan (`single_sources`, see single_source_reason; PI 7 Nov 2026: no
    automatic rule - until 7 Nov this read "no other independent source has a state within 3 sigma without p"); 10
    otherwise.
    ZPF (driving-force scale of the phases present): 100 for boundary and tie-line records (two or more phases, or a
    single-phase vertex of a partial tie line); 50 when an independent source reports the same boundary point within its
    uncertainty (same phase set, |dT| <= sigma_T and |dx| <= sigma_x). Single-phase field states (no tie line) are not
    boundary records: graded by the distance to the nearest observed boundary of their own phase (> 3 sigma: 10; 1-3: 50;
    <= 1: 100), assessed-diagram points never below 50."""
    def src(s):
        return s.get("reference") or s["source_file"]
    field = {}
    for s in states:
        for p in s.get("expected", []):
            v = dict(s.get("vertices", []) or [])
            # a phase's own vertex composition when known; the state's composition only for a single-phase state (where it is
            # the phase's composition); an unknown vertex of a multi-phase record is not placed anywhere (1.0.0 bug: it was
            # placed at the record's other composition)
            xv = v.get(p) if v.get(p) is not None else (s.get("x") if len(s.get("expected", [])) == 1 else None)
            if xv is not None:
                field.setdefault(p, []).append((s["T_K"], xv, s))
    bnd = {}
    for s in states:
        if len(s.get("expected", [])) >= 2 or s.get("kind") == "partial_tie_line":
            for p, xv in s.get("vertices", []):
                if xv is not None:
                    bnd.setdefault(p, []).append((s["T_K"], xv))
    for s in states:
        s.pop("certainty_tier", None); s.pop("energy_scale_J_per_mol_atom", None); s.pop("certainty_basis", None); s.pop("distance_to_boundary_sigma", None)
        s["certainty_rule"] = RULE3 if s.get("_fit_tiers") else RULE2
        fit_tiers, fit_src = s.pop("_fit_tiers", None) or {}, s.pop("_fit_tiers_src", "")
        if s.get("x") is None:
            s["zpf_certainty"] = {"certainty_tier": "uncertain", "energy_scale_J_per_mol_atom": 100, "certainty_basis": "no composition"}
            continue
        assessed = "assessed" in s["source_file"] or s.get("evidence_class") == "assessed"
        # ZPF tier of the phases present
        if len(s["expected"]) >= 2 or s.get("kind") == "partial_tie_line":
            rep = [o for o in states if o is not s and o["expected"] == s["expected"] and o.get("x") is not None and src(o) != src(s)
                   and abs(o["T_K"] - s["T_K"]) <= s["sigma_T_K"] and abs(o["x"] - s["x"]) <= s["sigma_x"]]
            s["zpf_certainty"] = ({"certainty_tier": "less_certain", "energy_scale_J_per_mol_atom": 50, "certainty_basis": f"boundary record replicated by {len({src(o) for o in rep})} independent source(s) within its uncertainty"}
                                  if rep else {"certainty_tier": "uncertain", "energy_scale_J_per_mol_atom": 100, "certainty_basis": "boundary or tie-line record"})
        else:
            p = s["expected"][0]
            dd = min((_d(s, t, xv) for t, xv in bnd.get(p, [])), default=float("inf"))
            tier = "uncertain" if dd <= 1 else ("less_certain" if dd <= 3 else "certain")
            if assessed and tier == "certain":
                tier = "less_certain"
            s["zpf_certainty"] = {"certainty_tier": tier, "energy_scale_J_per_mol_atom": TIER[tier], "distance_sigma": None if dd == float("inf") else round(dd, 3),
                                  "certainty_basis": (f"single-phase field state, nearest observed boundary of {p} at {dd:.2f} sigma" if dd != float("inf") else f"single-phase field state; no observed boundary of {p}") + ("; assessed-diagram point (never below 50)" if assessed else "")}
        # exclusions, per phase. When the hinge sidecar the fit read carries a tier for the phase (cells[].orchid.tiers), that
        # tier IS the one the objective used: it is copied, never re-derived (1.0.0 bug: the bundle re-classified and missed
        # the PI caveats and the coordinator's single-source rule of the fit). The classifier below is used only for phases
        # without a recorded tier (hinge files that predate per-phase tiers).
        ex = []
        for p in s.get("excluded") or []:
            ft = fit_tiers.get(p)
            if ft is not None:
                tier = ft["tier"]
                ex.append({"phase": p, "certainty_tier": tier, "energy_scale_J_per_mol_atom": TIER[tier],
                           "certainty_basis": f"tier used by the fit ({fit_src}): {ft.get('basis', 'no basis recorded')}",
                           "distance_sigma": None if ft.get("distance_sigma") is None else round(float(ft["distance_sigma"]), 3)})
                continue
            pts = field.get(p, [])
            dp = min((_d(s, t, xv) for t, xv, _ in pts), default=float("inf"))
            contested = any(_d(s, t, xv) <= 1.0 for t, xv, o in pts)
            single = single_source_reason(s, single_sources)
            if assessed or contested or dp <= 1.0:
                tier, why = "uncertain", ("assumed from an assessed diagram" if assessed else ("contested: a state within 1 sigma reports " + p if contested else f"adjacent to the {p} field ({dp:.2f} sigma)"))
            elif dp <= 3.0 or single:
                tier, why = "less_certain", (f"within 3 sigma of the {p} field ({dp:.2f})" if dp <= 3.0 else
                                             f"{p} field {'not observed' if dp == float('inf') else f'{dp:.2f} sigma away'}; single source (designated in the plan: {single})")
            else:
                tier, why = "certain", f"{p} field {'not observed' if dp == float('inf') else f'{dp:.2f} sigma away'}"
            ex.append({"phase": p, "certainty_tier": tier, "energy_scale_J_per_mol_atom": TIER[tier], "certainty_basis": why,
                       "distance_sigma": None if dp == float("inf") else round(dp, 3)})
        if ex:
            s["exclusions"] = ex
    return states


def main():
    which = sys.argv[1]
    reg = sys.argv[sys.argv.index("--registry") + 1] if "--registry" in sys.argv else None
    VERSION = sys.argv[sys.argv.index("--version") + 1] if "--version" in sys.argv else None   # new version -> states@V.json, MANIFEST@V.json
    sfx = f"@{VERSION}" if VERSION else ""
    P = plan(which); root = REPO / "assessments" / P["art"] / "evidence"
    root.mkdir(parents=True, exist_ok=True)
    man, held, states = [], [], []

    def put(src, rel, kind):
        rep = (P.get("replace") or {}).get(rel)
        if rep is not None:   # a new version of this file (1.2.0: home paths written as <home>/); the original stays in older bundles
            orig_rel, (rel, src) = rel, rep
        src = Path(src); d = root / rel
        try:
            obj = json.loads(src.read_text()) if src.suffix == ".json" else None
        except Exception:
            obj = None
        if obj is not None and long_strings(obj):
            held.append({"original": tl(src), "reason": "contains a source-text field longer than 500 characters"}); return None
        d.parent.mkdir(parents=True, exist_ok=True)
        if d.exists() and sha(d) != sha(src):
            raise SystemExit(f"FROZEN: {d} differs from its source {src}; a bundle is never overwritten (bump the bundle version instead)")
        if not d.exists():
            shutil.copy2(src, d)
        txt = d.read_text(errors="ignore") if d.suffix in (".json", ".tdb") else ""
        man.append({"path": rel, "sha256": sha(d), "original": tl(src), "kind": kind, "orchid_ids": sorted(set(ORC.findall(txt) + ORC.findall(src.name)))})
        if rep is not None:
            man[-1]["replaces"] = orig_rel
        return obj
    for src, g in sorted(P["data"].items()):
        obj = put(src, f"files/{g}/{src.name}", "espei_dataset")
        if obj is not None and obj.get("output") == "ZPF":
            for s in states_from_zpf(obj, src.name, g, P["element"]):
                s["source"] = "zpf"; states.append(s)
    for h in P["hinge"]:
        obj = put(h, f"hinge/{h.name}", "hinge_sidecar")
        lab_f = (P.get("hinge_labels") or {}).get(h)
        lab = None
        if lab_f is not None:
            # 1.2.0: labels (basis, observed_state, second_reading) from the relabelled version of the same hinge file; its
            # fit-read keys must equal those of the file the fit read, cell by cell
            lab = put(lab_f, f"hinge_labels/{Path(lab_f).name}", "hinge_labels")
            fk = ("T", "x", "expected", "sigma", "tie_line", "confidence", "penalize")
            if len(lab["cells"]) != len(obj["cells"]) or any({k: a.get(k) for k in fk} != {k: b.get(k) for k in fk} or
                                                              (a.get("orchid") or {}).get("tiers") != (b.get("orchid") or {}).get("tiers")
                                                              for a, b in zip(obj["cells"], lab["cells"])):
                raise SystemExit(f"{lab_f}: fit-read keys differ from {h}; labels not applied (nothing written)")
        for i, c in enumerate((obj or {}).get("cells", [])):
            o = c.get("orchid", {}) or {}
            ol = (lab["cells"][i].get("orchid") or {}) if lab is not None else {}
            if lab is not None:
                basis = str(ol.get("basis", ""))
                observed = bool(ol.get("observed_state"))
            else:
                basis = str(o.get("basis", "")) + (" option C confidence %s" % c.get("confidence") if c.get("confidence") not in (None, 1, 1.0) else "")
                observed = not ("assumed" in basis.lower() or "option c" in basis.lower())
            states.append({"source": "hinge", "source_file": f"hinge/{h.name}", "row": i, "kind": "single_phase" if len(c["expected"]) == 1 else "tie_line",
                           "T_K": float(c["T"]), "x": float(c["x"]), "element": P["element"], "expected": sorted(c["expected"]), "excluded": sorted(c.get("penalize", [])),
                           "vertices": [[k, v] for k, v in (c.get("tie_line") or {}).items()],
                           # structured id fields only (record / observation_id), never ids quoted inside notes
                           "orchid_ids": sorted({str(o[k]) for k in ("record", "observation_id") if o.get(k) and ORC.fullmatch(str(o[k]))}),
                           "sigma_T_K": float(o.get("sigma_T_K", SIG_T_DEF) or SIG_T_DEF), "sigma_x": float(o.get("sigma_x", SIG_X_DEF) or SIG_X_DEF),
                           "sigma_basis": "record's own sigma" if o.get("sigma_T_K") else "ORCHID calibration 'unknown' class defaults",
                           "exclusion_basis": basis or "not stated", "observed_state": observed, "hinge_sigma_used": c.get("sigma"), "confidence_used": c.get("confidence", 1),
                           "reference": str(o.get("reference") or o.get("dataset") or "")[:200], "evidence_class": "assessed" if "assessed" in str(o.get("dataset", "")) + str(o.get("reference", "")) else "experimental",
                           # the per-phase tiers the fit read (consumed by classify(), not written): only for penalised phases
                           "_fit_tiers": {p: t for p, t in (o.get("tiers") or {}).items() if p in c.get("penalize", [])},
                           "_fit_tiers_src": f"hinge/{h.name} cells[{i}].orchid.tiers"})
            if lab is not None:
                states[-1].update({"exclusion_basis_label_file": f"hinge_labels/{Path(lab_f).name} cells[{i}]",
                                   "exclusion_basis_superseded": ol.get("basis_superseded")})
                if ol.get("phase_assignment"):
                    states[-1]["phase_assignment"] = ol["phase_assignment"]
                if ol.get("second_reading"):
                    states[-1]["second_reading"] = ol["second_reading"]
    for f in P["oneshot"]:
        put(f, f"oneshot/{Path(f).name}", "oneshot_observations")
    for rel, f in P["model_inputs"].items():
        put(f, f"model_inputs/{rel}", "model_input")
    if P.get("pick_tdb"):
        put(P["pick_tdb"], f"artifact/{Path(P['pick_tdb']).name}", "artifact")
    for rel, f in P.get("references", {}).items():
        put(f, f"reference_outputs/{rel}", "reference_output")
    for rel, f in P.get("extra_references", {}).items():
        put(f, f"reference_outputs/{rel}", "reference_output")
    se = root / f"states_evaluated{sfx}.json" if VERSION else root / "states_evaluated.json"
    if se.exists():
        man.append({"path": se.name, "sha256": sha(se), "original": "protocols/tools/evaluate_states.py on the pick TDB", "kind": "states_evaluated", "orchid_ids": []})
    classify(states, P.get("single_sources"))
    if P.get("zpf_fit_tiers"):
        copy_zpf_tiers(states, P["zpf_fit_tiers"], root)
    # state ids from the Y25 registry
    sid = {}
    if reg:
        import pyarrow.parquet as pq
        t = pq.read_table(reg, columns=["observation_id", "state_id", "state_class_id", "in_release", "accepted"]).to_pylist()
        want = {i for s in states for i in s["orchid_ids"]} | {i for m in man for i in m["orchid_ids"]}
        base = {}
        for r in t:
            b = r["observation_id"].split(".")[0]
            if r["observation_id"] in want or b in want:
                sid[r["observation_id"]] = r; base.setdefault(b, r)
        for s in states:
            m = [sid.get(i) or base.get(i.split(".")[0]) for i in s["orchid_ids"]]
            s["state_ids"] = sorted({r["state_id"] for r in m if r}); s["state_class_ids"] = sorted({r["state_class_id"] for r in m if r})
            s["in_release"] = sorted({bool(r["in_release"]) for r in m if r})
        for mm in man:
            rs = [sid.get(i) or base.get(i.split(".")[0]) for i in mm["orchid_ids"]]
            mm["state_ids"] = sorted({r["state_id"] for r in rs if r}); mm["unmapped_orchid_ids"] = [i for i, r in zip(mm["orchid_ids"], rs) if not r]
            mm["all_in_release"] = all(bool(r["in_release"]) for r in rs if r) if any(rs) else None
    # ORCHID linkage (PI 6 Nov 2026): every evidence item links to its ORCHID records and states, or says why it cannot
    ORCH = Path(sys.argv[sys.argv.index("--orchid") + 1]).expanduser() if "--orchid" in sys.argv else None
    lit = {}
    if ORCH is not None:
        import glob as _g
        for f in sorted(_g.glob(str(ORCH / "literature/systems" / (P["system_file"] + "*.json")))):
            for r in json.loads(Path(f).read_text()).get("records", []):
                lit[r["id"]] = {"id": r["id"], "pid": r.get("pid"), "paper_id": r.get("paper_id"), "locator": r.get("locator"),
                                "file": "literature/systems/" + Path(f).name}
    intake = P.get("intake") or f"assessments/{P['art']}/intake/intake_manifest.json"
    def links_for(ids):
        out = []
        for i in ids:
            b = i.split(".")[0]; L = dict(lit.get(b) or {"id": b})
            r = sid.get(i) or (sid.get(b) if b in sid else None) or next((v for k, v in sid.items() if k.split(".")[0] == b), None)
            L.update({"observation_id": i, "state_id": r["state_id"] if r else None, "state_class_id": r["state_class_id"] if r else None,
                      "in_release": bool(r["in_release"]) if r else False, "in_literature_checkout": b in lit})
            out.append(L)
        return out
    for s in states:
        L = links_for(s.get("orchid_ids", []))
        s["orchid_links"] = L
        resolved = [l for l in L if l["in_literature_checkout"] or l["state_id"]]
        if resolved:
            s["orchid_link"] = "present"
            s["orchid_release"] = "v2026.10" if all(l["in_release"] for l in resolved) else "unreleased"
        else:
            s["orchid_link"] = "missing"
            s["orchid_release"] = "unreleased"
            if L:
                s["missing_reason"] = "new extraction pending intake (ORC id not in the local registry or literature checkout)"
                s["intake_ref"] = intake + "#items.orc_ids_not_in_registry"
            elif s.get("source") == "hinge":
                s["missing_reason"] = "exclusion added by the campaign"
                s["intake_ref"] = intake + "#items.campaign_added_exclusions"
            else:
                s["missing_reason"] = "dataset without row-level ORC ids (ESPEI-format data; pending intake)"
                s["intake_ref"] = intake + "#items.datasets_without_orchid_ids/" + s["source_file"].split("/")[-1]
    for mm in man:
        if mm["kind"] == "oneshot_observations":
            mm.update(orchid_link="missing", missing_reason="computed one-shot observation (produced_by the specific protocol)", intake_ref=intake + "#items.computed_observations")
        elif mm["kind"] in ("espei_dataset", "hinge_sidecar"):
            res_ = [i for i in mm["orchid_ids"] if i.split(".")[0] in lit or i in sid or i.split(".")[0] in {k.split(".")[0] for k in sid}]
            mm["orchid_link"] = "present" if res_ else "missing"
            if not res_:
                mm["missing_reason"] = ("exclusions added by the campaign" if mm["kind"] == "hinge_sidecar" else
                                        ("new extraction pending intake" if mm["orchid_ids"] else "dataset without row-level ORC ids (pending intake)"))
                mm["intake_ref"] = intake + ("#items.campaign_added_exclusions" if mm["kind"] == "hinge_sidecar" else "#items.datasets_without_orchid_ids/" + mm["path"].split("/")[-1])
    link_cov = {"states_with_link": sum(1 for s in states if s.get("orchid_link") == "present"), "states_missing": sum(1 for s in states if s.get("orchid_link") == "missing"),
                "missing_by_reason": {}, "orc_ids_resolved": len({l["id"] for s in states for l in s.get("orchid_links", []) if l["in_literature_checkout"] or l["state_id"]}),
                "orc_ids_unresolved": len({l["id"] for s in states for l in s.get("orchid_links", []) if not (l["in_literature_checkout"] or l["state_id"])}),
                "files_with_link": sum(1 for m in man if m.get("orchid_link") == "present"), "files_missing": sum(1 for m in man if m.get("orchid_link") == "missing"),
                "orchid_checkout": {"path": localpaths.tilde(localpaths.setting("orchid_data_next")), "commit": None}}
    for s in states:
        if s.get("orchid_link") == "missing":
            link_cov["missing_by_reason"][s["missing_reason"]] = link_cov["missing_by_reason"].get(s["missing_reason"], 0) + 1
    if ORCH is not None:
        import subprocess as _sp
        link_cov["orchid_checkout"]["commit"] = _sp.run(["git", "-C", str(ORCH), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip() or None
    if VERSION:
        tiers = {"zpf": {k: sum(1 for s in states if s.get("zpf_certainty", {}).get("certainty_tier") == k) for k in TIER},
                 "exclusions": {k: sum(1 for s in states for e in s.get("exclusions", []) if e["certainty_tier"] == k) for k in TIER}}
        if P.get("zpf_fit_tiers"):
            tiers["zpf"]["not_a_zpf_record"] = sum(1 for s in states if s.get("zpf_certainty", {}).get("certainty_tier") is None)
            tiers["observed_hinge_states"] = sum(1 for s in states if s.get("source") == "hinge" and s.get("observed_state"))
        rule = RULE4 if P.get("zpf_fit_tiers") else (RULE3 if any(str(s.get("certainty_rule")) == RULE3 for s in states) else RULE2)
    else:
        tiers = {k: sum(1 for s in states if s.get("certainty_tier") == k) for k in TIER}; rule = RULE
    sp = root / f"states{sfx}.json"
    if sp.exists() and VERSION is None and sha(sp) != hashlib.sha256(json.dumps({"artifact": P["art"], "certainty_rule": rule, "tier_energy_J_per_mol_atom": TIER, "counts": tiers, "n_states": len(states), "states": states}, indent=1).encode()).hexdigest():
        raise SystemExit("FROZEN: states.json of version 1 would change; build a new version with --version")
    txt = json.dumps({"artifact": P["art"], "certainty_rule": rule, "tier_energy_J_per_mol_atom": TIER, "counts": tiers, "link_coverage": link_cov, "n_states": len(states), "states": states}, indent=1)
    if sp.exists() and sp.read_text() != txt:
        # a versioned states file is frozen too (states_evaluated@V and the specific protocol pin its sha256)
        raise SystemExit(f"FROZEN: {sp.name} would change; build a new version with --version (nothing written)")
    frozen.write(sp, txt, "build_evidence_bundle.py")   # refuses a frozen file
    man.append({"path": sp.name, "sha256": sha(sp), "original": "derived by build_evidence_bundle.py", "kind": "states", "orchid_ids": []})
    mp = root / f"MANIFEST{sfx}.json"
    old = json.loads(mp.read_text()) if mp.exists() else {}
    bundle = {"bundle": f"{P['art']}-evidence", "version": VERSION or ("1.1.0" if P["art"].startswith("cuzr") else "1.0.0"),
              "previous": (sys.argv[sys.argv.index("--previous") + 1] if "--previous" in sys.argv else "MANIFEST.json (1.x: per-state tiers, superseded by the per-excluded-phase rule)") if VERSION else None, "created": old.get("created", time.strftime("%Y-%m-%dT%H:%M:%S%z")), "builder": "protocols/tools/build_evidence_bundle.py",
              "registry": {"path": "orchid-data-next branch Y25/state-ids-locator graph/observations.parquet", "sha256": sha(reg) if reg else None},
              "rule": "derived facts only; byte-identical copies; files with strings > 500 characters held", "files": man, "held": held,
              "counts": {"files": len(man), "states": len(states), "tiers": tiers, "orchid_ids": len({i for m in man for i in m["orchid_ids"]})}, "link_coverage": link_cov}
    lines = sorted(f"{m['sha256']}  {m['path']}" for m in man)
    bundle["bundle_sha256"] = hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest()
    frozen.write(mp, json.dumps(bundle, indent=1), "build_evidence_bundle.py")   # refuses a frozen file
    print(P["art"], bundle["version"], json.dumps(bundle["counts"]), "held", len(held), "bundle", bundle["bundle_sha256"][:16])


if __name__ == "__main__":
    main()
