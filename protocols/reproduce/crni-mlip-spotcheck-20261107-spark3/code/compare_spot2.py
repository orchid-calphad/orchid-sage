"""GPU spot check of 7 Nov 2026 (PI approval: "a small GPU spot check of the MLIP steps"): compare one SQS cell and one liquid MD
state recomputed on spark3 with the recorded spark1 values (crni-phaseforge-20261105).
  compare_spot2.py RECORDED_CAMPAIGN B069_RESULTS OUT_JSON OUT_MD
Tolerances (declared in the specific protocol): MLIP energies 0.1 kJ/mol-atom; liquid MD enthalpy within its statistical error
(|dH| <= 2 sqrt(SE_ref^2 + SE_new^2), SE = block standard error of 5 blocks of 20 ps, as in analyze_liquid.py)."""
import hashlib, json, sys
from pathlib import Path
import numpy as np

EV = 96.485332  # kJ/mol per eV
REC, NEW, OJ, OM = map(Path, sys.argv[1:5])


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


out = {"check": "crni GPU spot check (7 Nov 2026)", "original_host": "spark1", "rerun_host": "spark3",
       "model": "GRACE-2L-SMAX-OMAT-large", "solids": [], "liquid": None}
cell = "BCC_A2/x0.2500_s2026110501"
o = json.loads((REC / "collected_solids/GRACE-2L-SMAX-OMAT-large" / cell / "result.json").read_text())
n = json.loads((NEW / "solids/GRACE-2L-SMAX-OMAT-large" / cell / "result.json").read_text())
assert o["input_sha256"] == n["input_sha256"] and o["runner_sha256"] == n["runner_sha256"]
for st in ("s0_unrelaxed", "s1_volume", "s2_volume_ions", "s3_full"):
    a, b = o["stages"][st]["energy_eV_atom"], n["stages"][st]["energy_eV_atom"]
    d = (b - a) * EV
    out["solids"].append({"cell": cell, "stage": st, "E_spark1_eV_atom": a, "E_spark3_eV_atom": b, "diff_kJ_mol_atom": d, "tol_kJ_mol_atom": 0.1,
                          "lattice_kept_spark1": o["stages"][st].get("lattice_check", {}).get("lattice_kept"),
                          "lattice_kept_spark3": n["stages"][st].get("lattice_check", {}).get("lattice_kept"),
                          "pass": abs(d) <= 0.1 and o["stages"][st].get("lattice_check", {}).get("lattice_kept") == n["stages"][st].get("lattice_check", {}).get("lattice_kept")})
out["solids_input_sha256"] = o["input_sha256"]; out["solids_runner_sha256"] = o["runner_sha256"]
ld = NEW / "liquid/GRACE-2L-SMAX-OMAT-large/Cr50Ni50_N108_T2200"
if (ld / "result.json").exists():
    run = json.loads((ld / "run.json").read_text())
    th = np.load(ld / "thermo_10fs.npy"); N = 108
    H = (th[:, 0] + th[:, 1]) / N + th[:, 2] * th[:, 3] / N
    bm = np.array([b.mean() for b in np.array_split(H, 5)])
    new = {"H_eV_atom": float(H.mean()), "H_block_SE_eV_atom": float(bm.std(ddof=1) / np.sqrt(5)), "V_A3_atom": float(th[:, 3].mean() / N),
           "H_drift_last_minus_first_block_meV": float((bm[-1] - bm[0]) * 1000)}
    ref = json.loads((REC / "results/liquid_checks_enthalpy.json").read_text())["states"]["Cr50Ni50_N108_T2200"]
    d = (new["H_eV_atom"] - ref["H_eV_atom"]) * EV
    se = np.hypot(new["H_block_SE_eV_atom"], ref["H_block_SE_eV_atom"]) * EV
    out["liquid"] = {"state": "Cr50Ni50_N108_T2200", "seed": run["seed"], "input_sha256": run["input_sha256"], "runner_sha256": run["runner_sha256"],
                     "production_ps": json.loads((ld / "result.json").read_text())["production_ps"],
                     "H_spark1_eV_atom": ref["H_eV_atom"], "SE_spark1_eV_atom": ref["H_block_SE_eV_atom"], "H_spark3_eV_atom": new["H_eV_atom"],
                     "SE_spark3_eV_atom": new["H_block_SE_eV_atom"], "V_spark1_A3_atom": ref["V_A3_atom"], "V_spark3_A3_atom": new["V_A3_atom"],
                     "diff_kJ_mol_atom": float(d), "combined_SE_kJ_mol_atom": float(se), "tol_rule": "|dH| <= 2 x combined block SE",
                     "tol_kJ_mol_atom": float(2 * se), "z": float(d / se), "pass": bool(abs(d) <= 2 * se),
                     "note": "MD trajectories diverge across GPUs (chaotic dynamics); the mean enthalpy is compared within its statistical error"}
