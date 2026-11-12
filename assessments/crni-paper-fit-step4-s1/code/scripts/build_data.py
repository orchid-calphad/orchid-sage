"""Build the step datasets in data/<group>/ (labelled copies; values, sigma and weights unchanged from their sources).

groups:
  oneshot  PhaseForge one-shot observations (protocol 0.0a/0.1): BCC/FCC HM_MIX 298.15 K at x_Ni 0.25/0.5/0.75 (s2 seed means),
           CRNI2 HM_FORM 298.15 K, LIQUID HM_MIX 2200 K (MD), each sigma = max(sigma_MLIP, s0-s2, s2-s3) (Cu-Zr fit_step.py rule);
           LIQUID SM_MIX 1900/2200 K (provisional S_ex + S_ideal, ESPEI weight 0.2/u)
  liq      set E ZPF rows that contain LIQUID ((i) and (ii) files of 0.4a), + ORCHID eutectic ORC-SV7H3CNRYS (3-phase ZPF)
  thermo   set E thermochemistry: activities, HM_MIX (liquid; DFT Liu 2016 bcc/fcc), HM_FORM (Dench, Watson)
  solid    set E ZPF rows without LIQUID; CrNi2 ordering ORC-X3KVP7D3PO (863 K) as CRNI2 (x 2/3) + FCC_A1 (zero phase fraction)
Writes results/data_build.json (counts, provenance)."""
import copy
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
SR = Path.home() / "ScientificRuns"
SETE = SR / "cr-ni-rebuild-20261105/inputs/derived/setE_orchid_sigmas/datasets"
PF = SR / "crni-phaseforge-20261105/results"
SIG_MLIP = json.loads((Path.home() / "projects/orchid-phaseforge-demo/results/sigma_mlip.json").read_text())["sigma_MLIP_kJ"] * 1000
D = R / "data"
PARENTS = json.loads((SR / "cr-ni-rebuild-20261105/inputs/derived/setD_twophase_hinge/BUILD_LOG.json").read_text())["datasets"]
TAG = "crni-paper-fit-20261106"


def dump(g, name, d):
    (D / g).mkdir(parents=True, exist_ok=True)
    (D / g / name).write_text(json.dumps(d, indent=1))


def sol(ph, x):
    return {"mode": "manual", "sublattice_site_ratios": [1], "sublattice_configurations": [[["CR", "NI"]]],
            "sublattice_occupancies": [[[1 - x, x]]]}


