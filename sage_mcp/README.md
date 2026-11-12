# orchid-sage-mcp

An [MCP](https://modelcontextprotocol.io) server for **ORCHID-SAGE** (Systematic Assessment of Gibbs Energies). Its
CALPHAD protocols are machine-*executable*: an agent with no prior context can read a specific protocol, stage its
inputs by hash, run it one step at a time, and compare the result with the published TDB and its outputs. It can also
start a fresh assessment from the general protocol. Every departure from the protocol is a documented, versioned
change.

The server uses only the standard library. If the official `mcp` SDK is installed, the server runs on it (`MCPServer`
in mcp 2.x, `FastMCP` in 1.x). Otherwise it serves the MCP stdio protocol (tools, resources, prompts) with a small
built-in JSON-RPC loop. This is the same design as `orchid-mcp`. It reads the repository it sits in (`protocols/`,
`assessments/`) and never edits it.

## Install and run

```bash
cd orchid-sage                         # the checkout
python3 -m sage_mcp                    # stdio; Python >= 3.11, no installation needed
python3 -m sage_mcp --fallback         # force the built-in server even if `mcp` is installed
pip install -e .                       # optional: console script `orchid-sage-mcp` (editable install, so the repo is found)
```

A non-editable install must be told where the checkout is: `SAGE_REPO=<path to the checkout>`.

Machine-specific locations are never written in the code. Each comes from an environment variable or from the local
config `local/config.json` in the checkout (gitignored; copy `local.example/config.json`), and otherwise from a default
inside the checkout, so a clean clone works without one (`protocols/tools/localpaths.py`).

| variable | config key | default | meaning |
|---|---|---|---|
| `SAGE_REPO` | — | the directory above `sage_mcp/` | the orchid-sage checkout (must contain `protocols/tools/`) |
| `SAGE_MCP_STATE_DIR` | `state_dir` | `local/state` | registry of fresh assessments; proposed general-protocol versions (`general/`) |
| `SAGE_MCP_BACKENDS` | `backends_file` | `local/backends.json` | executor backends (remote ones disabled by default) |
| `SAGE_MCP_LONG_S` | — | `600` | items estimated above this many seconds need `allow_long=true` (fits always do) |
| `SAGE_MCP_FORBIDDEN` | `protected_paths` | — | extra directories (`:`-separated) where a run root may never be |
| `ORCHID_RUNS_ROOT`, `ORCHID_RESTRICTED_DIR` | `runs_root`, `restricted_dir` | `data/runs`, `data/private` | campaign directories and restricted material (never a run root) |
| `ORCHID_DATA_DIR` | `orchid_data_dir` | `data/orchid-data` | local ORCHID data for `gather_evidence` (never fetched online) |
| `ORCHID_MCP_SRC`, `ORCHID_SITE_DATA_DIR` | `orchid_mcp_src`, `site_data_dir` | not set | optional ORCHID context (invariant records, calculated assessments) via orchid-mcp, offline |
| `ORCHID_FIT_PYTHON`, `PHASEFORGEPLUS_SRC` | `fit_python`, `phaseforgeplus_src` | the running interpreter; not set | the fit interpreter and the PhaseForgePlus source for reproduce items |

### Claude Code

```bash
claude mcp add --scope user orchid-sage -e PYTHONPATH=<checkout> -- python3 -m sage_mcp
# with the mcp SDK (orchid-mcp's venv has mcp 2.3.0):
claude mcp add --scope user orchid-sage -e PYTHONPATH=<checkout> -- <venv with mcp>/bin/python -m sage_mcp
```

`python -m sage_mcp` needs the checkout on `sys.path` (`PYTHONPATH`); the server finds the repository from its own location.

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "orchid-sage": {
      "command": "/usr/bin/python3",
      "args": ["-m", "sage_mcp"],
      "env": {"PYTHONPATH": "<absolute path of the checkout>", "SAGE_REPO": "<absolute path of the checkout>"}
    }
  }
}
```

## Tools

**Read**

| tool | returns |
|---|---|
| `list_protocols()` | general, specific, proposed general versions, fresh assessments |
| `get_protocol(protocol, fields)` | summary (sections, inputs, run sequence, reproduce plan) or the full document |
| `get_steps(protocol, section?)` | steps with kind, exact command, environment, compute class; reproduce items |
| `get_step(protocol, step_id)` | one step or reproduce item. Gives the exact command, inputs, outputs with checks, kind, decision rule, tolerances and unbound placeholders. For a judgement step, also the recorded decision and its source |
| `get_run_cards(protocol)` | run sequence with each card (host, interpreter, seeds, threads, packages, trajectory) and its hash check |
| `get_decisions(protocol)` | decisions log, overrides, and (fresh) decision requests |
| `get_evidence_manifest(assessment, kind?, limit, offset)` | bundle counts, tiers, bundle sha256 (recomputed), files (paged) with hash check |
| `get_dashboard_data(assessment, section?, max_items)` | section list, or one section of the dashboard data |
| `get_open_questions(ids?)` | `protocols/OPEN_QUESTIONS.md` parsed |

**Check**

| tool | returns |
|---|---|
| `validate(document?)` | `validate.py --quiet`, filtered to one document; a fresh assessment is checked against the schema directly |
| `verify_inputs(protocol, detail)` | sha256 of every referenced file present (ok, mismatch, missing, restricted present/missing, remote) and of every file of the bundle manifests (`rerun_ready`) |
| `compute_ids(pid?, locator?, state?, observation_key?, orcid?, dataset_uuid?, new_namespace, check_id?)` | ORCHID ids offline (`orchid_ids`, [docs/ID_SCHEME.md](../docs/ID_SCHEME.md)): ORC- from a locator (DOI, dataset DOI or the provisional `local:<ORCID>/<dataset-uuid>` namespace), C-/S- from a state (phase registry of `ORCHID_DATA_DIR`), a new provisional namespace, or a recompute check; says what keeps an id provisional |

**Execute (reproduce mode)**

| tool | does |
|---|---|
| `plan_reproduction(protocol, run_root?, python?, pfp?, nproc)` | ordered items with bound commands, expected outputs, kind, compute class, measured estimates and tolerances, plus the recorded decisions of the judgement steps. Runs nothing |
| `run_step(protocol, step_id, run_root, confirm, allow_long, python, pfp, nproc, backend, detach?)` | runs ONE item (`stage` first). A short item runs synchronously, writes a run card and returns the log tail. A long item (`needs_allow_long`) starts detached by default and returns at once with status `running` |
| `start_step(protocol, step_id, run_root, confirm, allow_long, python, pfp, nproc)` | starts ONE item detached (same checks and refusals) and returns its handle: pids, job file, log |
| `step_status(protocol, run_root, step_id?, wait_s)` | running (elapsed, log tail), finished, lost or not started. `wait_s` blocks while the item runs, at most `SAGE_MCP_MAX_WAIT_S` (900 s). When the item has finished, writes its run card once, as a synchronous run would, and returns that result. Without `step_id`: every job of the run root |
| `compare_outputs(protocol, run_root)` | byte identity for deterministic items; `tdb_abs` / `json_tol` via `orchid_reproduce.py --compare-only`; writes `comparison/comparison.{json,md}` |

Reproduce items: `stage` (`orchid_reproduce.py --stage-only`), `environment_check` (from the specific protocol), the
bindings `evaluate_states` and `tdb_header` (deterministic; see SCHEMA_GAPS G1–G2), and then `reproduce.plan` (the fits).

**Fresh assessments and documented changes**

| tool | does |
|---|---|
| `new_assessment(system, assessment_id, run_root, phases?, T_range?, general?)` | specific protocol draft 0.1.0 in a fresh run root. Opens a decision request for every required decision and writes the PLAN.md draft |
| `gather_evidence(assessment, evidence_classes?)` | evidence bundle from local ORCHID data (format of `build_evidence_bundle.py`): states with certainty tiers, excluded phases at every observed state. Without a decided phase set it returns a preview only. Gaps are returned, never filled |
| `next_step(assessment)` | the next step with its mode (internal, command, judgement, job_spec), bound command, compute class and blockers, plus the whole sequence |
| `run_step(assessment, step_id, run_root, ...)` | as above. A judgement step produces a decision request; a GPU step produces a job spec |
| `record_decision(assessment, request_id, decision, who, why, bindings?)` | a person's answer. Unblocks the dependent steps |
| `record_external_run(assessment, step_id, run_card)` | a step that ran elsewhere (e.g. a GPU job), recorded from its schema-valid run card |
| `modify_protocol(assessment, change, who, why, evidence?)` | documented change: an override with `conforms: false` plus a decision. Bumps the version, is validated before it is accepted, and marks affected steps stale |
| `propose_general_change(change, who, why, bump?, base?)` | a NEW general-protocol version (semver by change type) with a changelog entry. Never edits a version in place |
| `migrate(assessment, to_version, who, why)` | moves an assessment to another general version as a recorded decision; changed steps go stale |
| `get_history(assessment)` | versions, overrides, decisions, requests, stale and re-run steps, events |
| `package(assessment)` | pins the final TDB and builds the RO-Crate; otherwise reports what is missing |
| `list_backends()` | local backend and configured remote ones |

**Resources:** `sage://protocol/<id>@<version>.yaml|.md`, `sage://run-card/<id>`, `sage://schema/<file>`,
`sage://dashboard/<artifact>/data`, `sage://evidence/<artifact>/manifest`, `sage://code/<artifact>/manifest`,
`sage://docs/{SCHEMA,REPRODUCE,OPEN_QUESTIONS}.md`, `sage://mcp/*.md`.

