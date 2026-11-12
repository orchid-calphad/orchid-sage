"""Per-dataset normalised residuals (residual / sigma) at a TDB, step-4 data. usage: per_dataset.py <tdb> <out.json>"""
import json, sys, glob, warnings
from pathlib import Path
import numpy as np
warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import model
from espei.datasets import load_datasets
from espei.error_functions.context import setup_context
from pycalphad import Database
db = Database(sys.argv[1]); th = model.read_theta(sys.argv[1])
out = {}
for g in ("oneshot", "liq", "thermo", "solid"):
    for f in sorted(glob.glob(str(model.RUN / "data" / g / "*.json"))):
        ctx = setup_context(db, load_datasets([f]), symbols_to_fit=model.NAMES)
        for r in ctx["residual_objs"]:
            try:
                res, w = r.get_residuals(th)
            except ValueError:
                continue
            if not len(res):
                continue
            z = np.asarray(res) / np.asarray(w)
            out[f"{g}/{Path(f).name}"] = {"type": type(r).__name__, "n": len(z), "rms_z": float(np.sqrt(np.mean(z ** 2))),
                                         "max_abs_z": float(np.max(np.abs(z))), "mean_z": float(np.mean(z)),
                                         "rms_residual": float(np.sqrt(np.mean(np.asarray(res) ** 2))), "sigma": float(np.mean(w))}
Path(sys.argv[2]).write_text(json.dumps(out, indent=1))
for k, v in out.items():
    print(f"{k[:78]:78s} {v['type'][:12]:12s} n {v['n']:3d} rms_z {v['rms_z']:6.2f} max {v['max_abs_z']:6.2f} mean {v['mean_z']:+6.2f} rmsres {v['rms_residual']:9.1f}")
