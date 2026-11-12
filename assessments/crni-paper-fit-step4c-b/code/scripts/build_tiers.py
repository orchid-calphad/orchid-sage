"""Certainty tiers (fit_protocol 0, item 8; PI 6 Nov) for every ZPF record and every exclusion of the step-4 test T6.

Tiers: certain 10, less certain 50, uncertain 100 J/mol-atom. The tier sets the hinge sigma and the ZPF driving-force scale
(ESPEI ZPF weight = 1000 / tier, ESPEI's default scale being 1000 J/mol). Observed states: confidence 1.0. tau stays 100.

Classification (the 3x rule is the protocol's operational reading of "well inside"):
- ZPF records: every row is a boundary observation (tie-line end, partial tie-line, invariant, ordering temperature) -> uncertain 100.
- Exclusion cells at ZPF states (set E cells built from ZPF rows) -> uncertain 100 (on a boundary). CRNI2 exclusions at the
  797-875 K bcc+fcc states conflict with ORC-X3KVP7D3PO (CrNi2 ordering at 863 K) -> uncertain 100 (sources disagree).
- Other exclusion cells (fcc/bcc calorimetry states, liquid thermochemistry states, Pugliese states, fcc Curie marks):
  d = distance in units of the state's own uncertainty, sqrt(((T - Tb)/sigma_T)^2 + ((x - xb)/sigma_x)^2), to the nearest
  OBSERVED boundary point (ZPF vertices with known composition, the eutectic, the Pugliese Table III limits); also computed to
  the step-4 pick's boundaries (segment ends on a 5 K grid) and the smaller of the two is used (conservative).
  d > 3 -> certain 10; 1 < d <= 3 -> less certain 50; d <= 1 -> uncertain 100.
  Single source: the Pugliese states' phases rest only on Pugliese's own Table III limits -> at most 50.
  State uncertainties: Curie marks: record sigma_effective (K) and 0.011; others: ORCHID 'unknown' class 16 K and 0.011.
Outputs: data/hinge/step4_hinge_tiers.json, data/liq_tier/, data/solid_tier/, results/tiers.json."""
import copy
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model
import pd4

R = model.RUN
HAO = Path.home() / "data/private/crni-assessment-export-20261105/records.jsonl"
PUG = Path.home() / "data/private/crni-pugliese-export-20261105/records.jsonl"
TIER = {"certain": 10.0, "less_certain": 50.0, "uncertain": 100.0}


def observed_boundary_points():
    pts = []
    for g in ("liq", "solid"):
        for f in sorted((R / "data" / g).glob("zpf*.json")):
            d = json.loads(f.read_text())
            for T, row in zip(d["conditions"]["T"], d["values"]):
                for v in row:
                    if v[2][0] is not None and v[0] != "CRNI2":
                        pts.append((float(T), v[2][0] if v[1] == ["NI"] else 1 - v[2][0], f.name))
    for l in PUG.read_text().splitlines():
        r = json.loads(l)
        if r["property"] == "PHASE_COMPOSITION":
            for p in r["phase_compositions"]:
                pts.append((r["temperature_K"], p["composition"]["NI"], "pugliese1970 Table III"))
    return np.array([(a, b) for a, b, _ in pts]), [c for _, _, c in pts]


def model_boundary_points():
    TH = model.read_theta(R / "tdb/step4_solid_pick.tdb")
    T = np.arange(600.0, 2201.0, 5.0)
    di = pd4.diagram(TH, T, pd4.ref_grid(T))
    pts = []
    for t, segs in zip(T, di):
        for kind, phs, xl, xr in segs:
            if kind == 2 and (xr - xl) > 2.5 / (pd4.NX - 1):
                for x in (xl, xr):
                    if pd4.X[0] < x < pd4.X[-1]:
                        pts.append((t, x))
    return np.array(pts)


def dist(P, T, x, sT, sx):
    return float(np.min(np.hypot((P[:, 0] - T) / sT, (P[:, 1] - x) / sx)))


