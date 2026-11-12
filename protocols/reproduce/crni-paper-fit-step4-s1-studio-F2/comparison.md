# Determinism check (F)

| step | file | result |
|---|---|---|
| build_oneshot_tdb (Cr-Ni build_tdb.py via run_with_fixed_date.py --date 2026-11-05) | `CrNi_PhaseForge_oneshot_Sex_GRACE-2L-SMAX-OMAT-large.tdb` | PASS byte-identical |
| build_oneshot_tdb (no S_ex variant) | `CrNi_PhaseForge_oneshot_GRACE-2L-SMAX-OMAT-large.tdb` | PASS byte-identical |
| make_base (Cr-Ni step-1 base) | `step1_oneshot.tdb` | PASS byte-identical |
| make_base (no S_ex) | `step1_oneshot_noSex.tdb` | PASS byte-identical |
| evaluate_states (both picks, spark1, run twice) | `states_evaluated.json` | PASS byte-identical |
| evaluate_step.py on the Cu-Zr pick (invariants, liquid stability, pure elements, formation energies; spark1) | `eval.json` | PASS byte-identical |
| evidence bundles rebuilt (snapshot and bundle builders, freeze guards on) | `MANIFEST.json bundle_sha256` | PASS byte-identical |
| tdb_header.py run twice | `release/*.tdb` | PASS byte-identical |

Optimizer, same machine: Cr-Ni step 2, start s0_start, Studio, current scripts (fit.py/model.py of 06:55): logpost -1703.6767365508058 vs -1703.6767365508058, nfev [113, 113], max |Δθ| 0.0 → PASS bit-identical.

**Overall: PASS**
