# CALPHAD model fitting protocol for ORCHID-SAGE

Version: 1.9 — 2026-11-04  
Status: normative workflow for agents; proposed SAGE integration contract.

## 1. Purpose and authority

This protocol governs the construction, refinement, validation, and uncertainty analysis of CALPHAD models using experimental observations and computational evidence. Its purpose is to make the scientific decisions of a fitting campaign reproducible, including decisions about evidence that cannot yet be used. A low objective value alone does not establish that a model reproduces the observed equilibrium states.

**ORCHID is the mandatory first and primary source of evidence and project context.** Before assembling a fit, consult the relevant ORCHID records, phase registry, source documents, invariant and transition tables, assessed diagrams, available thermodynamic databases, extraction protocols, and coordination records. Consult the current release and relevant pending corrections. Original publications remain authoritative for checking whether an extraction faithfully represents its source.

Follow the user's prescribed fitting sequence. Adding evidence does not authorize silently changing model forms, weights, residual definitions, parameter bounds, or optimization methods. Record changes in a new version of the fitting specification and preserve the preceding version. Resolve routine choices within the authorized scope; request a scientific decision only when an unresolved choice materially changes that scope or the interpretation of the results.

SAGE currently supports model screening and calculation planning. This document does not assert that SAGE executes fits, authenticates publications, or implements the residuals described below. A proposed adapter should translate a versioned ORCHID snapshot into SAGE’s supported caller-supplied evidence representation, preserving identifiers, hashes, and review status. Native snapshot ingestion is not established here; retrieval, fitting, and database contributions require appropriate adapters or external workflows.

### Workflow order and checkpoints

Proceed through the following stages, reusing reviewed inputs and calculations when they already satisfy the requirements. This sequence defines scientific dependencies rather than requiring all work to run serially.

| Stage | Sections | Check before advancing |
| --- | --- | --- |
| Define scope and inventory evidence | 2–4 | ORCHID consulted; prescribed baseline identified; gaps and literature needs recorded |
| Validate evidence and phase representation | 5–8 | Identities, topology, all grid points, invariant rows and absence assertions accounted for |
| Plan physical constraints and obtain missing computational evidence | 9–10 | Required PhaseForge calculations accepted or explicitly held; references and uncertainties reconciled |
| Assemble and verify the objective | 11 | Evidence and residual versions frozen; reference or alternative checks completed; gradients verified where used |
| Execute the approved fitting strategy | 12 | Baseline preserved; candidate and cost tracking active; diagnostics determine any authorized escalation |
| Accept candidates and characterize uncertainty | 13 | Independent equilibrium and topology checks completed; uncertainty claims match sampling support |
| Archive and return evidence to ORCHID | 14–15 | Deliverables reconciled; review and contribution status accurately recorded |

Apply validation at the checkpoint where an error can first be detected, as well as at final acceptance. Evidence acquisition and calculation preparation may proceed concurrently when independent. New evidence received after a search starts belongs to a new version of the objective; it must not silently change an active trajectory. Unresolved optional evidence may remain held while the documented baseline proceeds, but its intended scientific claim remains unvalidated.

## 2. Establish the fitting specification

Prepare a run specification before launching optimization. Identify the chemical system, pressure, composition and temperature domains, intended application, candidate phases, and known limitations of the model. Specify phase constitution, sublattices, site ratios, ordering relationships, reference states, adjustable parameters, fixed terms, parameter units, bounds, and initialization provenance.

Distinguish three different tasks: reproducing an existing assessment, recovering parameters from synthetic observations, and fitting experimental evidence. A successful reproduction verifies implementation; a synthetic recovery tests inference under controlled conditions; neither establishes agreement with independent experiments. If an experimental fit inherits fixed terms or initial parameters from an assessment, disclose that dependence.

The specification must identify the evidence snapshot, objective, physical constraints, optimizer sequence, evaluation budget, stopping rules, validation observations, and acceptance criteria. Record the expected deliverables and the requirements that are unresolved. Do not substitute optimizer termination for scientific acceptance.

## 3. Inventory ORCHID evidence before searching elsewhere

Create an evidence ledger that reconciles the source records with the actual files and residuals supplied to the fitter. Inventory thermochemistry, activities, heat capacities, entropies, phase compositions, equilibrium assemblages, invariant reactions, congruent transformations, and polymorphic transitions. Explicitly inspect invariant and transition tables, including supplementary information; their absence from an exported dataset does not mean that ORCHID lacks them.

For every observation, retain its persistent identifier, source identifier and locator, evidence class, original notation, normalized quantities, uncertainty, and disposition. Record composition and energy bases, temperature units, pressure assumptions, phase identities, experimental method where available, and relationships to other observations. Evidence classes must distinguish direct measurements, quoted measurements, assessments, calculations from an existing model, atomistic predictions, and derived constraints. Apply this classification at the row level when a table mixes measured and calculated values. Separately classify equilibrium status as equilibrium, constrained metastable, or kinetically unresolved. Preserve reported equilibration conditions and source-supported suspended phases. Do not translate kinetically unresolved observations into equilibrium inequalities without justification.

Link repeated quotations and extractions of the same measurement so that they do not become independent likelihood terms. Retain conflicting independent measurements with their provenance and uncertainty rather than averaging them without justification. Points sampled from one assessed field share a source and are not independent experiments.

Use explicit dispositions such as `included`, `validation`, `duplicate`, `held`, `out_of_scope`, or `invalid_extraction`. An exclusion requires a reason and source pointer. Reconcile counts at the stages of acquisition, review, export, and objective construction. No record may disappear because a loader cannot represent it.

## 4. Close evidence gaps and contribute to ORCHID

When the inventory identifies missing or ambiguous information, search the project library and the cited literature, then acquire additional papers through authorized repositories or publisher access. Follow citation chains when phase identities, crystal structures, reactions, or measurement conditions are unclear. Use institutional retrieval infrastructure where required and preserve the DOI, article version, retrieval record, and file checksum. Keep credentials out of artifacts and retain restricted full texts in authorized private storage.

Extract new information using the current ORCHID schemas and review protocol. Preserve the original table row or figure location, numerical precision, uncertainties, and any interpretation needed to normalize the observation. A fitted model may expose an inconsistency, but its prediction is not evidence for relabeling the source.

Prepare additions and corrections for ORCHID as part of the campaign deliverables. Include proposed records, registry mappings, source provenance, duplicate checks, review status, and correction lineage. Preserve published identifiers and link corrected records to their predecessors according to ORCHID's versioning rules. Independent review must address the source evidence; agreement between agents alone does not certify an extraction.

Reviewed local additions may be used in a versioned fit before a database release, provided their status and hashes are recorded. Distinguish records that are prepared, reviewed, merged, and released. Do not claim that a contribution is available in ORCHID until its receipt or release has been verified. Follow established authorization for external writes and publication.

### Mandatory export of newly acquired and derived information

Any new information introduced during a fitting campaign must be accounted for in an ORCHID contribution package. This includes digitized plots, extracted table rows, phase-assemblage annotations, corrected field geometry or labels, additional sampled states, and new presence or absence constraints. Export structured records and their supporting artifact references; retaining the information only in fitting scripts, plots, or the HTML report does not satisfy this requirement. Preparation of the export is part of the campaign, not an optional task deferred until a successful fit.

