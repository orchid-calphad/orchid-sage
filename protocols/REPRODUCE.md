# Reproducing the Cu–Zr and Cr–Ni picks

> **Public copy (7 Nov 2026).** The public repository holds the ORCHID-SAGE standard and the Cr–Ni assessment only. The Cu–Zr draft assessment named below (its specific protocol, run cards, evidence and reruns) is kept in the private record and is not part of the public copy; the final Cr–Ni protocol is `crni-paper-fit-step4c-b@1.0.4` (approved), and the status paragraph below is the one of 6 Nov.

Status on 6 Nov 2026: both specific protocols are still **drafts**. Reruns under the PI decisions of 6 Nov are in progress (Cu–Zr run 2 and the Cr–Ni step-4 ZPF-σ tests), and each specific protocol will be versioned when its rerun ends. This file explains how to reproduce the **current** picks from the repository alone, and records what has been reproduced so far.

## One command

```sh
python3 protocols/tools/orchid_reproduce.py protocols/specific/<artifact>@<version>.yaml \
    --root <fresh empty dir> --python <interpreter matching the lock> \
    --pfp <PhaseForgePlus src at c66656f> --nproc 4 --report <report.json>
```

The tool works in four stages:
1. **Stage.** It copies the code snapshot (`assessments/<artifact>/code/`) and the evidence bundle (`assessments/<artifact>/evidence/`) into the fresh root, checking every file against the bundle manifests by sha256.
2. **Check the environment.** It verifies the interpreter: espei 0.8.11.dev82+g9039ea215 and pycalphad 0.11.3.dev35+g9a6939dd2, as locked in `environment/`.
3. **Run.** It runs `reproduce.plan` of the specific protocol in order.
4. **Compare and report.** It compares the results and writes a JSON and a Markdown report:
   - deterministic outputs must be byte-identical;
   - refitted TDBs must agree parameter by parameter within declared absolute tolerances (`tdb_abs`);
   - objectives and diagram quantities must agree within declared absolute tolerances (`json_tol`).

It needs only the standard library. It never overwrites an existing root and never touches the campaign directories.

## Requirements

| item | where | pinned |
|---|---|---|
| fitting interpreter | the ESPEI (gradient PR, commit 9039ea2) + pycalphad environment of the lock file, named `fit_python` in `local/config.json` (the Mac Studio and the DGX Spark spark1 each had one) | `environment/espei-pr268.lock.txt`; `environment/pins/` |
| hinge code | PhaseForgePlus `src/` at c66656f (private; public commit 2da1d69 has the identical tree, `environment/pins/phaseforgeplus_equivalence.json`) | `environment/pins/spark1_phaseforgeplus_files.sha256` |
| MLIP stage (only to redo the one-shot) | image `cuzr-phaseforge-grace-gpu:20261104` (id `sha256:ac223e2cfa3e…`; archived as a tar.gz on the DGX Spark spark1, sha256 `74e140ed…`; recipe = the recorded Dockerfile) and the GRACE weights from Hugging Face (tags in `environment/pins/PINS.md`) | `environment/pins/PINS.md` |
| evidence | `assessments/<artifact>/evidence/` (bundle sha256 in `MANIFEST@2.0.0.json`; version 1 `MANIFEST.json` kept) | in the repo |
| code | `assessments/<artifact>/code/` (commit 94cc153 + later additions) | in the repo |

## What has been reproduced

| check | where | result | report |
|---|---|---|---|
| deterministic rebuilds: Cr–Ni one-shot TDBs (fixed date), Cr–Ni step-1 base, Cu–Zr pick evaluation, per-state evaluation, evidence bundles, TDB headers | Studio and spark1 | byte-identical | `reproduce/crni-paper-fit-step4-s1-studio-F2/comparison.md` |
| optimizer, same machine: Cr–Ni step 2, start s0 | Studio | bit-identical (logpost, θ, nfev) | same |
| Cu–Zr step 2 s1, H1 s1, H2 s7 (one recorded start per lineage step, recorded seeds) | spark1 CPU (the machine of run 1) | **byte-identical** lnL and TDB for all three (artifact sha256 9a39b415…); attempt 1 failed on a bundle bug (11 calorimetric files missing), fixed in bundle 1.1.0; a different-machine Cu–Zr rerun is still pending | `reproduce/cuzr-oneshot-h2-s7-spark1/` |
| Cr–Ni step 2 → 3b → 4 (all starts, ranking, pick), independent machine | spark1 CPU (Arm Linux; the original ran on the Studio, macOS M1) | **artifact reproduced**: step 4 logpost within 3×10⁻⁹, parameters within 0.2 % of tolerance, eutectic and CrNi2 top identical; step 2 within tolerance; **step 3b intermediate pick not reproduced** (flat mode, loose convergence, a different start picked; Q36) | `reproduce/crni-paper-fit-step4-s1-spark1/` |
| MLIP spot-check: 3 bcc and 1 fcc SQS, 4 pure-element cells, all 4 relaxation stages | spark2 GPU, an independent build of the same Dockerfile (image id 8eae0b91…, identical pip freeze) against the spark1 originals | 32/32 within 0.1 kJ/mol-atom (largest difference 4×10⁻⁴ kJ/mol-atom); lattice verdicts identical | `reproduce/crni-mlip-spotcheck/comparison.md` |

