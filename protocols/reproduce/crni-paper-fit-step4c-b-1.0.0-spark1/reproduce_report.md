# Reproduce report: crni-paper-fit-step4c-b@1.0.0

host spark1 (aarch64), python <home>/orchid-crni-mcmc-20261105/env/grad/bin/python, root `<home>/orchid-protocols-work-20261106/rerun-crni4cb-1.0.0`
started 2026-11-06T18:55:13-0600, finished 2026-11-06T21:44:25-0600; environment PASS (0.8.11.dev82+g9039ea215 0.11.3.dev35+g9a6939dd2)

| item | step | check | reference | rerun | tolerance | result |
|---|---|---|---|---|---|---|
| step4c_b | fit_solid | json_tol `steps/step4c_b_hingefloor/multistart.json` | -5657.288636859774 | -5657.293148832628 | 0.01 | PASS |
| step4c_b | fit_solid | tdb_abs `tdb/step4c_b_hingefloor_pick.tdb` | assessments/crni-paper-fit-step4c-b/evid | 9547bd6917472f890df7f0d27810d121869f3cf8 (worst |diff|/tol 3.87e-02) | per-symbol abs | PASS |
| step4c_b | fit_solid | json_tol `steps/step4c_b_hingefloor/evaluation.json` | 1614 | 1614.0 | 2 | PASS |
| step4c_b | fit_solid | json_tol `steps/step4c_b_hingefloor/evaluation.json` | 860 | 860.0 | 2 | PASS |
| check10a | pick_solid | json_equal `results/check10a_rerun.json` | s4_perturbed |  | byte | FAIL |
| global_10c | fit_solid | json_tol `steps/step4c_b_hingefloor_10c/basin_7201/status.json` | -5657.288636859766 | -5657.289734957976 | 0.01 | PASS |
| global_10c | fit_solid | json_tol `steps/step4c_b_hingefloor_10c/anneal_7201/status.json` | -5657.288636859768 | -5657.293148832564 | 0.01 | PASS |
| evaluate_states | evaluate_states | files_equal `evaluate/states_evaluated@1.0.0.json` | reference/states_evaluated@1.0.0.json | b610e5ecb4c0bb61ff6ee0c6837c42aeaac4f06f | byte | PASS |
| phase_sequence | final_pick | sequence_equal `phase_sequence_rerun.json` | phase_sequence_reference.json |  | byte | PASS |
| pure_elements | physics_checks | command exit code `` |  |  | byte | FAIL |
| laplace_weights | laplace | json_tol `results/uq/laplace_step4c_b.json` | 0.7660570156257861 | 0.7660570169113187 | 0.01 | PASS |

PhaseForge+ source check: {'path': '<home>/orchid-crni-mcmc-20261105/src/PhaseForgePlus', 'pinned_files': 406, 'mismatch': ['./.github/dependabot.yml', './.github/workflows/lint.yml', './.github/workflows/release.yml', './.github/workflows/tests.yml', './.gitignore', './.gitmodules', './.pre-commit-config.yaml', './.pytest_cache/.gitignore', './.pytest_cache/CACHEDIR.TAG', './.pytest_cache/README.md'], 'pass': False}
Expected failures: []; unexpected failures: ['check10a']

**Overall: FAIL** (an item marked expected=fail does not fail the run when it fails as declared)
