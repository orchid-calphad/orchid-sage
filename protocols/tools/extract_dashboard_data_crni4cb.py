#!/usr/bin/env python3
"""Dashboard data (assessment_results) of the Cr-Ni step-4 pick step4c-b (PI decision 6 Nov 2026). Standard library only.

  python3 tools/extract_dashboard_data_crni4cb.py OUT.json

Same rules as extract_dashboard_data.py (nothing recomputed; values copied from the campaign files), whose helpers it imports;
kept as a separate file so the extractor hashed in the existing dashboards stays byte-identical."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orchidproto as op  # noqa: E402
from extract_dashboard_data import H, PENDING, ref, rd, r6, finite, pca2, project, thin, read_npy, states_block, base_doc  # noqa: E402


# ================================================================================================ Cr-Ni step4c-b (PI pick, 6 Nov evening)
def crni4cb():
    """Cr-Ni with the step-4 pick step4c-b (hinge floor). Steps 1-3b as in crni(); step 4 = step4c_b_hingefloor, whose per-evaluation
    trajectories were recorded. Values copied from the campaign files, nothing recomputed."""
    C = H / "ScientificRuns/crni-paper-fit-20261106"
    S = C / "steps"; ST = "step4c_b_hingefloor"
    SP = "crni-paper-fit-step4c-b@0.2.0-draft"
    d = base_doc("crni-paper-fit-step4c-b-results", "CR-NI", "Cr-Ni: one-shot to step-4 pick step4c-b (hinge floor)", SP)
    d["orchid_release"] = "unreleased (set E + private exports)"
    inputs = []
    d["snapshot"] = {"frozen": True, "note": "Review snapshot of the step-4 pick step4c-b (PI decision 6 Nov 2026: hinge floor adopted). Steps 1-3b unchanged from crni-paper-fit-step4-s1.",
                     "underlying_data_utc": "2026-11-06T18:59:59Z"}
    d["status_banner"] = ("Draft. Step 4c-b: 8 of 8 starts converged (10a) into one mode; CrNi2 top 860 K (ORCHID 863 K), eutectic 1614 K (1618 K). "
                          "Notes, not rejections: fcc one-shot enthalpies moved +14.5 / +11.4 kJ (x 0.25 / 0.5); bcc S_ex(0.5) +2.96; one liquid S_ex at z -3.1; "
                          "a BCC_A2 + LIQUID sliver at 2176 K only (above every stated window).")
    summ = rd(C / "results/step_summary.json"); inputs.append(ref(C / "results/step_summary.json", "step summary (steps 1-4 s1)"))
    ev4 = rd(S / ST / "evaluation.json"); inputs.append(ref(S / ST / "evaluation.json", "step-4c-b evaluation"))
    e4 = next(e for e in ev4["evaluations"] if e["start"] == ev4["pick"])
    ms4 = rd(S / ST / "multistart.json"); inputs.append(ref(S / ST / "multistart.json", "step-4c-b multistart"))
    pick = C / "tdb/step4c_b_hingefloor_pick.tdb"
    d["pick"] = {"label": "step 4c-b s4", "artifact": ref(pick, "pick TDB"), "step": ST, "start": ev4["pick"], "objective": e4["logpost"],
                 "objective_name": "log posterior (ESPEI log-likelihood + smooth hinge + weak prior)",
                 "summary": "eutectic %s K (ORCHID 1618 K); CrNi2 top %s K (ORCHID 863 K); 8/8 starts converged, one mode; |g| %.1e" % (e4["topology"]["T_liquid_min"], e4["topology"]["T_CrNi2_max"], e4["grad_norm_q"])}
    added = {"step1_oneshot": "none (PhaseForge one-shot with S_ex)", "step2_liquidus": "liquid ZPF, eutectic, liquid S_ex, one-shot observations (CRNI2 not free)",
             "step3_thermo": "+ activities, HM_MIX, HM_FORM, Liu DFT (CRNI2 fixed)", "step3b_thermo_crni2free": "same data, CRNI2 free and anchored"}
    gmap = {"step1_oneshot": "oneshot_diagram", "step2_liquidus": "fit_liquidus", "step3_thermo": "fit_thermo", "step3b_thermo_crni2free": "fit_thermo"}
    rows = []
    for s in summ:
        n = s["step"]
        if n not in added:
            continue
        ev = rd(S / n / "evaluation.json") if (S / n / "evaluation.json").exists() else {}
        pe = next((e for e in ev.get("evaluations", []) if e["start"] == ev.get("pick")), {})
        tp = pe.get("topology", {})
        rows.append({"step": n, "general_step": gmap[n], "role": "failed" if n == "step3_thermo" else "lineage", "data_added": added[n], "free_parameters": len(s.get("free", [])),
                     "starts": s.get("n_starts"), "modes": len(s.get("modes", [])), "pick": s.get("pick"), "objective": s.get("logpost"), "objective_name": "log posterior",
                     "topology_ok": tp.get("ok"), "n_topology_ok": sum(1 for m in s.get("modes", []) if m.get("topology_ok")),
                     "key_results": f"T_eut {tp.get('T_liquid_min')} K; CrNi2 top {tp.get('T_CrNi2_max')} K; bad T {tp.get('n_bad')}; spurious severity {tp.get('spurious_severity')}",
                     "notes": "; ".join(pe.get("plausibility_notes", []) or [])})
    tp = e4["topology"]
    rows.append({"step": ST, "general_step": "fit_solid", "role": "lineage",
                 "data_added": "+ solid ZPF at per-record sigma_DF (floored at tiers), exclusions at every observed state (per-phase tiers, hinge sigma = max(tier, converted state uncertainty)), smooth hinge, 17 kinetically limited CrNi2 absences suspended, CrNi2 ordering",
                 "free_parameters": len(ms4[0]["free"]), "starts": len(ms4), "modes": 1, "pick": ev4["pick"], "objective": e4["logpost"], "objective_name": "log posterior",
                 "topology_ok": tp.get("ok"), "n_topology_ok": 0,
                 "key_results": f"T_eut {tp.get('T_liquid_min')} K; CrNi2 top {tp.get('T_CrNi2_max')} K; bad T {tp.get('n_bad')} ({tp.get('bad_T_range')}, {tp.get('spurious_severity')})",
                 "notes": "; ".join(e4.get("plausibility_notes", []) or [])})
    d["steps"] = rows
    d["states_evaluated"], ssum, refs = states_block("crni-paper-fit-step4c-b")
    if ssum:
        d["states_summary"] = ssum; inputs += refs
        d["evidence_bundle"] = ref(op.ROOT.parent / "assessments/crni-paper-fit-step4c-b/evidence/MANIFEST@1.0.0.json", "evidence bundle manifest")
    d["invariants"] = [
        {"reaction": "L = BCC_A2 + FCC_A1 (eutectic)", "orchid_ids": ["ORC-SV7H3CNRYS"], "observed_K": 1618, "observed_basis": "ORCHID record (accepted, experimental), sigma_eff 11 K", "sigma_K": 11,
         "calculated_K": tp["T_liquid_min"], "dT_K": tp["T_liquid_min"] - 1618, "pass": abs(tp["T_liquid_min"] - 1618) <= 25, "note": "calculated = lowest single-phase liquid T on the pd4 grid (2 K)"},
        {"reaction": "CrNi2 ordering (top of CRNI2)", "orchid_ids": ["ORC-X3KVP7D3PO"], "observed_K": 863, "observed_basis": "ORCHID record (single reader, not yet accepted), sigma_eff 16 K", "sigma_K": 16,
         "calculated_K": tp["T_CrNi2_max"], "dT_K": tp["T_CrNi2_max"] - 863, "pass": abs(tp["T_CrNi2_max"] - 863) <= 25, "note": "per-record ZPF sigma_DF + hinge floor (step 4c-b)"}]
    d["objective_components"] = {"name": "log posterior", "total": e4["logpost"], "components": {**e4["parts"], "log_prior": next(m for m in ms4 if m["start"] == ev4["pick"])["log_prior"]},
                                 "note": "groups: zpf (solid_c, liq_c), zpf_susp (12 metastable bcc+fcc rows with CRNI2 suspended), thermo, oneshot_anchor (relaxation midpoint rule), S_ex (provisional), smooth hinge"}
    pdf = C / "results/per_dataset_step4c_b_hingefloor.json"; pdr = rd(pdf); inputs.append(ref(pdf, "per-dataset residuals"))
    d["per_dataset_residuals"] = [{"dataset": k.split("/", 1)[1], "group": k.split("/", 1)[0], "type": v.get("type"), "n": v.get("n"), "rms_z": r6(v.get("rms_z")), "max_abs_z": r6(v.get("max_abs_z")),
                                   "rms_residual": r6(v.get("rms_residual")), "unit": "residual/sigma (ZPF: driving force / per-record sigma_DF)"} for k, v in pdr.items()]
    shifts = []
    for n in ("step2_liquidus", "step3_thermo", "step3b_thermo_crni2free", ST):
        ev = rd(S / n / "evaluation.json"); inputs.append(ref(S / n / "evaluation.json", f"{n} evaluation"))
        pe = next(e for e in ev["evaluations"] if e["start"] == ev["pick"])
        for o in pe["oneshot_shifts"]:
            ph = o["id"].split("_x")[0]
            shifts.append({"step": n, "id": o["id"], "phase": ph, "quantity": "HM_FORM" if ph == "CRNI2" else "HM_MIX",
                           "x": float(o["id"].split("_x")[1]) if "_x" in o["id"] else None, "shift_J": r6(o["shift_from_oneshot_model_J"]), "sigma_J": r6(o["sigma"]), "shift_sigma": r6(o["shift_from_oneshot_model_sigma"])})
    d["oneshot_shifts"] = shifts
    phf = C / "results/physics_step4c_b.json"; ph = rd(phf); inputs.append(ref(phf, "physics checks"))
    lc = ph["liquid_convexity"]["min_d2G_by_T"]
    d["checks"] = {"pure_elements": ph["unary"],
                   "liquid_convexity": {"min_d2G_dx2_J_per_mol": r6(min(v[1] for v in lc)), "T_range_K": [lc[0][0], lc[-1][0]], "convex": min(v[1] for v in lc) > 0},
                   "gaps": {"bcc": {k: v for k, v in ph["bcc"].items() if k != "metastable_binodal"}, "fcc": {k: v for k, v in ph["fcc"].items() if k != "metastable_binodal"}, "stable_same_phase_gaps": ph["stable_same_phase_gaps"]},
                   "plausibility": {"plausible": e4["plausible"], "notes": e4["plausibility_notes"], "max_abs_shift_sigma": e4["max_abs_shift_sigma"]},
                   "topology": e4["topology"] | {"phase_at_x052_1473K": e4.get("phase_at_x052_1473K")},
                   "data_consistency": {"file": ref(C / "results/data_consistency.json", "0.2a check (flags only)")}}
    clf = C / "results/uq/classified_mixture_draws_step4c_b.json"; lpf = C / "results/uq/laplace_step4c_b.json"
    cl = rd(clf); lp = rd(lpf)
    d["uq"] = {"method": "Laplace mixture at the step-4c-b modes; 1000 classified draws (no MCMC)", "summary": {k: v for k, v in cl.items() if k != "draws"},
               "modes": [{"name": m["name"], "logpost": m["logpost"], "log_evidence": m.get("log_evidence"), "positive_definite_fd": m.get("positive_definite_fd")} for m in lp["modes"]],
               "files": [ref(clf), ref(lpf), ref(C / "results/uq/laplace_step4c_b.draws.npy")],
               "note": "weights %s; independent marginals %s" % (lp["weights"].get("laplace"), json.dumps(lp.get("independent_marginals"))[:200])}
    LBL = ["L0liq_a", "L0liq_b", "L1liq_a", "L1liq_b", "L0bcc_a", "L0bcc_b", "L1bcc_a", "L1bcc_b", "L0fcc_a", "L0fcc_b", "L1fcc_a", "L1fcc_b", "CrNi2_a", "CrNi2_b"]
    names = [f"VV{i:04d}" for i in range(14)]
    phase = ["LIQUID"] * 4 + ["BCC_A2"] * 4 + ["FCC_A1"] * 4 + ["CRNI2"] * 2
    units = ["J/mol" if l.endswith("_a") else "J/mol/K" for l in LBL]
    scale = [50000.0 if l.endswith("_a") else 30.0 for l in LBL]
    one = next(m["theta"] for m in summ[0]["modes"] if summ[0]["pick"] in m["members"])
    runs = [{"step": "step1_oneshot", "start": "oneshot_Sex", "role": "lineage", "recorded": False, "reason": "no fit (the one-shot)", "is_pick": False,
             "points": [{"eval": 0, "objective": summ[0]["logpost"], "theta": [r6(v) for v in one], "topology_class": "wrong"}], "final_topology_class": "wrong", "wall_s": None, "n_eval": 0}]
    allvec = [one]
    for n in ("step2_liquidus", "step3_thermo", "step3b_thermo_crni2free"):
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
                         "final_topology_class": tc, "is_pick": False, "wall_s": r6(m.get("seconds")), "n_eval": m["nfev"]})
    tm = rd(S / ST / "trajectories_manifest.json"); inputs.append(ref(S / ST / "trajectories_manifest.json", "trajectory manifest"))
    for f in tm["files"]:
        tf = Path(f["path"].replace("~", str(H), 1))
        lines = [json.loads(l) for l in tf.read_text().splitlines() if l.strip()]
        hd = lines[0]; recs = [r for r in lines[1:] if "theta_free" in r]
        idx = [hd["names_all"].index(n) for n in hd["free"]]
        pts = []
        for r in recs:
            th = list(hd["theta_fixed_all"])
            for k, v in zip(idx, r["theta_free"]):
                th[k] = v
            allvec.append(th)
            comp = {k: r6(v) for k, v in (r.get("parts") or {}).items() if v}
            pts.append({"eval": r.get("eval"), "objective": r6(r.get("logpost")), "components": comp, "theta": [r6(v) for v in th], "t_s": r6(r.get("t_s")), "stage": r.get("stage", ""),
                        "topology_class": ({"ok": "ok"}.get(r["topology"].get("class"), "wrong") if isinstance(r.get("topology"), dict) else None)})
        start = tf.parent.name
        last_tc = next((p["topology_class"] for p in reversed(pts) if p.get("topology_class")), None)
        runs.append({"step": ST, "start": start, "role": "lineage", "recorded": True, "source": ref(tf, "per-evaluation trajectory"),
                     "points": thin(pts), "final_topology_class": last_tc, "is_pick": start == ev4["pick"], "wall_s": pts[-1]["t_s"] if pts else None, "n_eval": len(pts)})
    d["trajectory"] = {"parameter_names": names, "parameter_labels": LBL, "parameter_units": units, "phase_of_parameter": phase, "objective_name": "log posterior (higher is better)",
                       "component_note": "steps 2-3b (6 Nov, Studio): start and end only. Step 4c-b: every evaluation recorded (fit2.py), components by group; topology class every 10 evaluations", "oneshot_theta": [r6(v) for v in one], "runs": runs}
    draws = read_npy(C / "results/uq/laplace_step4c_b.draws.npy")
    P = pca2(allvec, scale)
    uq_pts = [{"kind": "draw", "xy": project(t, P, scale)} for t in draws] + [{"kind": "mode", "name": m["name"], "xy": project(m["theta"], P, scale)} for m in lp["modes"]]
    d["projection"] = {"method": "PCA of every retained parameter vector (start and end of steps 2-3b, every recorded evaluation of step 4c-b, the one-shot), each parameter divided by its scale; center = mean, basis = two leading eigenvectors (Jacobi); Laplace draws and modes projected onto the same basis (not used to build it)",
                       "scale": scale, "scale_basis": "sd of the weak Normal prior of the objective (50 kJ/mol on a-terms, 30 J/mol/K on b-terms; scripts/model.py)",
                       "center": P["center"], "basis": P["basis"], "explained_variance_ratio": P["explained"], "n_vectors": len(allvec),
                       "sign_convention": "largest-|component| of each basis vector positive", "uq_points": uq_pts, "note": "1000 Laplace-mixture draws (results/uq/laplace_step4c_b.draws.npy) and the mode centres"}
    d["decisions"] = op.load_doc(op.ROOT / "specific/crni-paper-fit-step4c-b@0.2.0-draft.yaml")["decisions"]
    d["next_actions"] = ["Confirm as data: Pugliese gamma assignments, Curie marks, ORC-X3KVP7D3PO (second reader).", "Independent rerun of step 4c-b on another machine (Y32).",
                         "PI: fcc one-shot moves (+14.5 / +11.4 kJ) and the 2176 K BCC_A2 + LIQUID sliver - notes or action?", "Export campaign-added exclusions and records to the ORCHID intake."]
    d["orchid_intake"] = PENDING("campaign-added exclusions and the two single-reader records are not yet in a contribution package")
    d["computation"] = [{"host": "mac-studio", "what": "step 4c-b fit, evaluation, Laplace", "pids": "44773 (step 4c-b)", "status": "finished"},
                        {"host": "spark1", "what": "one-shot solids and liquid MD", "status": "finished"}]
    figs = [("pick", C / "figures/step4c_b_hingefloor_pick.png", "step-4c-b pick, computed diagram with the ZPF observations of the fit (campaign figure, house style)"),
            ("steps", C / "figures/steps_1_to_3.png", "computed diagrams of the step 1-3 picks (campaign figure)")]
    d["figures"] = [{"panel": p, "caption": c, "file": ref(f, "figure")} for p, f, c in figs]
    d["artifacts"] = [ref(pick, "pick TDB")] + [ref(C / "tdb" / f, "step pick") for f in ("step1_oneshot.tdb", "step2_liquidus_pick.tdb", "step3_thermo_pick.tdb", "step3b_thermo_crni2free_pick.tdb")]
    d["provenance"] = {"extractor": ref(Path(__file__), "this extractor"), "inputs": inputs}
    return d


if __name__ == "__main__":
    out = Path(sys.argv[1])
    doc = finite(crni4cb())
    if finite.n:
        print(f"{finite.n} non-finite values on disk written as null")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False, allow_nan=False))
    print(out, round(out.stat().st_size / 1e6, 2), "MB")
