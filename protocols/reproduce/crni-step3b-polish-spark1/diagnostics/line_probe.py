"""Probe logpost along the hybrid (activity-FD) gradient direction at a start's pre-polish endpoint (Cr-Ni)."""
import json, sys, warnings
from pathlib import Path
import numpy as np
warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path.cwd() / "scripts"))
import model
step, start = sys.argv[1], sys.argv[2]
r = next(x for x in json.loads((Path("steps") / step / "multistart_prepolish.json").read_text()) if x["start"] == start)
t = model.GradTarget(f"steps/configs/{step}.json")
th0 = np.asarray(r["theta"], float)[t.idx]
def total(th):
    return t.value_only(th)
def act(th):
    return sum(float(res.get_likelihood(th)) for res in t.res if type(res).__name__ == "ActivityResidual")
h = 1e-4 * t.scale
g = np.zeros(len(th0))
for res in t.res:
    if type(res).__name__ != "ActivityResidual":
        _, gg = res.get_likelihood_and_gradient(th0); gg = np.atleast_1d(gg); g += gg if gg.size == len(th0) else 0
g += t.log_prior_grad(th0)
ga = np.array([(act(th0 + np.eye(len(th0))[i] * h[i]) - act(th0 - np.eye(len(th0))[i] * h[i])) / (2 * h[i]) for i in range(len(th0))])
gq = (g + ga) * t.scale
d = gq / np.linalg.norm(gq)
v0 = total(th0)
print("v0", v0, "|g_q| hybrid", np.linalg.norm(gq), flush=True)
for s in (1e-7, 1e-5, 1e-3):
    vp = total(th0 + s * d * t.scale); vm = total(th0 - s * d * t.scale)
    ap = act(th0 + s * d * t.scale) - act(th0); am = act(th0 - s * d * t.scale) - act(th0)
    print("step %.0e  +d %+.3e  -d %+.3e | activity +d %+.3e -d %+.3e | expected +-%.3e" % (s, vp - v0, vm - v0, ap, am, s * np.linalg.norm(gq)), flush=True)
