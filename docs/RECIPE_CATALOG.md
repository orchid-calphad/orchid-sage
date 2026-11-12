# CALPHAD modeling recipe catalog

36 candidate recipes (34 source-backed; 2 project rules from the PI awaiting literature support); 43 source records including inherited leads. All entries require domain review and numerical reproduction before scientific execution.

Recipes are concise implementation proposals informed by the listed sources. Applicability, caveats and test design include engineering synthesis; they are not quotations or claims that the source authors implemented this tool.

## cef-baseline — Crystallography-informed CEF baseline

Topic: foundations. Priority: P0. Method type: model_family.

Use an explicit site and constituent specification as a candidate CEF representation.

**Applies when:** See trigger and required evidence; domain review required.

**Limits:** Crystal structure alone does not fix thermodynamic parameterization.

**Validation:** Site ratios and atomic composition agree. Reference states and pure limits are consistent.

**Sources:**
- [Implementation of an Effective Bond Energy Formalism in the Multicomponent Calphad Approach](https://doi.org/10.6028/jres.123.020) — open full text; selected passages inspected; locator: Section 2, equations 1–3; Section 2.2, Table 1; Abstract.

## ebef-multisite — Effective Bond Energy Formalism

Topic: foundations. Priority: P0. Method type: constrained_parameterization.

Consider effective-bond parameterization for complex multisublattice phases.

**Applies when:** See trigger and required evidence; domain review required.

**Limits:** Not an exact reconstruction of arbitrary independently specified endmember energies. Matrix construction, rank tests and published numerical reproduction are not implemented.

**Validation:** Reproduce published parameter mapping. Test independent higher-order endmember energies and ternary equilibria.

**Sources:**
- [Implementation of an Effective Bond Energy Formalism in the Multicomponent Calphad Approach](https://doi.org/10.6028/jres.123.020) — open full text; selected passages inspected; locator: Section 2, equations 1–3; Section 2.2, Table 1; Abstract.
- [Applying the Effective Bond Energy Formalism (EBEF) to Describe the Sigma (σ) Phase in the Co-Cr-Ni-Re System](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=956715) — open author manuscript; introduction inspected; locator: Introduction, PDF pages 2–4; Abstract: matrix inversion method.

## site-merging — Evidence-supported sublattice reduction

Topic: foundations. Priority: P0. Method type: approximation.

Consider combining sites only when occupancy evidence supports the reduction over the intended domain.

**Applies when:** See trigger and required evidence; domain review required.

**Limits:** Successful binary fitting does not establish multicomponent transferability.

**Validation:** Compare occupancy and equilibrium predictions before and after reduction.

**Sources:**
- [Applying the Effective Bond Energy Formalism (EBEF) to Describe the Sigma (σ) Phase in the Co-Cr-Ni-Re System](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=956715) — open author manuscript; introduction inspected; locator: Introduction, PDF pages 2–4; Abstract: matrix inversion method.

## vacancy-treatment — Vacancy interpretation and normalization

Topic: foundations. Priority: P0. Method type: modeling_convention.

Establish vacancy role and the physical interpretation of limiting configurations.

**Applies when:** See trigger and required evidence; domain review required.

**Limits:** Abstract-level source supports screening only; no numerical vacancy-energy prescription is supplied.

**Validation:** Check empty-corner limits and equilibrium stability. Check atomic versus formula normalization and observed defects.

**Sources:**
- [Thermodynamic modelling of vacancies as a constituent](https://doi.org/10.1016/j.calphad.2019.101666) — publisher abstract inspected; equations not verified; locator: Abstract.

## ordering-coupling — Ordered and disordered phase coupling

Topic: foundations. Priority: P0. Method type: constraint_family.

Require explicit ordered/disordered relationships before parameter fitting.

**Applies when:** See trigger and required evidence; domain review required.

**Limits:** No automatic ordering transformation or correction subtraction is implemented.

**Validation:** Test disordered limit and avoid double counting contributions.

**Sources:**
- [Implementation of an Effective Bond Energy Formalism in the Multicomponent Calphad Approach](https://doi.org/10.6028/jres.123.020) — open full text; selected passages inspected; locator: Section 2, equations 1–3; Section 2.2, Table 1; Abstract.

## database-compatibility — Subsystem compatibility review

Topic: foundations. Priority: P0. Method type: assessment_practice.

Review subsystem descriptions together before combining them.

**Applies when:** See trigger and required evidence; domain review required.

**Limits:** Guidance source remains a bibliographic lead in this release. Structural preflight cannot certify Gibbs-energy equivalence.

**Validation:** Compare shared references and phase identities. Test binary limits and multicomponent extrapolation.

**Sources:**
- [Assessment techniques, database design and software facilities for thermodynamics and diffusion](https://www.sciencedirect.com/science/article/pii/S0364591606000150) — primary-source abstract/search passages inspected; locator: Abstract: quality assurance and combining assessments.

## reciprocal-zero — Zero-reciprocal-energy endmember estimate

Topic: endmembers. Priority: P0. Method type: assumption.

Close a reciprocal square by explicitly assuming its reciprocal energy is zero.

**Applies when:** A missing hypothetical endmember and three compatible reference energies.

**Limits:** Zero reciprocal energy is an assumption, not symmetry or a general identity; original cited method still needs tracing.

**Validation:** With consistent labels check G(A:C)+G(B:D)-G(A:D)-G(B:C)=0 and validate withheld energies.

**Sources:**
- [Calphad Modeling of LRO and SRO Using ab initio Data](https://www.mdpi.com/2075-4701/10/8/998) — primary article indexed passages inspected; direct full-text request rate-limited; locator: Sections 2.3, 4.2, 5.2.1, 5.2.2; indexed passages.

## independent-basis — Independent endmember and reaction bases

Topic: model_geometry. Priority: P0. Method type: exact_transformation_with_conditions.

Construct independent composition/site-occupancy bases and retain reaction coordinates.

**Applies when:** Fixed-site solution models with explicit stoichiometry and constraints.

**Limits:** Linear dependence of compositions does not imply linear dependence of endmember energies.

**Validation:** Verify rank, nullspace, reconstruction and unchanged admissible composition domain.

**Sources:**
- [Notes on the creation and manipulation of solid solution models](https://link.springer.com/article/10.1007/s00410-021-01825-1) — primary abstract and methods/Appendix A passages inspected; locator: Model geometry; independent endmember bases; Appendix A code.

## basis-change — Change model basis without losing energetic terms

Topic: model_geometry. Priority: P1. Method type: exact_transformation_with_conditions.

Transform reference and interaction terms together when changing an endmember basis.

**Applies when:** An explicitly defined invertible transformation on the represented model space.

**Limits:** Dropping interaction terms turns a transformation into an approximation.

**Validation:** Compare G and derivatives throughout the mapped domain.

**Sources:**
- [Notes on the creation and manipulation of solid solution models](https://link.springer.com/article/10.1007/s00410-021-01825-1) — primary abstract and methods/Appendix A passages inspected; locator: Model geometry; independent endmember bases; Appendix A code.

## ordering-symmetry — Symmetry-related ordered endmembers

Topic: ordering. Priority: P0. Method type: symmetry_constraint.

Tie endmember and interaction parameters only under validated site permutations.

**Applies when:** Equivalent sites in a specified parent lattice.

**Limits:** Equal site multiplicities alone do not prove crystallographic equivalence.

**Validation:** Verify allowed permutations and equal energies for symmetry-related configurations.

**Sources:**
- [Calphad Modeling of LRO and SRO Using ab initio Data](https://www.mdpi.com/2075-4701/10/8/998) — primary article indexed passages inspected; direct full-text request rate-limited; locator: Sections 2.3, 4.2, 5.2.1, 5.2.2; indexed passages.

## fcc-four-site — Four-sublattice FCC ordering candidate

Topic: ordering. Priority: P1. Method type: model_family.

Consider a four-sublattice representation when the target ordering requires distinctions lost in a two-site description.

**Applies when:** FCC ordering and intended multicomponent extension.

**Limits:** Do not force this model on every FCC solution or infer parameters from its name.

**Validation:** Reproduce disordered and ordered limits and relevant ordering transitions.

**Sources:**
- [Calphad Modeling of LRO and SRO Using ab initio Data](https://www.mdpi.com/2075-4701/10/8/998) — primary article indexed passages inspected; direct full-text request rate-limited; locator: Sections 2.3, 4.2, 5.2.1, 5.2.2; indexed passages.

## sro-correction — Explicit SRO contribution review

Topic: ordering. Priority: P1. Method type: approximation.

Consider a documented SRO approximation and separate it from existing energetic contributions.

**Applies when:** Short-range order affects thermodynamic observables beyond the chosen baseline.

**Limits:** A generic reciprocal interaction is not proof of a validated SRO treatment.

**Validation:** Compare random and ordered limits and independently measured thermochemistry.

**Sources:**
- [A description of the effect of short range ordering in the compound energy formalism](https://www.sciencedirect.com/science/article/abs/pii/S0364591604000148) — publisher abstract and introduction inspected; locator: Reciprocal interaction parameters; SRO approximation.

## thermal-vacancy-reference — Consistent thermal-vacancy reference conventions

Topic: vacancies. Priority: P0. Method type: conditional_reparameterization.

Evaluate the vacancy reference and interactions together rather than prescribing a universal reference energy.

**Applies when:** Thermal-vacancy model within the source formulation and validity domain.

**Limits:** Zero and positive reference conventions can be equivalent under the prescribed mapping; neither is universally safe.

**Validation:** Reproduce vacancy concentrations, heat capacity and high-temperature phase stability.

**Sources:**
- [Including state-of-the-art physical understanding of thermal vacancies in Calphad models](https://www.nature.com/articles/s41598-022-16926-5) — primary results and conclusion passages inspected; locator: Heat capacity comparison; Conclusion: equivalence of vacancy reference conventions under parameterization.
- [Thermodynamic modelling of vacancies as a constituent](https://doi.org/10.1016/j.calphad.2019.101666) — publisher abstract inspected; equations not verified; locator: Abstract.

## vacancy-double-count — Avoid double-counting thermal vacancies

Topic: vacancies. Priority: P0. Method type: consistency_check.

Check whether existing heat-capacity functions already include vacancy contributions before adding an explicit term.

**Applies when:** An existing unary description is extended with thermal vacancies.

**Limits:** Do not subtract an arbitrary correction without refitting or a justified decomposition.

**Validation:** Compare original and revised Cp plus held-out vacancy concentration data.

**Sources:**
- [Including state-of-the-art physical understanding of thermal vacancies in Calphad models](https://www.nature.com/articles/s41598-022-16926-5) — primary results and conclusion passages inspected; locator: Heat capacity comparison; Conclusion: equivalence of vacancy reference conventions under parameterization.

## defect-mechanism — Distinguish antisites and vacancy accommodation

Topic: vacancies. Priority: P0. Method type: model_selection.

Require occupancy and composition evidence before selecting a nonstoichiometry mechanism.

**Applies when:** Ordered or nonstoichiometric compounds.

**Limits:** This is a synthesis for model screening; abstract-level sources do not supply a universal defect-selection algorithm.

**Validation:** Predict both homogeneity range and independent site/defect observations.

**Sources:**
- [Thermodynamic modelling of vacancies as a constituent](https://doi.org/10.1016/j.calphad.2019.101666) — publisher abstract inspected; equations not verified; locator: Abstract.
- [Description of terminal substitutional solid solutions using the sublattice model](https://www.sciencedirect.com/science/article/abs/pii/S0364591619302081) — primary-source abstract/search passages inspected; locator: Abstract: terminal solutions with distinct site occupancies.

## terminal-multisite — Multisite terminal substitutional solutions

Topic: sublattices. Priority: P1. Method type: model_selection.

Allow multiple sublattices when terminal solid solutions show distinct site occupancies.

**Applies when:** An elemental structure has multiple inequivalent sites and appreciable substitution.

**Limits:** Terminal solution does not automatically mean one-sublattice ideal configurational entropy.

**Validation:** Compare site occupancy, entropy and phase boundaries with the single-site alternative.

**Sources:**
- [Description of terminal substitutional solid solutions using the sublattice model](https://www.sciencedirect.com/science/article/abs/pii/S0364591619302081) — primary-source abstract/search passages inspected; locator: Abstract: terminal solutions with distinct site occupancies.

## unary-consistency — Common unary functions and reference states

Topic: references. Priority: P0. Method type: consistency_check.

Identify exact unary functions and versions before combining fitted energies.

**Applies when:** Any assessment importing DFT, another database or a subsystem.

**Limits:** A matching reference-state label alone does not establish matching functions.

**Validation:** Compare unary G,H,S and transitions across imported components.

**Sources:**
- [SGTE data for pure elements](https://doi.org/10.1016/0364-5916(91)90030-N) — inherited bibliography lead; not independently full-text verified; locator: Local catalog entry.
- [ESPEI custom unary reference states](https://espei.org/how-to/custom_unary_data.html) — official documentation search passages inspected; locator: Custom unary reference states.

## reference-change — Controlled replacement of lattice stabilities

Topic: references. Priority: P1. Method type: conditional_reparameterization.

Propagate a changed elemental reference through affected assessment parameters.

**Applies when:** Replacing a lattice stability in an existing database.

**Limits:** Adding an energy offset to one term may change phase equilibria unintentionally.

**Validation:** Demonstrate intended preservation or documented changes of assessed equilibria.

**Sources:**
- [Revisiting the SGTE lattice stability of bcc aluminum](https://www.sciencedirect.com/science/article/pii/S0364591623001001) — publisher abstract and highlights inspected; locator: Inflection detection; reference replacement.

## mechanical-instability — Retain phase identity during atomistic relaxation

Topic: atomistics. Priority: P0. Method type: consistency_check.

Distinguish constrained reference energies, relaxed transformed structures and physical metastable phases.

**Applies when:** Relaxation changes topology or harmonic modes indicate instability.

**Limits:** A high-symmetry stationary structure is not necessarily mechanically stable.

**Validation:** Record strain/site mapping and stability diagnostics; do not label transformed energy as the original endmember.

**Sources:**
- [Calphad Modeling of LRO and SRO Using ab initio Data](https://www.mdpi.com/2075-4701/10/8/998) — primary article indexed passages inspected; direct full-text request rate-limited; locator: Sections 2.3, 4.2, 5.2.1, 5.2.2; indexed passages.
- [A computational free energy reference for mechanically unstable phases](https://www.sciencedirect.com/science/article/pii/S0364591625000720) — publisher abstract and highlights inspected; locator: Inflection detection and finite-temperature reference.

## unstable-reference — Inflection-detection reference candidate

Topic: atomistics. Priority: P1. Method type: specialized_method.

Evaluate a documented unstable-phase reference construction instead of assigning a collapsed structure energy.

**Applies when:** Mechanically unstable reference phases needed by CALPHAD.

**Limits:** Abstract screening only; method equations and examples must be reproduced before execution.

**Validation:** Reproduce published reference energy and finite-temperature treatment.

**Sources:**
- [Revisiting the SGTE lattice stability of bcc aluminum](https://www.sciencedirect.com/science/article/pii/S0364591623001001) — publisher abstract and highlights inspected; locator: Inflection detection; reference replacement.
- [A computational free energy reference for mechanically unstable phases](https://www.sciencedirect.com/science/article/pii/S0364591625000720) — publisher abstract and highlights inspected; locator: Inflection detection and finite-temperature reference.

## magnetic-consistency — Magnetic state and thermodynamic contribution consistency

Topic: magnetism. Priority: P0. Method type: consistency_check.

Track magnetic state in atomistic energies and the selected CALPHAD magnetic contribution.

**Applies when:** Magnetic phases or mixed ferro/antiferromagnetic systems.

**Limits:** Do not mix spin-polarized energies with a second unexamined ordering contribution.

**Validation:** Test transition behavior, entropy and limiting magnetic states.

**Sources:**
- [An improved magnetic model for thermodynamic modeling](https://www.sciencedirect.com/science/article/pii/S0364591612000612) — primary-source abstract/search passages inspected; locator: Abstract: ferro/antiferromagnetic artifacts.

## low-temperature — Low-temperature and third-law domain checks

Topic: temperature. Priority: P1. Method type: consistency_check.

Use a temperature model whose domain includes the intended low-temperature application.

**Applies when:** Extending a database below its assessed temperature interval.

**Limits:** Do not extrapolate a high-temperature polynomial to zero kelvin by default.

**Validation:** Check Cp and entropy limits and compare independent low-temperature measurements.

**Sources:**
- [Modeling of Gibbs energies of pure elements down to 0 K using segmented regression](https://www.sciencedirect.com/science/article/pii/S0364591616300906) — primary-source abstract/search passages inspected; locator: Abstract and introduction: low-temperature domain.

## high-temperature — Spurious solid restabilization scan

Topic: temperature. Priority: P0. Method type: consistency_check.

Check whether extrapolated solid functions spuriously undercut the liquid at high temperature.

**Applies when:** Solid descriptions used well above their stable domain.

**Limits:** Do not suppress a phase merely to hide an unexplained model artifact.

**Validation:** Reproduce a documented extrapolation treatment and scan competing Gibbs energies.

**Sources:**
- [A method for handling the extrapolation of solid crystalline phases to temperatures far above their melting point](https://www.nist.gov/publications/method-handling-extrapolation-solid-crystalline-phases-temperatures-far-above-their) — primary-source abstract/search passages inspected; locator: Abstract: spurious high-temperature restabilization.

## ionic-liquid — Two-sublattice ionic liquid candidate

Topic: ionic. Priority: P1. Method type: model_family.

Use the appropriate ionic-liquid formalism and its multicomponent-compatible expressions.

**Applies when:** Metal/oxide or ionic liquid descriptions requiring varying ionic character.

**Limits:** Current executable schema does not support charged species or variable site ratios; this entry is catalog-only.

**Validation:** Check charge balance and metallic/ionic limiting cases.

**Sources:**
- [Modification of the two-sublattice model for liquids](https://www.sciencedirect.com/science/article/pii/036459169190010H) — publisher abstract inspected; locator: Abstract: multicomponent compatibility.

## charge-domain — Charge-constrained admissible model domain

Topic: ionic. Priority: P1. Method type: constraint_family.

Construct the feasible occupancy domain with charge and stoichiometric constraints.

**Applies when:** Charged species in solids or ionic-liquid modeling.

**Limits:** Fixed-site and variable-ratio models require different implementations; catalog-only in v0.1.

**Validation:** Verify feasible endmembers, constraint rank and neutrality throughout sampled states.

**Sources:**
- [Notes on the creation and manipulation of solid solution models](https://link.springer.com/article/10.1007/s00410-021-01825-1) — primary abstract and methods/Appendix A passages inspected; locator: Model geometry; independent endmember bases; Appendix A code.
- [Modification of the two-sublattice model for liquids](https://www.sciencedirect.com/science/article/pii/036459169190010H) — publisher abstract inspected; locator: Abstract: multicomponent compatibility.

## mqm-pair — Modified quasichemical pair model

Topic: liquids. Priority: P1. Method type: model_family.

Consider pair-based configurational treatment where liquid SRO motivates it.

**Applies when:** Liquid or solid solutions within the pair approximation assumptions.

**Limits:** Not interchangeable with a random-mixing polynomial merely because both fit one dataset.

**Validation:** Recover random limit and reproduce pair fractions and thermochemistry.

**Sources:**
- [The Modified Quasichemical Model I—Binary Solutions](https://users.encs.concordia.ca/~tmg/images/3/3a/Modified_Quasichemical_Model-part_1.pdf) — primary paper first-page theory inspected; locator: Introduction; equations 1–10.

## mqm-quadruplet — Two-sublattice quadruplet treatment

Topic: liquids. Priority: P1. Method type: model_family.

Consider separate first- and second-neighbor SRO within a documented quadruplet model.

**Applies when:** Two-sublattice solutions with both SRO contributions.

**Limits:** Requires model-specific constituent definitions and normalization; catalog-only.

**Validation:** Recover pair-model limit and verify quadruplet/site balances.

**Sources:**
- [The modified quasi-chemical model: Part IV. Two-sublattice quadruplet approximation](https://doi.org/10.1007/s11661-001-0230-7) — publisher abstract inspected; locator: Abstract: FNN/SNN SRO and limiting cases.

## geometric-extrapolation — Choose and document multicomponent interpolation

Topic: extrapolation. Priority: P0. Method type: modeling_convention.

Record geometric interpolation conventions and test binary boundaries and ternary interiors.

**Applies when:** Combining lower-order interaction descriptions.

**Limits:** Muggianu, Toop and Kohler assumptions are not universally interchangeable.

**Validation:** Recover subsystem limits and compare independent higher-component equilibria.

**Sources:**
- [Interpolation and extrapolation with the CALPHAD method](https://www.jmst.org/article/2019/1005-0302/1005-0302-35-9-2115.shtml) — primary article methods and discussion passages inspected; locator: Binary and ternary weighting; geometric models.

## staged-assessment — Stage parameter assessment

Topic: assessment. Priority: P0. Method type: assessment_practice.

Organize evidence and constrain models before progressively fitting additional terms.

**Applies when:** New or revised thermodynamic assessments.

**Limits:** This workflow does not determine a universal parameter order.

**Validation:** Compare independent thermochemical and constitutional observations after each stage.

**Sources:**
- [Some guidelines for thermodynamic optimisation of phase diagrams](https://www.sciencedirect.com/science/article/pii/S0925838800014912) — primary-source abstract/search passages inspected; locator: Abstract and introduction: evidence, constraints, optimization.

## aicc-selection — Complexity-controlled parameter selection

Topic: statistics. Priority: P0. Method type: statistical_method.

Compare candidate parameter terms with a documented complexity penalty.

**Applies when:** A specified model family with suitable thermochemical data.

**Limits:** AICc does not choose the correct crystal model; invalid small-sample denominators and dependent data need handling. A within-subsystem complexity score does not test extrapolation to higher-order systems; see parsimony-for-extrapolation.

**Validation:** Verify score definition, identifiable terms and held-out predictions.

**Sources:**
- [ESPEI for efficient thermodynamic database development, modification, and uncertainty quantification: application to Cu–Mg](https://arxiv.org/abs/1902.01269) — primary preprint metadata and published supplementary documentation passages inspected; locator: Supplement: parameter_selection.selection.score_model; AICc.

## dataset-weighting — Dataset-level weighting and outlier review

Topic: statistics. Priority: P0. Method type: statistical_method.

Estimate or review dataset weights while preserving source-level disagreements.

**Applies when:** Conflicting thermochemical datasets with documented uncertainty.

**Limits:** Downweighting can conceal model discrepancy or a genuine transition; inspect physical causes.

**Validation:** Compare inferred weights against methods and source quality, and test sensitivity.

**Sources:**
- [Comparison of statistically-based methods for automated weighting of experimental data in CALPHAD-type assessment](https://www.osti.gov/servlets/purl/1592101) — primary-source abstract/search passages inspected; locator: Abstract: classical and Bayesian dataset weighting.

## information-design — Sensitivity-guided measurements and calculations

Topic: statistics. Priority: P0. Method type: statistical_method.

Use parameter sensitivity and information diagnostics to identify informative additional observations.

**Applies when:** A fitted candidate and explicit observation/error model.

**Limits:** Local sensitivity does not prove global identifiability; account for topology changes.

**Validation:** Compare rank/conditioning and uncertainty reduction across candidate observations.

**Sources:**
- [Sensitivity estimation for calculated phase equilibria](https://link.springer.com/article/10.1557/s43578-020-00073-6) — primary-source abstract/search passages inspected; locator: Sensitivity framework and Fisher information case study.

## posterior-checks — Parameter uncertainty and prediction propagation

Topic: statistics. Priority: P1. Method type: statistical_method.

Propagate parameter uncertainty to the observables used for decisions.

**Applies when:** A justified likelihood, priors and validated candidate model.

**Limits:** Conditional parameter uncertainty omits unmodeled model-form error.

**Validation:** Check convergence, predictive residuals and sensitivity to priors/data selection.

**Sources:**
- [ESPEI for efficient thermodynamic database development, modification, and uncertainty quantification: application to Cu–Mg](https://arxiv.org/abs/1902.01269) — primary preprint metadata and published supplementary documentation passages inspected; locator: Supplement: parameter_selection.selection.score_model; AICc.
- [Sensitivity estimation for calculated phase equilibria](https://link.springer.com/article/10.1557/s43578-020-00073-6) — primary-source abstract/search passages inspected; locator: Sensitivity framework and Fisher information case study.

## topology-review — Ternary topology and cross-section consistency

Topic: assessment. Priority: P0. Method type: consistency_check.

Cross-check phase-diagram sections, reactions and bounding subsystems before fitting.

**Applies when:** Constitutional data from multiple diagram representations.

**Limits:** A low optimization residual cannot resolve contradictory interpretations.

**Validation:** Test phase-rule consistency and compatible phase fields and reaction connections.

**Sources:**
- [Critical evaluation of ternary phase diagram data: Important considerations in the scrutiny of the correctness, coherence, and interpretation](https://www.sciencedirect.com/science/article/pii/S0364591619302809) — primary-source abstract/search passages inspected; locator: Publisher title and indexed abstract passages.

## steering-acceptance — Acceptance gate for steered or adaptive refits

Topic: assessment. Priority: P0. Method type: assessment_practice. Status: project rule; literature support pending.

Accept a fit whose objective was steered (re-weighted data, points added from an expected diagram, penalty terms on unattested phases) only if, against a control fit with the same evidence, constraints, optimiser, seeds and budget but no steering, the data-only misfit of every evidence class (phase boundaries, invariants, thermochemistry, first-principles energies; each against its own uncertainty) is no worse. Independent held-out evidence, preferably regions of the diagram excluded from both fitting and steering, ranks the accepted fits; it does not reject them.

**Applies when:** Any assessment loop that changes weights, adds evidence-derived points or adds penalty terms in response to a diagnosis of the calculated diagram.

**Limits:** A diagram-agreement score measured against the evidence used for steering is not independent and never justifies a fit on its own. The tolerance for 'no worse' must be stated and justified before the comparison (for example, the change expected from noise). A second assessment overlaid on the same diagram is not an independent hold-out: where it disagrees with the primary evidence it rewards matching the alternative. Held-out regions must be chosen before fitting and never used for steering; with little evidence the ranking has low power.

**Validation:** Report data-only misfit per evidence class and the count of points beyond 2 sigma for steered and control fits; label each steered fit accepted or rejected with the numbers behind the label. For each held-out region, refit without that region's evidence and steering and score only that region; rank accepted fits by held-out performance, with ties where differences are within tolerance.

**Sources:**
- ORCHID assessment rules set by the project PI (R. Arróyave) during the Co–Ga topology study (board task Y36) — internal project rule, recorded 2026-10-30; not a publication; literature support to be added after full-text verification; locator: PI statements, 30 Oct 2026: 'we can't overfit'; 'be mindful of making models too complex as they may break when extrapolating to higher order systems'.
- [ESPEI for efficient thermodynamic database development, modification, and uncertainty quantification: application to Cu–Mg](https://arxiv.org/abs/1902.01269) — primary preprint metadata and published supplementary documentation passages inspected; locator: Supplement: parameter_selection.selection.score_model; AICc.

## parsimony-for-extrapolation — Parsimony for extrapolation to higher-order systems

Topic: extrapolation. Priority: P0. Method type: model_selection. Status: project rule; literature support pending.

Prefer the simplest model that describes the data, because empirical complexity in a binary or ternary description is inherited by every higher-order system built on it. Parsimony targets empirical terms (high-order excess terms, temperature dependence without thermochemical support, large compensating parameters), not physically motivated structure such as an order-disorder partition or a magnetic contribution with a known transition temperature, which is judged by whether each parameter is physically constrained and supported by data.

**Applies when:** Any lower-order description intended for combination into multicomponent databases.

**Limits:** A complexity criterion within the fitted subsystem (for example AICc) is necessary but does not test extrapolation. A ternary check without ternary parameters or data detects breakage, not accuracy. Physically motivated models add parameters yet may extrapolate better; parameter count alone is not the criterion.

**Validation:** Report parameter count and highest excess-term order per phase, separating physical from empirical parameters. Scan every phase's Gibbs energy over the full composition range and a wide temperature range, including metastable regions: no inverted miscibility gaps, no spurious restabilization, no implausibly large or compensating parameters. Check sublattice models and phase names against the conventions of neighbouring systems so the description can be merged. Where neighbouring descriptions exist, combine them without higher-order parameters and check sections for spurious phases.

**Sources:**
- ORCHID assessment rules set by the project PI (R. Arróyave) during the Co–Ga topology study (board task Y36) — internal project rule, recorded 2026-10-30; not a publication; literature support to be added after full-text verification; locator: PI statements, 30 Oct 2026: 'we can't overfit'; 'be mindful of making models too complex as they may break when extrapolating to higher order systems'.
- [ESPEI for efficient thermodynamic database development, modification, and uncertainty quantification: application to Cu–Mg](https://arxiv.org/abs/1902.01269) — primary preprint metadata and published supplementary documentation passages inspected; locator: Supplement: parameter_selection.selection.score_model; AICc.
- [Interpolation and extrapolation with the CALPHAD method](https://www.jmst.org/article/2019/1005-0302/1005-0302-35-9-2115.shtml) — primary article methods and discussion passages inspected; locator: Binary and ternary weighting; geometric models.
- [A method for handling the extrapolation of solid crystalline phases to temperatures far above their melting point](https://www.nist.gov/publications/method-handling-extrapolation-solid-crystalline-phases-temperatures-far-above-their) — primary-source abstract/search passages inspected; locator: Abstract: spurious high-temperature restabilization.

## Additional source leads

Entries below extend the search queue; their presence does not imply they have been read or converted into recipes.

- [A regular solution model for phases with several components and sublattices, suitable for computer applications](https://doi.org/10.1016/0022-3697(81)90144-X) — inherited bibliography lead; not independently full-text verified.
- [A Bayesian approach to evaluating the uncertainty of thermodynamic data and phase diagrams](https://doi.org/10.1016/j.calphad.2003.11.002) — inherited bibliography lead; not independently full-text verified.
- [Vacancy thermodynamics for intermediate phases using the compound energy formalism](https://doi.org/10.1016/j.actamat.2008.07.002) — inherited bibliography lead; not independently full-text verified.
- [Critical Evaluation of Binary Phase Diagram Data: Best Practice Guidelines for Evaluation & Notes for Authors](https://www.apdic.info/fileadmin/content/research/binary_evaluations/docs/notes_authors_binary.pdf) — inherited bibliography lead; not independently full-text verified.
- [Critical Evaluation of Ternary Phase Diagram Data: Best Practice Guidelines for Evaluation & Notes for Authors](https://www.msiport.com/fileadmin/content/research/ternary_evaluations/docs/notes_author_ternary.pdf) — inherited bibliography lead; not independently full-text verified.
- [Critical Assessment 5: Thermodynamic data for vacancies](https://doi.org/10.1179/1743284714Y.0000000589) — inherited bibliography lead; not independently full-text verified.
- [The Need for Reliable Experimental Data in Computational Thermodynamics](https://doi.org/10.32908/hthp.v49.853) — inherited bibliography lead; not independently full-text verified.
- [Generalized method of sensitivity analysis for uncertainty quantification in Calphad calculations](https://doi.org/10.1016/j.calphad.2022.102504) — inherited bibliography lead; not independently full-text verified.
- [On the compound energy formalism applied to fcc ordering](https://doi.org/10.1016/S0364-5916(02)00007-X) — inherited bibliography lead; not independently full-text verified.
- [A note on models for phases with order/disorder transitions in thermodynamic software and databases](https://doi.org/10.2298/JMMB170801023S) — inherited bibliography lead; not independently full-text verified.
- [The compound energy formalism](https://doi.org/10.1016/S0925-8388(00)01481-X) — inherited bibliography lead; not independently full-text verified.
- [Modelling of thermodynamics and diffusion in multicomponent systems](https://doi.org/10.1179/174328408X372001) — inherited bibliography lead; not independently full-text verified.
- [Thermodynamic modelling of liquids: CALPHAD approaches and contributions from statistical physics](https://doi.org/10.1002/pssb.201350149) — inherited bibliography lead; not independently full-text verified.
- [The exponential excess Gibbs energy model revisited](https://doi.org/10.1016/j.calphad.2017.01.002) — inherited bibliography lead; not independently full-text verified.
- [Applying the Effective Bond Energy Formalism (EBEF) to describe the mu (μ) and sigma (σ) phases in the Co-Cr-Ni-W system](https://www.sciencedirect.com/science/article/abs/pii/S0364591625001002) — publisher abstract inspected.
- [The development of phase-based property data using the CALPHAD method and infrastructure needs](https://doi.org/10.1186/2193-9772-3-12) — inherited bibliography lead; not independently full-text verified.
- [Revised thermodynamic description of the Fe-Cr system based on an improved sublattice model of the σ phase](https://doi.org/10.1016/j.calphad.2017.10.002) — inherited bibliography lead; not independently full-text verified.