def main():
    OB, OBsrc = observed_boundary_points()
    MB = model_boundary_points()
    curie = {}
    for l in HAO.read_text().splitlines():
        r = json.loads(l)
        if r["property"] == "TRANSITION_TEMPERATURE":
            curie[r["id"]] = r["uncertainty_budget"]["quantities"]["value"]["sigma_effective"]
    H = json.loads((R / "data/hinge/step4_hinge_complete.json").read_text())
    cells, rows = [], []
    for c in H["cells"]:
        o = c.get("orchid", {})
        rec, ds = o.get("record"), o.get("dataset") or ""
        c2 = copy.deepcopy(c)
        if ds.startswith("zpf"):
            tier, basis, d = "uncertain", "exclusion at a ZPF state (boundary vertex)", None
            if "CRNI2" in c["penalize"] and c["T"] < 895 and abs(c["x"] - 2 / 3) < 0.05:
                basis += "; CRNI2 exclusion conflicts with ORC-X3KVP7D3PO (ordering 863 K)"
        else:
            sT, sx = (curie[rec], 0.011) if rec in curie else (16.0, 0.011)
            do, dm = dist(OB, c["T"], c["x"], sT, sx), dist(MB, c["T"], c["x"], sT, sx)
            d = min(do, dm)
            tier = "certain" if d > 3 else ("less_certain" if d > 1 else "uncertain")
            basis = f"distance {d:.1f} sigma to nearest boundary (observed {do:.1f}, model {dm:.1f}; sigma_T {sT} K, sigma_x {sx})"
            if "pugliese" in (o.get("reference") or "") and tier == "certain":
                tier, basis = "less_certain", basis + "; single source (phase from Pugliese's own Table III limits)"
        c2["sigma"] = TIER[tier]
        c2["confidence"] = 1.0
        c2["orchid"] = dict(o, tier=tier, tier_basis=basis)
        cells.append(c2)
        rows.append({"cell": rec or f"{ds}#{o.get('index')}", "T": c["T"], "x": c["x"], "expected": c["expected"], "penalize": c["penalize"],
                     "tier": tier, "sigma_J": TIER[tier], "distance_sigma": d, "basis": basis})
    H2 = dict(H, cells=cells, tier_rule="fit_protocol item 8 (PI 6 Nov): certain 10 / less certain 50 / uncertain 100; confidence 1.0")
    (R / "data/hinge/step4_hinge_tiers.json").write_text(json.dumps(H2, indent=1, default=float))
    zrows = []
    for g in ("liq", "solid"):
        dst = R / "data" / f"{g}_tier"
        dst.mkdir(parents=True, exist_ok=True)
        for f in sorted((R / "data" / g).glob("zpf*.json")):
            d = json.loads(f.read_text())
            d["weight"] = 1000.0 / TIER["uncertain"]
            d["comment"] = d.get("comment", "") + " | crni-paper-fit-20261106 tier TEST: every row a boundary observation -> uncertain tier, driving-force scale 100 J/mol (ESPEI weight 10)"
            (dst / f.name).write_text(json.dumps(d, indent=1))
            zrows.append({"file": f"{g}/{f.name}", "rows": len(d["values"]), "tier": "uncertain", "sigma_J": 100.0,
                          "basis": "boundary observations (tie-line ends / partial tie-lines / invariant / ordering temperature)"})
    from collections import Counter
    summ = {"hinge_cells_by_tier": dict(Counter(r["tier"] for r in rows)),
            "hinge_by_source_and_tier": {k: dict(v) for k, v in
                                         {s: Counter(r["tier"] for r in rows if s in str(r["cell"]) or s in json.dumps(r["basis"]))
                                          for s in ("zpf", "pugliese", "ORC-", "non-equilibrium", "hao_")}.items()},
            "zpf_rows_by_tier": {"uncertain": sum(z["rows"] for z in zrows)}}
    (R / "results/tiers.json").write_text(json.dumps({"summary": summ, "hinge_cells": rows, "zpf_files": zrows}, indent=1, default=float))
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
