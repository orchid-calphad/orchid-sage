# Cr–Ni liquidus-first CALPHAD fit from the PhaseForge one-shot (unified ORCHID + PhaseForge + PhaseForge+ paper) — plan

Written 6 Nov 2026, before any fit. Protocol: `<orchid-sage>/docs/fit_protocol.md` v2.0, Section 0 (0.0a–0.6), read in full;
nothing in it is reinterpreted here. Mac Studio only (hostname mac-studio, Mac13,1, 10 cores); local work, no remote or cloud
agents, no worktrees, no git commits, no `rm`, stop only own processes by exact PID. Studio load at start: ~10 (six Cu–Zr fit
processes of other campaigns, not touched), so at most 4 fit workers are used.

## Inputs (read only)
| what | where |
|---|---|
| one-shot TDB (start) | `crni-phaseforge-20261105/tdb/CrNi_PhaseForge_oneshot_Sex_GRACE-2L-SMAX-OMAT-large.tdb` (sha256 84ec5ae4…), and the variant without S_ex (108378d6…) for comparison |
| one-shot energies and σ | `results/solids_GRACE-2L-SMAX-OMAT-large.json` (s2 seed means, [s3, s0] interval), `results/oneshot_tdb.json` (CrNi2), `results/liquid_checks_enthalpy.json` (MD H_mix 2200 K), `results/liquid_excess_entropy.json` (S_ex 1900/2200 K, u) |
| set E data | `cr-ni-rebuild-20261105/inputs/derived/setE_orchid_sigmas/` (datasets with ORCHID-rule σ, hinge sidecar of 290 cells, option C) |
| CrNi2 ordering | ORCHID record ORC-X3KVP7D3PO (Hao et al. 2021 p. 13: ordering at 863 K near 66.7 at.% Ni, XRD and neutron diffraction, experimental via [160,161]; σ_eff 16 K; single reader, not yet accepted) in `<home>/data/private/crni-assessment-export-20261105/records.jsonl` |
| new exclusions | Pugliese 1970 Table III γ limits (`<home>/data/private/crni-pugliese-export-20261105`), fcc Curie marks of Hao Fig. 13(a) (assessment export) |
| eutectic | ORCHID ORC-SV7H3CNRYS (1618 K; L 0.46, bcc 0.38, fcc 0.50 x_Ni; experimental, accepted; σ 11 K) |
| code reused | `cr-ni-rebuild-20261105/scripts/` crni.py (GradTarget), fit.py (multistart L-BFGS-B, jitter retry), pdfast.py (hull diagram), curvature.py, laplace/scripts/hessian_mode.py, mixture.py; Cu–Zr `cuzr-protocol-oneshot-20261106/scripts/fit_step.py` for the one-shot observation datasets |

## Model (one-shot, frozen rules)
LIQUID, BCC_A2, FCC_A1 (disordered only, no FCC_L12), CRNI2 stoichiometric 1:2 (Pt2Mo type). SGTE91 unaries for every end-member,
never fitted (fcc Cr = GHSERCR + 7284 + 0.163T, bcc Ni included). No magnetic terms (as the one-shot). Excess electronic entropy of
the liquid taken as zero (PI, 6 Nov). Parameters (alphabetical L(CR,NI;k), a + bT):
VV0000/01 L0 liq, VV0002/03 L1 liq, VV0004/05 L0 bcc, VV0006/07 L1 bcc, VV0008/09 L0 fcc, VV0010/11 L1 fcc,
VV0012/13 CRNI2 (G = GFCCCR + 2 GHSERNI + VV0012 + VV0013·T, per formula unit, as the one-shot).
One-shot values: liq L0 −19115.3 + 1.53T (S_ex variant), L1 0; bcc 22450.6 / 38187.6; fcc −40467.4 / −8324.6; CrNi2 −43487.6; all b = 0
for the solids.

## One-shot energies as observations (0.0a, 0.1; Cu–Zr precedent `fit_step.py`)
- BCC_A2 and FCC_A1 HM_MIX at 298.15 K, x_Ni 0.25/0.5/0.75: the s2 seed means; σ_i = max(σ_MLIP, s0 − s2, s2 − s3) with
  σ_MLIP = 9.687 kJ/mol-atom (`orchid-phaseforge-demo/results/sigma_mlip.json`, as Cu–Zr), i.e. σ_MLIP widened so 1σ covers the staged
  interval.
