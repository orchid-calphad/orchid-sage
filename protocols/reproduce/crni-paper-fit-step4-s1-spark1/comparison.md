# Reproduce report: crni-paper-fit-step4-s1@0.1.0-draft

host spark1 (aarch64), python <home>/orchid-crni-mcmc-20261105/env/grad/bin/python, root `<home>/orchid-protocols-work-20261106/reproduce-crni-step4s1-c`
started 2026-11-06T08:36:25-0600, finished 2026-11-06T08:36:26-0600; environment PASS (0.8.11.dev82+g9039ea215 0.11.3.dev35+g9a6939dd2)

| item | step | check | reference | rerun | tolerance | result |
|---|---|---|---|---|---|---|
| step2 | fit_liquidus | json_tol `steps/step2_liquidus/multistart.json` | -1703.6767365088053 | -1703.6767369237646 | 0.01 | PASS |
| step2 | fit_liquidus | tdb_abs `tdb/step2_liquidus_pick.tdb` | assessments/crni-paper-fit-step4-s1/evid | 586549f5828c169d0997693cbef8ef187352ece4 (worst |diff|/tol 3.34e-01) | per-symbol abs | PASS |
| step2 | fit_liquidus | json_tol `steps/step2_liquidus/evaluation.json` | 1616 | 1616.0 | 2 | PASS |
| step2 | fit_liquidus | json_tol `steps/step2_liquidus/evaluation.json` | 1664 | 1662.0 | 2 | PASS |
| step3b | fit_thermo | json_tol `steps/step3b_thermo_crni2free/multistart.json` | -3941.800787656944 | -3941.8188020044654 | 0.05 | PASS |
| step3b | fit_thermo | tdb_abs `tdb/step3b_thermo_crni2free_pick.tdb` | assessments/crni-paper-fit-step4-s1/evid | 92f368cb896133e441de1f5eaebf8a6a2922a9a2 (worst |diff|/tol 3.47e+01) | per-symbol abs | FAIL |
| step3b | fit_thermo | json_tol `steps/step3b_thermo_crni2free/evaluation.json` | 1626 | 1626.0 | 2 | PASS |
| step3b | fit_thermo | json_tol `steps/step3b_thermo_crni2free/evaluation.json` | 1074 | 1038.0 | 2 | FAIL |
| step4 | fit_solid | json_tol `steps/step4_solid/multistart.json` | -6332.243665831225 | -6332.243665834535 | 0.01 | PASS |
| step4 | fit_solid | tdb_abs `tdb/step4_solid_pick.tdb` | assessments/crni-paper-fit-step4-s1/evid | 7ddafb90588b6118275847bb34421d003b6af81d (worst |diff|/tol 2.07e-03) | per-symbol abs | PASS |
| step4 | fit_solid | json_tol `steps/step4_solid/evaluation.json` | 1620 | 1620.0 | 2 | PASS |
| step4 | fit_solid | json_tol `steps/step4_solid/evaluation.json` | 780 | 780.0 | 2 | PASS |

**Overall: FAIL**
