"""run_global_crni2 (7 Nov 2026, Q40 fix): run_global_crni.py with model3 (no-CRNI2 database in memory, fail-closed record check)
instead of model2, and model3.py in code_sha256; no other change (the docstring below still says model2 for the original).

fit_protocol 10c global search (PI 6 Nov 2026, restored) for one Cr-Ni fit step, reusing the code pattern of
cuzr-protocol-20261104/run_global.py (optimizer_plan.json of 4 Nov): scipy basinhopping (T = 25 objective units, scaled step 0.05,
at most 100 hops, bounds + liquid-feasibility accept test) and dual_annealing (bounds, x0 = local best from the common start,
initial_temp 5230), each with the same local solver, a thermodynamic-evaluation budget stated before fitting, one seed, every
evaluation traced, the 10 best distinct feasible vectors archived. No global-optimality claim; scientific acceptance is separate.

Cr-Ni adaptation (agent decisions, labelled in PLAN.md):
  objective      minimise -logpost of the step's own objective (model2.GradTarget, same config, analytic gradient).
  coordinates    z = (theta - theta_start) / scale, scale = the multistart's optimiser scale (a-terms 1000 J/mol, b-terms 1 J/mol/K);
                 z0 = 0 at the common start (the 10a pick of the multistart).
  bounds         z in [-5, 5] per coordinate (the Cu-Zr scaled box of 4 Nov), i.e. +-5 kJ/mol on a-terms, +-5 J/mol/K on b-terms.
  local solver   L-BFGS-B with the analytic gradient, as the Cr-Ni multistart (fit2.py options ftol 1e-12, gtol 1e-6, maxcor 20),
                 bounded, at most 50 new evaluations per local solve (Cu-Zr local_subproblem_budget 50); best feasible point kept.
  feasibility    LIQUID convex over 600-2200 K (min d2G/dx2 > 0 on the physics.py grid, analytic; cheap), as the Cr-Ni physics check.
  budget         value+gradient evaluations (cache hits not counted), stated in PLAN.md before launch.
  invalid trial  non-finite value or gradient, exception, or out of bounds: logged and rejected (inf); no observation removed.
usage: run_global_crni.py CONFIG START_MULTISTART_JSON START_NAME METHOD(basin|anneal) SEED BUDGET OUTDIR
"""
import hashlib
import json
import os
import sys
import time
import warnings
from pathlib import Path

import numpy as np
from scipy.optimize import OptimizeResult, basinhopping, dual_annealing, minimize

warnings.filterwarnings("ignore")
R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import model3 as model  # noqa: E402  (run_global_crni2: model3 instead of model2, Q40)
R_ = 8.314462618


def d2(L0a, L0b, L1a, L1b, T, x):
    """d2G_LIQ/dx2 in x = x_Ni; identical to physics.py d2 (copied so that physics.py and its imports are not loaded)"""
    L0, L1 = L0a + L0b * T, L1a + L1b * T
    return -2 * L0 + L1 * (-6 + 12 * x) + R_ * T / (x * (1 - x))

CFG, MS, START, METHOD, SEED, BUDGET, OUTDIR = sys.argv[1:8]
SEED, BUDGET = int(SEED), int(BUDGET)
LOCAL_BUDGET = 50
BOX = 5.0
O = Path(OUTDIR); O.mkdir(parents=True, exist_ok=False)
t = model.GradTarget(str(R / CFG))
row = next(m for m in json.loads(Path(MS).read_text()) if m["start"] == START)
TH0 = np.asarray(row["theta"], float)[t.idx]
SC = t.scale
n_par = len(TH0)
bounds = np.array([[-BOX, BOX]] * n_par)
XG = np.linspace(1e-4, 1 - 1e-4, 4001)
TL = np.arange(600.0, 2201.0, 50.0)


def theta(z):
    return TH0 + np.asarray(z, float) * SC


def liquid_min(z):
    th = t.full(theta(z))
    return float(min(d2(th[0], th[1], th[2], th[3], T, XG).min() for T in TL))


