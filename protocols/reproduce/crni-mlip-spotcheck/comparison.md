# MLIP spot-check on a different GPU host (G2)

Original spark1 (image ac223e2c…), rerun spark2 (independent build 8eae0b91…, identical pip freeze); code relax_solids.py b763dbf8…; GRACE-2L-SMAX-OMAT-large.

| lattice | cell | stage | E spark1 (eV/atom) | E spark2 (eV/atom) | diff (kJ/mol-atom) | lattice verdict identical | result |
|---|---|---|---|---|---|---|---|
| BCC_A2 | x0.0000_pure | s0_unrelaxed | -9.51452349 | -9.51452352 | -0.000003 | True | PASS |
| BCC_A2 | x0.0000_pure | s1_volume | -9.52456618 | -9.52456587 | +0.000030 | True | PASS |
| BCC_A2 | x0.0000_pure | s2_volume_ions | -9.52456618 | -9.52456587 | +0.000030 | True | PASS |
| BCC_A2 | x0.0000_pure | s3_full | -9.52456618 | -9.52456587 | +0.000030 | True | PASS |
| BCC_A2 | x0.1250_s2026110501 | s0_unrelaxed | -8.93971867 | -8.93971838 | +0.000028 | True | PASS |
| BCC_A2 | x0.1250_s2026110501 | s1_volume | -8.93974205 | -8.93974216 | -0.000010 | True | PASS |
| BCC_A2 | x0.1250_s2026110501 | s2_volume_ions | -8.95202624 | -8.95202618 | +0.000005 | True | PASS |
| BCC_A2 | x0.1250_s2026110501 | s3_full | -8.95204701 | -8.95204699 | +0.000003 | True | PASS |
| BCC_A2 | x0.2500_s2026110501 | s0_unrelaxed | -8.39159041 | -8.39159006 | +0.000033 | True | PASS |
| BCC_A2 | x0.2500_s2026110501 | s1_volume | -8.39162304 | -8.39162298 | +0.000005 | True | PASS |
| BCC_A2 | x0.2500_s2026110501 | s2_volume_ions | -8.41078296 | -8.41078304 | -0.000007 | True | PASS |
| BCC_A2 | x0.2500_s2026110501 | s3_full | -8.41092097 | -8.41092090 | +0.000007 | True | PASS |
| BCC_A2 | x0.5000_s2026110501 | s0_unrelaxed | -7.37161513 | -7.37161094 | +0.000404 | True | PASS |
| BCC_A2 | x0.5000_s2026110501 | s1_volume | -7.37188792 | -7.37188794 | -0.000001 | True | PASS |
| BCC_A2 | x0.5000_s2026110501 | s2_volume_ions | -7.39897728 | -7.39897730 | -0.000002 | True | PASS |
| BCC_A2 | x0.5000_s2026110501 | s3_full | -7.41833078 | -7.41833082 | -0.000004 | True | PASS |
| BCC_A2 | x1.0000_pure | s0_unrelaxed | -5.39476917 | -5.39476915 | +0.000003 | True | PASS |
| BCC_A2 | x1.0000_pure | s1_volume | -5.39500115 | -5.39500146 | -0.000031 | True | PASS |
| BCC_A2 | x1.0000_pure | s2_volume_ions | -5.39500115 | -5.39500146 | -0.000031 | True | PASS |
| BCC_A2 | x1.0000_pure | s3_full | -5.39500115 | -5.39500146 | -0.000031 | True | PASS |
| FCC_A1 | x0.0000_pure | s0_unrelaxed | -9.13193095 | -9.13193089 | +0.000006 | True | PASS |
| FCC_A1 | x0.0000_pure | s1_volume | -9.13285457 | -9.13285360 | +0.000093 | True | PASS |
| FCC_A1 | x0.0000_pure | s2_volume_ions | -9.13285457 | -9.13285360 | +0.000093 | True | PASS |
| FCC_A1 | x0.0000_pure | s3_full | -9.13285457 | -9.13285360 | +0.000093 | True | PASS |
| FCC_A1 | x0.5000_s2026110511 | s0_unrelaxed | -7.40277068 | -7.40276930 | +0.000133 | True | PASS |
| FCC_A1 | x0.5000_s2026110511 | s1_volume | -7.40453399 | -7.40453399 | -0.000000 | True | PASS |
| FCC_A1 | x0.5000_s2026110511 | s2_volume_ions | -7.41352811 | -7.41352815 | -0.000004 | True | PASS |
| FCC_A1 | x0.5000_s2026110511 | s3_full | -7.41522719 | -7.41522721 | -0.000003 | True | PASS |
| FCC_A1 | x1.0000_pure | s0_unrelaxed | -5.48767814 | -5.48767813 | +0.000001 | True | PASS |
| FCC_A1 | x1.0000_pure | s1_volume | -5.48864483 | -5.48864472 | +0.000010 | True | PASS |
| FCC_A1 | x1.0000_pure | s2_volume_ions | -5.48864483 | -5.48864472 | +0.000010 | True | PASS |
| FCC_A1 | x1.0000_pure | s3_full | -5.48864483 | -5.48864472 | +0.000010 | True | PASS |

**Overall: PASS** (32/32; max |diff| 4.04e-04 kJ/mol-atom against a tolerance of 0.1)