## Tolerances (declared, from the observed spread)

| quantity | tolerance | observed spread | where seen |
|---|---|---|---|
| deterministic files | byte-identical | 0 | F checks |
| objective (log posterior or lnL) of a refitted start, another machine | 0.01 | 4×10⁻⁷ | Cr–Ni step 2 on spark1 |
| fitted parameters, another machine | 50 J/mol on a-terms and 0.03 J/mol/K on b-terms (Cr–Ni); 0.05 kJ and 0.03 J/K (Cu–Zr) | up to 17 J/mol on a soft a-term (fcc L1), 0.007 J/K on b-terms | Cr–Ni step 2 on spark1 |
| diagram quantities (eutectic, CrNi2 top, 13 Cu–Zr invariants) | 2 K | see the reports | — |
| MLIP energies, another GPU host and image build | 0.1 kJ/mol-atom per cell and stage | 4×10⁻⁴ kJ/mol-atom | spark2 spot-check |

Relative tolerances on single parameters are not used (fit_protocol 10b). Soft directions of the objective move by physically negligible absolute amounts but by large relative ones (OPEN_QUESTIONS Q34).

## What still cannot be reproduced byte for byte, and why

- **MLIP relaxations and MD on a GPU.** Results agree within the tolerance, not bitwise. TensorFlow GPU reductions are not deterministic and no determinism flags were set. The spark2 spot-check shows a spread of 4×10⁻⁴ kJ/mol-atom.
- **Liquid MD.** It was not rerun here. The Cu–Zr run-1 pick uses the reused GRACE-2L-OMAT liquid of `cuzr-fresh-phaseforge-20261104`, which is hashed but not regenerated (a 10 h run).
- **Refits on a different CPU architecture.** They agree within the tolerances above, not bitwise: the same mode is reached, but soft parameters differ in the last digits.
- **The code of the Cr–Ni step-4 fit.** It is not the byte-identical code that ran. `fit.py` and `model.py` were edited in place at 06:55 (trajectory recording), after the fit. The Studio rerun of a step-2 start is bit-identical, and the spark1 rerun of the whole sequence passes the tolerances, so the edit did not change the optimisation (OPEN_QUESTIONS Q35).
- **Restricted sources.** The Braga PDF and the private Cr–Ni exports are hashed only, never redistributed. The evidence bundles carry the derived facts, so a rerun does not need them. They are needed only to rebuild the bundles from the sources.
- **Cr–Ni set E and the 29 unregistered ORC ids.** They become citable by release only after the v2027.01 intake has been delivered (prepared in `assessments/<artifact>/intake/`).

## Expected results and the pick rule (6 Nov 2026)

- **Expected results.** Plan items say what result to expect (`expected: pass | fail | partial`, with a reason).
  `orchid_reproduce.py` marks a declared failure `FAIL (expected)` and does not fail the run for it, provided the command
  itself ran. Any other failure is listed under `unexpected_failures`.
- **The pick rule (fit_protocol 10a).**
  - A start is eligible only when its gradient norm, in the optimiser scaling, is below the threshold stated in the plan
    before fitting (default 1e-3).
  - Among eligible starts the order is: plausible, then the topology class, then the objective. Grid quantities never
    break a tie.
  - The tool is `python3 tools/pick_start.py steps/<step> --threshold 1e-3`. If nothing is eligible it writes
    `pick: null` and says so; the threshold is never loosened.
- **Acceptance checks without a fit.** `phase_sequence` (0.01 grid, transitions within 10 K), `pure_elements` and
  `laplace_weights` (Cr–Ni).
- **PhaseForge+ source.** `--pfp` is hash-checked against `environment/pins/spark1_phaseforgeplus_files.sha256` before
  anything runs.
