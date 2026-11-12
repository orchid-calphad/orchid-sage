"""Analytic vs central finite-difference gradient at a start's endpoint (Cr-Ni; run in a staged root)."""
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
q = np.asarray(r["theta"], float)[t.idx] / t.scale
v, g = t(q); v = float(v); g = np.asarray(g, float)
out = {"start": start, "logpost": v, "analytic_norm": float(np.linalg.norm(g)), "rows": []}
for h in (1e-3, 1e-4):
    fd = np.zeros_like(q)
    for i in range(len(q)):
        qp, qm = q.copy(), q.copy(); qp[i] += h; qm[i] -= h
        fd[i] = (float(t(qp)[0]) - float(t(qm)[0])) / (2 * h)
    out["rows"].append({"h": h, "fd_norm": float(np.linalg.norm(fd)), "diff_norm": float(np.linalg.norm(fd - g)),
                        "per_param": [[t.free[i], round(float(g[i]), 5), round(float(fd[i]), 5)] for i in range(len(q))]})
print(json.dumps(out))
