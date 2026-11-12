# Cr-Ni liquidus-first fit from the PhaseForge one-shot to the step-4 pick step4c-b s4 (hinge floor; step4c_b_hingefloor_pick.tdb)

`crni-paper-fit-step4c-b@0.2.0-draft` · specific protocol · status **draft** · licence CC-BY-4.0

> DRAFT. Reproduces the CURRENT Cr-Ni pick tdb/step4c_b_hingefloor_pick.tdb (PI decision 6 Nov 2026: step4c-b is the step-4 pick and the hinge floor is a protocol rule, fit_protocol item 8, bef0bae). Steps 1-3b are unchanged from crni-paper-fit-step4-s1@0.1.0-draft (same run cards, same files); step 4 is step4c_b_hingefloor. Draft until the PI approves it and an independent rerun has passed (Y32).

## Purpose

Rebuild the Cr-Ni TDB tdb/step4c_b_hingefloor_pick.tdb from its inputs: the PhaseForge one-shot (128-atom m_scraps SQS over the whole range, staged relaxation with GRACE-2L-SMAX-OMAT-large and the relaxation midpoint rule for the anchors, 100 ps liquid MD at 1900 and 2200 K with the corrected Hong-Liu entropy), set E Cr-Ni data with ORCHID-rule sigmas, two ORCHID records (eutectic ORC-SV7H3CNRYS, CrNi2 ordering ORC-X3KVP7D3PO), excluded phases at every observed state with per-phase certainty tiers, per-record ZPF scales sigma_DF floored at the tier, the hinge floor sigma = max(tier, converted state uncertainty), the smooth hinge onset, 17 kinetically limited CrNi2 absences suspended, and the sequence step 2 -> 3b -> 4c-b with gradient ESPEI on the Studio, followed by the physics checks and the Laplace-mixture UQ.

## Instantiates

- `orchid-calphad-fit@2.0.0` — `<orchid-sage>/protocols/general/orchid-calphad-fit@2.0.0.yaml` (sha256 `27b54fa9cd3f4fe5…`, local)

## Artifact

- tdb: `<home>/ScientificRuns/crni-paper-fit-20261106/tdb/step4c_b_hingefloor_pick.tdb` (sha256 `3692243331691fd6…`, local)
- produced_by `crni-paper-fit-step4c-b@0.2.0-draft`

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

## Code

- **snapshot** (file_set): orchid-sage (github orchid-calphad, private until release)
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
| step-3b pick | s1_perturbed (campaign ranker of 6 Nov) | fit_protocol 10a - converged starts only | **no** | no step-3b start meets 10a (Q36, Q39, DR-convergence-nonsmooth of 0.1.0-draft); step 4c-b starts from this TDB | OPEN_QUESTIONS Q36, Q39 |
| accepted topology | stated in PLAN.md before ranking (bcc | bcc+CrNi2 | CrNi2 | CrNi2+fcc | fcc below T_CrNi2 in 800-930 K; eutectic 1560-1680 K; no same-phase gap; no spurious field) | R2 | yes | stated before ranking | PLAN.md |
| plausibility thresholds | one-shot solid/compound within 10 kJ/mol-atom; |S_ex(0.5)| <= 2.5 J/mol-atom/K for bcc/fcc; liquid S_ex within 3u; thermochemistry RMSE by dataset within ~2 sigma; pure elements = SGTE | R1 | yes | stated before ranking | PLAN.md |
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
| `crni-step5-physics-residuals` | `physics_checks` | accepted |  |  | crni-step4c_b_hingefloor | results/physics_step4c_b.json, per_dataset_step4c_b_hingefloor.json (no run cards) |
| `crni-uq-laplace-step4c_b` | `laplace` | accepted |  |  | crni-step4c_b_hingefloor | weights 0.766 / 0.234 (A_s4 / A2_s5_flat, same basin); P(accepted topology) 0.989, P(CrNi2 within 25 K of 863 K) 0.871 |

## Acceptance target

