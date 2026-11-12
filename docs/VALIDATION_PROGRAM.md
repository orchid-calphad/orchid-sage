# Validation program

Validation must cover the full recipe library, with EBEF as one case. Use PhaseForge and VISION when new atomistic calculations are required. PhaseForge is available locally; VISION's location has been requested and its capabilities remain unverified.

| Recipe family | Required positive test | Required counterexample |
|---|---|---|
| Reciprocal relations | Explicit nonzero relation and justified site symmetry | Same composition but different energies |
| EBEF | Published binary reproduction and higher-component holdout | Higher-order interactions outside the approximation |
| Site merging | Full versus reduced energy, entropy and derivatives | Site preference invalidates merging |
| Ordering | Disordered limit, B2 ordering, then FCC ordering | Missing ordering states and false site symmetry |
| Vacancies | Stated reference convention and normalization | All-vacancy singularity and double-counted thermal terms |
| Reference states | Consistent elemental shift preserves equilibrium | Shift only one phase or mix molar bases |
| Relaxation | Constrained/unconstrained comparison with final structure checks | Transformed structure mislabeled as original phase |
| Magnetism and temperature | Published case within its validity range | Invalid low-temperature limits and high-temperature restabilization |
| Extrapolation and selection | Binary fit with independent ternary holdouts | Overfitting and unidentifiable parameters |
| Steering acceptance | Steered fit no worse than an unsteered control on data-only misfit per evidence class; accepted fits ranked on held-out regions | A low diagram score bought by distorting thermochemistry |
| Parsimony for extrapolation | Metastable Gibbs-energy scan and a merge with neighbouring systems without higher-order parameters | Empirical terms that fit the binary and break the ternary |
| Ionic and liquid models | Published numerical reproduction after schema extension | Charge imbalance and incorrect species domain |

Set tolerances before inspecting results. Exact transformations require equality to numerical tolerance within the stated domain, including derivatives where applicable. Approximate reductions require an error budget tied to the intended use. Successful execution and agreement between two workflows do not establish physical accuracy, especially when they share an MLIP or training data.

Record input and executable hashes, commits and local modifications, checkpoint identity, environment, constraints, seeds, reference states, normalization, runtime, final structures and raw outputs. Preserve failures. Distinguish analytical checks, integration checks, literature reproductions and predictive holdouts in the results ledger.

The initial PhaseForge integration check is `benchmarks/run_phaseforge_b2.py`. It calls the local MLIPcalc with CHGNet 0.3.0 on translated descriptions of unrelaxed B2 NiAl. The acceptance tolerance is fixed at 1e-5 in the energy units written by the executable. This tests translation invariance and executable integration only, not relaxed stability or predictive accuracy. It does not resume or change the optional ORCHID NiAl example.

Next calculation tests: cell-size normalization, occupation changes on inequivalent sites, and constrained versus unconstrained relaxation with structure identity checks. Run suitable matching cases through VISION once located. The broader scientific benchmarks above remain pending; the existing 17 unit tests do not substitute for them.

Completed initial integration checks: translation residual 9.50e-7 against tolerance 1e-5; doubled-cell energy residual 1.91e-6 against tolerance 2e-5. Both passed through PhaseForge MLIPcalc/CHGNet 0.3.0 using the existing mlipbench environment. Raw inputs, outputs and logs are in benchmarks/phaseforge-b2, including the initial missing-backend failure. These checks do not validate scientific recipe accuracy.
