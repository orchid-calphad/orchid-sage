#!/usr/bin/env python3
"""Extract the assessment-results document (dashboard data) of a pick from its campaign files. Standard library only.

  python3 tools/extract_dashboard_data.py cuzr|crni OUT.json

Rules: nothing is recomputed. Values are copied from the campaign's own result files; the only arithmetic is unit
bookkeeping (shift / sigma from two numbers on disk, nearest printed value = T_model - dT_nearest) and the 2-D projection
of the parameter vectors, which is deterministic and documented in the output (`projection`). A quantity that is not on
disk is written as {"status": "pending", "reason": ...}. A start whose per-evaluation history was not saved gets only its
start and end points, `recorded: false` ("trajectory not recorded"); nothing is interpolated.
Trajectory thinning for display: at most MAXPTS points per start are embedded (every k-th evaluation plus the first, the
best and the last); the full trace is referenced by sha256 in `source`.
"""
import json
import math
import os
import re
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orchidproto as op  # noqa: E402

H = Path.home()
MAXPTS = 240
PENDING = lambda r: {"status": "pending", "reason": r}  # noqa: E731


def ref(p, role=None, storage="local"):
    p = Path(p)
    r = {"path": op.tilde(p), "sha256": op.sha256_file(p), "storage_class": storage}
    if role:
        r["role"] = role
    return r


def rd(p):
    return json.loads(Path(p).read_text())


def r6(x):
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return None if x is None else (float(f"{x:.6g}") if isinstance(x, float) else x)


def finite(o):
    """JSON has no NaN/Infinity: a non-finite number on disk is written as null (and counted)."""
    if isinstance(o, float) and not math.isfinite(o):
        finite.n += 1
        return None
    if isinstance(o, dict):
        return {k: finite(v) for k, v in o.items()}
    if isinstance(o, list):
        return [finite(v) for v in o]
    return o


finite.n = 0


# ---------------------------------------------------------------- deterministic PCA (Jacobi eigenvalue algorithm)
def jacobi_eig(A, tol=1e-12, maxit=200):
    n = len(A)
    a = [row[:] for row in A]
    V = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for _ in range(maxit):
        off = sum(a[i][j] ** 2 for i in range(n) for j in range(n) if i != j)
        if off < tol:
            break
        for p in range(n):
            for q in range(p + 1, n):
                if abs(a[p][q]) < 1e-300:
                    continue
                th = (a[q][q] - a[p][p]) / (2 * a[p][q])
                t = (1 if th >= 0 else -1) / (abs(th) + math.sqrt(th * th + 1))
                c = 1 / math.sqrt(t * t + 1); s = t * c
                for k in range(n):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p] = c * akp - s * akq; a[k][q] = s * akp + c * akq
                for k in range(n):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k] = c * apk - s * aqk; a[q][k] = s * apk + c * aqk
                for k in range(n):
                    vkp, vkq = V[k][p], V[k][q]
                    V[k][p] = c * vkp - s * vkq; V[k][q] = s * vkp + c * vkq
    w = [a[i][i] for i in range(n)]
    order = sorted(range(n), key=lambda i: -w[i])
    return [w[i] for i in order], [[V[k][i] for k in range(n)] for i in order]


def pca2(vectors, scale):
    d = len(scale)
    Z = [[v[i] / scale[i] for i in range(d)] for v in vectors]
    n = len(Z)
    mu = [sum(z[i] for z in Z) / n for i in range(d)]
    C = [[0.0] * d for _ in range(d)]
    for z in Z:
        c = [z[i] - mu[i] for i in range(d)]
        for i in range(d):
            ci = c[i]
            if ci == 0.0:
                continue
            row = C[i]
            for j in range(i, d):
                row[j] += ci * c[j]
    for i in range(d):
        for j in range(i, d):
            C[i][j] /= max(n - 1, 1); C[j][i] = C[i][j]
    w, vecs = jacobi_eig(C)
    basis = []
    for v in vecs[:2]:
        k = max(range(d), key=lambda i: abs(v[i]))
        basis.append([x if v[k] > 0 else -x for x in v])
    tot = sum(max(x, 0) for x in w) or 1.0
    return {"center": [r6(m * s) for m, s in zip(mu, scale)], "center_scaled": mu,
            "basis": [[r6(basis[0][i]), r6(basis[1][i])] for i in range(d)], "_b": basis,
            "explained": [r6(max(w[0], 0) / tot), r6(max(w[1], 0) / tot)]}


def project(theta, P, scale):
    z = [theta[i] / scale[i] - P["center_scaled"][i] for i in range(len(scale))]
    return [r6(sum(z[i] * P["_b"][0][i] for i in range(len(z)))), r6(sum(z[i] * P["_b"][1][i] for i in range(len(z))))]


def thin(points):
    if len(points) <= MAXPTS:
        return points
    k = math.ceil(len(points) / MAXPTS)
    best = max(range(len(points)), key=lambda i: points[i]["objective"] if points[i]["objective"] is not None else -1e300)
    keep = sorted(set(range(0, len(points), k)) | {0, best, len(points) - 1})
    return [points[i] for i in keep]


