#!/usr/bin/env python3
"""Emit orchid-assessment-schema run cards (protocol.schema.json $defs/run_card) for the step-4 tests, by converting this
campaign's own files (run_card.json, multistart.json, evaluation.json, trajectories); nothing recomputed. Validates each card
with orchid-sage's SchemaValidator. Cards go to results/run_cards/ (orchid-sage/protocols is not written).
usage: emit_run_cards.py <step> [<step> ...]"""
import json
import sys
from pathlib import Path

SAGE = Path.home() / "projects/orchid-sage/protocols"
sys.path.insert(0, str(SAGE / "tools"))
import orchidproto as op  # noqa: E402

CN = Path.home() / "ScientificRuns/crni-paper-fit-20261106"
OUT = CN / "results/run_cards"
SP, GEN = "crni-paper-fit-step4-s1@0.1.0-draft", "orchid-calphad-fit@2.0.0"
LOCK = SAGE / "environment/espei-pr268.lock.txt"
CODE = ["fit2.py", "model2.py", "build_step4c_v2.py", "build_step4c_floor.py", "build_tiers3.py", "laplace2.py", "compare_tests_v3.py", "emit_run_cards_v5.py", "apply_pick_rule.py", "build_tiers2.py", "physics.py", "fit.py", "model.py", "evaluate.py", "pd4.py", "build_data.py", "build_hinge.py", "build_hinge_complete.py", "build_zpf_sigma.py",
        "build_tiers.py", "per_dataset.py", "compare_tests.py", "emit_run_cards.py"]


def ref(p, role=None, storage="local"):
    p = Path(p)
    r = {"path": op.tilde(p), "sha256": op.sha256_file(p), "storage_class": storage}
    if role:
        r["role"] = role
    return r


EXTRA_NOTES = {}
TIERS2 = CN / "results/tiers2.json"
if TIERS2.exists():
    _t = json.loads(TIERS2.read_text())["summary"]
    EXTRA_NOTES["step4T7_tiers_perphase"] = [f"tier counts (per excluded phase): {_t['exclusions_by_tier']}; by phase {_t['exclusions_by_phase_and_tier']}; ZPF rows {_t['zpf_rows_by_tier']}",
        f"states file results/states2.json sha256 {op.sha256_file(CN / 'results/states2.json')} (own implementation of the per-phase rule; orchid-sage classifier not yet updated at launch)"]


DECISION = ("PI ruling 6 Nov (source caveats): Karmazin 1982 550 C row (ORC-SI5MM4H42G, p. 255 'probably not at equilibrium') and Zhang 2014 "
            "(interface compositions not stated as equilibrium) stay in the fit at the weakest tier, 100 J/mol-atom, labelled. In this run: ")
DEC_STATE = {"step4c_combined": "applied: Karmazin 826 K and Zhang 2014 rows at tier 100 (results/tiers3.json)",
             "step4c_b_hingefloor": "applied: Karmazin 826 K and Zhang 2014 rows at tier 100 (results/tiers3.json)","step4T7_tiers_perphase": "Karmazin 826 K row already at 100 (uncertain); Zhang 2014 row at 50 (replicated) - NOT yet compliant; applied in scripts/build_tiers3.py for the next run (results/tiers3.json)",
             "step4T2a_zpfsigma_samehinge": "ruling postdates the run; ZPF rows were weighted by the converted sigma (Karmazin 826 K and Zhang rows as their conversion gave, results/zpf_sigma_conversion.json); next run: tier 100",
             "step4T1_excl": "ruling postdates the run; ZPF rows at ESPEI default scale (1000 J/mol), i.e. weaker than 100 J",
             "step4T3_excl_relax": "ruling postdates the run; ZPF rows at ESPEI default scale (1000 J/mol), i.e. weaker than 100 J"}
PICKRULE = CN / "results/pick_rule_step4_variants.json"