Use the current ORCHID schemas, identifier generator, registries, and validation tools. Look up existing source, figure, table, phase, state, and observation records before assigning identifiers. Reuse the appropriate existing identity when the information is already represented; create new observation or derived-record identities when the schema requires them. Do not invent official-looking IDs or use local filenames as canonical identifiers. Preserve published identities and express corrections, supersession, and derivation through the supported versioning relationships. If a schema or identifier mechanism is unavailable, retain a clearly provisional local identifier and an unresolved export disposition until it can be reconciled; do not claim the record has been accepted into ORCHID.

For plot and table extractions, retain the publication and exact figure, panel, page, or row locator, axis calibration and units, extraction method, uncertainty, and source-artifact checksum. For phase-assemblage annotations, retain the original and normalized phase labels, registry mappings, coordinates or region geometry, topology checks, and review decisions. For additional constraints, retain the parent observation or annotated field, sampling or derivation rule, temperature/composition/pressure domain, present/absent/unknown phase status, and any stability margin. Record shared-source and derived-data relationships so that denser sampling does not become falsely independent evidence.

Classify generated plots and tables by origin. Source-derived evidence and its annotations belong in the appropriate evidence collections; model predictions, residual maps, parameter-space plots, and optimizer summaries belong in the corresponding computational or analysis collection, with model, run and objective-version identifiers. Register supporting artifacts or manifests where the schema supports them, rather than creating a scientific observation for every rendering. A diagnostic mismatch may trigger source review, but a prediction cannot become an experimental phase-assemblage constraint merely because it improves the fit. Restricted source images and publications remain in permitted storage, with authorized references and checksums in the contribution package.

Before using new evidence in a versioned objective, validate its schema and units, identifier uniqueness, referential integrity, phase mappings, duplicate status, and derivation lineage. Apply the required source and independent review checks. Retain the accepted local evidence snapshot and hash, and cross-reference the exact observation IDs in the fitter's input manifest and residual diagnostics. Evidence received during an active trajectory must not change that trajectory's objective silently.

Maintain an export ledger linking every addition or correction to its canonical or provisional ID, parent IDs, contribution-package path, validation outcome, review status, and actual submission or release status. Perform the authorized export/submission to the designated ORCHID intake and verify the receipt. An unmerged contribution may remain pending review; distinguish this from a prepared but undelivered package. The campaign handoff and HTML report must show outstanding exports explicitly. No campaign may be reported as fully handed off while newly used evidence or annotations remain unaccounted for in this ledger.

## 5. Reconcile phase identities and model coverage

Retain the phase name printed in the source alongside the registry identifier and the model phase name. Resolve aliases using composition, crystal structure, space group, prototype, ordering, and the source's temperature range. Greek labels and similar names are insufficient to establish identity. Treat conflicts between a database comment and the underlying publication as explicit provenance issues; a remaining candidate with unknown structure must not win a mapping by elimination.

Inventory observed phases that the model cannot represent. A missing model phase is a coverage gap, not evidence that the phase is absent. Do not force a mapping merely to make a dataset load. Record whether a model extension is required, and version any approved extension before comparing fits.

Verify normalization across all phases and evidence sources, particularly energies per mole of atoms versus per mole of formula units. Confirm that endmember references, site ratios, and atomistic energy conversions are consistent with the Gibbs-energy model.

### Missing crystal structures: required fallback sequence

When atomic coordinates or a reliable structural identity are unavailable, follow this sequence and retain a search record. First inspect ORCHID's phase registry, structure records, original assessments, cited crystallographic papers, and supplementary materials. Then consult relevant crystallographic databases and the wider literature through authorized access. Resolve alternative settings, chemical ordering, partial occupancies, and polymorph labels using the original source. Record unsuccessful searches as well as recovered information so subsequent agents do not repeat an undocumented search.

Reconstruct a structure only when the available lattice parameters, symmetry, occupied sites, coordinates, and composition supply enough information to define it. A chemical formula, space group, or prototype name alone may be insufficient. Preserve the published representation, the reconstruction script and assumptions, and the resulting structure hash. Check composition, multiplicities, site occupations, symmetry, and physically meaningful geometry. Relaxation convergence alone does not verify crystallographic identity.

If the information remains insufficient, mark the phase as structurally unresolved. Do not substitute another polymorph, silently assign a convenient prototype, or invent coordinates. Continue calculations for independently resolved phases and references, while retaining the unresolved phase in model-coverage and calculation-readiness records.

Two scientific paths remain distinct. In a fresh PhaseForge prediction, the unresolved phase's atomistic property calculation remains held until a justified structure is available. A documented prototype hypothesis or structure-search calculation may be investigated within the authorized scope, with its method, assumptions, search domain, and validation requirements recorded. Its output is a computational candidate, not a verified experimental structure; numerical relaxation or energetic preference alone does not establish that it represents the reported phase. It may nevertheless qualify for provisional energetic use under the proportionate acceptance criteria below.

When partial structural information is available, use it to condition generation or restrict a structure search rather than treating the task as unconstrained. A possible structure-discovery path is a constrained generative model. Use a documented implementation whose supported chemistry and conditioning mechanisms have been checked. Condition on the known composition and, when supported by evidence, symmetry, site multiplicities, occupancies, cell-size or density ranges, and other structural observations. If crystallographic information is absent, do not invent a space-group constraint: retain the distinction between evidence-based restrictions and exploratory priors. Record hard constraints separately from soft conditioning and verify the generated outputs actually satisfy them. The same evidence should constrain conventional structure-search methods where their implementation supports it. For example, known composition and space group may restrict candidate stoichiometries and symmetry while atomic coordinates, compatible Wyckoff-site assignments, or lattice parameters remain search variables. Preserve uncertainties and alternative reported settings; do not turn tentative source assignments into exact restrictions without documenting that choice.

Generate a diverse ensemble of candidates rather than treating one output as the structure. Preserve model and checkpoint identity, training-domain limitations and known overlap with the target system, conditioning inputs, random seeds, generation settings, and all filtering decisions. Check stoichiometry, periodic geometry, unphysical contacts, occupancy and symmetry constraints, and duplicate structures before assigning expensive calculations. Relax and assess surviving candidates with independently justified methods; a generator's own score or evaluation with a related potential is not independent validation. Where needed, corroborate rankings with first-principles calculations and available experimental structural information, and evaluate dynamical or finite-temperature stability appropriate to the phase's domain.

A generated low-energy candidate does not prove the identity of an experimentally reported phase, and a high-temperature phase need not be a stable zero-temperature minimum. Keep plausible alternatives and quantify or expose their effect on the inferred thermodynamics. Until validated, candidate-specific energies may support explicitly labeled exploratory models or sensitivity studies, but must not silently replace missing verified-phase inputs in the fresh PhaseForge baseline. Export the candidates, constraints, provenance, validation results, and unresolved identity to ORCHID as proposed computational structures, using supported identifiers and review states. If no suitable generative implementation or sufficient compute is available, retain the unresolved status and continue independent work; this option does not establish that such a method is already implemented in PhaseForge or SAGE.