def read_npy(p):
    b = Path(p).read_bytes()
    assert b[:6] == b"\x93NUMPY"
    hl = struct.unpack("<H", b[8:10])[0]
    hdr = b[10:10 + hl].decode()
    assert "'<f8'" in hdr and "False" in hdr
    shape = tuple(int(x) for x in re.search(r"\((\d+), (\d+)\)", hdr).groups())
    data = struct.unpack("<%dd" % (shape[0] * shape[1]), b[10 + hl:10 + hl + 8 * shape[0] * shape[1]])
    return [list(data[i * shape[1]:(i + 1) * shape[1]]) for i in range(shape[0])]


def tdb_symbols(p):
    return {m.group(1): float(m.group(2)) for m in re.finditer(r"FUNCTION\s+(VV\d{4})\s+298\.15\s+([-+.\dEe]+);", Path(p).read_text())}


def states_block(art):
    """Per-state expected vs calculated assemblages from the latest evidence bundle (evaluate_states.py output), each state
    with its ORCHID links (ORC record ids, S-/C- state ids, release) or the reason it has none and its intake reference."""
    E = op.ROOT.parent / "assessments" / art / "evidence"
    v = sorted(E.glob("MANIFEST@*.json"))
    ver = json.loads(v[-1].read_text())["version"] if v else None
    se, st = (E / f"states_evaluated@{ver}.json", E / f"states@{ver}.json") if ver else (E / "states_evaluated.json", E / "states.json")
    if not se.exists():
        return PENDING("evaluate_states.py has not been run on this pick"), None, []
    ev = rd(se); SD = rd(st); S = SD["states"]
    rows = []
    for r in ev["rows"]:
        s = S[r["index"]]
        links = [{k: l.get(k) for k in ("id", "observation_id", "state_id", "state_class_id", "paper_id", "pid", "in_release")} for l in s.get("orchid_links", [])]
        rows.append({"orchid_ids": s.get("orchid_ids", []), "state_ids": s.get("state_ids", []), "orchid_link": s.get("orchid_link"), "orchid_links": links,
                     "orchid_release": s.get("orchid_release"), "missing_reason": s.get("missing_reason"), "intake_ref": s.get("intake_ref"),
                     "collection": "coverage" if "dense" in s["source_file"] or "assessed" in s["source_file"] else "fit",
                     "T_K": s["T_K"], "x": s.get("x"), "expected": s["expected"], "predicted": r["calculated"], "match": r["match"], "contains_expected": r["contains_expected"],
                     "excluded": s.get("excluded"), "excluded_present": r["excluded_present"], "kind": s["kind"], "source_file": s["source_file"],
                     "zpf_certainty": r.get("zpf_certainty"), "exclusions": r.get("exclusions")})
    summ = dict(ev["summary"]); summ["tiers"] = SD["counts"]; summ["link_coverage"] = {k: v for k, v in (SD.get("link_coverage") or {}).items() if k != "orchid_checkout"}
    summ["evidence_bundle_version"] = ver
    return rows, summ, [ref(se, f"per-state evaluation (evaluate_states.py, bundle {ver})"), ref(st, f"evidence states with tiers and ORCHID links (bundle {ver})")]


