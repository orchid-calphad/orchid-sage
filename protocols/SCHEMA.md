# orchid-assessment-schema 1.0.0-draft.2

This is the standard schema family for an ORCHID assessment deliverable: the documents that let a person or a machine read how a CALPHAD database was made and make it again. Four document types share one family and one version string, `orchid-assessment-schema@1.0.0-draft.2` (draft.1 documents still validate). The changes from draft.1 are in sage_mcp/SCHEMA_GAPS.md (G1–G15, merged and rejected):

| type | file | what it is | where |
|---|---|---|---|
| `general_protocol` | `schema/protocol.schema.json` | a reusable, versioned method (Y32 level 1), e.g. `orchid-calphad-fit@2.0.0` | `general/*.yaml` |
| `specific_protocol` | `schema/protocol.schema.json` | the full recipe of ONE artifact (a TDB), instantiating a general protocol (Y32 level 2) | `specific/*.yaml` |
| `run_card` | `schema/protocol.schema.json` | one execution: host, interpreter, command, seeds, hashed inputs and outputs, results | `run_cards/*.json` |
| `assessment_results` | `schema/assessment-results.schema.json` | everything the dashboard shows, as data | `dashboards/<artifact>/dashboard_data.json` |

`schema/common.schema.json` holds the definitions they share (file reference with sha256 and storage class, decision, tolerance, environment, code reference, `pending`).

## How the documents connect

```
TDB (artifact) --produced_by--> specific protocol --instantiates--> general protocol
specific protocol --consists_of (run_sequence)--> run cards --executes--> a step of the general (or specific) protocol
dashboard data --specific_protocol--> specific protocol;  dashboard.html = render(dashboard data)
```

A specific protocol pins the general protocol by id@version **and** by file sha256, so editing the general protocol breaks the link until the specific protocol is re-pinned. Run cards are converted from the campaigns' own records (`tools/backfill_run_cards.py`) and never recomputed.

## Steps follow schema.org HowTo

A protocol has `sections` (HowToSection), and each section has `steps` (HowToStep). Each step carries:

| field | HowTo term | rule |
|---|---|---|
| `name`, `text` | name, text | text in the imperative, enough for a person to carry out the step |
| `supply` | supply | `input:<id>`, `param:<name>`, or `<earlier_step>.<result>`; the validator checks the order |
| `tool` | tool | name, exact `command` where one exists, `code` and `environment` ids |
| `result` | result | ids and names of the outputs, with the checks each must pass |
| `kind` | (ORCHID) | `deterministic` (byte-identical on rerun), `numerical` (requires `tolerances`), `judgement` (requires `decision_rule` and `decided_by`) |

## Gates and ranking

`gates` are hard checks of process and identity: the software build, pure elements, exclusions present, inputs hashed, trajectory recorded, dashboard present, independent rerun. `ranking_criteria` are soft (R1 plausible energies, R2 topology, R3 quantitative), following the PI rule "rank fits, pick the reasonable one". See OPEN_QUESTIONS Q02.

## ORCHID concepts are named, not reinvented

| concept | field here | ORCHID source |
|---|---|---|
| record id | `orchid_record_id` (pattern `ORC-` + 10) | literature/SCHEMA.md `id` |
| state, state class | `state_id` (`S-` + 10 hex), `state_class_id` (`C-` + 10 hex) | literature/SCHEMA.md (branch Y25/state-ids-locator), graph/SCHEMA.md |
| excluded phases | referred to as `excluded_phases`; hinge cells keep the espei/SCHEMA.md keys (`T, x, expected, tie_line, penalize, sigma, confidence, orchid{observation_id, state_id, hull_tolerance_J_per_mol_atom}`) | espei/SCHEMA.md (branch schema/excluded-phases) |
| uncertainty | `uncertainty_budget.sigma_effective` (named in step text) | literature/SCHEMA.md |
| TDB provenance | `artifact.tdb_provenance` uses `generation_method`, `potential`, `parents` | phases/tdb_provenance.schema.json |

Gaps (OPEN_QUESTIONS Q28–Q30): there is no machine-readable record or state schema to `$ref`, the picks' data carry no state ids yet, and per-state assemblage agreement was not computed.

## Storage classes and restricted material

Every file reference is `{path, sha256, storage_class}`:

- `public`: may be redistributed.
- `local`: our files, not yet released.
- `restricted`: publisher PDFs and private ORCHID exports (the restricted-material directory). Referenced by path and sha256 only, never copied into a crate, never quoted beyond 500 characters.
- `remote_record`: a file on another host, known only through a run card (hash recorded there).

Paths are written with `~`, never with a user name.

## Evidence bundles and certainty tiers

