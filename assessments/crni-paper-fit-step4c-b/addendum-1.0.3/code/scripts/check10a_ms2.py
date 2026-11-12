"""check10a_ms2 (7 Nov 2026, Q40 fix): check10a_ms.py with three changes, and only these:
(1) the default model module is model3 (no-CRNI2 database in memory, fail-closed record check), model2 still selectable;
(2) the re-evaluation of each start at its multistart theta must equal the multistart file's logpost within REEVAL_TOL = 1e-6
    (absolute, log-units); a larger difference is a FAILURE OF THE CHECK, not an ineligible start: the output is written with
    check_ok false, pick null and the mismatching starts listed, and the script exits with status 3 (so a plan item that chains
    pick10a.py with && stops). Q40: a silently changed objective was classed not_stationary and the pick moved;
(3) each row records the target's per-category record counts (model3 GradTarget.record_counts) when the module provides them.
The tests themselves (kink10a.py), eligibility and the pick rule are unchanged.

check10a_ms docstring follows.
fit_protocol 10a (with the PI's kink rule of 6 Nov 2026, orchid-sage 6b8f443) applied to every start of a multistart file, then the
10a pick. Same tests as check10a.py (definitions in kink10a.py); differences, and only these: the multistart file, the output path and
the model module are arguments (so the polished step-3b starts of both machines can be checked in their own staged roots), and a start
is eligible only when it is smooth or kink-stationary AND every data point that sits on a model boundary lies within its own
uncertainty (|r| <= sigma; agent's operational reading of 10a, labelled) AND no equilibrium failed (a failed equilibrium is a failure,
never a zero driving force; failed regions are re-evaluated at 3 seeded jitters of the ZPF vertex starting composition and reported).
Read only: nothing refitted.
  check10a_ms.py CONFIG MULTISTART_JSON OUT_JSON [NPROC] [MODEL=model|model2]   (run from the staged root; CONFIG relative to it)
  check10a_ms2.py CONFIG MULTISTART_JSON OUT_JSON [NPROC] [MODEL=model3|model2|model]"""
import json
import os
import sys
import time
import warnings
from multiprocessing import get_context
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")
R = Path(__file__).resolve().parents[1]
CFG, MS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
NPROC = int(sys.argv[4]) if len(sys.argv) > 4 else 4
MODEL = sys.argv[5] if len(sys.argv) > 5 else "model3"
REEVAL_TOL = 1e-6


def rerun_failed(r, data, j, p, seeds=(1, 2, 3)):
    """re-evaluate a failed hyperplane with the vertex compositions jittered by 1e-4 (seeded); the state itself is unchanged"""
    from espei.error_functions.zpf_error import estimate_hyperplane
    import copy
    pr = data["phase_regions"][j]
    out = []
    for s in seeds:
        rng = np.random.default_rng(s)
        try:
            pr2 = copy.copy(pr)
            vx2 = []
            for vx in pr.vertices:
                v = copy.copy(vx)
                if all(b is not None for b in vx.comp_conds.values()):
                    v.comp_conds = {a: float(b) + 1e-4 * rng.standard_normal() for a, b in vx.comp_conds.items()}
                vx2.append(v)
            pr2.vertices = vx2
            hp = estimate_hyperplane(pr2, data["dbf"], p)
            out.append({"seed": s, "finite": bool(np.all(np.isfinite(hp)))})
        except Exception as e:  # noqa
            out.append({"seed": s, "finite": False, "error": repr(e)[:200]})
    return out


