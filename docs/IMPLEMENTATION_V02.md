# Mathematical checks and handoff — v0.2.0

The standalone tool now computes exact composition and site-occupancy ranks and solves explicitly supplied reciprocal-energy relations. These operations support model review without deciding whether a model is physically adequate. The catalog remains at 34 recipes and 42 source records; none has been promoted to a reproduced scientific recipe.

## Implemented operations

`python3 -m calphad_model_guide basis examples/sigma.json` enumerates at most 4096 formal corners and returns basis column indices, ranks and nullities using rational arithmetic. Composition columns contain elemental atom counts per formula unit. Occupancy columns distinguish occupants on different sublattices and include vacancies. The result includes formal all-vacancy corners when present; these are bookkeeping objects and do not establish a physically accessible state. Nullspace vectors and general basis transformations are not implemented.

The supplied four-component, five-site sigma specification gives 1024 corners, composition rank 4 and occupancy rank 16. A binary two-site example gives ranks 2 and 3. Neither result establishes the number of independent energy parameters or justifies removing calculations, because energetic differences can persist between configurations with identical composition.

`python3 -m calphad_model_guide reciprocal examples/reciprocal.json` solves `G_AC + G_BD - G_AD - G_BC = delta` for one missing value or reports the residual when all four are supplied. The caller must provide delta, a documented assumption and a common reference state. Inputs use a common J/mol_formula basis at a common thermodynamic state. Decimal and rational strings are accepted; output strings preserve exact fractions. A zero delta is never inserted automatically. Site labels describe a two-site rectangle with any remaining site occupations fixed. The tool cannot verify that the caller's energy labels, reference or assumption are physically correct.

## EBEF reproduction target

The primary target is Section 4.3 and equation (19) of [Pereira dos Santos and co-authors](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=956715), PDF pages 13–16. The paper constructs a binary indicator matrix relating endmember formation energies to effective bond terms and uses a pseudoinverse. This is distinct from either composition rank or a zero reciprocal-energy assumption.

Before exposing an EBEF transformation, implement the published matrix convention, check its dimensions and rank, reproduce a published binary case with the same energy normalization and reference corrections, and record reconstruction residuals. Then test independent configurations and preserve the distinction between fitted energies and the later thermodynamic adjustments. The equations and extracted matrix text have been inspected; a numerical reproduction and a visual transcription check remain outstanding. No EBEF solver is included in v0.2.0.

## Verification and continuation

All 17 unit tests pass, including the existing 13 checks, exact fractional arithmetic, both ranks, enumeration limits, every possible missing reciprocal term, nonzero residuals and rejection of undocumented or invalid constraints. This is software evidence, not validation of a CALPHAD assessment. The new routines use only the Python standard library and make no network calls.

Next work should reproduce one published EBEF case, then add transformation and derivative checks before connecting these methods to automated calculation planning. MCP, provider adapters, charged species, variable site ratios and scientific domain review remain pending. No ORCHID dataset, manuscript, release or repository was changed by this implementation.