STEP4C_NOTES = [
    "PI decision 6 Nov (fit_protocol 8): ZPF sigma = the T2a conversion, floored at the certainty tier (tiers3: 100; 50 replicated) - adopted default",
    "PI decision 6 Nov (kinetic rule; basis: 'maybe those experiments were not really at equilibrium and the intermetallic did not have time to precipitate'): "
    "12 Jette 1934 (797 K) and Karmazin 1982 (826/875 K) bcc+fcc rows enter as METASTABLE equilibria with CRNI2 suspended (ESPEI ZPF has no per-record "
    "phase switch; done exactly with a separate residual context on the TDB without the CRNI2 phase, model2.py); CRNI2 exclusions dropped at 17 states "
    "below 900 K (the 6 Jette/Karmazin ZPF-state cells, where Hao Fig. 16 reports CrNi2, and the 11 fcc Curie marks 324-572 K, anneal unstated); "
    "the remaining 349 CRNI2 exclusions (283 certain, 65 less certain, 1 uncertain) are all at T >= 948 K (unchanged); list in results/step4c_build.json",
    "PI decision 6 Nov: smooth hinge onset, softplus of width sigma/5 at the same scale (model2.install_smooth_hinge); gradient checked against central "
    "finite differences, max relative error 7.8e-9 (results/step4c_hinge_fd_check.json)",
    "set E cells at observed states, confidence 1.0; relaxation midpoint rule for the one-shot observations (data/oneshot_relax)"]
EXTRA_NOTES["step4c_combined"] = STEP4C_NOTES
EXTRA_NOTES["step4c_b_hingefloor"] = STEP4C_NOTES + ["LABELLED VARIANT (one change against step4c_combined): hinge sigma per (state, excluded phase) = max(tier, the state's own T/x uncertainty converted to energy), the floor the PI adopted for ZPF sigma applied to the hinge (results/step4c_b_hinge_floor.json; 868 of 878 pairs raised)"]


