"""step4c-b (labelled variant, one change against step4c): hinge sigma per (state, excluded phase) = max(tier3 sigma, the state's own
uncertainty converted to energy) - the same floor the PI adopted for ZPF sigma (converted, floored at tier), applied to the hinge.
Converted values from results/hinge_observed_sigma.json (build_hinge_observed.py: sqrt((sigma_T dDG/dT)^2 + (sigma_x G''|y-x|)^2) at the
step-4 pick, floor 100 J). Everything else identical to data/hinge/step4c_hinge.json. Writes data/hinge/step4c_hinge_floor.json."""
import json
from pathlib import Path
R = Path(__file__).resolve().parents[1]
conv = {}
for r in json.loads((R / "results/hinge_observed_sigma.json").read_text())["rows"]:
    conv[(round(r["T"], 2), round(r["x"], 6), r["penalized"])] = r["sigma_raw_J"]
H = json.loads((R / "data/hinge/step4c_hinge.json").read_text())
n, raised = 0, []
for c in H["cells"]:
    for p in list(c["sigma"]):
        s = conv.get((round(c["T"], 2), round(c["x"], 6), p))
        if s is not None and s > c["sigma"][p]:
            raised.append([c["T"], round(c["x"], 4), p, c["sigma"][p], round(s, 1)])
            c["sigma"][p] = float(s)
        n += 1
H["step4c_b_rule"] = "hinge sigma = max(tier, converted state uncertainty)"
(R / "data/hinge/step4c_hinge_floor.json").write_text(json.dumps(H, indent=1))
json.dump({"pairs": n, "raised": len(raised), "rows": raised}, open(R / "results/step4c_b_hinge_floor.json", "w"), indent=1)
import collections
print(n, "pairs;", len(raised), "raised; by phase", collections.Counter(r[2] for r in raised))
print(sorted(raised, key=lambda r: -r[4])[:6])
