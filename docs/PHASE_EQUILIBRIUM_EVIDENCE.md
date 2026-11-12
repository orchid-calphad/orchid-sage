# Phase-equilibrium evidence: present and absent phases

## Scope and status

This document records a proposed scientific extension for ORCHID-SAGE and its PhaseForge/ESPEI consumers. It does not claim that the current ORCHID-SAGE prototype implements CALPHAD fitting or phase-equilibrium residuals. The extension must be reviewed and validated before being treated as an executable recipe.

## State definition

An assessed equilibrium state at temperature, pressure, and overall composition records both:

1. every modeled phase observed in the equilibrium assemblage; and
2. every other phase in the declared candidate phase set that was not observed.

The latter is positive evidence about phase stability. A state is not fully represented by listing only the phases present. The candidate phase set and database/model version must be explicit; a phase absent from that model cannot be constrained.

This applies to single-phase, two-phase, and higher-order assemblages. Single-phase states are valid observations and must not be discarded by a filter designed only for tie-lines. For a multiphase state whose individual phase compositions are unknown, retain the overall-composition hyperplane constraint (ORCHID's `__HYPERPLANE__` representation) rather than requiring invented endpoint compositions.

## Thermodynamic sign convention and absence margin

Let the equilibrium chemical-potential vector define the common tangent hyperplane at overall composition `x`, with value `mu_bar dot x`. For candidate phase `p`, define its tangent-plane stability residual per mole of atoms as

`X_p = mu_bar dot x_p - G_p(T, P, x_p)`.

The phase composition `x_p` is selected to find the most competitive state of phase `p` against the hyperplane. Under this convention, a present phase has `X_p = 0` at equilibrium (within numerical/data tolerance). An absent phase should satisfy

`X_p <= -m`,

equivalently `G_p - mu_bar dot x_p >= m`.

Use a one-sided penalty only when the absent phase violates the requested margin:

`r_abs,p = max(0, X_p + m)`.

The initial conservative stability margin is **m = 100 J/mol-atoms**. Treat this as a minimum working threshold, not a fitted observation or universal constant; a larger value may be appropriate when supported by the assessment's uncertainty and numerical error. Record the selected margin, energy normalization, phase set, and source for every calculation. Do not penalize an absent phase for being more unstable than the margin.

For example, with a weighted least-squares objective, a possible contribution is `0.5 * w * (r_abs,p / sigma_p)^2`; `sigma_p` and `w` must follow the chosen observation/error model. For a dense grid, points in the same assessed field are dependent: use the field-level weight share (for example, `1/n_points_in_field`) rather than treating every grid point as an independent experiment. The margin does not replace that dependence correction.

## Data reconciliation and computation requirements

- Account for every record in the selected source dataset. Give each a stable source identifier and a disposition: evaluated; duplicate with a traceable canonical record; or not evaluable with a specific, documented reason. Do not silently omit records.
- Evaluate every record whose phase set and conditions are representable by the declared model, including every single-phase state and every multiphase state. Do not retain only field centers or only states with fixed phase endpoints.
- At each evaluated state, constrain every listed-present phase and evaluate absence residuals for every other phase in the explicitly declared modeled phase set.
- A non-evaluable record is not evidence of an absent phase. Report the exact model-coverage, missing-data, or malformed-record reason and keep it visible in counts and outputs. If omitted source records could affect the scientific conclusion, resolve the model or data coverage gap before claiming full-grid validation.
- For unknown phase endpoints, derive the common tangent plane and phase driving forces using the same hyperplane formulation as the present-phase ZPF constraints. Where available, use the selected ESPEI gradient implementation and verify gradients against finite differences on representative single- and multiphase states.
- Preserve overall composition, temperature, pressure, field identity, source locator, assessment release, TDB hash, and field share.
- Resolve phase aliases and composition domains before evaluation. Record phases that could not be evaluated; never silently interpret calculation failure or missing model coverage as evidence of absence.
- Validate the residual sign with stable/unstable test cases and check unit conversion to J/mol-atoms. Test that a present phase reaches zero residual, an absent phase below the margin contributes zero penalty, and an absent phase inside the margin contributes a positive penalty.

## Relationship to the Cu-Zr chapter run

The selected 94Zen-LB dense source contains 353 raw records across 25 assessment fields. Of these, 177 were identified as compatible with the current TDB; 176 require phases absent from that TDB. The corrected workflow must reconcile all 353 records, evaluate all records the model can represent, and report the remaining records individually or by auditable reason-coded groups. The 176 records are not to be silently treated as invalid or absent-phase evidence. Resolve their coverage gap or clearly limit the scope of any result that cannot include them.

For each evaluable dense-grid state, include single-phase and multiphase observations through the hyperplane formulation, applying present-phase constraints and absent-phase margins. The earlier hinge diagnostic that retained 116 cells and skipped 61 two-phase states used an inadequate endpoint/anchor filter. Those 61 states were valid data and should be evaluated. Use an initial absent-phase margin of 100 J/mol-atoms or greater, state the chosen value, and document optimizer and thermodynamic validation separately.

## Promotion gate

Before this becomes a standard ORCHID-SAGE recipe, implement a versioned state schema and residual API, add synthetic sign/gradient tests, reproduce the residuals for a source-backed binary benchmark, and demonstrate that field weighting and source-record reconciliation are honored. Until then this is a documented design requirement, not an implemented feature or a claim of validated uncertainty calibration.
