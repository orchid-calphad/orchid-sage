# Reproduce report: crni-paper-fit-step4c-b@1.0.3

host spark1 (aarch64), python <home>/orchid-crni-mcmc-20261105/env/grad/bin/python, root `<home>/orchid-protocols-work-20261106/rerun-crni4cb-1.0.3`
started 2026-11-07T14:00:33-0600, finished 2026-11-07T14:00:35-0600; environment PASS (0.8.11.dev82+g9039ea215 0.11.3.dev35+g9a6939dd2)

| item | step | check | reference | rerun | tolerance | result |
|---|---|---|---|---|---|---|
| check10a | pick_solid | json_tol `results/pick10a_rerun.json` | -5657.288636859774 | -5657.288636863667 | 0.01 | PASS |
| check10a | pick_solid | json_equal `results/pick10a_rerun.json` | True |  | byte | PASS |
| check10a | pick_solid | json_tol `results/pick10a_rerun.json` | 1614 | 1614.0 | 2 | PASS |
| check10a | pick_solid | json_tol `results/pick10a_rerun.json` | 860 | 860.0 | 2 | PASS |
| global_10c | global_search | json_tol `steps/step4c_b_hingefloor_10c/basin_7201/status.json` | -5657.288636859766 | -5657.288636863626 | 0.01 | PASS |
| global_10c | global_search | json_tol `steps/step4c_b_hingefloor_10c/anneal_7201/status.json` | -5657.288636859768 | -5657.288636863596 | 0.01 | PASS |
| evaluate_states | evaluate_states | files_equal `evaluate/states_evaluated@1.1.0.json` | reference/states_evaluated@1.1.0.json | e24d0853de4ad38f1992f8dd1b669d55843ff08c | byte | PASS |
| phase_sequence | final_pick | sequence_equal `phase_sequence_rerun.json` | phase_sequence_reference.json |  | byte | PASS |
| pure_elements | physics_checks | json_equal `results/physics_rerun.json` | True |  | byte | PASS |
| pure_elements | physics_checks | json_equal `results/physics_rerun.json` | BCC_A2 |  | byte | PASS |
| pure_elements | physics_checks | json_equal `results/physics_rerun.json` | FCC_A1 |  | byte | PASS |
| thermochemistry | per_dataset | json_equal `results/thermo_compare.json` | True |  | byte | PASS |
| laplace_weights | laplace | json_tol `results/uq/laplace_step4c_b.json` | 0.7660570156257861 | 0.7660570169113187 | 0.01 | PASS |

PhaseForge+ source check (note): {'path': '<home>/orchid-crni-mcmc-20261105/src/PhaseForgePlus', 'pin': 'protocols/environment/pins/spark1_phaseforgeplus_src_files.sha256', 'pinned_files': 10, 'mismatch': [], 'pass': True}
Notes: ['environment: match (note, not a failure)', 'phaseforgeplus: match (note, not a failure)']
Expected failures: []; unexpected failures: []

**Overall: PASS** (predictions and data-identity checks; environment and pins are notes; an item marked expected=fail does not fail the run when it fails as declared)
