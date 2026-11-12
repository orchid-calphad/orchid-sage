#!/usr/bin/env python3
"""Dashboard data (assessment_results) of crni-paper-fit-step4c-b@1.0.0 (frozen pick after the 10a kink rule and the 10c global search).
Standard library only.

  python3 tools/extract_dashboard_data_crni4cb_v1.py OUT.json

Builds on extract_dashboard_data_crni4cb.crni4cb() (kept byte-identical, so the 0.2.0-draft dashboard stays reproducible) and adds, copied
from the campaign files and nothing recomputed: the 1.0.0 specific-protocol reference, its decisions, the 10a re-checks (step 3b, step 4c-b,
both machines) and the 10c global-search runs as step rows, and the updated banner, next actions and computation."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orchidproto as op  # noqa: E402
from extract_dashboard_data import H, ref, rd, finite  # noqa: E402
from extract_dashboard_data_crni4cb import crni4cb  # noqa: E402

OLD, NEW = "crni-paper-fit-step4c-b@0.2.0-draft", "crni-paper-fit-step4c-b@1.0.0"


def crni4cb_v1():
    C = H / "ScientificRuns/crni-paper-fit-20261106"
    d = json.loads(json.dumps(crni4cb()).replace(OLD, NEW))
    d["id"] = "crni-paper-fit-step4c-b-1.0.0-results"
    d["title"] = d["title"] + " - 1.0.0 (10a kink rule, 10c)"
    s3 = {k: rd(C / f"results/check10a_step3b_{k}.json") for k in ("original_campaign", "polished_studio", "polished_spark1")}
    c4s, c4b = rd(C / "results/check10a_step4c_b_hingefloor.json"), rd(C / "results/check10a_step4c_b_hingefloor_spark1.json")
    g = rd(C / "results/global_10c_step4c_b_summary.json")
    inputs = d["provenance"]["inputs"]
    inputs.append(ref(Path(__file__), "this extractor (1.0.0 additions)"))
    for f, role in [*[(C / f"results/check10a_step3b_{k}.json", f"10a step 3b ({k})") for k in s3],
                    (C / "results/check10a_step4c_b_hingefloor.json", "10a step 4c-b (Studio)"), (C / "results/check10a_step4c_b_hingefloor_spark1.json", "10a step 4c-b (spark1)"),
                    (C / "results/global_10c_step4c_b_summary.json", "10c summary")]:
        inputs.append(ref(f, role))
    d["steps"].append({"step": "step3b_check10a", "general_step": "pick_thermo", "role": "lineage", "data_added": "none (re-evaluation under 10a with the kink rule)",
                       "free_parameters": 14, "starts": 8, "modes": 1, "pick": s3["original_campaign"]["pick"], "objective": s3["original_campaign"]["pick_logpost"],
                       "objective_name": "log posterior", "topology_ok": None, "n_topology_ok": 0,
                       "key_results": "; ".join(f"{k}: kinds {v['kinds']}, pick {v['pick']} ({v['pick_logpost']:.5f})" for k, v in s3.items()),
                       "notes": "original s1 = start TDB of step 4c-b; Studio-polished s1 differs in flat directions only (33x the 10b tolerance, 0.0046 lower)"})
    d["steps"].append({"step": "step4c_b_check10a", "general_step": "pick_solid", "role": "lineage", "data_added": "none (10a with the kink rule)", "free_parameters": 14,
                       "starts": 8, "modes": 1, "pick": c4s["pick"], "objective": c4s["pick_logpost"], "objective_name": "log posterior", "topology_ok": None, "n_topology_ok": 0,
                       "key_results": f"Studio {c4s['kinds']}, gap {c4s['gap_to_runner_up']:.2e}; spark1 {c4b['kinds']}, gap {c4b['gap_to_runner_up']:.2e}", "notes": "no failed equilibria"})
    for m in ("basin_7201", "anneal_7201"):
        x = g[m]
        d["steps"].append({"step": f"step4c_b_10c_{m}", "general_step": "fit_solid", "role": "lineage", "data_added": "none (10c global search from s4)", "free_parameters": 14,
                           "starts": 1, "modes": 1, "pick": "s4_perturbed (unchanged)", "objective": x["logpost_best"], "objective_name": "log posterior", "topology_ok": None, "n_topology_ok": 0,
                           "key_results": f"{x['n_evaluations']} evaluations ({x['n_invalid']} invalid), {x['n_local_solves']} local solves, best - s4 {x['status']['improvement_over_start']:.1e}, max |theta - s4| {x['best_theta_minus_s4_max_abs']:.1e} J/mol",
                           "notes": f"median visited logpost {x['logpost_median']:.1f}; seed 7201"})
    d["status_banner"] = ("Frozen 1.0.0 (draft until PI approval). Pick unchanged: step 4c-b s4, CrNi2 top 860 K (ORCHID 863 K), eutectic 1614 K (1618 K). "
                          "10a with the kink rule: step 3b pick s1 (kink-stationary) = the start TDB; step 4c-b 8/8 smooth on two machines. "
                          "10c basin hopping and dual annealing (1500 evaluations each): no better optimum. Notes as in 0.2.0-draft.")
    d["snapshot"]["note"] = "Frozen 1.0.0 review snapshot of the step-4 pick step4c-b after the 10a kink-rule re-checks and the 10c global search (6 Nov 2026 evening)."
    d["decisions"] = op.load_doc(op.ROOT / "specific/crni-paper-fit-step4c-b@1.0.0.yaml")["decisions"]
    d["next_actions"] = ["PI: approve crni-paper-fit-step4c-b@1.0.0.", "MCP-agent cold rerun (brief prepared, not launched).",
                         "Confirm as data: Pugliese gamma assignments, Curie marks, ORC-X3KVP7D3PO (second reader).",
                         "PI: fcc one-shot moves (+14.5 / +11.4 kJ) and the 2176 K BCC_A2 + LIQUID sliver - notes or action?", "Export campaign-added exclusions and records to the ORCHID intake."]
    d["computation"] = d.get("computation", []) + [
        {"host": "mac-studio and spark1", "what": "10a kink-rule re-checks (step 3b, step 4c-b)", "status": "finished"},
        {"host": "spark1", "what": "10c basin hopping and dual annealing (seed 7201, 1500 evaluations each)", "status": "finished"}]
    return d


if __name__ == "__main__":
    out = Path(sys.argv[1])
    doc = finite(crni4cb_v1())
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False, allow_nan=False))
    print(out, round(out.stat().st_size / 1e6, 2), "MB")
