# Development and scientific validation plan

The first release establishes an independent exchange format and transparent screening rules. Its catalog records what should be implemented and tested; it does not turn a paper citation into an executable scientific guarantee.

## Completed prototype

- Python API and CLI for search, validation, audit, recommendation, comparison and bounded planning.
- JSON schema and cross-field validation; source and input hashes in model reports.
- Recipes spanning model construction, endmember relations, vacancies, ordering, references, atomistics, magnetism, temperature, ionic models, liquids, extrapolation and statistics.
- Three intentionally incomplete examples and tests for configuration counting, normalization, conflicts, malformed input, compatibility and command behavior.

## Next implementation gates

1. Obtain domain review of the recipe assertions. Resolve equations and original references for the reciprocal-energy estimate, and preserve alternative vacancy conventions with their applicability conditions.
2. Implement exact rational linear algebra for composition/site constraints with explicit species stoichiometry and charge. Separate chemical basis rank from energetic degrees of freedom. Reproduce published Myhill–Connolly examples before generalizing.
3. Implement one source-verified EBEF mapping. Reproduce published energies/parameters, test rank and numerical conditioning, and validate on independent higher-order configurations. Do not label a heuristic pair-energy surrogate as EBEF.
4. Add Gibbs-energy and derivative equivalence tests for genuinely exact transformations, and occupancy/phase-equilibrium tests for approximations. Explicitly test reference-state changes and molar normalization.
5. Add data-provider adapters. ORCHID should supply phase/TDB provenance and candidate literature; direct TDB imports should retain file hashes and assessors' parameter conventions. Neither adapter should assume copied assessments are independent evidence.
6. Expose the tested Python API through MCP; add PhaseForge and ESPEI consumers. No MCP server is installed or registered in this prototype.
7. Evaluate a small benchmark spanning sigma/EBEF, ordered FCC or B2, and vacancy-bearing compounds. Hold out higher-order equilibria or configurations. Measure model adequacy, calculation cost and calibrated uncertainty separately.

The v1 model schema intentionally excludes charged or molecular species, variable site ratios and explicit energy expressions. Extend it before accepting oxide, salt, gas or pressure-dependent specifications. Preserve versioned migrations and reject unsupported features rather than coercing them into a neutral fixed-site model.

## Phase-equilibrium evidence extension

A phase-equilibrium state must represent both observed phases and non-observations for the declared candidate phase set, including valid single-phase states. Every source record must be reconciled, with explicit reasons for anything the model cannot evaluate. The proposed hyperplane-based residual, conservative 100 J/mol-atom minimum absence margin, dense-grid field weighting, and implementation gates are documented in [Phase-equilibrium evidence](PHASE_EQUILIBRIUM_EVIDENCE.md). This is a design requirement; the current prototype does not implement phase-equilibrium fitting.

## Recipe promotion

Use the progression `bibliographic lead → source-backed candidate → equation checked → numerical reproduction → domain review → executable recipe`. These stages describe the method's implementation evidence, not universal validity. Record counterexamples and competing methods as first-class entries. Promotion requires source locators, assumptions, test fixtures, a valid domain and reproducible results.

No live ORCHID release or manuscript needs to change while developing this tool. Research outputs may be archived in the team drive; publication, licensing and repository ownership remain separate decisions.

Version 0.2 implements neutral fixed-site composition/occupancy ranks and explicit reciprocal algebra. General transformations, charge constraints and published numerical reproductions in the gates above remain pending. See IMPLEMENTATION_V02.md.

The user expanded validation beyond EBEF: follow VALIDATION_PROGRAM.md and use PhaseForge and VISION for new calculations as appropriate. Two initial PhaseForge integration checks passed; VISION location remains pending.
