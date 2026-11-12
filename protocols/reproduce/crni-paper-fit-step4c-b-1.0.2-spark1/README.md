# Independent scripted rerun of crni-paper-fit-step4c-b@1.0.2 on spark1 (7 Nov 2026)

**Overall tool verdict: PASS.** Every prediction is within its tolerance, and every data-identity check is byte-identical, including `states_evaluated@1.1.0.json`, the file that 1.0.2 re-pinned. The environment check and the PhaseForge+ source check also match; under the PI's ruling of 6 Nov they are notes, not part of the verdict. One finding needs attention (below): the 10a re-evaluation of start s1 did not give the objective that the multistart recorded for the same parameter vector.

## How it was run

The run used a fresh root, from a `git archive` copy of orchid-sage at e73a44c (1.0.2 as approved; spec sha256 95c5e091…):

`python3 protocols/tools/orchid_reproduce.py protocols/specific/crni-paper-fit-step4c-b@1.0.2.yaml --root <home>/orchid-protocols-work-20261106/rerun-crni4cb-1.0.2 --python <home>/orchid-crni-mcmc-20261105/env/grad/bin/python --pfp <home>/orchid-crni-mcmc-20261105/src/PhaseForgePlus/src --nproc 4 --report <home>/orchid-protocols-work-20261106/rerun-crni4cb-1.0.2_report.json`

- **Timing.** 09:29–11:33 CST (2 h 04 min).
- **Load.** spark1 was idle before the start (load average 0.9 of 20 cores); no other job was touched.
- **Exact PIDs started.** bash 1711895 and orchid_reproduce 1711901, under the ssh wrapper 1711893. All have ended (exit 0).
- **Spec versions.** After the launch, a commit reference in one decision row of 1.0.2 was corrected (93c16cf, spec sha256 afcff291…; no command, pin or plan item changed). The final report was then written with `--compare-only` in the same root, from a copy at 93c16cf, as was done for 1.0.1.

**Report files.**
- `reproduce_report.{json,md}`: the final report (spec at 93c16cf).
- `reproduce_report_run.*`: the report of the run itself (spec at e73a44c; also PASS, same values).

## Per item (reference = the recorded Studio pick s4, mode A)

| item | quantity | reference | rerun (spark1) | tolerance | result |
|---|---|---|---|---|---|
| stage | 409 code and evidence files (stage manifest MANIFEST@1.1.0.json) | manifests | sha256 equal | byte | PASS |
| step4c_b | multistart + evaluate.py | – | 8 of 8 converged; endpoint objectives identical to the 1.0.1 rerun for all 8 starts; `evaluation.json` byte-identical to the 1.0.1 rerun | – | ran (judged at the 10a pick) |
| check10a | 10a pick by the rule | s4_perturbed (Studio) | **s2_perturbed**: 7 of 8 smooth and eligible, s1 not stationary (see finding); gap to runner-up 1.1e-8 | label is a note | – |
| check10a | objective of the 10a pick | −5657.288636859774 | −5657.288636867119 (Δ 7.3e-9) | 0.01 | PASS |
| check10a | pick eligible under 10a | true | true (smooth, \|g\| 5.3e-4) | – | PASS |
| check10a | eutectic (T_liquid_min) | 1614 K | 1614 K | 2 K | PASS |
| check10a | CrNi2 top | 860 K | 860 K | 2 K | PASS |
| global_10c | basin hopping best from the 10a pick (seed 7201, 1500 evaluations, 4447 s) | −5657.288636859766 | −5657.288636866923 | 0.01 | PASS (no better optimum; +2e-10 over the start) |
| global_10c | dual annealing best (1500 evaluations, 4273 s, both in parallel) | −5657.288636859768 | −5657.288636866808 | 0.01 | PASS (no better optimum; +3e-10) |
| evaluate_states | `states_evaluated@1.1.0.json` (695 states, 424 match) | e24d0853… | e24d0853… | byte | PASS |
| phase_sequence | phase order on heating, 0.01 grid, 600–2200 K, at the 10a pick | recorded pick | identical | labels identical, 10 K | PASS |
| pure_elements | unary limits; Cr, Ni stable phases below T_m (staged Cahn input) | true; BCC_A2; FCC_A1 | true; BCC_A2; FCC_A1 (liquid convex 600–2200 K, bcc spinodal top 1385 K, coherent 1338/1352/1275 K as recorded) | exact | PASS |
| thermochemistry | 22 data/thermo datasets, rms residual/σ at the 10a pick | `per_dataset_step4c_b_hingefloor.json` | 22 of 22 present, same n, max \|Δ rms_z\| 7.8e-6 | 0.1 | PASS |
| laplace_weights | main-mode weight | 0.7660570156 | 0.7660570169 | 0.01 | PASS* |

