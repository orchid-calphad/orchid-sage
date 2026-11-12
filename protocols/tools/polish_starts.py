#!/usr/bin/env python3
"""Polish every start of a fit step to convergence, then pick among the converged ones (general step polish_starts,
fit_protocol 10a; coordinator decision 6 Nov 2026). Run in a staged root (imports scripts/). Never edits the campaign code.

  PY polish_starts.py crni STEP [--threshold 1e-3] [--max-evals 1000] [--nproc 4]
  PY polish_starts.py cuzr STEP --starts 0,1,2 [--threshold 1e-3] [--max-evals 1000] [--nproc 4]
  PY polish_starts.py cuzr-pick STEP [--threshold 1e-3]          (Cu-Zr: evaluate + judge polished starts, 10a pick)

Settings (stated before fitting; identical on every machine):
  - the step's own objective (Cr-Ni model.GradTarget terms; Cu-Zr the setup of fit_step.py, executed unchanged); its
    gradient analytic for every term that passes the term-by-term check against central finite differences, and by
    central FD (step 1e-4 in the optimiser coordinates) for the term classes named by --fd-terms (those that fail it:
    found 6 Nov - gradient ESPEI 9039ea2 ActivityResidual at the Cr-Ni step-3b endpoint, ZPFResidual at Cu-Zr H1);
    the eligibility norm is that verified gradient's norm (the analytic-only norm is reported beside it);
  - optimiser coordinates as in the fit: Cr-Ni q = theta/scale (a /1000, b /1); Cu-Zr z with x = x_s + scale*z,
    scale = 3 for T terms, max(5 %|x_start|, 1) otherwise;
  - L-BFGS-B continued from each start's endpoint: ftol 0, gtol 0 (neither stops it), maxcor 20; restarted from the best
    point until the L2 norm of the gradient in those coordinates is below the threshold (default 1e-3), or the evaluation
    cap is reached (default 1000 per start), or two successive restarts improve the objective by less than 1e-12;
  - a non-finite objective or gradient returns (1e12, 0) so the line search backs off; the iterate kept is the
    best-objective point (a converged point when one is reached); the result never has a lower objective than the start;
  - single-threaded numerics are expected (OMP_NUM_THREADS=1); deterministic for a fixed build.
Starts that reach the cap unconverged stay INELIGIBLE and are reported; the threshold is never loosened.

Cr-Ni output: steps/STEP/multistart.json is replaced by the polished results (each entry with a `polish` record);
the pre-polish file is kept as steps/STEP/multistart_prepolish.json (never overwritten); per-start
steps/STEP/<start>/polish_trajectory.jsonl; steps/STEP/polish_report.json. Then run evaluate.py STEP and
pick_start.py steps/STEP, and evaluate.py STEP <10a pick> to write the pick TDB.
Cu-Zr output: steps/STEP/s<k>/polish/{result.json,tuned.tdb,trajectory.jsonl} (the fit's own s<k>/ files untouched);
cuzr-pick writes steps/STEP/pick_protocol_10a.json and copies the pick's polished TDB to tdb/STEP.tdb (the previous file
moved to tdb/STEP.prepolish.tdb, never deleted)."""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from multiprocessing import get_context
from pathlib import Path

import numpy as np

A = sys.argv
THR = float(A[A.index("--threshold") + 1]) if "--threshold" in A else 1e-3
CAP = int(A[A.index("--max-evals") + 1]) if "--max-evals" in A else 1000
NPROC = int(A[A.index("--nproc") + 1]) if "--nproc" in A else 4
FD_TERMS = A[A.index("--fd-terms") + 1].split(",") if "--fd-terms" in A else []
FD_H = 1e-4
SETTINGS = {"method": "L-BFGS-B continued from the endpoint", "ftol": 0.0, "gtol": 0.0, "maxcor": 20, "threshold_grad_norm": THR,
            "max_evals_per_start": CAP, "stall_rule": "two successive restarts improving the objective by < 1e-12",
            "nonfinite": "returns (1e12, 0)", "rule": "fit_protocol 10a + polish_starts (6 Nov 2026)",
            "gradient": ("analytic (gradient ESPEI) for every term except " + ",".join(FD_TERMS) + ", whose analytic gradient failed the term-by-term "
                         f"check; those by central finite differences, step {FD_H} in the optimiser coordinates") if FD_TERMS else "analytic (gradient ESPEI)",
            "fd_terms": FD_TERMS, "fd_step_optimiser_coordinates": FD_H if FD_TERMS else None}


