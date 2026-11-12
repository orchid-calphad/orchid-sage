#!/usr/bin/env python3
"""Compare the step-4 tests with the current pick (step4_solid s1) on one yardstick (the step-4 data at their step-4 weights:
results/per_dataset_<run>.json from per_dataset.py). Log posteriors differ by objective and are NOT comparable across runs.
Writes results/step4_tests_comparison.json."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model

R = model.RUN
RUNS = ["step4_solid", "step4T2a_zpfsigma_samehinge", "step4T7_tiers_perphase", "step4c_combined", "step4c_b_hingefloor"]


def group(pd):
    g = {"ZPF_DF_rms_J_liquid": [], "ZPF_DF_rms_J_solid": [], "CRNI2_ordering_DF_J": None}
    th = {}
    for k, v in pd.items():
        if v["type"] == "ZPFResidual":
            if "CRNI2" in k:
                g["CRNI2_ordering_DF_J"] = v["rms_residual"]
            else:
                g["ZPF_DF_rms_J_liquid" if k.startswith("liq/") else "ZPF_DF_rms_J_solid"].append((v["n"], v["rms_residual"]))
        elif k.startswith("thermo/"):
            th[k.split("/", 1)[1][:60]] = round(v["rms_z"], 2)
        elif k.startswith("oneshot/"):
            th["oneshot:" + k.split("/", 1)[1].replace("oneshot_", "")[:40]] = round(v["mean_z"], 2)
    for key in ("ZPF_DF_rms_J_liquid", "ZPF_DF_rms_J_solid"):
        a = g[key]
        g[key] = float(np.sqrt(sum(n * r * r for n, r in a) / sum(n for n, _ in a))) if a else None
    return g, th


def main():
    out = {"note": "logpost is objective-specific (different weights/data per run) and not comparable across runs; the yardstick "
                   "columns use the step-4 data at the step-4 weights for every pick", "runs": {}}
    for r in RUNS:
        ev = json.loads((R / "steps" / r / "evaluation.json").read_text())
        pk = next(e for e in ev["evaluations"] if e["start"] == ev["pick"])
        t = pk["topology"]
        pd = json.loads((R / "results" / f"per_dataset_{r}.json").read_text())
        g, th = group(pd)
        modes = sorted({round(e["logpost"], 1) for e in ev["evaluations"]}, reverse=True)
        out["runs"][r] = {"pick": ev["pick"], "logpost_own_objective": pk["logpost"], "n_starts": len(ev["evaluations"]),
                          "distinct_logposts": modes, "starts_in_pick_mode": sum(abs(e["logpost"] - pk["logpost"]) < 0.05 for e in ev["evaluations"]),
                          "T_CrNi2_max": t["T_CrNi2_max"], "dT_CrNi2_vs_863": t["T_CrNi2_max"] - 863, "T_eut": t["T_liquid_min"],
                          "dT_eut_vs_1618": t["T_liquid_min"] - 1618, "topology_ok_strict": t["ok"], "n_bad_T": t["n_bad"], "gaps": len(t["gaps"]),
                          "within_25K_eut": abs(t["T_liquid_min"] - 1618) <= 25, "within_25K_CrNi2": abs(t["T_CrNi2_max"] - 863) <= 25,
                          "phase_at_x052_1473K": pk["phase_at_x052_1473K"], "plausibility_notes": pk["plausibility_notes"],
                          "theta": pk["theta_labeled"], **g, "thermo_rms_z_by_dataset": th}
    (R / "results/step4_tests_comparison.json").write_text(json.dumps(out, indent=1, default=float))
    keys = ["pick", "starts_in_pick_mode", "T_CrNi2_max", "T_eut", "topology_ok_strict", "n_bad_T", "gaps", "within_25K_eut", "within_25K_CrNi2",
            "phase_at_x052_1473K", "ZPF_DF_rms_J_liquid", "ZPF_DF_rms_J_solid", "CRNI2_ordering_DF_J"]
    for r, v in out["runs"].items():
        print(r, {k: (round(v[k], 1) if isinstance(v[k], float) else v[k]) for k in keys})
        print("   notes:", v["plausibility_notes"])
    ds = list(next(iter(out["runs"].values()))["thermo_rms_z_by_dataset"])
    print("dataset".ljust(62), " ".join(r[-12:].rjust(12) for r in out["runs"]))
    for d in ds:
        print(d.ljust(62), " ".join(str(out["runs"][r]["thermo_rms_z_by_dataset"].get(d)).rjust(12) for r in out["runs"]))


if __name__ == "__main__":
    main()
