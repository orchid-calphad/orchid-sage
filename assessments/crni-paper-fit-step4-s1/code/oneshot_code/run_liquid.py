"""Cr-Ni liquid MD (adapted from the Cu-Zr campaign code/run_liquid_matrix.py, same integrators and sampling).

Same as Cu-Zr: 108-atom fcc-SQS start (864 = 2x2x2 repeat), premelt 2 ps at 3500 K (NHC NVT), isotropic MTK NPT at
1 atm, NHC NVT equilibration 5 ps, NHC NVT production 100 ps, 1 fs timestep, tdamp 100 fs, pdamp 1000 fs, velocities
every 2 fs, positions every 10 fs (unwrapped), thermo every 1000 steps.
Changes and why:
  * density stage 10 ps (Cu-Zr 5 ps) and the NVT volume set to the mean NPT volume of its last 5 ps (Cu-Zr: the
    instantaneous final NPT volume); removes a ~1 % volume-fluctuation offset from the enthalpy at small cost.
  * potential energy, kinetic energy, pressure and volume recorded every 10 fs in production (H = <U+K> + pV).
  * potential passed as an argument (GRACE-2L-SMAX-OMAT-large: PI default since 31 Oct 2026).
"""
import os
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'; os.environ['OMP_NUM_THREADS'] = '1'
import argparse, time, json, hashlib
from pathlib import Path
import numpy as np
import tensorflow as tf
from ase import units
from ase.io import read, write
from ase.md.velocitydistribution import MaxwellBoltzmannDistribution, Stationary
from ase.md.nose_hoover_chain import NoseHooverChainNVT, IsotropicMTKNPT
from materialsframework.calculators.grace import GraceCalculator

p = argparse.ArgumentParser()
p.add_argument('--size', type=int, choices=[108, 864], required=True)
p.add_argument('--temperature', type=float, required=True)
p.add_argument('--seed', type=int, required=True)
p.add_argument('--x-ni', type=float, required=True)
p.add_argument('--model', default='GRACE-2L-SMAX-OMAT-large')
p.add_argument('--production-ps', type=float, default=100.0)
a = p.parse_args()
R = Path('/campaign')
out = R / 'runs/liquid' / a.model / f'Cr{100*(1-a.x_ni):g}Ni{100*a.x_ni:g}_N{a.size}_T{a.temperature:g}'
out.mkdir(parents=True, exist_ok=True)


def save(path, obj):
    path = Path(path); t = path.with_suffix(path.suffix + '.tmp'); t.write_text(json.dumps(obj, indent=2)); t.replace(path)


def sha(q):
    return hashlib.sha256(Path(q).read_bytes()).hexdigest()


if (out / 'run.json').exists():
    raise RuntimeError('refuses preexisting run')
gpus = tf.config.list_physical_devices('GPU')
if not gpus:
    raise RuntimeError('NoGPU')
for g in gpus:
    tf.config.experimental.set_memory_growth(g, True)
source = next(q for q in (R / 'inputs/structures/LIQUID').glob('*/POSCAR')
              if abs(float(np.mean(read(q).numbers == 28)) - a.x_ni) < 1e-8)
atoms = read(source)
if a.size == 864:
    atoms = atoms.repeat((2, 2, 2))
assert len(atoms) == a.size
calc = GraceCalculator(model=a.model).calculator
if hasattr(calc, 'disable_uq'):
    calc.disable_uq()
atoms.calc = calc
MaxwellBoltzmannDistribution(atoms, temperature_K=3500, rng=np.random.default_rng(a.seed)); Stationary(atoms)
NPROD = int(round(a.production_ps * 1000))
stages = [('premelt', 3500, 2000), ('density', a.temperature, 10000), ('equilibrate', a.temperature, 5000), ('production', a.temperature, NPROD)]
settings = {'input': str(source.relative_to(R)), 'input_sha256': sha(source), 'size': a.size, 'target_T_K': a.temperature,
            'pressure_Pa': 101325, 'timestep_fs': 1., 'seed': a.seed, 'stages': {s: n for s, _, n in stages},
            'thermostat': 'NoseHooverChainNVT (ase)', 'barostat': 'IsotropicMTKNPT (ase), density stage only',
            'thermostat_damping_fs': 100, 'barostat_damping_fs': 1000, 'velocity_interval_fs': 2, 'position_interval_fs': 10,
            'nvt_volume': 'mean NPT volume over the last 5 ps of the density stage', 'model': a.model,
            'runner_sha256': sha(__file__), 'fit_ready': False, 'started_unix': time.time(), 'x_Ni': a.x_ni,
            'cell_size_acceptance': '108 provisional until the 108 vs 864 vibrational-entropy check (<5 %) passes'}
