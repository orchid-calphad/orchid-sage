"""Per residual category: does get_likelihood_and_gradient return a full gradient, and does it match a central FD?"""
import json, sys, warnings
from pathlib import Path
import numpy as np
warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path.cwd() / "scripts"))
import model
step, start = sys.argv[1], sys.argv[2]
ms = json.loads((Path("steps") / step / "multistart_prepolish.json").read_text())
r = next(x for x in ms if x["start"] == start)
t = model.GradTarget(f"steps/configs/{step}.json")
th = np.asarray(r["theta"], float)[t.idx]
h = 1e-4 * t.scale
out = {}
for res, cat in zip(t.res, t.cat):
    k = f"{cat}:{type(res).__name__}"
    v, g = res.get_likelihood_and_gradient(th)
    g = np.atleast_1d(np.asarray(g, float))
    fd = np.array([(res.get_likelihood(th + np.eye(len(th))[i] * h[i]) - res.get_likelihood(th - np.eye(len(th))[i] * h[i])) / (2 * h[i]) for i in range(len(th))])
    o = out.setdefault(k, {"n": 0, "grad_size_ok": True, "g": np.zeros(len(th)), "fd": np.zeros(len(th)), "v_lg": 0.0, "v_l": 0.0})
    o["n"] += 1; o["grad_size_ok"] &= g.size == len(th)
    if g.size == len(th): o["g"] += g
    o["fd"] += fd; o["v_lg"] += float(v); o["v_l"] += float(res.get_likelihood(th))
for k, o in out.items():
    print(k, "n", o["n"], "grad_size_ok", o["grad_size_ok"], "value(lg) %.6f value(l) %.6f" % (o["v_lg"], o["v_l"]),
          "|g*scale| %.4f |fd*scale| %.4f |diff| %.4f" % tuple(np.linalg.norm(x * t.scale) for x in (o["g"], o["fd"], o["g"] - o["fd"])))
if t.hinge is not None: print("hinge present")
