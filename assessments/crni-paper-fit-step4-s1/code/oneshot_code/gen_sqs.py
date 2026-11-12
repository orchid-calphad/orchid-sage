"""Cr-Ni SQS generation with m_scraps (adapted from the Cu-Zr campaign code/sqs_mscraps_source.py).

Changes from Cu-Zr and why:
  * 128-atom cells for BCC_A2 and FCC_A1 (PI rule, memory mlip-relaxation-protocol: solution SQS > 100 atoms,
    128 for bcc/fcc; Cu-Zr used 64). BCC: 4x4x4 conventional cube; FCC: most compact 128-atom supercell of the
    primitive cell (ase find_optimal_cell_shape, target sc).
  * Two independent SQS seeds per mixed composition (configuration spread as an uncertainty).
  * Pure-element cells in the same 128-atom supercells (same k-free MLIP, same cell -> no size bias in references).
  * LIQUID starting configurations: 108-atom fcc SQS (3x3x3 conventional), pairs 2 shells, exactly as Cu-Zr.
Same m_scraps objective, figure cutoffs (in NN units), auto_budget and ranks as Cu-Zr.
Run with <home>/.venvs/phaseforge/bin/python (m_scraps 0.6.0).
"""
import json, sys, time
from pathlib import Path
import numpy as np
from ase.build import bulk, find_optimal_cell_shape, make_supercell
import m_scraps

SP = ["Cr", "Ni"]
V = {"Cr": 12.00, "Ni": 10.94}   # A^3/atom, room-temperature elemental volumes (start geometry only; rescaled at run time)
CUT = {"FCC_A1": (2.05, 1.45, 1.05), "BCC_A2": (2.05, 1.20, 1.05), "LIQUID": (1.45, 1.05, 1.05)}
GRID = {"BCC_A2": [0, 8, 16, 32, 48, 64, 128],              # n_Ni of 128: x_Ni 0, .0625, .125, .25, .375, .5, 1 (ref)
        "FCC_A1": [0, 40, 48, 64, 80, 96, 112, 128],        # x_Ni 0 (ref), .3125, .375, .5, .625, .75, .875, 1
        "LIQUID": [0, 27, 54, 81, 108]}                     # x_Ni 0, .25, .5, .75, 1 of 108
SEEDS = {"BCC_A2": [2026110501, 2026110502], "FCC_A1": [2026110511, 2026110512], "LIQUID": [2026110521]}


def vol(x):
    return (1 - x) * V["Cr"] + x * V["Ni"]


def base(lat, x):
    v = vol(x)
    if lat == "BCC_A2":
        a = (2 * v) ** (1 / 3)
        return bulk("Cr", "bcc", a=a, cubic=True).repeat((4, 4, 4)), a * np.sqrt(3) / 2
    a = (4 * v) ** (1 / 3)
    if lat == "LIQUID":
        return bulk("Cr", "fcc", a=a, cubic=True).repeat((3, 3, 3)), a / np.sqrt(2)
    p = bulk("Cr", "fcc", a=a)
    P = find_optimal_cell_shape(p.cell, 128, "sc", verbose=False)
    return make_supercell(p, P), a / np.sqrt(2)


def make(lat, n_ni, seed, outdir):
    a0, d1 = base(lat, 0.5)
    n = len(a0)
    x = n_ni / n
    a0, d1 = base(lat, x)
    name = f"x{x:.4f}_s{seed}" if 0 < n_ni < n else f"x{x:.4f}_pure"
    d = Path(outdir) / lat / name
    if (d / "POSCAR").exists():
        return
    d.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    meta = {"lattice": lat, "x_Ni": x, "n_atoms": n, "n_Ni": n_ni, "generator": f"m_scraps {m_scraps.__version__}",
            "cell": a0.cell.array.tolist(), "nn_distance_start_A": d1}
    if n_ni in (0, n):
        a = a0.copy(); a.set_chemical_symbols([SP[1] if n_ni else SP[0]] * n)
        meta["note"] = "pure element in the same supercell"
    else:
        cut = [c * d1 for c in CUT[lat]]
        a = m_scraps.run_sqs_from_atoms(a0, species=SP, element_counts=[n - n_ni, n_ni], cell_dim=(1, 1, 1),
                                        figure_cutoffs=cut, figure_objective="weighted_l1", figure_wd=0.0, figure_wn=1.0,
                                        auto_budget=2, rng_seed=seed, ranks=4, work_dir=str(d / "m_scraps"))
        meta.update(seed=seed, figure_cutoffs_A=cut, figure_cutoffs_nn=CUT[lat], objective="weighted_l1 (wd=0, wn=1)",
                    auto_budget=2, final_fitness=a.info.get("scraps_final_fitness"))
    a.pbc = True
    # ideal-site reference kept in the same atom order as POSCAR (used by the lattice checks)
    a.write(d / "POSCAR", format="vasp", direct=True, sort=False)
    meta["seconds"] = round(time.time() - t0, 1)
    (d / "sqs_meta.json").write_text(json.dumps(meta, indent=1))
    print(lat, name, n, meta.get("final_fitness"), meta["seconds"], "s", flush=True)


if __name__ == "__main__":
    out = sys.argv[1]
    for lat, grid in GRID.items():
        for n_ni in grid:
            for s in (SEEDS[lat] if 0 < n_ni < (108 if lat == "LIQUID" else 128) else [None]):
                make(lat, n_ni, s, out)