save(out / 'run.json', settings); start = time.time()
vols = []
for stage, T, steps in stages:
    kw = {'timestep': 1 * units.fs, 'temperature_K': T, 'tdamp': 100 * units.fs}
    dyn = IsotropicMTKNPT(atoms, pressure_au=1.01325 * units.bar, pdamp=1000 * units.fs, **kw) if stage == 'density' else NoseHooverChainNVT(atoms, **kw)
    if stage == 'density':
        dyn.attach(lambda: vols.append(atoms.get_volume()) if dyn.nsteps > 5000 else None, interval=10)
    if stage == 'production':
        nv, npos = NPROD // 2, NPROD // 10
        vel = np.lib.format.open_memmap(out / 'velocities_ase.npy', mode='w+', dtype='float32', shape=(nv, len(atoms), 3))
        pos = np.lib.format.open_memmap(out / 'positions_A.npy', mode='w+', dtype='float32', shape=(npos, len(atoms), 3))
        th = np.lib.format.open_memmap(out / 'thermo_10fs.npy', mode='w+', dtype='float64', shape=(npos, 4))  # Epot, Ekin (eV/cell), P (eV/A3), V (A3)
        iv = [0]; ip = [0]
        np.save(out / 'cell_A.npy', atoms.cell.array); np.save(out / 'masses_amu.npy', atoms.get_masses())
        np.save(out / 'symbols.npy', np.array(atoms.get_chemical_symbols()))

        def record():
            if dyn.nsteps == 0:
                return
            if dyn.nsteps % 2 == 0:
                vel[iv[0]] = atoms.get_velocities(); iv[0] += 1
            if dyn.nsteps % 10 == 0:
                pos[ip[0]] = atoms.positions
                th[ip[0]] = (atoms.get_potential_energy(), atoms.get_kinetic_energy(),
                             -np.trace(atoms.get_stress(voigt=False, include_ideal_gas=True)) / 3, atoms.get_volume())
                ip[0] += 1
        dyn.attach(record, interval=1)

    def update():
        rec = {'stage': stage, 'steps': dyn.nsteps, 'planned_steps': steps, 'elapsed_s': time.time() - start,
               'temperature_K': atoms.get_temperature(), 'energy_eV_atom': atoms.get_total_energy() / len(atoms),
               'epot_eV_atom': atoms.get_potential_energy() / len(atoms),
               'volume_A3_atom': atoms.get_volume() / len(atoms), 'updated_unix': time.time(), 'fit_ready': False}
        if not np.isfinite([rec['temperature_K'], rec['energy_eV_atom'], rec['volume_A3_atom']]).all():
            raise RuntimeError('Nonfinite MD')
        save(out / 'progress.json', rec)
        with (out / 'thermo.jsonl').open('a') as f:
            f.write(json.dumps(rec) + '\n')
    dyn.attach(update, interval=1000); print('START', stage, steps, flush=True); dyn.run(steps)
    write(out / f'{stage}.final.traj', atoms)
    extra = {}
    if stage == 'density':
        vm = float(np.mean(vols)); extra = {'npt_mean_volume_A3_atom_last5ps': vm / len(atoms), 'npt_volume_std_A3_atom': float(np.std(vols)) / len(atoms),
                                            'final_volume_A3_atom': atoms.get_volume() / len(atoms)}
        atoms.set_cell(atoms.cell * (vm / atoms.get_volume()) ** (1 / 3), scale_atoms=True)
    save(out / f'{stage}.complete.json', {'steps': dyn.nsteps, 'finished_unix': time.time(), **extra,
                                          'restart_policy': 'stage boundary only; no claim of thermostat-state restart'})
    if stage == 'production':
        vel.flush(); pos.flush(); th.flush(); assert iv[0] == nv and ip[0] == npos
    print('END', stage, flush=True)
save(out / 'result.json', {'status': 'computed', 'fit_ready': False, 'n_atoms': len(atoms), 'temperature_K': a.temperature,
                           'production_ps': a.production_ps, 'elapsed_s': time.time() - start, 'finished_unix': time.time(),
                           'pending': ['liquid-state checks (MSD, RDF)', 'finite-size comparison', 'entropy analysis']})
