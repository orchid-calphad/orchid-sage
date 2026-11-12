#!/usr/bin/env python3
"""Q39 minimal reproducer: gradient ESPEI (Gradient-based_update, 9039ea2) analytic vs finite-difference gradients
of ActivityResidual (Cr-Ni) and ZPFResidual (Cu-Zr) at fit endpoints.

    OMP_NUM_THREADS=1 python reproduce_q39.py [crni|cuzr|all]

For each case, at the fit endpoint theta* and in the optimiser coordinates q (Cr-Ni q = theta/scale with scale 1000 for
a terms and 1 for b terms; Cu-Zr z = (theta - theta*)/scale with scale 3 for T terms and max(5 %|start value|, 1) otherwise):
  1. analytic gradient vs central FD at steps 1e-3, 1e-4, 1e-5 (central FD is step-independent, and differs from analytic);
  2. forward and backward one-sided slopes at steps 1e-4 and 1e-6 (they differ from each other at every step, so theta*
     sits on a kink of the residual; the analytic gradient is the derivative of the assemblage found at theta*);
  3. the equilibrium assemblage at the data point at theta* and at theta* +/- 1e-4 along the largest-discrepancy coordinate;
  4. analytic vs central FD at three nearby points theta* + 1e-2 * scale * N(0,1) (seeds 1, 2, 3): agreement < 1e-4 relative.
Writes results_<case>.json next to this script.
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")
from pycalphad import Database, Workspace, variables as v
from espei.datasets import load_datasets
from espei.error_functions.context import setup_context
from espei.utils import unpack_piecewise

HERE = Path(__file__).resolve().parent
D = HERE / "data"
EP = json.loads((D / "endpoints.json").read_text())


def crni():
    e = EP["crni"]; names = e["symbols"]; th = np.array(e["theta"], float)
    sc = np.array([1.0 if n in ("VV0001", "VV0003", "VV0005", "VV0007", "VV0009", "VV0011", "VV0013") else 1000.0 for n in names])
    db = Database(str(D / "crni.tdb"))
    ctx = setup_context(db, load_datasets([str(D / "crni_activity_1073K_xCr0.35.json")]), names)
    res = [r for r in ctx["residual_objs"] if type(r).__name__ == "ActivityResidual"][0]

    def assemblage(t):
        w = Workspace(database=db, components=["CR", "NI", "VA"], phases=["BCC_A2", "CRNI2", "FCC_A1", "LIQUID"],
                      conditions={v.P: 101325, v.T: 1073.15, v.X("CR"): 0.35, v.N: 1}, parameters=dict(zip(names, t)))
        ph = [str(p) for p in np.ravel(w.eq.Phase) if str(p)]
        return {"phases": ph, "NP": [float(x) for x in np.ravel(w.eq.NP)[:len(ph)]], "MU_CR": float(w.get(v.MU("CR")))}
    return "crni", names, th, sc, res, assemblage


def cuzr():
    e = EP["cuzr"]; names = e["symbols"]; th = np.array(e["theta"], float)
    db = Database(str(D / "cuzr.tdb"))
    xm = np.array([unpack_piecewise(db.symbols[s]) for s in names], float)   # the H1 start values (from the step-2 TDB)
    sc = np.array([3.0 if n in e["T_terms"] else max(abs(x) * 0.05, 1.0) for n, x in zip(names, xm)])
    files = [str(D / "cuzr_zpf_turchanin2008_1268K.json"), str(D / "cuzr_zpf_lundin1953_1268K.json")]
    ctx = setup_context(db, load_datasets(files), names)
    res = [r for r in ctx["residual_objs"] if type(r).__name__ == "ZPFResidual"][0]
    phases = ["BCC_A2", "CU10ZR7", "CU51ZR14", "CU5ZR_C15B", "CU8ZR3", "CUZR2", "CUZR_B2", "FCC_A1", "LIQUID"]

    def assemblage(t):
        out = {}
        for x in (0.72, 0.94):   # the hyperplane vertices of the Turchanin region
            w = Workspace(database=db, components=["CU", "ZR", "VA"], phases=phases,
                          conditions={v.P: 101325, v.T: 1268.0, v.X("ZR"): x, v.N: 1}, parameters=dict(zip(names, t)))
            ph = [str(p) for p in np.ravel(w.eq.Phase) if str(p)]
            out[f"x_Zr={x}"] = {"phases": ph, "NP": [float(y) for y in np.ravel(w.eq.NP)[:len(ph)]]}
        return out
    return "cuzr", names, th, sc, res, assemblage


def check(case):
    label, names, th, sc, res, assemblage = case
    n = len(th)
    L = lambda q: float(res.get_likelihood(th + sc * q))

    def LG(q):
        val, g = res.get_likelihood_and_gradient(th + sc * q)
        return float(val), np.asarray(g, float) * sc

    def central(q, h):
        return np.array([(L(q + h * np.eye(n)[i]) - L(q - h * np.eye(n)[i])) / (2 * h) for i in range(n)])

    def one_sided(q, h):
        l0 = L(q)
        return (np.array([(L(q + h * np.eye(n)[i]) - l0) / h for i in range(n)]),
                np.array([(l0 - L(q - h * np.eye(n)[i])) / h for i in range(n)]))
    q0 = np.zeros(n)
    val, g = LG(q0)
    out = {"case": label, "symbols": names, "logL": val, "analytic": g.tolist(), "analytic_norm": float(np.linalg.norm(g)), "central": {}, "one_sided": {}}
    for h in (1e-3, 1e-4, 1e-5):
        c = central(q0, h)
        out["central"][str(h)] = {"norm": float(np.linalg.norm(c)), "diff_norm": float(np.linalg.norm(c - g)), "values": c.tolist()}
    for h in (1e-4, 1e-6):
        f, b = one_sided(q0, h)
        out["one_sided"][str(h)] = {"forward": f.tolist(), "backward": b.tolist(), "fwd_minus_bwd_norm": float(np.linalg.norm(f - b)),
                                     "analytic_minus_fwd_norm": float(np.linalg.norm(g - f)), "analytic_minus_bwd_norm": float(np.linalg.norm(g - b))}
    c = np.array(out["central"]["0.0001"]["values"]); i = int(np.argmax(np.abs(c - g)))
    out["largest_discrepancy"] = {"symbol": names[i], "analytic": float(g[i]), "central_1e-4": float(c[i]),
                                  "forward_1e-6": out["one_sided"]["1e-06"]["forward"][i], "backward_1e-6": out["one_sided"]["1e-06"]["backward"][i],
                                  "assemblage_at_theta*": assemblage(th),
                                  "assemblage_at_+1e-4": assemblage(th + sc * 1e-4 * np.eye(n)[i]),
                                  "assemblage_at_-1e-4": assemblage(th - sc * 1e-4 * np.eye(n)[i])}
    out["nearby_points"] = []
    for seed in (1, 2, 3):
        q = 1e-2 * np.random.default_rng(seed).standard_normal(n)
        _, gq = LG(q); cq = central(q, 1e-4); f, b = one_sided(q, 1e-6)
        out["nearby_points"].append({"seed": seed, "analytic_norm": float(np.linalg.norm(gq)), "central_norm": float(np.linalg.norm(cq)),
                                     "rel_diff": float(np.linalg.norm(gq - cq) / np.linalg.norm(cq)),
                                     "kink_metric_fwd_minus_bwd_1e-6": float(np.linalg.norm(f - b))})
    (HERE / f"results_{label}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("case", "logL", "analytic_norm")}))
    print("  central FD:", {h: (round(r["norm"], 6), round(r["diff_norm"], 6)) for h, r in out["central"].items()}, "(norm, |analytic - FD|)")
    print("  one-sided:", {h: (round(r["fwd_minus_bwd_norm"], 6), round(r["analytic_minus_fwd_norm"], 6), round(r["analytic_minus_bwd_norm"], 6))
                           for h, r in out["one_sided"].items()}, "(|fwd-bwd|, |an-fwd|, |an-bwd|)")
    print("  largest:", json.dumps(out["largest_discrepancy"]))
    print("  nearby points:", [(r["seed"], f'{r["rel_diff"]:.2e}') for r in out["nearby_points"]])


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("crni", "all"):
        check(crni())
    if which in ("cuzr", "all"):
        check(cuzr())
