# ORCHID CALPHAD fit from a PhaseForge one-shot, liquid down (binary systems)

`orchid-calphad-fit@2.0.0` · general protocol · status **draft** · licence CC-BY-4.0

> Encodes fit_protocol.md v2.1 (6 Nov 2026: 2.0 plus the 6 Nov rulings, incl. certainty tiers per excluded phase (item 8), the converged-start pick rule (10a) with polish_starts, absolute tolerances (10b), the temperature-gated convexity constraint (0.4b) and the hinge floor (item 8, bef0bae)) (sha256 pinned in rationale_document), including the 6 Nov PI decisions (midpoint rule, held never means fixed, exclusions at every observed state, Braga-type one-sided liquidus points). Draft until the PI approves it and one independent rerun of a specific protocol has passed (Y32).

## Purpose

Build a binary CALPHAD database (TDB) that someone else, a person or a machine, can regenerate from its inputs: a frozen PhaseForge one-shot from MLIP energetics, then a staged fit with gradient ESPEI that starts at the liquid and works down (liquidus, thermochemistry, solid state, ambiguous structures), with every observation weighted by its own uncertainty, fits ranked topology first among those with plausible energies, cheap uncertainty by a Laplace mixture, and a package (TDB with header, specific protocol, run cards, evidence subset, dashboard, RO-Crate) that leaves no orphan TDB.

## Inputs

