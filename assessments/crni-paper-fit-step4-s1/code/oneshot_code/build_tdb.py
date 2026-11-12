"""One-shot Cr-Ni TDB from the PhaseForge energetics, SGTE unaries fixed, and its phase diagram.

Model form = the Kunselman et al. (2026) Cr-Ni model used by the PhaseForge+ fits
(<home>/ScientificRuns/cr-ni-rebuild-20261105/inputs/cr-ni-model.tdb): LIQUID, BCC_A2, FCC_A1, one sublattice, no magnetic terms,
SGTE91 unaries copied verbatim (never fitted). Interaction parameters:
  BCC_A2, FCC_A1: L0, L1 = RK fit (full composition grid, PI 6 Nov) of the s2 (volume + ions) SQS mixing enthalpies (0 K), no T dependence.
  CRNI2 (Pt2Mo-type): stoichiometric 1:2 compound on SGTE fcc references, G = GFCCCR + 2 GHSERNI + 3 H_f (H_f: MLIP s2 vs fcc Cr, fcc Ni).
  No partitioned FCC_L12 (PI decision 6 Nov: disordered fcc only).
  LIQUID: L0 a_0 = weighted RK fit of H_mix(2200 K); variant 'oneshot'      : b_k = 0 (PhaseForge one-shot, step 1)
                                                      variant 'oneshot_Sex' : b_k from the corrected Hong-Liu S_ex(2200 K)
Run with <home>/.venvs/espei/bin/python (pycalphad 0.11.2).
"""
import json, sys, hashlib, time, re
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = Path.home() / "ScientificRuns/cr-ni-rebuild-20261105/inputs/cr-ni-model.tdb"
MODEL = "GRACE-2L-SMAX-OMAT-large"
INCLUDE_CRNI2 = True    # PI 6 Nov (clarified): L12/L10/D022 unused; Pt2Mo-type CrNi2 stays as a stoichiometric compound


def rk(x, y, sig, n):
    A = np.stack([x * (1 - x) * (1 - 2 * x) ** k for k in range(n)], 1)
    W = 1 / np.asarray(sig) ** 2
    cov = np.linalg.inv(A.T @ (A * W[:, None]))
    return cov @ (A.T @ (W * y)), cov


def header():
    t = "\n".join(l for l in SRC.read_text().splitlines() if not l.lstrip().startswith("$"))
    keep = []
    for blk in re.split(r"(?<=!)\s*\n", t):
        b = blk.strip()
        if b.startswith("FUNCTION VV") or b.startswith("PARAMETER L(") or b.startswith("$"):
            continue
        if b:
            keep.append(b)
    return "\n".join(keep)


