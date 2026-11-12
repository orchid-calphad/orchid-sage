# Independent scripted rerun of crni-paper-fit-step4c-b@1.0.3 (draft) on spark1 (7 Nov 2026), and the Q40 fix proof

**Overall tool verdict: PASS.** Every prediction is within its tolerance and every data-identity check is byte-identical. The
10a re-evaluation now equals the multistart value at all 8 starts (difference 0.0), and every worker held all 12 `zpf_susp`
records. The multistart run with `fit3.py`/`model3.py` is bit-identical to the 1.0.2 rerun (`fit2.py`/`model2.py`) on the same
machine: θ, objective and number of evaluations are equal at all 8 starts, and `evaluation.json` is byte-identical. The environment
and PhaseForge+ source checks match. Under the PI's ruling of 6 Nov these are notes.

## What 1.0.3 changes (Q40)

Cause of Q40 (`../crni-paper-fit-step4c-b-1.0.2-spark1/q40/README.md`): `model2.no_crni2_tdb` truncated and rewrote the shared file
`data/cache/step3b_thermo_crni2free_pick_noCRNI2.tdb` while the spawned workers read it. One empty read therefore dropped the
12 `zpf_susp` records from one worker's objective without any error. 1.0.3 runs new versions of the scripts. The frozen versions are
unchanged (`assessments/crni-paper-fit-step4c-b/addendum-1.0.3/code/`; originals in `<home>/ScientificRuns/crni-paper-fit-20261106/scripts/`):

- `model3.py` builds the no-CRNI2 database in memory (`Database.from_string` of the same text), so nothing is written to a shared
  file. `GradTarget` raises `DataLossError` in two cases: the no-CRNI2 database does not hold exactly the start phases minus CRNI2,
  or a category loses a ZPF record, a fixed-configuration point or an activity dataset.
- In `check10a_ms2.py`, a re-evaluation that differs from the multistart value by more than 1e-6 is a **failure of the check**:
  the script exits 3, gives no pick, and `check_ok` is false. Each row records its per-category record counts.
- `fit3.py`, `laplace3.py` and `run_global_crni2.py` are the old scripts with model3 in place of model2. Nothing else changes.
- The protocol now instantiates `orchid-calphad-fit@2.1.2`, whose UQ step `modes` separates modes by parameters in units of the
  10b tolerances (coordinator, 7 Nov; see below). No plan item depends on this step.

## Fix proof (`fix_proof/`)

| test | Studio (mac-studio) | spark1 |
|---|---|---|
| model2 vs model3, one process each (no race possible), all 8 endpoints of the 1.0.2 rerun multistart: value, analytic gradient, `value_only`, every part, as `float.hex` (`prove_identity.py`, `compare_identity.py`) | **bit-identical at 8 of 8** (s1 −5657.288636863667, s2 −5657.288636867111, s4 −5657.293148832630) | **bit-identical at 8 of 8** (s1 −5657.288636863667, s2 −5657.288636867119, s4 −5657.293148832628); re-evaluation − multistart file = 0.0 at all 8 |
| race probe, 4 spawned processes × 1000 builds of the no-CRNI2 database (`probe_race_fixed.py`) | model3: 0 of 4000 bad (empty, partial or parse error) | model3: 0 of 4000 bad |
| the same probe while 2 model2 writers truncate the shared file (`MIX`) | model3: 0 of 2000 bad; model2: 26 of 2000 bad (positive control) | model3: 0 of 2000 bad; model2: 2 of 2000 bad |
| fail closed (`probe_guard.py`): normal build / Q40 defect injected (empty no-CRNI2 text) / one zpf_susp record dropped | 12 records, 3 phases / DataLossError / DataLossError | same |
| `check10a_ms2.py` with the s3 multistart value shifted by 1e-5 (4 workers) | – | exit 3, `check_ok` false, pick null, mismatch s3 −1.0e-5; 12 zpf_susp records in all 8 workers |
| 2.1.2 modes command, run verbatim from the YAML on the recorded multistart (`modes_check.py`) | 2 modes, s4 and s5, θ bit-identical to `modes_step4c_b.json` in order (labels `A_s4_perturbed`/`B_s5_perturbed`, recorded `A_s4`/`A2_s5_flat`); the 2.1.1 command gives 1 mode | – |

The cross-machine difference between the Studio values and the spark1 file is at most 1.1e-11. The tolerance of 1e-6 lies far above
this and far below the Q40 effect (139.6).

## How it was run

The run used a fresh root, staged from a `git archive` copy of orchid-sage at 379ebe6 (1.0.3 as first drafted; spec sha256
ef59106a…):

`python3 protocols/tools/orchid_reproduce.py protocols/specific/crni-paper-fit-step4c-b@1.0.3.yaml --root <home>/orchid-protocols-work-20261106/rerun-crni4cb-1.0.3 --python <home>/orchid-crni-mcmc-20261105/env/grad/bin/python --pfp <home>/orchid-crni-mcmc-20261105/src/PhaseForgePlus/src --nproc 4 --report <home>/orchid-protocols-work-20261106/rerun-crni4cb-1.0.3_report.json`

