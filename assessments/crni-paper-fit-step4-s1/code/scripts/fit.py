#!/usr/bin/env python3
"""Multistart MAP fit of one step (adapted from cr-ni-rebuild-20261105/scripts/fit.py; same optimiser and fallbacks).

Env: <fit-env> (Brandon Bocklund's ESPEI Gradient-based_update 9039ea2), PYTHONPATH incl. <home>/src/PhaseForgePlus/src.
L-BFGS-B in q = theta/scale (a /1000, b /1) with the analytic ESPEI-grad gradient; jitter retry, then value-only + central FD
fallback, every event logged (as fit.py). Changes from fit.py: step config (free symbols, data groups, hinge, start TDB);
a wall budget per start (best point kept); starts: s0 = start TDB, s1..s7 = a(1 + 0.1 N(0,1)) [+ N(0, 2 kJ) where a = 0],
b + N(0, 3 J/K) (seed 1000 + k, the Cu-Zr fit_step.py rule), plus named extra starts (EXTRA_STARTS json {name: theta14}).
usage: fit.py <config.json> <nproc> [n_perturbed=7]
"""
import hashlib
import json
import os
import sys
import time
import warnings
from multiprocessing import get_context
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model

_T = {}
TOPO_EVERY = 10
TU = np.arange(600.0, 2201.0, 5.0)


class Stop(Exception):
    pass


def target(cfgp):
    if cfgp not in _T:
        _T[cfgp] = model.GradTarget(cfgp)
    return _T[cfgp]


def run(job):
    warnings.filterwarnings("ignore")
    from scipy.optimize import minimize
    cfgp, name, theta0 = job
    t = target(cfgp)
    wall = float(t.cfg.get("wall_s", 5400))
    events, nev, best = [], [0], [np.inf, None]
    t0 = time.perf_counter()
    # per-evaluation trajectory (PI 6 Nov, dashboard): steps/<step>/<start>/trajectory.jsonl
    tdir = model.RUN / "steps" / t.cfg["name"] / name
    tdir.mkdir(parents=True, exist_ok=True)
    trj = open(tdir / "trajectory.jsonl", "w")
    trj.write(json.dumps({"header": True, "step": t.cfg["name"], "start": name, "names_all": model.NAMES, "labels_all": model.LABELS,
                          "free": t.free, "free_labels": [model.LABELS[i] for i in t.idx], "theta_fixed_all": t.theta_fixed.tolist(),
                          "objective": "logpost = sum of ESPEI log-likelihood components + hinge + log_prior; components keyed category:residual",
                          "topology_every": TOPO_EVERY, "topology_grid": "600-2200 K, 5 K steps (pd4)"}) + "\n")

    def topo(q):
        import pd4
        th = t.full(np.asarray(q) * t.scale)
        tp = pd4.topology(th, TU, pd4.ref_grid(TU))
        return {"class": "ok" if tp["ok"] else ("gap" if tp["gaps"] else "other"), "T_eut": tp["T_liquid_min"], "T_CrNi2": tp["T_CrNi2_max"],
                "n_bad": tp["n_bad"], "eutectic_ok": tp["eutectic_ok"], "crni2_ok": tp["crni2_ok"]}

    def record(q, val, stage):
        rec = {"eval": nev[0], "stage": stage, "t_s": round(time.perf_counter() - t0, 3), "logpost": val if np.isfinite(val) else None,
               "parts": t.last_parts, "theta_free": list(map(float, np.asarray(q) * t.scale))}
        if nev[0] == 1 or nev[0] % TOPO_EVERY == 0:
            rec["topology"] = topo(q)
        trj.write(json.dumps(rec, default=float) + "\n"); trj.flush()

    def f(q):
        nev[0] += 1
        if time.perf_counter() - t0 > wall:
            raise Stop()
        theta = q * t.scale
        try:
            val, g = t(q)
            val = float(val)
        except Exception as e:  # noqa
            val, g = -np.inf, None
            events.append({"q": q.tolist(), "error": repr(e)[:200]})
        record(q, val, "lbfgsb")
        if np.isfinite(val) and g is not None and np.all(np.isfinite(g)):
            if -val < best[0]:
                best[0], best[1] = -val, q.copy()
            return -val, -g
        rngj = np.random.default_rng(nev[0])
        for rel in (1e-6, 1e-5, 1e-4, 1e-3):
            qj = q * (1 + rel * rngj.standard_normal(len(q)))
            try:
                vj, gj = t(qj)
                vj = float(vj)
            except Exception:  # noqa
                continue
            if np.isfinite(vj) and np.all(np.isfinite(gj)):
                events.append({"q": q.tolist(), "analytic_value": val, "jitter_ok": rel})
                return -vj, -gj
        v2 = t.value_only(theta)
        ev = {"q": q.tolist(), "analytic_value": val, "value_only": v2}
        if not np.isfinite(v2):
            events.append(ev)
            return 1e12, np.zeros_like(q)
        g2 = np.zeros_like(q)
        for i in range(len(q)):
            h = 1e-3 * max(1.0, abs(q[i]))
            qp, qm = q.copy(), q.copy()
            qp[i] += h; qm[i] -= h
            g2[i] = (t.value_only(qp * t.scale) - t.value_only(qm * t.scale)) / (2 * h)
        ev["fd_gradient_used"] = True
        events.append(ev)
        return -v2, -g2

    q = np.asarray(theta0, float)[t.idx] / t.scale
    msgs, final = [], "converged"
    try:
        for _ in range(4):
            r = minimize(f, q, jac=True, method="L-BFGS-B",
                         options={"maxiter": 400, "maxfun": 800, "ftol": 1e-12, "gtol": 1e-6, "maxcor": 20})
            moved = float(np.linalg.norm(r.x - q))
            q = r.x
            msgs.append(str(r.message))
            if moved < 1e-5:
                break
        else:
            final = "not converged after 4 L-BFGS-B restarts"
    except Stop:
        final = "wall budget reached (best point kept)"
        q = best[1]
    if best[1] is not None and best[0] < -float(t(q)[0]) - 1e-9:
        q = best[1]
    val, g = t(q)
    rec_end = {"eval": nev[0], "stage": "final", "t_s": round(time.perf_counter() - t0, 3), "logpost": float(val), "parts": t.last_parts,
               "theta_free": list(map(float, q * t.scale)), "topology": topo(q), "final": final}
    trj.write(json.dumps(rec_end, default=float) + "\n"); trj.close()
    th = t.full(q * t.scale)
    parts = {k: v for k, (v, _) in t.parts(q * t.scale, gradient=False).items()}
    return {"step": t.cfg["name"], "start": name, "theta0": list(map(float, theta0)), "theta": th.tolist(),
            "free": t.free, "logpost": float(val), "log_prior": t.log_prior(q * t.scale), "parts": parts,
            "grad_norm_q": float(np.linalg.norm(g)), "nfev": nev[0], "messages": msgs, "final": final,
            "nonfinite_events": events[:50], "n_nonfinite": len(events), "seconds": time.perf_counter() - t0}