def oneshot(log):
    S = json.loads((PF / "solids_GRACE-2L-SMAX-OMAT-large.json").read_text())
    obs = []
    for ph in ("BCC_A2", "FCC_A1"):
        tab = {round(r["x_Ni"], 4): r for r in S["phases"][ph]["table"]}
        for x in (0.25, 0.5, 0.75):
            r = tab[x]
            s2, s0, s3 = r["H_mix_s2_mean"] * 1e3, r["H_mix_s0_mean"] * 1e3, r["H_mix_s3_mean"] * 1e3
            sg = max(SIG_MLIP, s0 - s2, s2 - s3, abs(r["seed_half_spread"]) * 1e3)
            basis = "sigma_MLIP" if sg == SIG_MLIP else "relaxation interval"
            obs.append({"id": f"{ph}_x{x:.2f}", "phase": ph, "output": "HM_MIX", "T_K": 298.15, "x_Ni": x, "value": s2, "sigma": sg,
                        "sigma_basis": basis, "interval_J": [s3, s0]})
    c = S["phases"]["FCC_ORDERED"]["cells"]["x0.6667_Pt2Mo_CrNi2"]["stages"]
    h2, h0, h3 = (c[k]["H_form_fcc_ref_kJ_mol_atom"] * 1e3 for k in ("s2_volume_ions", "s0_unrelaxed", "s3_full"))
    dser = 7284.0 / 3  # SGTE fcc Cr enthalpy above bcc Cr, per mole of atoms of CrNi2 (1/3 Cr): TDB uses GFCCCR
    sg = max(SIG_MLIP, h0 - h2, h2 - h3)
    obs.append({"id": "CRNI2", "phase": "CRNI2", "output": "HM_FORM", "T_K": 298.15, "x_Ni": 2 / 3, "value": h2 + dser, "sigma": sg,
                "sigma_basis": "sigma_MLIP" if sg == SIG_MLIP else "relaxation interval", "value_fcc_refs": h2,
                "note": "SER basis of the TDB = MLIP H_f vs fcc Cr, fcc Ni (s2) + 7284/3 J (SGTE fcc-bcc Cr enthalpy), as the one-shot TDB"})
    L = json.loads((PF / "liquid_checks_enthalpy.json").read_text())["H_mix"]
    for x, k in ((0.25, "Cr75Ni25_N108_T2200"), (0.5, "Cr50Ni50_N108_T2200"), (0.75, "Cr25Ni75_N108_T2200")):
        obs.append({"id": f"LIQUID_x{x:.2f}", "phase": "LIQUID", "output": "HM_MIX", "T_K": 2200.0, "x_Ni": x,
                    "value": L[k]["H_mix_kJ_mol_atom"] * 1e3, "sigma": SIG_MLIP, "sigma_basis": "sigma_MLIP (MD block SE %.0f J)" %
                    (L[k]["H_mix_SE_kJ_mol_atom"] * 1e3)})
    for o in obs:
        if o["phase"] == "CRNI2":
            solver = {"mode": "manual", "sublattice_site_ratios": [1, 2], "sublattice_configurations": [["CR", "NI"]]}
        else:
            solver = sol(o["phase"], o["x_Ni"])
        d = {"components": ["CR", "NI"], "phases": [o["phase"]], "solver": solver, "conditions": {"P": 101325, "T": o["T_K"]},
             "output": o["output"], "values": [[[o["value"]]]], "weight": 500.0 / o["sigma"],
             "reference": f"PhaseForge one-shot GRACE-2L-SMAX-OMAT-large observation {o['id']} ({TAG}); sigma {o['sigma']:.0f} J/mol-atom ({o['sigma_basis']})",
             "comment": "protocol 0.0a/0.1 one-shot observation; ESPEI weight = 500/sigma"}
        dump("oneshot", f"oneshot_{o['output']}_{o['id']}.json", d)
    E = json.loads((PF / "liquid_excess_entropy.json").read_text())["states"]
    sm = []
    for k, st in E.items():
        x, u = st["x_Ni"], st["S_excess_total_u"]
        val = st["S_excess_total"] + st["S_ideal"]
        d = {"components": ["CR", "NI"], "phases": ["LIQUID"], "solver": sol("LIQUID", x), "conditions": {"P": 101325, "T": float(st["T_K"])},
             "output": "SM_MIX", "values": [[[val]]], "weight": 0.2 / u, "tags": ["provisional"],
             "reference": f"GRACE-2L-SMAX-OMAT-large liquid MD {k}: vibrational (VACF) + corrected chemical excess entropy (provisional; correction ours); "
                          f"value = S_ex {st['S_excess_total']:.4f} + S_ideal {st['S_ideal']:.4f}; u {u:.3f} J/mol-atom/K; S_el,ex = 0 (PI 6 Nov)"}
        dump("oneshot", f"provisional_SM_MIX_LIQUID_{k}.json", d)
        sm.append({"state": k, "x_Ni": x, "T_K": st["T_K"], "S_ex": st["S_excess_total"], "u": u, "weight": 0.2 / u})
    log["oneshot"] = {"sigma_MLIP_J": SIG_MLIP, "observations": obs, "liquid_S_ex": sm}
    (R / "results" / "oneshot_observations.json").write_text(json.dumps({"model": "GRACE-2L-SMAX-OMAT-large", "observations": obs,
                                                                         "liquid_S_ex": sm}, indent=1))