- CRNI2 HM_FORM 298.15 K: −12.068 kJ/mol-atom on the SER basis of the TDB (= −14.496 vs fcc refs + 7.284/3), σ = max(σ_MLIP, interval).
- LIQUID HM_MIX at 2200 K, x 0.25/0.5/0.75: MD values (−4.21, −3.18, −4.28 kJ), σ = σ_MLIP (block SE ≪ σ).
- LIQUID S_ex (provisional, corrected Hong–Liu chemical + VACF vibrational) at 1900 and 2200 K, x 0.25/0.5/0.75, as SM_MIX (value =
  S_ex + S_ideal), ESPEI weight 0.2/u (u as reported). Flag: 1900 K is 0.6–0.7 J/mol-atom/K more negative than 2200 K (2–3 u). Before
  fitting, the H_mix(T) of the same runs is compared through dH = T dS; no T² or T ln T term is added (would need reporting first).
These are observations, not a penalty, and their σ is not widened unless measurements of that phase exist (step 3: the σ_MLIP is
already the DFT-vs-experiment error, so no widening is needed; stated, not done).

## Sequence (0.1), each step from the previous accepted step, versioned in `steps/<step>/`
| step | free | data added (all from set E unless noted; ESPEI weights from σ, no multipliers, ZPF weight 1) |
|---|---|---|
| 1 one-shot | – | none; diagram, pure elements, phase list |
| 2 liquidus | liq L0, L1 (a, b); bcc and fcc L0, L1 (a, b) = 12 | liquid-containing rows of the ZPF files (Bechtoldt fig. 1, Jenkins, Svechnikov; (i)+(ii) of partial tie-lines, 0.4a), the ORCHID eutectic (3-phase ZPF), liquid S_ex, all one-shot observations |
| 3 thermochemistry | same 12 | + activities (Pugliese bcc, Hao liquid), liquid HM_MIX (Batalin, Sudavtsova, Saltykov, Thiedemann), HM_FORM (Dench, Watson), DFT HM_MIX (Liu 2016) |
| 4 solid state | + CRNI2 a, b = 14 | + solid-only ZPF rows (bcc+fcc), the hinge (set E cells, option C), new BCC_A2 exclusions at observed single-phase fcc states (labelled, below), CRNI2 added to the excluded list at states above 895 K (863 + 2σ), CrNi2 ordering ZPF (CRNI2 at 2/3 with FCC_A1 at zero phase fraction, 863 K) |
| 5 ambiguous structures | – | none in Cr–Ni (CrNi2 is Pt2Mo-type, known); check CrNi2 and the solutions against the MLIP band (~10 kJ/mol-atom); final ranking |
Rows are split by phase content only (labelled files in `data/`); values, σ and weights are unchanged. Step 2 has no hinge (0.1 puts
exclusions in step 4); if a solid is stable above the liquidus after step 2, 0.4 applies (add the liquid-state exclusions that exist,
step 2b), reported.

New BCC_A2 exclusion records (0.4, item 8; put in from the start of step 4, labelled `crni-paper-fit new`):
- 17 Pugliese 1970 activity states that lie in the γ field by the paper's own Table III γ limits (25–45 at.% Cr, 1073–1448 K):
  expected FCC_A1, penalize BCC_A2 (+ LIQUID; + CRNI2 at T ≥ 895 K); basis "phase from the same paper's γ limits", assumed, option C
  (σ 1000, τ 100, confidence 0.5). Table II prints no phase per row, so this is an inference and is labelled so.
