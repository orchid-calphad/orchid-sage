# Q40: why the 10a re-evaluation of s1 gave −5517.68 instead of −5657.29 (investigation, 7 Nov 2026)

**Cause (confirmed): a write/read race on a shared cache file, not worker carry-over and not a nondeterministic objective.**
`model2.GradTarget.__init__` builds the `zpf_susp` category (the 12 Jette/Karmazin records evaluated with CRNI2 suspended) from
`model2.no_crni2_tdb(start_tdb)`, which rewrites the shared file `data/cache/step3b_thermo_crni2free_pick_noCRNI2.tdb`
(`Path.write_text`: truncate, then write) and returns its path; `Database(path)` then reads it. `check10a_ms.py` starts 4 spawned
workers that build their targets at the same moment (s1 is the first job of the first wave of 4). If one worker reads the file
between another worker's truncate and write, it reads an empty file. pycalphad parses it to an empty `Database` without error, and
ESPEI's `setup_context` silently keeps none of the 12 `zpf_susp` records (their phases are not in the database). That target then
lacks the `zpf_susp:ZPFResidual` term for the whole job, so every evaluation in the job (value, gradient, the 46-direction test) is
of a different objective.

## Evidence

All probes are read only, on copies of the 1.0.2 staged root (spark1 `<home>/orchid-protocols-work-20261106/q40/root`; Studio: a copy in
the agent scratchpad), with the run's interpreters (`spark1 <home>/orchid-crni-mcmc-20261105/env/grad`, `Studio <fit-env>`),
`OMP_NUM_THREADS=1`. Nothing was refitted.

1. **Fresh single process (`probe_eval.py`), twice each, s1, s2, s4, on spark1 and the Studio:** every value equals the multistart
   file to all printed digits (s1 −5657.288636864, \|g\| 2.27e-4; s2 −5657.288636867; s4 −5657.293148833), identical between
   repeats, orders and machines. The objective is deterministic at fixed θ.
2. **Term split at s1:** `zpf_susp:ZPFResidual` = **−139.608380**, and −5657.288637 + 139.608380 = −5517.680257, the recorded
   value. No other term is anywhere near that size difference.
3. **Empty no-CRNI2 database (`probe_eval.py --empty-susp`):** s1 evaluates at **−5517.680257224548, \|g\| 0.11879854393076754**
   on spark1, bit-identical to the 1.0.2 `check10a_rerun.json` row (Studio −5517.680257224549, \|g\| 0.118798543940). s2 gives
   −5517.680252 under the same defect, so any start can be hit.
4. **The race exists (`probe_race.py`, the truncate+rewrite+read loop alone):** 4 processes × 300 reads give 5 empty reads on spark1
   and 10 on the Studio, no partial reads and no parse errors; 1 process × 300 gives 0 on both.
5. **The full 4-worker setup (`probe_pool.py`, 6 rounds × 8 starts = 48 jobs on spark1, `probe_pool_n4_r6.json`):** 0 drops, every job
   holds 12 `zpf_susp` records and matches its file value. The window is narrow (0.4–0.8% of reads in the tight loop of
   item 4, less at pool start-up), which is why 1.0.0, 1.0.1 and the original Studio and spark1 checks were clean and 1.0.2 was hit
   once.
6. **Consistent with the record:** the 8 on-boundary points of s1 are all in the `zpf` group (Jenkins 1937, Svechnikov 1962), which is
   unaffected, so they were "the same 8"; `n_failed_equilibria` is 0 because the dropped records were never evaluated.
   Every other recorded 10a file (1.0.0, 1.0.1, Studio and spark1 4c-b, the three step-3b files) has re-evaluation = multistart value.

Ruled out: thread count (1 thread throughout), worker carry-over (each job builds a fresh `GradTarget`; repeated and reordered
evaluations in one process are identical), pycalphad/ESPEI caches, PhaseForge+ source (other 7 starts bit-identical).

## Effect on the verdicts

- **1.0.2 (spark1):** s1 was judged on a wrong objective and classed `not_stationary`; the rule then picked s2 (mode A, gap 1.1e-8).
  Every prediction is judged at the pick and still PASSES; the pick label is a note. A start hit by the drop is evaluated off the
  optimum of the objective it is judged on (\|g\| ~0.12), so in practice it is classed not stationary and lost, and the pick moves
  to the best remaining eligible start (here within 1.1e-8, same mode). Only if the hit start were still classed eligible would it
  win wrongly (−5517 is higher than −5657); this did not happen and is unlikely with the gradient test.
- **1.0.1 (spark1), Studio record, 1.0.0:** no drop (values equal the multistart file); verdicts stand.
- **MCP-agent rerun (brief 1.0.1):** same code path (`check10a_ms.py` through `orchid_reproduce.py`), same exposure; its verdict
  would be affected in the same way, i.e. rarely and so far only on the pick label.
- **Same pattern elsewhere in the plan:** `fit2.py` (spawned Pool, one target per worker built at the first call) and the 10c item
  (basin and anneal launched in parallel, each building a target) build `model2.GradTarget` concurrently too. A drop there would
  change a multistart endpoint or a 10c best; none happened in any recorded run (all 8 endpoints and both 10c bests reproduce).

## Recommended fix (for a new version, on the PI's go; frozen code unchanged)

1. Minimal, in `model2.no_crni2_tdb`: build the no-CRNI2 database **in memory** (`Database.from_string(text, fmt="tdb")`) instead of
   through a shared file, or write to a per-process temporary file and `os.replace` it into place (atomic), so no reader can see a
   truncated file.
2. Guard, in `GradTarget.__init__`: assert that every category keeps all its records (e.g. 12 `zpf_susp` records, `len(db.phases)`
   == 3 for the no-CRNI2 database); fail closed instead of silently dropping data.
3. In `check10a_ms.py`: record `logpost_multistart_file` (already done) and treat a mismatch above 1e-6 as a **failure of the check**,
   not as an ineligible start (Q40 third question). Evaluating each start in a fresh process is not needed: the workers already
   build a fresh target per job, and carry-over is ruled out.
