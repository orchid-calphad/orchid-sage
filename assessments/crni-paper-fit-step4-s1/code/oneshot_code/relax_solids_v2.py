"""Cr-Ni solid solutions (BCC_A2, FCC_A1 128-atom SQS): staged MLIP relaxation + lattice checks + bcc elastic constants.

Runs inside the Cu-Zr campaign container (cuzr-phaseforge-grace-gpu:20261104) on spark1, /campaign = run root.
PI protocol (memory mlip-relaxation-protocol): stages per cell
  s0 unrelaxed: ideal parent lattice at the Vegard volume of the MLIP same-lattice pure elements (static)
  s1 volume:    isotropic volume only, ions on ideal sites (1-D minimisation of E(V))
  s2 vol+ions:  isotropic volume + ion positions, cell shape fixed  (protocol value)
  s3 full:      cell shape free as well (lower bound; kept even if the lattice changes)
Lattice check after every stage. Nothing is dropped; the CALPHAD value lies in [s3, s0] and s2 is the protocol value.
Elastic constants (bcc, a few compositions): stress-strain at fixed strained cells (+-0.5 %, +-1 %), ions relaxed,
from the s2 structure; cubic averages of C11, C12, C44.
v2 (5 Nov, PI addition): also FCC_ORDERED (L12, L10, D022, Pt2Mo-type) on the fcc parent, same stages and checks;
already computed cells are skipped (result.json present).
Usage: python relax_solids_v2.py MODEL
"""
import os
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'; os.environ['OMP_NUM_THREADS'] = '1'
import sys, json, time, hashlib
from pathlib import Path
import numpy as np
import tensorflow as tf
from ase.io import read, write
from ase.optimize import FIRE, BFGS
from ase.filters import FrechetCellFilter
from ase.neighborlist import neighbor_list
from scipy.optimize import minimize_scalar
from materialsframework.calculators.grace import GraceCalculator

MODEL = sys.argv[1]
R = Path('/campaign')
S = R / 'inputs/structures'
OUT = R / 'runs/solids' / MODEL
FMAX, MAXSTEP = 0.005, 3000
EV_A3_GPA = 160.21766208
for g in tf.config.list_physical_devices('GPU'):
    tf.config.experimental.set_memory_growth(g, True)
if not tf.config.list_physical_devices('GPU'):
    raise RuntimeError('NoGPU')
calc = GraceCalculator(model=MODEL).calculator
if hasattr(calc, 'disable_uq'):
    calc.disable_uq()


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, o):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    t = p.with_suffix(p.suffix + '.tmp'); t.write_text(json.dumps(o, indent=1)); t.replace(p)


def nn_dist(lat, v):
    return ((2 * v) ** (1 / 3) * np.sqrt(3) / 2) if lat == 'BCC_A2' else ((4 * v) ** (1 / 3) / np.sqrt(2))


def lattice_check(lat, atoms, frac0, cell_ref=None):
    """Displacements from ideal sites (affine in the current cell), coordination, and (if cell_ref) shape strain."""
    n = len(atoms); v = atoms.get_volume() / n; d1 = nn_dist(lat, v)
    ideal = frac0 @ atoms.cell.array
    d = atoms.positions - ideal
    fr = d @ np.linalg.inv(atoms.cell.array); fr -= np.round(fr); d = fr @ atoms.cell.array
    d -= d.mean(0)
    u = np.linalg.norm(d, axis=1) / d1
    if lat == 'BCC_A2':
        a = d1 * 2 / np.sqrt(3); rc, want = 0.5 * (a + np.sqrt(2) * a), 14   # 1st + 2nd shells
    else:
        rc, want = 0.5 * (d1 + np.sqrt(2) * d1), 12
    i = neighbor_list('i', atoms, rc)
    cn = np.bincount(i, minlength=n)
    out = {'nn_distance_A': d1, 'disp_rms_over_d1': float(np.sqrt((u ** 2).mean())), 'disp_max_over_d1': float(u.max()),
           'coordination_cut_A': rc, 'coordination_expected': want, 'coordination_fraction_ok': float((cn == want).mean())}
    ok = out['disp_rms_over_d1'] < 0.08 and out['disp_max_over_d1'] < 0.25 and out['coordination_fraction_ok'] >= 0.95
    if cell_ref is not None:
        F = np.linalg.solve(cell_ref, atoms.cell.array)   # rows: new = ref @ F
        E = 0.5 * (F @ F.T - np.eye(3))
        dev = E - np.trace(E) / 3 * np.eye(3)
        out['shape_strain_dev_norm'] = float(np.linalg.norm(dev)); out['strain_from_s2'] = E.tolist()
        ok = ok and out['shape_strain_dev_norm'] < 0.02
    out['lattice_kept'] = bool(ok)
    return out