- fcc Curie-temperature marks (Hao Fig. 13(a), experimental, cited sources; single reader) with T ≥ 298.15 K (SGTE validity): expected
  FCC_A1, penalize BCC_A2, CRNI2, LIQUID (the export's stable_elsewhere list), option C.
Not added: Hao Fig. 16 boundary marks (CrNi2 + fcc, bcc + fcc; single-reader figure marks, CrNi2 composition spread 0.65–0.76 against a
stoichiometric model); ORCHID model-class CrNi2 temperatures 807/820/863 K (calculated stays out).

## Multistart, checks and ranking at every step
- ≥ 6 starts per step: start 0 = previous accepted step; starts 1–7 perturbed (a·(1 + 0.1 N), b + N(0, 3 J/K); seeded), plus at step 2
  the one-shot without S_ex. L-BFGS-B in q = θ/scale (a/1000, b/1), analytic ESPEI-grad gradient, jitter retry and FD fallback logged
  (fit.py). Objective = ESPEI log-likelihood + hinge (step 4) + a weak Normal prior centred at the one-shot (sd 50 kJ/mol on a, 30 J/mol/K
  on b), the rebuild's prior form, kept so that the Laplace step has a proper posterior.
- After every fit: diagram 600–2200 K (pycalphad-referenced hull construction, 2 K steps, 1201 x points; CRNI2 as a point at 2/3),
  topology check, pure-element check (stable phase of pure Cr and Ni vs SGTE across T; endpoint G equals SGTE to < 1e-6 J), energy shifts
  of every one-shot observation in units of its σ.
- Accepted topology (stated before ranking): below T_CrNi2 (window 800–930 K): bcc | bcc+CrNi2 | CrNi2 | CrNi2+fcc | fcc (peritectoid) or
  with an fcc window at 2/3 (congruent ordering, then eutectoid); T_CrNi2..T_eut: bcc | bcc+fcc | fcc; T_eut (1560–1680 K)..1728:
  bcc | bcc+L | L | L+fcc | fcc; 1728..2180: bcc | bcc+L | L; above: L. No same-phase gap in the stable diagram, no spurious field.
- Ranking (0.3), thresholds stated now: (1) plausible energies — every one-shot solid/compound observation within 10 kJ/mol-atom of its
  one-shot value at 298 K; |b| of the solutions ≤ 10 J/mol-atom/K per x(1−x) unit (|S_ex(0.5)| ≤ 2.5 J/mol-atom/K); liquid S_ex within
  3u; thermochemistry RMSE by dataset within ~2σ of its own σ; pure elements = SGTE. (2) topology as above, spurious-field severity
  by temperature. (3) quantitative: eutectic T within 25 K of 1618 K, CrNi2 ordering within 25 K of 863 K, then residuals by dataset.

## Physics checks (end)
Liquid convexity (∂²G/∂x² > 0 for LIQUID over 1400–2200 K, no spurious liquid gap); bcc metastable gap: fitted chemical spinodal
top, regular-solution estimate from the fitted and MLIP/DFT Ω (with SRO 0.79, vibrational entropy as set H), and Cahn's coherent term
from `cr-ni-coherent-20261105/results.json` (k = η²YV_m, base/low/high); convexity term (0.4b) only if a same-phase gap appears at observed
single-phase bcc states and both estimates make it unlikely — otherwise left to the data and reported; unary limits.

## Cheap UQ (no MCMC)
At the final step: distinct optima from the multistart (+ starts from perturbations of the pick), Laplace at each mode (central
differences of the analytic gradient, two step sizes; soft-direction repair as in `laplace/scripts/hessian_mode.py`), mixture weights
∝ exp(logpost) |Σ|^½, 1000 classified draws from the mixture: P(accepted topology), P(single-phase fcc at x_Ni 0.52, 1473 K),
lowest liquid T, CrNi2 top T; independent-marginal counterexample. As `cr-ni-rebuild-20261105/laplace/REPORT.md`.

## Wall-time estimate
Set E evaluations took ~2 s (value + gradient) per core; with ~450–700 observations here, ~2–4 s on a loaded Studio. A start needs
300–1500 evaluations → 0.3–1.5 h; 6–8 starts on 4 workers per step → ~1–3 h per step, ~5–9 h for steps 2–4, Laplace ~0.5 h, propagation
~0.5 h. Below the ~12 h stop mark. Each start has a wall budget (5400 s), reported if hit.

## Outputs
`steps/<step>/` (run cards with `espei.__version__`, interpreter, data-file hashes; multistart.json; per-start TDBs), `tdb/` (step picks),
`figures/` (computed diagrams only, house style `<home>/projects/2026_arroyave_nicr_paper/scripts/style.py`), `results/*.json`
(data_consistency, per-step summaries, ranking, physics checks, Laplace and mixture).

## Run log (appended during the run, 6 Nov)
- Step 2: 9 starts, one mode (logpost −1703.68). The mechanical ranker put s2 first on a 1-temperature grid difference (12 vs 13
  off-sequence temperatures) although s2 had not fully converged (|g| 0.011); the pick is the converged best start of the same mode (s7).
- Step 3a (CRNI2 fixed at its one-shot value, as first planned): broke the topology (CRNI2 stable to 1828 K, above the liquidus;
  eutectic 1652 K; FCC_A1 L1 driven to +131 kJ). Reported, not continued. Cause: 0.1 "held: one-shot energies kept through their
  assigned uncertainty (observations, not a penalty)" was implemented as fixed for CRNI2.
- Step 3b: same data, CRNI2 a, b free and held only by its one-shot HM_FORM observation (σ 9.7 kJ) — the protocol's own wording; one
  mode in 7 of 8 starts; eutectic 1626 K, CrNi2 top 1074 K. Step 4 starts from 3b.
- First step-2 launch stopped (own PIDs) after 5 s: model.py carried crni.py's SETUPTOOLS_SCM_PRETEND_VERSION, which hid the commit in
  espei.__version__; removed, every run card shows 0.8.11.dev82+g9039ea215. First step-3 launch failed on a start-TDB file name.
- UQ draws are classified on a 5 K grid (as the set E propagation), 4 processes.
