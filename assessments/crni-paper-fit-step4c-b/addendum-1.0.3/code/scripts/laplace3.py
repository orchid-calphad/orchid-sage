#!/usr/bin/env python3
"""laplace3 (7 Nov 2026, Q40 fix): laplace2.py importing model3 instead of model2; no other change.
laplace2 docstring follows.
Cheap UQ at the final step (no MCMC): Laplace at each distinct mode, mixture weights, classified draws.
Adapted from cr-ni-rebuild-20261105/laplace/scripts/hessian_mode.py and mixture.py (same Hessian rule: central differences of
the analytic gradient at relative steps 1e-3 and 3e-3 of max(1,|q|), symmetrised; soft-direction repair along the 3 softest
eigenvectors when -H is not positive definite; log w_k = logpost_k + d/2 log 2pi - 1/2 log|-H_theta|).
Draws: NDRAW from the mixture (by weight) and the independent-marginal counterexample (columns permuted).
Classified with pd4 over 600-2200 K: P(accepted topology), P(single-phase FCC_A1 at x_Ni 0.52, 1473 K), T_eut, T_CrNi2.
usage: laplace.py <config.json> <modes.json: [{name, theta}]> <out.json> [NDRAW=1000]"""
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import model3 as model
import pd4

S_SCAN = (-3, -1, 1, 3)


def hessian(t, q, rel):
    n = len(q)
    H = np.zeros((n, n))
    bad = []
    for j in range(n):
        h = rel * max(1.0, abs(q[j]))
        qp, qm = q.copy(), q.copy()
        qp[j] += h; qm[j] -= h
        vp, gp = t(qp); vm, gm = t(qm)
        if not (np.isfinite(vp) and np.isfinite(vm) and np.all(np.isfinite(gp)) and np.all(np.isfinite(gm))):
            bad.append(j)
        H[:, j] = (gp - gm) / (2 * h)
    return H, bad


def mode_laplace(t, m):
    q = np.asarray(m["theta"], float)[t.idx] / t.scale
    v0, g0 = t(q)
    H1, b1 = hessian(t, q, 1e-3)
    H2, b2 = hessian(t, q, 3e-3)
    H = 0.5 * (H1 + H1.T)
    w, V = np.linalg.eigh(-H)
    w_rep = w.copy()
    scans = {}
    if np.any(w <= 0):
        for k in range(3):
            r = {}
            for s in S_SCAN:
                v, _ = t(q + s * V[:, k])
                r[s] = float(v) - float(v0)
            w_rep[k] = max(-(r[1] + r[-1]), 1e-8)
            scans[f"dir{k}"] = {"eig_fd": float(w[k]), "kappa_s1": -(r[1] + r[-1]), "kappa_s3": -(r[3] + r[-3]) / 9, "rows": r}
    logS = float(np.sum(np.log(t.scale)))
    d = len(q)
    logdet_q = float(np.sum(np.log(w_rep)))
    cov_q = V @ np.diag(1 / w_rep) @ V.T
    D = np.diag(t.scale)
    return {"name": m["name"], "theta": list(map(float, m["theta"])), "logpost": float(v0), "grad_norm_q": float(np.linalg.norm(g0)),
            "eig_negH_q": w.tolist(), "eig_used": w_rep.tolist(), "positive_definite_fd": bool(np.all(w > 0)),
            "rel_stepsize_diff": float(np.max(np.abs(H1 - H2)) / np.max(np.abs(H1))), "nonfinite": b1 + b2, "soft_scans": scans,
            "log_volume": 0.5 * d * np.log(2 * np.pi) - 0.5 * (logdet_q - 2 * logS),
            "log_evidence": float(v0) + 0.5 * d * np.log(2 * np.pi) - 0.5 * (logdet_q - 2 * logS),
            "cov_free": (D @ cov_q @ D).tolist(), "sd_free": np.sqrt(np.diag(D @ cov_q @ D)).tolist(), "free": t.free}


TU = np.arange(600.0, 2201.0, 5.0)   # classification grid, 5 K steps (as the set E propagation)
_REF = {}


def _one(th):
    if "r" not in _REF:
        _REF["r"], _REF["r1"] = pd4.ref_grid(TU), pd4.ref_grid(np.array([1473.0]))
    tp = pd4.topology(th, TU, _REF["r"])
    return ({k: tp[k] for k in ("ok", "T_liquid_min", "T_CrNi2_max", "n_bad", "n_gap_T", "spurious_severity", "eutectic_ok", "crni2_ok")},
            pd4.phase_at(th, 1473.0, 0.52, _REF["r1"]))


