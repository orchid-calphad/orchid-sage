"""Residual-level gradient check with kink classification (gradient ESPEI ActivityResidual / ZPFResidual).

For every residual r_k: analytic dr_k/dq vs central, forward and backward FD (step h in optimiser coordinates q).
A residual is 'kinked' at the point when its one-sided slopes differ (|fwd - bwd| > ktol*(1+|fwd|)).
The likelihood gradient sum_k (-r_k/s_k^2) dr_k/dq is split into smooth and kinked residuals.

  python kinkcheck.py crni ROOT MULTISTART_JSON START [--perturb SEED EPS]
      ROOT holds tdb/step2_liquidus_pick.tdb and data/thermo/*.json (from assessments/crni-paper-fit-step4-s1:
      evidence/reference_outputs/tdb, evidence/files/thermo); MULTISTART_JSON e.g. reproduce/crni-step3b-polish-spark1/multistart_prepolish.json
  python kinkcheck.py cuzr ROOT CONFIG RESULT_JSON [--perturb SEED EPS]
      ROOT holds tdb/step2_liquidus.tdb and liq/*.json (from assessments/cuzr-oneshot-h2-s7: evidence/reference_outputs/tdb,
      evidence/files/liq); CONFIG evidence/model_inputs/steps/configs/stepH1_topology_hinge.json; RESULT_JSON reproduce/cuzr-h1-polish-spark1/s<k>/result_prepolish.json
"""
import json, sys, glob, warnings, time
import numpy as np
warnings.filterwarnings("ignore")
from pycalphad import Database
from espei.datasets import load_datasets
from espei.utils import unpack_piecewise

A = sys.argv
H = float(A[A.index("--h") + 1]) if "--h" in A else 1e-4
KTOL = 1e-2


def setup_crni(root, ms, start):
    from espei.error_functions.activity_error import calculate_activity_residuals
    from espei.error_functions.context import setup_context
    names = [f"VV{i:04d}" for i in range(14)]
    sc = np.array([1000. if i % 2 == 0 else 1. for i in range(14)])
    th = np.array(next(r for r in json.load(open(ms)) if r["start"] == start)["theta"], float)
    db = Database(f"{root}/tdb/step2_liquidus_pick.tdb")
    ds = load_datasets(sorted(glob.glob(f"{root}/data/thermo/*.json")))
    ctx = setup_context(db, ds, names)
    act = [r for r in ctx["residual_objs"] if type(r).__name__ == "ActivityResidual"][0]
    kw = act._activity_likelihood_kwargs

    def resid(x, grad=False):
        p = dict(zip(names, np.asarray(x, float).tolist()))
        out = calculate_activity_residuals(parameters=p, compute_gradient=grad, **kw)
        return [np.asarray(o, float) for o in out]
    return th, sc, resid, (lambda x: act.get_likelihood(np.asarray(x, float))), (lambda x: act.get_likelihood_and_gradient(np.asarray(x, float)))


def setup_cuzr(root, cfgp, resp):
    from espei.error_functions.context import setup_context
    from espei.error_functions.zpf_error import ZPFResidual, calculate_zpf_driving_forces
    cfg = json.load(open(cfgp)); free = sorted(cfg["free"])
    db = Database(f"{root}/tdb/step2_liquidus.tdb")
    xm = np.array([unpack_piecewise(db.symbols[s]) for s in free], float)
    isT = np.array([s in cfg["T_terms"] for s in free])
    sc = np.array([3.0 if isT[i] else max(abs(xm[i]) * 0.05, 1.0) for i in range(len(free))])
    x = np.asarray(json.load(open(resp))["x_best"], float)
    ctx = setup_context(db, load_datasets(sorted(glob.glob(f"{root}/liq/*.json"))), free)
    z = [r for r in ctx["residual_objs"] if isinstance(r, ZPFResidual)][0]
    inv = np.empty_like(z._sorted_order); inv[z._sorted_order] = np.arange(len(x))

    def resid(xx, grad=False):
        p = np.asarray(xx, float)[z._sorted_order]
        out = calculate_zpf_driving_forces(z.zpf_data, p, short_circuit=False, compute_gradient=grad)
        r = np.concatenate(out[0]).astype(float); w = 1000.0 / z.weight / np.concatenate(out[1]).astype(float)
        if not grad:
            return r, w
        J = np.reshape([g for dg in out[2] for g in dg], (r.size, len(xx)))[:, inv]
        return r, w, J
    return x, sc, resid, (lambda xx: z.get_likelihood(np.asarray(xx, float))), (lambda xx: z.get_likelihood_and_gradient(np.asarray(xx, float)))


