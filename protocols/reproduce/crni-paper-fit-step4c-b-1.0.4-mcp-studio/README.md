# crni-paper-fit-step4c-b@1.0.4 (final, approved): the AI-agent rerun through the ORCHID-SAGE MCP server, the record fixes, and the GPU spot check (7 Nov 2026)

**Rerun verdict: PASS** (13 of 13 checks, by predictions). This is the one more rerun the PI allowed ("we will only run one more").
**GPU spot check: SQS cell PASS; liquid MD enthalpy FAILS its declared tolerance** (diagnosis below; reported to the PI, no rerun).

## Machine

The rerun ran on the **Studio (mac-studio), the machine of the original fit**, not on spark1. sage_mcp executes reproduce
items on its local backend only (`reproduce.run_step` refuses any other backend; a configured remote backend only receives job
specs for GPU steps of fresh assessments) and the Claude CLI that drives the session is not installed on spark1, so spark1 was not
enabled (decision row of 7 Nov in the spec). Machine independence of the same science rests on the scripted spark1 reruns of
1.0.0-1.0.3 (`../crni-paper-fit-step4c-b-1.0.3-spark1/` and earlier).

## How it was run

- `claude -p "$(cat PROMPT.txt)" --strict-mcp-config --mcp-config mcp-only.json --allowedTools mcp__orchid-sage --output-format stream-json --verbose`
  (no `--bare`), from the fresh directory `<home>/mcp-rerun-crni-1.0.4-20261107/` (run root `run/`, PhaseForge+ `pfp-c66656f/src` = `git archive`
  of c66656f, 10 of 10 pinned source files match), interpreter `<fit-python>`, nproc 4, repo at 2beaaf1.
- Session PID **43970**; 21:09:15-23:47 UTC (2 h 38 min; 9480 s); **46 turns; USD 1.64** (claude-opus-5-5). Items ran under the
  sage_mcp job wrapper started by the MCP server (wrapper PIDs in `rerun/jobs/*.started.json`); all ended (return code 0).
- Tool use (`session/session_summary.json`): 31 MCP calls (run_step 10, step_status 14, get_protocol, get_steps, validate,
  verify_inputs, plan_reproduction, compare_outputs). **Not MCP-only in the strict sense:** the session also used the read-only
  built-ins ToolSearch (1), Read (11: the saved plan output and the 10 run cards in the run root) and Bash (3 attempts to inspect the
  saved plan file: 2 refused by the permission check, 1 ran `jq`, which is not installed, and failed). `--allowedTools` adds
  permissions but does not remove read-only built-ins; no write, process or network tool ran. A stricter session needs `--tools ""`.

## Result (`comparison.json`, `plan_compare.json`; reference = the recorded Studio pick s4, mode A)

| item | quantity | reference | rerun (Studio, MCP) | tolerance | result |
|---|---|---|---|---|---|
| verify_inputs | 6 bundle manifests (code 0.2.0, addenda 1.0.0/1.0.1/1.0.3/1.0.4, evidence 1.2.0) | 446 files | 0 mismatch, 0 missing; rerun_ready | byte | ok |
| step4c_b | multistart (fit3/model3) | recorded multistart (6 Nov) | θ, logpost and nfev **bit-identical at 8 of 8 starts**; 1934 s | – | ran |
| check10a | re-evaluation vs multistart; zpf_susp records | – | check_ok true; 12 in every worker; 1226 s | 1e-6 (fails the check) | ok |
| check10a | objective of the 10a pick (by rule: s4_perturbed, gap 1.9e-9) | −5657.288636859774 | −5657.288636859774 | 0.01 | PASS |
| check10a | pick eligible | true | true (smooth) | – | PASS |
| check10a | eutectic / CrNi2 top | 1614 K / 860 K | 1614 K / 860 K | 2 K | PASS / PASS |
| global_10c | basin hopping / dual annealing best (seed 7201, 1500 evaluations each) | −5657.288636859766 / −5657.288636859768 | −5657.288636859772 / −5657.288636859772 | 0.01 | PASS / PASS |
| evaluate_states | `states_evaluated@1.2.0.json` | cf2c9879… | cf2c9879… | byte | PASS |
| phase_sequence | phase order on heating, 0.01 grid, 600-2200 K | reference pick | identical | 10 K | PASS |
| pure_elements | unary.ok; Cr, Ni stable below T_m | true; BCC_A2; FCC_A1 | true; BCC_A2; FCC_A1 | exact | PASS ×3 |
| thermochemistry | 22 data/thermo datasets, rms residual/σ | recorded per-dataset | 22 of 22, max \|Δ rms_z\| 0.0 | 0.1 | PASS |
| laplace_weights | main-mode weight (modes_step4c_b@1.1.0.json: A_s4_perturbed, B_s5_perturbed) | 0.7660570156 | 0.7660570156 | 0.01 | PASS |

