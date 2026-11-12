# Brief for the rerun agents (from 6 Nov 2026, relayed by the coordinator)

From now on, every run you launch (MLIP container, fit step, evaluation, Laplace) has to leave a run card that `python3 protocols/tools/validate.py` (from the orchid-sage checkout) accepts.

## What each run card needs

Write `steps/<step>/run_card.json` (one per step; per start inside `results`) with these fields:
- **Identity:** `"type": "run_card"`, `"schema_version": "orchid-assessment-schema@1.0.0-draft"`, `run_id`.
- **What it executes:** `executes {specific_protocol, general_protocol: "orchid-calphad-fit@2.0.0", step}`, where `step` is a step id of `general/orchid-calphad-fit@2.0.0.yaml`.
- **Where and how it ran:**
  - `host`, `hardware_class`, `pids`, `started`, `finished`;
  - `interpreter` (the path), `packages` with `espei.__version__` and `pycalphad.__version__` printed from that interpreter;
  - the exact `command`;
  - `threads` (for example `OMP_NUM_THREADS=1`, number of worker processes).
- **Seeds:** the rule and the per-start values.
- **Inputs and outputs:** every input and output as `{path, sha256, storage_class}`. Restricted files (the restricted-material directory, `restricted_dir` in `local/config.json`; PDFs) appear by hash only.
- **Results:** per start, the objective, its components, termination, number of evaluations and wall time.
- **Trajectory:** a reference to `steps/<step>/<start>/trajectory.jsonl`.

## What else to record

- **Trajectory file:** one JSON line per evaluation, holding the evaluation index, wall time, stage, objective, components (split thermochemistry / one-shot anchors / S_ex / ZPF / hinge / prior wherever the objective allows), the full parameter vector with names, and the topology class every N evaluations and at the end.
- **MLIP containers:** add the image id (`docker image inspect --format '{{.Id}}'`; spark1's cuzr-phaseforge-grace-gpu:20261104 is `sha256:ac223e2cfa3e…`) and the sha256 of the model files.
- **Code:** copy every script you run into `<run>/code_used/` at launch and record its sha256 in the card. Never edit a script in place after a run has used it: write a new file or version, because the 06:55 in-place edit of Cr–Ni `fit.py` and `model.py` lost the code of the step-4 pick.

## Certainty tiers (fit_protocol item 8, PI 6 Nov)

- **Classify first.** Before fitting, run `<fit_python> -I protocols/tools/build_evidence_bundle.py generic --art <name> --element <EL> --run-card <a run card or campaign run_card.json listing the data files> --hinge <hinge.json> --registry <Y25 observations.parquet>` and put the tier of every ZPF row and exclusion into the objective. ESPEI's 1000 J/mol ZPF default is no longer used.
- **Tiers:**
  - certain: 10 J/mol-atom;
  - less certain: 50 J/mol-atom;
  - uncertain: 100 J/mol-atom (on a boundary, assumed from a diagram, or with conflicting sources).
- **The 3× rule.** "Certain" means the state lies more than 3× its own T/x uncertainty from the nearest observed boundary, and no source contradicts it. This 3× threshold is the coordinator's reading and still needs the PI's confirmation, so label it as such.
- **Observed states** enter at confidence 1.0.
- **In the run card:** record the counts per tier and the sha256 of `states.json`.

## When the run ends

Hand the coordinator the paths of the run cards and the trajectory files. The specific protocol is then versioned from them with `tools/backfill_run_cards.py` and `tools/pin_hashes.py`.
