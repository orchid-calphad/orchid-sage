"""v2 of emit_run_cards_10ac.py (only change: recorded_by, required by the run_card schema). Run cards (orchid-assessment-schema run_card) for the 10a re-checks (step 3b on both machines, step 4c-b on both machines) and the
10c global search of step 4c-b (6 Nov 2026 evening). Standard library only; reads the result files, writes results/run_cards/.
  python3 scripts/emit_run_cards_10ac.py"""
import hashlib
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
H = "<home>/ScientificRuns/crni-paper-fit-20261106"
SP = "crni-paper-fit-step4c-b@1.0.0"
PKG = {"espei": "0.8.11.dev82+g9039ea215", "pycalphad": "0.11.3.dev35+g9a6939dd2"}
OUT = R / "results/run_cards"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ref(rel, role, sc="local"):
    return {"path": f"{H}/{rel}", "sha256": sha(R / rel), "storage_class": sc, "role": role}


def card(id_, title, step, host, hw, interp, cmd, threads, started, finished, inputs, outputs, results, notes, seeds=None, pids=None):
    c = {"type": "run_card", "schema_version": "orchid-assessment-schema@1.0.0-draft.2", "id": id_, "version": "1.0.0", "title": title,
         "status": "complete", "run_id": id_, "executes": {"specific_protocol": SP, "general_protocol": "orchid-calphad-fit@2.0.0", "step": step},
         "host": host, "hardware_class": hw, "pids": pids or [], "started": started, "finished": finished, "interpreter": interp, "packages": PKG,
         "command": cmd, "threads": threads, "seeds": seeds or {"rule": "none (deterministic evaluation); random directions numpy default_rng(20261106)"},
         "inputs": inputs, "outputs": outputs, "results": results, "notes": notes,
         "recorded_by": {"tool": "crni-paper-fit-20261106/scripts/emit_run_cards_10ac_v2.py", "version": "2"}}
    (OUT / f"{id_}.json").write_text(json.dumps(c, indent=1) + "\n")
    return c


def summ(f):
    d = json.loads((R / f).read_text())
    return {"kinds": d["kinds"], "n_eligible": d["n_eligible"], "pick": d["pick"], "pick_logpost": d["pick_logpost"], "gap_to_runner_up": d["gap_to_runner_up"],
            "n_failed_equilibria_total": d["n_failed_equilibria_total"], "host": d.get("host"),
            "per_start": {r["start"]: {"logpost": r["logpost"], "kind": r["kind"], "eligible": r["eligible"], "grad_norm_q": r["grad_norm_scaled_analytic"],
                                       "worst_improvement": r["worst_direction"]["improvement"], "n_boundary_points": r["n_boundary_points"],
                                       "n_boundary_points_outside_own_uncertainty": r["n_boundary_points_outside_own_uncertainty"],
                                       "n_failed_equilibria": r["n_failed_equilibria"]} for r in d["rows"]}}


STUDIO, B464 = ("mac-studio", "Mac Studio M1 Max (10 cores)"), ("spark1", "DGX Spark GB10 (20 Arm cores), CPU only")
PY_S, PY_B = "<fit-python>", "<home>/orchid-crni-mcmc-20261105/env/grad/bin/python"
code = [ref("scripts/check10a_ms.py", "code"), ref("scripts/kink10a.py", "code"), ref("scripts/model.py", "code (step 3b objective)"),
        ref("scripts/model2.py", "code (step 4c-b objective)")]

card("crni-step3b-check10a", "Cr-Ni step 3b: 10a with the kink rule on the polished starts of both machines and the original campaign starts",
     "pick_thermo", STUDIO[0] + " and spark1", STUDIO[1] + "; " + B464[1], f"{PY_S} (Studio); {PY_B} (spark1)",
     "cd <staged step-3b root> && OMP_NUM_THREADS=1 PY -u scripts/check10a_ms.py steps/configs/step3b_thermo_crni2free.json "
     "steps/step3b_thermo_crni2free/multistart.json results/check10a_step3b_<set>.json 4|3 model",
     "OMP_NUM_THREADS=1; 4 workers (Studio), 3 (spark1)", "2026-11-06T16:43-0600", "2026-11-06T17:19-0600",
     code + [ref("steps/step3b_thermo_crni2free/multistart.json", "original campaign starts"), ref("steps/configs/step3b_thermo_crni2free.json", "objective config"),
             ref("tdb/step3b_thermo_crni2free_pick.tdb", "TDB step 4c-b started from")],
     [ref(f"results/check10a_step3b_{s}.json", f"10a result ({s})") for s in ("polished_spark1", "polished_studio", "original_campaign")],
     {s: summ(f"results/check10a_step3b_{s}.json") for s in ("polished_spark1", "polished_studio", "original_campaign")},
     ["polished starts: orchid-sage protocols/reproduce/crni-step3b-polish-{spark1,studio}/multistart.json, evaluated in their own staged roots",
      "pick s1_perturbed in all three sets (kink-stationary); the original-campaign s1 is the start TDB of step 4c-b (max |dtheta| 5e-7); spark1 s1 within 0.11 of the 10b tolerance; Studio-polished s1 33x tolerance in the flat directions (bcc L1, CrNi2 a/b), 0.0046 log-units lower",
      "|r| <= sigma as 'within its own uncertainty' is the agent's operational reading of 10a (labelled)"])

