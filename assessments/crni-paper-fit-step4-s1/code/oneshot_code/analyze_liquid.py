"""Cr-Ni liquid analysis (Studio, CPU) on trajectories collected from spark1 into collected_liquid/<model>/<state>/.

Reuses, unchanged: hongliu_mixing.py (corrected chemical term) and the campaign VACF estimator / RDF helpers
as defined in <home>/ScientificRuns/hongliu-chemical-mixing-20261105/run_cuzr.py (imported; sha256 recorded).
Stages:
  checks   : liquid-state checks (species MSD and diffusion, energy drift, pressure), enthalpy of mixing
  cutoffs  : first minima of the partial RDFs per state
  ideal    : ideal-mixing check of the configurational term: labels permuted at random on every MD neighbour graph
             must give S_chem,ex ~ 0 (finite-sample bias reported), before any excess entropy is reported
  entropy  : S_ex = S_vib,ex + S_chem,ex at each T with pure-liquid references at the same T; 108 vs 864 check
Units J/mol-atom/K and kJ/mol-atom.  Element label 1 = Ni (species 0 = Cr).
"""
import json, sys, time, hashlib
from pathlib import Path
import numpy as np

HL = Path.home() / "ScientificRuns/hongliu-chemical-mixing-20261105"
sys.path.insert(0, str(HL))
import hongliu_mixing as hm
import run_cuzr as rc   # only its generic functions are used (partial_rdf, first_min, dos_from_velocities, s_vib)

ROOT = Path(__file__).resolve().parents[1]
MODEL = "GRACE-2L-SMAX-OMAT-large"
C = ROOT / "collected_liquid" / MODEL
OUT = ROOT / "results"
EV = 96.485332  # kJ/mol per eV
NBLOCK = 5
XS = {0.0: "Cr100Ni0", 0.25: "Cr75Ni25", 0.5: "Cr50Ni50", 0.75: "Cr25Ni75", 1.0: "Cr0Ni100"}
TS = (2200, 1900)
BENCH = "Cr50Ni50_N864_T2200"
# Liquid windows: states that crystallized during production are analysed only over their liquid part (disposition kept).
# Cr100Ni0 1900 K: 2-ps block means of U drop from -8.88 to -9.06 eV/atom starting at 82 ps, MSD over the last 20 ps 2 A^2
# (crystallized, 280 K below SGTE T_m); the first 80 ps are liquid (MSD and stationary U).
LIQUID_WINDOW_PS = {"Cr100Ni0_N108_T1900": 80.0}


def st(x, T, N=108):
    return f"{XS[x]}_N{N}_T{T}"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 23), b""):
            h.update(b)
    return h.hexdigest()


def have(s):
    return (C / s / "result.json").exists()


def nframes(s, interval_fs):
    w = LIQUID_WINDOW_PS.get(s)
    return None if w is None else int(round(w * 1000 / interval_fs))


def load(s):
    d = C / s
    pos = np.load(d / "positions_A.npy", mmap_mode="r")
    if nframes(s, 10):
        pos = pos[:nframes(s, 10)]
    cell = np.load(d / "cell_A.npy"); L = float(cell[0, 0]); assert np.allclose(cell, L * np.eye(3))
    lab = (np.load(d / "symbols.npy") == "Ni").astype(int)
    return pos, L, lab


def save(name, obj):
    p = OUT / name; t = p.with_suffix(".tmp"); t.write_text(json.dumps(obj, indent=1)); t.replace(p)