Reproduced when (1) the deterministic files (data/<group>/, data/hinge/step4c_hinge_floor.json, configs) are byte-identical to the hashes in the step-4c-b run card; (2) rerunning step 4c-b from the step-3b pick with the same build returns the s4 start with logpost within 0.01 of -5657.2886, converged under 10a (|g|_q < 1e-3), and every parameter within 50 J/mol (a-terms) and 0.03 J/mol/K (b-terms) (fit_protocol 10b; or the pick TDB byte-identical, sha256 36922433...); (3) the reproduced diagram over 600-2200 K has the same phase sequence on heating at every x of a 0.01 grid, eutectic within 2 K of 1614 K and CrNi2 top within 2 K of 860 K (pd4 grid, 2 K steps); (4) pure elements exact; (5) the Laplace mixture weight of the main mode within 0.01 and P(accepted topology) within 0.03 with new draws.

- logpost of the s4 start: absolute 0.01 log-units
- fitted a-terms of the pick (J/mol): absolute 50 J/mol
- fitted b-terms of the pick: absolute 0.03 J/mol/K
- eutectic and CrNi2 top temperatures: absolute 2 K
- phase sequence on heating 600-2200 K on a 0.01 grid: categorical_identical
- Laplace mixture weight of the main mode: absolute 0.01 
- P(accepted topology) from 1000 new draws: absolute 0.03 

## Reproduce

see REPRODUCE.md (planned single command - orchid reproduce crni-paper-fit-step4c-b@0.2.0-draft)

Expected byte-identical: data/<group>/*.json and data/hinge/step4c_hinge_floor.json as in the step-4c-b run card; every run card conversion

Not reproducible byte for byte:

- Steps 1-3b: reproduced by crni-paper-fit-step4-s1@0.1.0-draft (unchanged); the step-3b pick does not meet 10a and its intermediate pick is machine-dependent (Q36, Q39); this plan starts from the frozen step-3b pick TDB in the bundle
- MLIP solids and liquid MD on the GPU (spark1): within the tolerances only; container digest not recorded
- No independent rerun of step 4c-b on a second machine yet
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
| 2026-11-06 | agent (labelled) | new specific protocol id crni-paper-fit-step4c-b (version 0.2.0-draft, supersedes crni-paper-fit-step4-s1@0.1.0-draft) rather than a 0.2.0 of the old id | a specific protocol names ONE artifact; the old id names the step-4 s1 TDB, which stays reproducible under its own document | this document |

## Limitations

- 10a applied as revised by the PI on 6 Nov (kink rule, 6b8f443): eligibility kind smooth for all 8 starts; the directional test is coordinate, +-gradient and 16 seeded random directions only (numpy default_rng(20261106)); "within its own uncertainty" read as |residual| <= sigma of the on-boundary data point (agent reading). An earlier agent check that used central FD as a corrected gradient (results/grad_verify_step4c_b_hingefloor.json) is superseded by this rule.
- Notes, not rejections (plausibility thresholds stated before ranking): fcc one-shot enthalpies moved +14.5 (x 0.25) and +11.4 kJ (x 0.5) (> 10 kJ) while fcc calorimetry is met; bcc S_ex(0.5) +2.96 J/mol-atom/K (> 2.5); liquid S_ex Cr75Ni25 2200 K at z -3.1 (> 3u).
- Strict topology flag false only for a BCC_A2 + LIQUID sliver at 2176 K (one grid temperature, above every stated window; severity high-T only); eutectic and CrNi2 window both met.
- Steps 2 and 3b did not meet the 10a rule (step 2 CRNI2 not free; step 3b no converged start, Q36/Q39); step 4c-b starts from the step-3b pick.
- The hinge-floor conversion was evaluated at the step-4 s1 pick, not at the step-3b start (recorded as an override, conforms).
- Liquid S_ex at 1900 vs 2200 K inconsistent with H_mix(T) (Cp_ex -16 vs +4.8 J/mol-atom/K, 6.5 sigma at x_Ni 0.25); read as sampling/reference error; no T^2 or T ln T term.
- Possible double counting - ORCHID eutectic vs Jenkins arrests; 6 duplicate row pairs in Jette kept.
- No independent rerun of step 4c-b yet.

## Open questions

See OPEN_QUESTIONS.md: Q05, Q10, Q11, Q12, Q25, Q26, Q27, Q36, Q39
