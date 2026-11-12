# GPU spot check of the MLIP steps (7 Nov 2026): spark3 vs the recorded spark1 values

Model GRACE-2L-SMAX-OMAT-large; container cuzr-phaseforge-grace-gpu:20261104 (spark3 image sha256:8eae0b91...); code relax_solids.py b763dbf81439..., run_liquid.py a4b6d40c...; weights hash-checked against provenance/potential_sha256.txt.

| item | quantity | reference (spark1) | rerun (spark3) | difference | tolerance | result |
|---|---|---|---|---|---|---|
| bcc SQS x_Ni 0.25, seed s2026110501 | E s0_unrelaxed (eV/atom) | -8.39159041 | -8.39159086 | -0.000043 kJ/mol-atom | 0.1 kJ/mol-atom | PASS |
| bcc SQS x_Ni 0.25, seed s2026110501 | E s1_volume (eV/atom) | -8.39162304 | -8.39162304 | +0.000000 kJ/mol-atom | 0.1 kJ/mol-atom | PASS |
| bcc SQS x_Ni 0.25, seed s2026110501 | E s2_volume_ions (eV/atom) | -8.41078296 | -8.41078293 | +0.000003 kJ/mol-atom | 0.1 kJ/mol-atom | PASS |
| bcc SQS x_Ni 0.25, seed s2026110501 | E s3_full (eV/atom) | -8.41092097 | -8.41092103 | -0.000006 kJ/mol-atom | 0.1 kJ/mol-atom | PASS |
| liquid Cr50Ni50, 108 atoms, 2200 K, 100 ps, seed 2026110503 | H (eV/atom) | -6.61923 ± 0.00523 | -6.68807 ± 0.00445 | -6.642 kJ/mol-atom (z -10.02) | 1.325 kJ/mol-atom (2 x combined SE) | FAIL |

**Overall: FAIL**

Diagnostic (not a verdict change): U+K differs by +0.512 kJ/mol-atom (z +2.92); <p>V differs by -7.154 kJ/mol-atom. the enthalpy difference is mostly the <p>V term: the NVT volume taken from 5 ps of NPT differs by +0.096 A3/atom between the runs, so <p> is +0.14 GPa (spark1) and -0.78 GPa (spark3); the block SE of the production run does not contain this volume uncertainty. Not a verdict change; a note for the PI.
