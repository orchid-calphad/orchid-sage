"""Protocol 0.2a data-consistency check for the data added or changed in this campaign; flags only, never changes data.
The set E datasets were checked in cr-ni-rebuild-20261105/results/data_consistency.json (copied by reference, summarised here).
Writes results/data_consistency.json."""
import json
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
SR = Path.home() / "ScientificRuns"
PF = SR / "crni-phaseforge-20261105/results"


def main():
    out = {"setE_reference": str(SR / "cr-ni-rebuild-20261105/results/data_consistency.json"), "items": {}}
    it = out["items"]
    # 1 uncertainty present
    nos = []
    for g in ("oneshot", "liq", "thermo", "solid"):
        for f in sorted((R / "data" / g).glob("*.json")):
            d = json.loads(f.read_text())
            if "weight" not in d:
                nos.append(f"{g}/{f.name} ({d['output']})")
    it["1_uncertainty_present"] = {
        "files_without_weight": nos,
        "note": "all non-ZPF observations carry weight = default ESPEI sd / sigma (ORCHID rule, sigma_MLIP, MD u). ZPF files carry no "
                "weight, i.e. ESPEI's 1000 J/mol driving-force scale (weight 1), as in set E and the Cu-Zr campaign ('ZPF weight 1, no "
                "multipliers'); ORCHID's temperature/composition sigma (e.g. 11 K, 0.011) is not converted to a driving-force sigma. FLAG "
                "(not changed): this is the one software-default scale left in the objective."}
    # 2 within-series
    it["2_within_series"] = {"pugliese1970 1448.15 K, x_Cr 0.95": "a_Cr = 0.112 among 0.979-0.998 (cell potential 1.236 V agrees "
                             "with neighbours): magnitude_suspect in the ORCHID reading, kept at its sigma (set E flag, unchanged)"}
    # 3 cross-quantity: liquid MD, dH = T dS between 1900 and 2200 K
    H = json.loads((PF / "liquid_checks_enthalpy.json").read_text())["H_mix"]
    S = json.loads((PF / "liquid_excess_entropy.json").read_text())["states"]
    rows = []
    for x, a, b in ((0.25, "Cr75Ni25_N108_T1900", "Cr75Ni25_N108_T2200"), (0.5, "Cr50Ni50_N108_T1900", "Cr50Ni50_N108_T2200"),
                    (0.75, "Cr25Ni75_N108_T1900", "Cr25Ni75_N108_T2200")):
        dH = (H[b]["H_mix_kJ_mol_atom"] - H[a]["H_mix_kJ_mol_atom"]) * 1e3
        sH = np.hypot(H[a]["H_mix_SE_kJ_mol_atom"], H[b]["H_mix_SE_kJ_mol_atom"]) * 1e3
        dS = S[b]["S_excess_total"] - S[a]["S_excess_total"]
        sS = np.hypot(S[a]["S_excess_total_u"], S[b]["S_excess_total_u"])
        TdS = 2050.0 * dS   # integral of T dS over 1900-2200 K at constant Cp_ex (midpoint rule)
        rows.append({"x_Ni": x, "dH_mix_2200_minus_1900_J": dH, "sd_J": sH, "dS_ex_2200_minus_1900": dS, "sd_S": sS,
                     "Tbar_dS_J": TdS, "sd_TdS_J": 2050 * sS, "Cp_ex_from_H": dH / 300.0, "Cp_ex_from_S": 2050 * dS / 300.0,
                     "z_dH": dH / sH, "z_dS": dS / sS, "z_consistency": (dH - TdS) / np.hypot(sH, 2050 * sS)})
    it["3_cross_quantity_liquid_T_dependence"] = {
        "rows": rows,
        "finding": "S_ex(2200) - S_ex(1900) is +0.32 to +0.73 J/mol-atom/K (0.9-2.3 sd), i.e. Cp_ex = +2.2 to +5.0 J/mol-atom/K, but the "
                   "same runs give H_mix(2200) - H_mix(1900) of -4.8, -1.1, -0.3 kJ/mol-atom (x_Ni 0.25, 0.5, 0.75), i.e. Cp_ex of -16, -4, -1 J/mol-atom/K. The "
                   "two estimates of Cp_ex have opposite signs (dH - T dS = -6.5, -2.2, -0.8 sd; the Cr-rich state fails clearly), so the 1900-2200 K difference is not a "
                   "thermodynamically consistent temperature dependence of the excess Gibbs energy. The Cr-rich 1900 K reference is an "
                   "undercooled liquid that crystallised after 82 ps (analysed over 80 ps). Read as a sampling/reference effect, not as "
                   "evidence for a T^2 or T ln T term; no term added. All six S_ex values stay in the fit at their u (flag).",
        "decision": "L0, L1 of the liquid kept a + bT; reported, no extra term"}
    # 4 basis and units
    it["4_basis_units"] = {"CRNI2 one-shot": "MLIP H_f relative to MLIP fcc Cr and fcc Ni (-14.496 kJ/mol-atom, s2) entered on the TDB's "
                           "SER basis as HM_FORM = -14.496 + 7.284/3 = -12.068 kJ/mol-atom (GFCCCR enthalpy 7284 J); residual at the "
                           "one-shot = 0 (checked)", "solutions": "HM_MIX relative to same-lattice end-members (ESPEI _MIX), per mole of atoms",
                           "liquid S_ex": "SM_MIX value = S_ex + S_ideal (pycalphad SM_MIX includes ideal mixing)"}
    # 5 duplicates
    it["5_duplicates"] = {
        "eutectic": "ORC-SV7H3CNRYS (1618 K; L 0.46, bcc 0.38, fcc 0.50; Hao citing [158,159]) may re-quote the arrests of Jenkins 1937 "
                    "(rows at 1611-1619 K, L 0.44-0.46) or Bechtoldt 1961; the original of [158,159] is not resolved here. Counted as printed; FLAG.",
        "jette1934": "6 identical row pairs in the ESPEI-datasets file (set F found them); set E counts them twice; kept as set E (frozen); FLAG",
        "CrNi2": "ORC-X3KVP7D3PO (text, 863 K) and the 9 Fig. 16(b) ordering marks (774-876 K) may share sources; only the text record is used"}
    # 6 cross-source at the same state
    sol = json.loads((PF / "solids_GRACE-2L-SMAX-OMAT-large.json").read_text())
    dft = {}
    for ph, f in (("BCC_A2", "dft_HM_MIX_BCC_A2_liu2016.json"), ("FCC_A1", "dft_HM_MIX_FCC_A1_liu2016.json")):
        d = json.loads((R / "data/thermo" / f).read_text())
        occ = d["solver"]["sublattice_occupancies"]
        xs = [o[0][1] if isinstance(o[0], list) else o[1] for o in occ]
        vals = np.ravel(d["values"])
        tab = {round(r["x_Ni"], 4): r["H_mix_s2_mean"] * 1e3 for r in sol["phases"][ph]["table"]}
        dft[ph] = [{"x_Ni": float(x), "DFT_Liu2016_J": float(v), "MLIP_s2_J": tab.get(round(float(x), 4)),
                    "diff_J": (tab[round(float(x), 4)] - float(v)) if round(float(x), 4) in tab else None} for x, v in zip(xs, vals)]
    it["6_cross_source"] = {
        "MLIP_vs_DFT_Liu2016": dft,
        "note": "MLIP (GRACE SMAX, s2, SQS 128) vs DFT SQS (Liu 2016) mixing enthalpies; disagreement reported, not settled. The fcc "
                "Cr-rich MLIP values use MLIP fcc Cr (37.8 kJ above bcc), the DFT ones their own fcc Cr: comparable as mixing energies.",
        "CrNi2_ordering": "text 863 K (ORC-X3KVP7D3PO, sigma 16 K) vs Fig. 16(b) marks 774-876 K (mean ~838 K): spread > sigma; reported"}
    it["7_pull_at_reference"] = "per-dataset log-likelihood of the pick by residual type in steps/*/evaluation.json; the set E pull at the " \
                                "Kunselman et al. reference is in the set E file (different model: no CRNI2, liquid L0 only)"
    (R / "results/data_consistency.json").write_text(json.dumps(out, indent=1, default=float))
    for r in rows:
        print({k: round(v, 3) for k, v in r.items()})
    for ph, l in dft.items():
        print(ph, [(round(z["x_Ni"], 3), round(z["DFT_Liu2016_J"]), None if z["MLIP_s2_J"] is None else round(z["MLIP_s2_J"])) for z in l])


if __name__ == "__main__":
    main()