def fd_grad(l, x, step):
    """central FD of l at x with per-coordinate steps `step` (array, same units as x); derivative w.r.t. x."""
    gr = np.zeros(len(x))
    for i in range(len(x)):
        e = np.zeros(len(x)); e[i] = step[i]
        gr[i] = (float(np.atleast_1d(l(x + e))[0]) - float(np.atleast_1d(l(x - e))[0])) / (2 * step[i])
    return gr


class Done(Exception):
    pass


def polish(fg, z0, log):
    """Minimise fg(z) -> (f, g) (f = -objective) from z0. Returns (z, f, gnorm, n, status)."""
    from scipy.optimize import minimize
    n = [0]; best = [np.inf, z0.copy(), np.inf]; conv = [None]

    def fun(z):
        n[0] += 1
        f, g = fg(z)
        ok = np.isfinite(f) and g is not None and np.all(np.isfinite(g))
        gn = float(np.linalg.norm(g)) if ok else None
        log({"eval": n[0], "objective": -f if ok else None, "grad_norm": gn})
        if not ok:
            if n[0] >= CAP:
                raise Done()
            return 1e12, np.zeros_like(z)
        if f < best[0]:
            best[0], best[1], best[2] = f, z.copy(), gn
        if gn < THR:
            conv[0] = (z.copy(), f, gn); raise Done()
        if n[0] >= CAP:
            raise Done()
        return f, g

    z = z0.copy(); stalls = 0; msgs = []
    try:
        while True:
            f_before = best[0]
            r = minimize(fun, z, jac=True, method="L-BFGS-B", options={"maxiter": 10 ** 6, "maxfun": max(CAP - n[0], 1) + 5, "ftol": 0.0, "gtol": 0.0, "maxcor": 20})
            msgs.append(str(r.message)); z = best[1].copy()
            stalls = stalls + 1 if not (best[0] < f_before - 1e-12) else 0
            if stalls >= 2:
                break
    except Done:
        pass
    if conv[0] is not None:
        zc, fc, gc = conv[0]
        return zc, fc, gc, n[0], "converged", msgs
    return best[1], best[0], best[2], n[0], ("evaluation cap reached" if n[0] >= CAP else "stalled (no further improvement)"), msgs