t0 = time.time(); cpu0 = time.process_time(); n = [0]; hits = [0]; cache = {}; best = [None]; ranked = []
trace = (O / "trace.jsonl").open("a", buffering=1); events = (O / "events.jsonl").open("a", buffering=1)


def save(name, data):
    f = O / name; tmp = f.with_suffix(".tmp"); tmp.write_text(json.dumps(data, indent=1, default=float)); tmp.replace(f)


class Budget(Exception):
    pass


class LocalBudget(Exception):
    pass


class InvalidTrial(Exception):
    pass


def fg(z):
    """f = -logpost and its gradient in z; traced; budgeted"""
    z = np.asarray(z, float)
    if not np.isfinite(z).all() or np.any(z < bounds[:, 0] - 1e-10) or np.any(z > bounds[:, 1] + 1e-10):
        raise InvalidTrial("out of bounds")
    key = z.tobytes()
    if key in cache:
        hits[0] += 1; v = cache[key]
        if v is None:
            raise InvalidTrial("cached invalid")
        return v
    if n[0] >= BUDGET:
        raise Budget()
    n[0] += 1
    rec = {"evaluation": n[0], "z": z.tolist(), "elapsed_s": round(time.time() - t0, 2), "cpu_s": round(time.process_time() - cpu0, 2)}
    try:
        val, g = t(theta(z) / SC)
        val = float(val); g = np.asarray(g, float)
        if not (np.isfinite(val) and np.all(np.isfinite(g))):
            raise FloatingPointError("non-finite value or gradient")
    except Exception as exc:  # noqa
        cache[key] = None; trace.write(json.dumps({**rec, "valid": False, "error": repr(exc)[:300]}) + "\n")
        raise InvalidTrial() from exc
    lm = liquid_min(z); feas = bool(lm > 0)
    f, gz = -val, -g  # t() returns d logpost / dq; dq/dz = 1 (q = theta/scale, z = (theta-theta0)/scale)
    rec.update(valid=True, logpost=val, parts=t.last_parts, liquid_feasible=feas, liquid_min_d2G=lm)
    trace.write(json.dumps(rec, default=float) + "\n"); cache[key] = (f, gz)
    if feas:
        ranked.append(rec)
        ranked.sort(key=lambda r: -r["logpost"])
        # 10 best distinct vectors (distinct: max |dz| > 1e-6)
        keep = []
        for r in ranked:
            if all(np.max(np.abs(np.array(r["z"]) - np.array(k["z"]))) > 1e-6 for k in keep):
                keep.append(r)
            if len(keep) == 10:
                break
        ranked[:] = keep
        if best[0] is None or val > best[0]["logpost"]:
            best[0] = rec; save("best_liquid_feasible.json", rec); save("top10.json", ranked)
    save("progress.json", {"evaluations": n[0], "cache_hits": hits[0], "best_logpost": None if best[0] is None else best[0]["logpost"],
                           "elapsed_s": time.time() - t0, "cpu_s": time.process_time() - cpu0})
    return f, gz


def value(z):
    try:
        if liquid_min(z) <= 0:
            return np.inf
        return fg(z)[0]
    except InvalidTrial:
        return np.inf


def local(fun, x0, args=(), **kwargs):
    initial = n[0]; selected = [None]
    x0 = np.clip(np.asarray(x0, float), bounds[:, 0], bounds[:, 1])
    try:
        v, g = fg(x0)
        if liquid_min(x0) > 0:
            selected[0] = (x0.copy(), v, g)

        def ev(x):
            if n[0] - initial >= LOCAL_BUDGET:
                raise LocalBudget()
            try:
                v, g = fg(x)
            except InvalidTrial:
                return 1e12, np.zeros_like(x)
            if liquid_min(x) > 0 and (selected[0] is None or v < selected[0][1]):
                selected[0] = (np.array(x), v, g)
            return v, g
        r = minimize(ev, x0, jac=True, method="L-BFGS-B", bounds=bounds,
                     options={"maxiter": 400, "maxfun": 800, "ftol": 1e-12, "gtol": 1e-6, "maxcor": 20})
        message, success = str(r.message), bool(r.success)
    except (InvalidTrial, LocalBudget) as exc:
        message, success = type(exc).__name__, False
    events.write(json.dumps({"kind": "local_stop", "evaluations": n[0], "success": success, "message": message}) + "\n")
    if selected[0] is None:
        return OptimizeResult(x=x0, fun=np.inf, success=False, message="no feasible local candidate", nfev=n[0] - initial)
    return OptimizeResult(x=selected[0][0], fun=selected[0][1], jac=selected[0][2], success=success, message=message, nfev=n[0] - initial)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


