#!/usr/bin/env python3
"""Per-step summary table -> results/step_summary.json (from steps/<step>/evaluation.json, run cards and configs)."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model

R = model.RUN
STEPS = ["step1_oneshot", "step2_liquidus", "step3_thermo", "step3b_thermo_crni2free", "step4_solid"]


def modes(evals, tol=0.05):
    out = []
    for e in sorted(evals, key=lambda z: -z["logpost"]):
        for m in out:
            if abs(m["logpost"] - e["logpost"]) < tol * max(1, abs(m["logpost"]) * 1e-4) or \
                    np.allclose(np.asarray(m["theta"]) / model.SCALE_ALL, np.asarray(e["theta"]) / model.SCALE_ALL, atol=0.05):
                m["members"].append(e["start"])
                break
        else:
            out.append({"logpost": e["logpost"], "theta": e["theta"], "members": [e["start"]], "topology_ok": e["topology"]["ok"],
                        "T_eut": e["topology"]["T_liquid_min"], "T_CrNi2": e["topology"]["T_CrNi2_max"], "n_bad": e["topology"]["n_bad"]})
    return out


def main():
    rows = []
    for s in STEPS:
        p = R / "steps" / s / "evaluation.json"
        if not p.exists():
            continue
        ev = json.loads(p.read_text())
        cfg = json.loads((R / "steps/configs" / f"{s}.json").read_text())
        pk = next(e for e in ev["evaluations"] if e["start"] == ev["pick"])
        card = json.loads((R / "steps" / s / "run_card.json").read_text())
        t = pk["topology"]
        rows.append({
            "step": s, "groups": cfg["groups"], "hinge": cfg.get("hinge"), "free": cfg["free"], "n_data_files": len(card.get("data_files", [])),
            "espei_version": card.get("espei_version"), "n_starts": len(ev["evaluations"]), "modes": modes(ev["evaluations"]),
            "pick": ev["pick"], "logpost": pk["logpost"], "parts": pk["parts"], "theta": pk["theta_labeled"],
            "topology_ok": t["ok"], "T_eut": t["T_liquid_min"], "T_CrNi2_max": t["T_CrNi2_max"], "n_bad_T": t["n_bad"],
            "bad_T_range": t["bad_T_range"], "bad_examples": t["bad"][:3], "gaps": t["gaps"][:3], "severity": t["spurious_severity"],
            "pure_elements_ok": pk["pure_elements"]["ok"], "plausible": pk["plausible"], "plausibility_notes": pk["plausibility_notes"],
            "oneshot_shifts_sigma": {o["id"]: round(o["shift_sigma"], 3) for o in pk["oneshot_shifts"]},
            "oneshot_shifts_J": {o["id"]: round(o["shift_J"]) for o in pk["oneshot_shifts"]},
            "moved_from_oneshot_sigma": {o["id"]: round(o["shift_from_oneshot_model_sigma"], 3) for o in pk["oneshot_shifts"]},
            "moved_from_oneshot_J": {o["id"]: round(o["shift_from_oneshot_model_J"]) for o in pk["oneshot_shifts"]},
            "max_abs_shift_sigma": pk["max_abs_shift_sigma"], "liquid_S_ex_z": {z["state"]: round(z["z"], 2) for z in pk["liquid_S_ex"]},
            "phase_at_x052_1473K": pk["phase_at_x052_1473K"]})
    (R / "results/step_summary.json").write_text(json.dumps(rows, indent=1, default=float))
    for r in rows:
        print(f"{r['step']:15s} starts {r['n_starts']} modes {len(r['modes'])} pick {r['pick']:14s} lp {r['logpost']:10.1f} "
              f"top {r['topology_ok']!s:5} Teut {r['T_eut']:.0f} TCrNi2 {r['T_CrNi2_max']:.0f} nbad {r['n_bad_T']} sev {r['severity']} "
              f"maxshift {r['max_abs_shift_sigma']:.2f} plaus {r['plausible']} pt {r['phase_at_x052_1473K']}")
        print("   residual vs one-shot obs (sigma):", r["oneshot_shifts_sigma"])
        print("   moved from one-shot model (sigma):", r["moved_from_oneshot_sigma"])
        print("   parts:", {k: round(v, 1) for k, v in r["parts"].items()}, "notes:", r["plausibility_notes"])
        print("   modes:", [(round(m["logpost"], 2), len(m["members"]), m["topology_ok"], m["T_eut"], m["T_CrNi2"]) for m in r["modes"]])


if __name__ == "__main__":
    main()
