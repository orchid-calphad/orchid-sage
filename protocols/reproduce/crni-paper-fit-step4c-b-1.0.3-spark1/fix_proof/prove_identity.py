"""Q40 fix proof (1): the objective of model3.GradTarget is bit-identical to model2.GradTarget when no race occurs.
One process, one module (no concurrency, so model2's cache-file write cannot race): build GradTarget for the step-4c-b config,
evaluate value and analytic gradient (t(q)), value_only and the per-part split at the multistart endpoint theta of every start,
and print them as float.hex, with the multistart file's logpost. Run once with MODEL=model2 and once with MODEL=model3, in fresh
processes; compare_identity.py compares the two outputs bit for bit. Read only: nothing is fitted (model2 rewrites its own
data/cache/*_noCRNI2.tdb in ROOT, as in every run).
  prove_identity.py ROOT MODEL OUT_JSON"""
import json
import os
import sys
import time
import warnings
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")
ROOT = Path(sys.argv[1]).resolve()
MODEL, OUT = sys.argv[2], sys.argv[3]
sys.path.insert(0, str(ROOT / "scripts"))
m = __import__(MODEL)
t0 = time.time()
t = m.GradTarget(str(ROOT / "steps/configs/step4c_b_hingefloor.json"))
n_susp = sum(len(r.zpf_data) for r, c in zip(t.res, t.cat) if c == "zpf_susp" and type(r).__name__ == "ZPFResidual")
ms = json.loads((ROOT / "steps/step4c_b_hingefloor/multistart.json").read_text())
rows = []
for r in sorted(ms, key=lambda z: z["start"]):
    th = np.asarray(r["theta"], float)[t.idx]
    v, g = t(th / t.scale)
    parts = dict(t.last_parts)
    vo = t.value_only(th)
    rows.append({"start": r["start"], "logpost_hex": float(v).hex(), "logpost": float(v), "file_logpost": r["logpost"],
                 "file_logpost_hex": float(r["logpost"]).hex(), "grad_hex": [float(x).hex() for x in g],
                 "grad_norm": float(np.linalg.norm(g)), "value_only_hex": float(vo).hex(),
                 "parts_hex": {k: float(x).hex() for k, x in sorted(parts.items())}})
    print(r["start"], "%.12f" % v, "file %.12f" % r["logpost"], "|g| %.6e" % np.linalg.norm(g), flush=True)
out = {"model": MODEL, "host": os.uname().nodename, "python": sys.executable, "pid": os.getpid(), "n_zpf_susp_records": n_susp,
       "n_residual_objects": len(t.res), "categories": sorted(set(t.cat)), "record_counts": getattr(t, "record_counts", None),
       "seconds": round(time.time() - t0, 1), "rows": rows}
Path(OUT).write_text(json.dumps(out, indent=1))