# ------------------------------------------------------------------ checks + enthalpy
def checks():
    res = {}
    for s in sorted(p.name for p in C.iterdir() if (p / "result.json").exists()):
        d = C / s
        pos, L, lab = load(s)
        th = np.load(d / "thermo_10fs.npy")
        if nframes(s, 10):
            th = th[:nframes(s, 10)]
        N = len(lab)
        H = (th[:, 0] + th[:, 1]) / N + th[:, 2] * th[:, 3] / N        # eV/atom, U + K + pV
        blocks = np.array_split(H, NBLOCK)
        bm = np.array([b.mean() for b in blocks])
        # species MSD from unwrapped positions (no wrapping in ase MD), centre-of-mass drift removed
        p = np.asarray(pos, float); p = p - p.mean(1, keepdims=True)
        msd = {}
        Dv = {}
        lags = np.array([100, 500, 1000, 2000, 5000])                     # x 10 fs
        for sp, k in (("Cr", 0), ("Ni", 1)):
            m = lab == k
            if not m.any():
                continue
            vals = [float(((p[l:, m] - p[:-l, m]) ** 2).sum(-1).mean()) for l in lags]
            msd[sp] = dict(zip([f"{l*10/1000:g}ps" for l in lags], vals))
            sl = np.polyfit(lags[1:] * 10e-15, np.array(vals[1:]) * 1e-20, 1)[0]
            Dv[sp] = float(sl / 6)
        res[s] = {"N": N, "H_eV_atom": float(H.mean()), "H_block_SE_eV_atom": float(bm.std(ddof=1) / np.sqrt(NBLOCK)),
                  "H_drift_last_minus_first_block_meV": float((bm[-1] - bm[0]) * 1000),
                  "U_eV_atom": float(th[:, 0].mean() / N), "P_GPa_mean": float(th[:, 2].mean() * 160.21766),
                  "V_A3_atom": float(th[0, 3] / N), "MSD_A2": msd, "D_m2_s": Dv,
                  "analysed_window_ps": LIQUID_WINDOW_PS.get(s, 100.0),
                  "liquid": bool(all(v > 5e-10 for v in Dv.values()) and all(m["50ps"] > 20 for m in msd.values()))}
        print(s, round(res[s]["H_eV_atom"], 5), res[s]["D_m2_s"], res[s]["liquid"], flush=True)
    hm_ = {}
    for T in TS:
        if not (st(0.0, T) in res and st(1.0, T) in res):
            continue
        h0, h1 = res[st(0.0, T)], res[st(1.0, T)]
        for x in (0.25, 0.5, 0.75):
            s = st(x, T)
            if s not in res:
                continue
            v = (res[s]["H_eV_atom"] - (1 - x) * h0["H_eV_atom"] - x * h1["H_eV_atom"]) * EV
            u = np.sqrt(res[s]["H_block_SE_eV_atom"] ** 2 + ((1 - x) * h0["H_block_SE_eV_atom"]) ** 2
                        + (x * h1["H_block_SE_eV_atom"]) ** 2) * EV
            hm_[s] = {"x_Ni": x, "T_K": T, "H_mix_kJ_mol_atom": float(v), "H_mix_SE_kJ_mol_atom": float(u),
                      "references": [st(0.0, T), st(1.0, T)],
                      "all_liquid": bool(res[s]["liquid"] and h0["liquid"] and h1["liquid"])}
    save("liquid_checks_enthalpy.json", {"states": res, "H_mix": hm_, "model": MODEL, "liquid_windows_ps": LIQUID_WINDOW_PS,
                                          "note": "H = <U+K> + <p>V per atom, NVT production 100 ps; SE from 5 blocks of 20 ps; "
                                                  "liquid = D > 5e-10 m2/s and MSD(50 ps) > 20 A2 for every species",
                                          "created_unix": time.time()})


# ------------------------------------------------------------------ cutoffs
def cutoffs():
    out = {}
    for s in sorted(p.name for p in C.iterdir() if (p / "result.json").exists()):
        pos, L, lab = load(s)
        stride = 50 if "N864" in s else 10
        r, g = rc.partial_rdf(pos, L, lab, stride=stride)
        rcm = np.full((2, 2), np.nan); peaks = {}
        for (i, j), gij in g.items():
            m, pk = rc.first_min(r, gij)
            rcm[i, j] = rcm[j, i] = m
            peaks[f"{'CrNi'[2*i:2*i+2]}-{'CrNi'[2*j:2*j+2]}"] = {"first_peak_A": pk, "first_min_A": m}
        tot = sum(g[k] for k in g)
        mt, _ = rc.first_min(r, tot / len(g))
        rcm = np.where(np.isnan(rcm), np.nanmax(rcm), rcm)
        out[s] = {"rc_partial_A": rcm.tolist(), "rc_total_A": mt, "partials": peaks, "L_A": L}
        print(s, peaks, round(mt, 3), flush=True)
    save("liquid_cutoffs.json", out)