In an experimental CALPHAD assessment, the phase may instead be represented by a justified phenomenological model and its parameters inferred from experimental evidence. Record the model's constitution, adjustable terms, reference convention, and identifiability limitations. Label the resulting parameters as experimentally inferred, not PhaseForge-predicted. This option does not permit copying an existing assessment's coefficients to conceal the missing calculation. It also does not establish a complete fresh atomistic prediction for the system: retain that limitation in the baseline specification, figures, comparisons, and HTML report. If this path changes the approved campaign scope or baseline model, record the decision before execution; otherwise proceed within the authorized experimental-refinement stage.

### Proportionate acceptance of proposed structures

Use an acceptance standard appropriate to the intended claim. Distinguish a structure confirmed to represent a reported experimental phase from a candidate sufficiently plausible to supply provisional modeling energetics. Experimental identity confirmation is not a prerequisite for all modeling use, and unresolved identity alone must not indefinitely block an explicitly candidate-assisted or analogue-assisted fit.

For provisional energetic use, require correct target composition or an explicit analogue composition mapping; physically sensible periodic geometry without unphysical contacts; consistency with reliable known structural constraints, or a recorded interpretation of any relaxation-induced change; a numerically converged calculation under declared constraints; and consistent energy normalization and reference states. Check for obvious calculation failures and retain the final structure, forces, stresses, and method limitations. Constrained calculations require appropriate convergence in the allowed degrees of freedom and disclosure of residual constrained forces. Do not demand agreement with an uncertain space-group assignment as if it were exact evidence.

When these basic checks pass, mark the result usable provisionally, retain its proposed-structure status, and allow it to supply an explicitly uncertain energetic estimate or initializer in the authorized modeling branch. Compare a modest ensemble of plausible candidates where available, record the selection rationale, and test whether alternative candidate energies materially change the fitted thermodynamics. Candidate spread can inform sensitivity analysis but does not by itself constitute calibrated statistical uncertainty. Do not automatically select a collapsed or transformed structure merely because it has the lowest energy.

Full experimental structure confirmation, exhaustive structure-space exploration, and full-Brillouin-zone phonon calculations are not mandatory gates for provisional energetic use. Request additional validation when a concrete issue, intended stability claim, or material sensitivity warrants it. A Gamma-point check may be useful corroboration but is neither universally required nor proof of full dynamical stability. Report exactly which checks were performed.

Represent at least three distinct dispositions in the ledger and monitor: confirmed/reconstructed source structure, usable provisional candidate or analogue, and unusable or unresolved calculation. Translate these descriptions into the current ORCHID schema rather than inventing canonical enum values. Only the affected property or claim should remain held. These proportionate structure checks do not relax the requirements for correct energy references, evidence accounting, or phase-diagram topology at final acceptance.

### TDB model and analogue-assisted energetic fallback

If a suitable crystal structure cannot be recovered and constrained generation or search is unavailable, unsuccessful, or insufficiently validated, an authorized fallback is to retain a suitable phase-model form from a TDB and approximate missing energetics from related structures. Record the failed or unresolved preceding avenues and the reason for selecting this fallback. Preserve phase constitution, sublattice definitions, site ratios, and reference conventions only where they are justified for the target; distinguish reuse of a model form from reuse of assessed energetic coefficients. In a fresh-prediction campaign, do not silently import fitted interaction or compound coefficients from the reference assessment.

Choose analogues using chemical and structural similarity, including bonding environments, ordering, coordination and relevant composition, rather than composition proximity alone. Record all selected analogues, their source structures, computed or experimental property provenance, temperature validity, and reasons for inclusion or rejection. In a campaign requiring fresh numerical calculations, compute the analogue properties afresh where numerical reuse is prohibited. Normalize energies and references consistently before interpolation, transfer, or another documented estimation rule. If no defensible analogue exists, retain the energetic gap explicitly instead of manufacturing an estimate.

Treat the resulting estimates as provisional initialization or uncertain priors, not direct measurements or verified PhaseForge properties of the unresolved phase. Identify which Gibbs-energy terms are estimated and which remain unconstrained; a static-energy analogue does not determine entropy, heat capacity, or finite-temperature stability. Specify the uncertainty model, shared-analogue correlations and model-discrepancy allowance where justified, and avoid counting both an analogue observation and its derived estimate as independent evidence. Do not use an arbitrary narrow uncertainty to force the fit toward the approximation.

Refine the resulting model against the accepted experimental and phase-assemblage evidence under a separately versioned specification. Test sensitivity to plausible alternative analogues, estimation rules, and prior strengths; distinguish initialization sensitivity from a prior that remains in the objective. Retain identifiability limitations when experiments cannot resolve the missing energetic information. A successful objective fit alone does not validate the structural analogy or remove the phase-state and topology acceptance requirements.

Label this branch as an analogue-assisted CALPHAD model. Keep the incomplete fresh PhaseForge prediction, any generated-structure candidates, and the analogue-assisted refinement separately identifiable, with no retrospective claim that estimated properties were directly calculated for a verified target structure. Export the model provenance and derived estimates to the appropriate ORCHID review intake with identifiers, parent records, uncertainty, and actual review status. Show the fallback phase, affected properties, supporting analogues and sensitivity results in the HTML monitor and final handoff.

Export recovered structures, reconstruction records, and computational candidates to the appropriate ORCHID intake with identifiers, source links, hashes, phase mappings, and their actual verification status, following Section 4. Clearly separate a source-verified structure, a reproducible source-based reconstruction, a proposed computational candidate, and an unresolved identity. If the canonical schema cannot represent a category, preserve a provisional review package and explicit schema hold rather than claiming native acceptance.

## 6. Validate diagram annotations and account for the entire grid

Treat a phase diagram as a graph of boundaries, vertices, invariant reactions, and adjacent fields. Validate phase-rule consistency, field connectivity, terminal behavior, invariant-line extents, boundary intersections, and the labels of single- and multiphase regions against an authoritative source or deterministic construction. A plausible drawing is insufficient. If exact topology cannot be established, mark the diagram as unsuitable for scientific acceptance and hold the affected claims.

Check annotation geometry as well as labels. Dashed boundaries, gaps in scanned lines, text glyphs, merged regions, narrow fields, and slivers can corrupt a dense grid even when a field-center label is correct. Inspect low-temperature fields explicitly. Retain composition sets when the same phase occurs at different compositions; reducing an assemblage to a set of phase names loses miscibility-gap information.

Account for every sampled point, including valid single-phase states. Maintain a separate inventory of all source fields, including fields with no sampled points. Represent line compounds and invariant features according to their dimensionality rather than demanding that a rectangular grid intersect them by chance. Densify observations where validated narrow fields, boundary neighborhoods, or unresolved topology require additional coverage.

After correcting geometry, preserve the old grid and observation lineage. First evaluate corrections at the original coordinates to isolate their effect; then regenerate or augment the grid under a documented sampling rule. Report changed labels separately from newly sampled observations. More points in one source field do not automatically justify more statistical weight.

