# Cr-Ni liquidus-first fit from the PhaseForge one-shot to the step-4 pick s1 (CrNi_paper_fit_FINAL_step4_s1.tdb)

`crni-paper-fit-step4-s1@0.1.0-draft` · specific protocol · status **draft** · licence CC-BY-4.0

> DRAFT. Reproduces the CURRENT Cr-Ni pick tdb/CrNi_paper_fit_FINAL_step4_s1.tdb. A ZPF-sigma test rerun of step 4 (step4T1_excl, step4T2_excl_zpfsigma, step4T2a_zpfsigma_samehinge, step4T3_excl_relax: exclusions completed at every observed state, ZPF driving-force sigma from each record's sigma_T) is IN PROGRESS in the same directory; this document will be versioned when it finishes and the PI decides which step 4 is the pick.

## Purpose

Rebuild the Cr-Ni TDB tdb/CrNi_paper_fit_FINAL_step4_s1.tdb from its inputs: the PhaseForge one-shot (128-atom m_scraps SQS over the whole range, staged relaxation with GRACE-2L-SMAX-OMAT-large, 100 ps liquid MD at 1900 and 2200 K with the corrected Hong-Liu entropy), set E Cr-Ni data with ORCHID-rule sigmas, two ORCHID records (eutectic ORC-SV7H3CNRYS, CrNi2 ordering ORC-X3KVP7D3PO), labelled BCC_A2 exclusions, and the sequence step 2 -> 3b -> 4 with gradient ESPEI on the Studio, followed by the physics checks and the Laplace-mixture UQ.

## Instantiates

- `orchid-calphad-fit@2.0.0` — `<orchid-sage>/protocols/general/orchid-calphad-fit@2.0.0.yaml` (sha256 `27b54fa9cd3f4fe5…`, local)

## Artifact

- tdb: `<home>/ScientificRuns/crni-paper-fit-20261106/tdb/CrNi_paper_fit_FINAL_step4_s1.tdb` (sha256 `d46bf5ddddbaeb1e…`, local)
- produced_by `crni-paper-fit-step4-s1@0.1.0-draft`

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

## Code

- **snapshot** (git): orchid-sage (github orchid-calphad, private until release) @ `94cc153`
- **phaseforgeplus** (git): <home>/src/PhaseForgePlus (local) @ `c66656faad884c7ed11354417bc89074665a74f3`
- **protocol_tools** (file_set): protocols/tools/ — entry points: orchid_reproduce.py, evaluate_states.py, build_evidence_bundle.py, tdb_header.py, run_with_fixed_date.py

## Environment

- **fit_env** (venv): <fit-env>; espei 0.8.11.dev82+g9039ea215, pycalphad 0.11.3.dev35+g9a6939dd2, numpy 2.5.4, scipy 1.18.1

## Overrides of the general protocol

| parameter | value here | general default | conforms | reason | source |
|---|---|---|---|---|---|
| certainty_tiers | ZPF energy scale = ESPEI default 1000 J/mol for every ZPF row; hinge exclusions at option C (confidence 0.5, sigma 1000) or campaign sigma | certainty tiers 10 / 50 / 100 J/mol-atom per state (evidence/states.json gives the tier each state would have); observed states at confidence 1.0 | **no** | the tier rule (fit_protocol item 8, 6 Nov) postdates the fit; the reruns apply it | fit_protocol item 8; coordinator 6 Nov |
| phases | LIQUID, BCC_A2, FCC_A1 (disordered), CRNI2 stoichiometric 1:2 (Pt2Mo type) on SGTE fcc references; no FCC_L12; no magnetic terms | disordered unless evidence requires ordering | yes | PI decision 6 Nov (FCC_A1 only); CrNi2 is a known ordered compound | crni-phaseforge-20261105 PLAN.md "PI decision (6 Nov) - disordered fcc only" |
| liquid temperatures | 2200 K (primary) and 1900 K (secondary); 864-atom check at x_Ni 0.5, 2200 K | one T just above the highest melting point | yes | 1900 K tests the temperature dependence; pure Cr crystallised at 1900 K after 82 ps and is analysed over 80 ps | crni-phaseforge-20261105 PLAN.md |
| prior | weak Normal prior centred at the one-shot (sd 50 kJ/mol on a-terms, 30 J/mol/K on b-terms) | none stated | yes | kept so that the Laplace step has a proper posterior (the rebuild's prior form) | PLAN.md multistart section; scripts/model.py |
| step-2 free set | 12 symbols (liquid, bcc, fcc a,b); CRNI2 a,b NOT free in step 2 | every phase free (held = anchored) | **no** | planned before the 6 Nov rule; step 3a showed fixing CrNi2 breaks the topology; step 3b and 4 free it | steps/configs/step2_liquidus.json; PLAN.md run log |
| step-4 exclusions | data/hinge/step4_hinge.json: set E 290 cells (CRNI2 added at T >= 895 K) + 17 Pugliese gamma states + 11 Curie marks, option C | excluded phases at EVERY observed state | **no** | the completion to every state (build_hinge_complete.py) came after the step-4 fit and is being tested in step4T1/T3 | scripts/build_hinge.py; scripts/build_hinge_complete.py |
| observed-absence weighting | BCC_A2 exclusions at the 17 Pugliese gamma states and 11 Curie marks entered by option C (confidence 0.5, sigma 1000) | confidence 1.0; sigma 10 J/mol-atom where certain (bcc in the Ni-rich fcc field is the PI example) | **no** | the rule was added after the step-4 fit (item 8, 6 Nov 07:27) | fit_protocol item 8; scripts/build_hinge.py |
| step-2 pick | s7_perturbed (converged best start of the single mode) | ranker pick | yes | the mechanical ranker chose s2 on a 1-temperature grid difference (12 vs 13 off-sequence temperatures) although s2 had not converged (|g| 0.011) | PLAN.md run log |
| accepted topology | stated in PLAN.md before ranking (bcc | bcc+CrNi2 | CrNi2 | CrNi2+fcc | fcc below T_CrNi2 in 800-930 K; eutectic 1560-1680 K; no same-phase gap; no spurious field) | R2 | yes | stated before ranking | PLAN.md |
| plausibility thresholds | one-shot solid/compound within 10 kJ/mol-atom; |S_ex(0.5)| <= 2.5 J/mol-atom/K for bcc/fcc; liquid S_ex within 3u; thermochemistry RMSE by dataset within ~2 sigma; pure elements = SGTE | R1 | yes | stated before ranking | PLAN.md |
| liquid entropy estimator | corrected Hong-Liu chemical term from <home>/ScientificRuns/hongliu-chemical-mixing-20261105/hongliu_mixing.py + the campaign VACF estimator (pre-PR scripts) | MLIPentropy (PhaseForge PR #11, a08ff3e) | yes | the Cr-Ni liquid analysis (5-6 Nov) predates the packaged MLIPentropy; the Cu-Zr validation of MLIPentropy 9e8140b against the same estimator agreed within 0.1 J/mol-atom/K | crni-phaseforge-20261105 PLAN.md "Reused from Cu-Zr"; cuzr-protocol-oneshot PLAN.md Run 2 item 2 |
| ZPF driving-force scale | ESPEI default 1000 J/mol (weight 1) | weights from uncertainties | yes | the conversion of each record's sigma_T is the test now running (step4T2*) | results/zpf_sigma_conversion.json; memory exclusions-required-held-free item 3 |

## Evidence selection

- ORCHID: set E (cr-ni-rebuild-20261105, ESPEI-format Cr-Ni datasets with ORCHID-rule sigmas) + ORCHID records from private exports @ `none (not a git checkout; every file hashed in the run cards)`; query: set E files split by phase content into data/{liq,thermo,solid}; + ORC-SV7H3CNRYS (eutectic, accepted) and ORC-X3KVP7D3PO (CrNi2 ordering, single reader)
- manifest: `<home>/ScientificRuns/crni-paper-fit-20261106/results/data_build.json` (sha256 `38cdfb89484f3655…`, local)
- evidence digest `bb4d7f64ddab35ef161e5da5a0d194a0c9bfaf0f95ffc76b37e4f32ed80ed4b0` from `<orchid-sage>/protocols/run_cards/crni-step4_solid.json` (sha256 `fe424cea8c266683…`, local)

**Exclusions**

- Hao Fig. 16 boundary marks (CrNi2 + fcc and bcc + fcc): single-reader figure marks; CrNi2 composition spread 0.65-0.76 against a stoichiometric model — PLAN.md step-4 exclusions paragraph
- ORCHID model-class CrNi2 temperatures 807/820/863 K: calculated stays out — PLAN.md
- L1_2 / L1_0 / D0_22 ordered fcc cells: computed, NOT USED (PI 6 Nov: disordered FCC_A1 only) — crni-phaseforge-20261105 results/NOT_USED.md

**Labelled interpretations**

- BCC_A2 exclusions at 17 Pugliese 1970 activity states: phase from the same paper's Table III gamma limits (Table II prints no phase per row); assumed, option C — scripts/build_hinge.py
- fcc Curie-temperature marks (Hao Fig. 13(a)) as single-phase fcc states at T >= 298.15 K: expected FCC_A1; penalize BCC_A2, CRNI2, LIQUID; option C; single reader — scripts/build_hinge.py
- CrNi2 ordering at 863 K (ORC-X3KVP7D3PO): ZPF CRNI2 (x 2/3) + FCC_A1 at zero phase fraction; CRNI2 excluded at T >= 895 K (863 K + 2 sigma_eff) — scripts/build_data.py; scripts/build_hinge.py
- eutectic 1618 K (ORC-SV7H3CNRYS): three-phase ZPF with the printed compositions — scripts/build_data.py
- partial tie-lines of set E: (i) known phase + (ii) ZPF vertex pair with a null partner composition (fit_protocol 0.4a) — scripts/build_data.py

**Single-reader records**

- CrNi2 ordering record (ORC-X3KVP7D3PO): single reader, not yet accepted; enters labelled (PI 6 Nov: second reading before release, not before fitting)
- fcc Curie marks of Hao Fig. 13(a): single reader; enters labelled
- Pugliese gamma assignments: inference from Table III limits; PI to confirm as data (REPORT.md open decision 2)

## Run sequence (failed attempts and side branches kept)

| run | step | status | starts | pick | from | summary |
|---|---|---|---|---|---|---|
| `crni-oneshot-solids-liquid` | `staged_relax` | accepted |  |  |  | solids both potentials, 128-atom SQS over the whole range; liquid 100 ps at 1900/2200 K; ideal-mixing check passed |
| `crni-oneshot-build` | `build_oneshot_tdb` | accepted |  |  |  | one-shot TDBs with and without S_ex; VV base |
| `crni-data-build` | `build_datasets` | accepted |  |  |  | build_data.py, build_hinge.py, data_consistency.py: results/data_build.json, data/hinge/step4_hinge.json, results/data_consistency.json (no run cards; outputs hashed via the step run cards) |
| `crni-step1_oneshot` | `oneshot_diagram` | accepted |  |  |  | Cr-rich fcc too stable; liquid down only to 1730 K; CrNi2 to 1156 K; pure elements exact |
| `crni-step2_liquidus` | `fit_liquidus` | accepted | 9 | s7_perturbed | crni-step1_oneshot | one mode (logpost -1703.68); eutectic 1616 K; CrNi2 (not free) to 1664 K |
| `crni-step3_thermo` | `fit_thermo` | failed | 8 | s4_perturbed | crni-step2_liquidus | CRNI2 fixed: CrNi2 stable to 1828 K above the liquidus; FCC L1 +131 kJ; reported, not continued |
| `crni-step3b_thermo_crni2free` | `fit_thermo` | accepted | 8 | s1_perturbed | crni-step2_liquidus | CRNI2 free, anchored at sigma 9.7 kJ: one mode in 7/8; eutectic 1626 K; CrNi2 top 1074 K |
| `crni-step4_solid` | `fit_solid` | accepted | 8 | s1_perturbed | crni-step3b_thermo_crni2free | logpost -6332.24 (main mode, 4 starts); right at every T except CrNi2 top 780 K vs 863 K; eutectic 1620 K |
| `crni-step5-physics-residuals` | `physics_checks` | accepted |  |  | crni-step4_solid | results/physics_final.json, per_dataset_step4_pick.json, step5_ambiguous_structures.json (no run cards) |
| `crni-uq-laplace-step4` | `laplace` | accepted |  |  | crni-step4_solid | weights 0.901 / 0.099; P(accepted topology) 0.20 with the CrNi2 window, 0.60 without |
| `crni-step4-zpfsigma-tests` | `fit_solid` | not_run |  |  | crni-step3b_thermo_crni2free | IN PROGRESS (6 Nov): step4T1_excl, step4T2_excl_zpfsigma, step4T2a_zpfsigma_samehinge, step4T3_excl_relax; read only here |

## Acceptance target

Reproduced when (1) the deterministic files (data/<group>/, data/hinge/step4_hinge.json, step-1 TDB, configs) are byte-identical to the hashes in the run cards; (2) rerunning step 4 from the step-3b pick with the same build on the Studio returns the main mode with logpost within 0.01 of -6332.2437 and every parameter within 50 J/mol (a-terms) and 0.03 J/mol/K (b-terms) (fit_protocol 10b; or the pick TDB byte-identical, sha256 d46bf5dd...); (3) the reproduced diagram over 600-2200 K has the same phase sequence on heating at every x of a 0.01 grid, eutectic within 2 K of 1620 K and CrNi2 top within 2 K of 780 K (pd4 grid, 2 K steps); (4) pure elements exact (excess terms < 0.1 J at the end points); (5) the Laplace mixture weights within 0.01 and P(accepted topology) within 0.03 with new draws.

- logpost of the main mode: absolute 0.01 log-units
- fitted a-terms of the pick (J/mol): absolute 50 J/mol
- fitted b-terms of the pick: absolute 0.03 J/mol/K
- eutectic and CrNi2 top temperatures: absolute 2 K
- phase sequence on heating 600-2200 K on a 0.01 grid: categorical_identical
- Laplace mixture weight of the main mode: absolute 0.01 
- P(accepted topology) from 1000 new draws: absolute 0.03 

## Reproduce

see REPRODUCE.md section "Cr-Ni step4 s1" (planned single command - orchid reproduce crni-paper-fit-step4-s1@0.1.0-draft)

Expected byte-identical: data/<group>/*.json and results/data_build.json from set E + the two exports via build_data.py; data/hinge/step4_hinge.json via build_hinge.py; tdb/step1_oneshot.tdb via make_base.py; every run card conversion

Not reproducible byte for byte:

- MLIP solids and liquid MD on the GPU (spark1): within the tolerances only; container digest not recorded
- The multistart uses 4 worker processes; per-start results are independent of the worker count, but this was not tested
- The step-4 objective at the pick was not re-evaluated on a second machine
- build_tdb.py writes the generation date into the one-shot TDB header line, so a rebuild on another day differs in that comment line only (compare with the header line removed)
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

## Limitations

- Pick topology misses the CrNi2 window (top 780 K vs 863 K; stated window 800-930 K); fcc one-shot enthalpies moved +13.7 (x 0.25) and +10.1 kJ (x 0.5) while fcc calorimetry is met within 0.5 sigma; bcc S_ex(0.5) +3.3 above the 2.5 threshold; CrNi2 S_f -6.6 J/mol-atom/K. Notes, not rejections.
- Step 2 had CRNI2 fixed (not free), which the 6 Nov rule no longer allows; step 4 used exclusions at a subset of states. Both are being addressed in the running tests.
- Per-iteration trajectories were not recorded (multistart.json keeps theta0 and theta per start only).
- Per-state assemblage agreement was not evaluated for the pick (dashboard shows it as pending).
- Liquid S_ex at 1900 vs 2200 K inconsistent with H_mix(T) (Cp_ex -16 vs +4.8 J/mol-atom/K, 6.5 sigma at x_Ni 0.25); read as sampling/reference error; no T^2 or T ln T term.
- Possible double counting - ORCHID eutectic vs Jenkins arrests; 6 duplicate row pairs in Jette kept.

## Open questions

See OPEN_QUESTIONS.md: Q05, Q10, Q11, Q12, Q25, Q26, Q27
