"""Q40 probe: the check10a_ms.py worker setup (spawn Pool(NPROC), one GradTarget per job, jobs in multistart order), but each job only
builds the target and evaluates once at its endpoint theta, and reports how many zpf_susp ZPF records its context holds and the value.
  probe_pool.py ROOT NPROC ROUNDS        (read only; writes nothing but model2's own data/cache/*_noCRNI2.tdb in ROOT)"""
import json
import sys
import time
import warnings
from multiprocessing import get_context
from pathlib import Path

import numpy as np

ROOT = Path(sys.argv[1]).resolve()
NPROC, ROUNDS = int(sys.argv[2]), int(sys.argv[3])


def job(start):
    warnings.filterwarnings("ignore")
    sys.path.insert(0, str(ROOT / "scripts"))
    import model2
    t0 = time.time()
    t = model2.GradTarget(str(ROOT / "steps/configs/step4c_b_hingefloor.json"))
    n_susp = sum(len(r.zpf_data) for r, c in zip(t.res, t.cat) if c == "zpf_susp" and type(r).__name__ == "ZPFResidual")
    r = next(m for m in json.loads((ROOT / "steps/step4c_b_hingefloor/multistart.json").read_text()) if m["start"] == start)
    th = np.asarray(r["theta"], float)[t.idx]
    v, g = t(th / t.scale)
    return {"start": start, "n_zpf_susp_records": n_susp, "logpost": float(v), "file": r["logpost"], "gnorm": float(np.linalg.norm(g)),
            "t_build_start": t0, "s": round(time.time() - t0, 1)}


def main():
    starts = [m["start"] for m in json.loads((ROOT / "steps/step4c_b_hingefloor/multistart.json").read_text())]
    allrows = []
    for k in range(ROUNDS):
        with get_context("spawn").Pool(NPROC) as p:
            rows = p.map(job, starts)
        for r in rows:
            r["round"] = k
            bad = abs(r["logpost"] - r["file"]) > 1e-6
            print(k, r["start"], "susp_records", r["n_zpf_susp_records"], "%.6f" % r["logpost"], "MISMATCH" if bad else "ok", flush=True)
        allrows += rows
    nb = sum(abs(r["logpost"] - r["file"]) > 1e-6 for r in allrows)
    print("SUMMARY jobs", len(allrows), "mismatches", nb, "dropped_susp", sum(r["n_zpf_susp_records"] == 0 for r in allrows))
    Path(ROOT.parent / f"probe_pool_n{NPROC}_r{ROUNDS}.json").write_text(json.dumps(allrows, indent=1))


if __name__ == "__main__":
    main()