## 7. Represent complete equilibrium-state evidence

An equilibrium observation must distinguish phases that are present, phases supported as absent, and phases whose status is unknown. An absence assertion needs a declared candidate set and a source basis, such as an assessed equilibrium field within a specified domain. Failure to mention a phase in a paper is not generally an absence observation. Calculation failure is never an absence observation.

Use ORCHID's current state and observation schemas. Store excluded-phase assertions as observation evidence rather than silently changing state identity. Preserve temperature, pressure, overall composition, phase configurations, composition sets, and available phase compositions. Single-phase states are valid evidence. Missing tie-line endpoints must remain unknown; do not fabricate them to satisfy an input format.

The residual adapter must specify how the supporting chemical potentials and unknown phase compositions are determined from the expected assemblage, enforcing mass balance, tangency where applicable, internal equilibrium, and declared phase-amount tolerances. A stoichiometric single phase does not uniquely determine the supporting chemical potentials. For nonunique planes, specify a reproducible constrained feasibility or optimization treatment and how its result enters the objective; do not select an arbitrary plane and interpret its penalty as unique evidence. Do not derive the plane solely from unrestricted equilibrium containing the unwanted phase being tested.

For a declared supporting chemical-potential vector, use a consistent residual convention. One useful convention, with energies normalized per mole of atoms, is

\[
\Delta G_p=\min_{\mathbf{x},\mathbf{y}\in\mathcal{D}_p}
\left[G_p(T,P,\mathbf{x},\mathbf{y})-\sum_i\mu_i x_i\right],
\]

where the minimization covers the permitted compositions and internal degrees of freedom of phase \(p\). Positive values place the phase above the supporting plane; negative values indicate that it can undercut that plane. For an absence margin \(\tau_{\mathrm{abs}}\geq0\), a one-sided hinge is

\[
r_{\mathrm{abs},p}=\max(0,\tau_{\mathrm{abs}}-\Delta G_p).
\]

Present phases must touch the supporting plane at the observed or fitted composition sets, within the declared tolerance, and satisfy mass balance and equilibrium conditions. A possible tolerance residual at a present composition is \(\max(0,|G_p-\boldsymbol\mu\cdot\mathbf{x}|-\tau_{\mathrm{present}})\); the implemented formulation must also check internal stability and prevent unobserved lower minima. A support plane constructed using only expected phases requires a subsequent search over all modeled candidates.

For a homogeneous single-phase observation, also test whether that phase can lower its energy by separating into composition sets. A phase-name match alone cannot detect this failure. Validate residual signs using deliberately stable and unstable examples, and document numerical minimization accuracy. If software uses the opposite driving-force sign, transform the inequality explicitly.

Keep four quantities distinct: physical stability margins, numerical tolerances, uncertainty or residual scales, and dataset weights. There is no universal 10 or 100 J/mol margin. Choose a defensible margin for the observations and model resolution, document sensitivity, and avoid demanding finite separation at an actual phase boundary where competing phases touch the same plane. Source dependence may motivate field-level weighting, but that policy must be explicit and fixed for a comparison.

## 8. Include invariant and transition evidence explicitly

Reconcile every acquired invariant or transition row with its fitting disposition. Preserve reaction type and direction, participating phases, temperature and uncertainty, compositions when known, and whether the row is experimental or calculated. Distinguish eutectic, peritectic, eutectoid, congruent, and polymorphic transformations; they impose different constraints.

Use a residual appropriate to the available observation. A temperature observation does not supply unreported phase compositions. Same-composition polymorphic transitions may require a specialized free-energy equality or transition-temperature residual if the standard ZPF interface cannot represent them. Unsupported observations must remain visible in the ledger with an implementation plan or explicit hold.

When constructing states above and below a reported reaction, retain their parent observation and explain the temperature offsets. These derived constraints do not constitute new independent measurements. Prevent double counting between direct reaction residuals, derived brackets, and diagram samples. Do not combine different reported temperatures into one invariant merely because the phase names agree.

## 9. Constrain physical behavior within a justified domain

Use thermochemical evidence and physical constraints to prevent implausible behavior that sparse phase observations cannot identify. For the liquid, assess entropy, enthalpy, heat capacity, and stability over the intended domain, with particular attention to extrapolation toward low temperature. Connect entropy and heat-capacity evidence to derivatives of the fitted Gibbs energy under consistent references: \(S=-(\partial G/\partial T)_{P,\mathbf{x}}\) and \(C_P=-T(\partial^2G/\partial T^2)_{P,\mathbf{x}}\), with internal degrees of freedom equilibrated under the declared constraints. Recording an entropy bound without connecting it to the model or objective is insufficient.

Where a homogeneous liquid is supported by evidence, test its stability against composition fluctuations and finite separation. Binary curvature and the Hessian projected onto the multicomponent composition simplex provide local tests; tangent-plane or convex-hull calculations test finite separation. Do not suppress a miscibility gap in a domain where it is physically supported. Record sampling resolution and numerical tolerances, and distinguish a sampled check from a mathematical certificate over a continuous domain.

Liquid phase separation is an explicit exception to a blanket convexity requirement. Before enabling a liquid-convexity constraint, consult ORCHID and the reviewed source diagrams for liquid–liquid coexistence. If the phase-diagram evidence supports liquid separation, disable the global convexity rule and fit the observed miscibility-gap boundaries, coexisting liquid compositions, critical behavior when reported, and associated invariant reactions. Preserve the two liquid composition sets even though they share a phase name. Any remaining convexity constraints must be restricted to separately justified homogeneous-liquid domains and must not eliminate the observed gap. Record the supporting observation IDs, domain, and decision in the objective specification and HTML monitor. Ambiguous evidence requires an explicit disposition or comparison of alternative models; absence of a reported gap alone is not proof of global convexity.

Derive temperature coverage from the actual functional form. An endpoint argument valid for an affine temperature dependence cannot automatically be reused for nonlinear expressions, including a Kaptay-type parameterization. A new liquid model requires renewed checks of derivatives, units, references, and stability over the declared domain.

When liquid entropy predictions are available through PhaseForge or another validated workflow, specify the implementation and reference treatment. Separate vibrational, configurational, and electronic contributions, and avoid adding ideal mixing twice or comparing absolute entropy with an excess quantity. Propagate uncertainty in reference subtraction. For each new chemical system, apply the approved finite-size procedure at one representative composition: compare 108 and 864 atoms at the same temperature with matched simulation and analysis settings, using 100 ps production by default. Accept the smaller cell for the broader campaign only if \(100|S_{108}-S_{864}|/|S_{864}|<5\%\). Record the composition and temperature selection rationale, settings, and both values. Investigate failure before adopting the smaller cell; do not automatically repeat the large-cell calculation at every composition. This criterion applies to vibrational entropy and does not validate other contributions. Do not apply a relative criterion to a near-zero excess quantity without an appropriate absolute tolerance.

For atomistic or MLIP evidence, retain structures, potential and software versions, relaxation and sampling settings, reference calculations, convergence checks, and uncertainties. Reuse compatible validated calculations and calculate only missing or incompatible properties. Computational predictions must remain identifiable as such. Bounds should reflect physical information and the intended domain, rather than being narrowed simply to make an optimizer terminate.

