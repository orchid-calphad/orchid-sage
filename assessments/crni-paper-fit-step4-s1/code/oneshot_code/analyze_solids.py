"""Cr-Ni solid solutions: mixing enthalpies per relaxation stage, lattice checks, bcc lattice parameter and elastic constants,
Cahn inputs (eta, Y), RK fits (L0, L1) of the s2 (protocol) values with the s0-s3 bracket as uncertainty.
Reads collected_solids/<model>/<lat>/<cell>/result.json (copied read-only from spark1). Writes results/solids_<model>.json.
"""
import json, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EV = 96.485332
STAGES = ("s0_unrelaxed", "s1_volume", "s2_volume_ions", "s3_full")


def rk_fit(x, y, sig, nterm=2):
    """y = x(1-x) sum_k L_k (1-2x)^k, x = x_Ni, (1-2x) = x_Cr - x_Ni (pycalphad L(CR,NI;k)); weighted LSQ."""
    A = np.stack([x * (1 - x) * (1 - 2 * x) ** k for k in range(nterm)], 1)
    W = 1 / np.asarray(sig) ** 2
    cov = np.linalg.inv(A.T @ (A * W[:, None]))
    p = cov @ (A.T @ (W * y))
    res = y - A @ p
    return p, cov, res


def main(model):
    C = ROOT / "collected_solids" / model
    out = {"model": model, "created_unix": time.time(), "phases": {}, "failures": []}
    for lat in ("BCC_A2", "FCC_A1"):
        rows = []
        cells = {p.parent.name: json.loads(p.read_text()) for p in sorted((C / lat).glob("*/result.json"))}
        for n, r in cells.items():
            if r.get("status") != "computed":
                out["failures"].append({"lattice": lat, "cell": n, "failures": r.get("failures")})
        ref = {}
        for n, r in cells.items():
            if n.endswith("_pure") and r.get("status") == "computed":
                ref["Ni" if r["x_Ni"] > 0.5 else "Cr"] = r
        pure_e = {k: v["stages"]["s2_volume_ions"]["energy_eV_atom"] for k, v in ref.items()}
        pure_v = {k: v["stages"]["s2_volume_ions"]["volume_A3_atom"] for k, v in ref.items()}
        for n, r in cells.items():
            if r.get("status") != "computed":
                continue
            x = r["x_Ni"]
            row = {"cell": n, "x_Ni": x, "n_atoms": r["n_atoms"]}
            for s in STAGES:
                if s not in r["stages"]:
                    continue
                e = r["stages"][s]["energy_eV_atom"]
                row[s] = {"H_mix_kJ_mol_atom": (e - (1 - x) * pure_e["Cr"] - x * pure_e["Ni"]) * EV,
                          "volume_A3_atom": r["stages"][s]["volume_A3_atom"],
                          "a_cubic_A": ((2 if lat == "BCC_A2" else 4) * r["stages"][s]["volume_A3_atom"]) ** (1 / 3),
                          "lattice_kept": r["stages"][s]["lattice_check"]["lattice_kept"],
                          "lattice_check": r["stages"][s]["lattice_check"],
                          "max_force_eV_A": r["stages"][s]["max_force_eV_A"], "converged": r["stages"][s].get("converged")}
            rows.append(row)
        rows.sort(key=lambda q: (q["x_Ni"], q["cell"]))
        # per composition: mean over seeds of s2; bracket [s3, s0]; sigma = max(half bracket, seed spread/2, 0.1 kJ)
        comps = sorted({q["x_Ni"] for q in rows if 0 < q["x_Ni"] < 1})
        table = []
        for x in comps:
            q = [r for r in rows if r["x_Ni"] == x]
            s2 = np.array([r["s2_volume_ions"]["H_mix_kJ_mol_atom"] for r in q])
            s0 = np.array([r["s0_unrelaxed"]["H_mix_kJ_mol_atom"] for r in q])
            s3 = np.array([r["s3_full"]["H_mix_kJ_mol_atom"] for r in q])
            half = float((s0.mean() - s3.mean()) / 2)
            seed = float(np.ptp(s2) / 2) if len(s2) > 1 else 0.0
            table.append({"x_Ni": x, "H_mix_s2_mean": float(s2.mean()), "H_mix_s2_seeds": s2.tolist(),
                          "H_mix_s0_mean": float(s0.mean()), "H_mix_s3_mean": float(s3.mean()),
                          "bracket_half_width": half, "seed_half_spread": seed, "sigma_kJ": max(half, seed, 0.1),
                          "a_s2_A_mean": float(np.mean([r["s2_volume_ions"]["a_cubic_A"] for r in q])),
                          "lattice_kept_s2_all": all(r["s2_volume_ions"]["lattice_kept"] for r in q),
                          "lattice_kept_s3_all": all(r["s3_full"]["lattice_kept"] for r in q)})
        x = np.array([t["x_Ni"] for t in table]); y = np.array([t["H_mix_s2_mean"] for t in table])
        sig = np.array([t["sigma_kJ"] for t in table])
        p, cov, res = rk_fit(x, y, sig, 2)
        q0, c0, r0 = rk_fit(x, y, sig, 1)   # PhaseForge sqscal default terms.in "1,0; 2,0": end-members + L0 only
        p3, cov3, res3 = rk_fit(x, np.array([t["H_mix_s3_mean"] for t in table]), sig, 2)
        p0, cov0, res0 = rk_fit(x, np.array([t["H_mix_s0_mean"] for t in table]), sig, 2)
        ph = {"cells": rows, "table": table, "pure_reference_energy_eV_atom": pure_e, "pure_reference_volume_A3_atom": pure_v,
              "pure_a_A": {k: ((2 if lat == "BCC_A2" else 4) * v) ** (1 / 3) for k, v in pure_v.items()},
              "RK_s2_J_mol": {"L0": p[0] * 1000, "L1": p[1] * 1000, "cov_J2": (cov * 1e6).tolist(), "residuals_kJ": res.tolist()},
              "RK_s2_L0only_J_mol": {"L0": q0[0] * 1000, "var_J2": float(c0[0, 0] * 1e6), "residuals_kJ": r0.tolist(),
                                     "note": "PhaseForge/sqs2tdb convention: H_mix relative to the same-lattice MLIP end-members; "
                                             "end-members replaced by SGTE in the TDB; L0 only (sqscal terms.in 1,0 / 2,0)"},
              "uncertainty_note": "sigma per composition = max(half of the staged interval [s3 full, s0 unrelaxed], half seed spread, 0.1 kJ); "
                                  "interval endpoints H_mix_s3_mean, H_mix_s0_mean carried for the fit",
              "RK_s3_J_mol": {"L0": p3[0] * 1000, "L1": p3[1] * 1000}, "RK_s0_J_mol": {"L0": p0[0] * 1000, "L1": p0[1] * 1000},
              "RK_note": "G_ex = x_Cr x_Ni [L0 + L1 (x_Cr - x_Ni)], fitted to the s2 (volume + ions) seed means, weights 1/sigma^2"}
        if lat == "BCC_A2":
            xs = np.array([0.0] + list(x)); a = np.array([ph["pure_a_A"]["Cr"]] + [t["a_s2_A_mean"] for t in table])
            m = xs <= 0.5
            c = np.polyfit(xs[m], a[m], 2)
            ph["lattice_parameter_vs_x"] = {"x_Ni": xs.tolist(), "a_A": a.tolist(), "quadratic_fit_coeffs_high_first": c.tolist(),
                                            "eta_at_x": {f"{xx:g}": float(np.polyval(np.polyder(c), xx) / np.polyval(c, xx))
                                                         for xx in (0.0, 0.125, 0.25, 0.375, 0.5)},
                                            "note": "eta = (1/a) da/dx_Ni from the s2 lattice parameters (0 K, MLIP)"}
            el = {}
            for e in sorted((C / lat).glob("*/elastic.json")):
                d = json.loads(e.read_text())
                c11, c12, c44 = d["C11_GPa"], d["C12_GPa"], d["C44_GPa"]
                A = 2 * c44 / (c11 - c12) if c11 != c12 else np.nan
                # Cahn: Y for the elastically softest of <100>, <111>
                Y100 = (c11 + 2 * c12) * (c11 - c12) / c11
                Y111 = 6 * c44 * (c11 + 2 * c12) / (c11 + 2 * c12 + 4 * c44)
                el[e.parent.name] = {"x_Ni": json.loads((e.parent / "result.json").read_text())["x_Ni"], "C11_GPa": c11, "C12_GPa": c12,
                                     "C44_GPa": c44, "C11_spread": d["C11_spread_GPa"], "C44_spread": d["C44_spread_GPa"],
                                     "zener_A": A, "Y100_GPa": Y100, "Y111_GPa": Y111, "Y_soft_GPa": min(Y100, Y111),
                                     "soft_direction": "100" if Y100 <= Y111 else "111"}
            ph["elastic_constants_0K"] = el
        out["phases"][lat] = ph
    # ordered fcc superstructures vs the disordered fcc (SQS) at the same composition and vs the fcc SQS lower hull
    fo = out["phases"].get("FCC_A1")
    if fo and (C / "FCC_ORDERED").exists():
        pe = fo["pure_reference_energy_eV_atom"]
        tab = {round(t["x_Ni"], 4): t for t in fo["table"]}
        hx = np.array([0.0] + [t["x_Ni"] for t in fo["table"]] + [1.0])
        orde = {}
        for stg in STAGES:   # hull of the disordered fcc SQS (seed means) per stage, pure ends = 0
            hy = np.array([0.0] + [t["H_mix_%s_mean" % stg[:2]] if ("H_mix_%s_mean" % stg[:2]) in t else np.nan for t in fo["table"]] + [0.0])
            orde.setdefault("_hull_inputs", {})[stg] = hy.tolist()
        for p_ in sorted((C / "FCC_ORDERED").glob("*/result.json")):
            r = json.loads(p_.read_text())
            if r.get("status") != "computed":
                out["failures"].append({"lattice": "FCC_ORDERED", "cell": p_.parent.name, "failures": r.get("failures")}); continue
            x = r["x_Ni"]; row = {"x_Ni": x, "n_atoms": r["n_atoms"], "stages": {}}
            for s in STAGES:
                e = r["stages"][s]["energy_eV_atom"]
                H = (e - (1 - x) * pe["Cr"] - x * pe["Ni"]) * EV
                key = {"s0_unrelaxed": "H_mix_s0_mean", "s1_volume": None, "s2_volume_ions": "H_mix_s2_mean", "s3_full": "H_mix_s3_mean"}[s]
                t = tab.get(round(x, 4))
                dis = t[key] if (t and key) else None
                # lower convex hull of disordered fcc SQS (s2) evaluated at x
                hy = np.array([0.0] + [q["H_mix_s2_mean"] for q in fo["table"]] + [0.0])
                pts = sorted(zip(hx, hy)); lo = []
                for pt in pts:
                    while len(lo) >= 2 and (lo[-1][0] - lo[-2][0]) * (pt[1] - lo[-2][1]) - (lo[-1][1] - lo[-2][1]) * (pt[0] - lo[-2][0]) <= 0:
                        lo.pop()
                    lo.append(pt)
                hull = float(np.interp(x, [q[0] for q in lo], [q[1] for q in lo]))
                row["stages"][s] = {"H_form_fcc_ref_kJ_mol_atom": H, "minus_disordered_fcc_same_stage_kJ": (H - dis) if dis is not None else None,
                                    "minus_fcc_SQS_s2_hull_kJ": H - hull,
                                    "volume_A3_atom": r["stages"][s]["volume_A3_atom"],
                                    "lattice_kept": r["stages"][s]["lattice_check"]["lattice_kept"],
                                    "shape_strain_dev_norm": r["stages"][s]["lattice_check"].get("shape_strain_dev_norm")}
            orde[p_.parent.name] = row
        orde.pop("_hull_inputs", None)
        for n_, rw_ in orde.items():
            rw_["use"] = ("used: CRNI2 stoichiometric compound (SGTE fcc references; s2 value, [s3, s0] interval as sigma)" if "Pt2Mo" in n_
                          else "computed, NOT USED (PI decision 6 Nov: disordered FCC_A1 only; L12, L10, D022 unused)")
        out["phases"]["FCC_ORDERED"] = {"cells": orde, "reference": "fcc Cr and fcc Ni (same MLIP, s2); hull = lower convex hull of the "
                                        "disordered fcc SQS s2 seed means incl. x 0.25, 2/3; positive = above"}
        for n, rw in orde.items():
            s2 = rw["stages"]["s2_volume_ions"]; s3 = rw["stages"]["s3_full"]
            print("ordered %-22s H_f %.2f  vs dis %s  vs hull %.2f | s3 vs hull %.2f kept s2/s3 %s/%s" % (
                n, s2["H_form_fcc_ref_kJ_mol_atom"], None if s2["minus_disordered_fcc_same_stage_kJ"] is None else round(s2["minus_disordered_fcc_same_stage_kJ"], 2),
                s2["minus_fcc_SQS_s2_hull_kJ"], s3["minus_fcc_SQS_s2_hull_kJ"], s2["lattice_kept"], s3["lattice_kept"]))
    p = ROOT / "results" / f"solids_{model}.json"
    p.write_text(json.dumps(out, indent=1))
    for lat, ph in out["phases"].items():
        if "RK_s2_J_mol" not in ph:
            continue
        print(lat, "L0 %.0f L1 %.0f J/mol" % (ph["RK_s2_J_mol"]["L0"], ph["RK_s2_J_mol"]["L1"]))
        for t in ph["table"]:
            print("  x=%.4f s2 %.2f [s3 %.2f, s0 %.2f] seeds %s a=%.4f kept s2/s3 %s/%s" % (
                t["x_Ni"], t["H_mix_s2_mean"], t["H_mix_s3_mean"], t["H_mix_s0_mean"], np.round(t["H_mix_s2_seeds"], 2), t["a_s2_A_mean"],
                t["lattice_kept_s2_all"], t["lattice_kept_s3_all"]))
    print("failures", out["failures"])


if __name__ == "__main__":
    main(sys.argv[1])
