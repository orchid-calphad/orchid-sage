# Schema gaps found while building the ORCHID-SAGE MCP server (6 Nov 2026)

These are proposals for the owner of `protocols/schema/` (orchid-assessment-schema 1.0.0-draft) and of the protocol
tools. The server works around each gap with the fields that exist today and says where it does so. Nothing here is
in the schema yet.

| id | gap | what sage_mcp does now | proposed addition |
|---|---|---|---|
| G1 | `evaluate_states.py` writes its two path arguments into `states_evaluated.json`, so byte identity depends on the working directory and the argument form | runs it in `evaluate/` with bare file names (`X.tdb states.json`), which reproduces the bundle copy byte for byte | write basenames only; or record `cwd` and arguments in a reproduce item (G2) |
| G2 | `reproduce.plan` has no deterministic items (only the fits). `tdb_header.py` needs `--code-commit` and `--release`, which are not recorded, and reads the pick from `artifact.file.path` (a campaign path) instead of the bundle copy | adds two bindings (`evaluate_states`, `tdb_header`) built from the general steps; reads the release string from the reference header and the commit from `code[snapshot]` | add the deterministic items to each `reproduce.plan`; add `cwd` and `copy` (repo path → root path, with sha256) to the plan-item schema; let `tdb_header.py` read `assessments/<id>/evidence/artifact/` |
| G3 | `run_card.converted_from` is required (minItems 1). A native run has nothing it was converted from | puts the run log (file_ref, role "run log written by sage_mcp (native run)") there | `recorded_by: {tool, version}` as an alternative to `converted_from` |
| G4 | No field for an open decision request (a judgement step waiting for a person) | keeps requests in `sage_state.json` (`decision_requests`); a decided request becomes a `decisions[]` entry with `id` and `applies_to` | `decision_requests[]: {id, step, question, evidence: [file_ref], blocks: [step ids], status: open\|decided, decision_id}` |
| G5 | Existing specific protocols do not fill `decisions[].applies_to`, so a judgement step cannot be linked to its decision | matches by step id, the ids of feeding steps and their run ids; says when nothing matches (e.g. the Cr–Ni step-4 pick is in `run_sequence` only) | fill `applies_to` in every decision (data, not schema) |
| G6 | No changelog field for a general-protocol version | `propose_general_change` writes the changelog line into `decisions[]`, the relation into `supersedes[]` and a summary into `status_note` | `changelog[]: {version, date, who, change, bump, why}` |
| G7 | `assessment_results` requires `pick` and `steps` (minItems 1), and `extract_dashboard_data.py` knows only the `cuzr` and `crni` campaigns, so an assessment in progress has no dashboard | `package()` reports the dashboard as pending for fresh assessments | allow `pending` for `pick` and `steps`; a generic extractor from run cards |
| G8 | `overrides[]` has no structured step reference or change kind | encodes them in `parameter`: `param:<name>`, `step:<id>.skip`, `step:<id>.after`, `step:<id>.tool.command`, `data:<key>`, `binding:<placeholder>`; the general step is named in `source` | `general_step` (step id) and `kind` (parameter, threshold, skip_step, add_step, reorder_step, tool, data_selection, binding) |
| G9 | `decisions[].source` is a string; evidence files cannot be referenced with a hash | writes the evidence paths into `source` | `evidence: [file_ref]` |
| G10 | `run_ref` cannot say why a run was superseded | sets `status: superseded` and keeps the card; the reason is in `sage_state.json` | `superseded_because`, `superseded_by` |
| G11 | `artifact.file.sha256`, `evidence_selection.manifest.sha256` and `run_sequence` (minItems 1) cannot be pending, so a draft in progress never validates | reports these three as `pending_for_draft` (not errors) while `status: draft` | allow `pending` for them when `status` is `draft` |
| G12 | No field for skipping, adding or reordering a step of the general protocol in a specific protocol | overrides (G8) + the specific protocol's own `sections` (section `sage_added_steps`) | `step_sequence: [step ids]` or per-step `after` |
| G13 | `validate.py` reads only `protocols/specific/*.yaml`; there is no YAML writer (yamlmini is a loader) | writes fresh specific protocols as JSON in the run root and validates them with `orchidproto.SchemaValidator` | accept `.json` in `protocols/specific/`, or a yamlmini dumper |
| G14 | Steps have no compute record (only the protocol-level `compute.typical_wall`) | classes by environment and kind; measured wall times from `protocols/reproduce/*/run_report.json`; every fit counts as long (host-dependent: Cr–Ni step 2 took 151 s on spark1 and 378 s on the Studio) | step-level `compute: {class, estimate_s, measured: [{host, wall_s}]}` |
| G15 | Placeholders in general-step commands (`<campaign>`, `<final>`, `<start.tdb>`, `<EL>`, ...) are not declared | binds the ones it can (`campaign`, `artifact`, `EL`, `nproc`, `version`, `final`), lists the rest as `unbound`; a person binds them with a documented `binding` change | `tool.placeholders: {name: {meaning, source}}` |