# ------------------------------------------------------------------------------------------------ Cr-Ni
def crni_job(job):
    import warnings
    warnings.filterwarnings("ignore")
    sys.path.insert(0, str(Path.cwd() / "scripts"))
    import model
    cfgp, r = job
    t = model.GradTarget(cfgp)
    q0 = np.asarray(r["theta"], float)[t.idx] / t.scale
    tr = open(Path("steps") / t.cfg["name"] / r["start"] / "polish_trajectory.jsonl", "w")
    t0 = time.perf_counter()

    def fg(q):
        th = np.asarray(q, float) * t.scale
        try:
            v, g = 0.0, np.zeros(len(th))
            for res in t.res:
                if type(res).__name__ in FD_TERMS:
                    v += float(res.get_likelihood(th)); g += fd_grad(res.get_likelihood, th, FD_H * t.scale)
                else:
                    lv, lg = res.get_likelihood_and_gradient(th); lg = np.atleast_1d(np.asarray(lg, float))
                    v += float(lv); g += lg if lg.size == len(th) else 0.0
            if t.hinge is not None:
                pv, pg = t.hinge(th); v -= float(pv); g -= np.asarray(pg, float)
            v += t.log_prior(th); g += t.log_prior_grad(th)
            return -v, -(g * t.scale)
        except Exception:  # noqa: BLE001
            return np.inf, None
    f0, g0 = fg(q0)
    gn0 = float(np.linalg.norm(g0)) if g0 is not None else None
    if gn0 is not None and gn0 < THR:
        q, f, gn, n, status, msgs = q0, f0, gn0, 0, "already converged", []
    else:
        q, f, gn, n, status, msgs = polish(fg, q0, lambda d: (tr.write(json.dumps(d) + "\n"), tr.flush()))
    tr.close()
    out = dict(r)
    th = t.full(q * t.scale)
    out.update(theta=th.tolist(), logpost=-float(f), grad_norm_q=gn,
               parts={k: v for k, (v, _) in t.parts(q * t.scale, gradient=False).items()}, log_prior=t.log_prior(q * t.scale),
               final=r.get("final", "") + " | polish: " + status,
               grad_norm_q_analytic_only=float(np.linalg.norm(np.asarray(t(q)[1], float))),
               polish={**SETTINGS, "status": status, "converged": status in ("converged", "already converged"), "n_evals": n,
                       "from_logpost": r["logpost"], "from_grad_norm_q": r.get("grad_norm_q"), "start_grad_norm_recomputed": gn0,
                       "max_abs_change": {"a_J_per_mol": float(np.max(np.abs((q - q0) * t.scale)[~model.IS_T[t.idx]], initial=0)),
                                          "b_J_per_mol_K": float(np.max(np.abs((q - q0) * t.scale)[model.IS_T[t.idx]], initial=0))},
                       "messages": msgs[-3:], "seconds": round(time.perf_counter() - t0, 1)})
    return out


