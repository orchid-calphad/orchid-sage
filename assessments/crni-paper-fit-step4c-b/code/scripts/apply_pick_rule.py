"""Pick rule (fit_protocol 10a, PI 6 Nov): a start is eligible only if converged with |g|_q < GTOL (1e-3, optimiser scaling);
among eligible starts the objective decides (no grid quantities). Reports each pick's |g| and the gap to the runner-up (best eligible
start in a different mode, |dlogpost| > 1e-3) and the mode table. usage: apply_pick_rule.py <step> [<step> ...]"""
import json, sys
from pathlib import Path
R = Path(__file__).resolve().parents[1]
GTOL = 1e-3
out = {}
for step in sys.argv[1:]:
    ev = json.loads((R / "steps" / step / "evaluation.json").read_text())
    E = sorted(ev["evaluations"], key=lambda e: -e["logpost"])
    el = [e for e in E if e["grad_norm_q"] < GTOL and e["final"].startswith("converged")]
    modes = []
    for e in E:
        for m in modes:
            if abs(m["logpost"] - e["logpost"]) < 1e-2:
                m["starts"].append(e["start"]); m["max_grad"] = max(m["max_grad"], e["grad_norm_q"]); break
        else:
            t = e["topology"]
            modes.append({"logpost": e["logpost"], "starts": [e["start"]], "max_grad": e["grad_norm_q"], "T_eut": t["T_liquid_min"],
                          "T_CrNi2": t["T_CrNi2_max"], "n_bad": t["n_bad"], "gap_T": t["n_gap_T"], "point": e["phase_at_x052_1473K"]})
    pick = el[0] if el else None
    ru = next((e for e in el[1:] if abs(e["logpost"] - pick["logpost"]) > 1e-3), None) if pick else None
    out[step] = {"gtol": GTOL, "n_eligible": len(el), "pick": pick["start"] if pick else None, "pick_logpost": pick["logpost"] if pick else None,
                 "pick_grad_norm_q": pick["grad_norm_q"] if pick else None, "runner_up": ru["start"] if ru else None,
                 "gap_to_runner_up": (pick["logpost"] - ru["logpost"]) if ru else None,
                 "gap_to_next_start": (pick["logpost"] - el[1]["logpost"]) if len(el) > 1 else None, "modes": modes,
                 "not_eligible": [(e["start"], e["grad_norm_q"]) for e in E if e not in el]}
    print(step, {k: v for k, v in out[step].items() if k != "modes"})
    for m in modes: print("   mode", round(m["logpost"], 3), len(m["starts"]), "maxg %.1e" % m["max_grad"], m["T_eut"], m["T_CrNi2"], m["n_bad"], m["gap_T"], m["point"])
p = R / "results/pick_rule_step4_variants.json"
old = json.loads(p.read_text()) if p.exists() else {}
old.update(out); p.write_text(json.dumps(old, indent=1, default=float))
