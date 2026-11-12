#!/usr/bin/env python3
"""Gradient check of the gradient-ESPEI objective (protocol step check_gradients): analytic gradient vs central finite
differences at the start TDB and at random perturbations (fixed seed), term by term over the ESPEI residual objects.
  FIT_PYTHON -I gradient_check.py START.tdb CONFIG.json --points 5 --seed 20261106 --out results/gradient_check.json
CONFIG: a campaign step config (groups = data/<group>/*.json under the config's run root, free = symbols).
Optional --compare-python PY (e.g. ESPEI 0.9.0 in env/uq) recomputes the log-likelihood (no gradient) at the same points
and reports the difference (fit_protocol 0.5: agreement to ~1e-9)."""
import glob, json, subprocess, sys, warnings
from pathlib import Path
import numpy as np
warnings.filterwarnings("ignore")
from pycalphad import Database
from espei.datasets import load_datasets
from espei.error_functions.context import setup_context
from espei.utils import unpack_piecewise
a = sys.argv; tdb, cfgp = a[1], Path(a[2]); cfg = json.loads(cfgp.read_text()); root = cfgp.resolve().parents[2]
npts = int(a[a.index("--points") + 1]) if "--points" in a else 5; seed = int(a[a.index("--seed") + 1]) if "--seed" in a else 20261106
out = a[a.index("--out") + 1] if "--out" in a else "gradient_check.json"
files = sorted(f for g in cfg["groups"] for f in glob.glob(str(root / "data" / g / "*.json")))
db = Database(tdb); free = sorted(cfg["free"]); x0 = np.array([float(unpack_piecewise(db.symbols[s])) for s in free])
objs = setup_context(db, load_datasets(files), free)["residual_objs"]
rng = np.random.default_rng(seed); pts = [x0] + [x0 * (1 + 0.02 * rng.normal(size=x0.size)) + 0.1 * rng.normal(size=x0.size) for _ in range(npts - 1)]
rows = []
for k, x in enumerate(pts):
    for r in objs:
        L, G = r.get_likelihood_and_gradient(x); G = np.atleast_1d(G)
        if G.size != x.size:
            continue
        fd = np.zeros_like(x)
        for i in range(x.size):
            h = 1e-6 * max(1.0, abs(x[i])); xp = x.copy(); xm = x.copy(); xp[i] += h; xm[i] -= h
            fd[i] = (r.get_likelihood_and_gradient(xp)[0] - r.get_likelihood_and_gradient(xm)[0]) / (2 * h)
        rel = float(np.max(np.abs(G - fd) / np.maximum(1.0, np.abs(fd))))
        rows.append({"point": k, "residual": type(r).__name__, "lnL": float(L), "max_rel_grad_diff": rel})
res = {"tdb": tdb, "config": str(cfgp), "seed": seed, "points": [p.tolist() for p in pts], "rows": rows,
       "worst_rel_grad_diff": max((r["max_rel_grad_diff"] for r in rows), default=None)}
Path(out).write_text(json.dumps(res, indent=1)); print(json.dumps({"worst_rel_grad_diff": res["worst_rel_grad_diff"], "n": len(rows)}))
