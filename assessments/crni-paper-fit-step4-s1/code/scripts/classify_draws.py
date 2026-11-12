"""Per-draw classification of the Laplace mixture draws: strict topology, topology apart from the CrNi2 window, gaps by phase,
Ni-rich bcc field (single-phase BCC_A2 at x_Ni > 0.5 anywhere 600-2200 K). usage: classify_draws.py <draws.npy> <out.json>"""
import json, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pd4
TU = np.arange(600.0, 2201.0, 5.0)


def one(th):
    ref = pd4.ref_grid(TU)
    tp = pd4.topology(th, TU, ref, t_c2=(0.0, 1e9))
    di = pd4.diagram(th, TU, ref)
    nirich_bcc = any(k == 1 and p == ("BCC_A2",) and xr > 0.5 and xr - xl > 0.005 for segs in di for k, p, xl, xr in segs)
    return {"ok_no_crni2_window": tp["ok"], "T_CrNi2": tp["T_CrNi2_max"], "T_eut": tp["T_liquid_min"], "n_bad": tp["n_bad"],
            "gap_phases": sorted({g[1] for g in tp["gaps"]}), "gap_T": [min((g[0] for g in tp["gaps"]), default=None), max((g[0] for g in tp["gaps"]), default=None)],
            "nirich_bcc": bool(nirich_bcc)}


if __name__ == "__main__":
    D = np.load(sys.argv[1]); pd4.ref_grid(TU)
    with get_context("spawn").Pool(4) as p:
        r = p.map(one, list(D), chunksize=10)
    ok2 = np.array([z["ok_no_crni2_window"] for z in r]); tc = np.array([z["T_CrNi2"] for z in r])
    strict = ok2 & (tc >= 800) & (tc <= 930)
    out = {"n": len(r), "P_ok_strict": float(strict.mean()), "P_ok_apart_from_CrNi2_window": float(ok2.mean()),
           "P_CrNi2_in_800_930": float(((tc >= 800) & (tc <= 930)).mean()), "P_CrNi2_within_25K_of_863": float((np.abs(tc - 863) <= 25).mean()),
           "P_gap_by_phase": {ph: float(np.mean([ph in z["gap_phases"] for z in r])) for ph in ("BCC_A2", "FCC_A1", "LIQUID")},
           "P_nirich_bcc_field": float(np.mean([z["nirich_bcc"] for z in r])), "draws": r}
    Path(sys.argv[2]).write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: v for k, v in out.items() if k != "draws"}))
    g = [z["gap_T"] for z in r if z["gap_phases"]]
    if g: print("gap T ranges (first 10):", g[:10])
