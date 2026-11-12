# Cr–Ni liquidus-first fit from the PhaseForge one-shot (6 Nov 2026)

Written by the coordinator from the agent's hand-back; the agent wrote no report file. Plan and run log in `PLAN.md`. Mac Studio only; espei 0.8.11.dev82+g9039ea215 from `<fit-env>` in every run card. No MCMC.

## Set-up
- Start: one-shot S_ex TDB, interaction terms and CRNI2 as VV symbols (values unchanged); SGTE end-members never fitted.
- One-shot observations: bcc/fcc HM_MIX at x_Ni 0.25/0.5/0.75 (s2), CrNi2 HM_FORM, liquid HM_MIX at 2200 K; σ = max(9.69 kJ, relaxation interval). Liquid S_ex at 1900/2200 K as provisional SM_MIX, weight 0.2/u.
- Set E data unchanged. Added: eutectic ORC-SV7H3CNRYS (three-phase ZPF); CrNi2 ordering ORC-X3KVP7D3PO (863 K, single reader); step-4 hinge: set E's 290 cells + CRNI2 excluded at T ≥ 895 K + new BCC_A2 exclusions at 17 Pugliese γ states (Table III limits; 1073–1448 K, x_Ni 0.55–0.75) and 11 fcc Curie marks (T ≥ 298 K), option C (σ 1000, τ 100, confidence 0.5), labelled.

## Steps
| step | data added | starts / modes | logpost | topology (600–2200 K) | one-shot moves (σ) |
|---|---|---|---|---|---|
| 1 one-shot | – | – | (−5617 on step-2 objective) | Cr-rich fcc too stable; liquid down only to 1730 K; CrNi2 to 1156 K | 0 |
| 2 liquidus | liquid ZPF, eutectic, S_ex, one-shot obs. | 9 / 1 | −1703.7 | eutectic 1616 K; CrNi2 (held) to 1664 K | ≤ 0.26 |
| 3a thermo, CrNi2 fixed | activities, HM_MIX, HM_FORM, Liu DFT | 8 / 4 | −4086 | broken: CrNi2 to 1828 K, above liquidus; fcc L1 +131 kJ | fcc ≤ 2.2 |
| 3b thermo, CrNi2 free | same | 8 / 1 (7 of 8) | −3941.8 | eutectic 1626 K; CrNi2 to 1074 K | fcc 0.5–0.9; CrNi2 0.27 |
| 4 solid state | solid ZPF, hinge, CrNi2 ordering, CrNi2 a,b free | 8 / 5 (main in 4) | −6332.24 | right at every T; eutectic 1620 K; **CrNi2 top 780 K vs 863 K** | bcc ≤ 0.23; fcc 1.24/1.08/0.38; CrNi2 0.29; liquid ≤ 0.16 |
| 5 ambiguous | none (CrNi2 Pt2Mo type) | – | – | CrNi2 HM_FORM −9.27 vs −12.07 (MLIP) | – |

Step-4 residuals (rms residual/σ): fcc HM_FORM 0.33–0.50; bcc HM_FORM 0.29–0.43; liquid HM_MIX 0.37–2.2 (Batalin worst); liquid activities 0.7–1.65; Pugliese activities 0.53–0.57 except 1448 K at 2.54 (flagged a_Cr = 0.112 point, 8.9σ, kept); liquid S_ex |z| ≤ 2.6; Liu DFT fcc 1.5; hinge −0.5 (all exclusions satisfied).

**Pick:** step 4 s1 (`tdb/CrNi_paper_fit_FINAL_step4_s1.tdb`), main mode, |g| 6e-5. Other modes > 10 log-units lower, non-stationary (kink). Notes, not rejections: fcc one-shot enthalpies moved +13.7 kJ (x 0.25) and +10.1 kJ (x 0.5) while fcc calorimetry is met within 0.5σ (SGTE vs MLIP/DFT fcc-Cr conflict; Liu DFT −12.7 kJ at x 0.25); bcc S_ex(0.5) +3.3 J/mol-atom/K (above the 2.5 chosen); CrNi2 S_f −6.6 J/mol-atom/K.

## Physics checks
- Liquid convex 600–2200 K.
- bcc metastable gap: chemical spinodal top 1329 K; coherent 1278/1293/1210 K (base/low/high k); binodal x 0.08–0.42 at 1200 K; hidden in bcc+fcc. Incoherent T_c (SRO / SRO+vib): 698/1149 K MLIP, 1056/1739 K DFT, 603/993 K fit. Convexity term not applied (0.4c).
- fcc metastable spinodal to 958 K on the Cr side, inside bcc+fcc.
- Unary limits exact.

## UQ (Laplace mixture)
- Weights: main 0.901, mode B 0.099, kink modes < 1e-7.
- 1000 classified draws: P(accepted topology) 0.20 ± 0.01 with the 800–930 K CrNi2 window (0.60 without); P(CrNi2 top within 25 K of 863 K) 0.13; CrNi2 top 670/775/910 K (5/50/95 %); P(fcc at x_Ni 0.52, 1473 K) 0.941 ± 0.007; eutectic 1595/1625/1680 K; bcc+bcc gap in 9.3 % of draws at 1200–1525 K.
- Independent marginals: P(accepted) 0.008, P(fcc) 0.31.
- Set E's Ni-rich bcc field at 1200–1500 K is gone; 28 % of draws push bcc past x_Ni 0.5 only at 1520–1760 K.

## Open decisions
1. CrNi2 83 K miss from the ZPF driving-force scale (default 1000 J/mol; σ_T 16 K × ΔS ≈ 12 J/mol-atom/K → ≈ 190 J/mol). Convert every ZPF σ to a driving-force σ?
2. Confirm as data: Pugliese γ assignments (Table III limits), Curie marks (single reader), ORC-X3KVP7D3PO (single reader).
3. Should 0.1 state that held compounds are free, anchored by their σ, in every step (3a vs 3b)?
4. Liquid S_ex 1900 vs 2200 K: Cp_ex from H_mix (−16) vs S_ex (+4.8) J/mol-atom/K, 6.5σ at x_Ni 0.25; read as sampling/reference; no T² or T ln T term.
5. Possible double counting: ORCHID eutectic vs Jenkins arrests; 6 duplicate row pairs in Jette kept.

Process: first step-2 launch stopped after 5 s (own PIDs) to remove `SETUPTOOLS_SCM_PRETEND_VERSION`; first step-3 launch failed on a start-TDB name and was relaunched; step-2 pick is the converged best start, not the ranker's grid-noise choice.
