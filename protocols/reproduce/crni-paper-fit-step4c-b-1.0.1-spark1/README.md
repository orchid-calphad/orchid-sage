# Independent scripted rerun of crni-paper-fit-step4c-b@1.0.1 on spark1 (6–7 Nov 2026)

**Overall tool verdict: PASS.** Every prediction is within its tolerance, and every data-identity check is byte-identical. The environment check and the PhaseForge+ source check also match; under the PI's ruling they are notes, not part of the verdict.

## How it was run

The run used a fresh root, from a `git archive` copy of orchid-sage at 6c83ea0:

`python3 protocols/tools/orchid_reproduce.py protocols/specific/crni-paper-fit-step4c-b@1.0.1.yaml --root <home>/orchid-protocols-work-20261106/rerun-crni4cb-1.0.1 --python <home>/orchid-crni-mcmc-20261105/env/grad/bin/python --pfp <home>/orchid-crni-mcmc-20261105/src/PhaseForgePlus/src --nproc 4`

- **Timing.** 22:05–00:51 CST. 408 files were staged by hash.
- **Load.** spark1 had a load of about 11 of 20 cores from other jobs, which were not touched.
- **Exact PIDs started.** bash 4161122 and orchid_reproduce 4161126. Both have ended.

**Spec versions.**
1. The run used the spec of 6c83ea0 (sha256 046e8104…).
2. During the run, the PI ruled on the 1.0.0 verdict ("this is too strict"). Under that ruling, 1.0.1 was amended at 203a9c1 (sha256 11d4ab39…) in three ways:
   - The verdict now comes from predictions only.
   - The 10b parameter comparison is a note.
   - A thermochemistry item was added.
3. No command of the items already run changed. The new item `thermochemistry` was run in the same root with `--no-stage --only thermochemistry` (2.9 s).
4. The final report was then written with `--compare-only`, both from a copy at 203a9c1.

**Report files.**
- `reproduce_report.{json,md}`: the final report.
- `reproduce_report_run.*`: the report of the run itself (6c83ea0 spec; also PASS).
- `reproduce_report_thermochemistry.json`: the report of the thermochemistry item.

## Per item (reference = the recorded Studio pick s4, mode A)

| item | quantity | reference | rerun (spark1) | tolerance | result |
|---|---|---|---|---|---|
| stage | 408 code and evidence files | manifests | sha256 equal | byte | PASS |
| step4c_b | multistart + evaluate.py (2305.6 s) | – | 8 of 8 converged; 5 starts in mode A (s1, s2, s3, s6, s7), 3 in mode A2 (s0, s4, s5) | – | ran (no expectations of its own; judged at the 10a pick) |
| check10a | 10a pick by the rule (1913.0 s) | s4_perturbed (Studio) | **s1_perturbed**: 8 of 8 smooth, 8 eligible, gap to runner-up 3.5e-9 | label is a note | – |
| check10a | objective of the 10a pick | −5657.288636859774 | −5657.288636863667 (Δ 3.9e-9) | 0.01 | PASS |
| check10a | pick eligible under 10a | true | true (smooth) | – | PASS |
| check10a | eutectic (T_liquid_min) | 1614 K | 1614 K | 2 K | PASS |
| check10a | CrNi2 top | 860 K | 860 K | 2 K | PASS |
| global_10c | basin hopping best from the 10a pick (seed 7201, 1500 evaluations) | −5657.288636859766 | −5657.288636863626 | 0.01 | PASS (no better optimum) |
| global_10c | dual annealing best (5170.9 s, both in parallel) | −5657.288636859768 | −5657.288636863596 | 0.01 | PASS (no better optimum) |
| evaluate_states | `states_evaluated@1.0.0.json` (695 states) | b610e5ec… | b610e5ec… | byte | PASS |
| phase_sequence | phase order on heating, 0.01 grid, 600–2200 K, at the 10a pick | recorded pick | 0 compositions differ | labels identical, 10 K | PASS |
| pure_elements | unary limits; Cr, Ni stable phases below T_m (staged Cahn input) | true; BCC_A2; FCC_A1 | true; BCC_A2; FCC_A1 (liquid convex 600–2200 K, bcc spinodal top 1385 K, coherent 1338/1352/1275 K as recorded) | exact | PASS |
| thermochemistry | 22 data/thermo datasets, rms residual/σ at the 10a pick | `per_dataset_step4c_b_hingefloor.json` | 22 of 22 present, same n, max \|Δ rms_z\| 4.9e-6 | 0.1 | PASS |
| laplace_weights | main-mode weight (555.6 s) | 0.7660570156 | 0.7660570169 | 0.01 | PASS* |

\* As in 1.0.0, this item uses the recorded `modes_step4c_b.json`, so it tests the Hessian and mixture code, not the mode finding.

## Notes (never failures)

- **Parameters (10b, `rerun/pick10a_rerun.json`).** The five determined symbols (liquid L0/L1 a,b and CrNi2 a: VV0000–VV0003, VV0012) are within the tolerance: worst |Δ|/tol is 0.020. The nine symbols in the flat A/A2 directions (bcc and fcc L0/L1 a,b and CrNi2 b) are undetermined. Against the recorded mode A_s4 the largest |Δ|/tol is 0.039 over all symbols, and none of the undetermined symbols lies beyond tolerance there. The other TDB lines are identical. The pick TDB is not byte-identical to the recorded one, because it holds a different start of the same mode.
- **Start and mode labels.** The 10a pick is s1 on spark1 and s4 on the Studio. Both are in mode A. Start s4 fell into A2 on spark1, as in the 1.0.0 rerun, which shows that the start split between modes is the same on this machine.
- **Environment.** espei 0.8.11.dev82+g9039ea215 and pycalphad 0.11.3.dev35+g9a6939dd2: match.
- **PhaseForge+ source.** All 10 files of `environment/pins/spark1_phaseforgeplus_src_files.sha256` match.

## What 1.0.1 fixed relative to the 1.0.0 rerun

| 1.0.0 failure | 1.0.1 |
|---|---|
| 1. check10a required the label s4 | judged at the pick named by the rule: PASS |
| 2. global_10c started from the label s4 (mode A2 on spark1) | starts from the 10a pick, s1: both methods return to the pick |
| 3. pure_elements could not run (input read from `<home>/ScientificRuns` by an absolute path) | physics.py 1.0.1 reads the staged input: PASS on spark1 |
| 4. the PhaseForge+ pin covered caches and the full checkout | 10 source files: match |

## Files

- `rerun/`: the 10a check and pick summary, `multistart.json`, `evaluation.json`, the 10a pick TDB, the 10c status files, physics, per-dataset and thermochemistry comparison, the Laplace output, the phase sequences and `reproduce_logs/`.
- The full run root stays on spark1 at `<home>/orchid-protocols-work-20261106/rerun-crni4cb-1.0.1`.