\* As before, this item uses the recorded `modes_step4c_b.json`, so it tests the Hessian and mixture code, not the mode finding.

## Finding: the 10a re-evaluation of s1 differs from its multistart objective (unresolved)

- The multistart endpoint of s1 is bit-identical to that of the 1.0.1 rerun (same θ, objective −5657.288636863667, \|g\| 2.3e-4 in the multistart record).
- In the 1.0.1 rerun, `check10a_ms.py` re-evaluated that θ at −5657.288636863667 (smooth, the 10a pick). In this rerun, the same script on the same machine, with the same code and the same θ (difference 0.0), evaluated it at **−5517.680257224548** with analytic \|g\| 0.119 and 9 improving directions, so s1 was classed `not_stationary`, and the rule picked s2 of the same mode.
- No equilibrium was reported as failed (`n_failed_equilibria` 0), and the 8 on-boundary points are the same 8 data points as in 1.0.1. The difference of about 140 log-units therefore comes from an objective evaluation that is not deterministic at a fixed θ. A plausible cause, not tested here, is state carried by the 4 worker processes from one start to the next (s1 took 453 s here and 1275 s in 1.0.1, so the starts reached the workers in a different order). It could be checked by re-evaluating s1 alone.
- The verdict does not change: the pick s2 is in mode A, and every prediction passes. But a re-evaluation at a fixed θ should not move the objective, and the same effect could change which start is eligible. This is open for the coordinator and the PI. The numbers are in `rerun/check10a_rerun.json` here and in `../crni-paper-fit-step4c-b-1.0.1-spark1/rerun/check10a_rerun.json`.

## Notes (never failures)

- **Parameters (10b, `rerun/pick10a_rerun.json`).** The five determined symbols (VV0000–VV0003, VV0012) are within the tolerance; the worst |Δ|/tol is 0.011. The nine symbols in the flat A/A2 directions are undetermined, and none of them lies beyond tolerance against the recorded mode A_s4 (largest |Δ|/tol over all symbols 0.023). The other TDB lines are identical.
- **Start and mode labels.** The 10a pick is s2 here, s1 in the 1.0.1 rerun and s4 on the Studio, all in mode A. As in 1.0.0 and 1.0.1, s0, s4 and s5 fall into A2 on spark1.
- **Environment.** espei 0.8.11.dev82+g9039ea215 and pycalphad 0.11.3.dev35+g9a6939dd2: match.
- **PhaseForge+ source.** All 10 files of `environment/pins/spark1_phaseforgeplus_src_files.sha256` match.

## What 1.0.2 changed relative to the 1.0.1 rerun

1.0.2 changes only the evidence pins (bundle 1.1.0). Here that shows up only in the `evaluate_states` item, which is now byte-identical against `states_evaluated@1.1.0.json` (424 of 695 states match, was 404 with bundle 1.0.0). The fit, its starts and the predictions are those of 1.0.1.

## Files

- `rerun/` holds:
  - the 10a check and pick summary, `multistart.json`, `evaluation.json` and the 10a pick TDB;
  - the 10c status files;
  - the physics, per-dataset and thermochemistry comparisons;
  - the Laplace output, the phase sequences and `reproduce_logs/`.
- The full run root stays on spark1 at `<home>/orchid-protocols-work-20261106/rerun-crni4cb-1.0.2`.