def card(step):
    D = CN / "steps" / step
    camp = D / "run_card.campaign.json"
    if not camp.exists():
        (D / "run_card.json").rename(camp)
    rc = json.loads(camp.read_text())
    ms = json.loads((D / "multistart.json").read_text())
    ev = json.loads((D / "evaluation.json").read_text())
    evs = {e["start"]: e for e in ev["evaluations"]}
    trj = sorted(D.glob("*/trajectory.jsonl"))
    man = {"step": step, "format": "jsonl: header line (names_all, labels_all, free, free_labels, theta_fixed_all), then one line per "
                                    "evaluation {eval, stage, t_s, logpost, parts by category, theta_free, topology every 10 evaluations}; final line stage 'final'",
           "files": [ref(t, "per-evaluation trajectory") for t in trj]}
    (D / "trajectories_manifest.json").write_text(json.dumps(man, indent=1))
    inputs = ([ref(CN / "results/states2.json", "states file (tiers per excluded phase)"), ref(CN / "results/tiers2.json", "tier table")] if step == "step4T7_tiers_perphase" else []) + [ref(CN / rc["start_tdb"], "start TDB"), ref(CN / "steps/configs" / f"{step}.json", "step config"), ref(LOCK, "interpreter lock (espei-pr268)")]
    if rc["config"].get("hinge"):
        inputs.append(ref(CN / rc["config"]["hinge"], "hinge sidecar"))
    for f in rc["data_files"]:
        inputs.append({"path": op.tilde(f["path"]), "sha256": f["sha256"], "storage_class": "local", "role": "data file read by the objective (hash from run_card.json)"})
    inputs += [ref(CN / "scripts" / c, "code") for c in CODE if (CN / "scripts" / c).exists()]
    inputs += [ref(p, "code used (snapshot copied at launch, code_used/<step>/)") for p in sorted((CN / "code_used" / step).glob("*")) if p.is_file()]
    outputs = [ref(D / "multistart.json", "all starts"), ref(D / "evaluation.json", "evaluation and ranking"), ref(D / "trajectories_manifest.json", "trajectory manifest")]
    outputs += [ref(t, "per-evaluation trajectory") for t in trj] + [ref(t, "start TDB") for t in sorted(D.glob("*.tdb"))]
    results = {}
    for m in ms:
        e = evs.get(m["start"], {})
        results[m["start"]] = {"logpost": m["logpost"], "log_prior": m.get("log_prior"), "components": m["parts"], "termination": m["final"],
                               "messages": m.get("messages"), "n_eval": m["nfev"], "wall_s": round(m["seconds"], 1), "grad_norm_q": m["grad_norm_q"],
                               "n_nonfinite": m["n_nonfinite"], "topology": e.get("topology"), "plausible": e.get("plausible"),
                               "plausibility_notes": e.get("plausibility_notes")}
    c = {"type": "run_card", "schema_version": op.SCHEMA_VERSION, "id": f"crni-{step}", "version": "1.0.0",
         "title": f"Cr-Ni {step}: {len(ms)} starts, pick {ev['pick']}", "status": "complete", "run_id": f"crni-{step}",
         "executes": {"specific_protocol": SP, "general_protocol": GEN, "step": "fit_solid"},
         "status_note": "test variant (PI decisions of 6 Nov); not a lineage step", "host": rc["host"], "hardware_class": "Mac Studio M1 Max (10 cores)",
         "pids": [rc["pid"]], "started": rc["started_utc"], "finished": rc.get("finished_utc") or {"status": "pending", "reason": "not recorded"},
         "interpreter": op.tilde(rc["python"]), "packages": {"espei": rc["espei_version"], "pycalphad": rc["pycalphad_version"]},
         "command": f"cd <home>/ScientificRuns/crni-paper-fit-20261106 && PYTHONPATH=<home>/src/PhaseForgePlus/src <fit-python> {'-W ignore scripts/fit2.py' if step.startswith('step4c') else 'scripts/fit.py'} steps/configs/{step}.json {rc['nproc']} 7; <fit-python> scripts/evaluate.py {step}",
         "threads": f"{rc['nproc']} worker processes", "config": rc["config"],
         "seeds": {"rule": "s0 = start TDB; s1..s7 a(1 + 0.1 N(0,1)) [+ N(0, 2 kJ) where a = 0], b + N(0, 3 J/K), numpy default_rng(1000 + k) (fit.py)",
                   "starting_vectors": rc["starts"]},
         "inputs": inputs, "outputs": outputs, "results": results, "trajectory": ref(D / "trajectories_manifest.json", "trajectory manifest"),
         "ranking": {"pick": ev["pick"], "rule": ev["pick_rule"], "order": ev["ranking"]},
         "converted_from": [ref(D / "run_card.campaign.json", "campaign run card"), ref(D / "multistart.json", "campaign multistart record"),
                            ref(CN / "logs" / f"{step}.log", "run log")],
         "notes": [rc["config"].get("note", ""), rc["config"].get("held_rule", ""), rc["config"].get("pick_rule", "")] + EXTRA_NOTES.get(step, []) + [DECISION + DEC_STATE.get(step, "n/a")]}
    if PICKRULE.exists():
        pr = json.loads(PICKRULE.read_text()).get(step)
        if pr:
            c["ranking"]["pick_rule_10a"] = {k: v for k, v in pr.items() if k != "modes"}
            c["ranking"]["modes"] = pr["modes"]
    return c


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    V = op.SchemaValidator()
    for step in sys.argv[1:]:
        c = card(step)
        errs = V.validate(c, "protocol.schema.json")
        (OUT / f"crni-{step}.json").write_text(json.dumps(c, indent=1, ensure_ascii=False) + "\n")
        (CN / "steps" / step / "run_card.json").write_text(json.dumps(c, indent=1, ensure_ascii=False) + "\n")
        print(step, "schema errors:", len(errs), errs[:3])


if __name__ == "__main__":
    main()
