import json, sys, time, warnings
from pathlib import Path
import numpy as np
warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path.cwd() / "scripts"))
import model
t0 = time.time(); t = model.GradTarget("steps/configs/step3b_thermo_crni2free.json"); print("setup", round(time.time() - t0, 1))
ms = json.loads(Path("steps/step3b_thermo_crni2free/multistart_prepolish.json").read_text()); th = np.asarray(ms[0]["theta"], float)[t.idx]
for res, cat in zip(t.res, t.cat):
    n = type(res).__name__
    a = time.time(); res.get_likelihood(th); b = time.time(); res.get_likelihood_and_gradient(th); c = time.time()
    if b - a > 0.01 or c - b > 0.01: print(cat, n, "l %.2fs lg %.2fs" % (b - a, c - b), flush=True)
