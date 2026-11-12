"""TEST (PI 6 Nov, Cr-Ni only): ZPF records with a driving-force sigma converted from each record's own T/x uncertainty.

Formula (stated before the run), per ZPF row (one ESPEI file per row, values unchanged):
  sigma_DF = sqrt( (|dS| sigma_T)^2 + (G''_a(x_a) sigma_x |x_b - x_a|)^2 )   [J/mol-atom]
  (temperature term: first-order T derivative of the driving force; composition term: shift of the tie-line plane at the
   partner end when the known vertex a moves by sigma_x, fixed T; mean over known solution-phase vertices)
  - dS: reaction entropy of the vertex pair at the tie-line ends at the row's T, |S_b(x_b) - S_a(x_a) - (x_b - x_a) dS_a/dx| (J/mol-atom/K; = dH_rxn/T; first-order T derivative of the ZPF driving force)
        (three-phase rows: mean over the three pairs), from the current step-4 pick (step4_solid s1) with pycalphad SM;
        a null-composition partner takes the pick's tie-line end at that T (nearest T within 100 K if the field is absent there).
  - G''_a: second composition derivative of G of the known vertex's phase in the pick (central difference, h 1e-4).
  - sigma_T, sigma_x: the record's own uncertainty. set E ZPF rows (ESPEI-datasets, method not printed): ORCHID calibration
    2026-10-24 'unknown' class, T_TRANSITION 16 K, X_PHASE 0.011; ORC-SV7H3CNRYS sigma_eff 11 K and X_PHASE 0.011;
    ORC-X3KVP7D3PO 16 K (stoichiometric CRNI2, partner composition unknown: sigma_x term 0).
  - floor (no record weighted beyond its printed precision): sigma_DF >= sqrt((|dS| 1 K)^2 + (G''_a 0.001 |x_b - x_a|)^2)
    (ORCHID reading resolutions T_TRANSITION 1 K, X_PHASE 0.001).
  ESPEI weight = 1000 J/mol (ESPEI's ZPF default scale) / sigma_DF.
Writes data/liq_zs/, data/solid_zs/ (one file per row) and results/zpf_sigma_conversion.json."""
import copy
import json
import sys
import warnings
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import model
import pd4

R = model.RUN
TH = model.read_theta(R / "tdb/step4_solid_pick.tdb")
REC = {"zpf_eutectic_ORC-SV7H3CNRYS.json": (11.0, 0.011), "zpf_CRNI2_ordering_ORC-X3KVP7D3PO.json": (16.0, 0.0)}
DEF = (16.0, 0.011)
_db = {}


def S(phase, T, x):
    from pycalphad import Database, calculate
    if "db" not in _db:
        _db["db"] = Database(str(R / "tdb/step4_solid_pick.tdb"))
    db = _db["db"]
    if phase == "CRNI2":
        r = calculate(db, ["CR", "NI", "VA"], phase, T=T, P=101325, N=1, output="SM")
    else:
        r = calculate(db, ["CR", "NI", "VA"], phase, T=T, P=101325, N=1, output="SM", points=np.array([[1 - x, x]]))
    return float(np.asarray(r.SM).ravel()[0])


def Gpp(phase, T, x, h=1e-4):
    from pycalphad import calculate
    db = _db["db"]
    xs = np.array([max(x - h, 1e-6), x, min(x + h, 1 - 1e-6)])
    r = calculate(db, ["CR", "NI", "VA"], phase, T=T, P=101325, N=1, points=np.stack([1 - xs, xs], 1))
    g = np.asarray(r.GM).ravel()
    return float((g[2] - 2 * g[1] + g[0]) / ((xs[2] - xs[1]) * (xs[1] - xs[0])))


_diag = {}


def segs_at(T):
    T = float(round(T))
    if T not in _diag:
        _diag[T] = pd4.diagram(TH, np.array([T]), pd4.ref_grid(np.array([T])))[0]
    return _diag[T]


def tie(T, a, b, xa=None):
    """tie-line ends (x_a, x_b) of the pair {a,b} in the pick at T (nearest T within 100 K); choose the segment nearest xa."""
    for dT in [0] + [s * k for k in range(5, 105, 5) for s in (1, -1)]:
        best = None
        for kind, phs, xl, xr in segs_at(T + dT):
            if kind == 2 and set(phs) == {a, b} and a != b:
                ends = {phs[0]: xl, phs[1]: xr}
                d = abs(ends[a] - xa) if xa is not None else 0
                if best is None or d < best[0]:
                    best = (d, ends[a], ends[b], T + dT)
        if best:
            return best[1:]
    return None


def slope(T, a, b, xa):
    xs, Ts = [], []
    for dT in (-10, 10):
        t = tie(T + dT, a, b, xa)
        xs.append(None if t is None else t[0]); Ts.append(None if t is None else t[2])
    if None in xs or Ts[0] != T - 10 or Ts[1] != T + 10:  # the field must exist at both T - 10 and T + 10 in the pick
        return None
    dxdT = (xs[1] - xs[0]) / 20.0
    return 1.0 / max(abs(dxdT), 1e-7)


