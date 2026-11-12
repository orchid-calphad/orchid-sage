# Open questions for the PI (protocols, 6 Nov 2026)

Questions found while encoding `docs/fit_protocol.md` (sha256 703ddbf6…, as of 6 Nov 06:16 CST) as `general/orchid-calphad-fit@2.0.0.yaml`, back-filling the Cu–Zr and Cr–Ni specific protocols, and doing the cold read. None is resolved silently in the YAML: where a choice had to be written down, the YAML records the campaign practice and names the question. Q06 was dropped while writing (it duplicated Q05), so the numbering skips it.

## A. fit_protocol.md: ambiguities and self-contradictions

### Q01
> **Status 6 Nov (reproducibility pass): RESOLVED (housekeeping): fit_protocol.md header now reads Version 2.1 — 2026-11-06 and names the executable YAML; no science change.**

**Version label.** The header reads "Version 2.0 — 2026-11-05". The text also holds the 6 Nov changes (0.0a frozen, the midpoint rule, "held never means fixed", item 8 extended to every observed state, the electronic-entropy assumption). With no new version, "2.0" names two different texts. The YAML calls itself 2.0.0 and pins the prose by sha256. Proposal: call the prose 2.1 (or 2.0.1) and add a change log line for 6 Nov.

### Q02
**"No pass/fail gates" against "gate".** Section 0.3 says "There are no pass/fail gates on a single number". Item 3 then reads "invariant temperatures (gate and within 25 K)". Here "gate" is the Cu–Zr paper's 13-invariant count (`evaluate_step.py`), not a general concept. Section 14, the Y32 cards and unary-limits-fixed ("a violation fails the artefact") do use hard gates. The YAML separates hard **gates** (process and identity checks: software build, pure elements, exclusions present, hashes, dashboard, rerun) from soft **ranking criteria** (R1–R3). Please confirm that split, and say what "gate" in 0.3 item 3 means in general.

### Q03
**Electronic entropy.** Table 0.0b says excess electronic entropy is "taken as zero for metallic liquids, stated as an assumption (PI, 6 Nov)". Section 10.D says "Missing electronic or configurational contributions remain unknown rather than zero." The YAML follows 0.0b, because it is the later PI decision. Section 10.D should be rewritten to match.

### Q04
**State tolerance τ.** Item 8 sets the default τ to 100 J/mol-atom. Section 7 says "There is no universal 10 or 100 J/mol margin". Item 8 reconciles the two in one clause: Section 7 applies to sensitivity, not to the default. A third value adds to the confusion: the espei/SCHEMA.md hinge section says PhaseForge+ defaults to 50 J/mol-atom. Both campaigns pass margin 100 explicitly. Please confirm 100 as the protocol default and say whether Section 7 is to be reworded.

### Q05
**Option C settings.** In 0.4a, the exclusions assumed from a diagram use σ 1000, τ 100 and confidence 0.5. These are marked "coordinator choice, pending PI confirmation". Both campaigns use them, and the YAML records them as a parameter with that status. Are they confirmed?

### Q07
**Redlich–Kister order of the one-shot.** 0.0a and 0.0b say "RK fit … sqs2tdb or own documented fit" and give no number of terms. The Cr–Ni PLAN (PI ruling, 5 Nov) reads `sqscal` as using terms "1,0 / 2,0", so L0 only for the solutions and the liquid, with L0+L1 "a diagnostic". The Cu–Zr builder states sqs2tdb default terms "1,0 / 2,1" = L0 + L1 and uses L0 + L1. The Cr–Ni one-shot TDB (`build_tdb.py`, full-range fit) also has L0 + L1 for bcc and fcc, but only L0 for the liquid. Which order is the protocol default for the solutions and for the liquid?

### Q08
**σ_MLIP value.** 0.0a says σ_MLIP comes from `dft-error-vs-experiment`, with no number. Both campaigns use 9.687 kJ/mol-atom from `orchid-phaseforge-demo/results/sigma_mlip.json`, built from 8 Cu–Zr MP pairs. The memory note `dft-error-vs-experiment` says "Y28b σ_MLIP = 13.75". Is 9.687 the protocol value for every system, or should σ_MLIP be calibrated per system?

