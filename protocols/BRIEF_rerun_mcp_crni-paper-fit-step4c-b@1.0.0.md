# Cold-start brief: MCP-agent rerun of crni-paper-fit-step4c-b@1.0.0 (prepared 6 Nov 2026; not launched)

The PI launches this rerun. It follows `protocols/BRIEF_rerun_agents.md` (run cards, trajectories, no in-place edits) and the
cold-start prompt of `sage_mcp/REPRODUCE_WITH_MCP.md`, updated for version 1.0.0 of the Cr–Ni specific protocol (10a with the kink
rule, the 10c global search, and the stage fix for `tdb/step1_oneshot.tdb`).

## The prompt (give it verbatim to an agent that has only the orchid-sage MCP server connected)

> You are reproducing the ORCHID-SAGE assessment crni-paper-fit-step4c-b@1.0.0. You have only the orchid-sage MCP tools. Do not
> guess: every command, path, tolerance and decision comes from a tool result. Never run a step the tools refuse. LOCAL work only:
> no remote or cloud agents, no `rm` (move aside), stop only processes you started, by exact PID; never touch other jobs on the host.
> 1. Read: get_protocol("crni-paper-fit-step4c-b@1.0.0"), then get_steps. Note the reproduce items (step4c_b, check10a, global_10c,
>    evaluate_states, phase_sequence, pure_elements, laplace_weights) and the judgement steps.
> 2. Validate: validate("crni-paper-fit-step4c-b@1.0.0"). Report every error.
> 3. Verify inputs: verify_inputs(...). The rerun needs only `bundle_manifests` to be ok (`rerun_ready: true`); the three manifests are
>    the 0.2.0 code snapshot, the 1.0.0 addendum snapshot and evidence bundle 1.0.0.
> 4. Plan: plan_reproduction(..., run_root=<a NEW directory outside the repository, <home>/ScientificRuns and <home>/data/private>).
> 5. Run in plan order, one call each: stage, environment_check, then step4c_b (numerical, allow_long=true), check10a (numerical,
>    allow_long=true), global_10c (numerical, allow_long=true), evaluate_states, phase_sequence, pure_elements, laplace_weights
>    (allow_long=true). Pass python= and the PhaseForge+ source the tools ask for.
> 6. Judgement steps are never executed: get_step returns the recorded decision and its source (get_decisions lists them, the agent
>    decisions labelled).
> 7. Compare: compare_outputs(...).
> 8. Report: items run; PASS/FAIL per check with reference, rerun value and tolerance; what was not run and why; the report path;
>    and every choice the tools did not settle. Judge reproducibility by predictions (objective, 10a pick and kind, diagram topology,
>    eutectic and CrNi2 top, boundaries, thermochemistry); parameters in flat directions are reported as undetermined, not as failures.

## Expected results (from the scripted rerun and the original run)

| item | expected | reference |
|---|---|---|
| step4c_b | s4 logpost within 0.01 of −5657.2886369; every parameter within 50 J/mol (a) / 0.03 J/mol/K (b); eutectic 1614 K and CrNi2 top 860 K within 2 K | run card crni-step4c_b_hingefloor |
| check10a | the check asks for the label s4_perturbed and FAILED in the scripted spark1 rerun (s4 fell into the flat neighbour mode A2; the 10a pick s1 matched the original pick's objective within 4e-9 and its parameters within 0.039 of the tolerance). Report the pick's objective and parameters, not the label | run card crni-step4c_b-check10a; reproduce README failure 1 |
| global_10c | best logpost of each method within 0.01 of the pick (no better optimum); the plan starts from the label s4, which may be the A2 mode on another machine (reproduce README failure 2) | run cards crni-step4c_b-10c-{basin,anneal} |
| evaluate_states | `states_evaluated@1.0.0.json` byte-identical | evidence bundle 1.0.0 |
| phase_sequence | identical phase order at every x of a 0.01 grid, transitions within 10 K | acceptance target |
| pure_elements | unary limits exact; Cr BCC_A2, Ni FCC_A1 below T_m. Expected to FAIL to run on a host without `<home>/ScientificRuns/cr-ni-coherent-20261105/results.json` (absolute path in physics.py; not staged): report it as a stage gap | reproduce README failure 3 |
| laplace_weights | main-mode weight 0.766 within 0.01 | run card crni-uq-laplace-step4c_b |

The scripted rerun of the same document (spark1) and its outcome are in `protocols/reproduce/crni-paper-fit-step4c-b-1.0.0-spark1/`.

## What an agent driving sage_mcp needs (and what the tools do not give it)

1. **Host and interpreter.** A host with the locked fitting environment: `<fit-env>` (Studio) or
   `spark1:<home>/orchid-crni-mcmc-20261105/env/grad/bin/python` (pass `python=`; open point 3 of REPRODUCE_WITH_MCP.md). espei
   0.8.11.dev82+g9039ea215, pycalphad 0.11.3.dev35+g9a6939dd2, scipy 1.18.1 (10c uses scipy's `seed=` stream).
2. **PhaseForge+ source** for the hinge (`{PFP}`), hash-checked against `environment/pins/spark1_phaseforgeplus_files.sha256` (the check covers the full checkout and fails on the minimal spark1 copy, whose 9 `src/` files all match; reproduce README failure 4):
   Studio `<home>/src/PhaseForgePlus/src`, spark1 `<home>/orchid-crni-mcmc-20261105/src/PhaseForgePlus/src`.
3. **Wall time and CPU.** step4c_b ≈ 1.6 h with 4 workers (5673 s on the Studio, 4.2 s per evaluation on spark1); check10a ≈ 0.4–0.8 h;
   global_10c ≈ 1.9 h (two processes in parallel); laplace_weights ≈ 0.5 h. About 4.5 h in all, with 4–6 cores free. The fits are
   synchronous MCP calls (open point 8: no background-job mode), so the agent's client must allow calls of about 2 h, or the PI runs
   the long items with `orchid_reproduce.py --only` and the agent records them with `record_external_run` and compares.
4. **A new run root** outside the repository, `<home>/ScientificRuns` and `<home>/data/private`, with ~200 MB free (traces of 10c ≈ 20 MB).
5. **Load discipline.** Check the host load first; other agents' Cu–Zr chains may be running on the Studio and spark1: never touch them.
6. **No restricted files are needed.** The evidence bundle carries the derived facts; the two private exports are hashed only.
7. **Known gaps the agent should report, not fix.** The general protocol has no step for 10c (recorded under `fit_solid`); the 10a
   "within its own uncertainty" test is the agent reading |r| ≤ σ (labelled); dual annealing fits only 2 local solves into its budget.
