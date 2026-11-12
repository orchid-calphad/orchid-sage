# Comparison: crni-paper-fit-step4c-b@1.0.4

run root `<home>/mcp-rerun-crni-1.0.4-20261107/run`, 2026-11-07T17:46:32-0600

| item | rule | path | result |
|---|---|---|---|
| stage |  |  | ran (no output to compare) |
| environment_check |  |  | ran (no output to compare) |
| check10a | json_tol | results/pick10a_rerun.json | PASS |
| check10a | json_equal | results/pick10a_rerun.json | PASS |
| check10a | json_tol | results/pick10a_rerun.json | PASS |
| check10a | json_tol | results/pick10a_rerun.json | PASS |
| global_10c | json_tol | steps/step4c_b_hingefloor_10c/basin_7201/status.json | PASS |
| global_10c | json_tol | steps/step4c_b_hingefloor_10c/anneal_7201/status.json | PASS |
| evaluate_states | files_equal | evaluate/states_evaluated@1.2.0.json | PASS |
| phase_sequence | sequence_equal | phase_sequence_rerun.json | PASS |
| pure_elements | json_equal | results/physics_rerun.json | PASS |
| pure_elements | json_equal | results/physics_rerun.json | PASS |
| pure_elements | json_equal | results/physics_rerun.json | PASS |
| thermochemistry | json_equal | results/thermo_compare.json | PASS |
| laplace_weights | json_tol | results/uq/laplace_step4c_b.json | PASS |

**Overall (13 compared): PASS**