## Status 6 Nov 2026: merged into orchid-assessment-schema@1.0.0-draft.2

| Gap | Outcome | Where |
|---|---|---|
| G1 | **merged (tool)**: `evaluate_states.py` writes basenames + sha256 only; output byte-identical across working directories | protocols/tools/evaluate_states.py |
| G2 | **merged**: plan items `cwd`, `copy` ({repo path: {to, sha256}}, hash-checked), `expected`; deterministic items `evaluate_states`, `tdb_header` (with the `--release` value) in both specific protocols; `tdb_header.py` reads the pick from `evidence/artifact/` (or `--pick`). sage_mcp now uses the protocol's own items when declared | protocol.schema.json `reproduce.plan.items`; specific protocols; reproduce.py |
| G3 | **merged**: `run_card.recorded_by: {tool, version}` as an alternative to `converted_from` (anyOf) | protocol.schema.json run_card |
| G4 | **merged**: `decision_requests[]` | common_fields |
| G5 | **merged (data)**: every decision in both specific protocols has `applies_to`; the step-4 (Cr–Ni) and H2 (Cu–Zr) picks are decisions now | specific protocols |
| G6 | **merged**: `changelog[]` | common_fields |
| G7 | **partly merged**: `pick` and `steps` may be `pending`. **Rejected for now**: a generic run-card extractor — it is a tool, not a schema change, and needs run cards of a fresh assessment to test against; left to the MCP's `package()` | assessment-results.schema.json |
| G8 | **merged**: `overrides[].general_step`, `overrides[].kind` | specific_protocol.overrides |
| G9 | **merged**: `decisions[].evidence: [file_ref]` | common.schema.json decision |
| G10 | **merged**: `run_ref.superseded_because`, `superseded_by` | run_ref |
| G11 | **partly merged**: `run_sequence` minItems 1 applies only when `status` is not draft. **Rejected**: an anyOf(file_ref, pending_file) for `artifact.file` / `evidence_selection.manifest` — it replaces the precise "sha256: expected string" error that sage_mcp's `pending_for_draft` handling keys on with an opaque "matches none of anyOf", which broke the fresh-assessment tests; the null-hash-in-draft reporting stays validator-side. `pending_file` is defined in common.schema.json for later use | protocol.schema.json |
| G12 | **merged**: `specific_protocol.step_sequence` | specific_protocol |
| G13 | **merged**: validate.py reads `protocols/specific/*.json` | protocols/tools/validate.py |
| G14 | **merged**: step-level and plan-item `compute: {class, estimate_s, measured: [{host, wall_s, source}]}` | common.schema.json compute |
| G15 | **merged**: `tool.placeholders: {name: {meaning, source}}` | protocol.schema.json tool |

Also new in draft.2 (PI 6 Nov):
- `exclusion_entry` (a tier for each excluded phase) and `zpf_certainty` on states_evaluated rows. These replace the row-level `certainty_tier`.
- ORCHID linkage (`orchid_link`, `orchid_links`, `orchid_release`, `missing_reason`, `intake_ref`). A missing link must carry its reason and an intake reference.
- Compare rules `json_equal`, `files_equal` and `sequence_equal`.
- `reference_value` may be a string, a boolean or null.
- draft.1 documents still validate: `schema_version` accepts both values.