## 10. PhaseForge calculations and handoff to fitting

### Implementation and readiness

Use the ORCHID PhaseForge branch and its versioned liquid-entropy protocol when constructing or refining liquid models. Liquid entropy assessment is a required workflow stage. It may yield component diagnostics or a documented hold when total entropy is not fit-ready; an unresolved estimator must not supply numerical constraints merely to complete the stage. Preserve the user's prescribed order of computational initialization and experimental refinement.

The implementation inspected for this document is the Studio checkout `<home>/projects/phaseforge-orchid`, branch `orchid/liquid-entropy-protocol`, commit `77204fdc9017cca3caff5961aafce40cc80b571b`. Its authoritative workflow document is `docs/protocols/liquid-entropy.md`; its README and `bin/` scripts define available commands. This is a reproducibility anchor, not a requirement to use an obsolete revision: inspect the approved revision and record changes before a new campaign. The remote is `https://github.com/dogusariturk/PhaseForge.git`; do not assume the local branch or protocol commit has been published there.

At that revision, entropy analysis is not integrated into the PhaseForge command line, and configurational chemical-mixing calibration remains unresolved. An archived implementation is available on the Studio under `<home>/transfer/ORCHID_oneshot_results/vision_entropy_pilot_20261024/`, including `run_entropy_pilot.py` and `entropy_from_traj.py`. These are explicitly pilot scripts, not production-certified executables. Locate the latest reviewed campaign implementation through ORCHID before reuse, record its path and hash, and check its trajectory units, estimator conventions, and validation results. Do not silently substitute the archived pilot for a validated implementation.

### A. Inventory and plan the calculations

Build a calculation manifest connecting ORCHID phase identities to structures, solid-solution compositions, liquid states, and elemental references. Mark compatible existing calculations for reuse and list missing properties. Compatibility requires matching reference conventions, potential and checkpoint, structure identity, normalization, and sufficiently converged settings; a matching filename or chemical formula is insufficient.

Select an MLIP with verified support for the elements and relevant environments. Preserve model/checkpoint hashes and the PhaseForge, MaterialsFramework, atomistic engine, and analysis versions. A potential used successfully for another system is not automatically validated for the new liquid or metastable structures. Define temperature/composition coverage, reference states, uncertainty checks, and acceptance criteria before launching. Use the authorized compute host and scheduler with durable execution; do not launch production work merely to document this protocol.

### B. Compounds and solid solutions

Obtain crystal structures through ORCHID and its source references, extending the search to authorized structure databases and papers where necessary. Map ordering, polymorphs, occupancies, and sublattices to the intended CALPHAD model. Preserve source structures and identifiers. Apply the missing-structure fallback in Section 5 when coordinates or phase identity cannot be established; never fill this gap silently with another polymorph or assessed coefficients. For disordered solutions, use SQS or the approved configuration-sampling method at compositions sufficient to constrain the selected interaction terms. Record supercell size, correlation targets and errors, configuration seeds, and any treatment of short-range order.

Use the verified PhaseForge entry points appropriate to the task: `sqscal` for its supported SQS-to-TDB workflow, `MLIPrelax` or `runstruct_MLIP` for relaxation, and `MLIPcalc` for static energies. Inspect the selected revision's help and generated inputs rather than copying a system-specific command. Run in isolated calculation directories because wrappers write conventional filenames.

Check forces, stresses, volume, and structural identity after relaxation. A structure that transforms into another phase must not retain the intended phase's energy label. If a constrained metastable calculation is required, declare and preserve its constraints. Compute compatible elemental references, convert energy differences to a common molar-atom basis, and record configuration and model uncertainty. Include phonon or other finite-temperature terms only through an explicitly validated method; zero-temperature formation energies alone do not establish a finite-temperature Gibbs energy.

### C. Liquid MD preparation and production

Choose a composition-temperature matrix that includes pure-liquid references at the same temperatures and pressure as the alloys. Include off-equiatomic compositions and multiple temperatures when the intended liquid parameterization requires them. State how the domain relates to observed liquid fields and any intentionally metastable extension. Do not interpret composition-dependent simulation temperatures as measurements of mixing properties at one common temperature.

Prepare well-defined cells and velocity seeds, melt the starting structures, equilibrate density at the target pressure, and equilibrate at the target temperature before production. NPT density equilibration followed by fixed-volume NVT sampling is an available pattern; record the chosen ensemble, pressure units, timestep, thermostat/barostat parameters, cell treatment, equilibration discard, and production duration. Temperatures and durations from an earlier chemical system are examples, not universal acceptance settings. Establish liquid behavior through species-resolved diffusion over time and structural diagnostics, alongside stationary energy, temperature, and density. Retain crystallized, phase-separated, drifting, or incomplete runs with explicit dispositions.

At the inspected revision, `MLIPmd` generates a 2,000-step NVT run with a nominal 1 fs timestep and averages its recorded total energies. `MLIPliquid` chooses a temperature from the elemental melting-point average plus an offset. Neither behavior establishes production convergence or a common-temperature reference convention. Use generated-input mode (`-nr`) where supported to inspect and adapt inputs under the approved workflow. Smoke tests verify execution only and must not become fitting evidence.

For entropy production, apply the 108/864-atom acceptance rule in Section 9 and the default 100 ps production baseline, then assess trajectory-length convergence. Preserve positions, velocities, species, masses, cell information, energies, and timestamps at explicitly recorded sampling intervals. Velocity and position intervals may differ; neither should be confused with the integration timestep. Verify velocity-unit conversions and sufficient temporal resolution for the analyzed spectrum. Preserve full restart metadata, and disclose when an interrupted stage is replayed instead of exactly resumed.

Estimate sampling uncertainty with correlated-trajectory-aware blocks and, where required by the run specification, independent seeds. Check sensitivity to equilibration discard, production duration, timestep, and density treatment. Compute enthalpy with the appropriate kinetic and pressure-volume terms or document why they cancel in the chosen difference; do not relabel an arbitrary average potential energy as enthalpy. Keep sampling error separate from potential and methodological error.

### D. Component-resolved liquid entropy

The ORCHID branch specifies the Hong–Liu approach, *Physical Review Research* **7**, L012030 (2025), DOI `10.1103/PhysRevResearch.7.L012030`. Before adopting an implementation, consult the source and supplementary definitions through ORCHID and verify that the code implements the intended convention. The inspected pilot obtains a vibrational estimate from a mass-weighted velocity autocorrelation spectrum with oscillator entropy weighting, and configurational diagnostics from neighbor-count distributions. It reports alternative binary conventions and omits electronic entropy. These limitations must remain visible in the handoff.

For the vibrational analysis, retain autocorrelation and spectral-window choices, frequency units, mode normalization, temperature consistency, and the treatment of low-frequency and negative spectral weight. Check sensitivity to trajectory blocks, window length, sampling interval, and normalization. Do not silently clip or rescale a defective spectrum and report the result as validated. Separate classical and quantum-weighted estimates and identify which enters the model.