- **orchid_evidence** — ORCHID evidence (literature records and the ESPEI bundle) at a pinned commit or release (local)
- **unaries** — SGTE unary data for every pure-element end-member (the TDB's own SGTE functions) (public)
- **mlip_weights** — GRACE-2L-SMAX-OMAT-large (value) and GRACE-2L-OMAT (cross-check) model files (public)
- **structures** — compound structures (ORCHID phase registry and cited crystallography; fit_protocol 5) (local)
- **sigma_mlip** — sigma_MLIP, the MLIP-vs-experiment energy uncertainty (dft-error-vs-experiment) (local)
- **restricted_sources** — publisher PDFs and private ORCHID exports read for new evidence (restricted)

## Code

- **espei_grad** (git): https://github.com/cjkunselman18/ESPEI (branch Gradient-based_update, Brandon Bocklund's update, PR #268) @ `9039ea215c8946ff6761528071db9e519f37dfb1`
- **phaseforgeplus** (git): <home>/src/PhaseForgePlus (local) @ `c66656faad884c7ed11354417bc89074665a74f3` — entry points: phaseforgeplus.utils.hinge.HingePenalty
- **mlipentropy** (git): https://github.com/ArroyaveLab/PhaseForge.git (branch liquid-entropy-estimator; PhaseForge PR #11 to dogusariturk/PhaseForge) @ `a08ff3ef7aa5dd43e88fce7fb040e13db5471c7b` — entry points: bin/MLIPentropy
- **phaseforge_fork** (git): https://github.com/ArroyaveLab/PhaseForge.git (branch orchid/mscraps-sqs, local only) @ `23c415c3b8f524c77446a6ed14fcdebbc349a619` — entry points: bin/sqscal -sqs mscraps -relaxrange, bin/mscraps_sqsdb
- **reference_oneshot_code** (file_set): <home>/ScientificRuns/crni-phaseforge-20261105/code/ — entry points: gen_sqs.py, gen_sqs_fullrange.py, relax_solids.py, relax_solids_v2.py, run_liquid.py, analyze_solids.py, analyze_liquid.py, build_tdb.py
- **reference_fit_code** (file_set): <home>/ScientificRuns/crni-paper-fit-20261106/scripts/ — entry points: build_data.py, build_hinge.py, build_hinge_complete.py, data_consistency.py, fit.py, evaluate.py, physics.py, laplace.py, classify_draws.py, per_dataset.py, summarize.py, fig_steps.py
- **protocol_tools** (file_set): <orchid-sage>/protocols/tools/ — entry points: validate.py, build_crate.py, build_dashboard.py, backfill_run_cards.py, extract_dashboard_data.py, fig_dashboard_panels.py

## Environment

- **fit_env** (venv): <fit-env>; espei 0.8.11.dev82+g9039ea215, pycalphad 0.11.3.dev35+g9a6939dd2, numpy 2.5.4, scipy 1.18.1, symengine 0.13.0, xarray 2026.9.0, matplotlib 3.11.2, pyyaml 6.0.3
- **mlip_container** (container): cuzr-phaseforge-grace-gpu:20261104; tensorflow 25.02 (NGC), tensorpotential 0.6.2.1, materialsframework 1.0.0, m_scraps 0.6.0
- **sqs_env** (venv): <home>/.venvs/phaseforge; m_scraps 0.6.0
- **stdlib_tools** (system): ; 

## Parameters

| parameter | default | unit | frozen | meaning | source |
|---|---|---|---|---|---|
| `sqs_atoms_bcc_fcc` | 128 | atoms | yes | SQS cell size for bcc and fcc solutions | fit_protocol 0.0a SQS |
| `sqs_atoms_hcp_min` | 108 | atoms | yes | minimum SQS cell size for hcp (Cu-Zr used 128) | fit_protocol 0.0a SQS |
| `sqs_seeds` | 2 |  | yes | m_scraps seeds per composition and lattice | fit_protocol 0.0a SQS |
| `sqs_composition_grid` | "1/16, 1/8, 1/4, 3/8, 1/2, 5/8, 3/4, 7/8, 15/16 of the second element, plus both pure elements in the same supercell" |  | yes | whole composition range of every lattice | fit_protocol 0.0a SQS (PI 5 Nov) |
| `relaxation_stages` | "s0 unrelaxed (ideal parent lattice, Vegard volume) -> s1 volume -> s2 volume + ions (value) -> s3 full (lower bound)" |  | yes | staged relaxation; cell shape never relaxed for the value; lattice check after every stage; every stage kept | fit_protocol 0.0a Relaxation |
| `relaxation_optimizer` | "FIRE + FrechetCellFilter, fmax 0.005 eV/A, at most 3000 steps per stage" |  |  | as in the reference implementation relax_solids.py | crni-phaseforge-20261105/code/relax_solids.py |
| `value_rule` | "s2 if the s2 lattice check passes; otherwise the midpoint of [s3, s0] with sigma = half-width (at least sigma_MLIP)" |  | yes | protocol value of each SQS or compound energy | fit_protocol 0.0a Cells that transform (PI 6 Nov) |
| `potential` | "GRACE-2L-SMAX-OMAT-large" |  | yes | value potential for solids AND liquid; GRACE-2L-OMAT only as cross-check | fit_protocol 0.0a Potential (PI 31 Oct; liquid PI 6 Nov) |
| `references` | "SGTE for every pure-element end-member (mechanically unstable ones included)" |  | yes | no inflection detection; never fitted | fit_protocol 0.0a Reference states; unary-limits-fixed |
| `rk_order` | "L0 + L1 (a_k) for the solutions" |  |  | Redlich-Kister terms of the one-shot solution phases; alphabetical element order. Cu-Zr and Cr-Ni both used L0 + L1 (see OPEN_QUESTIONS Q07) | fit_protocol 0.0a Fit and TDB |
| `liquid_md` | "2 ps premelt (3500 K), 5-10 ps NPT, 5 ps NVT, 100 ps NVT production at T just above the highest melting point; 108 atoms, one 864-atom check at x 0.5; pure liquids at the same T" |  | yes | liquid MD settings | fit_protocol 0.0a Liquid and 9 |
| `finite_size_acceptance` | 5 | percent |  | accept 108 atoms if 100|S108 - S864|/|S864| < 5 % (vibrational entropy) | fit_protocol 9 |
| `electronic_excess_entropy` | 0 | J/mol-atom/K |  | taken as zero for metallic liquids; stated as an assumption | fit_protocol 0.0b (PI 6 Nov); see OPEN_QUESTIONS Q03 |
| `sigma_mlip` | 9687 | J/mol-atom |  | sigma of every one-shot energy observation: max(sigma_MLIP, s0 - s2, s2 - s3, half seed spread) | fit_protocol 0.0a Uncertainty; dft-error-vs-experiment |
| `espei_default_sd` | {"HM": 500, "SM": 0.2, "ACR": 0.05, "ZPF": 1000} | J/mol, J/mol/K, -, J/mol |  | ESPEI default standard deviations; weight = default sd / sigma of the observation | fit_protocol 0.2 |
| `hull_tolerance_tau` | 100 | J/mol-atom |  | state tolerance of excluded phases (hull_tolerance_J_per_mol_atom, basis default) | fit_protocol item 8 |
| `observed_absence` | {"confidence": 1.0, "sigma_certain": 10, "sigma_otherwise": "the state own uncertainty converted to energy (sigma_T |dS| or the composition equivalent)", "tau": 100} | J/mol-atom |  | exclusion at an OBSERVED state (phase stable elsewhere, not in the measured assemblage) - full confidence, never down-weighted; sigma 10 J/mol-atom where the absence is certain (never reported in a well-studied replicated region) | fit_protocol item 8 (PI 6 Nov - if a phase is not present, that is a very strong signal) |
| `certainty_tiers` | {"certain": 10, "less_certain": 50, "uncertain": 100} | J/mol-atom |  | PER EXCLUDED PHASE (PI 6 Nov) - 10 when the state is more than 3 of its own T/x uncertainties from any observed field or boundary of that phase and no source reports the phase there; 50 within 3 or single-source; 100 adjacent, diagram-assumed or contested. ZPF records - 100 for boundary/tie-line records, 50 when replicated by independent sources; single-phase field states by their distance to the nearest boundary of their phase. Replaces ESPEI 1000 J/mol | fit_protocol item 8 (PI 6 Nov 2026) |
| `hinge_sigma_floor` | "sigma = max(certainty tier, converted state uncertainty)" | J/mol-atom |  | per (state, excluded phase): the hinge scale is the larger of the tier (certainty_tiers) and the state own T and x uncertainty converted to energy as for the per-record ZPF scale sigma_DF - sqrt((sigma_T |dDG/dT|)^2 + (sigma_x |G_e'' (y - x_e)|)^2), DG the driving force of the excluded phase above the target line, from the previous accepted step; the tier is the floor, not the scale, so a 10 J/mol-atom tier binds only where the state itself is that well defined | fit_protocol item 8 hinge floor (PI 6 Nov 2026, adopted after the Cr-Ni step-4c test: 0 of 8 starts stationary without it, 8 of 8 with it) |
| `pick_gradient_threshold` | 0.001 |  |  | a start is eligible for the pick only if its gradient norm in the optimiser scaling is below this threshold, stated in the plan before fitting; near-ties among eligible starts are broken by the objective, never by grid quantities; if none is eligible say so, never loosen it. Kink rule (PI 6 Nov: local kinks are inevitable): a start is also eligible when kink-stationary - every one-sided directional derivative <= 0 (no improvement above 1e-6 log-units) along +- the analytic gradient, +- each parameter and 16 seeded random directions at scaled steps 1e-6, 1e-5, 1e-4; the run card lists the kind (smooth or kink) and the data points on a model boundary, each within its own uncertainty; central FD is never used as a gradient; a failed equilibrium is a failure, rerun from perturbed starts and reported, never a zero driving force | fit_protocol 10a (PI 6 Nov 2026; kink rule 6b8f443) |
| `polish` | {"method": "L-BFGS-B continued from each endpoint, ftol 0, gtol 0, maxcor 20, restarted from the best point", "stop": "verified gradient norm < pick_gradient_threshold, or the evaluation cap, or two restarts improving < 1e-12", "max_evals_per_start": 1000, "gradient": "analytic for terms that pass check_gradients; central FD (1e-4 in optimiser coordinates) for the term classes that fail it"} |  |  | polish_starts settings, stated in the plan before fitting and identical on every machine; a start that reaches the cap unconverged stays ineligible | coordinator decision 6 Nov 2026 (fit_protocol 10a: converge, never loosen) |
| `convexity_T_allow` | null | K |  | per solution phase: the highest temperature at which concavity may be allowed; the convexity constraint applies only at observed single-phase states above it. Set before fitting from the corrected T_c estimates of 0.4c (SRO and excess vibrational entropy corrections to the incoherent T_c, Cahn coherency correction; MLIP, DFT and fitted excess terms with uncertainties); T_allow is the upper end of that range, recorded with its basis | fit_protocol 0.4b temperature gate (PI 6 Nov 2026, commit b2d612d) |
| `option_c_exclusions` | {"sigma": 1000, "tau": 100, "confidence": 0.5} |  |  | SUPERSEDED for observed states by observed_absence and certainty_tiers (kept for exclusions assumed from a diagram, at the uncertain tier energy) | fit_protocol 0.4a (coordinator choice pending PI confirmation; OPEN_QUESTIONS Q05) |
| `starts_per_step` | 8 |  |  | multistart: start 0 = previous accepted step; starts k >= 1 perturb a-terms a(1 + 0.1 N(0,1)) [+ N(0, 2 kJ) where a = 0] and b-terms b + N(0, 3 J/mol/K), numpy default_rng(1000 + k) | campaign practice 5-6 Nov (Cu-Zr fit_step.py, Cr-Ni fit.py); OPEN_QUESTIONS Q19 |
| `optimizer` | "L-BFGS-B in scaled coordinates with the analytic ESPEI-grad gradient" |  |  | Cr-Ni: q = theta/scale (a/1000, b/1), jitter retry then value-only + central FD fallback, every event logged. Cu-Zr: scale 3 J/K (b) and max(0.05|x0|, 1) (a), up to 6 L-BFGS-B restarts of maxiter 300 | campaign practice; fit_protocol 12.A |
| `wall_budget_per_start` | 5400 | s |  | per-start wall budget; the best point is kept and the budget hit is reported | campaign practice |
| `plausibility_compound_band` | 10 | kJ/mol-atom |  | compounds and solid one-shot values within this band of the one-shot (DFT/MLIP error) | fit_protocol 0.3 item 1; dft-error-vs-experiment |
| `plausibility_liquid_sex` | 3 | u |  | liquid S_ex within 3 of its own uncertainty | campaign PLANs (stated before ranking) |
| `invariant_window` | 25 | K |  | quantitative check of invariant temperatures | fit_protocol 0.3 item 3 |
| `mcmc_stop_hours` | 12 | h |  | above this projected wall time stop for a decision | fit_protocol 0.6 |
| `laplace_draws` | 1000 |  |  | classified draws from the Laplace mixture | Cr-Ni PLAN (cheap UQ, no MCMC) |
| `laplace_hessian_steps` | [0.001, 0.003] |  |  | relative central-difference steps of the analytic gradient, times max(1, |q|), symmetrised; soft-direction repair along the 3 softest eigenvectors | cr-ni-rebuild laplace/scripts/hessian_mode.py |

## Preflight, established practice and the plan

*Rationale: fit_protocol 0.0b, 0.5, 0.6, 1, 2, 11*

### 1. Check established practice before writing the brief (`read_established_practice`, judgement)

Read fit_protocol.md Section 0.0b (the established-practice table), Section 0.0a, and the REPORT.md and PLAN.md of the last campaign that did the same step. Write in the plan which rows of 0.0b apply and quote what was done before for every item that the new brief touches. A new instruction refines established practice; it replaces it only when the PI says so.

- **Inputs:** `input:orchid_evidence`
- **Tool:** reading (no software)
- **Results:** `practice_note` established-practice paragraph of PLAN.md [checks: every 0.0b row named, conflicts quoted]
- **Decision rule:** if the brief and 0.0b seem to conflict, stop and ask the PI, quoting what was done before; never reinterpret 0.0a from a short instruction — **decided by** PI (coordinator raises the question)
- *Rationale:* fit_protocol 0.0b

### 2. Write the run specification (PLAN.md) before any launch (`write_plan`, deterministic)

Write PLAN.md in the campaign directory before launching anything: system, T-x domain, phases and models (disordered unless evidence requires ordering; ask the PI before adding phases or sublattices), parameters and their VV symbols, inputs with paths and sha256, data groups per step, free symbols per step, ranking thresholds (stated now, before ranking), compute hosts and a wall-time estimate per block. If any block projects beyond 12 h, stop for a decision.

- **Inputs:** `read_established_practice.practice_note`, `param:mcmc_stop_hours`
- **Tool:** editor — `cp protocols/templates/PLAN.template.md <campaign>/PLAN.md && $EDITOR <campaign>/PLAN.md   # then: python3 protocols/tools/check_plan.py <campaign>/PLAN.md`
- **Results:** `plan` PLAN.md [checks: written before the first launch (file mtime earlier than every run card), thresholds stated, wall-time estimate present]
- *Rationale:* fit_protocol 2, 0.6

### 3. Verify the ESPEI build that is actually imported (`verify_build`, deterministic)

From the interpreter that will run every fit, print espei.__version__ and espei.__file__. It must read 0.8.11.dev82+g9039ea215. Write both into every run card and result file. Do not set SETUPTOOLS_SCM_PRETEND_VERSION (it hides the commit). Environment names are not evidence.

- **Tool:** python — `<fit-python> -c "import espei, pycalphad; print(espei.__version__, espei.__file__, pycalphad.__version__)"`
- **Results:** `build_record` version line in every run card [checks: espei 0.8.11.dev82+g9039ea215, pycalphad 0.11.3.dev35+g9a6939dd2]
- **Gates:** G1_software_build
- *Rationale:* fit_protocol 0.5

### 4. Check the gradient build against ESPEI 0.9.0 and finite differences (`check_gradients`, numerical)

Before a campaign on a new system or a new build, evaluate the log-likelihood and its gradient at the reference parameters and at a few random points with the gradient build and with ESPEI 0.9.0, term by term, and compare the gradient with central finite differences away from phase switches. Record the agreement and the nonsmooth regions. Repeat the term-by-term FD comparison at the endpoints of every fit step before its pick: a term class whose analytic gradient disagrees with FD (stable under a tenfold change of the FD step) is named in polish.fd_terms, and the eligibility norm of fit_protocol 10a is the norm of that verified gradient (6 Nov 2026: gradient ESPEI 9039ea2 ActivityResidual at the Cr-Ni step-3b endpoint, |analytic - FD| 1.35 of 3.48; ZPFResidual at Cu-Zr H1 s1, 0.31 of 8.69).

- **Inputs:** `verify_build.build_record`
- **Tool:** gradient check — `<fit-python> -I protocols/tools/gradient_check.py <start.tdb> <config.json> --points 5 --seed 20261106 --out results/gradient_check.json` (wraps the cr-ni-rebuild-20261105/tests procedure (ESPEI 0.9.0 comparison runs with <home>/orchid-crni-mcmc-20261105/env/uq))
- **Results:** `gradient_check` results/gradient_check.json [checks: term-by-term agreement ~1e-9, FD agreement reported]
- **Tolerance:** log-likelihood difference gradient build vs ESPEI 0.9.0: absolute 1e-09 log-units
- *Rationale:* fit_protocol 0.5, 11

### 5. Reproduce the reference assessment first (`reproduce_reference`, numerical)

When a published assessment with a TDB exists, compute its diagram and score it on exactly the objective the candidates will use; record discrepancies between the paper and the distributed TDB. An unexpectedly large penalty is a reason to audit labels, units and signs before fitting.

- **Inputs:** `input:orchid_evidence`, `verify_build.build_record`
- **Tool:** score the reference TDB — `<fit-python> -I protocols/tools/evaluate_states.py <reference.tdb> assessments/<artifact>/evidence/states.json results/reference_states.json --nproc 4`
- **Results:** `reference_check` results/reference_check.json [checks: reference scored on the common objective, offending states listed]
- **Tolerance:** invariant temperatures of the reference reproduced from its TDB: absolute 2 K
- *Rationale:* fit_protocol 0.5, 11

## Evidence, exclusions, weights and the consistency check

*Rationale: fit_protocol 0.2, 0.2a, 0.4a, item 8, 3, 4, 6, 7, 8*

### 1. Build the step datasets from ORCHID at a pinned commit (`build_datasets`, deterministic)

Copy the ESPEI datasets of the system from orchid-data-next espei/ at the pinned commit into data/<group>/ (liq: ZPF rows containing LIQUID; thermo: activities, HM_MIX, HM_FORM, DFT; solid: ZPF rows without LIQUID; dense: assessed dense grids, kept as their own evidence class). Values, sigma and weights unchanged; keep only phase regions whose phases are all in the model (drop, never rename); write a manifest with source path, sha256 and rows kept/dropped per file. Every observation not yet in ORCHID gets the sigma ORCHID's published rules would give it (literature/UNCERTAINTY_CALIBRATION.md) and is queued for extraction.

- **Inputs:** `input:orchid_evidence`, `write_plan.plan`
- **Tool:** build_data.py — `<fit-python> scripts/build_data.py`
- **Results:** `datasets` data/<group>/*.json [checks: values identical to the ORCHID files]; `manifest` data manifest with sha256 per file [checks: rows kept + dropped = rows read]
- *Rationale:* fit_protocol 3, 0.2

### 2. Encode partial tie-lines and one-sided liquidus points (`partial_tielines`, deterministic)

Where only one end of a tie-line is reported, write two observations of the same parent: (i) the known phase at its reported composition and (ii) a ZPF vertex pair of the known phase with the partner phase at null composition (zero phase fraction). Liquidus-only points (temperature printed, no solid named) are written as liquid + primary solid at T with the solid composition null, the primary solid taken from the source's own diagram, labelled as an interpretation; ambiguous primary solids are held, not guessed. Never drop the partner phase, never invent the missing composition.

- **Inputs:** `build_datasets.datasets`
- **Tool:** build_data.py (partial tie-line split) — `<fit-python> scripts/build_data.py   # the (i)/(ii) split is part of build_data.py`
- **Results:** `split_datasets` (i) and (ii) files of 0.4a, labelled [checks: both derived from the same parent observation, no composition written for the partner]
- *Rationale:* fit_protocol 0.4a; memory exclusions-required-held-free item 4

### 3. Add excluded phases at every observed state (`exclusions_every_state`, deterministic)

For every observed state of every dataset that enters the objective, single-phase states included, list the phases of the model that are stable elsewhere in the system but not at that state (relation adjacent_field, adjacent_line or stable_elsewhere, ORCHID excluded_phases), and write hinge cells in the format of espei/SCHEMA.md (T, x, expected, tie_line, penalize, sigma, confidence, orchid{observation_id, state_id, hull_tolerance_J_per_mol_atom}). An exclusion at an OBSERVED state (the phase is stable elsewhere but absent from the measured assemblage) enters at confidence 1.0, never down-weighted; its sigma is 10 J/mol-atom where the absence is certain (a phase never reported in a well-studied, replicated region) and otherwise the state's own uncertainty converted to energy (sigma_T |dS|, or the composition equivalent); tau stays 100. Only exclusions assumed from a diagram (not observed) enter by option C (sigma 1000 J/mol-atom, tau 100, confidence 0.5); both kinds are labelled. Exclusions from thermochemical states only where the state lies above every experimental liquidus observation at that composition. List every state that still lacks a cell and why.

- **Inputs:** `partial_tielines.split_datasets`, `param:hull_tolerance_tau`, `param:observed_absence`, `param:option_c_exclusions`
- **Tool:** build_hinge_complete.py — `<fit-python> scripts/build_hinge_complete.py`
- **Results:** `hinge` data/hinge/<step>_hinge.json [checks: every observed state has a cell or a listed reason, option C cells labelled]; `exclusion_audit` results/exclusion_audit.json
- **Gates:** G4_exclusions_present
- *Rationale:* fit_protocol item 8, 0.4a (PI 6 Nov)

### 4. Classify the certainty tier of every ZPF and exclusion observation (`classify_certainty`, deterministic)

Build the evidence bundle of the fit (a NEW bundle version when anything changes) and grade every term. Each phase EXCLUDED at a state gets its own tier from that state's distance to the phase's own observed field or boundary, in the state's T/x uncertainties - 10 J/mol-atom beyond 3 uncertainties with no source reporting the phase there; 50 within 3, or supported by a single source; 100 when adjacent, assumed from a diagram, or contested. Each ZPF record gets 100 when it is a boundary or tie-line record and 50 when independent sources replicate it within their uncertainty; single-phase field states are graded by their distance to the nearest boundary of their own phase. Observed states enter at confidence 1.0. Write exclusions[] (phase, tier, energy scale, basis) and zpf_certainty into states@<version>.json; the objective's ZPF and hinge scales come from them. Hinge floor (item 8): each exclusion's hinge scale is sigma = max(tier, the state's T and x uncertainty converted to energy as for sigma_DF, at the previous accepted step); write the converted value, the tier and the scale used per (state, excluded phase) beside the hinge file.

- **Inputs:** `exclusions_every_state.hinge`, `param:certainty_tiers`, `param:observed_absence`, `param:hinge_sigma_floor`
- **Tool:** build_evidence_bundle.py — `<fit-python> -I protocols/tools/build_evidence_bundle.py generic --art <artifact> --element <EL> --run-card <run card listing the data files> --hinge <hinge.json> --oneshot results/oneshot_observations.json --pick <pick.tdb> --registry <Y25 graph/observations.parquet> --version <new bundle version>`
- **Results:** `states` assessments/<artifact>/evidence/states@<version>.json (zpf_certainty per state; exclusions[] with a tier per excluded phase) [checks: every ZPF record and every excluded phase has a tier and a basis]; `bundle` assessments/<artifact>/evidence/MANIFEST.json (bundle sha256) [checks: no source-text field over 500 characters]
- *Rationale:* fit_protocol item 8 (certainty tiers, PI 6 Nov)

### 5. Set every weight from the observation's own uncertainty (`weights_from_sigma`, deterministic)

ESPEI weight = ESPEI default standard deviation / sigma of the observation, with sigma = uncertainty_budget.sigma_effective for ORCHID records (converted as the ESPEI bundle does, espei/SCHEMA.md). No hand-set multipliers. Repeated quotations of one measurement count once. Assessed dense grids are reported as their own evidence class and are never up-weighted.

- **Inputs:** `exclusions_every_state.hinge`, `param:espei_default_sd`
- **Tool:** build_data.py (weights) — `<fit-python> scripts/build_data.py && <fit-python> scripts/data_consistency.py   # weights are written by build_data.py and audited by data_consistency.py item 1`
- **Results:** `weighted_datasets` datasets with weights [checks: no dataset at a software default sigma except the ZPF driving-force scale (OPEN_QUESTIONS Q11)]
- *Rationale:* fit_protocol 0.2

### 6. Run the data consistency check (flags only) (`data_consistency`, deterministic)

Run the seven checks of fit_protocol 0.2a on every dataset that enters the objective (uncertainty present with a basis; within-series jumps and bounds; cross-quantity tests such as Gibbs-Duhem; basis and units; duplicates; cross-source disagreement; pull at the reference). Write results/data_consistency.json. It flags; it never changes data. A flagged value stays at its uncertainty unless the PI holds it; report the fit with and without it when it matters.

- **Inputs:** `weights_from_sigma.weighted_datasets`, `reproduce_reference.reference_check`
- **Tool:** data_consistency.py — `<fit-python> scripts/data_consistency.py`
- **Results:** `consistency` results/data_consistency.json [checks: seven items present, flagged values listed with record ids]
- **Gates:** G3_data_consistency_run
- *Rationale:* fit_protocol 0.2a

### 7. Reconcile the evidence ledger and the ORCHID export ledger (`evidence_ledger`, deterministic)

Write the evidence ledger (every observation with its ORC id, state_id, evidence class, sigma and disposition included / validation / duplicate / held / out_of_scope / invalid_extraction) and the export ledger of every new or derived item (extractions, interpretations, campaign-added exclusions) with its provisional or canonical id and its review and delivery status. No record disappears because a loader cannot represent it. Single-reader records may enter a fit labelled; a second reading is needed before release, not before fitting.

- **Inputs:** `data_consistency.consistency`
- **Tool:** evidence bundle + intake — `<fit-python> -I protocols/tools/build_evidence_bundle.py generic --art <artifact> --element <EL> --run-card <run card> --hinge <hinge.json> --registry <Y25 observations.parquet> && python3 protocols/tools/prepare_intake.py assessments/<artifact>` (the bundle MANIFEST.json + states.json is the evidence ledger; intake/ is the contribution manifest (fit_protocol 14 names; OPEN_QUESTIONS Q16))
- **Results:** `ledger` evidence_ledger.jsonl + contribution_manifest.json [checks: counts reconcile acquisition -> export -> objective]
- *Rationale:* fit_protocol 3, 4

## PhaseForge one-shot (frozen, fit_protocol 0.0a) = step 1 of the sequence

*Rationale: fit_protocol 0.0a, 0.0b, 5, 9, 10*

### 1. Generate the SQS cells with m_scraps (`gen_sqs`, deterministic)

Generate 128-atom SQS for bcc and fcc (and at least 108 atoms for hcp; 128 is the precedent) with m_scraps 0.6.0, two seeds per composition, over the whole composition grid, plus both pure elements in the same supercells. Settings: weighted_l1 objective, figure cut-offs in nearest-neighbour units (2.05, 1.45, 1.05) fcc/hcp and (2.05, 1.20, 1.05) bcc, auto_budget 2. Record the seeds, check all seed pairs are distinct, hash every POSCAR.

- **Inputs:** `param:sqs_atoms_bcc_fcc`, `param:sqs_atoms_hcp_min`, `param:sqs_seeds`, `param:sqs_composition_grid`, `write_plan.plan`
- **Tool:** gen_sqs.py — `<home>/.venvs/phaseforge/bin/python code/gen_sqs.py inputs/structures`
- **Results:** `sqs_cells` inputs/structures/<LATTICE>/<cell>/POSCAR [checks: atom counts, distinct seed pairs, logs/gen_sqs.log]
- *Rationale:* fit_protocol 0.0a SQS

### 2. Relax every SQS and compound in stages, with a lattice check after each (`staged_relax`, numerical)

Run every cell with the value potential and the cross-check potential, in detached containers on an approved GPU host (check load first; never spark4): s0 unrelaxed at the Vegard volume of the MLIP same-lattice pure elements (static); s1 isotropic volume; s2 volume + ions with the shape fixed (the protocol value); s3 full (lower bound, kept even if the lattice changes). After each stage check the lattice (SQS: displacements, coordination, s3 shape strain; compounds: displacements + spglib space group). Keep every stage of every cell; never drop a cell that transforms. Record container names and host PIDs in logs/launch_solids.tsv. Pull results read-only.

- **Inputs:** `gen_sqs.sqs_cells`, `input:structures`, `input:mlip_weights`, `param:relaxation_stages`, `param:relaxation_optimizer`, `param:potential`
- **Tool:** relax_solids.py in the GPU container — `docker run -d --gpus all --name <campaign>-solids-<tag> --ipc=host -e XLA_FLAGS=--xla_gpu_cuda_data_dir=/opt/cuda13 -v /usr/local/cuda-13.0:/opt/cuda13:ro -v $R:/campaign -v $R/inputs/potential:/root/.cache/grace:ro cuzr-phaseforge-grace-gpu:20261104 sh -c "python -u /campaign/code/relax_solids.py <MODEL> > /campaign/logs/solids-<tag>.log 2>&1"`
- **Results:** `solids_raw` collected_solids/<MODEL>/<LATTICE>/<cell>/result.json [checks: 4 stages per cell, lattice check per stage]
- **Tolerance:** s2 mixing or formation energy per cell on a rerun (GPU, same image and weights): absolute 0.1 kJ/mol-atom
- **Tolerance:** lattice-check verdict per cell and stage: categorical_identical
- *Rationale:* fit_protocol 0.0a Relaxation; mlip-relaxation-protocol

### 3. Apply the value rule and assign sigma per point (`value_rule`, deterministic)

Per composition and lattice: if the s2 lattice check passes, the value is the s2 seed mean; otherwise the value is the midpoint of [s3, s0] and its half-width is the uncertainty. sigma_i = max(sigma_MLIP, s0 - s2, s2 - s3, half seed spread) for s2 values, max(sigma_MLIP, half-width) for midpoint values. Mixing energies relative to the same-lattice MLIP end-members (s2 pure cells); compound formation energies relative to the MLIP pure elements in their SGTE stable structures. A compound "keeps its structure" when its s2 space group equals the prototype's (Cu-Zr precedent, coordinator decision, labelled; OPEN_QUESTIONS Q09).

- **Inputs:** `staged_relax.solids_raw`, `input:sigma_mlip`, `param:value_rule`, `param:sigma_mlip`
- **Tool:** analyze_solids.py / build_oneshot.py — `<fit-python> code/build_oneshot.py`
- **Results:** `solids_summary` results/solids_<MODEL>.json [checks: every cell present, value rule recorded per point]; `oneshot_observations` results/oneshot_observations.json [checks: value and sigma per observation, sigma_basis]
- *Rationale:* fit_protocol 0.0a (midpoint rule PI 6 Nov)

### 4. Run the liquid MD (100 ps production) (`liquid_md`, numerical)

With the value potential, run the liquid at five compositions (x 0, 0.25, 0.5, 0.75, 1) with 108 atoms and one 864-atom check at x 0.5, all at the same temperature just above the highest melting point: 2 ps premelt at 3500 K, NPT density equilibration, NVT equilibration, 100 ps NVT production, positions and velocities saved every 2 fs. Seeds fixed and recorded. Check every run is liquid (species MSD/diffusion, RDF, no crystallisation) and keep failed runs with their disposition (e.g. analyse a run that crystallised over its liquid window only).

- **Inputs:** `input:mlip_weights`, `param:liquid_md`, `param:potential`
- **Tool:** run_liquid.py in the GPU container — `docker run -d --gpus all --name <campaign>-liq-<tag> ... cuzr-phaseforge-grace-gpu:20261104 sh -c "python -u /campaign/code/run_liquid.py --size <108|864> --x-<el> <x> --seed <seed> --model GRACE-2L-SMAX-OMAT-large"`
- **Results:** `liquid_runs` collected_liquid/<run>/ (thermo.jsonl, positions, velocities) [checks: liquid by MSD, production 100 ps]
- **Tolerance:** H_mix at x 0.25/0.5/0.75 on a rerun: absolute 0.5 kJ/mol-atom
- **Tolerance:** S_ex at x 0.25/0.5/0.75 on a rerun: absolute 0.3 J/mol-atom/K
- *Rationale:* fit_protocol 0.0a Liquid, 9, 10.C

### 5. Compute the liquid excess entropy with MLIPentropy (ideal-mixing check first) (`liquid_entropy`, numerical)

Convert the production runs to ASE trajectories with positions and velocities on the same frames, then run MLIPentropy with the pure-liquid references at the same T. The ideal-mixing check (random labels on the MD neighbour graphs) must give |S_chem,ex| at or below its tolerance before any value is used. S_ex = vibrational (VACF) + corrected chemical (pair/quasi-chemical) term; excess electronic entropy taken as zero (assumption). Apply the 108/864 finite-size rule. Values enter later steps as SM_MIX observations labelled provisional.

- **Inputs:** `liquid_md.liquid_runs`, `param:finite_size_acceptance`, `param:electronic_excess_entropy`
- **Tool:** MLIPentropy — `MLIPentropy -temp=<T> -dt=2 -ref=<A_liq.traj> -ref=<B_liq.traj> -alloy=<x025.traj> -alloy=<x050.traj> -alloy=<x075.traj> -o results/liquid_excess_entropy.json`
- **Results:** `liquid_sex` results/liquid_excess_entropy.json [checks: ideal-mixing check passed, finite-size check reported, provisional label]
- **Tolerance:** S_ex per composition from the same trajectories (deterministic estimator, fixed seed): absolute 1e-06 J/mol-atom/K
- *Rationale:* fit_protocol 10.D; docs/protocols/liquid-entropy.md

### 6. Fit Redlich-Kister terms and write the one-shot TDB with SGTE end-members (`build_oneshot_tdb`, deterministic)

Weighted least squares (weights 1/sigma_fit^2, sigma_fit = max(half [s3, s0] interval, half seed spread, 0.1 kJ)) of the protocol values for the solution phases (L0 + L1, a-terms only); liquid L0 (+ L1) a-terms from H_mix and, for the S_ex variant, b-terms from S_ex; compounds as line compounds G = sum of SGTE unaries + (a+b) H_f. Elements and interaction parameters in alphabetical order. Interaction and compound terms are written as VV symbols (VV0000...) so the fit steps can move them; the T-coefficient symbols start at 0. Pure-element end-members are the SGTE unaries copied verbatim, never fitted.

- **Inputs:** `value_rule.solids_summary`, `liquid_md.liquid_runs`, `liquid_entropy.liquid_sex`, `input:unaries`, `param:rk_order`, `param:references`
- **Tool:** build_tdb.py / build_oneshot.py + make_base.py — `<fit-python> code/build_oneshot.py && <fit-python> scripts/make_base.py`
- **Results:** `oneshot_tdb` tdb/step1_oneshot.tdb [checks: SGTE unary lines identical to the source TDB, VV layout recorded, sha256 recorded]
- *Rationale:* fit_protocol 0.0a Fit and TDB

### 7. Draw the one-shot diagram and run the pure-element check (`oneshot_diagram`, deterministic)

Compute the diagram of the one-shot TDB over the declared T range, run the pure-element check (stable phase sequence and melting points equal SGTE; ordered end-members equal their disordered parent) and record which phases exist and where. Look at the diagram. This is step 1 of the sequence: no fitting.

- **Inputs:** `build_oneshot_tdb.oneshot_tdb`
- **Tool:** evaluate.py / evaluate_step.py — `<fit-python> scripts/evaluate.py step1_oneshot`
- **Results:** `oneshot_eval` steps/step1_oneshot/evaluation.json + figure [checks: pure elements = SGTE, phases recorded]
- **Gates:** G2_pure_elements
- *Rationale:* fit_protocol 0.1 step 1; unary-limits-fixed

## Staged fit from the liquid down (fit_protocol 0.1)

Every fit step below is executed by the same fit procedure (fit_step), followed by evaluate_and_pick. Each step starts from the previous ACCEPTED step and is versioned in steps/<step>/. "Held" never means fixed: every phase and compound stays free in every step, anchored by its one-shot value entered as an observation at its sigma (PI 6 Nov). A step that breaks the topology is reported, not silently continued.

*Rationale: fit_protocol 0.1, 0.2, 0.3, 0.4, 12*

### 1. Step 2, liquidus (`fit_liquidus`, numerical)

Fit with data groups oneshot + liq: the liquid-containing ZPF rows ((i)+(ii) files of 0.4a), invariants involving the liquid, the provisional liquid S_ex (SM_MIX, weight 0.2/u) and every one-shot observation at its sigma. Free: the liquid a,b terms, the solution a,b terms and the compound a,b terms (held = anchored, not fixed). Multistart with the starts_per_step rule; record the full trajectory (record_trajectory). Before step 3: no solid stable above the liquidus anywhere; liquid stable at high T; invariants involving the liquid.

- **Inputs:** `oneshot_diagram.oneshot_eval`, `build_oneshot_tdb.oneshot_tdb`, `value_rule.oneshot_observations`, `liquid_entropy.liquid_sex`, `exclusions_every_state.hinge`, `weights_from_sigma.weighted_datasets`, `param:starts_per_step`, `param:optimizer`, `param:wall_budget_per_start`
- **Tool:** fit.py (multistart MAP) — `cd <campaign> && PYTHONPATH=<home>/src/PhaseForgePlus/src OMP_NUM_THREADS=1 <fit-python> scripts/fit.py steps/configs/step2_liquidus.json <nproc> 7`
- **Results:** `starts` steps/step2_liquidus/ (run_card.json, multistart.json, s*.tdb, trajectory.jsonl) [checks: espei.__version__ in run card, every start kept]
- **Tolerance:** log posterior of each start on a rerun (same build, CPU, OMP_NUM_THREADS=1): absolute 0.01 log-units
- **Tolerance:** parameters of the picked start on a rerun: absolute
- *Rationale:* fit_protocol 0.1 step 2

### 2. Polish every start to convergence (after every fit step) (`polish_starts`, numerical)

After the multistart of every fit step (fit_liquidus, fit_thermo, fit_solid and system-specific fit steps), continue each start from its endpoint with the same objective and the polish settings until the verified gradient norm (check_gradients) is below pick_gradient_threshold or the evaluation cap is reached. Keep the pre-polish results (multistart_prepolish.json, s<k>/ files) as recorded runs. Report every start's norm before and after, its status and its parameter changes; a start that reaches the cap unconverged stays ineligible. Then pick (10a) among the converged starts only; if none converged, report it and do not loosen the threshold.

- **Inputs:** `fit_liquidus.starts`, `check_gradients.gradient_check`, `param:polish`, `param:pick_gradient_threshold`
- **Tool:** polish_starts.py — `<python> protocols/tools/polish_starts.py crni|cuzr <step> [--starts ...] --max-evals <cap> --fd-terms <failed term classes>; then python3 protocols/tools/pick_start.py steps/<step> --threshold <plan value> (Cr-Ni) or polish_starts.py cuzr-pick <step> (Cu-Zr)`
- **Results:** `polished` steps/<step>/multistart.json (polished, with polish records) + multistart_prepolish.json + polish_report.json; or s<k>/polish/ [checks: pre-polish results kept, settings recorded, every start reported]; `pick_10a` steps/<step>/pick_protocol_10a.json [checks: only converged starts eligible, threshold as stated in the plan]
- **Tolerance:** polished parameters of the pick across machines: absolute
- *Rationale:* fit_protocol 10a; coordinator decision 6 Nov 2026

### 3. Look at the diagrams, rank the starts and pick (step 2) (`pick_liquidus`, judgement)

For every start: diagram over the declared T range, topology check, pure-element check, one-shot shifts in units of sigma, plausibility. Rank by fit_protocol 0.3 (plausible energies, then topology with spurious-field severity by temperature, then quantitative). Look at the pick's diagram before naming it. Copy the pick to tdb/step2_liquidus_pick.tdb.

- **Inputs:** `fit_liquidus.starts`
- **Tool:** evaluate.py — `<fit-python> scripts/evaluate.py step2_liquidus [pick_start_name]`
- **Results:** `pick` steps/step2_liquidus/evaluation.json + tdb/step2_liquidus_pick.tdb + figure [checks: ranking recorded, pick diagram looked at]
- **Decision rule:** fit_protocol 10a - only starts with gradient norm below pick_gradient_threshold are eligible (python3 protocols/tools/pick_start.py steps/<step> --threshold <plan value>); rank eligible starts by R1-R3 classes (plausible; topology class) and break near-ties by the objective, never by grid quantities; if no start is eligible, report it and do not loosen the threshold — **decided by** campaign coordinator (agent), reported to the PI; PI decides when no fit is plausible or the topology is wrong in every start
- **Gates:** G2_pure_elements
- *Rationale:* fit_protocol 0.3, 0.1

### 4. Step 3, thermochemistry (`fit_thermo`, numerical)

From the step-2 pick, add calorimetry, activities and mixing enthalpies (and DFT where ORCHID holds it) at their own sigma. Same free set; widen a compound's sigma only where calorimetry for it exists. Multistart; record the trajectory. Before step 4: topology unchanged; thermochemical residuals by dataset.

- **Inputs:** `pick_liquidus.pick`, `weights_from_sigma.weighted_datasets`, `value_rule.oneshot_observations`, `param:starts_per_step`
- **Tool:** fit.py — `cd <campaign> && PYTHONPATH=<home>/src/PhaseForgePlus/src OMP_NUM_THREADS=1 <fit-python> scripts/fit.py steps/configs/step3_thermo.json <nproc> 7`
- **Results:** `starts` steps/step3_thermo/ [checks: as step 2]
- **Tolerance:** log posterior of each start on a rerun: absolute 0.01 log-units
- *Rationale:* fit_protocol 0.1 step 3

### 5. Rank and pick (step 3) (`pick_thermo`, judgement)

As pick_liquidus, for step 3; copy the pick to tdb/step3_thermo_pick.tdb.

- **Inputs:** `fit_thermo.starts`
- **Tool:** evaluate.py — `<fit-python> scripts/evaluate.py step3_thermo`
- **Results:** `pick` steps/step3_thermo/evaluation.json + pick TDB
- **Decision rule:** as pick_liquidus (10a eligibility and objective tie-break); a step that breaks the topology is reported and the cause found before it is repeated (e.g. Cr-Ni 3a, a compound fixed instead of anchored) — **decided by** campaign coordinator (agent), reported to the PI
- *Rationale:* fit_protocol 0.3

### 6. Step 4, solid state (`fit_solid`, numerical)

From the step-3 pick, add the solid-state ZPF rows, dense assemblages (as their own evidence class) and the hinge of excluded phases at every observed state. Multistart; record the trajectory. Before step 5: full topology over the declared T range; spurious-field severity by temperature.

- **Inputs:** `pick_thermo.pick`, `exclusions_every_state.hinge`, `weights_from_sigma.weighted_datasets`, `param:starts_per_step`
- **Tool:** fit.py — `cd <campaign> && PYTHONPATH=<home>/src/PhaseForgePlus/src OMP_NUM_THREADS=1 <fit-python> scripts/fit.py steps/configs/step4_solid.json <nproc> 7`
- **Results:** `starts` steps/step4_solid/
- **Tolerance:** log posterior of each start on a rerun: absolute 0.01 log-units
- *Rationale:* fit_protocol 0.1 step 4, item 8

### 7. When the topology moves, add ZPF evidence (not a special term) (`topology_moves`, judgement)

If the ranked fits of a step have the wrong topology, find which observations pull against the right topology (by dataset and evidence class), add the ZPF evidence that exists (the invariant observations of the reactions in question, two-phase points around them, excluded phases by item 8), all from ORCHID records with their ids, and refit from the last step at the same uncertainty-derived weights, as a new labelled step. Never hand-edit parameters and never add a topology penalty. If honest weights still cannot reach the right topology with plausible energies, report it as a finding about the data and the model.

- **Inputs:** `fit_solid.starts`
- **Tool:** per-dataset pull (topology_cost.py, zpf_by_file.py, per_dataset.py) — `<fit-python> scripts/per_dataset.py tdb/<wrong-topology pick>.tdb results/per_dataset_<step>.json && <fit-python> -I protocols/tools/evaluate_states.py tdb/<pick>.tdb assessments/<artifact>/evidence/states.json results/states_<step>.json   # then compare the pulls of the datasets that hold the reactions in question`
- **Results:** `pull_report` results/topology_pull.json or a labelled extra step (e.g. Cu-Zr H1/H2) [checks: observations that conflict listed with ids]
- **Decision rule:** add only evidence that exists in ORCHID (ids); a new step needs a new config and run cards; same weights — **decided by** PI for any new data class or encoding; coordinator for adding existing ORCHID invariant/exclusion cells
- *Rationale:* fit_protocol 0.4

### 8. Check same-phase splitting and decide on a convexity constraint (`same_phase_split`, judgement)

For each solution phase with single-phase observations, check whether the fit splits it into two composition sets. If there is no source report of a miscibility gap and the mixing energies do not suggest one (regular-solution T_c with the SRO factor, Cahn's coherent term, excess vibrational entropy, DFT/MLIP error on Omega), apply a convexity constraint at the observed single-phase states only; otherwise leave it to the data and report the topology uncertainty. Temperature gate (0.4b): the constraint applies only at observed single-phase states above convexity_T_allow of that phase, set before fitting from the corrected T_c estimates (SRO, excess vibrational entropy, Cahn coherency) with their basis; below it concavity is left to the data. Its energy scale follows the state's certainty tier. Report the sensitivity of the result to T_allow.

- **Inputs:** `fit_solid.starts`
- **Tool:** physics.py — `<fit-python> scripts/physics.py <tdb> results/physics_<step>.json`
- **Results:** `gap_assessment` results/physics_<step>.json [checks: chemical and coherent results both reported]
- **Decision rule:** convexity term only if both the incoherent estimate and Cahn's term make a gap unlikely and no source reports one; applied only above convexity_T_allow (0.4b) — **decided by** campaign coordinator, reported; PI if the decision changes the model
- *Rationale:* fit_protocol 0.4b (incl. the temperature gate, b2d612d), 0.4c

### 9. Rank and pick (step 4) (`pick_solid`, judgement)

As pick_liquidus, for step 4; copy the pick to tdb/step4_solid_pick.tdb.

- **Inputs:** `fit_solid.starts`, `same_phase_split.gap_assessment`, `topology_moves.pull_report`
- **Tool:** evaluate.py — `<fit-python> scripts/evaluate.py step4_solid`
- **Results:** `pick` steps/step4_solid/evaluation.json + pick TDB
- **Decision rule:** as pick_liquidus (10a eligibility and objective tie-break) — **decided by** campaign coordinator (agent), reported to the PI
- *Rationale:* fit_protocol 0.3, 10a

### 10. Step 5, ambiguous structures (`ambiguous_structures`, judgement)

For phases with uncertain structures, do the best possible while keeping them within the DFT/MLIP error band (~10 kJ/mol-atom) of the MLIP hull; record the structure disposition (confirmed, provisional candidate or analogue, unresolved; fit_protocol 5). Write results/step5_ambiguous_structures.json even when none applies.

- **Inputs:** `pick_solid.pick`
- **Tool:** evaluation of the pick against the MLIP hull — `<fit-python> scripts/evaluate.py <step>   # writes oneshot_shifts (sigma units) and formation energies vs the MLIP values; record results/step5_ambiguous_structures.json`
- **Results:** `step5` results/step5_ambiguous_structures.json
- **Decision rule:** a compound beyond the band is a note, not a rejection, unless calorimetry also disagrees — **decided by** campaign coordinator, reported to the PI
- *Rationale:* fit_protocol 0.1 step 5, 5

### 11. Record the trajectory of every start (REQUIRED) (`record_trajectory`, deterministic)

For every fit step and every start, write one JSON line per objective evaluation to steps/<step>/<start>/trajectory.jsonl: evaluation index, wall time, optimizer stage, objective (log posterior or log-likelihood, named), its components (ZPF, activities, fixed-configuration properties split into thermochemistry, one-shot anchors and S_ex where the objective allows, hinge, prior), and the full parameter vector in physical units with the symbol names. Record the topology class wherever a diagram is evaluated (at least start and end). Existing campaigns without histories are shown start -> end only, labelled "trajectory not recorded".

- **Inputs:** `fit_liquidus.starts`, `fit_thermo.starts`, `fit_solid.starts`
- **Tool:** fit.py trace writer — `written by scripts/fit.py itself (steps/<step>/<start>/trajectory.jsonl, one JSON line per evaluation; topology every TOPO_EVERY evaluations); verify with python3 protocols/tools/check_trajectory.py steps/<step>` (Cu-Zr fit_step.py writes trace.jsonl per start; Cr-Ni fit.py records trajectory.jsonl since 6 Nov 06:55)
- **Results:** `trajectory` steps/<step>/<start>/trajectory.jsonl [checks: one line per evaluation, parameter names stated]
- **Gates:** G5_trajectory_recorded
- *Rationale:* PI 6 Nov (dashboard trajectory and model-space evolution)

## Physics checks and the final ranking

*Rationale: fit_protocol 0.3, 0.4c, 9, 13*

### 1. Physics checks of the final candidates (`physics_checks`, deterministic)

For the final pick (and the runner-up): liquid convexity over the declared domain (min d2G/dx2 by T; no spurious liquid gap unless sources report one); metastable gaps of each solution (chemical spinodal top, coherent spinodal with Cahn's term, metastable binodal, incoherent T_c estimates); unary limits (excess terms vanish at the end points; stable pure phases equal SGTE); stable same-phase gaps.

- **Inputs:** `ambiguous_structures.step5`, `pick_solid.pick`
- **Tool:** physics.py — `<fit-python> scripts/physics.py tdb/<final>.tdb results/physics_final.json`
- **Results:** `physics` results/physics_final.json
- **Gates:** G2_pure_elements
- *Rationale:* fit_protocol 0.4c, 9

### 2. Expected vs calculated assemblage at every observed state (`evaluate_states`, deterministic)

For the pick TDB, compute the equilibrium assemblage (pycalphad, P = 101325 Pa) at every state of the evidence bundle, fit and coverage, and record expected vs calculated phases, match, contains-expected and excluded phases present, with ORC ids, state ids and certainty tiers. Deterministic for a fixed TDB and pycalphad build.

- **Inputs:** `pick_solid.pick`, `classify_certainty.states`
- **Tool:** evaluate_states.py — `<fit-python> -I protocols/tools/evaluate_states.py tdb/<final>.tdb assessments/<artifact>/evidence/states.json assessments/<artifact>/evidence/states_evaluated.json --nproc 4`
- **Results:** `states_evaluated` assessments/<artifact>/evidence/states_evaluated.json [checks: every state evaluated or listed as skipped, byte-identical on rerun]
- *Rationale:* fit_protocol 13 (unrestricted equilibrium over the declared phase set); PI 6 Nov (per-state agreement)

### 3. Residuals by dataset at the pick (`per_dataset`, deterministic)

Compute residual/sigma per dataset file at the pick (rms, max, mean, n), every data group, and write them.

- **Inputs:** `pick_solid.pick`, `weights_from_sigma.weighted_datasets`
- **Tool:** per_dataset.py — `<fit-python> scripts/per_dataset.py tdb/<final>.tdb results/per_dataset_<final>.json`
- **Results:** `residuals` results/per_dataset_<final>.json
- *Rationale:* fit_protocol 0.3 item 3

### 4. Name the final pick (`final_pick`, judgement)

State the plausibility thresholds (already in PLAN.md), rank the accepted step picks and their runner-ups, look at the diagram of the pick, and copy it to tdb/<System>_<campaign>_FINAL_<step>_<start>.tdb. Misses against experiment and the MLIP are listed as notes, not as rejections.

- **Inputs:** `physics_checks.physics`, `per_dataset.residuals`, `pick_solid.pick`
- **Tool:** evaluate.py + summarize.py — `<fit-python> scripts/summarize.py`
- **Results:** `final_tdb` tdb/<...>_FINAL_<step>_<start>.tdb [checks: sha256 recorded]; `step_summary` results/step_summary.json
- **Decision rule:** rank fits, pick the reasonable one; topology first among fits with plausible energies; a right topology bought with implausible energies does not win — **decided by** campaign coordinator proposes; PI accepts the pick for release
- *Rationale:* fit_protocol 0.3; rank-models-pick-reasonable

## Uncertainty (Laplace mixture; MCMC only if separately approved)

*Rationale: fit_protocol 0.6, 13; Cr-Ni PLAN "cheap UQ"*

### 1. Collect the distinct optima (`modes`, deterministic)

From the final step's multistart (plus restarts from perturbations of the pick if needed), group the converged starts into distinct modes by objective and parameters, and write results/uq/modes_<step>.json.

- **Inputs:** `final_pick.final_tdb`, `fit_solid.starts`
- **Tool:** laplace.py (mode list) — `<fit-python> -c "import json; m=json.load(open('steps/<step>/multistart.json')); m=[x for x in m if x['final']=='converged']; m.sort(key=lambda x:-x['logpost']); modes=[]; [modes.append(x) for x in m if all(abs(x['logpost']-y['logpost'])>0.5 for y in modes)]; json.dump([{'name':chr(65+i)+'_'+x['start'],'theta':x['theta'],'logpost':x['logpost'],'grad_norm_q':x['grad_norm_q']} for i,x in enumerate(modes)], open('results/uq/modes_<step>.json','w'), indent=1)"` (distinct modes = converged starts more than 0.5 log-units apart (the Cr-Ni modes_step4.json rule))
- **Results:** `modes` results/uq/modes_<step>.json
- *Rationale:* fit_protocol 13

### 2. Laplace approximation at each mode and mixture weights (`laplace`, numerical)

At each mode compute -H by central differences of the analytic gradient at the two relative steps, symmetrise, and repair soft directions along the three softest eigenvectors when -H is not positive definite. Mixture weights: log w_k = logpost_k + d/2 log 2 pi - 1/2 log|-H_theta|. Draw laplace_draws parameter vectors from the mixture (fixed seed) and the independent-marginal counterexample.

- **Inputs:** `modes.modes`, `param:laplace_hessian_steps`, `param:laplace_draws`
- **Tool:** laplace.py — `cd <campaign> && PYTHONPATH=<home>/src/PhaseForgePlus/src <fit-python> scripts/laplace.py steps/configs/<step>.json results/uq/modes_<step>.json results/uq/laplace_<step>.json 1000`
- **Results:** `laplace` results/uq/laplace_<step>.json + laplace_<step>.draws.npy
- **Tolerance:** mixture weight of the main mode on a rerun: absolute 0.01 
- **Tolerance:** eigenvalues of -H in q: relative 0.05 
- *Rationale:* fit_protocol 13

### 3. Classify the draws and propagate (`classify_draws`, numerical)

Classify every draw on a 5 K grid over the declared T range: accepted topology (strict, and apart from narrow windows declared in PLAN.md), gaps by phase, spurious fields, invariant temperatures; report probabilities with binomial errors, and the independent-marginal comparison.

- **Inputs:** `laplace.laplace`
- **Tool:** classify_draws.py — `<fit-python> scripts/classify_draws.py results/uq/laplace_<step>.draws.npy results/uq/classified_mixture_draws.json`
- **Results:** `uq_summary` results/uq/classified_mixture_draws.json
- **Tolerance:** P(accepted topology) on a rerun with the same draws: absolute 0.0 
- **Tolerance:** P(accepted topology) on a rerun with new draws: absolute 0.03 
- *Rationale:* fit_protocol 0.6, 13

### 4. MCMC only if separately approved (`mcmc_optional`, judgement)

MCMC is not part of this protocol by default. If the PI approves it for a campaign, follow fit_protocol 0.6 (ESPEI's own likelihood on CPU; approved Sparks spark1, spark2, spark3, never spark4; Vision needs the PI's go; walkers at MAP + a ball scaled by the Laplace covariance; convergence rules fixed before sampling; above ~12 h stop for a decision).

- **Inputs:** `classify_draws.uq_summary`, `param:mcmc_stop_hours`
- **Tool:** ESPEI 0.9.0 MCMC (calphad-uq) (only with a recorded PI approval)
- **Results:** `mcmc` results/uq/mcmc_* (when approved)
- **Decision rule:** run only with a PI approval recorded in decisions — **decided by** PI
- *Rationale:* fit_protocol 0.6; phaseforge-plus-gradient-only

## Packaging and reproducibility (no orphan TDBs)

*Rationale: fit_protocol 14; Y32 (ORCHID_COORDINATION.md 30 Oct); full-reproducibility*

### 1. Write the TDB header block (`tdb_header`, deterministic)

Prepend a comment block to the released TDB: protocol id@version (specific and general), run id of the pick, code commits, environment lock hash or container digest, sha256 of every input (unary source TDB, ORCHID evidence commit and evidence digest, MLIP weights), objective and weights, gates passed, and the reproduce command. The body below the header stays byte-identical to the pick TDB; record both hashes.

- **Inputs:** `final_pick.final_tdb`
- **Tool:** tdb_header.py — `python3 protocols/tools/tdb_header.py protocols/specific/<artifact>@<version>.yaml release/<artifact>.tdb --code-commit <orchid-sage commit> --release <ORCHID release tag>`
- **Results:** `released_tdb` release/<artifact>.tdb [checks: body sha256 = pick sha256]
- *Rationale:* Y32 TDB header rule

### 2. Write the specific protocol and the run cards (`specific_protocol`, deterministic)

Write specific/<artifact>@<version>.yaml (instantiates this protocol; every override, the evidence selection with the evidence digest, the run sequence with failed attempts kept, decisions with dates and quotes, the artifact sha256, the acceptance target) and one run card per run (run_cards/), converted from the campaign's own run cards (never recomputed). Pin hashes with tools/pin_hashes.py and validate with tools/validate.py.

- **Inputs:** `final_pick.final_tdb`, `final_pick.step_summary`, `record_trajectory.trajectory`
- **Tool:** backfill_run_cards.py + validate.py — `python3 tools/backfill_run_cards.py && python3 tools/pin_hashes.py specific/<file>.yaml && python3 tools/validate.py`
- **Results:** `specific` specific/<artifact>@<version>.yaml + run_cards/*.json [checks: validator passes]
- **Gates:** G6_no_orphan, G7_inputs_hashed
- *Rationale:* Y32 specific protocol

### 3. Build the assessment dashboard (REQUIRED, frozen snapshot of the pick) (`dashboard`, deterministic)

Extract the assessment-results document (dashboard data) from the campaign files with the system's extractor (no recomputation; anything not on disk is shown as pending), validate it, and render the standalone HTML with tools/build_dashboard.py in frozen-snapshot mode: pick diagram with the fitted data, step sequence and per-step table, assemblage agreement map, invariant scorecard with ORCHID ids, objective components, per-dataset residuals, one-shot energies moved in sigma, physics checks, trajectory timeline and model-space projection, UQ, decisions, next actions and ORCHID intake, provenance with sha256. No external network.

- **Inputs:** `final_pick.final_tdb`, `final_pick.step_summary`, `record_trajectory.trajectory`, `physics_checks.physics`, `per_dataset.residuals`, `evaluate_states.states_evaluated`, `classify_draws.uq_summary`, `specific_protocol.specific`
- **Tool:** extract_dashboard_data.py + build_dashboard.py — `python3 tools/extract_dashboard_data.py <system> dashboards/<artifact>/dashboard_data.json && python3 tools/build_dashboard.py dashboards/<artifact>/dashboard_data.json dashboards/<artifact>/dashboard.html --snapshot`
- **Results:** `dashboard` dashboards/<artifact>/dashboard.html + dashboard_data.json [checks: validates against assessment-results.schema.json, renders offline, readable at 360 px width]
- **Gates:** G8_dashboard_present
- *Rationale:* PI 6 Nov ("should also be something delivered in each assessment"); fit_protocol 14 Required HTML campaign report

### 4. Build the Workflow Run RO-Crate (`crate`, deterministic)

Build crates/<artifact>/ with tools/build_crate.py: ro-crate-metadata.json (RO-Crate 1.1, Workflow Run Crate and Process Run Crate profiles; the specific protocol as the main workflow, its HowToSteps, one CreateAction per run card with object = inputs and result = outputs, restricted inputs as hash-only contextual entities), the protocol rendered as HTML and Markdown, the dashboard, the run cards and the artifact.

- **Inputs:** `specific_protocol.specific`, `dashboard.dashboard`
- **Tool:** build_crate.py — `python3 tools/build_crate.py specific/<artifact>@<version>.yaml crates/<artifact>`
- **Results:** `crate` crates/<artifact>/ro-crate-metadata.json + preview [checks: every hasPart file exists with its sha256; no restricted file inside]
- *Rationale:* Y32 standards

### 5. Independent rerun on another machine (`independent_rerun`, numerical)

Re-execute the specific protocol on a different machine (Studio vs MacBook vs Spark) from the hashed inputs, compare deterministic outputs byte for byte and numerical outputs against the tolerances, and attach the comparison report. A protocol counts only after this passes; no calculated observation and no TDB enters a release without it.

- **Inputs:** `crate.crate`
- **Tool:** orchid_reproduce.py — `python3 protocols/tools/orchid_reproduce.py protocols/specific/<artifact>@<version>.yaml --root <fresh dir on another machine> --python <interpreter matching the lock> --pfp <PhaseForgePlus src at c66656f> --nproc 4 --report reproduce/<artifact>/comparison.json`
- **Results:** `rerun_report` reproduce/<artifact>/comparison.json
- **Tolerance:** invariant temperatures of the reproduced diagram: absolute 2 K
- **Tolerance:** stable phase sequence on heating at each composition of a 0.01 grid: categorical_identical
- **Gates:** G9_independent_rerun
- *Rationale:* Y32 addendum (PI 30 Oct "the name of the game is full reproducibility")

### 6. Prepare the ORCHID contribution package (`orchid_intake`, deterministic)

Export every new or derived item (extractions, interpretations, campaign-added exclusions, computed observations with produced_by) to the ORCHID intake with provisional ids and review status; distinguish prepared, delivered, merged and released. Nothing is published without the PI's go.

- **Inputs:** `evidence_ledger.ledger`, `crate.crate`
- **Tool:** prepare_intake.py — `python3 protocols/tools/prepare_intake.py assessments/<artifact>   # writes assessments/<artifact>/intake/ (prepared, not delivered)`
- **Results:** `intake` contribution_manifest.json + export ledger [checks: every new item accounted for]
- *Rationale:* fit_protocol 4, 14

## Gates (hard)

- **G1_software_build** — espei.__version__ printed from the fitting interpreter equals 0.8.11.dev82+g9039ea215 in every run card
- **G2_pure_elements** — pure-element limits: SGTE phase sequence and melting points reproduced; ordered end-members equal their disordered parent; a violation fails the artefact (unary-limits-fixed)
- **G3_data_consistency_run** — results/data_consistency.json exists for every dataset that enters the objective (flags only; the gate is that the check ran)
- **G4_exclusions_present** — every observed state has excluded phases (a hinge cell) or a listed reason why not (fit_protocol item 8: a dataset without them is incomplete)
- **G5_trajectory_recorded** — every start of every fit step has a trajectory record (PI 6 Nov); back-filled campaigns are labelled "trajectory not recorded"
- **G6_no_orphan** — the TDB ships with its specific protocol, run cards and evidence subset (Y32)
- **G7_inputs_hashed** — every input and output that exists on disk is referenced with its sha256 and the hashes match (validate.py)
- **G8_dashboard_present** — the frozen dashboard of the pick is in the package and validates (PI 6 Nov)
- **G9_independent_rerun** — an independent rerun on another machine is within the tolerances (Y32; required before release, not before fitting)

## Ranking criteria (soft)

- **R1_plausible_energies** — filter first: compounds within ~10 kJ/mol-atom of the one-shot/MLIP values; thermochemistry within roughly its uncertainty; no physically odd entropies; pure elements equal SGTE. A fit that buys topology with implausible energies does not win. State the thresholds before ranking.
- **R2_topology** — among plausible fits: right reaction types, right fields, no spurious phases; severity of a spurious phase by temperature (practical T worse than above boiling; artefacts above the gas-stability limit may be irrelevant)
- **R3_quantitative** — invariant temperatures (within 25 K of the observed values), then thermochemical RMSE by dataset; in-sample and held-out separately where a hold-out exists

## Tolerances

- deterministic outputs (datasets, hinge files, TDB from given parameters, run-card conversions, dashboard data): byte_identical
- MLIP energies (GPU): absolute 0.1 kJ/mol-atom (per cell and stage; same image and weights)
- optimiser result (same build, CPU, single thread): absolute 0.01 log-units (log posterior of the pick)
- fitted parameters: absolute (fit_protocol 10b - absolute per parameter from the observed spread (Cr-Ni 50 J/mol and 0.03 J/mol/K; Cu-Zr 0.05 kJ/mol and 0.03 J/mol/K); never relative)
- invariant temperatures of the final diagram: absolute 2 K
- phase sequence on heating over the declared T range at a 0.01 composition grid: categorical_identical

## Decisions

| date | who | decision | why | source |
|---|---|---|---|---|
| 2026-10-30 | PI | PhaseForge+ refinements use Brandon Bocklund's Gradient-based_update of Courtney Kunselman's gradient ESPEI; no MCMC or HMC fits | the gradient method is the capability ORCHID's CALPHAD vision rests on; MCMC/HMC on Cu-Zr were slow and unconverged | memory phaseforge-plus-gradient-only |
| 2026-10-30 | PI | pure-element limits from the unary data; ordered end-members equal the disordered parent; mandatory pure-element check | Y28 Co-Ga refits made B2 at pure Ga stable | memory unary-limits-fixed |
| 2026-10-30 | PI | full reproducibility: general protocol, specific protocol and run cards; no orphan TDBs — “the name of the game is full reproducibility” | no TDB in the field is strictly reproducible | ORCHID_COORDINATION.md Y32 (30 Oct 10:45-10:55); memory full-reproducibility |
| 2026-10-31 | PI | rank fits and pick the most reasonable one; no pass/fail gates on fits — “We should just rank models and pick the most reasonable one.” | strict criteria rejected all 15 Co-Ga fits | memory rank-models-pick-reasonable |
| 2026-10-31 | PI | MLIP/DFT error ~9-10 kJ/mol-atom: gates and sigmas never tighter | DFT itself is off from calorimetry by that much | memory dft-error-vs-experiment |
| 2026-10-31 | PI | staged relaxation (unrelaxed -> volume -> volume + ions -> full); never relax shape for the value; keep every stage | Y36 found collapsed shape-relaxed structures | memory mlip-relaxation-protocol |
| 2026-11-05 | PI | fit from the liquid down (one-shot, liquidus, thermochemistry, solid state, ambiguous structures) — “starting from the liquid down is a good strategy overall” | this is how expert assessors work; fewer phases at high T | memory calphad-fit-sequence-liquidus-first; fit_protocol 0.1 |
| 2026-11-05 | PI | weights come from uncertainties; no hand-set multipliers | Cr-Ni Pugliese activities at the ESPEI default bought the wrong topology | fit_protocol 0.2 |
| 2026-11-05 | PI | SGTE references for every end-member including mechanically unstable ones; no inflection detection | compatibility with existing databases | memory unary-limits-fixed; fit_protocol 0.0a |
| 2026-11-05 | PI | data consistency check required before fitting | one suspect activity among neighbours of 0.98-0.998 | fit_protocol 0.2a |
| 2026-11-06 | PI | one-shot frozen (fit_protocol 0.0a): m_scraps, staged relaxation, SMAX potential, SGTE, own or sqs2tdb RK fit, 100 ps liquid — “we cannot change things every time” | repeated over-reading of "the standard way" on 5-6 Nov | memory phaseforge-standard-run |
| 2026-11-06 | PI | cells that fail the lattice check at volume + ions take the midpoint of the unrelaxed-full interval with sigma = half-width | every mixed Cu-Zr SQS transformed with the shape fixed | fit_protocol 0.0a; memory phaseforge-standard-run |
| 2026-11-06 | PI | "held" never means fixed: held compounds stay free, anchored by their one-shot observation at its sigma | in Cr-Ni step 3 fixing CrNi2 left it stable above the liquidus | fit_protocol 0.1; memory exclusions-required-held-free |
| 2026-11-06 | PI | excluded phases required at every observed state, single-phase states included — “exclusion fields should have been there in the first place” | Cr-Ni set E lacked bcc exclusions; half of its posterior draws grew a spurious Ni-rich bcc field | fit_protocol item 8 |
| 2026-11-06 | coordinator | polish_starts after every fit step - converge each start (verified gradient) before the 10a pick; the threshold is never loosened | no Cr-Ni step-3b start and no Cu-Zr H1 start was converged; the analytic gradient of two term classes was found wrong (check_gradients) | coordinator message 6 Nov 2026; OPEN_QUESTIONS Q36, Q37, Q39 |
| 2026-11-06 | PI | convexity constraint gated by temperature (T_allow from SRO, vibrational and coherency-corrected T_c) | concavity may be real but metastable at low temperature | fit_protocol 0.4b (b2d612d) |
| 2026-11-06 | PI | hinge floor - each exclusion hinge scale sigma = max(certainty tier, the state T and x uncertainty converted to energy, as for sigma_DF) | Cr-Ni step 4c: 0 of 8 starts stationary without it, 8 of 8 with it, one mode, CrNi2 860 K vs 863 K observed | fit_protocol item 8 (commit bef0bae) |
| 2026-11-06 | PI | tiers per excluded phase (not per state); ZPF 100 for boundary records and 50 when replicated | the per-state 3x reading made every tie-line state uncertain (Cr-Ni 11/0/636) | fit_protocol item 8 |
| 2026-11-06 | PI | pick rule - converged starts only (gradient-norm threshold stated before fitting, default 1e-3), near-ties broken by the objective; reproduction tolerances absolute per parameter | Cr-Ni step 3b picked a different loosely converged start on another machine | fit_protocol 10a and 10b |
| 2026-11-06 | PI | certainty tiers for the energy scale of ZPF and hinge terms (10 / 50 / 100 J/mol-atom); observed states at confidence 1.0; the ESPEI 1000 J/mol ZPF default is gone | one honest energy scale per state instead of a software default | fit_protocol item 8 (6 Nov); coordinator message 6 Nov (3x rule = operational reading pending PI) |
| 2026-11-06 | PI | observed absence is a strong signal - exclusions at observed states at confidence 1.0; sigma 10 J/mol-atom where certain — “if a phase is not present, that is a very strong signal” | at option C the bcc exclusions at 17 observed Cr-Ni fcc states cost ~0.03 nats each and removed only a fifth of the spurious Ni-rich bcc field | fit_protocol item 8 (added 6 Nov 07:27) |
| 2026-11-06 | PI | excess electronic entropy of metallic liquids taken as zero, stated as an assumption — “Excess electronic entropy is likely zero” | likely zero for metallic liquids | memory hong-liu-entropy-correction; fit_protocol 0.0b |
| 2026-11-06 | PI | the assessment dashboard is a required deliverable of every assessment; a standard schema for the deliverable; trajectory and model-space evolution recorded | make the fit inspectable and reproducible | coordinator messages 6 Nov (this protocol) |

## Limitations

- The fit steps are implemented as campaign scripts (reference_fit_code), not a packaged tool; a system needs its own copies (system names, VV layout, topology definitions).
- The container image digest of the MLIP steps is not yet recorded; GPU MLIP results are reproducible only within the declared tolerances.
- The optimiser is deterministic only for a fixed build, thread count and hardware; across machines the tolerance rule applies.
- Topology classification uses campaign-specific checks (Cu-Zr judge.py T1-T5, Cr-Ni pd4.topology); pd-graph certification is not yet part of the protocol.
- The liquid entropy correction (pair/quasi-chemical chemical term) is provisional until a human check and the authors' review.
- The ZPF driving-force scale is ESPEI's default (1000 J/mol); converting each record's sigma_T is under test on Cr-Ni (6 Nov).
- The ZPF energy scale of the 6 Nov picks is still ESPEI's default; the certainty tiers apply from the reruns on.

## Open questions

See OPEN_QUESTIONS.md: Q01, Q02, Q03, Q04, Q05, Q32, Q33, Q07, Q08, Q09, Q10, Q11, Q12, Q13, Q14, Q15, Q16, Q17, Q18, Q19, Q20, Q21

## Citations

- C. Kunselman, B. Bocklund, A. van de Walle, R. Otis, R. Arróyave, Analytically differentiable metrics for phase stability, Calphad 86 (2024) 102705, doi:10.1016/j.calphad.2024.102705
- B. Bocklund et al., ESPEI for efficient thermodynamic database development, modification, and uncertainty quantification, MRS Communications 9 (2019) 618, doi:10.1557/mrc.2019.59
- Y. Hong, Z.-K. Liu, Physical Review Research 7, L012030 (2025), doi:10.1103/PhysRevResearch.7.L012030 (liquid entropy; chemical-mixing term corrected by ORCHID)
- J. W. Cahn, On spinodal decomposition, Acta Metallurgica 9 (1961) 795 (coherent spinodal)
- A. T. Dinsdale, SGTE data for pure elements, Calphad 15 (1991) 317, doi:10.1016/0364-5916(91)90030-N