def classify(TH, ref=None, ref1=None, nproc=4):
    from multiprocessing import get_context
    pd4.ref_grid(TU); pd4.ref_grid(np.array([1473.0]))
    with get_context("spawn").Pool(nproc) as pool:
        r = pool.map(_one, list(TH), chunksize=10)
    return [a for a, _ in r], [b for _, b in r]


def summarize(tops, at):
    n = len(tops)
    ok = np.array([t["ok"] for t in tops])
    fcc = np.array([a == "FCC_A1" for a in at])
    p = float(ok.mean()); pf = float(fcc.mean())
    q = lambda k: np.nanpercentile([t[k] if np.isfinite(t[k]) else np.nan for t in tops], [5, 50, 95]).tolist()
    return {"n": n, "P_topology_ok": p, "se_ok": float(np.sqrt(p * (1 - p) / n)), "P_FCC_x052_1473K": pf,
            "se_fcc": float(np.sqrt(pf * (1 - pf) / n)), "P_gap": float(np.mean([t["n_gap_T"] > 0 for t in tops])),
            "P_eutectic_ok": float(np.mean([t["eutectic_ok"] for t in tops])), "P_crni2_ok": float(np.mean([t["crni2_ok"] for t in tops])),
            "regions_at_point": {a: at.count(a) / n for a in sorted(set(at))},
            "T_eut_5_50_95": q("T_liquid_min"), "T_CrNi2_5_50_95": q("T_CrNi2_max"),
            "failure_counts": {"eutectic": int(sum(not t["eutectic_ok"] for t in tops)), "crni2": int(sum(not t["crni2_ok"] for t in tops)),
                               "gap": int(sum(t["n_gap_T"] > 0 for t in tops)), "bad_sequence": int(sum(t["n_bad"] > 0 for t in tops))}}


def main():
    cfgp, modesp, outp = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    ndraw = int(sys.argv[4]) if len(sys.argv) > 4 else 1000
    t0 = time.perf_counter()
    t = model.GradTarget(cfgp)
    modes = json.loads(Path(modesp).read_text())
    comps = []
    for m in modes:
        c = mode_laplace(t, m)
        comps.append(c)
        print(json.dumps({k: c[k] for k in ("name", "logpost", "grad_norm_q", "positive_definite_fd", "log_volume", "log_evidence")}),
              flush=True)
    le = np.array([c["log_evidence"] for c in comps])
    w = np.exp(le - le.max()); w /= w.sum()
    hgt = np.array([c["logpost"] for c in comps])
    wh = np.exp(hgt - hgt.max()); wh /= wh.sum()
    ref = pd4.ref_grid(pd4.TT); ref1 = pd4.ref_grid(np.array([1473.0]))
    rng = np.random.default_rng(20261106)
    counts = rng.multinomial(ndraw, w)
    draws, lab = [], []
    for c, nk in zip(comps, counts):
        if nk == 0:
            continue
        mu = np.asarray(c["theta"])[t.idx]
        Z = rng.multivariate_normal(mu, np.asarray(c["cov_free"]), size=nk)
        TH = np.tile(np.asarray(c["theta"]), (nk, 1)); TH[:, t.idx] = Z
        draws.append(TH); lab += [c["name"]] * nk
    TH = np.concatenate(draws)
    tops, at = classify(TH, ref, ref1)
    res = {"config": cfgp, "modes": comps, "weights": {"names": [c["name"] for c in comps], "laplace": w.tolist(), "height_only": wh.tolist()},
           "mode_classes": {}, "mixture": summarize(tops, at), "draw_component_counts": dict(zip([c["name"] for c in comps], counts.tolist()))}
    for c in comps:
        tp = pd4.topology(np.asarray(c["theta"]), TU, pd4.ref_grid(TU))
        res["mode_classes"][c["name"]] = {"ok": tp["ok"], "T_eut": tp["T_liquid_min"], "T_CrNi2": tp["T_CrNi2_max"], "n_bad": tp["n_bad"]}
        idx = [i for i, l in enumerate(lab) if l == c["name"]]
        if idx:
            res["mode_classes"][c["name"]]["P_ok_in_component"] = float(np.mean([tops[i]["ok"] for i in idx]))
    ind = TH.copy()
    prng = np.random.default_rng(20261106)
    for k in t.idx:
        ind[:, k] = ind[prng.permutation(len(ind)), k]
    ti, ai = classify(ind, ref, ref1)
    res["independent_marginals"] = summarize(ti, ai)
    res["seconds"] = time.perf_counter() - t0
    np.save(outp.with_suffix(".draws.npy"), TH)
    outp.write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(res["weights"]), flush=True)
    print("mixture", json.dumps(res["mixture"]), flush=True)
    print("independent", json.dumps(res["independent_marginals"]), flush=True)


if __name__ == "__main__":
    main()