For configurational entropy, retain neighbor definitions, RDF cutoffs, species/pair selections, and the chemical-mixing convention. Validate a controlled ideal-mixing limit before exporting total excess entropy. Alternative pair selections remain separate sensitivity cases unless a calibrated uncertainty model supports combining them. Their spread is not automatically a statistical uncertainty or a parameter bound.

If electronic entropy is required, use a separately documented electronic-structure calculation with representative liquid snapshots, consistent composition and references, converged numerical settings, and declared electronic temperature and occupation treatment. Assess snapshot variability and convergence separately. Missing electronic or configurational contributions remain unknown rather than zero. A validated vibrational result can be retained as a component diagnostic while total entropy remains held.

### E. Convert predictions into CALPHAD evidence

For a binary liquid with \(x=x_B\), matching pure-liquid references, and a total entropy convention that includes chemical mixing exactly once, use

\[
S_{\mathrm{ideal}}=-R[(1-x)\ln(1-x)+x\ln x],\qquad
S_{\mathrm{ex}}=S_{\mathrm{liquid}}-(1-x)S_{A,\mathrm{liquid}}-xS_{B,\mathrm{liquid}}-S_{\mathrm{ideal}}.
\]

Use the continuous endpoint limit for \(x\ln x\). Preserve covariance introduced by shared pure-liquid references and reuse of the same trajectories. Do not subtract ideal mixing until the estimator's chemical-mixing convention is established.

For the specific Redlich–Kister convention \(G_{\mathrm{ex}}=x(1-x)\sum_k(a_k+b_kT)(1-2x)^k\),

\[
S_{\mathrm{ex,model}}=-x(1-x)\sum_k b_k(1-2x)^k.
\]

The equiatomic entropy constrains only \(b_0\) within this parameterization; off-equiatomic observations constrain additional combinations. For other temperature dependences, including Kaptay-type expressions, differentiate the actual model instead of reusing this linear formula. Compare several temperatures to test the chosen functional form.

Export accepted predictions as explicitly computational evidence with units, uncertainty assumptions, covariance groups, provenance, and a fit-readiness decision. Use supported ESPEI observations where representable and a versioned custom residual adapter otherwise. Retain a held record when the interface or estimator is unsupported. Do not count total entropy, its components, and derived combinations as independent observations of the same trajectories.

Use validated entropy estimates as soft constraints with defensible uncertainties. Hard parameter bounds require an additional physical justification; neither sampling errors alone nor disagreement among unvalidated estimators supplies it. Report the entropy contribution to the objective separately and compare it for the reference assessment and candidate models. Preserve the baseline fit and perform an explicitly versioned entropy-constrained refinement under the authorized sequence. Phase assemblages, non-observations, invariants, and the other experimental evidence remain part of that refinement.

Archive the calculation manifest, input and trajectory hashes, component outputs, reference subtractions, convergence diagnostics, covariance treatment, and acceptance or hold decisions. Link these artifacts to proposed ORCHID computational records. This workflow defines required evidence and handoffs; it does not imply that the current PhaseForge CLI or SAGE automatically executes all stages.

## 11. Specify and verify the complete objective

Write down all objective components, their mathematical definitions, units, uncertainty assumptions, weights, and treatment of correlated observations. Separate likelihood terms from priors and physical penalties. Call a quantity a likelihood only when its probabilistic model is specified. Log component scores and the largest observation-level residuals in addition to the total.

Pin software versions and commits, including any ESPEI pull request that supplies accelerated gradients, the thermodynamic engine, and local adapters. Verify that the intended gradient implementation is actually called. Compare gradients with numerical checks at representative perturbed parameters away from phase switches; record nonsmooth regions where an ordinary derivative comparison is not meaningful.

When a suitable reference assessment is available, reproduce it using its supplied functions and database before a large search. Document discrepancies between the paper and distributed database. Score that reference under exactly the same evidence and objective as candidate models, and inspect its offending states. An unexpectedly large penalty is a reason to audit labels, mappings, units, residual signs, and reference implementation before increasing optimization effort. If no suitable assessment is available after consulting ORCHID and the literature, document that finding and use analytic identities, synthetic cases, endmember and reference consistency, residual sign tests, and equilibrium-solver checks as applicable. The absence of a prior assessment does not by itself block a new-system fit.

Reject invalid parameter trials through a controlled, optimizer-compatible failure policy. Log the cause and retain the last feasible checkpoint. Do not silently remove failing observations or change the number of residuals during a search. Separate infeasible parameter trials from software defects that require investigation.

## 12. Search reproducibly and measure cost

Complete the prescribed baseline protocol before introducing an authorized alternative. Methods such as basin hopping, dual annealing, CMA-ES, differential evolution, or Bayesian optimization are choices to be justified by the problem and available budget, not mandatory steps in every fit. Gradient-assisted methods require verified gradients and a clear treatment of phase-switch nonsmoothness.

### A. Prepare parameters and establish the baseline

Optimize in documented scaled coordinates so that energy coefficients, temperature coefficients, and higher-order terms have appropriate step sizes. Preserve a reversible mapping to physical parameters and transform gradients consistently. Freeze parameters that are outside the agreed scope. Enforce exact model relations through a valid parameterization or explicit constraints, and distinguish hard feasibility restrictions from soft physical penalties. Scaling coordinates must not change the scientific objective or its relative evidence weights.

Evaluate the initializer before optimization, including objective components and phase-state errors. Reevaluate selected vectors to determine whether solver settings, caching, or stochastic calculations introduce variability. Use the prescribed initialization and baseline method; when the sequence includes a PhaseForge initialization followed by experimental refinement, retain both models and their input manifests. A diagnostic evaluation of a known assessment does not authorize replacing the initialization with its parameters.

Where a smooth local region and validated derivatives are available, use the approved local solver with the accelerated ESPEI gradient implementation. Bounded quasi-Newton or trust-region methods are options for scalar objectives; nonlinear least squares is appropriate only when the objective genuinely has the required residual structure. Confirm that gradients cover all fitted contributions, including custom hinge, entropy, and stability terms, or document a tested hybrid derivative strategy. A gradient for only part of the objective is not the full objective gradient.

### B. Select exploration methods by the observed difficulty

The following choices are campaign-design guidance, not a universal ranking or a required sequence. Select methods under the existing authorization and record why they address the observed difficulty.