- **Timing.** 11:54–14:00 CST (2 h 06 min). Per item: step4c_b 1561 s, check10a 975 s, global_10c 4464 s, laplace 527 s.
- **Load.** spark1 load average was 0.1 at the start. A 10a test of my own (4 workers, `q40fix/`) ran alongside it until 12:07. No
  other job was touched.
- **Exact PIDs started.** Under the ssh wrapper bash 2052102: bash 2052108 and orchid_reproduce 2052109. All have ended (EXIT 0).
- **Spec versions.** After the launch, 1.0.3 was moved to `orchid-calphad-fit@2.1.2`. That change added the `mode_tolerances`
  override and replaced one decision row; no command, code pin or plan item changed (330c9e2, 7a0d54c). The final report was then
  written with `--compare-only` in the same root, from a copy at 7a0d54c (spec sha256 ee75514c…), as was done for 1.0.1 and 1.0.2.

**Report files.**
- `reproduce_report.{json,md}`: the final report, from the spec at 7a0d54c.
- `reproduce_report_run.*`: the report of the run itself, from the spec at 379ebe6. It is also PASS, with the same values.

## Per item (reference = the recorded Studio pick s4, mode A)

| item | quantity | reference | rerun (spark1) | tolerance | result |
|---|---|---|---|---|---|
| stage | code and evidence files (manifests incl. addendum-1.0.3) | manifests | sha256 equal | byte | PASS |
| step4c_b | multistart (fit3/model3) + evaluate.py | – | 8 of 8 converged; θ, logpost and nfev bit-identical to the 1.0.2 rerun at all 8 starts; `evaluation.json` byte-identical | – | ran (judged at the 10a pick) |
| check10a | re-evaluation vs multistart file | – | 0.0 at 8 of 8; `check_ok` true; 12 zpf_susp records in every worker | 1e-6 (failure of the check) | – |
| check10a | 10a pick by the rule | s4_perturbed (Studio) | **s1_perturbed**: 8 of 8 smooth and eligible; gap to runner-up 3.5e-9 (as in the 1.0.1 rerun) | label is a note | – |
| check10a | objective of the 10a pick | −5657.288636859774 | −5657.288636863667 (Δ 3.9e-9) | 0.01 | PASS |
| check10a | pick eligible under 10a | true | true (smooth, \|g\| 2.3e-4) | – | PASS |
| check10a | eutectic (T_liquid_min) | 1614 K | 1614 K | 2 K | PASS |
| check10a | CrNi2 top | 860 K | 860 K | 2 K | PASS |
| global_10c | basin hopping best from the 10a pick (seed 7201, 1500 evaluations, 4461 s) | −5657.288636859766 | −5657.288636863626 | 0.01 | PASS (no better optimum) |
| global_10c | dual annealing best (1500 evaluations, 4263 s, run in parallel with basin hopping) | −5657.288636859768 | −5657.288636863596 | 0.01 | PASS (no better optimum) |
| evaluate_states | `states_evaluated@1.1.0.json` (695 states, 424 match) | e24d0853… | e24d0853… | byte | PASS |
| phase_sequence | phase order on heating, 0.01 grid, 600–2200 K, at the 10a pick | recorded pick | identical | labels identical, 10 K | PASS |
| pure_elements | unary limits; Cr, Ni stable phases below T_m | true; BCC_A2; FCC_A1 | true; BCC_A2; FCC_A1 | exact | PASS |
| thermochemistry | 22 data/thermo datasets, rms residual/σ at the 10a pick | `per_dataset_step4c_b_hingefloor.json` | 22 of 22 present, same n, max \|Δ rms_z\| 4.9e-6 | 0.1 | PASS |
| laplace_weights (laplace3/model3) | main-mode weight | 0.7660570156 | 0.7660570169 (identical to the 1.0.2 rerun) | 0.01 | PASS* |

\* This item uses the recorded `modes_step4c_b.json`, so it tests the Hessian and mixture code, not the mode finding.

## Notes (never failures)

- **Parameters (10b, `rerun/pick10a_rerun.json`).** The determined symbols are within the tolerance. The nine symbols in the flat
  A/A2 directions are undetermined, and the other TDB lines are identical.
- **Start label.** The 10a pick is s1 here (as in the 1.0.1 rerun), s2 in the 1.0.2 rerun (where s1 was hit by Q40) and s4 on the
  Studio, all in mode A. With the fix, s1, the best eligible start of this multistart, is picked again.
- `pick10a.py` (unchanged, 1.0.1 addendum) still names `check10a_ms.py` in its `rule` text, although it read the
  `check10a_ms2.py` output.
- **Environment.** espei 0.8.11.dev82+g9039ea215 and pycalphad 0.11.3.dev35+g9a6939dd2 match. All 10 files of the PhaseForge+
  source pin match.

## Files

- `fix_proof/` holds the proof scripts and their outputs for the Studio and spark1.
- `rerun/` holds:
  - the 10a check and pick summary, `multistart.json`, `evaluation.json` and the 10a pick TDB;
  - the 10c status files;
  - the physics, per-dataset and thermochemistry comparisons;
  - the Laplace output, the phase sequences and `reproduce_logs/`.
- The full run root stays on spark1 at `<home>/orchid-protocols-work-20261106/rerun-crni4cb-1.0.3`. The proof roots are at
  `<home>/orchid-protocols-work-20261106/q40fix/` and, on the Studio, in the agent scratchpad.