### Q09
**"Structure kept" for compounds under the midpoint rule.** 0.0a defines the lattice check for SQS cells. For compounds, Cu–Zr run 2 used "the s2 space group equals the prototype's". That was a coordinator decision, labelled as such; Cu51Zr14 keeps P-6 but moves 0.14 d1. Should this become the protocol rule?

### Q10
**"Held never means fixed" against the free sets.** Section 0.1 says every held phase stays free. Both picks still had parameters outside the free set:
- Cr–Ni step 2: CRNI2 a,b.
- Cu–Zr step 2 and H1: 7 symbols.
- Cu–Zr H2: VV0007 and VV0015.

Are b-terms the model never introduced (L1 b of bcc/hcp in Cu–Zr) "held", or simply not in the model? The YAML marks these overrides as `conforms: false`.

### Q11
**ZPF weight.** 0.2 reads "Every observation enters the likelihood with the weight implied by its own uncertainty". The 0.2a item 1 check requires that none "sits at a software default". The ZPF driving-force scale is still ESPEI's default of 1000 J/mol in both picks, and the conversion of σ_T is under test on Cr–Ni. Until that test ends, should 0.2 say explicitly that ZPF is the one exception?

### Q12
**Ranking when nothing is plausible.** 0.3 makes plausible energies a filter. In Cu–Zr H2, 0 of 8 starts pass every plausibility check (HM_FORM RMSE 5.17–6.20 > 5), and `rank_protocol.py` ranks by the number of checks passed. Cr–Ni step 4 is "plausible: false" too: the fcc one-shot values moved more than 10 kJ, and bcc S_ex is above 2.5. Should 0.3 say what happens when the filter empties the set: rank by checks passed, or fall back to topology?

### Q13
**Window of item 3.** "Within 25 K" does not say of what. Cu–Zr compares with Wang 2006 experimental values; Cr–Ni compares with the ORCHID records. Proposal: within 25 K of the ORCHID invariant record (its σ shown), with other sources as notes.

### Q14
**Stop threshold.** 0.6 says "Above ~12 h, stop for a decision". The Cr–Ni one-shot plan used 24 h ("below the ~24 h stop threshold → proceed"). Is the threshold for MLIP/GPU blocks different from the threshold for fits and MCMC?