**Prompts:** `reproduce_assessment(protocol, run_root)`, `explain_assessment(protocol)`,
`run_fresh_assessment(system, assessment_id, run_root)`.

## Safety model

- **Run roots.** A run root must be absolute, fresh (absent or empty) when it is created, and marked by the server with
  `.sage_run_root.json`. It is refused if it lies inside, or contains, any of these: the orchid-sage repository,
  the campaign directories (`runs_root`), the restricted material (`restricted_dir`), the ORCHID data checkouts, the
  PhaseForgePlus checkout, the home directory itself, or anything in `protected_paths` or `SAGE_MCP_FORBIDDEN`. Steps run only in a marked root, and only in the root staged for that protocol.
- **Commands.** The working directory is the run root. Before a command runs, it is statically checked. A command is
  refused if it writes outside the root (`>`, `cp/mv/tee/ln` targets, `--out/--report/-o/--root`), changes directory
  out of it, contains `rm`, or calls `sudo/ssh/scp/rsync/curl/wget/docker/git push`. This is a check plus working-directory
  confinement, not an OS sandbox. The scripts the protocol runs are trusted because they are pinned by hash.
- **One step per call.** `confirm=true` is required. Long steps need `allow_long=true`: every fit, and anything estimated
  above `SAGE_MCP_LONG_S` or without an estimate. GPU steps never run: the server writes a job spec. Judgement steps never
  run: the server returns the recorded decision (reproduce mode) or opens a decision request (fresh mode), and only
  `record_decision` with a named `who` and a `why` answers it. `who` cannot be the server.