ok = all(r["pass"] for r in out["solids"]) and (out["liquid"] is None or out["liquid"]["pass"])
out["overall"] = "PASS" if ok and out["liquid"] is not None else ("PASS (solids; liquid pending)" if ok else "FAIL")
OJ.write_text(json.dumps(out, indent=1))
L = [f"# GPU spot check of the MLIP steps (7 Nov 2026): spark3 vs the recorded spark1 values", "",
     "Model GRACE-2L-SMAX-OMAT-large; container cuzr-phaseforge-grace-gpu:20261104 (spark3 image sha256:8eae0b91...); code relax_solids.py "
     f"{o['runner_sha256'][:12]}..., run_liquid.py a4b6d40c...; weights hash-checked against provenance/potential_sha256.txt.", "",
     "| item | quantity | reference (spark1) | rerun (spark3) | difference | tolerance | result |", "|---|---|---|---|---|---|---|"]
for r in out["solids"]:
    L.append(f"| bcc SQS x_Ni 0.25, seed s2026110501 | E {r['stage']} (eV/atom) | {r['E_spark1_eV_atom']:.8f} | {r['E_spark3_eV_atom']:.8f} | {r['diff_kJ_mol_atom']:+.6f} kJ/mol-atom | 0.1 kJ/mol-atom | {'PASS' if r['pass'] else 'FAIL'} |")
if out["liquid"]:
    q = out["liquid"]
    L.append(f"| liquid Cr50Ni50, 108 atoms, 2200 K, 100 ps, seed {q['seed']} | H (eV/atom) | {q['H_spark1_eV_atom']:.5f} ± {q['SE_spark1_eV_atom']:.5f} | {q['H_spark3_eV_atom']:.5f} ± {q['SE_spark3_eV_atom']:.5f} | {q['diff_kJ_mol_atom']:+.3f} kJ/mol-atom (z {q['z']:+.2f}) | {q['tol_kJ_mol_atom']:.3f} kJ/mol-atom (2 x combined SE) | {'PASS' if q['pass'] else 'FAIL'} |")
L += ["", f"**Overall: {out['overall']}**", ""]
OM.write_text("\n".join(L) + "\n")
print(out["overall"]); print("\n".join(L))
# --- diagnostic (added after the comparison, never changes the verdict above): the NVT production volume is the mean NPT
# volume of the last 5 ps of the density stage, so <p> at that volume is not 1 atm and <p>V enters H. Compare U+K and p.
if out["liquid"]:
    def stats(d):
        th = np.load(Path(d) / "thermo_10fs.npy"); N = 108
        E = (th[:, 0] + th[:, 1]) / N; pv = th[:, 2] * th[:, 3] / N
        se = lambda a: float(np.array([b.mean() for b in np.array_split(a, 5)]).std(ddof=1) / np.sqrt(5))  # noqa: E731
        return {"E_UK_eV_atom": float(E.mean()), "E_SE": se(E), "pV_eV_atom": float(pv.mean()), "p_GPa": float(th[:, 2].mean() * 160.21766),
                "V_A3_atom": float(th[:, 3].mean() / N), "T_K": float((th[:, 1] / N).mean() / (1.5 * 8.617333262e-5)),
                "nvt_volume_from_density_stage": json.loads((Path(d) / "density.complete.json").read_text())["npt_mean_volume_A3_atom_last5ps"]}
    a = stats(REC / "collected_liquid/GRACE-2L-SMAX-OMAT-large/Cr50Ni50_N108_T2200"); b = stats(ld)
    dE = (b["E_UK_eV_atom"] - a["E_UK_eV_atom"]) * EV; sE = np.hypot(a["E_SE"], b["E_SE"]) * EV
    out["liquid_diagnostic"] = {"spark1": a, "spark3": b, "dE_UK_kJ_mol_atom": float(dE), "combined_SE_E_kJ_mol_atom": float(sE), "z_E": float(dE / sE),
                                "d_pV_kJ_mol_atom": float((b["pV_eV_atom"] - a["pV_eV_atom"]) * EV),
                                "reading": "the enthalpy difference is mostly the <p>V term: the NVT volume taken from 5 ps of NPT differs by "
                                           f"{b['nvt_volume_from_density_stage'] - a['nvt_volume_from_density_stage']:+.3f} A3/atom between the runs, so <p> is "
                                           f"{a['p_GPa']:+.2f} GPa (spark1) and {b['p_GPa']:+.2f} GPa (spark3); the block SE of the production run does not "
                                           "contain this volume uncertainty. Not a verdict change; a note for the PI."}
    OJ.write_text(json.dumps(out, indent=1))
    q = out["liquid_diagnostic"]
    with OM.open("a") as fh:
        fh.write(f"Diagnostic (not a verdict change): U+K differs by {q['dE_UK_kJ_mol_atom']:+.3f} kJ/mol-atom (z {q['z_E']:+.2f}); <p>V differs by "
                 f"{q['d_pV_kJ_mol_atom']:+.3f} kJ/mol-atom. {q['reading']}\n")
    print(json.dumps({k: v for k, v in q.items() if k not in ('spark1', 'spark3')}, indent=1)); print(a); print(b)