### Q15
> **Status 6 Nov (reproducibility pass): RESOLVED (housekeeping): Section 10 now names MLIPentropy (PR #11, a08ff3e; campaigns ran 9e8140b), marks 77204fd as historical and the 24 Oct pilot as superseded; 10.B points to the 0.0a campaign implementation.**

**Section 10 is out of date.** It names `orchid/liquid-entropy-protocol @ 77204fd`, the archived pilot scripts, and "configurational chemical-mixing calibration remains unresolved". The current estimator is `MLIPentropy` (PR #11, a08ff3e; campaigns used 9e8140b), with the pair (quasi-chemical) correction. Section 10.B names `sqscal` as the entry point, but 0.0a withdrew the `sqscal` defaults. Section 10 should be updated.

### Q16
> **Status 6 Nov (reproducibility pass): RESOLVED (housekeeping): Section 14 keeps the contract names and adds a column with the files the campaigns actually write (protocols/SCHEMA.md family, evidence bundle, dashboards, intake). phase_mapping.json is still not written (listed as pending).**

**Section 14 file names.** The table lists `fit_spec.yaml`, `evidence_ledger.jsonl`, `objective_spec.json`, `status.html`, etc. as "an illustrative integration contract". Neither 6 Nov campaign writes most of them. The new schema family covers several of them (specific protocol, run cards, assessment results, dashboard). Should Section 14 be rewritten to point at protocols/SCHEMA.md, keeping the ledger files as required separate outputs?

### Q17
**UQ method.** fit_protocol.md has no Laplace-mixture section. Laplace appears only to scale the MCMC walker ball in 0.6. The general YAML encodes the Cr–Ni practice: Laplace at each mode, mixture weights, 1000 classified draws, no MCMC by default. Please confirm that this belongs in the general protocol.

### Q18
**Physics checks scope.** 0.4c makes Cahn and the incoherent T_c estimates "default heuristics" for solid solutions. Section 9 makes liquid convexity conditional on the source evidence. The Cu–Zr picks have neither check. Are both required for every pick, or only when a gap is suspected?

### Q19
**Multistart rule.** fit_protocol.md does not specify the start generation. The memory note `phaseforge-plus-gradient-only` (PI, 30 Oct) says "start 0 MLIP-centred, the rest Latin-hypercube within priors … check that the best basin is reached by at least 2 starts". Both 6 Nov campaigns used multiplicative Gaussian perturbations (a(1+0.1N), b+N(0,3), seed 1000+k). The superseded card `orchid-automated-assessment@0.1.0` names basin hopping as the default (PI, 31 Oct). Which rule is the protocol rule?

### Q20
**Prior.** The Cr–Ni objective has a weak Normal prior centred at the one-shot (50 kJ, 30 J/K), "so that the Laplace step has a proper posterior". The Cu–Zr objective has none. fit_protocol.md does not mention a prior; Section 11 asks to "separate likelihood terms from priors". Should the general protocol require the weak prior?

### Q21
**Sequence order against the H series.** 0.1 prescribes 2 → 3 → 4 → 5. After the 5 Nov PI decision, Cu–Zr went 2 → H1 (liquidus + hinge) → H2 (all data), with steps 3–4 as a side branch. 0.4 ("add ZPF evidence") allows a labelled extra step. Is replacing 3–4 by H1/H2 conforming to 0.1, or a system-specific override?

## B. Specific protocols: gaps the cold read could not close

### Q22
> **Status 6 Nov (reproducibility pass): CLOSED: image id sha256:ac223e2cfa3e… recorded; Dockerfile recorded; the image is archived on spark1 (cuzr-phaseforge-grace-gpu_20261104.tar.gz, sha256 74e140ed…); GRACE weights hashed in all three run roots and traced to their Hugging Face sources and tags (protocols/environment/pins/PINS.md). spark2 and spark3 hold an independent build of the same Dockerfile (image id 8eae0b91…) with an identical pip freeze.**

**Cu–Zr container and weights.** No digest or Dockerfile for `cuzr-phaseforge-grace-gpu:20261104`. The GRACE model files are hashed (`potential_sha256.txt`) but have no stable public location (Y32 asks for Zenodo, R2 or git). A third party cannot rebuild the MLIP steps. Can we record the digest on spark1 (`docker image inspect`) and deposit the image recipe and the weights' source?

### Q23
> **Status 6 Nov (reproducibility pass): PARTLY CLOSED: interpreter locks for every environment and the per-cell raw relaxation results are referenced through the run cards; the run-1 SQS POSCARs and collected_solids result.json files are not yet hashed one by one (they sit unchanged in the campaign directories).**

**Cu–Zr raw MLIP outputs.** `collected_solids/<model>/<lattice>/<cell>/result.json` (the input of the one-shot builder) and the 60 SQS POSCARs are not hashed one by one in the specific protocol; only the summaries are. Run 2 reads the same files. Should they be hashed now (cheap), before anything moves?

### Q24
> **Status 6 Nov (reproducibility pass): CLOSED: the spark1 copy is file-by-file identical to the Studio's PhaseForgePlus checkout @ c66656f (406 files).**

**Cu–Zr PhaseForgePlus copy on spark1.** The hinge code ran from the campaign's own PhaseForgePlus copy on spark1 (`runs/cuzr-protocol-oneshot-20261106/src/PhaseForgePlus` in its home directory), and its commit is not in the run cards. c66656f is assumed. Can the rerun agent record it?

### Q25
> **Status 6 Nov (reproducibility pass): PARTLY CLOSED: the Cr–Ni evidence is frozen as a hashed bundle in the repo (assessments/crni-paper-fit-step4-s1/evidence/, derived facts only), and the ORCHID intake for v2027.01 is prepared (intake/intake_manifest.json: 29 ORC ids absent from the Y25 registry, 59 set-E files without ORC ids, 318 campaign-added exclusions, the one-shot observations). It becomes citable by release only after delivery and the January release (PI go). ORC-SV7H3CNRYS is already in the released registry.**

**Cr–Ni evidence is not an ORCHID release.** Set E (cr-ni-rebuild, ESPEI example datasets with ORCHID-rule σ) and two records read from private exports (ORC-X3KVP7D3PO single reader; ORC-SV7H3CNRYS accepted) are not in a release or a git commit. The badge and the data statement need "the exact tag of the records used". Should set E and the two records be exported to orchid-data-next and tagged before the paper?

### Q26
**Cr–Ni step-4 exclusions.** The pick used `step4_hinge.json` (set E cells + 17 Pugliese γ + 11 Curie). The completion to every observed state (`build_hinge_complete.py`) came later and is in the running tests. Is the paper pick the current step 4, or the test that adds the completion?

### Q27
**Cr–Ni topology acceptance.** The stated window for CrNi2 (800–930 K) is missed: the top is at 780 K. Under "rank, don't gate" the pick stands, and the dashboard shows "Right topology: no" for every step. Should the paper report the miss as a note, or wait for the ZPF-σ test?

### Q32
**Observed absence, added to item 8 at 07:27 on 6 Nov.** Exclusions at observed states now enter at confidence 1.0, with σ 10 J/mol-atom where the absence is "certain" and otherwise the state's own σ converted to energy. Three points need settling:
- Who decides "certain", and by what test? The YAML says the coordinator proposes and the PI confirms.
- How does one tell an exclusion at an observed state from one "assumed from a diagram" when the observed state's assemblage is itself read off a diagram (Pugliese γ states inferred from Table III limits; Cu–Zr exclusions built from ZPF rows by the stable-elsewhere rule)?
- Both picks used option C (0.5) everywhere, so neither conforms (Cr–Ni override marked `conforms: false`).

### Q33
> **Status 6 Nov: RESOLVED by the PI (fit_protocol item 8: tiers per excluded phase; ZPF 100, 50 when replicated). Implemented in build_evidence_bundle.py as certainty-tiers@2; bundles rebuilt as NEW versions 2.0.0 (v1 kept). Readings used where the rule leaves room, for the PI to see:**
> - **"diagram-assumed"**: the state is an assessed-diagram point (Cr–Ni set E, Cu–Zr dense/assessed grids).
> - **"single-source"**: no other independent source has a state within 3σ that also lacks the phase. **Superseded 7 Nov 2026 by the PI** ("Yes" to "only Pugliese, as the fit used"): a dataset is single source only when it is the only report of that measurement and is designated so in the plan before fitting, with its reason; there is no automatic 3σ-neighbour rule (fit_protocol item 8; orchid-calphad-fit@2.1.1). The frozen bundles 2.0.0 of Cu–Zr and Cr–Ni step4-s1 were built with the 3σ reading and stay as built.
> - **"contested"**: a state within 1σ reports the phase.
> - **single-phase ZPF states** (not boundary records): graded by the distance to the nearest observed boundary of their own phase (>3σ 10, 1–3σ 50, ≤1σ 100); assessed points are never below 50.
>
> **Counts, ZPF / exclusions (certain, less certain, uncertain):**
> - Cr–Ni: 145/72/430 and 495/280/9.
> - Cu–Zr: 21/179/168 and 258/7/1.
>
> **The old per-state counts:** Cr–Ni 11/0/636; Cu–Zr 79/51/238.

**Certainty tiers: the operational reading.** The tiers are implemented as stated by the coordinator (more than 3x the state's own T/x σ from the nearest observed boundary = certain, 1–3x = less certain, otherwise uncertain). Three consequences need the PI's eye:
- Every ZPF tie-line or invariant vertex lies on a boundary by definition, so all of them are "uncertain" (100 J/mol-atom). Only single-phase and excluded-phase states can be certain. This gives Cr–Ni 11 certain, 0 less certain, 636 uncertain, and Cu–Zr 79 / 51 / 238.
- σ_T and σ_x default to the ORCHID 'unknown' class (16 K, 0.011) when a record has no budget.
- "Conflicting" is tested only between single-phase states within 1σ.

Is this the intended reading?

### Q34
> **Status 6 Nov: RESOLVED (fit_protocol 10b). Both specific protocols state absolute per-parameter tolerances in acceptance_target and in every tdb_abs check (Cr–Ni 50 J/mol, 0.03 J/mol/K; Cu–Zr 0.05 kJ/mol, 0.03 J/mol/K); no relative tolerance remains.**

**Tolerance for refitted parameters.** The independent rerun of Cr–Ni step 2 on spark1 reproduced the objective to 4e-7, but one soft parameter (fcc L1 a) moved by 17 J/mol (5.6 % relative). Per-parameter relative tolerances are therefore the wrong rule. The specific protocols now use absolute tolerances in each parameter's unit, set from the observed spread with margin (Cr–Ni 50 J/mol on a-terms and 0.03 J/mol/K on b-terms; Cu–Zr 0.05 kJ and 0.03 J/K), plus the diagram checks of the acceptance target (eutectic, CrNi2 top within 2 K). Please confirm.

### Q35
**Cr–Ni step-4 code not retained.** `fit.py` and `model.py` were edited in place at 06:55 (trajectory recording) after the step-4 fit, so the exact code of the pick is lost. The snapshot holds the edited versions, and the independent rerun tests that they reproduce the pick. The brief to the rerun agents now forbids in-place edits after a run.

### Q36
> **Status, 6 Nov evening (polish_starts and the 10a rule, run on both machines): there is still NO eligible step-3b start. The threshold is not loosened.**
> - **Before polish:** 0 of 8 starts are below 1e-3 on either machine (spark1 |g| 0.079–0.22; Studio 0.066–0.22). The best objective is s1 −3941.8008 on spark1 and s7 −3941.8009 on the Studio.
> - **After polish:** L-BFGS-B was continued with the verified gradient (activity term by FD). It ended with 0 of 8 converged on spark1 and 0 of 8 on the Studio. Every start stalls at |g| 0.07–1.34 with an unchanged objective.
> - **Cause:** the endpoints sit on a kink of the activity term (Q39), where no gradient norm can be small.
> - **Consequence:** under 10a the step-3b pick is empty. The chains stopped before step 4, so the step-4 artifact is unchanged; under 10a it no longer has a valid lineage.
> - **Decision for the PI:** DR-convergence-nonsmooth in the Cr–Ni protocol.
> - **Records:** reproduce/crni-step3b-polish-{spark1,studio}/.

**Intermediate picks are not reproducible when the mode is flat.** In the independent Cr–Ni rerun on spark1, the final artifact (step 4) reproduces: logpost within 3e-9, every parameter within 0.2 % of its tolerance, eutectic 1620 K and CrNi2 top 780 K identical. The intermediate step-3b pick does not.

- **What happens.** The step-3b mode is flat in the bcc interaction terms and the CrNi2 a,b terms, and the starts converge only loosely (|g| 0.06–0.2). `evaluate.py` breaks near-ties between starts by grid quantities (topology, CrNi2 window). It therefore chose s1 (logpost −3941.819, CrNi2 top 1038 K) in the rerun, against s1 (−3941.801, 1074 K) originally. The rerun's best start, s6 at −3941.8008, matches the original pick's objective.
- **Why the step-4 pick still holds.** Step 4 starts from either step-3b pick and returns the same optimum.
- **Proposals:**
  1. require a gradient-norm threshold (e.g. |g| < 1e-3 in scaled coordinates) before a start can be picked;
  2. break ties within 0.05 log-units by the objective, not by grid quantities;
  3. declare intermediate picks numerical with a tolerance on the final artifact only.

  These are science/protocol choices for the PI.

### Q37
> **Status, 6 Nov evening (polish_starts, run 1's three H1 starts rerun on both machines):**
> - **H1 polish:** only s0 converges, on both machines (|g| 9.1e-4 on spark1, 7.3e-4 on the Studio). Its lnL is −2011.67491 on spark1 and −2011.67477 on the Studio, a difference of 1.4e-4. Starts s1 (run 1's pick) and s2 stall (|g| 0.15–91).
> - **The 10a H1 pick is s0 on both machines.** s0 fails topology check T3 (compounds at 300 K). Run 1 picked s1, which has the right topology but is unconverged. s0 is the pick only because it is the sole eligible start.
> - **Across machines:** after polish the two s0 points agree in objective. 10 of their 19 parameters are still outside the 10b tolerances (worst VV0033: 0.50 kJ, 16.8× the tolerance). Before polish the worst was 783×. The objective is nearly flat along those directions, so |g| < 1e-3 does not pin the parameters to 10b tolerances.
> - **H2:** started from the polished s0 on both machines.
>   - On spark1, before polish, the best H2 start is s0 at lnL −5336.46, 2.2 better than run 1's pick (H2 s7, −5338.67). The H2 polish is running at about 5 min per evaluation; after 37 evaluations the leading starts are at |g| ≈ 0.1.
>   - On the Studio, the H2 fits are running.
>   - The final 10a H2 pick and its cross-machine comparison are pending, so whether the final artifact changes is not yet established.
> - **Also observed:** run 1's own H2 s7, started from the identical reference H1 TDB, ends 1.29 lnL apart across machines (Studio −5337.378, spark1 −5338.671). The reproduce of 6 Nov is in reproduce/cuzr-oneshot-h2-s7-studio/.
> - **Records:** reproduce/cuzr-h1-polish-{spark1,studio}/, including cross_machine_h1_s0.json.
> - **H2 on spark1, finished 7 Nov:** 0 of 8 starts eligible, so the 10a H2 pick is empty.
>   - s0, s4 and s6 reached the 400-evaluation cap at |g| 0.03–0.04, all at lnL ≈ −5336.43 to −5336.44. That is one mode, better than run 1's pick by 2.2.
>   - The other five starts stalled (|g| 400–1800).
>   - The final artifact is therefore not replaced under 10a. A higher cap might reach 1e-3 for the three capped starts; that is a compute decision.
>   - Records: reproduce/cuzr-h2-polish-spark1/. The Studio H2 chain is still running.

**Cu–Zr H1 does not reproduce across machines (same cause as Q36).** On the Studio (6 Nov) step 2 s1 reproduces within tolerance: not byte-identical, worst parameter at 2e-4 of its tolerance. H1 s1 starts from an identical lnL (−27487.7237, agreeing to 1e-12) but ends elsewhere: lnL −2011.94 against −2012.26 on spark1, with VV0009 at 22.9 against 13.4. The start is not converged on either machine (|g| 0.058 and 0.16, against the 10a threshold of 1e-3). On spark1, the machine of run 1, H1 and H2 are byte-identical.
- Under 10a no H1 start of run 1 is eligible, so the H1 → H2 lineage of run 1 is not reproducible by rule.
- The run-2 campaign (cuzr-oneshot-run2) states the 10a threshold before fitting.
- The specific protocol marks h1_s1 and h2_s7 `expected: partial`.

### Q38
> **Status, later on 6 Nov.** Rule 0.4b is now encoded: the parameter convexity_T_allow and the temperature gate in same_phase_split. Three rules from b31a0ca are pinned in the rationale but are not yet steps or parameters: the per-record ZPF scale σ_DF, the smooth (softplus) hinge, and kinetically limited absences. Note that the smooth hinge addresses one source of the kinks in Q39. The activity-term kink of Q39 is a different source: it comes from equilibrium phase switches at activity data points.

**fit_protocol 0.4b (committed b2d612d, 09:21 on 6 Nov) is not yet encoded in the general protocol.** Rule 0.4b gates the convexity constraint by T_allow, taken from SRO, vibrational and coherency-corrected T_c. The general protocol's rationale_document is re-pinned to that version of fit_protocol.md, but no step or parameter carries 0.4b yet, and neither pick used it. It should become a parameter of the fit steps (T_allow and its basis), with a minor version bump of the general protocol, once the PI confirms the wording.

### Q39
> **RETRACTED, 6 Nov (late): the analytic gradient is correct; the endpoints are kinks.** Diagnosis in `protocols/reproduce/espei-gradient-q39/` (85de78a, `kinkcheck.py`, `endpoints_check.json`). At each endpoint one or more data points sit exactly on a model phase boundary (Cr–Ni 3b s1: Pugliese activity at x_Cr 0.35, 1073 K on FCC / FCC+CRNI2, and Katayama 1783 K on LIQUID / LIQUID+BCC; Cu–Zr H1 s1: the model's L + CUZR2 + BCC eutectic at exactly 1268 K, the Turchanin/Lundin invariant). Central FD there averages the two one-sided slopes, so "FD stable at two steps" cannot tell a kink from a bug; one-sided slopes can. On smooth residuals analytic and FD agree to 1e-9–6e-9; at nearby non-kink points the whole term agrees to ~1e-7. The central-FD substitution in polish_starts is therefore not a gradient either and should be withdrawn. Separate issue (Cu–Zr H1 s2): a ZPF hyperplane-vertex equilibrium fails to converge at θ* and ESPEI scores the region as zero driving force (`zpf_error.py:444-450`), so a failed equilibrium counts as a perfect fit; a design question for upstream. Remedy for kinks remains DR-convergence-nonsmooth (PI).
>
> **Status, later on 6 Nov: the FD-corrected gradient does not make the starts converge either.**
> - At the Cr–Ni s0 endpoint, a two-sided probe along the verified-gradient direction lowers the logpost on both sides. The drop is linear in the step from 1e-7 to 1e-3: −4.4e-9 and −2.0e-8 at a step of 1e-7. The activity term's one-sided slopes are +1.55 and −1.79.
> - So the endpoint is a kink of the activity term, not a smooth point that needs more iterations.
> - **Likely cause:** ESPEI computes activities from equilibrium chemical potentials at each data point. Their parameter derivative jumps where the stable assemblage at a point changes, which suggests the fit has pushed a phase boundary onto an activity point. I could not identify the point, because `get_residuals` is not implemented for activities in this build.
> - **Smooth starts do converge:** Cu–Zr H1 s0 converged on both machines.
> - **Options for the PI (DR-convergence-nonsmooth); none is implemented:**
>   - a non-smooth stationarity test (e.g. the minimum-norm sampled gradient within a ball);
>   - smoothing the activity term (as was done for the hinge in b31a0ca);
>   - excluding activity points that sit on a model phase boundary.

**The analytic gradient of two ESPEI term classes is wrong at the fit endpoints. This is the cause behind Q36 and Q37.** I compared each term's analytic gradient (gradient ESPEI 9039ea2) with central finite differences, at the endpoints, in the optimiser coordinates:
- **Cr–Ni step 3b, s1 endpoint (spark1).** ActivityResidual: |analytic − FD| = 1.35, against |FD| = 3.48. Every other term agrees to < 1e-4. The total true gradient norm is 1.32, against 0.079 analytic. Most of the difference is on the bcc and CrNi2 terms (VV0008–VV0013). The FD gradient is the same at steps 1e-3 and 1e-4.
- **Cu–Zr H1, s1 endpoint (spark1).** ZPFResidual: |diff| = 0.31, against |FD| = 8.69. The hinge, fixed-configuration and other terms agree to 3e-10. The total is 0.15 by FD against 0.43 analytic, because the ZPF and hinge gradients nearly cancel. The result is the same at FD steps 1e-4 and 1e-5.
- **What this explains.** L-BFGS-B is driven by the wrong gradient. Its line search stalls at points that are not stationary for the objective (a continuation with the analytic gradient alone stalled after about 50 evaluations on every Cr–Ni 3b start), and where it stops depends on rounding. Hence the machine-dependent endpoints of Q36 and Q37.
- **What the protocol does now.**
  - check_gradients is repeated at the endpoints of every fit step.
  - The term classes that fail it get central-FD gradients in polish_starts (1e-4 in optimiser coordinates).
  - The 10a eligibility norm is the norm of that verified gradient.
- **For the PI / Brandon.** The activity and ZPF gradients of the Gradient-based_update branch should be checked upstream. We do not patch ESPEI. The 0.9.0 comparison (fit_protocol 0.5) checks values, not gradients.

## C. Schema gaps (do-not-invent rule)

### Q28
**No JSON Schema file exists for literature records or states.** The schema family names ORCHID's fields exactly (`id` ORC-…, `state_id` S-…, `state_class_id` C-…, `excluded_phases`, the hinge cell keys, `uncertainty_budget.sigma_effective`) and copies their patterns. It cannot `$ref` them, because literature/SCHEMA.md and graph/SCHEMA.md are prose. A machine-readable ORCHID record schema would let these be `$ref`s.

### Q29
> **Linkage, 6 Nov (PI): every evidence state now carries `orchid_link` (present/missing), its ORC record ids, S-/C- state ids, release, and the chain record → state → paper DOI → locator from the orchid-data-next literature checkout. A missing link carries `missing_reason` and an `intake_ref` into intake/intake_manifest.json. validate.py reports coverage and fails when a claimed ORC id does not resolve.**
> - Cr–Ni: 1 of 647 states linked. 29 ORC ids are not in the registry or checkout. 60 set-E datasets have no ORC ids, and 318 exclusions were added by the campaign.
> - Cu–Zr: 91 of 368 states linked (64 records); 79 datasets have no ORC ids.
> - The data site has no per-record URL yet, so the dashboards link the record's paper DOI and show pid/locator.

> **Status 6 Nov (reproducibility pass): CLOSED for ORC-identified states: state ids come from the Y25 registry (branch Y25/state-ids-locator, graph/observations.parquet). Cu–Zr: 91 of 368 states mapped (all 125 ORC ids in the bundle map); Cr–Ni: 1 of 647 (set E rows carry no ORC ids). The rest wait for the intake.**

**State ids are missing in both picks' data.** The ESPEI datasets and hinge cells of both campaigns carry ORC ids, but no S-/C- state ids (the Y25 branch is not merged into the bundle). `states_evaluated` therefore cannot be keyed by state_id yet.

### Q30
> **Status 6 Nov (reproducibility pass): CLOSED: protocols/tools/evaluate_states.py (pycalphad, deterministic, byte-identical on rerun) evaluates every observed state; results in assessments/<artifact>/evidence/states_evaluated.json and in both dashboards. Cu–Zr H2 s7: 158/368 exact matches, 201/368 with the expected phases present; Cr–Ni step 4 s1: 353/647 and 522/647 (partial tie lines are judged by 'expected present').**

**Per-state assemblage agreement was not computed for either pick.** The Cu–Zr y36 campaign had it (`states.json`). The dashboard shows it as pending. Should it become a required step output (`evaluate_states`) of the general protocol?

### Q31
**Brand values.** The badge geometry is "PROPOSED (PI to confirm)" in orchid-brand figures.md. Light-theme `oqmd`, `assessed` and `unspecified` are below 3:1 on white (2.31, 2.25, 2.85). The brand handles this with markers and legends; neither dashboard here uses those three colours.

### Q40
> **Status 7 Nov: RESOLVED, pending PI approval of crni-paper-fit-step4c-b@1.0.3.** Cause: a write/read race on the shared cache file `data/cache/step3b_thermo_crni2free_pick_noCRNI2.tdb` (`model2.no_crni2_tdb`, `Path.write_text`) read by 4 spawned workers; an empty read silently dropped the 12 `zpf_susp` records (`reproduce/crni-paper-fit-step4c-b-1.0.2-spark1/q40/README.md`). Answers: (1) s1 alone and repeated is deterministic and equals the multistart value; (2) a fresh process per start is not needed (no carry-over); (3) yes, a mismatch is now a failure of the check (`check10a_ms2.py`, > 1e-6, exit 3). Fix in new versions only (`addendum-1.0.3`: `model3.py` builds the database in memory and fails closed on any lost record; `fit3.py`, `laplace3.py`, `run_global_crni2.py`, `check10a_ms2.py`); objective bit-identical to `model2` at all 8 endpoints on both machines; race probe 0 bad reads. Proof and rerun: `reproduce/crni-paper-fit-step4c-b-1.0.3-spark1/README.md`.

**The 10a re-evaluation at a fixed θ is not deterministic (crni-paper-fit-step4c-b@1.0.2 rerun on spark1, 7 Nov 2026).** The multistart endpoint of start s1 was bit-identical to the 1.0.1 rerun (logpost −5657.288636863667). `check10a_ms.py` (4 worker processes) re-evaluated it at −5657.288636863667 in 1.0.1, but at −5517.680257 with \|g\| 0.119 in 1.0.2: the same θ, the same machine, the same code, no failed equilibria, and the same 8 on-boundary points. s1 was therefore classed `not_stationary`, and the rule picked s2 of the same mode A, so the verdict (predictions) is still PASS. A plausible cause, not tested, is state carried by a worker from one start to the next (the start order differed: s1 took 453 s here and 1275 s in 1.0.1). Open questions:
- Re-evaluate s1 alone, and twice in one worker, to confirm or rule out the cause.
- Should 10a evaluate each start in a fresh process?
- Should the multistart's own objective be cross-checked against the 10a re-evaluation (a mismatch would be a failure, not an ineligible start)?

See `reproduce/crni-paper-fit-step4c-b-1.0.2-spark1/README.md`.
