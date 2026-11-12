"""Q40 fix proof (3): GradTarget of model3 fails closed. (a) normal build: record counts per category (12 zpf_susp records, 3 phases
in the no-CRNI2 database); (b) the Q40 defect injected (no_crni2_text returns '' = what an empty read gave): DataLossError must be
raised; (c) a dropped file record injected (setup_context keeps one ZPF record fewer in zpf_susp): DataLossError must be raised.
  probe_guard.py ROOT OUT_JSON"""
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT / "scripts"))
import model3  # noqa: E402

CFG = str(ROOT / "steps/configs/step4c_b_hingefloor.json")
out = {}
t = model3.GradTarget(CFG)
out["a_normal"] = {"record_counts": t.record_counts, "n_zpf_susp_records": t.record_counts["zpf_susp"]["held"]["ZPFResidual"],
                   "no_crni2_phases": t.record_counts["zpf_susp"]["phases"]}
orig = model3.no_crni2_text
model3.no_crni2_text = lambda tdb: ""
try:
    model3.GradTarget(CFG); out["b_empty_db"] = {"raised": False}
except model3.DataLossError as e:
    out["b_empty_db"] = {"raised": True, "message": str(e)}
model3.no_crni2_text = orig
import espei.error_functions.context as C  # noqa: E402
orig_setup = C.setup_context


def drop_one(dbf, datasets, **kw):
    ctx = orig_setup(dbf, datasets, **kw)
    for r in ctx["residual_objs"]:
        if type(r).__name__ == "ZPFResidual" and len(r.zpf_data) == 12:
            r.zpf_data = r.zpf_data[:-1]
    return ctx


C.setup_context = drop_one
try:
    model3.GradTarget(CFG); out["c_dropped_record"] = {"raised": False}
except model3.DataLossError as e:
    out["c_dropped_record"] = {"raised": True, "message": str(e)}
C.setup_context = orig_setup
out["fail_closed_ok"] = (out["a_normal"]["n_zpf_susp_records"] == 12 and out["a_normal"]["no_crni2_phases"] == ["BCC_A2", "FCC_A1", "LIQUID"]
                         and out["b_empty_db"]["raised"] and out["c_dropped_record"]["raised"])
Path(sys.argv[2]).write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