def starts(cfgp, n_pert):
    c, _ = model.load_config(cfgp)
    th0 = model.read_theta(model.RUN / c["start_tdb"])
    jobs = [("s0_start", th0)]
    free = np.array([model.NAMES.index(s) for s in c["free"]])
    for k in range(1, n_pert + 1):
        rng = np.random.default_rng(1000 + k)
        th = th0.copy()
        for i in free:
            if model.IS_T[i]:
                th[i] = th0[i] + rng.normal(0, 3.0)
            else:
                th[i] = th0[i] * (1 + 0.1 * rng.normal()) + (rng.normal(0, 2000.0) if th0[i] == 0 else 0.0)
        jobs.append((f"s{k}_perturbed", th))
    if os.environ.get("EXTRA_STARTS"):
        for nm, th in json.loads(Path(os.environ["EXTRA_STARTS"]).read_text()).items():
            jobs.append((nm, np.asarray(th, float)))
    return jobs


def main():
    cfgp, nproc = sys.argv[1], int(sys.argv[2])
    n_pert = int(sys.argv[3]) if len(sys.argv) > 3 else 7
    c, files = model.load_config(cfgp)
    out = model.RUN / "steps" / c["name"]
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(cfgp, n, th) for n, th in starts(cfgp, n_pert)]
    card = {"step": c["name"], "config": c, **model.espei_version(), "start_tdb": c["start_tdb"],
            "start_tdb_sha256": model.sha(model.RUN / c["start_tdb"]),
            "hinge_sha256": model.sha(model.RUN / c["hinge"]) if c.get("hinge") else None,
            "data_files": [{"path": f, "sha256": model.sha(f)} for f in files],
            "starts": {n: list(map(float, th)) for _, n, th in jobs}, "nproc": nproc,
            "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "pid": os.getpid()}
    (out / "run_card.json").write_text(json.dumps(card, indent=1))
    print("espei", card["espei_version"], card["python"], flush=True)
    res = []
    with get_context("spawn").Pool(nproc) as pool:
        for r in pool.imap_unordered(run, jobs):
            r["espei_version"] = card["espei_version"]
            res.append(r)
            print(json.dumps({k: r[k] for k in ("step", "start", "logpost", "grad_norm_q", "nfev", "seconds", "final", "n_nonfinite")}),
                  flush=True)
            res.sort(key=lambda z: -z["logpost"])
            (out / "multistart.json").write_text(json.dumps(res, indent=1))
    card["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (out / "run_card.json").write_text(json.dumps(card, indent=1))


if __name__ == "__main__":
    main()