def crni(step):
    d = Path("steps") / step
    ms = d / "multistart.json"; pre = d / "multistart_prepolish.json"
    if not pre.exists():
        shutil.copy2(ms, pre)
    res0 = json.loads(pre.read_text())
    cfgp = str(Path("steps/configs") / f"{step}.json")
    out = []
    with get_context("spawn").Pool(NPROC) as pool:
        for r in pool.imap_unordered(crni_job, [(cfgp, r) for r in res0]):
            out.append(r)
            print(json.dumps({"start": r["start"], "logpost": r["logpost"], "grad_norm_q": r["grad_norm_q"], **{k: r["polish"][k] for k in ("status", "n_evals", "seconds")}}), flush=True)
    out.sort(key=lambda z: -z["logpost"])
    ms.write_text(json.dumps(out, indent=1))
    rep = {"step": step, "settings": SETTINGS, "n_starts": len(out), "n_converged": sum(r["polish"]["converged"] for r in out),
           "starts": [{"start": r["start"], "logpost_before": r["polish"]["from_logpost"], "grad_norm_before": r["polish"]["from_grad_norm_q"],
                       "logpost_after": r["logpost"], "grad_norm_after": r["grad_norm_q"], "status": r["polish"]["status"], "n_evals": r["polish"]["n_evals"],
                       "max_abs_change": r["polish"]["max_abs_change"]} for r in out]}
    (d / "polish_report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: rep[k] for k in ("step", "n_starts", "n_converged")}))


# ------------------------------------------------------------------------------------------------ Cu-Zr
def cuzr_one(cfgp, sid):
    """Execute fit_step.py's setup unchanged (everything before its optimiser), then polish from result.json x_best."""
    R = Path.cwd(); src = (R / "scripts/fit_step.py").read_text()
    pre = src[:src.index("tr = open(OUT")]
    cfg = json.loads(Path(cfgp).read_text())
    OUT = R / "steps" / cfg["name"] / f"s{sid}"
    if (OUT / "polish" / "result.json").exists():
        print(f"s{sid}: polished result present, kept", flush=True); return
    card = (OUT / "run_card.json").read_bytes() if (OUT / "run_card.json").exists() else None
    g = {"__file__": str(R / "scripts/fit_step.py"), "__name__": "fit_step_setup"}
    sys.argv = ["fit_step.py", cfgp, str(sid)]
    exec(compile(pre, "fit_step.py(setup)", "exec"), g)
    if card is not None:
        (OUT / "run_card.json").write_bytes(card)      # the setup rewrites it; the fit's own card is kept
    res = json.loads((OUT / "result.json").read_text())
    xs = np.asarray(res["x_best"], float); scale = g["scale"]; objs = g["objs"]; hinge = g["hinge"]

    def lnl_an(x):   # fit_step.py's lnl_grad (defined after its setup), reproduced term for term
        L, G, per = 0.0, np.zeros(len(x)), {}
        for r in objs:
            l, gg = r.get_likelihood_and_gradient(np.asarray(x, float))
            per[type(r).__name__] = per.get(type(r).__name__, 0) + float(l); L += float(l)
            gg = np.atleast_1d(np.asarray(gg, float))
            if gg.size == len(x):
                G += gg
        if hinge is not None:
            pen, pg = hinge(np.asarray(x, float)); per["HingePenalty"] = -float(pen); L -= float(pen); G -= np.asarray(pg, float)
        return L, G, per

    def lnl_grad(x):
        if not FD_TERMS:
            return lnl_an(x)
        L, G, per = 0.0, np.zeros(len(x)), {}
        for r in objs:
            nm = type(r).__name__
            if nm in FD_TERMS:
                l = float(r.get_likelihood(np.asarray(x, float))); gg = fd_grad(r.get_likelihood, np.asarray(x, float), FD_H * scale)
            else:
                l, gg = r.get_likelihood_and_gradient(np.asarray(x, float)); gg = np.atleast_1d(np.asarray(gg, float))
                if gg.size != len(x):
                    gg = np.zeros(len(x))
            per[nm] = per.get(nm, 0) + float(l); L += float(l); G += gg
        if hinge is not None:
            pen, pg = hinge(np.asarray(x, float)); per["HingePenalty"] = -float(pen); L -= float(pen); G -= np.asarray(pg, float)
        return L, G, per
    P = OUT / "polish"; P.mkdir(exist_ok=True)
    tr = open(P / "trajectory.jsonl", "w"); t0 = time.time()

    def fg(z):
        L, G, _ = lnl_grad(xs + scale * z)
        if not (np.isfinite(L) and np.all(np.isfinite(G))):
            return np.inf, None
        return -L, -G * scale
    z0 = np.zeros(len(xs))
    f0, g0 = fg(z0); gn0 = float(np.linalg.norm(g0)) if g0 is not None else None
    if gn0 is not None and gn0 < THR:
        z, f, gn, n, status, msgs = z0, f0, gn0, 0, "already converged", []
    else:
        z, f, gn, n, status, msgs = polish(fg, z0, lambda d: (tr.write(json.dumps(d) + "\n"), tr.flush()))
    tr.close()
    x = xs + scale * z
    txt = g["TDB"].read_text()
    for s, v in zip(g["free"], x):
        txt = re.sub(r"(FUNCTION\s+%s\s+298\.15\s+)[-+.\dEe]+;" % s, lambda mm: mm.group(1) + "%.6f;" % v, txt)
    (P / "tuned.tdb").write_text(f"$ staged Cu-Zr {cfg['name']} start {sid} polished (polish_starts.py; gradient ESPEI %s)" % __import__("espei").__version__ + "\n" + txt)
    L, G, per = lnl_grad(x)
    isT = g["isT"]
    an = lnl_an(x)[1] * scale
    out = {"start": sid, "symbols": g["free"], "grad_norm_scaled_analytic_only": float(np.linalg.norm(an)), "x_prepolish": xs.tolist(), "x_best": x.tolist(), "lnL_prepolish": res["lnL_best"], "lnL_best": float(L),
           "per_residual": per, "grad_norm_scaled_prepolish": gn0, "grad_norm_scaled": gn, "grad_norm_unscaled": float(np.linalg.norm(G)),
           "grad_norm_unscaled_prepolish": res.get("grad_norm_best"), "polish": {**SETTINGS, "status": status, "converged": status in ("converged", "already converged"),
           "n_evals": n, "messages": msgs[-3:], "seconds": round(time.time() - t0, 1),
           "max_abs_change": {"a": float(np.max(np.abs(x - xs)[~isT], initial=0)), "b": float(np.max(np.abs(x - xs)[isT], initial=0))}},
           "final": res.get("final", "") + " | polish: " + status, "espei_version": __import__("espei").__version__, "python": sys.executable,
           "n_eval": res.get("n_eval", 0) + n, "host": os.uname().nodename}
    (P / "result.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({"step": cfg["name"], "start": sid, "lnL": out["lnL_best"], "lnL_prepolish": res["lnL_best"], "grad_norm_scaled": gn,
                      "status": status, "n_evals": n}), flush=True)