def split_zpf(log):
    log["zpf_split"] = {}
    for f in sorted(SETE.glob("zpf*.json")):
        d = json.loads(f.read_text())
        T = d["conditions"]["T"]
        T = T if isinstance(T, list) else [T] * len(d["values"])
        rows = {"liq": [], "solid": []}
        if f.name.startswith("zpf_single"):  # (i) rows follow their parent (ii) row (set D BUILD_LOG parent_indices)
            pl = PARENTS[f.name]
            par = json.loads((SETE / pl["parent_dataset"]).read_text())["values"]
            for i, pi in enumerate(pl["parent_indices"]):
                rows["liq" if any(v[0] == "LIQUID" for v in par[pi]) else "solid"].append(i)
        else:
            for i, (t, r) in enumerate(zip(T, d["values"])):
                rows["liq" if any(v[0] == "LIQUID" for v in r) else "solid"].append(i)
        for g, idx in rows.items():
            if not idx:
                continue
            d2 = copy.deepcopy(d)
            d2["values"] = [d["values"][i] for i in idx]
            d2["conditions"] = dict(d["conditions"], T=[T[i] for i in idx])
            d2["phases"] = sorted({v[0] for r in d2["values"] for v in r})
            d2["comment"] = d.get("comment", "") + f" | {TAG}: rows {'with' if g == 'liq' else 'without'} LIQUID of set E file (indices {idx}); values unchanged"
            dump(g, f.name, d2)
        log["zpf_split"][f.name] = {g: len(v) for g, v in rows.items()}
    # ORCHID eutectic (accepted, experimental): ORC-SV7H3CNRYS
    d = {"components": ["CR", "NI"], "phases": ["BCC_A2", "FCC_A1", "LIQUID"], "conditions": {"P": 101325, "T": [1618.0]},
         "output": "ZPF", "values": [[["LIQUID", ["NI"], [0.46]], ["BCC_A2", ["NI"], [0.38]], ["FCC_A1", ["NI"], [0.50]]]],
         "reference": "ORCHID ORC-SV7H3CNRYS (Hao, Ruban, Xiong, Calphad 73 (2021) 102268, p. 13, citing [158,159]); eutectic 1618 K, "
                      "L 0.46, bcc 0.38, fcc 0.50 x_Ni; sigma_eff 11 K", "comment": f"{TAG}: three-phase invariant; possible overlap with "
                      "Jenkins 1937 arrests near 1618 K (flagged in data_consistency.json, counted as printed)"}
    dump("liq", "zpf_eutectic_ORC-SV7H3CNRYS.json", d)
    # CrNi2 ordering, ORC-X3KVP7D3PO
    d = {"components": ["CR", "NI"], "phases": ["CRNI2", "FCC_A1"], "conditions": {"P": 101325, "T": [863.0]}, "output": "ZPF",
         "values": [[["CRNI2", ["NI"], [0.666667]], ["FCC_A1", ["NI"], [None]]]],
         "reference": "ORCHID ORC-X3KVP7D3PO (Hao et al. 2021 p. 13: CrNi2 ordering at 863 K near 66.7 at.% Ni, XRD and neutron diffraction "
                      "[160,161]; experimental; single reader, not yet accepted); sigma_eff 16 K",
         "comment": f"{TAG}: highest temperature of CRNI2 (x 2/3) on the hull; the fcc partner at zero phase fraction with null composition "
                    "(0.4a form); composition 'vicinity of 66.7 at.% Ni' taken as 2/3 (specification gap)"}
    dump("solid", "zpf_CRNI2_ordering_ORC-X3KVP7D3PO.json", d)


def thermo(log):
    n = []
    for f in sorted(SETE.glob("*.json")):
        if f.name.startswith("zpf"):
            continue
        d = json.loads(f.read_text())
        d["comment"] = d.get("comment", "") + f" | {TAG}: set E file unchanged"
        dump("thermo", f.name, d)
        n.append(f.name)
    log["thermo_files"] = n


if __name__ == "__main__":
    log = {}
    oneshot(log)
    split_zpf(log)
    thermo(log)
    (R / "results" / "data_build.json").write_text(json.dumps(log, indent=1))
    for g in ("oneshot", "liq", "thermo", "solid"):
        print(g, len(list((D / g).glob("*.json"))))
    for o in log["oneshot"]["observations"]:
        print(o["id"], round(o["value"]), round(o["sigma"]), o["sigma_basis"])
