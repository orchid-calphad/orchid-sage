# Reproducing a pick with the ORCHID-SAGE MCP server

This is a pointer for `protocols/REPRODUCE.md`. The command `orchid_reproduce.py` described there runs a whole
`reproduce.plan` at once. The MCP server (`sage_mcp/`) exposes the same procedure to an AI agent one step at a time:
stage by hash, run one item, compare. It wraps `orchid_reproduce.py` (`--stage-only`, `--compare-only --only`),
`validate.py`, `evaluate_states.py` and `tdb_header.py` through their command lines and does not change them.

## The cold-start prompt

This is the exact prompt given to an agent that has only the MCP server connected. It is also the server prompt
`reproduce_assessment` with these two arguments.

> You are reproducing the ORCHID-SAGE assessment crni-paper-fit-step4-s1@0.1.0-draft. You have only the orchid-sage
> MCP tools. Do not guess: every command, path, tolerance and decision comes from a tool result. Never run a step the
> tools refuse.
> 1. Read: get_protocol, then get_steps. Note the reproduce items and the judgement steps.
> 2. Validate: validate("crni-paper-fit-step4-s1@0.1.0-draft"). Report every error.
> 3. Verify inputs: verify_inputs(...). The rerun needs only `bundle_manifests` to be ok (`rerun_ready: true`).
> 4. Plan: plan_reproduction(..., run_root=<a NEW directory outside the repository, the campaign directories and the restricted material>).
> 5. Run the deterministic items, one call each, in plan order: stage, environment_check, then every other
>    deterministic item. Numerical items (the fits) need allow_long=true; run them only if asked to.
> 6. Judgement steps are never executed: get_step returns the recorded decision and its source.
> 7. Compare: compare_outputs(...).
> 8. Report items run, PASS/FAIL per check, what was not run and why, the report path, and every choice the tools did
>    not settle.

## Dry run (6 Nov 2026, Studio, stdio fallback server, no other knowledge)

| item | kind | result |
|---|---|---|
| stage | deterministic | 90 files staged from the code and evidence manifests, every sha256 checked |
| environment_check | deterministic | `0.8.11.dev82+g9039ea215 0.11.3.dev35+g9a6939dd2`: PASS |
| evaluate_states | deterministic | `states_evaluated.json` byte-identical (sha256 `09b27871…`), 5 s |
| tdb_header | deterministic | released TDB byte-identical (sha256 `c06b3405…`) |
| step4 | numerical | refused without `allow_long` (as designed) |
| step2 | numerical, run separately with allow_long | multistart logpost identical (difference 0.0), pick TDB byte-identical; 378 s on the Studio |

`compare_outputs` writes `<run_root>/comparison/comparison.json` and `.md`. Its `pass` covers the compared checks only.
The items listed in `not_run` were not reproduced.

## Points where an agent still has to be told something (status 6 Nov, after the PI decisions)

1. **Closed.** Both specific protocols declare their deterministic items in `reproduce.plan`: `evaluate_states` and
   `tdb_header`, with `cwd`, `copy` (repo path → root path, sha256-checked) and `expected`. The server uses the protocol's
   items and adds its own bindings only for a protocol that lacks them.
2. **Closed.** `tdb_header.py` reads the pick from the bundle copy (`evidence/artifact/`, or `--pick`). The `--release`
   value is written in the plan item (`unreleased (ORCHID next; v2027.01 intake prepared)`). The release header cites
   evidence bundle 2.0.0.
3. Open: on a host without a configured fit interpreter (`fit_python` in `local/config.json`), `python=` must be given.
4. **Closed.** The PhaseForge+ source is hash-checked against `protocols/environment/pins/spark1_phaseforgeplus_files.sha256`
   (in git). The server checks it before any item whose command or env uses `{PFP}`; `orchid_reproduce.py` checks it
   before a run (report field `phaseforgeplus`). The Studio source matches. Since 6 Nov (crni-paper-fit-step4c-b@1.0.1) a
   protocol may name its own pin list (code entry `phaseforgeplus`, file id `source_pin`; source files only), and a mismatch is a
   note, never a refusal or a failure (PI: "this is too strict"); the verdict comes from the predictions.
5. **Closed.** `acceptance_target` uses absolute per-parameter tolerances (fit_protocol 10b), the same as the plan.
6. **Closed.** Expected results are explicit (`expected: {result: pass|fail|partial, reason, source}`):
   - Cr–Ni step3b is `partial` (Q36), and `pick_rule_step3b` expects no eligible start under 10a.
   - Cu–Zr h1_s1 and h2_s7 are `partial` (Q37).
   - `orchid_reproduce.py` reports an expected failure as `FAIL (expected)` and lists it separately.
7. **Closed.** Every decision has `applies_to`, and the Cr–Ni step-4 and Cu–Zr H2 picks are decisions.
8. **Closed (7 Nov).** Long items no longer depend on one tool call staying open. `run_step` starts a long reproduce item
   (`needs_allow_long`) detached and returns at once (`start_step` does the same explicitly); `step_status(protocol, run_root,
   step_id, wait_s)` reports progress, blocks at most 900 s per call (server cap `SAGE_MCP_MAX_WAIT_S`), and, when the item
   has ended, writes the run card exactly as a synchronous run does (plus the existing `pids` field). The job keeps running
   if the session ends; its state is in `<run_root>/jobs/`. Fresh-assessment steps still run synchronously.
9. **Closed.** New plan items:
   - `phase_sequence`: phase order on heating at every x of a 0.01 grid, transitions within 10 K, using the campaign
     evaluators (tool `protocols/tools/phase_sequence.py`);
   - `pure_elements`;
   - `laplace_weights` (Cr–Ni; main-mode weight 0.901 within 0.01).
10. New: `get_evidence_links(assessment)` returns each evidence state's ORCHID links, or the reason and intake reference
    when it has none. `get_evidence_manifest` reads the newest bundle version and returns `orchid_link` with each file.

See `sage_mcp/README.md` for installation and the safety model.