Each pick has a versioned, hashed evidence bundle in the repository at `assessments/<artifact>/evidence/`. A bundle is never overwritten: any change gives a new version, `MANIFEST@<version>.json` with `states@<version>.json` and `states_evaluated@<version>.json`. Version 1 (`MANIFEST.json`) is kept. A bundle holds:
- the exact ESPEI datasets and hinge sidecars the objective read (byte-identical copies);
- the one-shot observations;
- the model inputs needed for a rerun;
- reference outputs;
- `states@V.json`: one record per observed state, with tiers and ORCHID links;
- `states_evaluated@V.json`: expected vs calculated assemblage at every state, path-independent (basenames + sha256);
- `MANIFEST@V.json`: the sha256 of every file, the `bundle_sha256` over all of them, tier counts and link coverage.

Only derived facts go in. A file with a source-text field longer than 500 characters would be held, not copied. The specific protocol cites the bundle in `evidence_selection.bundle`.

### Certainty tiers (certainty-tiers@2, fit_protocol item 8, PI 6 Nov 2026)

Tiers are assigned by the general-protocol step `classify_certainty` (`tools/build_evidence_bundle.py`).

- **`exclusions[]`** (`exclusion_entry`, one per excluded phase):
  - fields: `phase`, `certainty_tier`, `energy_scale_J_per_mol_atom`, `certainty_basis`, `distance_sigma`, `n_independent_sources`;
  - 10 J/mol-atom: beyond 3 of the state's own uncertainties from any observed field or boundary of the phase, and no source reporting it there;
  - 50: within 3, or at a state of a single-source dataset: only a dataset the plan designates single source before fitting, with its reason (PI 7 Nov 2026; no automatic 3σ-neighbour rule; `build_evidence_bundle.py` plan `single_sources`, generic `--single-source MATCH=REASON`);
  - 100: adjacent, diagram-assumed or contested.
- **`zpf_certainty`** (one per state):
  - boundary and tie-line records: 100, or 50 when an independent source replicates them;
  - single-phase field states: by their distance to their phase's nearest boundary.

The tier is on each exclusion entry, not on the state. The readings used are listed in OPEN_QUESTIONS Q33.

### ORCHID linkage (required, PI 6 Nov 2026)

Every evidence state carries:
- `orchid_link`: `present` or `missing`;
- `orchid_ids`: ORCHID literature `id`, ORC-…;
- `state_ids`: Y25 `state_id` / `state_class_id`, S-/C-…;
- `orchid_release`: `v2026.10` or `unreleased`;
- `orchid_links[]`: the resolvable chain, i.e. the record `id`, `pid`, `paper_id` (DOI) and `locator` from `literature/systems/<SYS>.json` of the orchid-data-next checkout, then state ids, then `in_release`.

A missing link carries `missing_reason` and `intake_ref`, a path into `intake/intake_manifest.json` that resolves once the intake is released. The reasons are:
- a new extraction pending intake;
- a dataset without row-level ORC ids;
- an exclusion added by the campaign;
- a computed one-shot observation.

`validate.py` reports the coverage. It fails when a state claims an ORC id that does not resolve in the local checkout, or when a missing link has no reason or intake reference. The badge ids files (`fig_*_orchid_ids.json`) are generated from these links.

## Pending, never invented

Any quantity of the results document may be `{"status": "pending", "reason": "..."}`, and the dashboard shows it as pending. A start whose per-evaluation history was not saved gets `recorded: false` and only its start and end points ("trajectory not recorded"); nothing is interpolated.

## The trajectory record (required, PI 6 Nov 2026)

`assessment_results.trajectory.runs[]` holds one entry per step and start: `points[]` with `eval`, `objective`, `components`, `theta` (the full parameter vector, named by `parameter_names` with `parameter_units` and `phase_of_parameter`), `topology_class` where evaluated, `t_s`, `stage`. The general protocol step `record_trajectory` makes writing it a required output of every fit step (gate G5).

`projection` stores a deterministic 2-D basis:

- Every parameter is divided by a stated scale (prior sd where the objective has a prior, otherwise a declared display scale).
- `center` is the mean of all retained vectors.
- `basis` is the two leading eigenvectors of their covariance (Jacobi), with the largest-magnitude component of each made positive.

Anyone can therefore recompute the projected points from `theta`, `scale`, `center` and `basis`.

## Mapping to RO-Crate, PROV and schema.org

