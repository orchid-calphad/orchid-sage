"""PI rule 6 Nov ("if a phase is not present, that is a very strong signal"): exclusions at OBSERVED states enter at confidence 1.0
with sigma = the state's own uncertainty converted to energy, never looser than... (floor) tau = 100 J/mol-atom; option C stays only
for exclusions assumed from a diagram at non-observed states (none in this hinge: every cell sits at an observed state).

Input: data/hinge/step4_hinge_complete.json (all cells at observed states). Output: data/hinge/step4_hinge_observed.json and
results/hinge_observed_sigma.json (per record and penalized phase).

Per cell and penalized phase p (sigma given per phase, which the PhaseForge+ hinge accepts):
  DG_p(y) = G_p(y) - H(y), H the cell's target line (one expected phase e: tangent of G_e at x; two: line through the tie-line ends),
  y = argmin DG_p (CRNI2: 2/3), all from the current step-4 pick (step4_solid s1);
  temperature term  dDG/dT at y (central difference +-1 K, same construction)        x sigma_T
  composition term  |G_e''(x) (y - x)| (shift of the target line at y when the state moves by sigma_x; for two expected phases
                     the nearer end and its phase)                                       x sigma_x
  sigma_p = max(100, sqrt((sigma_T dDG/dT)^2 + (sigma_x comp)^2))
State uncertainties: fcc Curie marks: the record's own ORCHID sigma_effective (K) and X_PHASE 0.011; all other states (set E ZPF
states, liquid/solid thermochemistry states, Pugliese states): ORCHID 'unknown' class, T 16 K, x 0.011 (no printed uncertainty).
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model
import pd4

R = model.RUN
TH = model.read_theta(R / "tdb/step4_solid_pick.tdb")
HAO = Path.home() / "data/private/crni-assessment-export-20261105/records.jsonl"
TAU = 100.0
X = pd4.X
IDX = {"BCC_A2": 0, "FCC_A1": 1, "LIQUID": 2}


def Gall(T):
    G, gc2 = pd4.G_at(TH, [T], pd4.ref_grid(np.array([T])))
    return G[:, 0, :], float(gc2[0])


def line(G, cell):
    exp = cell["expected"]
    if len(exp) == 1:
        g = G[IDX[exp[0]]]
        j = int(np.clip(np.searchsorted(X, cell["x"]), 1, len(X) - 2))
        s = (g[j + 1] - g[j - 1]) / (X[j + 1] - X[j - 1])
        return lambda y: g[j] + s * (y - X[j]), [(exp[0], X[j])]
    ends = [(p, float(cell["tie_line"][p])) for p in exp]
    pts = []
    for p, xe in ends:
        j = int(np.clip(np.searchsorted(X, xe), 1, len(X) - 2))
        pts.append((X[j], G[IDX[p]][j], p))
    (x1, g1, _), (x2, g2, _) = sorted(pts)
    return lambda y: g1 + (g2 - g1) * (y - x1) / (x2 - x1), [(p, xx) for xx, _, p in pts]


def dg(T, cell, p):
    G, gc2 = Gall(T)
    H, anchors = line(G, cell)
    if p == "CRNI2":
        return gc2 - H(2 / 3), 2 / 3, anchors, G
    d = G[IDX[p]] - H(X)
    k = int(np.argmin(d))
    return float(d[k]), float(X[k]), anchors, G


def main():
    H0 = json.loads((R / "data/hinge/step4_hinge_complete.json").read_text())
    curie = {}
    for l in HAO.read_text().splitlines():
        r = json.loads(l)
        if r["property"] == "TRANSITION_TEMPERATURE":
            curie[r["id"]] = r["uncertainty_budget"]["quantities"]["value"]["sigma_effective"]
    out, rows = [], []
    for c in H0["cells"]:
        rec = c.get("orchid", {}).get("record")
        sT, sx = (curie[rec], 0.011) if rec in curie else (16.0, 0.011)
        sig = {}
        for p in c["penalize"]:
            d0, y, anchors, G = dg(c["T"], c, p)
            dp, _, _, _ = dg(c["T"] + 1, c, p)
            dm, _, _, _ = dg(c["T"] - 1, c, p)
            dTd = abs(dp - dm) / 2.0
            pe, xe = min(anchors, key=lambda a: abs(a[1] - y))
            g = G[IDX[pe]]
            j = int(np.clip(np.searchsorted(X, xe), 1, len(X) - 2))
            gpp = (g[j + 1] - 2 * g[j] + g[j - 1]) / ((X[j + 1] - X[j]) * (X[j] - X[j - 1]))
            comp = abs(gpp * (y - xe))
            raw = float(np.hypot(sT * dTd, sx * comp))
            sig[p] = max(TAU, raw)
            rows.append({"record": rec or f"{c['orchid'].get('dataset')}#{c['orchid'].get('index')}", "T": c["T"], "x": c["x"],
                         "expected": c["expected"], "penalized": p, "DG_at_pick_J": d0, "y": y, "dDG_dT": dTd, "comp_J_per_x": comp,
                         "sigma_T": sT, "sigma_x": sx, "sigma_raw_J": raw, "sigma_J": sig[p], "floor_active": raw < TAU})
        c2 = dict(c)
        c2["sigma"] = sig
        c2["confidence"] = 1.0
        c2["orchid"] = dict(c["orchid"], observed_state_rule="PI 6 Nov: exclusion at an observed state, confidence 1.0, sigma converted from the state's uncertainty (floor tau 100)")
        out.append(c2)
    H = dict(H0, cells=out, confidence_rule="observed states: 1.0; option C only for exclusions assumed from a diagram (none here)")
    (R / "data/hinge/step4_hinge_observed.json").write_text(json.dumps(H, indent=1, default=float))
    s = np.array([r["sigma_J"] for r in rows])
    summ = {"n_cells": len(out), "n_penalized_pairs": len(rows), "sigma_J_percentiles_0_5_50_95_100": np.percentile(s, [0, 5, 50, 95, 100]).tolist(),
            "n_floor_active": int(sum(r["floor_active"] for r in rows)),
            "by_penalized": {p: np.percentile([r["sigma_J"] for r in rows if r["penalized"] == p], [0, 50, 100]).tolist()
                             for p in ("BCC_A2", "FCC_A1", "LIQUID", "CRNI2") if any(r["penalized"] == p for r in rows)},
            "violated_at_pick_DG_below_tau": int(sum(r["DG_at_pick_J"] < TAU for r in rows))}
    (R / "results/hinge_observed_sigma.json").write_text(json.dumps({"summary": summ, "rows": rows}, indent=1, default=float))
    print(json.dumps(summ))


if __name__ == "__main__":
    main()