def stage_record(atoms, extra=None):
    n = len(atoms)
    r = {'energy_eV_atom': float(atoms.get_potential_energy() / n), 'volume_A3_atom': float(atoms.get_volume() / n),
         'max_force_eV_A': float(np.abs(atoms.get_forces()).max()),
         'stress_GPa_voigt': (atoms.get_stress() * EV_A3_GPA).tolist(), 'cell_A': atoms.cell.array.tolist()}
    if extra:
        r.update(extra)
    return r


def scale_to(atoms, v):
    a = atoms.copy(); a.set_cell(atoms.cell * (v / (atoms.get_volume() / len(atoms))) ** (1 / 3), scale_atoms=True); a.calc = calc
    return a


def vol_only(atoms):
    v0 = atoms.get_volume() / len(atoms)
    f = lambda s: scale_to(atoms, v0 * s).get_potential_energy()
    r = minimize_scalar(f, bounds=(0.85, 1.15), method='bounded', options={'xatol': 1e-5})
    return scale_to(atoms, v0 * r.x), int(r.nfev)


def relax(atoms, hydro, logfile, traj):
    filt = FrechetCellFilter(atoms, hydrostatic_strain=hydro)
    opt = FIRE(filt, logfile=str(logfile), trajectory=str(traj))
    conv = opt.run(fmax=FMAX, steps=MAXSTEP)
    return bool(conv), int(opt.nsteps)


def run_cell(lat, d, vegard_v=None):
    name = d.name; od = OUT / lat / name; od.mkdir(parents=True, exist_ok=True)
    res_p = od / 'result.json'
    if res_p.exists():
        return json.loads(res_p.read_text())
    a = read(d / 'POSCAR'); a.calc = calc
    frac0 = a.get_scaled_positions(wrap=False)
    n = len(a); xni = float(np.mean(np.array(a.get_chemical_symbols()) == 'Ni'))
    res = {'lattice': lat, 'cell': name, 'x_Ni': xni, 'n_atoms': n, 'model': MODEL, 'input_sha256': sha(d / 'POSCAR'),
           'runner_sha256': sha(__file__), 'fmax_eV_A': FMAX, 'optimizer': 'FIRE + ase FrechetCellFilter', 'stages': {},
           'started_unix': time.time(), 'failures': []}
    try:
        # s0
        if vegard_v is not None:
            a = scale_to(a, (1 - xni) * vegard_v['Cr'] + xni * vegard_v['Ni'])
        res['stages']['s0_unrelaxed'] = stage_record(a, {'lattice_check': lattice_check(lat, a, frac0)})
        # s1
        a1, nfev = vol_only(a)
        res['stages']['s1_volume'] = stage_record(a1, {'nfev': nfev, 'lattice_check': lattice_check(lat, a1, frac0)})
        write(od / 'CONTCAR_s1', a1, format='vasp', direct=True)
        # s2
        a2 = a1.copy(); a2.calc = calc
        conv, ns = relax(a2, True, od / 's2.log', od / 's2.traj')
        res['stages']['s2_volume_ions'] = stage_record(a2, {'converged': conv, 'steps': ns,
                                                            'lattice_check': lattice_check(lat, a2, frac0)})
        if not conv:
            res['failures'].append('s2 not converged in %d steps' % MAXSTEP)
        write(od / 'CONTCAR_s2', a2, format='vasp', direct=True)
        # s3
        a3 = a2.copy(); a3.calc = calc
        conv, ns = relax(a3, False, od / 's3.log', od / 's3.traj')
        res['stages']['s3_full'] = stage_record(a3, {'converged': conv, 'steps': ns,
                                                     'lattice_check': lattice_check(lat, a3, frac0, a2.cell.array)})
        if not conv:
            res['failures'].append('s3 not converged in %d steps' % MAXSTEP)
        write(od / 'CONTCAR_s3', a3, format='vasp', direct=True)
        res['status'] = 'computed'
    except Exception as e:  # a failed cell is listed, never a gate
        res['status'] = 'failed'; res['failures'].append(repr(e))
    res['finished_unix'] = time.time()
    save(res_p, res)
    print(lat, name, res['status'], {k: round(v['energy_eV_atom'], 5) for k, v in res['stages'].items()}, flush=True)
    return res


