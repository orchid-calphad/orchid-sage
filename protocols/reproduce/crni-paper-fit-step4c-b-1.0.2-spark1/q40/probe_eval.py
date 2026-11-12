"""Q40 probe: evaluate multistart endpoints at fixed theta with model2.GradTarget, value and per-part split (read only; no fit).
  probe_eval.py ROOT START[,START...] [--repeat N] [--empty-susp]
--empty-susp: build the zpf_susp category from an EMPTY no-CRNI2 TDB (what a reader sees if it opens the file while another
worker has just truncated it in model2.no_crni2_tdb), to test the race hypothesis. The file on disk is not touched: Database is
patched in model2's namespace for that category only."""
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")
ROOT = Path(sys.argv[1]).resolve()
STARTS = sys.argv[2].split(",")
REP = int(sys.argv[sys.argv.index("--repeat") + 1]) if "--repeat" in sys.argv else 1
EMPTY = "--empty-susp" in sys.argv
sys.path.insert(0, str(ROOT / "scripts"))
import model2  # noqa: E402

if EMPTY:
    import pycalphad
    _orig_no = model2.no_crni2_tdb
    model2.no_crni2_tdb = lambda tdb: "__EMPTY__"
    _Db = pycalphad.Database

    class _PatchedDb(_Db):
        def __new__(cls, *a, **k):
            if a and a[0] == "__EMPTY__":
                return _Db.from_string("", fmt="tdb")
            return _Db(*a, **k)
    pycalphad.Database = _PatchedDb

ms = json.loads((ROOT / "steps/step4c_b_hingefloor/multistart.json").read_text())
out = []
t = model2.GradTarget(str(ROOT / "steps/configs/step4c_b_hingefloor.json"))
for k in range(REP):
    for s in STARTS:
        r = next(m for m in ms if m["start"] == s)
        th = np.asarray(r["theta"], float)[t.idx]
        t0 = time.time()
        v, g = t(th / t.scale)
        parts = dict(t.last_parts)
        out.append({"rep": k, "start": s, "logpost": float(v), "file": r["logpost"], "gnorm": float(np.linalg.norm(g)),
                    "parts": parts, "s": round(time.time() - t0, 1)})
        print(k, s, "%.9f" % v, "file %.9f" % r["logpost"], "|g| %.2e" % np.linalg.norm(g),
              {kk: round(vv, 6) for kk, vv in parts.items()}, flush=True)
print("JSON", json.dumps(out))