def main():
    sol = json.loads((ROOT / "results" / f"solids_{MODEL}.json").read_text())
    liqH = json.loads((ROOT / "results/liquid_checks_enthalpy.json").read_text())["H_mix"]
    liqS = json.loads((ROOT / "results/liquid_excess_entropy.json").read_text())["states"]
    T0 = 2200
    hs = [v for v in liqH.values() if v["T_K"] == T0]
    x = np.array([v["x_Ni"] for v in hs]); h = np.array([v["H_mix_kJ_mol_atom"] for v in hs]) * 1000
    hu = np.array([max(v["H_mix_SE_kJ_mol_atom"], 0.05) for v in hs]) * 1000
    nL = 1   # L0 only, as for the solids (PhaseForge default terms); three noisy MD points would be interpolated exactly by L0-L2
    aL, aLc = rk(x, h, hu, nL)
    ss = [v for v in liqS.values() if v["T_K"] == T0]
    xs = np.array([v["x_Ni"] for v in ss]); s = np.array([v["S_excess_total"] for v in ss]); su = np.array([v["S_excess_total_u"] for v in ss])
    bS, bSc = rk(xs, s, su, 1)
    bL = -bS   # S_ex = -x(1-x) sum b_k (1-2x)^k
    # PhaseForge convention (sqscal -> sqs2tdb): SGTE unaries for every end-member, MLIP mixing energy relative to the
    # same-lattice MLIP end-members. Full composition grid (PI 6 Nov) -> L0 + L1 for BCC_A2 and FCC_A1 (MaterialsFramework sqs2tdb
    # default terms "1,0 / 2,1"); the L0-only fit is kept in results as a diagnostic.
    params = {lat: [sol["phases"][lat]["RK_s2_J_mol"]["L0"], sol["phases"][lat]["RK_s2_J_mol"]["L1"]] for lat in ("BCC_A2", "FCC_A1")}
    head = header()
    meta = {"created_unix": time.time(), "unary_source": str(SRC), "unary_source_sha256": hashlib.sha256(SRC.read_bytes()).hexdigest(),
            "model": MODEL, "solid_L_J_mol": params, "liquid_a_J_mol": aL.tolist(), "liquid_a_cov": aLc.tolist(),
            "liquid_b_from_Sex_J_mol_K": bL.tolist(), "liquid_b_cov": bSc.tolist(), "liquid_T_ref_K": T0, "tdbs": {}}
    from pycalphad import Database, binplot, variables as v
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    # PI decision 6 Nov: disordered fcc only (FCC_A1, no partitioned FCC_L12). CrNi2 (Pt2Mo-type) stays a stoichiometric compound.
    # Compound convention as in the Cu-Zr PhaseForge build: G = sum_i n_i GHSER_i + n * H_f, with H_f relative to the MLIP stable
    # elements (bcc Cr, fcc Ni), i.e. the MLIP fcc-referenced value shifted by x_Cr (E_fcc,Cr - E_bcc,Cr).
    ordd = sol["phases"].get("FCC_ORDERED", {}).get("cells", {})
    c2 = [v for k, v in ordd.items() if k.endswith("Pt2Mo_CrNi2")]
    EV = 96.485332
    eb = sol["phases"]["BCC_A2"]["pure_reference_energy_eV_atom"]["Cr"]; ef = sol["phases"]["FCC_A1"]["pure_reference_energy_eV_atom"]["Cr"]
    # CrNi2 on SGTE fcc references (PI 6 Nov): G = GFCCCR + 2 GHSERNI + 3 H_f, H_f = MLIP s2 (volume + ions) formation energy
    # relative to MLIP fcc Cr and fcc Ni; sigma = half the staged interval [s3, s0].
    st2 = c2[0]["stages"] if c2 else None
    h2 = st2["s2_volume_ions"]["H_form_fcc_ref_kJ_mol_atom"] * 1000 if c2 else None
    h2_sig = 0.5 * (st2["s0_unrelaxed"]["H_form_fcc_ref_kJ_mol_atom"] - st2["s3_full"]["H_form_fcc_ref_kJ_mol_atom"]) * 1000 if c2 else None
    meta["CrNi2"] = {"H_f_fcc_refs_J_mol_atom": h2, "sigma_half_interval_J_mol_atom": h2_sig,
                     "reference": "MLIP fcc Cr, fcc Ni (s2); TDB: GFCCCR + 2 GHSERNI + 3 H_f (SGTE fcc references)",
                     "model": "stoichiometric CRNI2 (1:2), Pt2Mo-type, no T dependence", "fcc_Cr_minus_bcc_Cr_MLIP_kJ": (ef - eb) * EV}
    for variant in ("oneshot", "oneshot_Sex"):
        lines = [f"$ Cr-Ni PhaseForge one-shot ({variant}), {MODEL}; SGTE91 unaries fixed (from {SRC.name}); generated {time.strftime('%Y-%m-%d')}",
                 "$ BCC_A2/FCC_A1 L0, L1 (full composition grid): RK fit of 128-atom SQS mixing enthalpies (volume+ions relaxed, 0 K)",
                 f"$ LIQUID L0..L{nL-1}: a_k from MLIP MD H_mix at {T0} K" + ("; b_k from corrected Hong-Liu S_ex (provisional)" if variant == "oneshot_Sex" else "; b_k = 0"),
                 head]
        for ph, L in params.items():
            for k, val in enumerate(L):
                lines.append(f"PARAMETER L({ph},CR,NI;{k}) 1 {val:.4f}; 10000 N !")
        for k in range(nL):
            b = bL[k] if (variant == "oneshot_Sex" and k < len(bL)) else 0.0
            lines.append(f"PARAMETER L(LIQUID,CR,NI;{k}) 1 {aL[k]:.4f}{b:+.5f}*T; 10000 N !")
        if INCLUDE_CRNI2 and h2 is not None:
            lines += ["PHASE CRNI2 % 2 1 2 !", "CONSTITUENT CRNI2 :CR : NI : !",
                      f"PARAMETER G(CRNI2,CR:NI;0) 1 GFCCCR+2*GHSERNI{3 * h2:+.4f}; 10000 N !"]
        p = ROOT / "tdb" / f"CrNi_PhaseForge_{variant}_{MODEL}.tdb"
        p.write_text("\n".join(lines) + "\n")
        db = Database(str(p))
        comps = ["CR", "NI", "VA"]
        phases = ["LIQUID", "BCC_A2", "FCC_A1"] + (["CRNI2"] if (INCLUDE_CRNI2 and h2 is not None) else [])
        fig = plt.figure(figsize=(7, 5.5)); ax = fig.gca()
        binplot(db, comps, phases, {v.X("NI"): (0, 1, 0.01), v.T: (600, 2400, 10), v.P: 101325, v.N: 1}, plot_kwargs={"ax": ax})
        ax.set_title(f"Cr-Ni PhaseForge {variant} ({MODEL})")
        fig.savefig(ROOT / "figures" / f"phase_diagram_{variant}.png", dpi=150); plt.close(fig)
        # pure-element check (SGTE melting points must be unchanged) and simple invariant scan
        from pycalphad import equilibrium
        chk = {}
        for el, Tm in (("CR", 2180.0), ("NI", 1728.0)):
            eq = equilibrium(db, [el, "VA"], [q for q in phases if q != "CRNI2"], {v.T: (Tm - 5, Tm + 6, 10), v.P: 101325, v.N: 1})
            stable = [sorted(set(n for n in np.atleast_1d(eq.Phase.values[0, 0, i].ravel()) if n)) for i in range(2)]
            chk[el] = {"below": stable[0], "above": stable[1], "T_m_SGTE": Tm}
        eq = equilibrium(db, comps, phases, {v.X("NI"): (0.001, 1, 0.01), v.T: (1000, 2400, 5), v.P: 101325, v.N: 1})
        ph = eq.Phase.transpose("X_NI", "T", "vertex", ...).values.reshape(len(eq.X_NI), len(eq.T), -1)
        Ts = eq.T.values; Xs = eq.X_NI.values if hasattr(eq, "X_NI") else eq.coords["X_NI"].values
        liq_min = None
        for j, T in enumerate(Ts):
            if np.any(np.array([("LIQUID" in r) and len([q for q in r if q]) == 1 for r in ph[:, j]])):
                liq_min = float(T); break
        bcc_max_x = {}; fcc_min_x = {}
        for j, T in enumerate(Ts):
            if int(T) % 100 == 0:
                single = lambda name: [float(Xs[i]) for i in range(len(Xs)) if list(n for n in ph[i, j] if n) == [name]]
                b = single("BCC_A2"); f = single("FCC_A1")
                bcc_max_x[int(T)] = max(b) if b else None; fcc_min_x[int(T)] = min(f) if f else None
        meta["tdbs"][variant] = {"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "pure_element_check": chk,
                                 "lowest_T_single_phase_liquid_K": liq_min, "bcc_single_phase_max_xNi_by_T": bcc_max_x,
                                 "fcc_single_phase_min_xNi_by_T": fcc_min_x, "figure": f"figures/phase_diagram_{variant}.png"}
        print(variant, chk, "eutectic~", liq_min, flush=True)
    (ROOT / "results/oneshot_tdb.json").write_text(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