def cuzr_gradcheck(cfgp, sid, h=1e-4):
    """Per residual object (and the hinge): analytic gradient vs central FD at s<sid>'s endpoint, in the optimiser's z."""
    R = Path.cwd(); src = (R / "scripts/fit_step.py").read_text(); pre = src[:src.index("tr = open(OUT")]
    cfg = json.loads(Path(cfgp).read_text()); OUT = R / "steps" / cfg["name"] / f"s{sid}"
    card = (OUT / "run_card.json").read_bytes() if (OUT / "run_card.json").exists() else None
    g = {"__file__": str(R / "scripts/fit_step.py"), "__name__": "fit_step_setup"}; sys.argv = ["fit_step.py", cfgp, str(sid)]
    exec(compile(pre, "fit_step.py(setup)", "exec"), g)
    if card is not None:
        (OUT / "run_card.json").write_bytes(card)
    x = np.asarray(json.loads((OUT / "result.json").read_text())["x_best"], float); sc = g["scale"]
    rows = {}
    terms = [(type(r).__name__, r.get_likelihood_and_gradient, r.get_likelihood) for r in g["objs"]]
    if g["hinge"] is not None:
        H = g["hinge"]
        terms.append(("HingePenalty", lambda v: (lambda pg: (-pg[0], -np.asarray(pg[1], float)))(H(v)), lambda v: -H(v)[0]))
    for name, lg, l in terms:
        v, gr = lg(x); gr = np.atleast_1d(np.asarray(gr, float))
        fd = np.array([(float(np.atleast_1d(l(x + np.eye(len(x))[i] * h * sc[i]))[0]) - float(np.atleast_1d(l(x - np.eye(len(x))[i] * h * sc[i]))[0])) / (2 * h) for i in range(len(x))])
        o = rows.setdefault(name, {"n": 0, "g": np.zeros(len(x)), "fd": np.zeros(len(x)), "size_ok": True})
        o["n"] += 1; o["size_ok"] &= gr.size == len(x)
        if gr.size == len(x):
            o["g"] += gr * sc
        o["fd"] += fd
    out = {k: {"n": o["n"], "size_ok": bool(o["size_ok"]), "analytic_norm": float(np.linalg.norm(o["g"])), "fd_norm": float(np.linalg.norm(o["fd"])),
               "diff_norm": float(np.linalg.norm(o["g"] - o["fd"]))} for k, o in rows.items()}
    tot_g = sum(o["g"] for o in rows.values()); tot_fd = sum(o["fd"] for o in rows.values())
    out["total"] = {"analytic_norm": float(np.linalg.norm(tot_g)), "fd_norm": float(np.linalg.norm(tot_fd)), "diff_norm": float(np.linalg.norm(tot_g - tot_fd))}
    print(json.dumps({"step": cfg["name"], "start": sid, "h_z": h, "terms": out}))