def chem_state(s, rcm, stride=1, shuffle=None):
    pos, L, lab = load(s)
    nf = pos.shape[0]
    blocks = [hm.Accumulator() for _ in range(NBLOCK)]
    tot = hm.Accumulator()
    for f in range(0, nf, stride):
        lb = lab if shuffle is None else shuffle.permutation(lab)
        adj = hm.liquid_neighbours(np.asarray(pos[f], float), L, lb, rcm)
        st_ = hm.adj_statistics(lb, adj)
        tot.add(*st_); blocks[min(NBLOCK - 1, f * NBLOCK // nf)].add(*st_)
    return tot, blocks


# ------------------------------------------------------------------ ideal-mixing check
def ideal():
    cut = json.loads((OUT / "liquid_cutoffs.json").read_text())
    rows = {}
    rng = np.random.default_rng(20261105)
    for T in TS:
        for x in (0.25, 0.5, 0.75):
            s = st(x, T)
            if not have(s):
                continue
            # one common cutoff (total-RDF minimum) so the shuffled graph is the MD graph; labels permuted per frame
            rcm = np.full((2, 2), cut[s]["rc_total_A"])
            tot, blocks = chem_state(s, rcm, stride=5, shuffle=rng)
            r = tot.result(heavy=1)
            be = [b.result(heavy=1)["bethe_excess"] for b in blocks]
            rows[s] = {"x_Ni": x, "T_K": T, "S_ideal": r["ideal"], "S_chem_pair_shuffled": r["bethe"],
                       "S_chem_excess_shuffled": r["bethe_excess"], "block_SE": float(np.std(be, ddof=1) / np.sqrt(NBLOCK)),
                       "zbar": r["zbar"], "paper_eq15_16_shuffled": r["paper"]}
            print("ideal check", s, round(r["bethe_excess"], 4), "J/mol/K vs ideal", round(r["ideal"], 4), flush=True)
    passed = all(abs(v["S_chem_excess_shuffled"]) < 0.05 for v in rows.values())
    save("liquid_ideal_mixing_check.json", {"states": rows, "criterion": "|S_chem,ex(random labels)| < 0.05 J/mol-atom/K",
                                            "passed": bool(passed), "created_unix": time.time()})
    return passed


# ------------------------------------------------------------------ vibrational
def vib_state(s):
    d = C / s
    run = json.loads((d / "run.json").read_text())
    v = np.load(d / "velocities_ase.npy", mmap_mode="r")
    m = np.load(d / "masses_amu.npy")
    T, dt = run["target_T_K"], run["velocity_interval_fs"]
    if nframes(s, dt):
        v = v[:nframes(s, dt)]
    N = v.shape[1]
    nu, g, _, _ = rc.dos_from_velocities(np.asarray(v), m, dt, T, 3)
    full = rc.s_vib(nu, g, T) / N
    nf = v.shape[0]; bl = []
    for b in range(NBLOCK):
        sl = slice(b * nf // NBLOCK, (b + 1) * nf // NBLOCK)
        nu, g, _, _ = rc.dos_from_velocities(np.asarray(v[sl]), m, dt, T, 3)
        bl.append(rc.s_vib(nu, g, T) / N)
    return {"S_vib_full_3ps": float(full), "S_vib_blocks_3ps": [float(b) for b in bl],
            "S_vib_block_SE": float(np.std(bl, ddof=1) / np.sqrt(NBLOCK)), "T_K": T, "N": N,
            "velocities_sha256": sha(d / "velocities_ase.npy")}


def summarise(acc):
    r = acc.result(heavy=1)
    return {"x_Ni": r["x"][1], "zbar": r["zbar"], "y_bonds": r["y"], "S_ideal": r["ideal"], "S_chem_pair": r["bethe"],
            "S_chem_excess": r["bethe_excess"], "S_chem_excess_xref_variant": r["bethe_xref_excess"], "paper_eq15_16": r["paper"]}


def entropy():
    cut = json.loads((OUT / "liquid_cutoffs.json").read_text())
    chk = json.loads((OUT / "liquid_checks_enthalpy.json").read_text())["states"]
    ideal_ok = json.loads((OUT / "liquid_ideal_mixing_check.json").read_text())["passed"]
    variants = {"partial_rdf_minima": lambda c: np.array(c["rc_partial_A"]),
                "partial_minus_0.1A": lambda c: np.array(c["rc_partial_A"]) - 0.1,
                "partial_plus_0.1A": lambda c: np.array(c["rc_partial_A"]) + 0.1,
                "single_total_rdf_minimum": lambda c: np.full((2, 2), c["rc_total_A"])}
    res = {"ideal_mixing_check_passed": ideal_ok, "states": {}, "cutoff_cases": {}, "vibrational": {}}
    alloys = [st(x, T) for T in TS for x in (0.25, 0.5, 0.75) if have(st(x, T))] + ([BENCH] if have(BENCH) else [])
    for vname, fn in variants.items():
        res["cutoff_cases"][vname] = {}
        for s in alloys:
            tot, blocks = chem_state(s, fn(cut[s]), stride=1 if "N864" not in s else 10)
            row = summarise(tot)
            vals = [summarise(b)["S_chem_excess"] for b in blocks]
            row["S_chem_excess_block_SE"] = float(np.std(vals, ddof=1) / np.sqrt(NBLOCK))
            res["cutoff_cases"][vname][s] = row
            print(vname, s, round(row["S_chem_excess"], 4), round(row["zbar"], 2), flush=True)
    vib = {}
    for s in sorted(p.name for p in C.iterdir() if (p / "result.json").exists()):
        vib[s] = vib_state(s); print("vib", s, round(vib[s]["S_vib_full_3ps"], 3), round(vib[s]["S_vib_block_SE"], 3), flush=True)
    res["vibrational"] = vib
    base = res["cutoff_cases"]["partial_rdf_minima"]
    for T in TS:
        r0, r1 = st(0.0, T), st(1.0, T)
        if r0 not in vib or r1 not in vib:
            continue
        for x in (0.25, 0.5, 0.75):
            s = st(x, T)
            if s not in vib:
                continue
            vex = vib[s]["S_vib_full_3ps"] - (1 - x) * vib[r0]["S_vib_full_3ps"] - x * vib[r1]["S_vib_full_3ps"]
            vse = float(np.sqrt(vib[s]["S_vib_block_SE"] ** 2 + ((1 - x) * vib[r0]["S_vib_block_SE"]) ** 2 + (x * vib[r1]["S_vib_block_SE"]) ** 2))
            ch = base[s]["S_chem_excess"]; cse = base[s]["S_chem_excess_block_SE"]
            spread = max(abs(res["cutoff_cases"][v][s]["S_chem_excess"] - ch) for v in variants)
            uch = float(np.hypot(cse, spread))
            ok = bool(chk[s]["liquid"] and chk[r0]["liquid"] and chk[r1]["liquid"])
            res["states"][s] = {"x_Ni": x, "T_K": T, "S_vib_excess": float(vex), "S_vib_excess_SE": vse,
                                "S_chem_excess": ch, "S_chem_excess_block_SE": cse, "S_chem_excess_cutoff_spread": spread,
                                "S_chem_excess_u": uch, "S_excess_total": float(vex + ch), "S_excess_total_u": float(np.hypot(vse, uch)),
                                "S_ideal": base[s]["S_ideal"], "zbar": base[s]["zbar"], "paper_eq15_16_readings": base[s]["paper_eq15_16"],
                                "all_states_liquid": ok, "references": [r0, r1],
                                "status": "provisional (correction ours, pending human review)" if ok and ideal_ok else "held"}
            print("S_ex", s, round(vex, 3), "+", round(ch, 3), "=", round(vex + ch, 3), "+-", round(np.hypot(vse, uch), 3), flush=True)
    s108, s864 = st(0.5, 2200), BENCH
    if s108 in vib and s864 in vib:
        a, b = vib[s108]["S_vib_full_3ps"], vib[s864]["S_vib_full_3ps"]
        res["finite_size"] = {"state": "Cr50Ni50 2200 K", "S108_vib": a, "S864_vib": b, "relative_difference_percent": 100 * abs(a - b) / abs(b),
                              "pass_5_percent": bool(100 * abs(a - b) / abs(b) < 5),
                              "S_chem_excess_N108": base.get(s108, {}).get("S_chem_excess"),
                              "S_chem_excess_N864": base.get(s864, {}).get("S_chem_excess"),
                              "S_vib_excess_N864_not_formed": "no 864-atom pure references (protocol: one composition only)"}
    res["meta"] = {"created_unix": time.time(), "model": MODEL, "library_sha256": sha(HL / "hongliu_mixing.py"),
                   "estimator_source_sha256": sha(HL / "run_cuzr.py"), "script_sha256": sha(__file__), "units": "J/mol-atom/K",
                   "uncertainty": "S_chem u = quadrature(5x20 ps block SE, max |cutoff variant - base|); S_vib SE from 5 blocks of alloy "
                                  "and x-weighted pure references; potential and method errors not included; excess electronic entropy assumed zero (metallic liquid; PI, 6 Nov)",
                   "electronic_entropy": "excess electronic entropy assumed zero (metallic liquid; PI, 6 Nov)",
                   "S_el_excess_assumption": {"value_J_mol_atom_K": 0.0, "basis": "assumed zero for a metallic liquid (PI ruling, 6 Nov 2026); not computed"},
                   "liquid_windows_ps": LIQUID_WINDOW_PS}
    save("liquid_excess_entropy.json", res)


if __name__ == "__main__":
    for stage in sys.argv[1:]:
        {"checks": checks, "cutoffs": cutoffs, "ideal": ideal, "entropy": entropy}[stage]()
