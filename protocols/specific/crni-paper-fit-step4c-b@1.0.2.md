# Cr-Ni liquidus-first fit from the PhaseForge one-shot to the step-4 pick step4c-b s4 (hinge floor; 10a kink rule; 10c global search; step4c_b_hingefloor_pick.tdb; reproduce plan fixed; evaluated states corrected)

`crni-paper-fit-step4c-b@1.0.2` · specific protocol · status **approved** · licence CC-BY-4.0

> 1.0.2, APPROVED by the PI on 7 Nov 2026 ("Yes"; decision row of that date). The approval is recorded in place, as the draft notes of 1.0.0-1.0.2 provide (status draft until the PI approves): only status, status_note, decisions and the pointer reproducibility.independent_rerun (to the 1.0.2 rerun directory) changed, no version bump; it still instantiates orchid-calphad-fit@2.1.0, the general version the fit ran under (2.1.1 only re-pins the rationale for the 7 Nov single-source definition, which the fit already followed). Identical to 1.0.1 (kept unchanged) except the evidence pins of states and states_evaluated (bundle 1.1.0; changelog 1.0.2): the fit inputs, objective and artifact are unchanged. Same science as 1.0.0; the reproduce plan and its pins were fixed in 1.0.1. Reproduces the Cr-Ni pick tdb/step4c_b_hingefloor_pick.tdb (unchanged from 0.2.0-draft). New in 1.0.0: step 3b re-evaluated under fit_protocol 10a with the kink rule on both machines (pick s1_perturbed, kink-stationary = the TDB step 4c-b started from), step 4c-b 10a on both machines (8 of 8 smooth, pick s4), 10c basin hopping and dual annealing from s4 (seed 7201, 1500 evaluations each; no better optimum), and an independent scripted rerun on spark1.

## Purpose

Rebuild the Cr-Ni TDB tdb/step4c_b_hingefloor_pick.tdb from its inputs: the PhaseForge one-shot (128-atom m_scraps SQS over the whole range, staged relaxation with GRACE-2L-SMAX-OMAT-large and the relaxation midpoint rule for the anchors, 100 ps liquid MD at 1900 and 2200 K with the corrected Hong-Liu entropy), set E Cr-Ni data with ORCHID-rule sigmas, two ORCHID records (eutectic ORC-SV7H3CNRYS, CrNi2 ordering ORC-X3KVP7D3PO), excluded phases at every observed state with per-phase certainty tiers, per-record ZPF scales sigma_DF floored at the tier, the hinge floor sigma = max(tier, converted state uncertainty), the smooth hinge onset, 17 kinetically limited CrNi2 absences suspended, and the sequence step 2 -> 3b -> 4c-b with gradient ESPEI on the Studio, followed by the physics checks and the Laplace-mixture UQ.

## Instantiates

- `orchid-calphad-fit@2.1.0` — `<orchid-sage>/protocols/general/orchid-calphad-fit@2.1.0.yaml` (sha256 `d3b4aedabbfbaf55…`, local)

## Artifact

- tdb: `<home>/ScientificRuns/crni-paper-fit-20261106/tdb/step4c_b_hingefloor_pick.tdb` (sha256 `3692243331691fd6…`, local)
- produced_by `crni-paper-fit-step4c-b@1.0.2`

## Inputs

- **oneshot_results** — PhaseForge one-shot energetics and liquid results (crni-phaseforge-20261105) (local)
  - `<home>/ScientificRuns/crni-phaseforge-20261105/results/solids_GRACE-2L-SMAX-OMAT-large.json` (sha256 `1a254993067fb230…`, local) — staged SQS energies (value potential)
  - `<home>/ScientificRuns/crni-phaseforge-20261105/results/solids_GRACE-2L-OMAT.json` (sha256 `ba7e4dc6fc171a9e…`, local) — cross-check potential
  - `<home>/ScientificRuns/crni-phaseforge-20261105/results/liquid_checks_enthalpy.json` (sha256 `88bc894ceada3bfe…`, local) — liquid H_mix 1900/2200 K
  - `<home>/ScientificRuns/crni-phaseforge-20261105/results/liquid_excess_entropy.json` (sha256 `8f8c1869df94e0ae…`, local) — liquid S_ex (provisional)
  - `<home>/ScientificRuns/crni-phaseforge-20261105/results/liquid_ideal_mixing_check.json` (sha256 `7df7b32826ab40be…`, local) — ideal-mixing check
  - `<home>/ScientificRuns/crni-phaseforge-20261105/results/oneshot_tdb.json` (sha256 `51ab0531d7300f6e…`, local) — one-shot build record
  - `<home>/ScientificRuns/crni-phaseforge-20261105/tdb/CrNi_PhaseForge_oneshot_Sex_GRACE-2L-SMAX-OMAT-large.tdb` (sha256 `84ec5ae41a42650e…`, local) — one-shot TDB with S_ex (start)
  - `<home>/ScientificRuns/crni-phaseforge-20261105/tdb/CrNi_PhaseForge_oneshot_GRACE-2L-SMAX-OMAT-large.tdb` (sha256 `108378d67447667b…`, local) — one-shot TDB without S_ex (comparison start)
- **unaries** — SGTE91 unaries of the Kunselman et al. Cr-Ni model form (LIQUID, BCC_A2, FCC_A1; no magnetic terms) (local)
  - `<home>/ScientificRuns/cr-ni-rebuild-20261105/inputs/cr-ni-model.tdb` (sha256 `f9a7769eb204a825…`, local)
- **mlip_weights** — GRACE potentials (hash list) (public)
  - `<home>/ScientificRuns/crni-phaseforge-20261105/provenance/potential_sha256.txt` (sha256 `bd774abc6bb5ffc1…`, local)