def job(start):
    sys.path.insert(0, str(R / "scripts"))
    model = __import__(MODEL)
    import kink10a as K
    t0 = time.time()
    t = model.GradTarget(str(R / CFG))
    r = next(m for m in json.loads(Path(MS).read_text()) if m["start"] == start)
    th0 = np.asarray(r["theta"], float)[t.idx]; q0 = th0 / t.scale
    v0, g = t(q0)
    L = lambda th: t.value_only(np.asarray(th, float))
    el = K.eligibility(L, th0, t.scale, np.asarray(g, float))
    bp = K.boundary_points(t.res, th0, t.scale, groups=t.cat)
    fe = K.failed_equilibria(t.res, th0, groups=t.cat)
    if fe:
        from espei.error_functions.zpf_error import ZPFResidual
        for f in fe:
            for gi, rr in enumerate(t.res):
                if isinstance(rr, ZPFResidual) and t.cat[gi] == f["group"]:
                    p = np.asarray(th0, float)[rr._sorted_order]
                    for data in rr.zpf_data:
                        if data["dataset_reference"] == f["reference"]:
                            f["rerun_perturbed"] = rerun_failed(rr, data, f["region"], p)
    hk = []
    if t.hinge is not None:   # hinge: term-level one-sided check (min over configurations can switch)
        for i in range(len(th0)):
            e = np.zeros(len(th0)); e[i] = 1e-4 * t.scale[i]
            p0 = -t.hinge(th0)[0]; pp = -t.hinge(th0 + e)[0]; pm = -t.hinge(th0 - e)[0]
            f, b = (pp - p0) / 1e-4, (p0 - pm) / 1e-4
            if abs(f - b) > 1e-2 * (1 + abs(f)):
                hk.append([t.free[i], float(f), float(b)])
    n_out = sum(not b["within_own_uncertainty"] for b in bp)
    elig = bool(el["eligible"] and n_out == 0 and not fe)
    d_file = float(v0) - float(r["logpost"])
    return {"start": start, "logpost": float(v0), "logpost_multistart_file": r["logpost"], "reevaluation_minus_file": d_file,
            "reevaluation_matches_file": bool(abs(d_file) <= REEVAL_TOL), "record_counts": getattr(t, "record_counts", None), **el, "eligible_stationarity": el["eligible"],
            "eligible": elig, "boundary_points": bp, "n_boundary_points": len(bp), "n_boundary_points_outside_own_uncertainty": n_out,
            "hinge_unequal_sides": hk, "failed_equilibria": fe, "n_failed_equilibria": len(fe), "theta": [float(v) for v in th0],
            "seconds": round(time.time() - t0, 1)}


def main():
    import espei
    starts = [m["start"] for m in json.loads(Path(MS).read_text())]
    with get_context("spawn").Pool(NPROC) as p:
        rows = p.map(job, starts)
    mism = [{"start": r["start"], "reevaluation": r["logpost"], "multistart_file": r["logpost_multistart_file"],
             "difference": r["reevaluation_minus_file"]} for r in rows if not r["reevaluation_matches_file"]]
    el = [r for r in rows if r["eligible"]] if not mism else []
    pick = max(el, key=lambda r: r["logpost"]) if el else None
    els = sorted([r["logpost"] for r in el])
    out = {"config": CFG, "multistart": str(Path(MS).resolve()), "model_module": MODEL, "host": os.uname().nodename,
           "rule": "fit_protocol 10a with the kink rule (PI 6 Nov 2026, orchid-sage 6b8f443); tests scripts/kink10a.py; eligible = (smooth or kink-stationary) and every boundary point |r| <= sigma and no failed equilibrium",
           "espei_version": espei.__version__, "python": sys.executable,
           "reevaluation_tolerance": REEVAL_TOL, "check_ok": not mism, "reevaluation_mismatches": mism,
           "check_failure": (f"re-evaluation differs from the multistart file by more than {REEVAL_TOL} at {len(mism)} start(s); "
                             "the objective evaluated is not the one the multistart optimised (check failed, no pick)") if mism else None,
           "kinds": {k: sum(r["kind"] == k for r in rows) for k in ("smooth", "kink", "not_stationary")}, "n_eligible": len(el),
           "pick": pick["start"] if pick else None, "pick_logpost": pick["logpost"] if pick else None,
           "gap_to_runner_up": (els[-1] - els[-2]) if len(els) > 1 else None,
           "n_failed_equilibria_total": sum(r["n_failed_equilibria"] for r in rows), "rows": rows}
    Path(OUT).write_text(json.dumps(out, indent=1, default=float))
    for r in sorted(rows, key=lambda r: -r["logpost"]):
        print(r["start"], "%.5f" % r["logpost"], r["kind"], "elig", r["eligible"], "|g| %.1e" % r["grad_norm_scaled_analytic"], "worst", r["worst_direction"],
              "bp", r["n_boundary_points"], "out", r["n_boundary_points_outside_own_uncertainty"], "failed", r["n_failed_equilibria"], flush=True)
    print("kinds", out["kinds"], "eligible", out["n_eligible"], "pick", out["pick"], "gap", out["gap_to_runner_up"])
    if mism:
        print("CHECK FAILED:", out["check_failure"], mism, flush=True)
        sys.exit(3)


if __name__ == "__main__":
    main()
