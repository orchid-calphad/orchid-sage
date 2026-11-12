#!/usr/bin/env python3
"""Physics checks of a fitted parameter set (protocol 0.4b, 0.4c; unary limits).
1. Liquid convexity: min over x of d2G_LIQ/dx2 at 600-2200 K (no liquid miscibility gap, stable or metastable).
2. bcc metastable gap: chemical spinodal top T_c of BCC_A2 alone from the fit; Cahn coherent spinodal top with
   d2G/dx2 + 2 eta^2 Y V_m (k = eta^2 Y V_m from cr-ni-coherent-20261105/results.json, cases base/low/high);
   metastable bcc+bcc binodal (lower hull of G_bcc alone) at 1000-1600 K; incoherent estimates (0.4c): regular solution
   T_c = Omega/2R with Omega = 4 H_mix(0.5) from the MLIP one-shot (s2), Liu 2016 DFT and the fit; SRO factor 0.79 (bcc);
   excess vibrational entropy S_ex,vib(0.5) = 2.69 +- 0.98 J/mol-atom/K (set H phonons), T_c = 0.79 Omega / (2R + 4 S); DFT/MLIP
   error sigma_Omega = 4 x 9.7 kJ ... reported as a range.
3. fcc the same (chemical spinodal top).
4. Unary limits: excess terms vanish at the end points; stable pure phases equal SGTE (evaluate.pure_check).
usage: physics.py <theta_json_or_tdb> <out.json>"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model
import pd4
from evaluate import pure_check

R_ = 8.314462618
SR = Path.home() / "ScientificRuns"


def d2(L0a, L0b, L1a, L1b, T, x):
    L0, L1 = L0a + L0b * T, L1a + L1b * T
    # G_ex = x(1-x)[L0 + L1(1-2x)] in x = x_Ni ; second derivative analytic
    return -2 * L0 + L1 * (-6 + 12 * x) + R_ * T / (x * (1 - x))


def spinodal_top(p, shift=0.0, Tgrid=np.arange(200.0, 4001.0, 1.0)):
    x = np.linspace(1e-4, 1 - 1e-4, 4001)
    top, xs = None, None
    for T in Tgrid:
        v = d2(*p, T, x) + shift
        if (v < 0).any():
            top, xs = float(T), float(x[np.argmin(v)])
    return top, xs


def binodal(th, T, k=0):
    ref = pd4.ref_grid(np.array([T]))
    ex, _ = pd4.excess(th, [T])
    g = ref[k, 0] + ex[k, 0]
    h = pd4._lower_hull(pd4.X, g)
    best = None
    for a, b in zip(h[:-1], h[1:]):
        if b - a > 3 and (best is None or pd4.X[b] - pd4.X[a] > best[1] - best[0]):
            best = (float(pd4.X[a]), float(pd4.X[b]))
    return best


def main():
    src = Path(sys.argv[1])
    th = model.read_theta(src) if src.suffix == ".tdb" else np.asarray(json.loads(src.read_text())["theta"])
    out = {"source": str(src), "theta": dict(zip(model.LABELS, th.tolist()))}
    xg = np.linspace(1e-4, 1 - 1e-4, 4001)
    liq = []
    for T in np.arange(600.0, 2201.0, 50.0):
        v = d2(th[0], th[1], th[2], th[3], T, xg)
        liq.append([float(T), float(v.min()), float(xg[np.argmin(v)])])
    out["liquid_convexity"] = {"min_d2G_by_T": liq, "convex_everywhere_600_2200": bool(all(r[1] > 0 for r in liq)),
                               "spinodal_top_K": spinodal_top((th[0], th[1], th[2], th[3]))[0]}
    pb = (th[4], th[5], th[6], th[7])
    coh = json.loads((SR / "cr-ni-coherent-20261105/results.json").read_text())["cases"]
    top, xs = spinodal_top(pb)
    out["bcc"] = {"chemical_spinodal_top_K": top, "at_x_Ni": xs,
                  "coherent_spinodal_top_K": {k: spinodal_top(pb, 2 * c["k_J"])[0] for k, c in coh.items()},
                  "coherent_k_J": {k: c["k_J"] for k, c in coh.items()},
                  "metastable_binodal": {str(T): binodal(th, T) for T in (800.0, 1000.0, 1200.0, 1400.0, 1600.0)},
                  "H_mix_0.5_fit_J": 0.25 * th[4], "S_ex_0.5_fit": -0.25 * th[5]}
    est = {}
    S, sS = 2.69, 0.98
    for nm, H in (("MLIP_oneshot_s2", 6046.4), ("DFT_Liu2016", 9150.0), ("fit", 0.25 * th[4])):
        Om = 4 * H
        est[nm] = {"Omega_J": Om, "Tc_MF_K": Om / (2 * R_), "Tc_SRO_K": 0.79 * Om / (2 * R_),
                   "Tc_SRO_vib_K": 0.79 * Om / (2 * R_ + 4 * S),
                   "Tc_SRO_vib_range_K": [0.79 * Om / (2 * R_ + 4 * (S + sS)), 0.79 * Om / (2 * R_ + 4 * max(S - sS, 0))],
                   "Tc_SRO_vib_sigmaOmega_range_K": [0.79 * max(Om - 4 * 9687, 0) / (2 * R_ + 4 * S), 0.79 * (Om + 4 * 9687) / (2 * R_ + 4 * S)]}
    out["bcc"]["incoherent_estimates"] = est
    pf = (th[8], th[9], th[10], th[11])
    ft, fx = spinodal_top(pf)
    out["fcc"] = {"chemical_spinodal_top_K": ft, "at_x_Ni": fx,
                  "metastable_binodal": {str(T): binodal(th, T, 1) for T in (600.0, 700.0, 800.0, 900.0)},
                  "note": "metastable unless a stable FCC+FCC appears in pd4 (stable_same_phase_gaps)"}
    out["unary"] = pure_check(th)
    tp = pd4.topology(th)
    out["stable_same_phase_gaps"] = tp["gaps"]
    Path(sys.argv[2]).write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({"liq_convex": out["liquid_convexity"]["convex_everywhere_600_2200"], "liq_spinodal_top": out["liquid_convexity"]["spinodal_top_K"],
                      "bcc_chem_top": top, "bcc_coh": out["bcc"]["coherent_spinodal_top_K"], "bcc_binodal": out["bcc"]["metastable_binodal"],
                      "fcc_top": out["fcc"]["chemical_spinodal_top_K"], "fcc_top_x": out["fcc"]["at_x_Ni"], "fcc_binodal": out["fcc"]["metastable_binodal"], "unary_ok": out["unary"]["ok"], "gaps": tp["gaps"][:3]}, default=float))
    for k, v in est.items():
        print(k, {a: (round(b) if not isinstance(b, list) else [round(z) for z in b]) for a, b in v.items()})


if __name__ == "__main__":
    main()