- **Backends.** `local` runs CPU commands. A remote backend (e.g. a DGX Spark) is used only if a person adds it to
  `backends.json` with `"enabled": true` and names it in `run_step(..., backend=...)`:

  ```json
  {"gpu1": {"kind": "ssh", "host": "<ssh host alias>", "workdir": "sage-runs", "gpu": true, "enabled": true}}
  ```

  Even then, this version only writes the job spec and returns a submission hint for the person to run. The server never
  connects to the host.
- **Restricted material.** Restricted files (`restricted_dir`, publisher PDFs) are hashed when present. They are never
  read out, copied or staged. Evidence bundles hold derived facts only, and files with a source-text field longer than
  500 characters are held back (the rule of `build_evidence_bundle.py`).
- **No network, no deletion.** No tool goes online. `orchid-mcp` is used offline from local directories only. No tool
  deletes a file. A superseded run card or evidence bundle is kept, and a rebuild writes a new directory (`evidence_v2`).

## Fresh-assessment flow (design note)

1. `new_assessment` copies the general protocol's inputs, code, environment and tolerances into a draft specific
   protocol (JSON, in `<run_root>/protocol/`). It opens decision requests for established practice (the judgement step
   `read_established_practice`), the phase set, the T range and the unaries source. It writes the PLAN.md draft from
   `protocols/templates/PLAN.template.md`.