def main():
    t0 = time.time()
    if A[1] == "crni":
        x, sc, resid, lik, likg = setup_crni(A[2], A[3], A[4])
        label = f"crni:{A[4]}"
    else:
        x, sc, resid, lik, likg = setup_cuzr(A[2], A[3], A[4])
        label = f"cuzr:{A[4]}"
    if "--perturb" in A:
        i = A.index("--perturb"); seed, eps = int(A[i + 1]), float(A[i + 2])
        x = x + sc * eps * np.random.default_rng(seed).standard_normal(len(x))
        label += f":perturb(seed={seed},eps={eps})"
    n = len(x)
    t1 = time.time(); v, g = likg(x); t_grad = time.time() - t1
    t1 = time.time(); lik(x); t_val = time.time() - t1
    g = np.asarray(g, float) * sc
    r, w, J = resid(x, grad=True)
    J = J * sc
    plus, minus = [], []
    for i in range(n):
        e = np.zeros(n); e[i] = H * sc[i]
        plus.append(resid(x + e)[0]); minus.append(resid(x - e)[0])
    plus, minus = np.array(plus).T, np.array(minus).T     # (residuals, params)
    fwd, bwd, cen = (plus - r[:, None]) / H, (r[:, None] - minus) / H, (plus - minus) / (2 * H)
    kinked = np.any(np.abs(fwd - bwd) > KTOL * (1 + np.abs(fwd)), axis=1)
    coef = -r / w ** 2                                   # d logpdf / d r
    gl_an = coef @ J; gl_fd = coef @ cen
    sm, kk = ~kinked, kinked
    # term-level central FD of the likelihood (as in the 6 Nov check)
    fdL = np.array([(lik(x + np.eye(n)[i] * H * sc[i]) - lik(x - np.eye(n)[i] * H * sc[i])) / (2 * H) for i in range(n)])
    rows = []
    for k in np.where(kinked)[0]:
        rows.append({"k": int(k), "r": float(r[k]), "sigma": float(w[k]), "|J_an|": float(np.linalg.norm(J[k])), "|fwd|": float(np.linalg.norm(fwd[k])), "|bwd|": float(np.linalg.norm(bwd[k])),
                     "an_matches_side_per_param": ["fwd" if abs(J[k, i] - fwd[k, i]) <= KTOL * (1 + abs(fwd[k, i])) else "bwd" if abs(J[k, i] - bwd[k, i]) <= KTOL * (1 + abs(bwd[k, i])) else ("same" if abs(fwd[k,i]-bwd[k,i]) <= KTOL*(1+abs(fwd[k,i])) else "neither") for i in range(n)]})
    out = {"case": label, "h_q": H, "n_params": n, "n_residuals": int(r.size), "n_kinked": int(kinked.sum()), "logL": float(v),
           "term": {"analytic_norm": float(np.linalg.norm(g)), "fd_norm": float(np.linalg.norm(fdL)), "diff_norm": float(np.linalg.norm(g - fdL)),
                    "rel_diff": float(np.linalg.norm(g - fdL) / max(np.linalg.norm(fdL), 1e-300))},
           "check_analytic_equals_residual_assembly": float(np.linalg.norm(g - gl_an)),
           "smooth_residuals": {"analytic_norm": float(np.linalg.norm(coef[sm] @ J[sm])), "diff_norm": float(np.linalg.norm(coef[sm] @ (J[sm] - cen[sm]))),
                                "max_abs_dr_diff": float(np.max(np.abs(J[sm] - cen[sm]), initial=0)),
                                "max_rel_dr_diff": float(np.max(np.abs(J[sm] - cen[sm]) / (1 + np.abs(cen[sm])), initial=0))},
           "kinked_residuals": {"diff_norm": float(np.linalg.norm(coef[kk] @ (J[kk] - cen[kk]))), "rows": rows},
           "timing_s": {"value": round(t_val, 2), "value_and_gradient": round(t_grad, 2), "check_total": round(time.time() - t0, 1)}}
    print(json.dumps(out))


main()