def elastic(lat, name):
    od = OUT / lat / name; p = od / 'elastic.json'
    if p.exists() or not (od / 'CONTCAR_s2').exists():
        return
    a0 = read(od / 'CONTCAR_s2'); a0.calc = calc
    s0 = a0.get_stress(voigt=True)
    rows = []
    C = np.zeros((6, 6))
    for k in range(6):
        sl = []
        for e in (-0.01, -0.005, 0.005, 0.01):
            eps = np.zeros((3, 3))
            if k < 3:
                eps[k, k] = e
            else:
                i, j = [(1, 2), (0, 2), (0, 1)][k - 3]; eps[i, j] = eps[j, i] = e / 2   # engineering shear e
            a = a0.copy(); a.calc = calc
            a.set_cell(a0.cell.array @ (np.eye(3) + eps), scale_atoms=True)
            opt = FIRE(a, logfile=None); conv = opt.run(fmax=FMAX, steps=MAXSTEP)
            s = a.get_stress(voigt=True) - s0
            sl.append((e, s)); rows.append({'component': k, 'strain': e, 'converged': bool(conv), 'stress_GPa': (s * EV_A3_GPA).tolist()})
        es = np.array([q[0] for q in sl]); ss = np.array([q[1] for q in sl])
        C[:, k] = np.polyfit(es, ss, 1)[0] * EV_A3_GPA
    C = 0.5 * (C + C.T)
    c11 = float(np.mean([C[0, 0], C[1, 1], C[2, 2]])); c12 = float(np.mean([C[0, 1], C[0, 2], C[1, 2]]))
    c44 = float(np.mean([C[3, 3], C[4, 4], C[5, 5]]))
    save(p, {'lattice': lat, 'cell': name, 'model': MODEL, 'C_GPa_voigt': C.tolist(), 'C11_GPa': c11, 'C12_GPa': c12, 'C44_GPa': c44,
             'C11_spread_GPa': float(np.ptp([C[0, 0], C[1, 1], C[2, 2]])), 'C44_spread_GPa': float(np.ptp([C[3, 3], C[4, 4], C[5, 5]])),
             'method': 'stress-strain, strains +-0.5 %, +-1 % (engineering shear), ions relaxed (FIRE fmax 0.005) at fixed strained cell, '
                       'reference = s2 structure (residual stress subtracted); cubic averages', 'rows': rows,
             'temperature': '0 K static', 'finished_unix': time.time()})
    print('elastic', lat, name, round(c11, 1), round(c12, 1), round(c44, 1), flush=True)


if __name__ == '__main__':
    t0 = time.time()
    summary = {'model': MODEL, 'started_unix': t0}
    vv_fcc = {}
    for lat in ('BCC_A2', 'FCC_A1', 'FCC_ORDERED'):
        dirs = sorted((S / lat).glob('x*'))
        if lat == 'FCC_ORDERED':   # ordered fcc superstructures: Vegard start from the FCC_A1 pure-element volumes
            for d in dirs:
                run_cell(lat, d, vv_fcc)
            continue
        pure = [d for d in dirs if d.name.endswith('_pure')]
        vv = {}
        for d in pure:
            r = run_cell(lat, d)
            vv['Ni' if r['x_Ni'] > 0.5 else 'Cr'] = r['stages']['s2_volume_ions']['volume_A3_atom']
        summary[lat + '_pure_volumes_A3_atom'] = vv
        if lat == 'FCC_A1':
            vv_fcc = vv
        for d in dirs:
            if d not in pure:
                run_cell(lat, d, vv)
    for name in ('x0.0000_pure', 'x0.1250_s2026110501', 'x0.2500_s2026110501', 'x0.5000_s2026110501'):
        try:
            elastic('BCC_A2', name)
        except Exception as e:
            print('elastic failed', name, repr(e), flush=True)
    summary['finished_unix'] = time.time(); summary['elapsed_s'] = time.time() - t0
    save(OUT / 'summary.json', summary)
    print('DONE', summary['elapsed_s'], flush=True)