2. `gather_evidence` reads `espei/<class>/<SYSTEM>/` of the local ORCHID data (experimental and invariants by
   default; `assessed` only through a documented data-selection change). It copies files byte for byte and groups them
   liq/thermo/solid by content. States come from `build_evidence_bundle.states_from_zpf`, and certainty tiers from its
   `classify` (10/50/100 J/mol-atom). Exclusions go at every observed state: the declared phases minus the measured
   assemblage, at confidence 1.0, with sigma equal to the tier energy (fit_protocol item 8, in the espei/SCHEMA.md
   sidecar keys). Until the phase set is decided it only previews the data, which then serves as evidence for that
   decision. What it cannot do is listed as a gap: the partial tie-line split, weights from sigma, the data consistency
   check (all system-specific `build_data.py` today), Y25 state ids, and observed phases outside the declared set.
3. `next_step` walks the general protocol's sections in order, applying documented skips, additions, reorders and tool
   changes. A step is ready when every step feeding it (`supply`) is done or skipped and no open request blocks it. The
   modes are: `internal` (server code: PLAN, evidence), `command` (bound command, refused while placeholders are unbound
   or campaign scripts are missing from the run root), `judgement` (decision request) and `job_spec` (GPU: the one-shot
   relaxations and the liquid MD).
4. Every executed step writes a schema-valid run card (host, interpreter, packages, command, seeds, inputs and outputs
   by sha256, trajectory record or `not_recorded`) and a `run_sequence` entry in the current protocol version.
5. Changes: `modify_protocol` writes the next version (minor bump). The override has `conforms: false` and names the
   general step; the decision records who, when, why and the evidence. Every step whose inputs the change affects, and
   everything downstream of it, goes stale: its run cards move to `superseded_run_cards` (the files are kept) and its
   `run_sequence` entries become `superseded`. Frozen parameters (fit_protocol 0.0a) change only when `who` is the PI.
   `propose_general_change` writes a new general version under the state directory, never in `protocols/general`.
   Assessments move to it only through `migrate`.
6. Limits of this version: the fit steps of the general protocol are campaign scripts (general protocol limitation 1),
   so on a fresh system they are "not executable" until a person copies and adapts the reference code into the run root
   and records it as a `tool` change. There is no dashboard for a fresh assessment (SCHEMA_GAPS G7). Long reproduce items
   run detached (`start_step` / `step_status`, state in `<run_root>/jobs/`); long fresh-assessment steps are still
   synchronous calls.

## Tests

```bash
python3 -m unittest discover -s sage_mcp/tests -t .                                   # stdio fallback
<venv with mcp>/bin/python -m unittest discover -s sage_mcp/tests -t .                # also the SDK server
```

The tests use local data only, and a socket guard fails any network access. The deterministic rerun test (stage, environment
check, `evaluate_states`, `tdb_header`, compare) runs when the fit interpreter (`fit_python`) is configured; it takes about 10 s. No test
runs a fit, a GPU step or a remote job.

## Licence

The code is MIT; protocols, schema, docs and data are CC BY 4.0 (see `LICENSES.md`).