def base_doc(sid, system, title, sp):
    return {"type": "assessment_results", "schema_version": op.SCHEMA_VERSION, "id": sid, "system": system, "title": title,
            "specific_protocol": sp, "general_protocol": "orchid-calphad-fit@2.0.0",
            "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(os.environ["SOURCE_DATE_EPOCH"]) if os.environ.get("SOURCE_DATE_EPOCH") else None))}


# ================================================================================================ Cu-Zr
def cuzr():
    C = H / "ScientificRuns/cuzr-protocol-oneshot-20261106"
    A = C / "attic/run1_s2value_20261106"
    S = A / "steps"
    d = base_doc("cuzr-oneshot-h2-s7-results", "CU-ZR", "Cu-Zr: one-shot to H2 pick s7 (run 1)", "cuzr-oneshot-h2-s7@0.1.0-draft")
    d["orchid_release"] = "next @ dc48bc6 (after v2026.10; unreleased)"
    inputs = []
    d["snapshot"] = {"frozen": True, "note": "Frozen review snapshot of the run-1 pick (6 Nov 2026). Run 2 under the 6 Nov PI decisions is in progress; this dashboard is not updated by it.", "underlying_data_utc": "2026-11-06T11:00:00Z"}
    d["status_banner"] = "Draft. The run-1 pick predates four PI decisions of 6 Nov (midpoint rule, SMAX liquid, Braga two-sided, exclusions at every state); run 2 is in progress. No H2 start passes every plausibility check (HM_FORM RMSE 5.17-6.20 > 5 kJ/mol-atom)."
    rk = {n: rd(S / n / "ranking_protocol.json") for n in ("step2_liquidus", "stepH1_topology_hinge", "stepH2_hinge_thermo", "step3_thermo", "step4_zpf_dense", "stepH2b_hinge_thermo_braga")}
    for n in rk:
        inputs.append(ref(S / n / "ranking_protocol.json", "ranking"))
    pick = A / "tdb/stepH2_hinge_thermo_PICK_s7.tdb"
    res7 = rd(S / "stepH2_hinge_thermo/s7/result.json")
    d["pick"] = {"label": "H2 s7", "artifact": ref(pick, "pick TDB"), "step": "stepH2_hinge_thermo", "start": "s7", "objective": res7["lnL_best"],
                 "objective_name": "ESPEI log-likelihood + hinge (lnL)", "summary": "gate 9/13; 10/13 within 25 K of Wang; activity RMSE 1.62 kJ/mol; HM_FORM RMSE 5.55 kJ/mol-atom; compound moves +6.3, +8.3, +9.1, +5.3, -0.1, +0.5 kJ/mol-atom (Cu5Zr ... CuZr2)"}
    e1 = rd(S / "step1/eval/eval.json")
    rows = [{"step": "step1_oneshot", "general_step": "oneshot_diagram", "role": "lineage", "data_added": "none (PhaseForge one-shot, s2 values; liquid GRACE-2L-OMAT reused)", "free_parameters": 0,
             "starts": None, "modes": None, "pick": None, "objective": None, "objective_name": "lnL", "topology_ok": False, "n_topology_ok": None,
             "key_results": f"gate {e1['gate'][0]}/{e1['gate'][1]}; pure elements = SGTE: {e1['pure_element_check_pass']}", "notes": "Cu51Zr14 melts 1785 K, CuZr2 1794 K; BCC single-phase x 0.54-0.84 from 720 to 2025 K; CuZr not stable (REPORT.md)"}]
    meta = {"step2_liquidus": ("fit_liquidus", "lineage", "liquid ZPF, invariants with the liquid, provisional S_ex, one-shot observations"),
            "stepH1_topology_hinge": ("cuzr_fit_h1", "lineage", "+ hinge cells at the Cu5Zr and Cu10Zr7 reactions (from the step-2 pick)"),
            "stepH2_hinge_thermo": ("cuzr_fit_h2", "lineage", "+ activities, HM_FORM (sigma floor 4.85 kJ), solid ZPF, dense grid; 26 free"),
            "step3_thermo": ("fit_thermo", "side_branch", "+ activities and HM_FORM (from the step-2 pick)"),
            "step4_zpf_dense": ("fit_solid", "side_branch", "+ solid ZPF and dense grid (from the step-3 pick)"),
            "stepH2b_hinge_thermo_braga": ("cuzr_fit_h2b", "side_branch", "H2 + Braga 1998 known-phase-only points (single reader, labelled)")}
    for n, (g, role, added) in meta.items():
        r = rk[n]; ps = next(x for x in r["starts"] if x["start"] == r["picked_start"])
        rows.append({"step": n, "general_step": g, "role": role, "data_added": added, "free_parameters": len(rd(S / n / f"s{r['picked_start']}/result.json")["symbols"]),
                     "starts": r["n_starts"], "modes": None, "pick": f"s{r['picked_start']}", "objective": ps["lnL"], "objective_name": "lnL",
                     "topology_ok": ps["topology_ok"], "n_topology_ok": r["n_topology_ok"],
                     "key_results": f"gate {ps['gate']}/13; within 25 K {ps['within25']}; plausible checks passed {sum(ps['plausible'].values())}/5",
                     "notes": "; ".join(f"{k}={v}" for k, v in ps["plausibility"].items())})
    d["steps"] = rows
    d["states_evaluated"], ssum, refs = states_block("cuzr-oneshot-h2-s7")
    if ssum:
        d["states_summary"] = ssum; inputs += refs
        d["evidence_bundle"] = ref(op.ROOT.parent / "assessments/cuzr-oneshot-h2-s7/evidence/MANIFEST.json", "evidence bundle manifest")
    # invariants with ORC ids
    e7 = rd(S / "stepH2_hinge_thermo/s7/eval/eval.json")
    pinv = rd(C / "work/ref/printed_invariants_paper.json")
    inputs += [ref(S / "stepH2_hinge_thermo/s7/eval/eval.json", "pick checks"), ref(C / "work/ref/printed_invariants_paper.json", "printed invariants with ORC ids")]
    byrx = {}
    for p in pinv:
        byrx.setdefault(p["reaction"], []).extend([p["id"]] + p.get("also_reported_as", []))
    inv = []
    for q in e7["invariants"]:
        tm, dtn = q.get("T_model"), q.get("dT_nearest")
        inv.append({"reaction": q["reaction"], "orchid_ids": sorted(set(byrx.get(q["reaction"], []))),
                    "observed_K": r6(tm - dtn) if (tm is not None and dtn is not None) else None, "observed_basis": "nearest printed fit value of the paper's gate table (printed_fit_K); Wang 2006 experimental values in note",
                    "calculated_K": tm, "dT_K": dtn, "pass": q.get("gate_pass"),
                    "note": f"Wang exp {q.get('wang_exp')}; Wang calc {q.get('wang_calc')}; dT vs Wang exp {q.get('dT_vs_wang_exp')}"})
    d["invariants"] = inv
    d["objective_components"] = {"name": "lnL (ESPEI residuals + hinge penalty)", "total": res7["lnL_best"], "components": res7["per_residual"],
                                 "note": "FixedConfigurationPropertyResidual holds the calorimetric HM_FORM, the one-shot anchors and the provisional S_ex together (ESPEI does not separate them)"}
    d["per_dataset_residuals"] = PENDING("per-dataset residuals were not written for H2 s7 (zpf_by_file.py exists but was not run on this pick)")
    # one-shot shifts in sigma, per lineage pick
    obs = {o["id"]: o for o in rd(A / "results/oneshot_observations.json")["observations"]}
    inputs.append(ref(A / "results/oneshot_observations.json", "one-shot observations with sigma"))
    shifts = []
    for n, s in (("step2_liquidus", 1), ("stepH1_topology_hinge", 1), ("stepH2_hinge_thermo", 7)):
        e = rd(S / n / f"s{s}/eval/eval.json")
        inputs.append(ref(S / n / f"s{s}/eval/eval.json", f"{n} pick checks"))
        for ph, v in e["formation_0K_J_mol_atom"].items():
            o = obs[f"{ph}_HM_FORM"]
            shifts.append({"step": n, "id": o["id"], "phase": ph, "quantity": "HM_FORM (0 K)", "x": None, "shift_J": v["shift"], "sigma_J": r6(o["sigma_J_mol_atom"]), "shift_sigma": r6(v["shift"] / o["sigma_J_mol_atom"])})
        for ph, xs in e["mixing_enthalpy_J_mol_atom"].items():
            for x, v in xs.items():
                o = obs[f"{ph}_HM_MIX_x{float(x):.2f}"]
                shifts.append({"step": n, "id": o["id"], "phase": ph, "quantity": "HM_MIX", "x": float(x), "shift_J": v["shift"], "sigma_J": r6(o["sigma_J_mol_atom"]), "shift_sigma": r6(v["shift"] / o["sigma_J_mol_atom"])})
    d["oneshot_shifts"] = shifts
    ps7 = next(x for x in rk["stepH2_hinge_thermo"]["starts"] if x["start"] == 7)
    d["checks"] = {"pure_elements": e7["pure_elements"] | {"pass": e7["pure_element_check_pass"]},
                   "liquid_convexity": PENDING("no liquid-convexity check was written for H2 s7; liquid stability on a 5 K x 0.01 grid is in checks.topology.liquid_stability"),
                   "gaps": PENDING("no miscibility-gap check (0.4b/0.4c) was run on the Cu-Zr picks"),
                   "plausibility": {"values": ps7["plausibility"], "passed": ps7["plausible"], "thresholds": "compound 0 K H_f within 10 kJ/mol-atom of the one-shot; |S_f| <= 5; activity RMSE <= 3 kJ/mol; HM_FORM RMSE <= 5 kJ/mol-atom; liquid S_ex within 3u (judge.py)"},
                   "topology": {"checks": ps7["topology"], "liquid_stability": {k: v for k, v in e7["liquid_stability"].items() if k != "liquidus_K_by_x"}, "compound_stability_K": e7["visual_check"]["compound_stability_K_300_2200"]},
                   "data_consistency": {"file": ref(C / "results/data_consistency_braga.json", "0.2a check of the Braga candidates (H2b only)")}}
    d["uq"] = PENDING("no UQ was run for the Cu-Zr picks")
    # trajectories
    oneshot = tdb_symbols(A / "tdb/step1_oneshot.tdb")
    names = sorted(oneshot)
    units, phase, labels = [], [], []
    PH = {0: "LIQUID", 2: "LIQUID", 4: "FCC_A1", 6: "FCC_A1", 8: "BCC_A2", 10: "BCC_A2", 12: "HCP_A3", 14: "HCP_A3"}
    CP = ["CU5ZR_C15B", "CU51ZR14", "CU8ZR3", "CU10ZR7", "CUZR_B2", "CUZR2"]
    NAT = {"CU5ZR_C15B": 6, "CU51ZR14": 65, "CU8ZR3": 11, "CU10ZR7": 17, "CUZR_B2": 2, "CUZR2": 3}
    scale = []
    for nm in names:
        k = int(nm[2:])
        if k < 16:
            ph = PH[k - k % 2]; L = (k % 4) // 2; ab = "b" if k % 2 else "a"
            phase.append(ph); labels.append(f"L{L}({ph}) {ab}"); units.append("J/mol/K" if ab == "b" else "kJ/mol")
            scale.append(3.0 if ab == "b" else 9.687)
        elif k < 30:
            ph = CP[k - 16]; phase.append(ph); labels.append(f"{ph} a"); units.append("kJ/mol-formula"); scale.append(9.687 * NAT[ph])
        else:
            ph = CP[k - 30]; phase.append(ph); labels.append(f"{ph} b"); units.append("J/mol-formula/K"); scale.append(3.0 * NAT[ph])
    runs, allvec = [], [[oneshot[n] for n in names]]
    runs.append({"step": "step1_oneshot", "start": "oneshot", "role": "lineage", "recorded": False, "reason": "no fit (the one-shot)", "is_pick": False,
                 "points": [{"eval": 0, "objective": None, "theta": [r6(oneshot[n]) for n in names], "topology_class": "wrong"}], "final_topology_class": "wrong", "wall_s": None, "n_eval": 0})
    for n, (g, role, _) in meta.items():
        r = rk[n]
        for sd in sorted((S / n).glob("s[0-9]*")):
            res = rd(sd / "result.json"); cfg = res["config"]
            start = tdb_symbols(A / cfg["start_tdb"])
            free = res["symbols"]
            ps = next(x for x in r["starts"] if x["start"] == int(sd.name[1:]))
            tc = "ok" if ps["topology_ok"] else "wrong"
            pts = []
            tr = sd / "trace.jsonl"
            for line in tr.read_text().split("\n"):
                if not line.strip():
                    continue
                j = json.loads(line)
                th = dict(start); th.update(dict(zip(free, j["x"])))
                vec = [th[nm] for nm in names]
                allvec.append(vec)
                pts.append({"eval": j["eval"], "objective": j["lnL"], "components": {k: r6(v) for k, v in j["per"].items()}, "theta": [r6(v) for v in vec],
                            "t_s": j["t_s"], "stage": j["stage"]})
            pts[-1]["topology_class"] = tc
            inputs.append(ref(tr, f"trace {n}/{sd.name}"))
            runs.append({"step": n, "start": sd.name, "role": role, "recorded": True, "source": ref(tr, "per-evaluation trace (fit_step.py)"),
                         "points": thin(pts), "final_topology_class": tc, "is_pick": (n == "stepH2_hinge_thermo" and sd.name == "s7"),
                         "wall_s": r6(res["wall_s"]), "n_eval": res["n_eval"]})
    d["trajectory"] = {"parameter_names": names, "parameter_labels": labels, "parameter_units": units, "phase_of_parameter": phase,
                       "objective_name": "lnL (higher is better)", "component_note": d["objective_components"]["note"] + "; topology class evaluated at the end of each start only (judge.py T1-T5)",
                       "oneshot_theta": [r6(oneshot[n]) for n in names], "runs": runs}
    P = pca2(allvec, scale)
    d["projection"] = {"method": "PCA of every retained parameter vector (all evaluations of all starts of all steps + the one-shot), each parameter divided by its scale; center = mean, basis = two leading eigenvectors of the sample covariance (Jacobi), sign: largest-magnitude component positive",
                       "scale": scale, "scale_basis": "display scale, not a prior (the Cu-Zr objective has none): sigma_MLIP 9.687 kJ/mol-atom for a-terms (times atoms per formula for compounds); 3 J/mol/K for b-terms (the start-perturbation sd of fit_step.py), times atoms per formula for compounds",
                       "center": P["center"], "basis": P["basis"], "explained_variance_ratio": P["explained"], "n_vectors": len(allvec),
                       "sign_convention": "largest-|component| of each basis vector positive", "uq_points": [],
                       "note": "projected coordinates are computed by the dashboard from theta, center, scale and basis"}
    d["decisions"] = [x for x in op.load_doc(op.ROOT / "specific/cuzr-oneshot-h2-s7@0.1.0-draft.yaml")["decisions"]]
    d["next_actions"] = ["Finish run 2 (midpoint rule, SMAX liquid, Braga two-sided, exclusions at every state) and version the specific protocol to 0.2.0.",
                         "Evaluate per-state assemblage agreement of the pick on the fit and coverage states.", "Liquid convexity and gap checks (0.4b/0.4c) on the pick.",
                         "Record the spark1 container digest and the PhaseForgePlus commit of the spark1 copy.", "Independent rerun on another machine (Y32)."]
    d["orchid_intake"] = PENDING("no contribution package for this campaign yet (campaign-added hinge exclusions and Braga records are not exported)")
    d["computation"] = [{"host": "spark1", "what": "solids (containers) and fits (CPU)", "pids": "solids 1057575, 1057813; fits in logs/launch_fits.tsv", "status": "finished (run 1)"},
                        {"host": "mac-studio", "what": "ranking and evaluation", "status": "finished"}]
    figs = [("pick", A / "figures/stepH2_PICK_s7.png", "H2 s7 diagram (campaign figure, computed from the pick TDB)"),
            ("oneshot", A / "figures/oneshot_binplot_GRACE-2L-SMAX-OMAT-large.png", "one-shot diagram (pycalphad binplot)"),
            ("step1_eval", A / "figures/step1_oneshot_eval.png", "one-shot evaluation")]
    d["figures"] = [{"panel": p, "caption": c, "file": ref(f, "figure")} for p, f, c in figs]
    d["artifacts"] = [ref(pick, "pick TDB"), ref(A / "tdb/step1_oneshot.tdb", "one-shot TDB"), ref(A / "tdb/stepH1_topology_hinge.tdb", "H1 pick"), ref(A / "tdb/step2_liquidus.tdb", "step-2 pick")]
    d["provenance"] = {"extractor": ref(Path(__file__), "this extractor"), "inputs": inputs}
    return d


# ================================================================================================ Cr-Ni
def crni():
    C = H / "ScientificRuns/crni-paper-fit-20261106"
    S = C / "steps"
    d = base_doc("crni-paper-fit-step4-s1-results", "CR-NI", "Cr-Ni: one-shot to step-4 pick s1", "crni-paper-fit-step4-s1@0.1.0-draft")
    d["orchid_release"] = "unreleased (set E + private exports)"
    inputs = []
    d["snapshot"] = {"frozen": True, "note": "Frozen review snapshot of the step-4 pick (6 Nov 2026), for the Cr-Ni paper SI / Zenodo crate. The ZPF-sigma test reruns of step 4 are in progress and are not shown.", "underlying_data_utc": "2026-11-06T11:16:28Z"}
    d["status_banner"] = "Draft. Pick misses the CrNi2 window (top 780 K vs 863 K); step 4 used exclusions at a subset of states; ZPF-sigma tests of step 4 in progress."
    summ = rd(C / "results/step_summary.json"); inputs.append(ref(C / "results/step_summary.json", "step summary"))
    ev4 = rd(S / "step4_solid/evaluation.json"); inputs.append(ref(S / "step4_solid/evaluation.json", "step-4 evaluation"))
    e4 = next(e for e in ev4["evaluations"] if e["start"] == ev4["pick"])
    pick = C / "tdb/CrNi_paper_fit_FINAL_step4_s1.tdb"
    d["pick"] = {"label": "step 4 s1", "artifact": ref(pick, "pick TDB"), "step": "step4_solid", "start": "s1_perturbed", "objective": e4["logpost"],
                 "objective_name": "log posterior (ESPEI log-likelihood + hinge + weak prior)", "summary": "eutectic 1620 K (ORCHID 1618 K); CrNi2 top 780 K (ORCHID 863 K); right topology at every T apart from the CrNi2 window; |g| 6e-5"}
    added = {"step1_oneshot": "none (PhaseForge one-shot with S_ex)", "step2_liquidus": "liquid ZPF, eutectic, liquid S_ex, one-shot observations (CRNI2 not free)",
             "step3_thermo": "+ activities, HM_MIX, HM_FORM, Liu DFT (CRNI2 fixed)", "step3b_thermo_crni2free": "same data, CRNI2 free and anchored",
             "step4_solid": "+ solid ZPF, hinge (set E + labelled exclusions), CrNi2 ordering, CRNI2 a,b free"}
    gmap = {"step1_oneshot": "oneshot_diagram", "step2_liquidus": "fit_liquidus", "step3_thermo": "fit_thermo", "step3b_thermo_crni2free": "fit_thermo", "step4_solid": "fit_solid"}
    rows = []
    for s in summ:
        n = s["step"]
        ev = rd(S / n / "evaluation.json") if (S / n / "evaluation.json").exists() else {}
        pe = next((e for e in ev.get("evaluations", []) if e["start"] == ev.get("pick")), {})
        tp = pe.get("topology", {})
        rows.append({"step": n, "general_step": gmap[n], "role": "failed" if n == "step3_thermo" else "lineage", "data_added": added[n], "free_parameters": len(s.get("free", [])),
                     "starts": s.get("n_starts"), "modes": len(s.get("modes", [])), "pick": s.get("pick"), "objective": s.get("logpost"), "objective_name": "log posterior",
                     "topology_ok": tp.get("ok"), "n_topology_ok": sum(1 for m in s.get("modes", []) if m.get("topology_ok")),
                     "key_results": f"T_eut {tp.get('T_liquid_min')} K; CrNi2 top {tp.get('T_CrNi2_max')} K; bad T {tp.get('n_bad')}; spurious severity {tp.get('spurious_severity')}",
                     "notes": "; ".join(pe.get("plausibility_notes", []) or [])})
    d["steps"] = rows
    d["states_evaluated"], ssum, refs = states_block("crni-paper-fit-step4-s1")
    if ssum:
        d["states_summary"] = ssum; inputs += refs
        d["evidence_bundle"] = ref(op.ROOT.parent / "assessments/crni-paper-fit-step4-s1/evidence/MANIFEST.json", "evidence bundle manifest")
    d["invariants"] = [
        {"reaction": "L = BCC_A2 + FCC_A1 (eutectic)", "orchid_ids": ["ORC-SV7H3CNRYS"], "observed_K": 1618, "observed_basis": "ORCHID record (accepted, experimental), sigma_eff 11 K", "sigma_K": 11,
         "calculated_K": e4["topology"]["T_liquid_min"], "dT_K": e4["topology"]["T_liquid_min"] - 1618, "pass": abs(e4["topology"]["T_liquid_min"] - 1618) <= 25, "note": "calculated = lowest single-phase liquid T on the pd4 grid (2 K)"},
        {"reaction": "CrNi2 ordering (top of CRNI2)", "orchid_ids": ["ORC-X3KVP7D3PO"], "observed_K": 863, "observed_basis": "ORCHID record (single reader, not yet accepted), sigma_eff 16 K", "sigma_K": 16,
         "calculated_K": e4["topology"]["T_CrNi2_max"], "dT_K": e4["topology"]["T_CrNi2_max"] - 863, "pass": abs(e4["topology"]["T_CrNi2_max"] - 863) <= 25, "note": "83 K low; attributed to the ZPF driving-force scale (open decision 1)"}]
    d["objective_components"] = {"name": "log posterior", "total": e4["logpost"], "components": {**e4["parts"], "log_prior": next(m for m in rd(S / "step4_solid/multistart.json") if m["start"] == "s1_perturbed")["log_prior"]},
                                 "note": "FixedConfigurationPropertyResidual holds calorimetric HM_FORM/HM_MIX, DFT HM_MIX, the one-shot anchors and the provisional S_ex together"}
    pdr = rd(C / "results/per_dataset_step4_pick.json"); inputs.append(ref(C / "results/per_dataset_step4_pick.json", "per-dataset residuals"))
    d["per_dataset_residuals"] = [{"dataset": k.split("/", 1)[1], "group": k.split("/", 1)[0], "type": v.get("type"), "n": v.get("n"), "rms_z": r6(v.get("rms_z")), "max_abs_z": r6(v.get("max_abs_z")),
                                   "rms_residual": r6(v.get("rms_residual")), "unit": "residual/sigma (ZPF: driving force / 1000 J/mol default scale)"} for k, v in pdr.items()]
    shifts = []
    for n in ("step2_liquidus", "step3_thermo", "step3b_thermo_crni2free", "step4_solid"):
        ev = rd(S / n / "evaluation.json"); inputs.append(ref(S / n / "evaluation.json", f"{n} evaluation"))
        pe = next(e for e in ev["evaluations"] if e["start"] == ev["pick"])
        for o in pe["oneshot_shifts"]:
            ph = o["id"].split("_x")[0]
            shifts.append({"step": n, "id": o["id"], "phase": ph if ph != "CRNI2" else "CRNI2", "quantity": "HM_FORM" if ph == "CRNI2" else "HM_MIX",
                           "x": float(o["id"].split("_x")[1]) if "_x" in o["id"] else None, "shift_J": r6(o["shift_from_oneshot_model_J"]), "sigma_J": r6(o["sigma"]), "shift_sigma": r6(o["shift_from_oneshot_model_sigma"])})
    d["oneshot_shifts"] = shifts
    ph = rd(C / "results/physics_final.json"); inputs.append(ref(C / "results/physics_final.json", "physics checks"))
    lc = ph["liquid_convexity"]["min_d2G_by_T"]
    d["checks"] = {"pure_elements": ph["unary"],
                   "liquid_convexity": {"min_d2G_dx2_J_per_mol": r6(min(v[1] for v in lc)), "T_range_K": [lc[0][0], lc[-1][0]], "convex": min(v[1] for v in lc) > 0},
                   "gaps": {"bcc": {k: v for k, v in ph["bcc"].items() if k != "metastable_binodal"}, "fcc": {k: v for k, v in ph["fcc"].items() if k != "metastable_binodal"}, "stable_same_phase_gaps": ph["stable_same_phase_gaps"]},
                   "plausibility": {"plausible": e4["plausible"], "notes": e4["plausibility_notes"], "max_abs_shift_sigma": e4["max_abs_shift_sigma"]},
                   "topology": e4["topology"] | {"phase_at_x052_1473K": e4.get("phase_at_x052_1473K")},
                   "data_consistency": {"file": ref(C / "results/data_consistency.json", "0.2a check (flags only)")}}
    cl = rd(C / "results/uq/classified_mixture_draws.json"); lp = rd(C / "results/uq/laplace_step4.json")
    d["uq"] = {"method": "Laplace mixture at the step-4 modes; 1000 classified draws (no MCMC)", "summary": {k: v for k, v in cl.items() if k != "draws"},
               "modes": [{"name": m["name"], "logpost": m["logpost"], "log_evidence": m.get("log_evidence"), "positive_definite_fd": m.get("positive_definite_fd")} for m in lp["modes"]],
               "files": [ref(C / "results/uq/classified_mixture_draws.json"), ref(C / "results/uq/laplace_step4.json"), ref(C / "results/uq/laplace_step4.draws.npy")],
               "note": "REPORT.md: weights main 0.901, mode B 0.099; independent marginals P(accepted) 0.008"}
    # trajectories (start -> end only)
    LBL = ["L0liq_a", "L0liq_b", "L1liq_a", "L1liq_b", "L0bcc_a", "L0bcc_b", "L1bcc_a", "L1bcc_b", "L0fcc_a", "L0fcc_b", "L1fcc_a", "L1fcc_b", "CrNi2_a", "CrNi2_b"]
    names = [f"VV{i:04d}" for i in range(14)]
    phase = ["LIQUID"] * 4 + ["BCC_A2"] * 4 + ["FCC_A1"] * 4 + ["CRNI2"] * 2
    units = ["J/mol" if l.endswith("_a") else "J/mol/K" for l in LBL]
    scale = [50000.0 if l.endswith("_a") else 30.0 for l in LBL]
    one = next(m["theta"] for m in summ[0]["modes"] if summ[0]["pick"] in m["members"])
    runs = [{"step": "step1_oneshot", "start": "oneshot_Sex", "role": "lineage", "recorded": False, "reason": "no fit (the one-shot)", "is_pick": False,
             "points": [{"eval": 0, "objective": summ[0]["logpost"], "theta": [r6(v) for v in one], "topology_class": "wrong"}], "final_topology_class": "wrong", "wall_s": None, "n_eval": 0}]
    allvec = [one]
    for n in ("step2_liquidus", "step3_thermo", "step3b_thermo_crni2free", "step4_solid"):
        ms = rd(S / n / "multistart.json"); ev = rd(S / n / "evaluation.json")
        evs = {e["start"]: e for e in ev["evaluations"]}
        inputs.append(ref(S / n / "multistart.json", f"{n} multistart"))
        for m in ms:
            e = evs.get(m["start"], {}); tc = "ok" if e.get("topology", {}).get("ok") else ("wrong" if e else "unknown")
            th0 = m.get("theta0") or m["theta"]
            allvec += [th0, m["theta"]]
            runs.append({"step": n, "start": m["start"], "role": "failed" if n == "step3_thermo" else "lineage", "recorded": False,
                         "reason": "trajectory not recorded: fit.py (6 Nov) kept only the start and end vectors (multistart.json)", "source": ref(S / n / "multistart.json", "start and end vectors"),
                         "points": [{"eval": 0, "objective": None, "theta": [r6(v) for v in th0], "topology_class": None},
                                    {"eval": m["nfev"], "objective": m["logpost"], "components": {k: r6(v) for k, v in m["parts"].items()}, "theta": [r6(v) for v in m["theta"]], "topology_class": tc, "t_s": r6(m.get("seconds"))}],
                         "final_topology_class": tc, "is_pick": (n == "step4_solid" and m["start"] == "s1_perturbed"), "wall_s": r6(m.get("seconds")), "n_eval": m["nfev"]})
    # recorded trajectories of the independent rerun (spark1, 6 Nov; same code snapshot and evidence bundle)
    TR = op.ROOT / "reproduce/crni-paper-fit-step4-s1-spark1/trajectories"
    for tf in sorted(TR.glob("*/*/trajectory.jsonl")) if TR.exists() else []:
        lines = [json.loads(l) for l in tf.read_text().splitlines() if l.strip()]
        hd = lines[0]; recs = lines[1:]
        idx = [hd["names_all"].index(n) for n in hd["free"]]
        pts = []
        for r in recs:
            th = list(hd["theta_fixed_all"])
            for k, v in zip(idx, r["theta_free"]):
                th[k] = v
            allvec.append(th)
            comp = {k: r6(v) for k, v in (r.get("parts") or {}).items() if v}
            pts.append({"eval": r["eval"], "objective": r6(r["logpost"]), "components": comp, "theta": [r6(v) for v in th], "t_s": r6(r.get("t_s")), "stage": r.get("stage", ""),
                        "topology_class": ({"ok": "ok"}.get(r["topology"]["class"], "wrong") if r.get("topology") else None)})
        last_tc = next((p["topology_class"] for p in reversed(pts) if p.get("topology_class")), None)
        runs.append({"step": hd["step"] + " (rerun spark1)", "start": hd["start"], "role": "independent_rerun", "recorded": True, "source": ref(tf, "recorded trajectory of the independent rerun"),
                     "points": thin(pts), "final_topology_class": last_tc, "is_pick": False, "wall_s": pts[-1]["t_s"] if pts else None, "n_eval": len(pts)})
    d["trajectory"] = {"parameter_names": names, "parameter_labels": LBL, "parameter_units": units, "phase_of_parameter": phase, "objective_name": "log posterior (higher is better)",
                       "component_note": "original fits (6 Nov, Studio): start and end only, end components from multistart.json. Independent rerun (spark1): every evaluation recorded, components split zpf / oneshot_anchor / S_ex / hinge / prior; topology class (pd4) every TOPO_EVERY evaluations", "oneshot_theta": [r6(v) for v in one], "runs": runs}
    draws = read_npy(C / "results/uq/laplace_step4.draws.npy")
    P = pca2(allvec, scale)
    uq_pts = [{"kind": "draw", "xy": project(t, P, scale)} for t in draws] + [{"kind": "mode", "name": m["name"], "xy": project(m["theta"], P, scale)} for m in lp["modes"]]
    d["projection"] = {"method": "PCA of every retained parameter vector (start and end of every start of steps 2-4 + the one-shot), each parameter divided by its scale; center = mean, basis = two leading eigenvectors (Jacobi); Laplace draws and modes projected onto the same basis (not used to build it)",
                       "scale": scale, "scale_basis": "sd of the weak Normal prior of the objective (50 kJ/mol on a-terms, 30 J/mol/K on b-terms; scripts/model.py)",
                       "center": P["center"], "basis": P["basis"], "explained_variance_ratio": P["explained"], "n_vectors": len(allvec),
                       "sign_convention": "largest-|component| of each basis vector positive", "uq_points": uq_pts, "note": "1000 Laplace-mixture draws (results/uq/laplace_step4.draws.npy) and the mode centres"}
    d["decisions"] = op.load_doc(op.ROOT / "specific/crni-paper-fit-step4-s1@0.1.0-draft.yaml")["decisions"]
    d["next_actions"] = ["Finish the step-4 ZPF-sigma tests (T1, T2, T2a, T3) and decide the step-4 pick (PI).", "Confirm as data: Pugliese gamma assignments, Curie marks, ORC-X3KVP7D3PO (second reader).",
                         "Evaluate per-state assemblage agreement of the pick.", "Record the spark1 container digest; independent rerun on another machine (Y32).", "Export campaign-added exclusions and records to the ORCHID intake."]
    d["orchid_intake"] = PENDING("campaign-added exclusions (17 Pugliese gamma states, 11 Curie marks) and the two single-reader records are not yet in a contribution package")
    d["computation"] = [{"host": "mac-studio", "what": "fits, evaluation, Laplace", "pids": "step4 18544; laplace in logs/laplace.pid", "status": "finished"},
                        {"host": "spark1", "what": "one-shot solids and liquid MD", "status": "finished"}]
    figs = [("pick", C / "figures/final_pick.png", "step-4 pick, computed diagram with the ZPF observations of the fit (campaign figure, house style)"),
            ("steps", C / "figures/steps_sequence.png", "computed diagrams of the step picks (campaign figure)")]
    d["figures"] = [{"panel": p, "caption": c, "file": ref(f, "figure")} for p, f, c in figs]
    d["artifacts"] = [ref(pick, "pick TDB")] + [ref(C / "tdb" / f, "step pick") for f in ("step1_oneshot.tdb", "step2_liquidus_pick.tdb", "step3_thermo_pick.tdb", "step3b_thermo_crni2free_pick.tdb")]
    d["provenance"] = {"extractor": ref(Path(__file__), "this extractor"), "inputs": inputs}
    return d


if __name__ == "__main__":
    which, out = sys.argv[1], Path(sys.argv[2])
    doc = finite({"cuzr": cuzr, "crni": crni}[which]())
    if finite.n:
        print(f"{finite.n} non-finite values on disk written as null")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False, allow_nan=False))
    print(out, round(out.stat().st_size / 1e6, 2), "MB")
