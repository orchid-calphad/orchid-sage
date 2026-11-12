# Independent scripted rerun of crni-paper-fit-step4c-b@1.0.0 on spark1 (6 Nov 2026)

**Command.** `python3 protocols/tools/orchid_reproduce.py protocols/specific/crni-paper-fit-step4c-b@1.0.0.yaml --root <home>/orchid-protocols-work-20261106/rerun-crni4cb-1.0.0 --python <home>/orchid-crni-mcmc-20261105/env/grad/bin/python --pfp <home>/orchid-crni-mcmc-20261105/src/PhaseForgePlus/src --nproc 4`

**Setup.**
- Run on spark1 (aarch64 Linux), from a copy of the repository. The pick was made on the Studio (arm64 macOS).
- Wall time 18:55–21:44 CST, 405 files staged by hash.
- The spec copy used has sha256 7387d3ee… Its `reproduce` section is identical to the committed 1.0.0 (5bede65); the two differ only in pinned hashes and one added decision.
- The first attempt failed after 24 s because `tdb/step1_oneshot.tdb` was not staged. The stage was fixed in 1.0.0 before the commit, and that attempt is kept in spark1 `<home>/orchid-protocols-work-20261106/attic-rerun-crni4cb-1.0.0-attempt1*`.

**Overall tool verdict: FAIL.** Two checks fail (check10a, pure_elements) and the PhaseForge+ pin check fails. **Judged by predictions, the artifact reproduces.** Each failure is explained below; none is a difference in the fitted model.

## Byte-identical
| item | file | result |
|---|---|---|
| stage | 405 code and evidence files | sha256 equal to the manifests |
| evaluate_states | `states_evaluated@1.0.0.json` (695 states, at the bundle pick TDB) | byte-identical (b610e5ec…) |
| environment | espei 0.8.11.dev82+g9039ea215, pycalphad 0.11.3.dev35+g9a6939dd2 | PASS |

## Within tolerance (predictions)
| quantity | original (Studio) | rerun (spark1) | tolerance | verdict |
|---|---|---|---|---|
| 10a pick objective | s4 −5657.2886369 | s1 −5657.2886369 (Δ 4e-9) | 0.01 | PASS |
| 10a kind | 8/8 smooth | 8/8 smooth | – | same |
| pick parameters (rerun 10a pick vs original pick) | – | max 0.039 of tolerance (CrNi2 a +0.98 J/mol, b −0.0012 J/mol/K) | 50 J/mol, 0.03 J/mol/K | PASS |
| pick TDB (`tdb_abs`) | 36922433… | 9547bd69… | as above | PASS (not byte-identical) |
| eutectic / CrNi2 top | 1614 / 860 K | 1614 / 860 K | 2 K | identical |
| phase sequence on heating, 0.01 grid, 600–2200 K | – | identical labels, transitions within 10 K | 10 K | PASS |
| thermochemistry, 63 datasets (`per_dataset.py` at both picks, run on the Studio) | – | largest residual difference 0.33 J/mol; z differences ≤ 0.022 | – | same |
| pure elements (`physics.py` at the rerun pick, run on the Studio) | unary ok; Cr BCC_A2, Ni FCC_A1 | same; liquid convex 600–2200 K; bcc spinodal top 1385 K (same) | exact | PASS (see the failure below) |
| 10c best, basin hopping / dual annealing | −5657.2886369 / −5657.2886369 | −5657.2897350 / −5657.2931488 | 0.01 | PASS (no point above the pick) |
| Laplace main-mode weight | 0.766057 | 0.766057 | 0.01 | PASS* |

\* The plan item uses the bundle's reference `modes_step4c_b.json`, not the rerun's own modes. It therefore tests the Hessian and mixture code, not the mode finding.

**Two minima of one flat basin (A and A2), and how they reproduce.**
- The objective has two minima in one flat basin: mode A at −5657.288637 and mode A2 at −5657.293149.
- They are 0.0045 log-units apart and up to 5.9× the 10b tolerance apart in parameters (bcc L1 a −286 J/mol, fcc L1 a +294 J/mol, bcc L1 b +0.18 J/mol/K).
- **Start split.** In the original, 7 starts reached mode A and 1 reached A2 (s5). In the rerun, 5 reached A (s1, s2, s3, s6, s7) and 3 reached A2 (s0, s4, s5).
- **Each mode reproduces.** A matches within 0.039 of the tolerance, and the rerun's A2 matches the original s5 within 0.011.
- **Undetermined directions.** The flat directions between the two modes (bcc L1, fcc L1 a) are reported as **undetermined** at the 10b tolerance. The predictions agree in both modes: identical diagram, invariants and thermochemistry.

## Failures and their causes
1. **check10a (FAIL, defect in the plan, not in the model).** The check requires `pick == "s4_perturbed"`, a start label. On spark1, s4 fell into mode A2, so the 10a pick is s1 (mode A). Its objective is the original pick's within 4e-9 and its parameters within 0.039 of the tolerance. The check should compare the pick's objective and parameters (`json_tol` and `tdb_abs`), not its name.
2. **global_10c starts from s4 by name (passes, but tests the wrong point).** The plan hard-codes `s4_perturbed` as the start. In the rerun, s4 is mode A2.
   - Basin hopping rose from −5657.29315 to −5657.28973 in 1500 evaluations but did not reach mode A.
   - Dual annealing stayed at A2.
   - So, at T 25, step 0.05 and 1500 evaluations, the global search does not cross the 0.3 kJ/mol gap between the two flat minima.
   - The start should be the 10a pick, read from `results/check10a_rerun.json`.
3. **pure_elements (FAIL, missing stage input).** `physics.py` reads `<home>/ScientificRuns/cr-ni-coherent-20261105/results.json` (Cahn inputs, sha256 c7d7369e…) by an absolute path. That file is not in the bundles, so the item cannot run on a host without the campaign tree. The 0.2.0-draft plan had the same gap. The check itself passes when run on the Studio.
4. **PhaseForge+ pin check (FAIL, scope of the check).** The pin file lists 406 files of the full checkout. The spark1 copy holds only `pyproject.toml`, `README.md` and `src/`. All 9 pinned `src/` files match; `utils/hinge.py` is 892c139f… on spark1, in its venv and on the Studio. The check should pin the source files the run imports.

**Proposed 1.0.1 fixes (not made; a plan change needs its own rerun):**
- check10a: compare the pick's objective and parameters, not the start label;
- global_10c: start from the 10a pick;
- stage the coherent-strain results file and run `physics.py` with that input;
- PhaseForge+ pins: restrict them to `src/`.

## Files
- `reproduce_report.{json,md}`: the tool's own report.
- `prediction_comparison_params.json`: the parameter comparisons by mode.
- `thermo_comparison_summary.json`: the per-dataset comparison.
- `rerun/`: the rerun's `multistart.json`, `evaluation.json`, `check10a_rerun.json`, the pick, s1 and s4 TDBs, the 10c status and parameters, the Laplace output, the phase sequences, `reproduce_logs/`, and the Studio-side `physics_rerun.json` and `per_dataset_{rerun,ref}.json`.