Notes (never failures): the 10a pick is s4_perturbed, mode A_s4_perturbed, the recorded labels; parameters: the 5 determined
symbols within 10b, VV0004-VV0011 and VV0013 undetermined; P(accepted topology) 0.989 (recorded 0.989; not a compare_outputs
check); environment check passed. The agent noted that no tool reported the PhaseForge+ pin check (the operator verified it before
launch: 10 of 10) and that the stage ran under the MCP server's interpreter.

## Record fixes of 1.0.4 and the proof that the fit inputs are unchanged (`../crni-paper-fit-step4c-b-1.0.4-records/`)

- `hinge_relabel_proof.json`: `step4c_hinge_floor@1.1.0.json` vs the file the fit reads: the projection the objective reads
  (cells T, x, expected, sigma, tie_line, confidence, penalize; element; margin) serialises to identical bytes (sha256 a27a2da8…
  both), all 3305 numbers/booleans/nulls identical (878 sigma values), and the files are equal once the label keys are removed.
- `home_path_proof.json`: five <home>/ versions; only path strings change; every JSON number identical.
- `modes_record_proof.json`: the 2.1.2 modes command, run verbatim on the recorded multistart, gives the recorded modes (theta
  bit-identical in order) under the names A_s4_perturbed / B_s5_perturbed.
- `objective_identity_stage104.json`: the objective of the 1.0.4 staged root (bundle 1.2.0, addendum-1.0.4, oneshot_parameters
  from its <home>/ version) is **bit-identical** on the Studio to the 1.0.3 fix proof (value, gradient, value_only, every part, as
  float.hex) at 8 of 8 endpoints; 12 zpf_susp records.
- The MCP rerun itself reproduced the original Studio multistart bit for bit (above).

## GPU spot check (`../crni-mlip-spotcheck-20261107-spark3/`, run card `run_cards/crni-mlip-spotcheck-20261107-spark3.json`)

PI approval of 7 Nov ("a small GPU spot check of the MLIP steps"); not a protocol rerun. **spark3** (GPU idle at launch; the
original host spark1 and spark4 not used), container `cuzr-phaseforge-grace-gpu:20261104` (image sha256:8eae0b91…; spark1 used ac223e2c…),
GRACE-2L-SMAX-OMAT-large (7 of 7 weight files match `provenance/potential_sha256.txt`), protocol code `relax_solids.py` (b763dbf8…) and
`run_liquid.py` (a4b6d40c…) launched as in `code/launch_liquid.sh`. Container PIDs 2761332 (solids, 40 s) and 2761574 (liquid,
20:49-21:43 UTC, 3217 s).

| item | quantity | spark1 (recorded) | spark3 | difference | tolerance | result |
|---|---|---|---|---|---|---|
| bcc SQS x_Ni 0.25, s2026110501 | E s0 unrelaxed (eV/atom) | −8.39159041 | −8.39159086 | −0.000043 kJ/mol-atom | 0.1 | PASS |
| | E s1 volume | −8.39162304 | −8.39162304 | +0.000000 | 0.1 | PASS |
| | E s2 volume + ions (protocol value) | −8.41078296 | −8.41078293 | +0.000003 | 0.1 | PASS |
| | E s3 full | −8.41092097 | −8.41092103 | −0.000006 | 0.1 | PASS |
| liquid Cr50Ni50, 108 atoms, 2200 K, 100 ps, seed 2026110503 | H = ⟨U+K⟩ + ⟨p⟩V (eV/atom) | −6.61923 ± 0.00523 | −6.68807 ± 0.00445 | **−6.64 kJ/mol-atom (z −10.0)** | 1.33 (2 × combined block SE) | **FAIL** |

Diagnosis (added after the comparison; the verdict stands): ⟨U+K⟩ differs by only +0.51 kJ/mol-atom (z +2.9). Almost all of the
difference is the ⟨p⟩V term (−7.15 kJ/mol-atom): the NVT production volume is the mean NPT volume of the last 5 ps of the density
stage, which came out 0.096 Å³/atom larger on spark3 (12.900 vs 12.804), so ⟨p⟩ is −0.78 GPa there and +0.14 GPa on spark1. The block
standard error of the production run does not contain this volume uncertainty, so the declared tolerance is too narrow for the
recorded enthalpy estimator. The liquid H_mix entering the fit carries the same estimator in every state. **This is a science
question for the PI** (whether to evaluate H at the 1 atm volume or widen the stated uncertainty); nothing was rerun or changed.

## Crate

`protocols/crates/crni-paper-fit-step4c-b-1.0.4/` (`tools/build_crate.py ... --addenda --decisions --pinned-evidence --substitutes
--reproduce-tree`). It holds this directory, the records, the spot check and its run card.