- **sigma_mlip** — sigma_MLIP = 9.687 kJ/mol-atom (local)
  - `<home>/projects/orchid-phaseforge-demo/results/sigma_mlip.json` (sha256 `deb9e596c03bc640…`, local)
- **set_e** — set E Cr-Ni datasets with ORCHID-rule sigmas and the set E hinge (cr-ni-rebuild-20261105) (local)
  - `<home>/ScientificRuns/cr-ni-rebuild-20261105/inputs/derived/setE_orchid_sigmas/BUILD_LOG.json` (sha256 `546a0fb42cc4f4cb…`, local) — build log with the sigma basis per file
- **orchid_records_restricted** — private ORCHID exports read for the CrNi2 ordering record, the eutectic, Pugliese gamma states and Curie marks (restricted)
  - `<home>/data/private/crni-assessment-export-20261105/records.jsonl` (sha256 `bb4aab0d9f917b4d…`, restricted) — Hao et al. 2021 assessment export (ORC-X3KVP7D3PO; Curie marks of Fig. 13(a)); hash only
  - `<home>/data/private/crni-pugliese-export-20261105/records.jsonl` (sha256 `c1d698974d373b27…`, restricted) — Pugliese & Fitterer 1970 export (Table II states, Table III limits); hash only
- **coherent_inputs** — Cahn coherent-strain inputs (k = eta^2 Y V_m; base/low/high) (local)
  - `<home>/ScientificRuns/cr-ni-coherent-20261105/results.json` (sha256 `c7d7369ef5944b00…`, local)
- **step4c_inputs** — step-4c data build (tiers3, per-record sigma_DF, completed exclusions, hinge floor) - derived files of the campaign (local)
  - `<home>/ScientificRuns/crni-paper-fit-20261106/results/step4c_build.json` (sha256 `fea24302a699a357…`, local) — step-4c build record
  - `<home>/ScientificRuns/crni-paper-fit-20261106/results/tiers3.json` (sha256 `509c66c81a04cdc7…`, local) — per-excluded-phase tiers
  - `<home>/ScientificRuns/crni-paper-fit-20261106/results/zpf_sigma_conversion.json` (sha256 `b52523f841d01883…`, local) — per-record sigma_DF
  - `<home>/ScientificRuns/crni-paper-fit-20261106/results/hinge_observed_sigma.json` (sha256 `66a38330f4c693da…`, local) — converted state uncertainty per (state, excluded phase)
  - `<home>/ScientificRuns/crni-paper-fit-20261106/results/step4c_b_hinge_floor.json` (sha256 `8f7dd81cd84c61cf…`, local) — hinge floor - 868 of 878 scales raised
  - `<home>/ScientificRuns/crni-paper-fit-20261106/data/hinge/step4c_hinge_floor.json` (sha256 `4ab667e875b304bf…`, local) — hinge sidecar read by the objective
  - `<home>/ScientificRuns/crni-paper-fit-20261106/results/check10a_step4c_b_hingefloor.json` (sha256 `97799d5164702165…`, local) — fit_protocol 10a with the kink rule (PI 6 Nov, 6b8f443): 8 of 8 smooth and kink-stationary, 8-11 on-boundary ZPF vertices per endpoint all within their own sigma, no failed equilibria; pick s4 (scripts/check10a.py, kink10a.py)
  - `<home>/ScientificRuns/crni-paper-fit-20261106/results/check10a_step4c_b_hingefloor_spark1.json` (sha256 `fa47f2386c86fe78…`, local) — 10a with the kink rule on spark1 (scripts/check10a_ms.py): identical kinds, pick s4, gap 1.867e-9
  - `<home>/ScientificRuns/crni-paper-fit-20261106/results/check10a_step3b_original_campaign.json` (sha256 `b3d340ef5cc67323…`, local) — step 3b under 10a with the kink rule, original campaign starts (Studio): pick s1 kink-stationary = start TDB of step 4c-b
  - `<home>/ScientificRuns/crni-paper-fit-20261106/results/check10a_step3b_polished_spark1.json` (sha256 `564f8a5918514654…`, local) — step 3b under 10a, polished starts of spark1: pick s1 (within 0.11 of the 10b tolerance of the start TDB)
  - `<home>/ScientificRuns/crni-paper-fit-20261106/results/check10a_step3b_polished_studio.json` (sha256 `58edc121344f65a6…`, local) — step 3b under 10a, polished starts of the Studio: pick s1, same start, 33x tolerance in flat directions, 0.0046 lower
  - `<home>/ScientificRuns/crni-paper-fit-20261106/results/global_10c_step4c_b_summary.json` (sha256 `b8673cf2e8a706df…`, local) — 10c summary (basin hopping and dual annealing from s4, seed 7201, 1500 evaluations each): no better optimum
  - `<home>/ScientificRuns/crni-paper-fit-20261106/results/check10a_step4c_b_10c_global_bests.json` (sha256 `ddde21027544f81f…`, local) — 10a check of the two global-search bests

## Code

- **snapshot** (file_set): orchid-sage (github orchid-calphad, private until release)
- **snapshot_addendum_1_0_0** (file_set): orchid-sage (github orchid-calphad, private until release)
- **snapshot_addendum_1_0_1** (file_set): orchid-sage (github orchid-calphad, private until release)
- **snapshot_steps_1_3b** (git): orchid-sage (github orchid-calphad, private until release) @ `94cc153`
- **phaseforgeplus** (git): <home>/src/PhaseForgePlus (local) @ `c66656faad884c7ed11354417bc89074665a74f3`
- **protocol_tools** (file_set): protocols/tools/ — entry points: orchid_reproduce.py, evaluate_states.py, build_evidence_bundle.py, tdb_header.py, run_with_fixed_date.py

