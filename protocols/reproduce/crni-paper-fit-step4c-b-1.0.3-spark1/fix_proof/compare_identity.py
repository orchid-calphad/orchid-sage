"""Q40 fix proof (1), comparison: two prove_identity.py outputs (model2, model3) are bit-identical in value, gradient, value_only
and every part at every start; also reports re-evaluation minus multistart file. Exit 1 if anything differs.
  compare_identity.py A.json B.json OUT.json"""
import json
import sys
from pathlib import Path

A, B = (json.loads(Path(p).read_text()) for p in sys.argv[1:3])
rows, ok = [], A["n_zpf_susp_records"] == B["n_zpf_susp_records"] == 12 and A["n_residual_objects"] == B["n_residual_objects"]
for a, b in zip(A["rows"], B["rows"]):
    assert a["start"] == b["start"]
    same = {k: a[k] == b[k] for k in ("logpost_hex", "grad_hex", "value_only_hex", "parts_hex")}
    d_file = float.fromhex(b["logpost_hex"]) - b["file_logpost"]
    rows.append({"start": a["start"], **{f"identical_{k[:-4]}": v for k, v in same.items()}, "logpost": b["logpost"],
                 "grad_norm": b["grad_norm"], "file_logpost": b["file_logpost"], "reevaluation_minus_file": d_file})
    ok = ok and all(same.values())
out = {"a": {k: A[k] for k in ("model", "host", "n_zpf_susp_records", "n_residual_objects")},
       "b": {k: B[k] for k in ("model", "host", "n_zpf_susp_records", "n_residual_objects")},
       "bit_identical_all": ok, "rows": rows}
Path(sys.argv[3]).write_text(json.dumps(out, indent=1))
for r in rows:
    print(r)
print("BIT-IDENTICAL ALL:", ok)
sys.exit(0 if ok else 1)