def cuzr(step, starts):
    cfgp = f"steps/configs/{step}.json"
    procs = []
    for s in starts:
        while len([p for p in procs if p.poll() is None]) >= NPROC:
            time.sleep(5)
        procs.append(subprocess.Popen([sys.executable, "-u", __file__, "cuzr-one", cfgp, str(s), "--threshold", str(THR), "--max-evals", str(CAP)]
                                      + (["--fd-terms", ",".join(FD_TERMS)] if FD_TERMS else [])))
    rc = [p.wait() for p in procs]
    print("cuzr polish return codes", rc)


def cuzr_pick(step):
    R = Path.cwd(); D = R / "steps" / step; py = sys.executable
    rows = []
    for f in sorted(D.glob("s*/polish/result.json")):
        r = json.loads(f.read_text()); s = r["start"]; P = f.parent; ev = P / "eval"
        if not (ev / "eval.json").exists():
            subprocess.run([py, str(R / "scripts/evaluate_step.py"), str(P / "tuned.tdb"), f"{step}_s{s}_polished", str(ev)], check=True, cwd=R, capture_output=True)
        j = json.loads(subprocess.run([py, str(R / "scripts/judge.py"), str(P / "tuned.tdb"), str(ev / "eval.json")], check=True, cwd=R,
                                      capture_output=True, text=True).stdout.strip().splitlines()[-1])
        j.update(start=s, lnL=r["lnL_best"], grad_norm_scaled=r["grad_norm_scaled"], eligible=r["grad_norm_scaled"] is not None and r["grad_norm_scaled"] < THR,
                 polish_status=r["polish"]["status"])
        j.pop("tdb", None)
        rows.append(j)
    el = [j for j in rows if j["eligible"]]
    # 10a: classes of protocol 0.3 (plausibility, topology), then the objective; no gate / within-25 K / RMSE tie-breaks
    key = lambda j: (j["all_plausible"], sum(j["plausible"].values()), j["topology_ok"], sum(j["topology"].values()), j["lnL"], -j["start"])  # noqa: E731
    pick = max(el, key=key) if el else None
    out = {"step": step, "rule": "fit_protocol 10a after polish_starts: eligible if scaled gradient norm < threshold; rank all_plausible, "
           "number plausible, topology_ok, number topology, then lnL (no grid tie-breaks)", "threshold": THR, "n_starts": len(rows), "n_eligible": len(el),
           "pick": pick["start"] if pick else None, "pick_lnL": pick["lnL"] if pick else None,
           "note": None if pick else "no start converged below the threshold; not loosened", "starts": sorted(rows, key=lambda j: -j["lnL"])}
    (D / "pick_protocol_10a.json").write_text(json.dumps(out, indent=1))
    if pick:
        tgt = R / "tdb" / f"{step}.tdb"
        if tgt.exists() and not (R / "tdb" / f"{step}.prepolish.tdb").exists():
            shutil.move(tgt, R / "tdb" / f"{step}.prepolish.tdb")
        shutil.copy(D / f"s{pick['start']}/polish/tuned.tdb", tgt)
    print(json.dumps({k: out[k] for k in ("step", "n_starts", "n_eligible", "pick", "pick_lnL")}))


if __name__ == "__main__":
    sys.path.insert(0, str(Path.cwd() / "scripts"))
    mode = A[1]
    if mode == "crni":
        crni(A[2])
    elif mode == "cuzr":
        cuzr(A[2], [int(s) for s in A[A.index("--starts") + 1].split(",")])
    elif mode == "cuzr-one":
        cuzr_one(A[2], int(A[3]))
    elif mode == "cuzr-gradcheck":
        cuzr_gradcheck(A[2], int(A[3]), float(A[A.index("--h") + 1]) if "--h" in A else 1e-4)
    elif mode == "cuzr-pick":
        cuzr_pick(A[2])