## Environment

- **fit_env** (venv): <fit-env>; espei 0.8.11.dev82+g9039ea215, pycalphad 0.11.3.dev35+g9a6939dd2, numpy 2.5.4, scipy 1.18.1

## Overrides of the general protocol

| parameter | value here | general default | conforms | reason | source |
|---|---|---|---|---|---|
| certainty_tiers | per excluded phase (tiers3: 10 / 50 / 100 J/mol-atom); ZPF records 100, 50 when replicated (Karmazin 550 C and Zhang at 100); observed states at confidence 1.0 | certainty tiers per excluded phase (item 8) | yes | applied as written | results/tiers3.json; fit_protocol item 8 |
| hinge_sigma_floor | hinge sigma = max(tier, converted state uncertainty), converted at the step-4 s1 pick (build_hinge_observed.py; 868 of 878 scales raised) | max(tier, converted state uncertainty) at the previous accepted step | yes | the conversion was evaluated at the step-4 s1 pick (the then-current step-4 fit), not at the step-3b pick the fit started from | scripts/build_step4c_floor.py; results/hinge_observed_sigma.json |
| ZPF driving-force scale | per-record sigma_DF = sqrt((|dS| sigma_T)^2 + (G'' sigma_x |dx|)^2), floored at the record tier | weights from uncertainties (item 8 per-record ZPF scale) | yes | applied as written | results/zpf_sigma_conversion.json |
| hinge onset | smooth (softplus) onset of width sigma/5 | smooth hinge (item 8) | yes | applied as written | steps/configs/step4c_b_hingefloor.json hinge_smooth |
| kinetically limited absences | CRNI2 exclusions dropped at 17 short-anneal states below 900 K; 12 Jette/Karmazin rows below 900 K enter as metastable bcc+fcc with CRNI2 suspended (data/zpf_susp) | item 8 kinetically limited absences | yes | applied as written; recorded as a decision | steps/configs/step4c_b_hingefloor.json note; scripts/model2.py |
| phases | LIQUID, BCC_A2, FCC_A1 (disordered), CRNI2 stoichiometric 1:2 (Pt2Mo type) on SGTE fcc references; no FCC_L12; no magnetic terms | disordered unless evidence requires ordering | yes | PI decision 6 Nov (FCC_A1 only); CrNi2 is a known ordered compound | crni-phaseforge-20261105 PLAN.md "PI decision (6 Nov) - disordered fcc only" |
| liquid temperatures | 2200 K (primary) and 1900 K (secondary); 864-atom check at x_Ni 0.5, 2200 K | one T just above the highest melting point | yes | 1900 K tests the temperature dependence; pure Cr crystallised at 1900 K after 82 ps and is analysed over 80 ps | crni-phaseforge-20261105 PLAN.md |
| prior | weak Normal prior centred at the one-shot (sd 50 kJ/mol on a-terms, 30 J/mol/K on b-terms) | none stated | yes | kept so that the Laplace step has a proper posterior (the rebuild's prior form) | PLAN.md multistart section; scripts/model2.py |
| step-2 free set | 12 symbols (liquid, bcc, fcc a,b); CRNI2 a,b NOT free in step 2 | every phase free (held = anchored) | **no** | planned before the 6 Nov rule; step 3a showed fixing CrNi2 breaks the topology; step 3b and 4c-b free it | steps/configs/step2_liquidus.json; PLAN.md run log |
| step-2 pick | s7_perturbed (converged best start of the single mode) | ranker pick | yes | the mechanical ranker chose s2 on a 1-temperature grid difference although s2 had not converged (|g| 0.011) | PLAN.md run log |
| step-3b pick | s1_perturbed (campaign ranker of 6 Nov), confirmed by 10a with the kink rule (kink-stationary; pick on the original starts and on the polished starts of both machines) | fit_protocol 10a (smooth or kink-stationary) | yes | every step-3b endpoint is a kink (Q39); under the PI kink rule of 6b8f443 s1 is eligible and has the highest objective among eligible starts | results/check10a_step3b_*.json; run card crni-step3b-check10a |
| 10a boundary-point uncertainty | |r| <= sigma of that residual (ZPF driving force or activity) as "within its own uncertainty" | each on-boundary data point within its own uncertainty of that boundary (fit_protocol 10a) | yes | agent operational reading (labelled); all on-boundary points have |r|/sigma <= 0.70 | scripts/kink10a.py |
| 10c settings | basinhopping T 25, stepsize 0.05, niter 100, accept test bounds + liquid convexity 600-2200 K; dual_annealing initial_temp 5230, x0 = local best; seed 7201; 1500 value+gradient evaluations per method; z = (theta - theta_s4)/scale in [-5, 5] (+-5 kJ/mol, +-5 J/mol/K); local L-BFGS-B with the analytic gradient, <= 50 evaluations per local solve | fit_protocol 10c (cuzr-protocol-20261104 run_global.py, optimizer_plan.json) | yes | box, local solver (L-BFGS-B as the Cr-Ni multistart and orchid-automated-assessment@0.1.0) and liquid test are agent adaptations stated in PLAN.md before launch (labelled) | PLAN.md addendum; scripts/run_global_crni.py |
| accepted topology | stated in PLAN.md before ranking (bcc | bcc+CrNi2 | CrNi2 | CrNi2+fcc | fcc below T_CrNi2 in 800-930 K; eutectic 1560-1680 K; no same-phase gap; no spurious field) | R2 | yes | stated before ranking | PLAN.md |
| plausibility thresholds | one-shot solid/compound within 10 kJ/mol-atom; |S_ex(0.5)| <= 2.5 J/mol-atom/K for bcc/fcc; liquid S_ex within 3u; thermochemistry RMSE by dataset within ~2 sigma; pure elements = SGTE | R1 | yes | stated before ranking | PLAN.md |
| low_temperature_hull_states | not applied (no 0 K convex-hull states in the data) | fit_protocol 8b (0 K convex hull as low-temperature stability evidence for phases close to the hull; orchid-sage f42412e, pinned in orchid-calphad-fit@2.1.0) | **no** | item 8b postdates the Cr-Ni freeze (1.0.0, 5bede65) and the PI ruled it out for Cr-Ni | PI 6 Nov 2026 (coordinator brief for 1.0.1) |
| liquid entropy estimator | corrected Hong-Liu chemical term (hongliu_mixing.py) + the campaign VACF estimator (pre-PR scripts) | MLIPentropy (PhaseForge PR #11, a08ff3e) | yes | the Cr-Ni liquid analysis (5-6 Nov) predates the packaged MLIPentropy; Cu-Zr validation agreed within 0.1 J/mol-atom/K | crni-phaseforge-20261105 PLAN.md; cuzr-protocol-oneshot PLAN.md Run 2 item 2 |

## Evidence selection

- ORCHID: set E (cr-ni-rebuild-20261105, ESPEI-format Cr-Ni datasets with ORCHID-rule sigmas) + ORCHID records from private exports @ `none (not a git checkout; every file hashed in the run card)`; query: set E files split by phase content into data/{liq_c,solid_c,zpf_susp,thermo,oneshot_relax} (step-4c build); + ORC-SV7H3CNRYS (eutectic, accepted) and ORC-X3KVP7D3PO (CrNi2 ordering, single reader)
- manifest: `<home>/ScientificRuns/crni-paper-fit-20261106/results/step4c_build.json` (sha256 `fea24302a699a357…`, local)
- evidence digest `dac8043938d25f42611f0e287819ccce4a1abb67f7f22cfe089c3d97998b054e` from `<orchid-sage>/protocols/run_cards/crni-step4c_b_hingefloor.json` (sha256 `6abdca1d7a071796…`, local)

**Exclusions**

- Hao Fig. 16 boundary marks (CrNi2 + fcc and bcc + fcc): single-reader figure marks; CrNi2 composition spread 0.65-0.76 against a stoichiometric model — PLAN.md step-4 exclusions paragraph
- ORCHID model-class CrNi2 temperatures 807/820/863 K: calculated stays out — PLAN.md
- L1_2 / L1_0 / D0_22 ordered fcc cells: computed, NOT USED (PI 6 Nov: disordered FCC_A1 only) — crni-phaseforge-20261105 results/NOT_USED.md
- CRNI2 exclusions at 17 short-anneal states below 900 K: kinetically limited absences (PI 6 Nov, item 8): another source reports CrNi2 there — steps/configs/step4c_b_hingefloor.json

**Labelled interpretations**

- BCC_A2 exclusions at 17 Pugliese 1970 activity states: phase from the same paper's Table III gamma limits (Table II prints no phase per row); assumed — scripts/build_hinge.py; build_hinge_complete.py
- fcc Curie-temperature marks (Hao Fig. 13(a)) as single-phase fcc states at T >= 298.15 K: expected FCC_A1; penalize BCC_A2, CRNI2, LIQUID; single reader — scripts/build_hinge.py
- CrNi2 ordering at 863 K (ORC-X3KVP7D3PO): ZPF CRNI2 (x 2/3) + FCC_A1 at zero phase fraction; CRNI2 excluded above it — scripts/build_data.py; scripts/build_hinge_complete.py
- eutectic 1618 K (ORC-SV7H3CNRYS): three-phase ZPF with the printed compositions — scripts/build_data.py
- partial tie-lines of set E: (i) known phase + (ii) ZPF vertex pair with a null partner composition (fit_protocol 0.4a) — scripts/build_data.py
- 12 Jette/Karmazin rows below 900 K: metastable bcc + fcc with CRNI2 suspended (data/zpf_susp, evaluated without CRNI2) — scripts/model2.py; scripts/build_step4c_v2.py

**Single-reader records**

- CrNi2 ordering record (ORC-X3KVP7D3PO): single reader, not yet accepted; enters labelled (PI 6 Nov: second reading before release, not before fitting)
- fcc Curie marks of Hao Fig. 13(a): single reader; enters labelled
- Pugliese gamma assignments: inference from Table III limits; PI to confirm as data

## Run sequence (failed attempts and side branches kept)

| run | step | status | starts | pick | from | summary |
|---|---|---|---|---|---|---|
| `crni-oneshot-solids-liquid` | `staged_relax` | accepted |  |  |  | solids both potentials, 128-atom SQS over the whole range; liquid 100 ps at 1900/2200 K; ideal-mixing check passed |
| `crni-oneshot-build` | `build_oneshot_tdb` | accepted |  |  |  | one-shot TDBs with and without S_ex; VV base |
| `crni-data-build` | `build_datasets` | accepted |  |  |  | build_data.py, build_hinge.py, data_consistency.py (steps 2-3b inputs; outputs hashed via the step run cards) |
| `crni-step1_oneshot` | `oneshot_diagram` | accepted |  |  |  | Cr-rich fcc too stable; liquid down only to 1730 K; CrNi2 to 1156 K; pure elements exact |
| `crni-step2_liquidus` | `fit_liquidus` | accepted | 9 | s7_perturbed | crni-step1_oneshot | one mode (logpost -1703.68); eutectic 1616 K; CrNi2 (not free) to 1664 K |
| `crni-step3_thermo` | `fit_thermo` | failed | 8 | s4_perturbed | crni-step2_liquidus | CRNI2 fixed: CrNi2 stable to 1828 K above the liquidus; reported, not continued |
| `crni-step3b_thermo_crni2free` | `fit_thermo` | accepted | 8 | s1_perturbed | crni-step2_liquidus | CRNI2 free, anchored at sigma 9.7 kJ: one mode in 7/8; eutectic 1626 K; CrNi2 top 1074 K |
| `crni-step4_solid` | `fit_solid` | superseded | 8 | s1_perturbed | crni-step3b_thermo_crni2free | the 0.1.0-draft pick (CrNi2 top 780 K) |
| `crni-step4c-data-build` | `build_datasets` | accepted |  |  |  | build_hinge_complete.py, build_tiers3.py, build_zpf_sigma.py, build_hinge_observed.py, build_step4c_v2.py, build_step4c_floor.py: data/{liq_c,solid_c,zpf_susp,oneshot_relax}, data/hinge/step4c_hinge_floor.json (no run cards; every output hashed in the step-4c-b run card) |
| `crni-step4c_b_hingefloor` | `fit_solid` | accepted | 8 | s4_perturbed | crni-step3b_thermo_crni2free | logpost -5657.2886; 8 of 8 starts converged (|g|_q 4.5e-05 to 9.9e-04, all < 1e-3; 10a with the kink rule (PI 6 Nov): 8 of 8 smooth, each also kink-stationary (0 violations in 46 directions x 3 steps); on-boundary data points: 8 ZPF vertices (Jenkins 1937, Svechnikov 1962; 11 at s5), |r|/sigma <= 0.007; no failed equilibria; results/check10a_step4c_b_hingefloor.json) in one mode (spread 4.5e-03); eutectic 1614 K, CrNi2 top 860 K |
| `crni-step3b-check10a` | `pick_thermo` | accepted |  |  | crni-step3b_thermo_crni2free | 10a with the kink rule: 0 smooth / 3 kink / 5 not stationary on each of three start sets (original, polished Studio, polished spark1); pick s1_perturbed in all three; original s1 = start TDB of step 4c-b; 5 on-boundary data points, |r|/sigma <= 0.70; no failed equilibria |
| `crni-step4c_b-check10a` | `pick_solid` | accepted |  |  | crni-step4c_b_hingefloor | 8 of 8 smooth on the Studio and spark1; pick s4_perturbed; gap 1.9e-9 |
| `crni-step4c_b-10c-basin` | `fit_solid` | accepted |  |  | crni-step4c_b-check10a | basin hopping from s4, seed 7201, 1500 evaluations (budget reached, ~30 hops, 31 local solves, 0 invalid): best = s4 (+8e-12 log-units, 3.4e-5 J/mol away) |
| `crni-step4c_b-10c-anneal` | `fit_solid` | accepted |  |  | crni-step4c_b-check10a | dual annealing from s4, seed 7201, 1500 evaluations (budget reached, 2 local solves, median visited logpost -9573): best = s4 (+5e-12, 3.6e-5 J/mol away); pick by 10a over multistart + both global bests stays s4 |
| `crni-step5-physics-residuals` | `physics_checks` | accepted |  |  | crni-step4c_b_hingefloor | results/physics_step4c_b.json, per_dataset_step4c_b_hingefloor.json (no run cards) |
| `crni-uq-laplace-step4c_b` | `laplace` | accepted |  |  | crni-step4c_b_hingefloor | weights 0.766 / 0.234 (A_s4 / A2_s5_flat, same basin); P(accepted topology) 0.989, P(CrNi2 within 25 K of 863 K) 0.871 |

## Acceptance target

Reproduced when (1) the deterministic files (data/<group>/, data/hinge/step4c_hinge_floor.json, configs) are byte-identical to the hashes in the step-4c-b run card; (2) rerunning step 4c-b from the step-3b pick with the same build gives a 10a pick (named by the rule - eligible starts, then the objective - never by its start label) with logpost within 0.01 of -5657.2886, eligible under 10a (smooth or kink-stationary), judged by its predictions (PI 6 Nov 2026, "this is too strict"); its parameters are compared with 50 J/mol (a-terms) and 0.03 J/mol/K (b-terms) (fit_protocol 10b) and reported as a note, the flat directions of the basin (where the recorded minima A_s4 and A2_s5_flat differ by more than these tolerances) as undetermined; start and mode labels, cache files, timestamps and environment details that do not change a prediction are notes, never failures; byte checks only for data identity (staged inputs, evidence bundle, evaluated states); (2b) 10c from the rerun's 10a pick (seed 7201, 1500 evaluations per method) finds no point more than 0.01 above it; (3) the reproduced diagram over 600-2200 K has the same phase sequence on heating at every x of a 0.01 grid, eutectic within 2 K of 1614 K and CrNi2 top within 2 K of 860 K (pd4 grid, 2 K steps); (4) pure elements exact; (4b) thermochemistry at the 10a pick: every data/thermo dataset with rms residual/sigma within 0.1 of the recorded pick; (5) the Laplace mixture weight of the main mode within 0.01 and P(accepted topology) within 0.03 with new draws.

- logpost of the s4 start: absolute 0.01 log-units
- best logpost of each 10c run: absolute 0.01 log-units
- fitted a-terms of the pick (J/mol): absolute 50 J/mol
- fitted b-terms of the pick: absolute 0.03 J/mol/K
- eutectic and CrNi2 top temperatures: absolute 2 K
- phase sequence on heating 600-2200 K on a 0.01 grid: categorical_identical
- thermochemistry: rms residual/sigma of each data/thermo dataset at the 10a pick: absolute 0.1 
- Laplace mixture weight of the main mode: absolute 0.01 
- P(accepted topology) from 1000 new draws: absolute 0.03 

## Reproduce

python3 protocols/tools/orchid_reproduce.py protocols/specific/crni-paper-fit-step4c-b@1.0.2.yaml --root NEW_DIR --python PY --pfp PFP_SRC --nproc 4 --report REPORT.json (REPRODUCE.md)

Expected byte-identical: data/<group>/*.json and data/hinge/step4c_hinge_floor.json as in the step-4c-b run card; every run card conversion

Not reproducible byte for byte:

- Steps 1-3b: reproduced by crni-paper-fit-step4-s1@0.1.0-draft (unchanged); the step-3b pick does not meet 10a and its intermediate pick is machine-dependent (Q36, Q39); this plan starts from the frozen step-3b pick TDB in the bundle
- MLIP solids and liquid MD on the GPU (spark1): within the tolerances only; container digest not recorded
- 10c on another machine: the scipy streams are seeded, but the objective differs in the last digits across architectures, so the global trajectories are compared by their best objective, not evaluation by evaluation
- Restricted inputs (two private exports) cannot be redistributed; a third party needs the ORCHID records they produce (ORC ids listed) or the papers

## Decisions

| date | who | decision | why | source |
|---|---|---|---|---|
| 2026-11-05 | PI | SGTE references for every end-member including fcc Cr (7.3 kJ); no inflection detection | compatibility with existing databases | crni-phaseforge-20261105 PLAN.md "PI ruling on references (5 Nov)" |
| 2026-11-05 | PI | ordered fcc cells computed for the record; then disordered FCC_A1 only (6 Nov) | CrNi2 is the real ordered phase; no evidence for a partitioned L1_2 | crni-phaseforge-20261105 PLAN.md |
| 2026-11-06 | PI | bcc and fcc SQS over the whole composition range | each RK fit extrapolated over half the range | crni-phaseforge-20261105 PLAN.md "Extension (PI decision, 6 Nov)" |
| 2026-11-06 | PI | "held" never means fixed: CRNI2 free in step 3b and 4, anchored by its one-shot HM_FORM at sigma 9.7 kJ — “held never means fixed” | step 3a with CRNI2 fixed left it stable above the liquidus | PLAN.md run log; fit_protocol 0.1 |
| 2026-11-06 | agent | step-2 pick s7_perturbed instead of the ranker's s2_perturbed | s2 not converged (|g| 0.011); the ranker's choice rested on a 1-temperature grid difference | PLAN.md run log |
| 2026-11-06 | PI | excess electronic entropy of the liquid taken as zero (assumption) | metallic liquid | PLAN.md model section; memory hong-liu-entropy-correction |
| 2026-11-06 | PI | single-reader records (Curie marks; CrNi2 at 863 K) may enter the fit labelled; a second reading before release | avoid blocking the fit | memory exclusions-required-held-free |
| 2026-11-06 | PI | test the ZPF driving-force sigma from each record's sigma_T on Cr-Ni only (one measured change) | CrNi2 83 K miss attributed to the default 1000 J/mol scale | REPORT.md open decision 1; memory exclusions-required-held-free item 3 |
| 2026-11-06 | agent (reported to the PI) | step-4 pick = s1_perturbed (main mode; logpost -6332.2437; 4 of 8 starts) | protocol 0.3 ranking of evaluate.py; the higher-objective modes were absent in the original run; under fit_protocol 10a the same mode is picked (5 eligible starts) | REPORT.md Pick; steps/step4_solid/evaluation.json |
| 2026-11-06 | PI | step-4 pick = step4c-b (step4c_b_hingefloor, start s4_perturbed); the hinge floor sigma = max(tier, converted state uncertainty) adopted as a protocol rule | 0 of 8 starts stationary without the floor (step4c), 8 of 8 with it, one mode, CrNi2 860 K vs 863 K observed | coordinator message 6 Nov 2026; fit_protocol item 8 (commit bef0bae) |
| 2026-11-06 | PI | per-record ZPF scale sigma_DF floored at the tier, smooth hinge onset (sigma/5), kinetically limited absences (CrNi2 suspended at short-anneal states) | Cr-Ni test: one mode in 8 of 8 starts, phase-boundary misfit halved, thermochemistry unchanged | fit_protocol item 8 (commit b31a0ca) |
| 2026-11-06 | PI | 10a accepts kink-stationary endpoints; central FD is not a gradient; failed equilibria are failures — “local kinks are inevitable” | local kinks are inevitable (data points on model phase boundaries) | fit_protocol 10a (orchid-sage 6b8f443) |
| 2026-11-06 | agent (labelled) | step 3b not refitted: its 10a pick (s1, kink-stationary) is the TDB step 4c-b started from | pick identical on the original starts and on spark1; the Studio-polished s1 differs only in flat directions and step 4 reaches the same optimum from either step-3b pick (Q36) | REPORT.md step 3b under the new 10a |
| 2026-11-06 | agent (labelled) | 10c adaptations: box z in [-5, 5] around s4 in the multistart scaling, L-BFGS-B local solver with <= 50 evaluations per solve, liquid convexity 600-2200 K as feasibility, objective -logpost, global runs launched from s4 before the 10a re-check of step 4c-b had finished on spark1 (the coordinator Studio check had already picked s4) | Cu-Zr scaled box; same local solver as the multistart; physics.py liquid check | PLAN.md addendum |
| 2026-11-06 | agent (labelled) | pick kept at s4 although the dual-annealing best is 5e-12 log-units higher | the two points are 3.6e-5 J/mol apart (rounding level; 10b tolerances 50 J/mol, 0.03 J/mol/K), both smooth under 10a; keeping s4 leaves the artifact TDB byte-identical | results/check10a_step4c_b_10c_global_bests.json |
| 2026-11-06 | agent (labelled) | version 1.0.0 frozen with status draft (approval is the PI's) | schema status approved means PI approval | this document |
| 2026-11-06 | agent (labelled) | new specific protocol id crni-paper-fit-step4c-b (version 0.2.0-draft, supersedes crni-paper-fit-step4-s1@0.1.0-draft) rather than a 0.2.0 of the old id | a specific protocol names ONE artifact; the old id names the step-4 s1 TDB, which stays reproducible under its own document | this document |
| 2026-11-06 | PI | fit_protocol item 8b (0 K convex hull as low-temperature stability evidence) is not applied to Cr-Ni — “we dont need the convex hull rule for Cr-Ni” | 8b postdates the Cr-Ni freeze (1.0.0, 5bede65); the data and objective of the pick stay as frozen | coordinator brief 6 Nov 2026 for 1.0.1 |
| 2026-11-06 | agent (labelled) | check10a judged at the 10a pick named by the rule (check10a_ms.py; pick10a.py), not at the label s4_perturbed; global_10c starts from that pick (results/pick10a_start.txt); the step4c_b label checks ([start=s4_perturbed] logpost, topology) moved to check10a; phase_sequence and pure_elements use the 10a pick TDB (tdb/step4c_b_hingefloor_pick10a.tdb) instead of the evaluate.py ranking pick | on spark1 start s4 fell into the flat neighbour mode A2 (1.0.0 rerun, failure 1-2); the pick of this protocol is the 10a pick, which evaluate.py does not compute | protocols/reproduce/crni-paper-fit-step4c-b-1.0.0-spark1/README.md; coordinator brief 6 Nov 2026 |
| 2026-11-06 | PI | the rerun verdict is judged by predictions only - objective, 10a pick (by rule), topology and phase sequence, eutectic and CrNi2 top, thermochemistry, pure elements and Laplace weight within tolerance; parameters in flat directions, mode and start labels, cache files, timestamps and environment details that do not change predictions are notes; environment pins cover the source files of the code that runs; strict byte checks only for data identity (staged inputs, evidence bundle, evaluated states) — “this is too strict” | the 1.0.0 spark1 rerun reproduced every prediction but the tool said FAIL | coordinator message 6 Nov 2026 (PI on the 1.0.0 rerun) |
| 2026-11-06 | agent (labelled) | thermochemistry enters the plan as item thermochemistry (per_dataset.py at the 10a pick; thermo_compare.py): every data/thermo dataset of the recorded per_dataset output present with the same number of points and |delta rms_z| <= 0.1; the 10b parameter comparison and the TDB text check stay in results/pick10a_rerun.json as notes | the PI lists thermochemistry among the judged predictions; 0.1 sigma is a tenth of each dataset's own uncertainty, above the 0.022 seen between the A and A2 modes in the 1.0.0 rerun; the staged root holds the data/thermo group only (the oneshot and ZPF groups of per_dataset.py are not staged under those names), so only thermochemistry is judged | scripts/thermo_compare.py; protocols/reproduce/crni-paper-fit-step4c-b-1.0.0-spark1/thermo_comparison_summary.json |
| 2026-11-06 | agent (labelled) | a parameter is undetermined at the 10b tolerance when the two recorded minima of the basin (modes_step4c_b.json, A_s4 and A2_s5_flat) differ by more than its tolerance (here bcc L0/L1 a,b, fcc L0/L1 a,b and CrNi2 b: VV0004-VV0011, VV0013); such parameters are reported, not failed; the other five must lie within 10b | operational reading of the PI rule that flat directions are reported as undetermined; the set comes from recorded data, not from the rerun | scripts/pick10a.py; coordinator brief 6 Nov 2026 |
| 2026-11-06 | agent (labelled) | PhaseForge+ source pin = the 9 files under src/ and pyproject.toml (README, tests, examples, .git and caches left out) | the run imports src/ only; pyproject.toml names the package; the 1.0.0 check pinned the full checkout including .pytest_cache and .ruff_cache (failure 4) | protocols/environment/pins/PINS.md |
| 2026-11-06 | agent (labelled) | instantiate a new general version orchid-calphad-fit@2.1.0 (rationale re-pinned, 10c step global_search) instead of editing 2.0.0 in place | editing 2.0.0 changes its hash and would break the instantiates pin of the frozen 1.0.0 (and of 0.2.0-draft, step4-s1 0.1.0-draft and cuzr-oneshot-h2-s7 0.1.0-draft); versions are never edited in place | this document |
| 2026-11-06 | agent (labelled) | version 1.0.1 kept at status draft (approval is the PI's) | schema status approved means PI approval | this document |
| 2026-11-07 | agent (labelled) | bug fix in build_evidence_bundle.py and new evidence bundle 1.1.0 (states@1.1.0.json sha256 b2a93c9de507ee9bae1e463df61dc4b7269a8eaa8017a45c0f710948012988a2, states_evaluated@1.1.0.json sha256 e24d0853de4ad38f1992f8dd1b669d55843ff08c556706308bbeffdb3e4f50ad, MANIFEST@1.1.0.json bundle_sha256 e5a035a379c50a2d81081cf0f6ce187340b321c651da872640d9f3a4efc60483); the evaluate_states reference is states_evaluated@1.1.0.json; bundle 1.0.0 and protocol 1.0.1 kept unchanged | (a) states_from_zpf took each vertex value raw and ignored its component: 183 of 496 ZPF vertices are given in x(CR), so 130 of 329 ZPF states sat at x(NI) = x(CR) (e.g. Svechnikov r011, bcc at x(CR) 0.662 placed at x(NI) 0.662); (b) a phase with an unknown vertex was placed at the record's other composition; (c) the bundle re-derived exclusion tiers with its own classifier (526 / 343 / 9) instead of the tiers the fit read from the hinge file (673 / 186 / 19, with the PI caveats). The fit read the data and hinge files directly: the objective and the TDB do not change (hinge_sigma_used = fit sigma for 878 of 878 pairs); only the derived state files and their evaluation change (match 424 of 695, was 404). The definition of single source in item 8 stays open for the PI (the hinge tiers are kept as the fit used them) | tier mismatch report of 7 Nov 2026 (coordinator scratchpad); sage_mcp/tests/test_evidence_bundle.py |
| 2026-11-07 | agent (labelled) | version 1.0.2 kept at status draft (approval is the PI's) | schema status approved means PI approval | this document |
| 2026-11-07 | PI | definition of single source in fit_protocol item 8 (exclusion certainty tiers) - ONLY the hard-coded single-source datasets, as the fit used: Pugliese & Fitterer, phases from the paper's own Table III limits (scripts/build_tiers3.py of crni-paper-fit-20261106); a dataset is single source when it is the only report of that measurement and is designated so in the plan before fitting, with its reason; no automatic rule that a state without a second source within 3 sigma is single source — “Yes (to: only Pugliese, as the fit used)” | the 7 Nov tier mismatch report left the definition open (the bundle classifier used a 3-sigma-neighbour reading, the fit the Pugliese designation); the ruling confirms the tiers the fit read (bundle 1.1.0 copies them: 673 / 186 / 19, of which 149 at 50 for single source), so nothing in this protocol, its bundle or its artifact changes | coordinator brief 7 Nov 2026; fit_protocol item 8 (orchid-sage 7ba6726); orchid-calphad-fit@2.1.1 |
| 2026-11-07 | PI | crni-paper-fit-step4c-b@1.0.2 approved — “Yes” | the PI approved the draft of 7 Nov (commit b10db2e): 1.0.1 with the corrected evidence pins (bundle 1.1.0) | coordinator brief 7 Nov 2026 |
| 2026-11-07 | PI | independent rerun of 1.0.2 on spark1 with orchid_reproduce.py from a fresh root (nproc 4, as for 1.0.1), judged by predictions (rule of 6 Nov); RO-Crate of 1.0.2 built into its own directory, the 1.0.0 crate kept | every approved specific protocol carries a passing independent rerun and a crate (full reproducibility standard) | coordinator brief 7 Nov 2026 (items 3 and 4; no verbatim quote relayed) |
| 2026-11-07 | agent (labelled) | approval recorded in place on 1.0.2 (status draft -> approved, status_note, these decision rows and the independent_rerun pointer; nothing else changed) and instantiates kept at orchid-calphad-fit@2.1.0 | the draft notes of 1.0.0-1.0.2 say the status stays draft until the PI approves, i.e. approval is a status change of the approved version, not a new version; 2.1.0 is the general version the fit and the 1.0.1 rerun ran under and its file is unchanged, so its pin still holds; moving to 2.1.1 would change this document's content for a rationale re-pin only | this document |

## Limitations

- Thermochemistry is judged on the 22 data/thermo datasets only; the one-shot anchors and ZPF groups of per_dataset.py are not staged under their group names and are covered by the objective, the diagram and the phase sequence.
- laplace_weights uses the recorded modes (modes_step4c_b.json), so it tests the Hessian and mixture code, not the mode finding (unchanged from 1.0.0).
- 10a applied as revised by the PI on 6 Nov (kink rule, 6b8f443): eligibility kind smooth for all 8 starts; the directional test is coordinate, +-gradient and 16 seeded random directions only (numpy default_rng(20261106)); "within its own uncertainty" read as |residual| <= sigma of the on-boundary data point (agent reading). An earlier agent check that used central FD as a corrected gradient (results/grad_verify_step4c_b_hingefloor.json) is superseded by this rule.
- Notes, not rejections (plausibility thresholds stated before ranking): fcc one-shot enthalpies moved +14.5 (x 0.25) and +11.4 kJ (x 0.5) (> 10 kJ) while fcc calorimetry is met; bcc S_ex(0.5) +2.96 J/mol-atom/K (> 2.5); liquid S_ex Cr75Ni25 2200 K at z -3.1 (> 3u).
- Strict topology flag false only for a BCC_A2 + LIQUID sliver at 2176 K (one grid temperature, above every stated window; severity high-T only); eutectic and CrNi2 window both met.
- Step 2 CRNI2 not free (planned before the held-is-free rule). Step 3b meets 10a only through the kink rule (every endpoint is a kink); its flat directions (bcc L1, CrNi2 a/b) are undetermined at 10b tolerance across machines (Studio-polished s1 33x tolerance).
- 10c: dual annealing fitted only 2 local solves into 1500 evaluations (most evaluations are visiting moves across the +-5 box); basin hopping made ~30 hops before the budget, all returning to the s4 basin. No global-optimality claim.
- The hinge-floor conversion was evaluated at the step-4 s1 pick, not at the step-3b start (recorded as an override, conforms).
- Liquid S_ex at 1900 vs 2200 K inconsistent with H_mix(T) (Cp_ex -16 vs +4.8 J/mol-atom/K, 6.5 sigma at x_Ni 0.25); read as sampling/reference error; no T^2 or T ln T term.
- Possible double counting - ORCHID eutectic vs Jenkins arrests; 6 duplicate row pairs in Jette kept.

## Open questions

See OPEN_QUESTIONS.md: Q05, Q10, Q11, Q12, Q25, Q26, Q27, Q36, Q39
