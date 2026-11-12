"""fit_protocol 10a with the PI's kink rule (6 Nov 2026, orchid-sage 6b8f443) applied to every start of a Cr-Ni step, then the 10a
pick. Read only: the step's own objective (model2.GradTarget, same config) at each start's endpoint (multistart.json theta); nothing
refitted; thresholds as stated in the plan (1e-3, steps 1e-6/1e-5/1e-4, improvement 1e-6). Test definitions: scripts/kink10a.py.
Pick: among eligible starts (smooth or kink), the highest objective (near-ties by the objective, never by grid quantities).
  check10a.py STEP [NPROC]  -> results/check10a_<STEP>.json"""
import json
import sys
import warnings
from multiprocessing import get_context
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")
R = Path(__file__).resolve().parents[1]
STEP = sys.argv[1]; NPROC = int(sys.argv[2]) if len(sys.argv) > 2 else 4


def job(start):
    sys.path.insert(0, str(R / "scripts"))
    import model2 as model
    import kink10a as K
    t = model.GradTarget(str(R / f"steps/configs/{STEP}.json"))
    r = next(m for m in json.loads((R / f"steps/{STEP}/multistart.json").read_text()) if m["start"] == start)
    th0 = np.asarray(r["theta"], float)[t.idx]; q0 = th0 / t.scale
    v0, g = t(q0)
    L = lambda th: t.value_only(np.asarray(th, float))
    el = K.eligibility(L, th0, t.scale, np.asarray(g, float))
    bp = K.boundary_points(t.res, th0, t.scale, groups=t.cat)
    fe = K.failed_equilibria(t.res, th0, groups=t.cat)
    if t.hinge is not None:   # hinge: term-level one-sided check (min over configurations can switch)
        hk = []
        for i in range(len(th0)):
            e = np.zeros(len(th0)); e[i] = 1e-4 * t.scale[i]
            p0 = -t.hinge(th0)[0]; pp = -t.hinge(th0 + e)[0]; pm = -t.hinge(th0 - e)[0]
            f, b = (pp - p0) / 1e-4, (p0 - pm) / 1e-4
            if abs(f - b) > 1e-2 * (1 + abs(f)):
                hk.append([t.free[i], float(f), float(b)])
    else:
        hk = []
    return {"start": start, "logpost": float(v0), **el, "boundary_points": bp, "n_boundary_points": len(bp),
            "n_boundary_points_outside_own_uncertainty": sum(not b["within_own_uncertainty"] for b in bp),
            "hinge_unequal_sides": hk, "failed_equilibria": fe, "n_failed_equilibria": len(fe)}


def main():
    starts = [m["start"] for m in json.loads((R / f"steps/{STEP}/multistart.json").read_text())]
    with get_context("spawn").Pool(NPROC) as p:
        rows = p.map(job, starts)
    el = [r for r in rows if r["eligible"]]
    pick = max(el, key=lambda r: r["logpost"]) if el else None
    out = {"step": STEP, "rule": "fit_protocol 10a with the kink rule (PI 6 Nov 2026, orchid-sage 6b8f443); scripts/kink10a.py", "espei_version": __import__("espei").__version__,
           "kinds": {k: sum(r["kind"] == k for r in rows) for k in ("smooth", "kink", "not_stationary")}, "n_eligible": len(el),
           "pick": pick["start"] if pick else None, "pick_logpost": pick["logpost"] if pick else None,
           "gap_to_runner_up": (pick["logpost"] - sorted([r["logpost"] for r in el])[-2]) if len(el) > 1 else None,
           "n_failed_equilibria_total": sum(r["n_failed_equilibria"] for r in rows), "rows": rows}
    (R / f"results/check10a_{STEP}.json").write_text(json.dumps(out, indent=1, default=float))
    for r in sorted(rows, key=lambda r: -r["logpost"]):
        print(r["start"], "%.4f" % r["logpost"], r["kind"], "|g| %.1e" % r["grad_norm_scaled_analytic"], "worst", r["worst_direction"], "boundary pts", r["n_boundary_points"],
              "outside sigma", r["n_boundary_points_outside_own_uncertainty"], "hinge kinks", len(r["hinge_unequal_sides"]), "failed eq", r["n_failed_equilibria"])
    print("kinds", out["kinds"], "eligible", out["n_eligible"], "pick", out["pick"], "gap", out["gap_to_runner_up"])


if __name__ == "__main__":
    main()