manifest = {"method": METHOD, "seed": SEED, "budget_evaluations": BUDGET, "local_budget": LOCAL_BUDGET, "box_scaled": [-BOX, BOX],
            "config": CFG, "config_sha256": sha(R / CFG), "start_multistart": str(Path(MS).resolve()), "start_multistart_sha256": sha(MS),
            "start": START, "start_logpost": row["logpost"], "theta_start_free": TH0.tolist(), "scale": SC.tolist(), "free": t.free,
            "start_tdb": str(t.tdb), "start_tdb_sha256": sha(t.tdb), "hinge_sha256": sha(R / t.cfg["hinge"]) if t.cfg.get("hinge") else None,
            "data_files": [{"path": f, "sha256": sha(f)} for f in t.files], "code_sha256": {p.name: sha(p) for p in [Path(__file__), R / "scripts/model3.py", R / "scripts/model.py"]},
            "basin": {"T": 25, "stepsize": 0.05, "niter": 100}, "anneal": {"initial_temp": 5230, "x0": "local best from z0 (same local solver)"},
            "local_solver": "L-BFGS-B, analytic gradient, bounds, ftol 1e-12 gtol 1e-6 maxcor 20, <= 50 new evaluations",
            "feasibility": "LIQUID min d2G/dx2 > 0 at 600-2200 K (50 K), x 1e-4..1-1e-4 (4001)", **model.espei_version(),
            "scipy": __import__("scipy").__version__, "pid": os.getpid(), "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
save("run_manifest.json", manifest)
z0 = np.zeros(n_par)
try:
    if METHOD == "basin":
        result = basinhopping(value, z0, niter=100, T=25, stepsize=0.05, seed=SEED, minimizer_kwargs={"method": local},
                              accept_test=lambda **kw: bool(np.all(kw["x_new"] >= bounds[:, 0]) and np.all(kw["x_new"] <= bounds[:, 1]) and liquid_min(kw["x_new"]) > 0))
    else:
        initial = local(value, z0)
        result = dual_annealing(value, bounds, x0=initial.x, maxfun=BUDGET, seed=SEED, minimizer_kwargs={"method": local}, initial_temp=5230)
    status = {"termination": str(result.message), "completed": True}
except Budget:
    status = {"termination": "thermodynamic evaluation budget reached", "completed": True}
except Exception as exc:  # noqa
    status = {"termination": repr(exc)[:500], "completed": False, "error": True}
if best[0]:
    thb = t.full(theta(best[0]["z"]))
    model.write_tdb(t.tdb, thb, O / "best.tdb", header=f"$ 10c {METHOD} seed {SEED} best liquid-feasible evaluation {best[0]['evaluation']} logpost {best[0]['logpost']:.10f}")
    save("parameters.json", {"names": model.NAMES, "labels": model.LABELS, "theta": thb.tolist(), "z": best[0]["z"], "logpost": best[0]["logpost"]})
    status.update(best_logpost=best[0]["logpost"], best_evaluation=best[0]["evaluation"],
                  improvement_over_start=best[0]["logpost"] - row["logpost"], accepted=False,
                  acceptance_note="global-search result; 10a eligibility, topology and physics checks are separate")
status.update(evaluations=n[0], cache_hits=hits[0], elapsed_s=time.time() - t0, cpu_s=time.process_time() - cpu0,
              finished=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
save("status.json", status)
print(json.dumps(status), flush=True)
