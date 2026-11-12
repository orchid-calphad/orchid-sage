# CALPHAD modeling recipes: literature search and implementation priorities

Prepared 27 October 2026. This is a structured scoping search, not an exhaustive systematic review. The accompanying catalog preserves primary-source links and differentiates inspected abstracts or passages from inherited bibliographic leads. None of its scientific recipes has yet passed numerical reproduction within this tool.

## Scope and search method

The search began with the user's sigma-phase example and expanded through modeling families and assessment tasks. Targeted web queries covered EBEF, reciprocal endmember relationships, ordering constraints, vacancy reference conventions, mechanically unstable phases, lattice stabilities, magnetic models, low/high-temperature extrapolation, ionic liquids, quasichemical models, model bases, statistical parameter selection, weighting, sensitivity and multicomponent compatibility. The local ORCHID bibliography was queried for Kattner and effective-bond work. An existing local best-practices bibliography supplied additional leads, which retain their inherited status unless independently checked.

Primary papers, author manuscripts, institutional publication pages and official software documentation were used to support the retained entries. Aggregator results served only as discovery leads. Full-text access varied: NIST papers and selected author manuscripts were available, while some publisher requests failed or provided abstracts only. The search did not download restricted articles, inspect all cited equations or reproduce numerical examples. Inherited entries should not be counted as newly read papers.

## Findings that change the proposed tool

### Preserve sites while reducing energetic freedom

The EBEF papers support a distinction between crystallographic resolution and the number of independent energy parameters. The 2018 formulation and the 2023 sigma application should anchor an implementation effort, with the later Co–Cr–Ni–W application serving as an additional test involving two TCP phases. The recommendation is to retain alternative conventional CEF descriptions and compare them against EBEF using independent evidence. The catalog does not promise exact recovery of arbitrary endmember energies from a reduced basis. [2018 formulation](https://doi.org/10.6028/jres.123.020), [2023 sigma application](https://doi.org/10.1007/s11669-023-01079-3), [2025 mu/sigma application](https://doi.org/10.1016/j.calphad.2025.102897).

### Distinguish several kinds of reduction

A zero-reciprocal-energy estimate, a symmetry relationship, a change of endmember basis and an empirical sublattice merger have different meanings. The first imposes an energetic assumption; symmetry requires a crystallographic mapping; an exact basis transformation must retain the represented energy function; site merging restricts the modeled occupancy space. These operations must carry different method labels and validation tests. The LRO/SRO article identifies reciprocal estimates for missing endmembers, but tracing its original cited construction remains outstanding. [LRO/SRO discussion, especially Sections 2.3 and 5.2](https://doi.org/10.3390/met10080998).

Myhill and Connolly provide a mathematical treatment of fixed-site solution-model geometry, independent endmember bases and transformations, with accompanying code. This is particularly useful for a general tool because it exposes domain and basis questions separately from phase-specific empirical choices. Composition-vector dependence alone must never be interpreted as an energy identity. [Model construction and manipulation](https://doi.org/10.1007/s00410-021-01825-1).

### Vacancy conventions need conditional rules

The library should not encode a universal requirement that the pure-vacancy energy be either zero or positive. The 2019 treatment discusses vacancy content and limiting states, while the 2022 thermal-vacancy study shows how different reference conventions can yield equivalent descriptions under its specified parameterization. The latter also discusses avoiding double counting contributions already represented in heat-capacity descriptions. Treat these as conditional methods, with checks on defect concentration, thermophysical properties and phase stability. [Vacancies as a constituent](https://doi.org/10.1016/j.calphad.2019.101666), [thermal-vacancy treatment](https://doi.org/10.1038/s41598-022-16926-5).

### Relaxation is part of the thermodynamic definition

A structure that transforms during atomistic relaxation cannot simply supply an energy labeled as the initial phase. A constrained stationary structure also need not be a physical metastable state. Recent work on inflection-detection references gives a candidate treatment for mechanically unstable phases, but the accessible abstracts do not justify implementing its equations by inference. The tool should first record structural identity, constraints and instability diagnostics. [Bcc-Al reference](https://doi.org/10.1016/j.calphad.2023.102628), [finite-temperature unstable-phase reference](https://doi.org/10.1016/j.calphad.2025.102869).

### Model quality extends outside the fitted phase boundaries

Magnetic contributions, low-temperature behavior and high-temperature extrapolation need independent checks. The magnetic-model study identifies artifacts in mixed magnetic systems. Low-temperature unary work addresses a regime for which conventional high-temperature polynomials were not designed. The high-temperature study addresses artificial restabilization of crystalline phases. These findings motivate diagnostic recipes rather than automatic replacement of existing models. [Magnetism](https://doi.org/10.1016/j.calphad.2012.07.002), [low-temperature unary models](https://doi.org/10.1016/j.calphad.2016.09.001), [high-temperature extrapolation](https://doi.org/10.1016/j.calphad.2020.101737).

### A general tool must include nonmetallic model families

Ionic-liquid and quasichemical approaches require species, charge, coordination and sometimes composition-dependent site ratios beyond a neutral fixed-site schema. The catalog therefore includes them without pretending that the initial executable interface supports their domains. A future adapter must preserve their limiting cases and normalization. [Ionic-liquid model](https://doi.org/10.1016/0364-5916(91)90010-H), [quasichemical pair model](https://doi.org/10.1007/s11663-000-0103-2), [quadruplet model](https://doi.org/10.1007/s11661-001-0230-7).

### Model selection and information selection belong together

ESPEI's documented parameter selection provides a precedent for controlling complexity within a specified model family. Dataset-weighting methods address disagreement and outliers, while sensitivity analysis can identify observations that constrain poorly determined parameters. These methods do not replace crystallographic reasoning or quantify model-form uncertainty automatically. They suggest a workflow in which model construction, fitting and the choice of the next measurement inform each other. [ESPEI paper](https://doi.org/10.1557/mrc.2019.59), [dataset weighting](https://doi.org/10.1016/j.calphad.2019.101728), [sensitivity analysis](https://doi.org/10.1557/s43578-020-00073-6).

## Priorities

The first implementation tier should cover explicit normalization and references, vacancy interpretation, composition/occupancy bases, symmetry constraints, a reproduced EBEF case and checks for incompatible subsystem models. A second tier should add magnetic and temperature-dependent contributions, statistical diagnostics and carefully scoped liquid/ionic adapters. Pressure-dependent and kinetic models require additional domain representations and remain research extensions.

Success should be judged by demonstrated recovery of published examples, detection of invalid assumptions and useful performance on held-out observations. A larger bibliography alone does not establish a better model recommendation engine.

## Remaining gaps

Equation-level review and expert adjudication remain necessary for every recipe selected for execution. The coverage is strongest for metallic CALPHAD and adjacent fixed-site solution models. Gas/associate models, aqueous electrolytes, pressure-dependent thermodynamics, diffusion mobilities and treatment of molecular constituents need deeper dedicated searches. The catalog records bibliographic leads separately so the tool can expand without treating incomplete reading as verified guidance.
