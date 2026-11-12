"""Prompts: cold-start procedures for an agent that has only this MCP server connected."""

from __future__ import annotations

REPRODUCE = """You are reproducing the ORCHID-SAGE assessment {protocol}. You have only the orchid-sage MCP tools. Do not guess:
every command, path, tolerance and decision comes from a tool result. Never run a step the tools refuse.

1. Read. get_protocol("{protocol}") (summary), then get_steps("{protocol}"). Note the reproduce items and the judgement steps.
2. Validate. validate("{protocol}"). Report every error. Hash mismatches of campaign files or reports do not block a rerun;
   mismatches of the bundle manifests do.
3. Verify inputs. verify_inputs("{protocol}"). The rerun needs only `bundle_manifests` to be ok (`rerun_ready: true`).
   List what is missing or restricted; restricted files are never read out or copied.
4. Plan. plan_reproduction("{protocol}", run_root="{run_root}"). Use a NEW directory outside the repository, the campaign
   directories and the restricted material. Write down, per item: kind, command, expected outputs, compute class, estimate, tolerances.
5. Run the deterministic items, one call each, in plan order:
   run_step("{protocol}", "stage", "{run_root}", confirm=true)
   run_step("{protocol}", "environment_check", "{run_root}", confirm=true)
   then every other item with kind "deterministic" (e.g. evaluate_states, tdb_header).
   If environment_check fails, stop and report the interpreter versions (python=<path> selects another interpreter).
   Numerical items (the fits) need allow_long=true when flagged needs_allow_long; run them only if asked to. A long item
   starts detached: run_step returns at once with status "running". Then call step_status("{protocol}", "{run_root}",
   <item>, wait_s=900) again until status is "finished" (each call returns within 15 min; the item keeps running between
   calls); the finished call writes the run card. Never start an item twice; one item runs at a time.
6. Judgement steps are never executed. For each, get_step("{protocol}", <step>) returns the recorded decision and its source.
7. Compare. compare_outputs("{protocol}", "{run_root}"). Deterministic outputs must be byte-identical; numerical ones are
   compared with the declared tolerances.
8. Report: items run, PASS/FAIL per check with reference and rerun hashes or values, what was not run and why, the
   comparison report path, and every point where you had to make a choice the tools did not settle.
"""

EXPLAIN = """Explain the ORCHID-SAGE assessment {protocol} to a CALPHAD reader, from the tools only.
1. get_protocol("{protocol}") and get_steps("{protocol}"): system, purpose, the general protocol it instantiates, the step sequence
   (one-shot -> liquidus -> thermochemistry -> solid state + exclusions -> ambiguous structures -> checks -> ranking -> UQ -> package).
2. get_run_cards("{protocol}"): what ran where (host, interpreter, seeds), which starts were picked, which runs failed.
3. get_decisions("{protocol}"): who decided what and why; overrides with conforms=false are departures from the general protocol.
4. get_evidence_manifest(<assessment>) and get_dashboard_data(<assessment>): evidence counts, certainty tiers, the pick and its checks.
5. get_open_questions(): the questions this assessment still depends on (its open_questions list).
Say what is pending as pending. Cite the ORCHID record ids and the sources the documents name; never invent a number.
"""

FRESH = """You are starting a FRESH ORCHID-SAGE assessment of {system} with only the orchid-sage MCP tools.
The server never decides science: model choice, picks, phases or sublattices and data conflicts are decision requests that
a person answers. Every change to the method is a documented change (modify_protocol) that bumps the protocol version.

1. new_assessment(system="{system}", assessment_id="{assessment_id}", run_root="{run_root}"[, phases=[...], T_range=[lo, hi]]).
   The run root must be new and outside the repository, the campaign directories and the restricted material.
2. Read the open decision requests it returns. Do NOT answer them yourself: show each one (question, evidence) to the PI or
   the person in charge and record their answer with record_decision(assessment, request_id, decision, who, why, bindings).
3. gather_evidence(assessment): the evidence bundle from the local ORCHID data (espei datasets), states with certainty tiers,
   excluded phases at every observed state (needs the phase set). Report its `gaps` as gaps; never fill them.
4. Loop: next_step(assessment) -> read `next` (mode, command, compute, blockers) ->
     mode internal or command: run_step(assessment, step, run_root, confirm=true[, allow_long=true for long CPU steps]);
     mode judgement: run_step creates the decision request; stop and ask; record_decision when answered;
     mode job_spec (GPU: one-shot relaxations, liquid MD): run_step writes the job spec; hand it to the executor; when the job
       has run, record_external_run(assessment, step, run_card);
     not executable (campaign scripts, unbound placeholders): propose the documented change (modify_protocol type tool or
       binding) to the person, with why and evidence; never edit files by hand.
5. After any change, get_history(assessment) shows versions, overrides, decisions and the steps marked stale; re-run them.
6. When the final pick is recorded, package(assessment).
Report at every stop: what ran, run cards written, open decisions, gaps.
"""

PROMPTS = {
    "reproduce_assessment": ("Cold-start procedure: validate, verify inputs, plan, run the deterministic steps, compare, report",
                             [("protocol", "specific protocol id@version, e.g. crni-paper-fit-step4-s1@0.1.0-draft", True),
                              ("run_root", "a new absolute directory for the rerun", True)], REPRODUCE),
    "explain_assessment": ("Explain an assessment (steps, runs, decisions, evidence, open questions) from the documents",
                           [("protocol", "specific protocol id@version", True)], EXPLAIN),
    "run_fresh_assessment": ("Cold-start procedure for a fresh assessment of a binary system (decisions stay with people)",
                             [("system", "binary system, alphabetical, e.g. AL-CU", True), ("assessment_id", "new protocol id, lower case", True),
                              ("run_root", "a new absolute directory", True)], FRESH),
}


def render(name: str, args: dict) -> str:
    desc, params, tpl = PROMPTS[name]
    vals = {p: args.get(p) or f"<{p}>" for p, _, _ in params}
    return tpl.format(**vals)