| ORCHID | RO-Crate / schema.org | W3C PROV-O |
|---|---|---|
| crate root | `Dataset`, `conformsTo` Process Run Crate 0.5 and Workflow Run Crate 0.5 | prov:Collection |
| specific protocol | `File` + `SoftwareSourceCode` + `ComputationalWorkflow` + `HowTo` (`mainEntity`) | prov:Plan |
| general protocol | `File` + `SoftwareSourceCode` + `HowTo`; specific `isBasedOn` general | prov:Plan (`instantiates` ≈ prov:specializationOf) |
| section / step | `HowToSection` / `HowToStep` (`step`, `position`, `text`) | prov:Plan part |
| step input / tool / result | `HowToSupply` / `HowToTool` / `result` | prov:used / prov:Agent (software) / prov:generated |
| run card | `CreateAction` (`instrument` = protocol, `object` = inputs, `result` = outputs, `startTime`, `endTime`, `actionStatus`, `agent` = host) with the card as `subjectOf` | prov:Activity; `hadPlan` → the HowToStep; `wasDerivedFrom` → the run it started from |
| artifact (TDB) | `File` in `artifact/`, `wasGeneratedBy` the overall run | prov:Entity, prov:wasGeneratedBy |
| campaign input not in the crate | contextual `CreativeWork` with `sha256` and `storageClass`; restricted ones carry `conditionsOfAccess` | prov:Entity |
| decision | one `ChooseAction` per `decisions[]` row (`tools/build_crate.py --decisions`; from crni-paper-fit-step4c-b@1.0.3): `agent` = the PI `Person` (who starts with PI) and/or the ORCHID agent `SoftwareApplication` (who starts with agent), `endTime` = date, `description` = decision + "Why:" reason, `object` = the `HowToStep`s of `applies_to`, `subjectOf` = a `CreativeWork` naming the source (`text` = the quote), `instrument` = the specific protocol, `actionStatus` completed; listed in the root's `mentions`. Gaps (no property in schema.org, RO-Crate 1.1 or the Process/Workflow Run Crate 0.5 profiles, so none invented): the reason has no field of its own (kept in `description`); no property links a decision to the runs it informed (reachable through `object` → `HowToStep` ← run `hadPlan`); the qualifiers of `who` ("labelled", "reported to the PI", coordinator brief) survive only in the source entity's description; no ORCID is recorded in `maintainers`, so the PI `Person` has none | prov:Activity (schema.org Action), `agent` ≈ prov:wasAssociatedWith, `object` ≈ prov:used; these PROV correspondences are documentation only: the profiles define no PROV-O terms, so no prov:wasAssociatedWith / prov:used / prov:generated / prov:wasInformedBy is emitted for decisions (closed in 1.0.3 except the gaps listed) |
| dashboard + data | `File`s `about` the artifact; the data `conformsTo` assessment-results.schema.json | prov:Entity derived from the run outputs |

## Tools (standard library only, except the figure exporter)

| tool | does |
|---|---|
| `tools/validate.py [--crosscheck PY]` | schema check of all four types; every file reference exists and its sha256 matches; step inputs produced by an earlier step; cross-document links; evidence digest; no restricted file inside `protocols/`; optional cross-check with PyYAML and `jsonschema` from an existing interpreter |
| `tools/pin_hashes.py` | fills `sha256: null`; refreshes hashes of files under `protocols/` only (a changed campaign file stays an error) |
| `tools/backfill_run_cards.py` | converts the campaigns' run records into run cards |
| `tools/extract_dashboard_data.py cuzr\|crni OUT` | builds the results document from campaign files (no recomputation) |
| `tools/build_dashboard.py DATA OUT --snapshot` | standalone HTML dashboard, ORCHID style always (brand tokens, IBM Plex embedded, no theme switch, no network) |
| `tools/fig_dashboard_panels.py DATA OUTDIR` | static paper panels in the hero style, with the ORCHID badge on figures that plot ORCHID records (runs with the fit interpreter `fit_python` of `local/config.json`, matplotlib) |
| `tools/build_crate.py SPEC OUTDIR` | Workflow Run RO-Crate + HTML and Markdown renderings |
| `tools/sync_palette.py` | syncs `tools/palette.json` from `design-system/tokens.json` of the orchid-brand repository (a sibling checkout; the brand wins) |
| `tools/build_all.sh` | everything above, in order, then validates |
| `tools/yamlmini.py`, `tools/lint_yaml.py` | the stdlib YAML subset loader and a flow-collection linter |
| `tools/orchid_reproduce.py SPEC --root NEW` | stages code and evidence by hash into a fresh root, checks the environment against the lock, runs `reproduce.plan`, compares (byte, `tdb_abs` per-symbol absolute tolerances, `json_tol`) and writes a JSON + Markdown report |
| `tools/build_evidence_bundle.py cuzr\|crni\|generic ...` | freezes the evidence bundle; classifies certainty tiers; maps ORC ids to Y25 state ids |
| `tools/evaluate_states.py TDB states.json OUT` | expected vs calculated assemblage at every observed state (pycalphad; deterministic) |
| `tools/tdb_header.py SPEC OUT.tdb` | writes the Y32 header block (orchid-brand statements.md layout); the body stays byte-identical |
| `tools/run_with_fixed_date.py --date D SCRIPT` | reruns a script that stamps today's date into its output with the recorded date (byte-identical rebuild of the Cr–Ni one-shot TDBs) |
| `tools/snapshot_code.py`, `tools/prepare_intake.py`, `tools/gradient_check.py`, `tools/check_plan.py`, `tools/check_trajectory.py` | code snapshot with manifest; ORCHID intake preparation (not delivery); gradient vs finite-difference check; plan and trajectory checks |

The YAML is written in a small subset (block mappings and sequences, flow collections on one line, quoted scalars, `|` and `>` blocks; no anchors or tags), so the tools need only the standard library. `validate.py --crosscheck` confirms that PyYAML reads every file identically.