def convert(T, row, rec):
    sT, sx = rec
    known = [(v[0], (v[2][0] if v[1] == ["NI"] else 1 - v[2][0])) for v in row if v[2][0] is not None]
    phases = [v[0] for v in row]
    dS, notes, ends = [], [], {}
    pairs = [(phases[i], phases[j]) for i in range(len(phases)) for j in range(i + 1, len(phases))]
    if not pairs:  # (i) single-phase row of a partial tie-line: partner = the pick's neighbouring phase at that boundary
        a, xa = known[0]
        cand = []
        for b in ("BCC_A2", "FCC_A1", "LIQUID", "CRNI2"):
            if b != a:
                tb = tie(T, a, b, xa)
                if tb is not None:
                    cand.append((abs(tb[0] - xa) + abs(tb[2] - T) / 1000.0, b))
        if cand:
            pairs = [(a, min(cand)[1])]
            phases = phases + [min(cand)[1]]
            notes.append(f"single-phase row: partner {min(cand)[1]} from the pick")
    for a, b in pairs:
        if b is None:
            continue
        xa = dict(known).get(a); xb = dict(known).get(b)
        t = tie(T, a, b, xa)
        if t is not None:
            xa = xa if xa is not None else t[0]
            xb = xb if xb is not None else t[1]
            if abs(t[2] - T) > 0:
                notes.append(f"{a}+{b} field taken at {t[2]:.0f} K")
        else:
            notes.append(f"{a}+{b} field absent in the pick; partner at the known composition")
            xa = xa if xa is not None else xb
            xb = xb if xb is not None else xa
        xa = 2 / 3 if a == "CRNI2" else xa
        xb = 2 / 3 if b == "CRNI2" else xb
        ends[(a, b)] = (xa, xb)
        # reaction entropy of the vertex pair: S_b(x_b) - [S_a(x_a) + (x_b - x_a) dS_a/dx], tangent taken on a solution phase
        if a == "CRNI2":
            a, b, xa, xb = b, a, xb, xa
        h = 1e-4
        dSa = (S(a, T, min(xa + h, 1 - 1e-6)) - S(a, T, max(xa - h, 1e-6))) / (2 * h)
        dS.append(abs(S(b, T, xb) - S(a, T, xa) - (xb - xa) * dSa))
    dSm = float(np.mean(dS)) if dS else None
    if dSm is None:
        raise RuntimeError(f"no entropy difference for row at {T}: {row}")
    # composition equivalent at fixed T: moving known vertex a by sigma_x shifts the tie-line plane at the partner end by
    # G''_a(x_a) sigma_x |x_b - x_a| (mean over known solution-phase vertices)
    cx, cxp = [], []
    for a, xa in known:
        if a == "CRNI2" or sx == 0:
            continue
        for (p1, p2), (e1, e2) in ends.items():
            if a in (p1, p2):
                xb = e2 if a == p1 else e1
                gpp = Gpp(a, T, xa)
                cx.append(abs(gpp) * sx * abs(xb - xa)); cxp.append(abs(gpp) * 0.001 * abs(xb - xa))
    sxdf = float(np.mean(cx)) if cx else 0.0
    sxp = float(np.mean(cxp)) if cxp else 0.0
    sig_main = float(np.hypot(dSm * sT, sxdf))
    sig_floor = float(np.hypot(dSm * 1.0, sxp))
    sig = max(sig_main, sig_floor)
    return {"T": T, "phases": phases, "dS": dSm, "sigma_T": sT, "sigma_x": sx, "sigma_DF_T_part": dSm * sT, "sigma_DF_x_part": sxdf,
            "sigma_DF": sig, "weight": 1000.0 / sig, "floor_active": sig_floor >= sig_main, "notes": notes}


def main():
    out = []
    for g in ("liq", "solid"):
        dst = R / "data" / f"{g}_zs"
        dst.mkdir(parents=True, exist_ok=True)
        for f in sorted((R / "data" / g).glob("zpf*.json")):
            d = json.loads(f.read_text())
            rec = REC.get(f.name, DEF)
            for i, (T, row) in enumerate(zip(d["conditions"]["T"], d["values"])):
                c = convert(float(T), row, rec)
                d1 = copy.deepcopy(d)
                d1["values"] = [row]
                d1["conditions"] = dict(d["conditions"], T=[T])
                d1["phases"] = sorted({v[0] for v in row})
                d1["weight"] = c["weight"]
                d1["comment"] = d.get("comment", "") + (f" | crni-paper-fit-20261106 ZPF-sigma TEST: row {i}; sigma_DF {c['sigma_DF']:.0f} J/mol "
                                                         f"(T part {c['sigma_DF_T_part']:.0f}, x part {c['sigma_DF_x_part']:.0f}); weight {c['weight']:.3f}")
                (dst / f"{f.stem}__r{i:03d}.json").write_text(json.dumps(d1, indent=1))
                out.append({"file": f"{g}/{f.name}", "row": i, **c})
    s = np.array([o["sigma_DF"] for o in out])
    summ = {"n": len(out), "sigma_DF_J_percentiles_0_5_50_95_100": np.percentile(s, [0, 5, 50, 95, 100]).tolist(),
            "weight_percentiles": np.percentile([o["weight"] for o in out], [0, 5, 50, 95, 100]).tolist(),
            "n_floor_active": int(sum(o["floor_active"] for o in out)), "n_with_notes": int(sum(bool(o["notes"]) for o in out)),
            "source_model": "tdb/step4_solid_pick.tdb (step4_solid s1)"}
    (R / "results/zpf_sigma_conversion.json").write_text(json.dumps({"summary": summ, "rows": out}, indent=1, default=float))
    print(json.dumps(summ))
    for o in out:
        if "ORC" in o["file"] or o["sigma_DF"] < 40 or o["sigma_DF"] > 3000:
            print(o["file"][:60], o["row"], round(o["T"]), o["phases"], round(o["dS"], 2), round(o["sigma_DF_x_part"]),
                  round(o["sigma_DF"]), o["notes"][:1])


if __name__ == "__main__":
    main()