| Approach | When to consider it | Settings and limitations to record |
| --- | --- | --- |
| Local gradient refinement | A feasible start has a locally smooth objective and verified gradients | Scaling, bounds, solver tolerances, projected optimality where applicable, and phase-switch failures |
| Multistart local refinement | Initial-condition sensitivity is uncertain or several basins are suspected | Start-generation distribution, perturbation scales, seed pairs, local budget and distinct basins recovered |
| Basin hopping | Useful local minimization is available but local minima prevent progress | Proposal scales, acceptance temperature in objective units, feasibility checks and local-solver cost; it combines perturbations with local minimization ([SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.basinhopping.html)) |
| Dual annealing | Broader bounded exploration is warranted | Visiting/acceptance settings, restarts and local search; explicitly pass bounds to a custom local minimizer where required ([SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.dual_annealing.html)) |
| CMA-ES | Correlated continuous parameters and unreliable derivatives motivate adaptive population search | Initial covariance and step size, bounds handling, population size and restart policy; derivative-free does not mean immune to invalid evaluations ([CMA-ES authors' documentation](https://cma-es.github.io/)) |
| Differential evolution | Population-based exploration of finite parameter bounds is affordable | Population initialization, mutation/recombination, update policy, constraints and polishing cost; budget for its potentially high evaluation count ([SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.differential_evolution.html)) |
| Bayesian optimization / TuRBO | Thermodynamic evaluations are expensive enough to justify surrogate overhead | Initial design, surrogate, acquisition rule, batch size, trust-region adaptation and restart policy; local surrogate models are central to TuRBO ([original paper](https://arxiv.org/abs/1910.01739)) |

Ordinary simulated annealing and dual annealing are distinct implementations; record the actual transition rule, schedule, and local search rather than using their names interchangeably. Likewise, basin hopping must not be labeled minima hopping without implementing and documenting the latter's distinct escape procedure. An atomistic-inspired optimizer is an optional research extension, not a substitute for the approved baseline.

For gradient-aware Bayesian optimization, distinguish gradients used to optimize the acquisition function from thermodynamic objective derivatives supplied as surrogate training observations. Only the latter constitutes derivative-informed modeling of the objective. Identify a verified implementation supporting the required derivative observations, transformations, and uncertainty treatment before claiming this capability. Standard use of TuRBO does not establish gradient-aware objective modeling. Keep derivatives at unresolved phase switches out of a smooth derivative-observation model unless their treatment is justified. Confirm promising surrogate proposals with the full thermodynamic objective before ranking or archiving them as evaluated models.

### C. Combine methods without changing the scientific comparison

A possible authorized hybrid sequence is global or population exploration, local refinement of several distinct feasible candidates, and independent validation of the retained models. Preserve the global candidate if local refinement fails or worsens its score. Use the same objective and hard constraints in both stages, and charge refinement to the combined method's cost. Distinguish the raw exploration result from the polished result.

Multistart and perturbed-best experiments answer different questions. Distributed starts probe the specified search domain; perturbations around the current best probe local robustness. Record the perturbation distribution and its magnitude in scaled and physical units. Use both small and larger feasible perturbations when authorized to test whether apparent stability persists beyond one neighborhood. A prescribed repeated comparison, including its requested repetition count, must be completed or reported as incomplete. No fixed number of repetitions guarantees global convergence.

For fair head-to-head experiments, pair the starting seed conditions across methods and define how a population or BO initial design incorporates the common starting vector. Count initialization evaluations. A warm start from previous trajectories is allowed only if disclosed and matched or separately reported. Predeclare the primary budget and performance target, then compare success frequency, best feasible and accepted score distributions, and cost to the target. Report failed runs and budget-limited runs; do not calculate performance statistics from successful runs alone. Changing weights, bounds, model terms, or training observations creates a separate scientific comparison.

### D. Diagnose stagnation before extending the search

| Observation | Required diagnostic | Possible next step within authorized scope |
| --- | --- | --- |
| No improvement and a substantial trustworthy gradient | Check parameter scaling, gradient signs, line-search failures, active bounds and missing derivative terms | Repair numerical issues, then repeat the affected baseline checks |
| Small local gradient but different restarts find better candidates | Check whether stationarity holds only within the current basin | Broaden restart perturbations or use the selected global method |
| Population or trust region collapses | Inspect diversity, candidate duplicates, bound handling, step sizes and restart triggers | Apply the documented restart policy; retain the best feasible model |
| Most proposals fail | Separate physical infeasibility from solver crashes, nonfinite evaluations and adapter defects | Fix the identified cause; do not hide failures by dropping observations |
| Objective improves while assemblages remain wrong | Inspect component weights, absence constraints, support planes, labels and unrestricted equilibria | Audit evidence and residuals before proposing a versioned objective change |
| Different methods encounter the same unresolved mismatch | Check inconsistent evidence, phase coverage, parameter identifiability and model flexibility | Report the limitation; propose a scoped evidence or model revision rather than claiming optimizer convergence |

Define stagnation through a recorded improvement tolerance and evaluation window relative to the observed numerical resolution. Define local stationarity using an appropriate constrained optimality measure where derivatives apply. Record budget exhaustion separately. Extend a budget only under authorization and preserve the earlier stopping record. Do not claim that more iterations can resolve a contradictory dataset or a missing phase model.

### E. Preserve trajectories, compare cost, and report termination

Freeze the evidence, parameterization, bounds, and objective for comparisons. Use matched starting perturbations and independent seeds when comparing methods across repeated trials. Count actual thermodynamic evaluations, gradient work, invalid trials, cache use, surrogate overhead, and wall and processor time. Optimizer iterations alone are not a comparable cost measure.

Preserve parameter vectors, component scores, state mismatches, physical checks, and timestamps along the trajectories. Archive approximately the top ten distinct candidates per trajectory, with the count configurable in the run specification. Keep objective-ranked candidates and scientifically accepted candidates distinguishable; do not discard an informative failure merely because it is not publishable. Use scaled parameter distances and predicted observables to assess whether candidate models are meaningfully different.

For long jobs, verify inputs and environments on the authorized compute host and use detached execution, durable logs, checkpoints, and recorded process identifiers. Inspect existing jobs before submitting replacements.

Report termination precisely: budget exhausted, objective stagnation, local stationarity, or robustness to the declared restart tests. In a rugged landscape, agreement across searches and perturbed restarts provides evidence of robustness, not a proof of a global optimum. A stalled search may reflect poor scaling, incorrect gradients, conflicting evidence, or insufficient model flexibility as well as a local minimum.

## 13. Validate candidates before propagating uncertainty

For equilibrium observations, evaluate candidate models with unrestricted equilibrium calculations over the declared modeled phase set, along with the observation residuals. Evaluate intentionally metastable observations under their source-supported constraints, record suspended phases, and report this validation separately from unrestricted equilibrium agreement. Kinetically unresolved observations remain held for equilibrium interpretation unless further evidence resolves their status. Report missing and spurious phases, incorrect composition sets, reaction-temperature errors, thermochemical errors, low-temperature behavior, and liquid stability. Small driving-force penalties can coexist with incorrect assemblages, so report both energetic and categorical agreement.

Validate every displayed phase diagram topologically. Check invariant connectivity and line extents, terminal fields, narrow fields, and single-phase regions against authoritative evidence. Identify genuine conflicts between sources rather than drawing a compromise topology. A diagram with unresolved topology must not be presented as a scientifically accepted result.

For campaigns invoking SAGE steering, apply the relevant requirements of the validation program: require data-only misfit by evidence class to be no worse than an unsteered control within predeclared tolerances, separately report steering penalties, and rank accepted candidates on held-out regions when available. Do not silently add a control campaign or change the prescribed optimizer sequence. If the required control or validation evidence is unavailable, report steering validation as pending, or not applicable with justification.

Keep validation observations separate where independent evidence exists. Additional points from the same source diagram test coverage and implementation, but do not establish independent experimental validation. If validation observations are subsequently used for fitting, version the split and the resulting claims.

Only proceed to uncertainty propagation after the model passes the declared physical and evidence checks. Examine identifiable parameter combinations and distinct acceptable basins. Local perturbation or sampling near a minimum characterizes a conditional neighborhood unless broader coverage is demonstrated. For MCMC or NUTS, retain chain diagnostics and do not interpret nonconverged chains as a validated posterior. When applying an established propagation method, identify its publication, code version, assumptions, and required inputs rather than inferring the method from an author's name.

## 14. Deliverables and proposed SAGE checks

The following names are an illustrative integration contract, not an assertion that these files are currently generated or parsed by SAGE. Existing ORCHID schemas and persistent identifiers take precedence over new local conventions.

| Artifact | Required contents |
| --- | --- |
| `fit_spec.yaml` | Scope, model, parameterization, prescribed sequence, budgets, stopping and acceptance criteria |
| `evidence_ledger.jsonl` | Source and record identifiers, evidence classes, units, uncertainty, dependencies, dispositions and source locators |
| `phase_mapping.json` | Printed names, registry and model identities, structural justification and unresolved coverage |
| `coverage.json` | Source-field inventory, accounting for all grid points and table rows, corrections and exclusions |
| `objective_spec.json` | Residual formulas, scales, weights, priors, constraints, implementation versions and checks |
| `reference_check.json` | Reference reproduction, common-objective scores and diagnostics; or documented absence and alternative checks |
| `runs/` | Immutable input manifests, environment records, seeds, trajectories, costs, checkpoints and archived candidates |
| `status.html` and report status record | Readable campaign dashboard, data freshness, scientific gates, update mechanism and verified delivery status |
| `optimizer_plan.json` | Approved baseline and alternatives, parameter scaling, method settings, paired comparison design, budgets and escalation rules |
| `validation.json` | State agreement, thermochemistry, topology, physical stability, uncertainty readiness and acceptance decision |
| `contribution_manifest.json` and export ledger | All new plots, tables, annotations, states and constraints; canonical/provisional IDs, parent links, schema checks, review and verified delivery status |

Record a status of `PASS`, `FAIL`, `HELD`, or `NOT_APPLICABLE` for each applicable requirement, together with the reason, evidence pointer or hash, and responsible reviewer or automated check. Metadata completeness is not scientific certification.

| Decision point | Required evidence to proceed |
| --- | --- |
| Evidence reconciled | ORCHID inventory, source and registry checks, table and grid accounting, unresolved items explicitly scoped |
| Search ready | Frozen objective, working residuals and gradients where used, reference diagnostics or documented alternative checks, feasible initialization and durable execution plan |
| Candidate accepted | Declared thermochemical, assemblage, topology and physical checks satisfied within stated tolerances |
| Uncertainty ready | Accepted model, documented sampling domain and appropriate diagnostics or propagation assumptions |
| Contribution delivered | Every addition or correction accounted for by ID and lineage; schema and reference checks passed; intake receipt or release verified, with pending review distinguished from non-delivery |

An unresolved issue should hold the affected evidence, calculation, or claim. Continue independent work where its interpretation remains valid, and do not describe a partially validated model as accepted over the full domain.

### Required HTML campaign report

Generate a self-contained `status.html` at campaign initialization and keep it current throughout execution. The report is a required scientific deliverable, not an optional console-log replacement. Present an informative, complete, visually coherent overview with readable typography, accessible contrast, responsive layouts, clearly labeled plots and units, and concise explanations of what the results mean. Use text as well as color to communicate status. Keep detailed provenance, residual tables, and parameter records available in expandable sections so the overview remains readable. Verify the rendered report at desktop and narrow-screen widths; check labels, links, plots, and missing-data states.

Begin the HTML report with a schematic of the entire protocol: scope, ORCHID evidence and literature acquisition, structure and annotation checks, fresh PhaseForge calculations, objective verification, initialization and fitting, scientific validation, and uncertainty. Show missing-structure recovery and analogue-assisted alternatives, the liquid finite-size/entropy decision, and the return path after failed checks. Identify the current stage and completed, active, held, and waiting stages using recorded checkpoints and acceptance gates. Display ORCHID contribution export and reporting as continuing activities. Numerical completion must not be drawn as scientific acceptance. Keep the schematic self-contained and readable on narrow screens.

The overview must show the campaign purpose, current stage, protocol version, scientific acceptance status, outstanding issues, and next actions. Display generation time, underlying-data timestamps, last successful process check, update cadence, and a visible stale-data or publisher-failure indication. Distinguish a static review snapshot from an actively maintained report; browser auto-refresh alone is not a data-update mechanism. Never show an unchecked process as currently running.

Include evidence and phase coverage; invariant and transition dispositions; computational-property and entropy readiness; optimizer settings and cost; best-so-far trajectories; objective components; common-objective reference comparisons; candidate diversity when available; and the independent validation gates. Keep different objective versions and their reference scores separate. Identify uncertainty, held observations, and unavailable results explicitly rather than fabricating plots or using zeros for missing values. A lower fitting objective must not be labeled scientific acceptance. Display the exact domain of a physical check, including any liquid-convexity temperature interval. Any phase diagram remains subject to the topology rules in this protocol; show its pending status if no acceptable diagram exists.

Generate the HTML from versioned machine-readable status records and checkpoints. Publish by atomic replacement after validation, retain the last good report on failure, and log publisher errors separately from scientific-job errors. Use a documented event hook or durable observational publisher with an explicit cadence, heartbeat, process identifier and stop procedure. Record when job monitoring ends. The report generator must not restart fits, modify scientific inputs, or turn missing data into success. Embed assets needed for offline viewing; escape inserted text and avoid exposing credentials or restricted source documents through public links.

Provide an HTML prototype for user review before treating its layout as the reporting standard. When requested, place it in the user's designated shared location, including Dropbox, and verify delivery. Record whether that copy is a timestamped snapshot or an updating mirror, with its own synchronization status. Do not claim live Dropbox updates solely because a live report exists on a compute host. Preserve review snapshots and document subsequent changes to the template.

## 15. Instruction to a fitting agent

Consult ORCHID first and reconcile what it contains with what the fitter actually uses. Acquire and extract additional literature when the evidence requires it, and export newly acquired or derived plots, tables, annotations, states and constraints to ORCHID with proper identifiers, provenance and review status. Preserve the prescribed protocol and version any authorized change. Account for every observation, including single-phase states, supported absences, and invariant or transition rows. Verify phase identities and annotation topology before densifying the grid. Test the objective against known references, constrain physical behavior in a justified domain, and preserve candidate trajectories and computational costs. Accept a model through explicit scientific checks, then characterize uncertainty within the domain that the evidence and sampling support.

Related SAGE documents: [phase-equilibrium evidence design](PHASE_EQUILIBRIUM_EVIDENCE.md), [validation program](VALIDATION_PROGRAM.md), and [project scope](../README.md). Numerical settings in earlier examples are case-specific; they do not establish universal stability margins, weights, or sampling rules for this protocol.
