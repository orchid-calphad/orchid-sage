# Cold-start brief: MCP-agent rerun of crni-paper-fit-step4c-b@1.0.1 (prepared 6 Nov 2026; not launched)

The PI launches this rerun. It follows `protocols/BRIEF_rerun_agents.md` (run cards, trajectories, no in-place edits) and the
cold-start prompt of `sage_mcp/REPRODUCE_WITH_MCP.md`, updated for version 1.0.1 of the Cr–Ni specific protocol. Version 1.0.1 has
the same science as 1.0.0 (same data, objective, starts, seeds, settings and artifact). It fixes only the plan defects that the
scripted 1.0.0 rerun on spark1 found:

- the 10a and 10c items no longer depend on a start label;
- `pure_elements` reads a staged input;
- the PhaseForge+ pin covers source files only;
- the general protocol is `orchid-calphad-fit@2.1.0`.

The brief for 1.0.0 (`BRIEF_rerun_mcp_crni-paper-fit-step4c-b@1.0.0.md`) is kept unchanged.

## The prompt (give it verbatim to an agent that has only the orchid-sage MCP server connected)

> You are reproducing the ORCHID-SAGE assessment crni-paper-fit-step4c-b@1.0.1. You have only the orchid-sage MCP tools. Do not
> guess: every command, path, tolerance and decision comes from a tool result. Never run a step the tools refuse. LOCAL work only:
> no remote or cloud agents, no `rm` (move aside), stop only processes you started, by exact PID; never touch other jobs on the host.
> 1. Read: get_protocol("crni-paper-fit-step4c-b@1.0.1"), then get_steps. Note the reproduce items (step4c_b, check10a, global_10c,
>    evaluate_states, phase_sequence, pure_elements, thermochemistry, laplace_weights) and the judgement steps.
> 2. Validate: validate("crni-paper-fit-step4c-b@1.0.1"). Report every error.
> 3. Verify inputs: verify_inputs(...). The rerun needs only `bundle_manifests` to be ok (`rerun_ready: true`); the four manifests are
>    the 0.2.0 code snapshot, the 1.0.0 and 1.0.1 addendum snapshots and evidence bundle 1.0.0.
> 4. Plan: plan_reproduction(..., run_root=<a NEW directory outside the repository, <home>/ScientificRuns and <home>/data/private>).
> 5. Run in plan order, one call each: stage, environment_check, then step4c_b (numerical, allow_long=true), check10a (numerical,
>    allow_long=true), global_10c (numerical, allow_long=true), evaluate_states, phase_sequence, pure_elements, thermochemistry
>    (allow_long=true), laplace_weights (allow_long=true). Pass python= and the PhaseForge+ source the tools ask for. check10a must
>    run before global_10c, phase_sequence, pure_elements and thermochemistry: it writes the 10a pick they use (results/pick10a_start.txt, tdb/step4c_b_hingefloor_pick10a.tdb).
> 6. Judgement steps are never executed: get_step returns the recorded decision and its source (get_decisions lists them, the agent
>    decisions labelled).
> 7. Compare: compare_outputs(...).
> 8. Report: items run; PASS/FAIL per check with reference, rerun value and tolerance; what was not run and why; the report path;
>    and every choice the tools did not settle. The verdict is by predictions only (PI, 6 Nov: "this is too strict"): objective
>    of the 10a pick (by rule), diagram topology and phase sequence, eutectic and CrNi2 top, thermochemistry, pure elements and
>    Laplace weight within tolerance, plus the byte checks of data identity (staged inputs, evidence bundle, evaluated states).
>    Parameters (results/pick10a_rerun.json; flat directions undetermined), start and mode labels, cache files, timestamps,
>    the environment check and the PhaseForge+ pin are notes, never failures.

## Expected results (from the scripted 1.0.1 rerun on spark1 and the original run)

