#!/usr/bin/env python3
"""Phase sequence on heating at every composition of a 0.01 grid (acceptance target 'phase sequence identical').

  PY phase_sequence.py crni|cuzr TDB OUT.json [--tmin 600 --tmax 2200 --dt 5]   (run in a staged root: imports scripts/)

Uses the campaign's own fast exact-on-grid evaluators from the code snapshot, so the result is the same construction the
campaigns ranked with: Cr-Ni scripts/pd4.py (lower convex hulls, CRNI2 as a point; T 600-2200 K), Cu-Zr scripts/model.py
(analytic model, lower hull; T 300-2200 K). Output: {x: [[T_start, "PHASE+PHASE"], ...]} with the temperatures where the
stable assemblage changes; deterministic for a fixed TDB. Two TDBs reproduce each other when their outputs are equal."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "scripts"))
import numpy as np  # noqa: E402

a = sys.argv; system, tdb, out = a[1], a[2], a[3]
g = lambda k, d: float(a[a.index(k) + 1]) if k in a else d  # noqa: E731
xs = [round(0.01 * i, 2) for i in range(1, 100)]
res = {}
if system == "crni":
    import model, pd4  # noqa: E401,E402
    tmin, tmax, dt = g("--tmin", 600), g("--tmax", 2200), g("--dt", 5)
    T = np.arange(tmin, tmax + 0.1, dt); th = model.read_theta(tdb); ref = pd4.ref_grid(T)
    D = pd4.diagram(th, T, ref)   # one hull construction per temperature (as pd4.phase_at, vectorised over x)

    def lab_at(segs, x):
        for kind, phs, xl, xr in segs:
            if xl - 1e-12 <= x <= xr + 1e-12 and not (kind == 1 and phs == ("CRNI2",)):
                return "+".join(sorted(phs)) if kind == 2 else phs[0]
        return "?"
    for x in xs:
        seq, prev = [], None
        for t, segs in zip(T, D):
            lab = lab_at(segs, x)
            if lab != prev:
                seq.append([float(t), lab]); prev = lab
        res[f"{x:.2f}"] = seq
else:
    import model as m  # noqa: E402
    tmin, tmax, dt = g("--tmin", 300), g("--tmax", 2200), g("--dt", 5)
    p = m.Params.from_tdb(tdb)
    for x in xs:
        seq, prev = [], None
        for t in np.arange(tmin, tmax + 0.1, dt):
            lab = "+".join(sorted(str(q) for q in m.stable_at(float(t), p, x)))
            if lab != prev:
                seq.append([float(t), lab]); prev = lab
        res[f"{x:.2f}"] = seq
Path(out).write_text(json.dumps({"system": system, "tdb": Path(tdb).name, "grid": {"x_step": 0.01, "T": [tmin, tmax, dt]}, "sequence": res}, indent=0))
print(out, "written")