card("crni-step4c_b-check10a", "Cr-Ni step 4c-b: 10a with the kink rule on the 8 starts, Studio and spark1", "pick_solid", STUDIO[0] + " and spark1",
     STUDIO[1] + "; " + B464[1], f"{PY_S} (Studio, check10a.py, coordinator); {PY_B} (spark1, check10a_ms.py)",
     "spark1: cd <home>/orchid-protocols-work-20261106/crni-10c-spark1 && OMP_NUM_THREADS=1 PY -u scripts/check10a_ms.py steps/configs/step4c_b_hingefloor.json steps/step4c_b_hingefloor/multistart.json results/check10a_step4c_b_multistart.json 2 model2",
     "OMP_NUM_THREADS=1; 2 workers (spark1)", "2026-11-06T16:58-0600", "2026-11-06T17:45-0600",
     code + [ref("steps/step4c_b_hingefloor/multistart.json", "starts"), ref("steps/configs/step4c_b_hingefloor.json", "objective config")],
     [ref("results/check10a_step4c_b_hingefloor.json", "10a result (Studio)"), ref("results/check10a_step4c_b_hingefloor_spark1.json", "10a result (spark1)")],
     {"studio": summ("results/check10a_step4c_b_hingefloor.json"), "spark1": summ("results/check10a_step4c_b_hingefloor_spark1.json")},
     ["8 of 8 smooth on both machines; pick s4_perturbed; gap 1.869e-9 (Studio) vs 1.867e-9 (spark1)"])

for m in ("basin", "anneal"):
    d = R / f"steps/step4c_b_hingefloor_10c/{m}_7201"
    man = json.loads((d / "run_manifest.json").read_text()); st = json.loads((d / "status.json").read_text())
    s = json.loads((R / "results/global_10c_step4c_b_summary.json").read_text())[f"{m}_7201"]
    rel = f"steps/step4c_b_hingefloor_10c/{m}_7201"
    card(f"crni-step4c_b-10c-{m}", f"Cr-Ni step 4c-b: 10c {'basin hopping' if m == 'basin' else 'dual annealing'} from the 10a pick s4 (seed 7201, 1500 evaluations)",
         "fit_solid", B464[0], B464[1], PY_B,
         f"cd <home>/orchid-protocols-work-20261106/crni-10c-spark1 && OMP_NUM_THREADS=1 PY -u scripts/run_global_crni.py steps/configs/step4c_b_hingefloor.json "
         f"steps/step4c_b_hingefloor/multistart.json s4_perturbed {m} 7201 1500 {rel}", "OMP_NUM_THREADS=1; 1 process", man["started"], st["finished"],
         [ref("scripts/run_global_crni.py", "code"), ref("scripts/model2.py", "code"), ref("steps/step4c_b_hingefloor/multistart.json", "common start (s4)"),
          ref("steps/configs/step4c_b_hingefloor.json", "objective config"), ref("tdb/step3b_thermo_crni2free_pick.tdb", "start TDB of the objective"),
          ref("data/hinge/step4c_hinge_floor.json", "hinge sidecar")],
         [ref(f"{rel}/{f}", f) for f in ("run_manifest.json", "status.json", "trace.jsonl", "top10.json", "events.jsonl", "best.tdb", "parameters.json")],
         {"best": {"logpost": st["best_logpost"], "evaluation": st["best_evaluation"], "improvement_over_start": st["improvement_over_start"]},
          "termination": st["termination"], "evaluations": st["evaluations"], "cache_hits": st["cache_hits"], "wall_s": st["elapsed_s"],
          **{k: s[k] for k in ("n_invalid", "n_liquid_infeasible", "n_local_solves", "logpost_median", "n_within_0.01_of_pick", "best_theta_minus_s4_max_abs")}},
         ["fit_protocol 10c; code pattern cuzr-protocol-20261104/run_global.py; settings and agent decisions (bounds z in [-5,5], L-BFGS-B local, <= 50 evaluations per local solve, liquid convexity accept test) in PLAN.md addendum, stated before launch",
          "no better optimum: best = s4 within 4e-5 J/mol; no global-optimality claim",
          "schema gap: the general protocol orchid-calphad-fit@2.0.0 has no step for 10c; recorded under fit_solid"],
         seeds={"rule": "scipy seed=7201 (legacy RandomState) for the method; data, objective deterministic"}, pids=[man["pid"]])
print("ok", sorted(p.name for p in OUT.glob("*10*")))