| item | expected | reference |
|---|---|---|
| step4c_b | the multistart and evaluate.py run (exit code 0). This item has no expectations of its own: its predictions are judged at the 10a pick (check10a) | run card crni-step4c_b_hingefloor |
| check10a | 10a pick (by rule) logpost within 0.01 of −5657.2886369; eligible; eutectic 1614 K and CrNi2 top 860 K within 2 K. Notes: the 10b parameter comparison (determined VV0000–VV0003, VV0012; the other nine undetermined) and the TDB text. The start label may differ by machine (s4 on the Studio, s1 in the 1.0.0 spark1 rerun) | run card crni-step4c_b-check10a; `results/pick10a_rerun.json` |
| global_10c | from the 10a pick: best logpost of each method within 0.01 of −5657.2886369 (no better optimum) | run cards crni-step4c_b-10c-{basin,anneal} |
| evaluate_states | `states_evaluated@1.0.0.json` byte-identical | evidence bundle 1.0.0 |
| phase_sequence | at the 10a pick: identical phase order at every x of a 0.01 grid, transitions within 10 K | acceptance target |
| pure_elements | at the 10a pick: unary limits exact; Cr BCC_A2, Ni FCC_A1 below T_m (the Cahn input is staged; no <home>/ScientificRuns path) | acceptance target |
| thermochemistry | at the 10a pick: the 22 data/thermo datasets present, rms residual/σ within 0.1 of the recorded pick (`results/thermo_compare.json`) | bundle reference_outputs per_dataset_step4c_b_hingefloor.json |
| laplace_weights | main-mode weight 0.766 within 0.01 (uses the recorded modes) | run card crni-uq-laplace-step4c_b |
| PhaseForge+ pin (note) | the 10 files of `environment/pins/spark1_phaseforgeplus_src_files.sha256` match (the protocol names it: code `phaseforgeplus`, file `source_pin`) | PINS.md |

The scripted rerun of the same document on spark1 and its outcome are in `protocols/reproduce/crni-paper-fit-step4c-b-1.0.1-spark1/`.

## What an agent driving sage_mcp needs (and what the tools do not give it)

1. **Host and interpreter.** A host with the locked fitting environment: `<fit-env>` (Studio) or
   `spark1:<home>/orchid-crni-mcmc-20261105/env/grad/bin/python` (pass `python=`; open point 3 of REPRODUCE_WITH_MCP.md). espei
   0.8.11.dev82+g9039ea215, pycalphad 0.11.3.dev35+g9a6939dd2, scipy 1.18.1 (10c uses scipy's `seed=` stream).
2. **PhaseForge+ source** for the hinge (`{PFP}`), hash-checked against the source pin the protocol declares
   (`environment/pins/spark1_phaseforgeplus_src_files.sha256`: the 9 files under `src/` and `pyproject.toml` of c66656f). The Studio
   checkout `<home>/src/PhaseForgePlus` is now at a later commit (6698473; `hinge.py` and `objective.py` unchanged, other files may
   differ). Give the agent a c66656f copy, or the spark1 copy `<home>/orchid-crni-mcmc-20261105/src/PhaseForgePlus/src`. Note that
   `model.py` puts `<home>/src/PhaseForgePlus/src` ahead of `PYTHONPATH` when that directory exists (snapshot code, unchanged).
3. **Wall time and CPU.** On spark1 with 4 workers in the 1.0.0 rerun:

   | item | wall time |
   |---|---|
   | step4c_b | 0.6 h |
   | check10a | 0.3 h |
   | global_10c | 1.6 h (two processes in parallel) |
   | laplace_weights | 0.3 h |

   About 3 h in all, with 4–6 cores free. The Studio took 1.6 h for step4c_b alone. The fits are synchronous MCP calls (open point
   8: no background-job mode), so the agent's client must allow calls of about 2 h. Otherwise the PI runs the long items with
   `orchid_reproduce.py --only`, and the agent records them with `record_external_run` and compares.
4. **A new run root** outside the repository, `<home>/ScientificRuns` and `<home>/data/private`, with ~200 MB free (traces of 10c ≈ 20 MB).
5. **Load discipline.** Check the host load first; other agents' Cu–Zr chains may be running on the Studio and spark1: never touch them.
6. **No restricted files are needed.** The evidence bundle carries the derived facts; the two private exports are hashed only.
7. **Known limits the agent should report, not fix.**
   - The 10a "within its own uncertainty" test is the agent reading |r| ≤ σ (labelled).
   - Dual annealing fits only 2 local solves into its budget.
   - The undetermined set is an operational reading (labelled): the symbols where the two recorded minima A_s4 and A2_s5_flat differ by more than the 10b tolerance.
   - Thermochemistry is not a plan item.
   - Item 8b of fit_protocol (0 K hull) is not applied to Cr–Ni (PI, 6 Nov).
