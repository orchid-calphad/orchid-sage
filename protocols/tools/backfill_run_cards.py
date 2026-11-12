#!/usr/bin/env python3
"""Back-fill run cards (orchid-assessment-schema run_card) for the runs that produced the current picks, by
CONVERTING the campaigns' own records (run_card.json, result.json, multistart.json, ranking/evaluation files,
launch TSVs). Nothing is recomputed: values are copied, files are hashed, and every card lists the files it was
converted from. Campaign directories are only read.

  python3 tools/backfill_run_cards.py [OUT_DIR] [--check]  -> run_cards/*.json (or OUT_DIR/*.json)

Frozen cards (tools/frozen.py: pinned by a protocol or crate) are never changed: if any card would change, nothing is
written, the cards are named on stderr and the exit status is 3. --check reports and writes nothing.

Campaigns (under runs_root of local/config.json):
  Cu-Zr  cuzr-protocol-oneshot-20261106/  run 1 (moved to attic/run1_s2value_20261106/ on 6 Nov)
  Cr-Ni  crni-phaseforge-20261105/ (one-shot) and crni-paper-fit-20261106/ (fit)
Host names come from local/config.json (machine labels studio, spark1). Command lines are copied as the campaigns
recorded them (record text, written with ~ for the home directory).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import localpaths  # noqa: E402
import orchidproto as op  # noqa: E402
import frozen  # noqa: E402

_ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
OUT = Path(_ARGS[0]) if _ARGS else op.ROOT / "run_cards"
WRITES = frozen.Writes("backfill_run_cards.py")
RUNS = localpaths.setting("runs_root")
SP1, SP1_SSH, STUDIO = localpaths.host("spark1"), localpaths.host("spark1_ssh"), localpaths.host("studio")
RH = localpaths.remote_home()                       # home directory on the DGX Sparks, as their records write it
FITPY = localpaths.RECORD_FIT_PYTHON                # the Studio fit interpreter, as the records write it
GEN = "orchid-calphad-fit@2.0.0"
CUZR_SP = "cuzr-oneshot-h2-s7@0.1.0-draft"
CRNI_SP = "crni-paper-fit-step4-s1@0.1.0-draft"
CZ = RUNS / "cuzr-protocol-oneshot-20261106"
CZA = CZ / "attic/run1_s2value_20261106"
CN1 = RUNS / "crni-phaseforge-20261105"
CN = RUNS / "crni-paper-fit-20261106"
B464_FIT = f"{RH}/runs/cuzr-protocol-oneshot-20261106/fit/"


SNAPMAP = {}
for _art in ("cuzr-oneshot-h2-s7", "crni-paper-fit-step4-s1"):
    _m = op.ROOT.parent / "assessments" / _art / "code" / "MANIFEST.json"
    if _m.exists():
        for _f in json.loads(_m.read_text())["files"]:
            _q = op.ROOT.parent / "assessments" / _art / "code" / _f["path"]
            SNAPMAP[(_art, _f["original"])] = _q
            if not _f["path"].startswith("records/") and not _f["path"].endswith(f".{SP1}_0425.py"):
                SNAPMAP.setdefault((_art, Path(_f["original"]).name), _q)


def code_ref(art, p, role="code"):
    """Code is referenced by its repo snapshot (byte-identical to what ran), not by the live run directory."""
    q = SNAPMAP.get((art, op.tilde(p))) or SNAPMAP.get((art, Path(p).name))
    if q is None:
        return ref(p, role + " (live run directory; not in the snapshot)")
    r = ref(q, role + f" (snapshot of {op.tilde(p)})")
    r["path"] = str(q.relative_to(op.ROOT.parent))
    return r


def ref(p, role=None, storage="local", note=None):
    p = Path(p)
    r = {"path": op.tilde(p), "sha256": op.sha256_file(p), "storage_class": storage}
    if role:
        r["role"] = role
    if note:
        r["note"] = note
    return r


def remote(path, sha, role, source):
    return {"path": f"{SP1}:" + path.replace(RH + "/", "<home>/"), "sha256": sha, "storage_class": "remote_record",
            "role": role, "hash_source": source}


def card(run_id, title, sp, step, status, **kw):
    c = {"type": "run_card", "schema_version": op.SCHEMA_VERSION, "id": run_id, "version": "1.0.0", "title": title,
         "status": status, "run_id": run_id, "executes": {"specific_protocol": sp, "general_protocol": GEN, "step": step}}
    c.update(kw)
    return c


def write(c):
    WRITES.add(OUT / f"{c['run_id']}.json", json.dumps(c, indent=1, ensure_ascii=False) + "\n")   # committed all or none in __main__
    return c["run_id"]


def tdb_stem_value(tdb, sym):
    import re
    m = re.search(r"FUNCTION\s+%s\s+298\.15\s+([-+.\dEe]+);" % sym, Path(tdb).read_text())
    return float(m.group(1)) if m else None


# ------------------------------------------------------------------------------------------------ Cu-Zr
def cuzr():
    ids = []
    # one-shot solids (DGX Spark containers)
    tsv = CZ / f"logs/{SP1}/launch_solids.tsv"
    rows = [l.split("\t") for l in tsv.read_text().strip().split("\n")]
    ids.append(write(card(
        "cuzr-r1-oneshot-solids", "Cu-Zr one-shot: staged MLIP relaxation of 60 SQS + 6 compounds (both potentials)", CUZR_SP,
        "staged_relax", "complete", host=SP1_SSH, hardware_class="DGX Spark (GB10 GPU)",
        pids=[int(r[2]) for r in rows], started=rows[0][3].strip(),
        finished={"status": "pending", "reason": "end time not recorded in a Studio file; REPORT.md states 66/66 cells per potential"},
        interpreter="python (container cuzr-phaseforge-grace-gpu:20261104)",
        packages={"image": "cuzr-phaseforge-grace-gpu:20261104", "image_digest": "pending (not recorded)", "tensorpotential": "0.6.2.1", "materialsframework": "1.0.0"},
        command=f"code/launch_solids.sh on {SP1} -> docker run ... python -u /campaign/code/relax_solids.py GRACE-2L-SMAX-OMAT-large | GRACE-2L-OMAT",
        seeds={"sqs": "m_scraps seeds BCC 2026110601/02, FCC 2026110611/12, HCP 2026110631/32 (code/gen_sqs.py)"},
        inputs=[code_ref("cuzr-oneshot-h2-s7", CZ / "code/relax_solids.py", "relaxation driver"), code_ref("cuzr-oneshot-h2-s7", CZ / "code/gen_sqs.py", "SQS generator"),
                code_ref("cuzr-oneshot-h2-s7", CZ / f"logs/{SP1}/potential_sha256.txt", "MLIP weight hashes")],
        outputs=[ref(CZA / "results/solids_GRACE-2L-SMAX-OMAT-large.json", "staged energies, value potential"),
                 ref(CZA / "results/solids_GRACE-2L-OMAT.json", "staged energies, cross-check potential")],
        results={"cells_per_potential": "66/66 (REPORT.md)", "lattice": "every mixed SQS at x_Zr 0.125-0.875 leaves its parent lattice at s2"},
        trajectory={"status": "not_recorded", "reason": "relaxation, not a fit"},
        converted_from=[code_ref("cuzr-oneshot-h2-s7", tsv, "launch TSV"), code_ref("cuzr-oneshot-h2-s7", CZ / "REPORT.md", "campaign report")],
        notes=["run 1 used the s2 value for every cell; the PI's midpoint rule (6 Nov) postdates it (rerun in progress)"])))
    # one-shot TDB build (run 1)
    ot = json.loads((CZA / "results/oneshot_tdb.json").read_text())
    ids.append(write(card(
        "cuzr-r1-oneshot-build", "Cu-Zr one-shot TDB and observations (run 1, s2 value; liquid reused from GRACE-2L-OMAT)", CUZR_SP,
        "build_oneshot_tdb", "complete", host=STUDIO, hardware_class="Mac Studio M1 Max", started="2026-11-06",
        finished="2026-11-06", interpreter=FITPY, packages={"pycalphad": "0.11.3.dev35+g9a6939dd2", "numpy": "2.5.4"},
        command=f"{FITPY} code/attic_build_oneshot_run1.py   (run-1 version of build_oneshot.py)",
        seeds={},
        inputs=[ref(CZA / "results/solids_GRACE-2L-SMAX-OMAT-large.json", "staged energies"), ref(CZ / "tdb/previous/step1_oneshot_staged20261105.tdb", "VV layout base"),
                ref(RUNS / "cuzr-fresh-phaseforge-20261104/initialization/candidate_assisted_v19/liquid_initializer.json", "liquid L0/L1 (GRACE-2L-OMAT 100 ps, 2178 K)"),
                ref(localpaths.sibling("orchid-phaseforge-demo") / "results/sigma_mlip.json", "sigma_MLIP"), code_ref("cuzr-oneshot-h2-s7", CZ / "code/attic_build_oneshot_run1.py", "builder")],
        outputs=[ref(CZA / "tdb/step1_oneshot.tdb", "step-1 base TDB"), ref(CZA / "results/oneshot_observations.json", "one-shot observations"),
                 ref(CZA / "results/oneshot_tdb.json", "build record"), ref(CZA / "tdb/CuZr_PhaseForge_oneshot_GRACE-2L-OMAT.tdb", "cross-check TDB")],
        results={"liquid_potential_flag": ot.get("liquid_potential_flag")},
        trajectory={"status": "not_recorded", "reason": "deterministic build, not a fit"},
        converted_from=[ref(CZA / "results/oneshot_tdb.json", "build record")])))
    # step-1 evaluation
    ids.append(write(card(
        "cuzr-r1-step1-eval", "Cu-Zr step 1: one-shot diagram and checks", CUZR_SP, "oneshot_diagram", "complete",
        host=STUDIO, started="2026-11-06", finished="2026-11-06", interpreter=FITPY,
        packages={"pycalphad": "0.11.3.dev35+g9a6939dd2"}, command=f"{FITPY} scripts/evaluate_step.py tdb/step1_oneshot.tdb step1_oneshot steps/step1/eval",
        seeds={}, inputs=[ref(CZA / "tdb/step1_oneshot.tdb", "one-shot TDB"), code_ref("cuzr-oneshot-h2-s7", CZ / "scripts/evaluate_step.py", "evaluator"), code_ref("cuzr-oneshot-h2-s7", CZ / "scripts/model.py", "analytic model")],
        outputs=[ref(CZA / "steps/step1/eval/eval.json", "checks"), ref(CZA / "steps/step1/eval/fig_step1_oneshot.png", "diagram")],
        results=_cuzr_eval_summary(CZA / "steps/step1/eval/eval.json"),
        trajectory={"status": "not_recorded", "reason": "no fit"}, converted_from=[ref(CZA / "steps/step1/eval/eval.json")])))
    tsv = (CZ / "logs/launch_fits.tsv").read_text().strip().split("\n")
    launch = {}
    for l in tsv:
        st, s, pid, t = l.split("\t")
        launch.setdefault(st, []).append((s, int(pid), t))
    steps = [("step2_liquidus", "fit_liquidus", "accepted"), ("stepH1_topology_hinge", "cuzr_fit_h1", "accepted"),
             ("stepH2_hinge_thermo", "cuzr_fit_h2", "accepted"), ("step3_thermo", "fit_thermo", "side_branch"),
             ("step4_zpf_dense", "fit_solid", "side_branch"), ("stepH2b_hinge_thermo_braga", "cuzr_fit_h2b", "side_branch")]
    for name, gstep, role in steps:
        D = CZA / "steps" / name
        rk = json.loads((D / "ranking_protocol.json").read_text())
        starts = sorted(D.glob("s[0-9]*"))
        rc0 = json.loads((starts[0] / "run_card.json").read_text())
        cfg = rc0["config"]
        inputs, seen = [], set()
        for s in starts:
            rc = json.loads((s / "run_card.json").read_text())
            for f in rc["data_files"]:
                p = f["path"].replace(B464_FIT, str(CZ) + "/")
                if not Path(p).exists():
                    p = f["path"].replace(B464_FIT, str(CZA) + "/")
                if p in seen:
                    continue
                seen.add(p)
                r = {"path": op.tilde(p), "sha256": f["sha256"], "storage_class": "local", "role": "data file read by the objective (hash from run_card.json)"}
                inputs.append(r)
        start_local = CZA / cfg["start_tdb"]
        inputs.insert(0, ref(start_local, "start TDB"))
        inputs.insert(1, ref(CZA / "steps/configs" / (name + ".json"), "step config"))
        if cfg.get("hinge"):
            inputs.insert(2, ref(CZA / Path(cfg["hinge"]).name, "hinge sidecar (cells from the step-2 pick)"))
        for code in ("scripts/fit_step.py", "scripts/rank_protocol.py", "scripts/judge.py", "scripts/evaluate_step.py", "scripts/model.py", "code/run_step.sh"):
            inputs.append(code_ref("cuzr-oneshot-h2-s7", CZ / code))
        outputs, results, traj = [], {}, []
        for s in starts:
            r = json.loads((s / "result.json").read_text())
            sid = s.name
            outputs += [ref(s / "tuned.tdb", f"{sid} TDB"), ref(s / "result.json", f"{sid} result"), ref(s / "eval/eval.json", f"{sid} checks")]
            if (s / "trace.jsonl").exists():
                traj.append(ref(s / "trace.jsonl", f"{sid} per-evaluation trace"))
            rs = next((x for x in rk["starts"] if x["start"] == int(sid[1:])), {})
            results[sid] = {"lnL_start": r["lnL_start"], "lnL_best": r["lnL_best"], "components_best": r["per_residual"],
                            "termination": r["final"], "n_eval": r["n_eval"], "wall_s": round(r["wall_s"], 1), "grad_norm_best": r["grad_norm_best"],
                            "perturbation_seed": json.loads((s / "run_card.json").read_text())["perturbation_seed"],
                            "topology": rs.get("topology"), "topology_ok": rs.get("topology_ok"), "plausibility": rs.get("plausibility"),
                            "plausible": rs.get("plausible"), "gate": rs.get("gate"), "within25": rs.get("within25")}
        pick = rk["picked_start"]
        outputs.append(ref(CZA / "tdb" / (name + ".tdb"), "pick copied to tdb/<step>.tdb"))
        if name == "stepH2_hinge_thermo":
            outputs.append(ref(CZA / "tdb/stepH2_hinge_thermo_PICK_s7.tdb", "the pick (artifact)"))
        ln = launch.get(name, [])
        ids.append(write(card(
            f"cuzr-r1-{name}", f"Cu-Zr run 1 {name}: {len(starts)} starts, pick s{pick}", CUZR_SP, gstep,
            "complete", status_note=f"role in the specific protocol: {role}", host=rc0["host"], hardware_class=f"DGX Spark {SP1} CPU (fits), Mac Studio (ranking)",
            pids=[p for _, p, _ in ln], started=ln[0][2] if ln else rc0["started_utc"],
            finished={"status": "pending", "reason": "per-start wall time in results; end time not logged"},
            interpreter=rc0["python"].replace(RH + "/", f"{SP1}:<home>/"), packages={"espei": rc0["espei_version"], "pycalphad": rc0["pycalphad_version"]},
            command=f"code/run_step.sh {name} {len(starts)}   ({SP1}: OMP_NUM_THREADS=1 PFP_SRC=<home>/runs/cuzr-protocol-oneshot-20261106/src/PhaseForgePlus/src <home>/orchid-crni-mcmc-20261105/env/grad/bin/python -u scripts/fit_step.py steps/configs/{name}.json <s>); then CUZR_PY={FITPY} python scripts/rank_protocol.py {name} on the Studio",
            threads="OMP_NUM_THREADS=1 per start", config=cfg,
            seeds={"rule": "start 0 = start TDB; start k > 0: numpy default_rng(1000 + k); constants x(1 + 0.1 N(0,1)), T terms + N(0, 3 J/K)",
                   "per_start": {s.name: json.loads((s / "run_card.json").read_text())["perturbation_seed"] for s in starts}},
            inputs=inputs, outputs=outputs, results=results,
            trajectory=traj[0] if len(traj) == 1 else ({"status": "not_recorded", "reason": "no trace"} if not traj else traj[[t["role"].split()[0] for t in traj].index(f"s{pick}")]),
            ranking={"rule": rk["rule"], "picked_start": f"s{pick}", "n_starts": rk["n_starts"], "n_topology_ok": rk["n_topology_ok"], "n_plausible": rk["n_plausible"],
                     "order": [f"s{x['start']}" for x in rk["starts"]]},
            converted_from=[ref(starts[0] / "run_card.json", "campaign run card (start 0)"), ref(D / "ranking_protocol.json", "ranking")] +
                           [ref(s / "run_card.json", f"campaign run card {s.name}") for s in starts[1:]],
            notes=[f"per-start traces (trace.jsonl, one line per evaluation with lnL, components and x): " + ", ".join(t["path"] for t in traj)] if traj else [])))
    return ids


def _cuzr_eval_summary(p):
    e = json.loads(Path(p).read_text())
    return {"gate": e.get("gate"), "within_25K_of_wang_exp": e.get("within_25K_of_wang_exp"), "pure_element_check_pass": e.get("pure_element_check_pass"),
            "solid_above_liquidus": e.get("solid_above_liquidus"), "compound_stability_K_300_2200": e.get("visual_check", {}).get("compound_stability_K_300_2200")}


# ------------------------------------------------------------------------------------------------ Cr-Ni
def crni():
    ids = []
    ids.append(write(card(
        "crni-oneshot-solids-liquid", "Cr-Ni one-shot: staged MLIP solids (both potentials) and 100 ps liquid MD with MLIPentropy", CRNI_SP,
        "staged_relax", "complete", host=SP1_SSH, hardware_class="DGX Spark (GB10 GPU)", started="2026-11-05T17:12:00Z",
        finished={"status": "pending", "reason": "end time of the 864-atom run not recorded in a Studio file"},
        interpreter="python (container cuzr-phaseforge-grace-gpu:20261104)",
        packages={"image": "cuzr-phaseforge-grace-gpu:20261104", "image_digest": "pending (not recorded)", "tensorpotential": "0.6.2.1", "materialsframework": "1.0.0", "m_scraps": "0.6.0"},
        command=f"code/gen_sqs.py + gen_sqs_fullrange.py (Studio); relax_solids.py / relax_solids_v2.py and run_liquid.py in containers on {SP1} (code/launch_liquid.sh); collect.sh; analyze_solids.py; analyze_liquid.py",
        seeds={"sqs": "bcc 2026110501/02, fcc 2026110511/12 (PLAN.md STANDARD section)"},
        inputs=[code_ref("crni-paper-fit-step4-s1", CN1 / f"code/{c}") for c in ("gen_sqs.py", "gen_sqs_fullrange.py", "relax_solids.py", "relax_solids_v2.py", "run_liquid.py", "analyze_solids.py", "analyze_liquid.py", "launch_liquid.sh", "collect.sh")]
               + [code_ref("crni-paper-fit-step4-s1", CN1 / "provenance/potential_sha256.txt", "MLIP weight hashes")],
        outputs=[ref(CN1 / "results" / f, "result") for f in ("solids_GRACE-2L-SMAX-OMAT-large.json", "solids_GRACE-2L-OMAT.json", "liquid_checks_enthalpy.json", "liquid_excess_entropy.json", "liquid_ideal_mixing_check.json", "liquid_cutoffs.json")],
        results={"note": "pure Cr at 1900 K crystallised after 82 ps; analysed over its first 80 ps (PLAN.md results notes)", "ideal_mixing_check": "|S_chem,ex| <= 0.004 J/mol-atom/K"},
        trajectory={"status": "not_recorded", "reason": "relaxation and MD, not a fit"},
        converted_from=[code_ref("crni-paper-fit-step4-s1", CN1 / "PLAN.md", "campaign plan and run log"), code_ref("crni-paper-fit-step4-s1", CN1 / "results/NOT_USED.md", "used / not used record")])))
    ot = json.loads((CN1 / "results/oneshot_tdb.json").read_text())
    ids.append(write(card(
        "crni-oneshot-build", "Cr-Ni one-shot TDBs (with and without liquid S_ex) and the step-1 base", CRNI_SP, "build_oneshot_tdb", "complete",
        host=STUDIO, started="2026-11-06", finished="2026-11-06", interpreter=FITPY,
        packages={"pycalphad": "0.11.3.dev35+g9a6939dd2"},
        command=f"{FITPY} code/build_tdb.py (crni-phaseforge-20261105); {FITPY} scripts/make_base.py (crni-paper-fit-20261106)",
        seeds={}, inputs=[ref(CN1 / "results/solids_GRACE-2L-SMAX-OMAT-large.json"), ref(CN1 / "results/liquid_excess_entropy.json"), ref(CN1 / "results/liquid_checks_enthalpy.json"),
                          ref(RUNS / "cr-ni-rebuild-20261105/inputs/cr-ni-model.tdb", "unary source (SGTE91)"), code_ref("crni-paper-fit-step4-s1", CN1 / "code/build_tdb.py"), code_ref("crni-paper-fit-step4-s1", CN / "scripts/make_base.py")],
        outputs=[ref(CN1 / "tdb/CrNi_PhaseForge_oneshot_Sex_GRACE-2L-SMAX-OMAT-large.tdb", "one-shot with S_ex"), ref(CN1 / "tdb/CrNi_PhaseForge_oneshot_GRACE-2L-SMAX-OMAT-large.tdb", "one-shot without S_ex"),
                 ref(CN1 / "results/oneshot_tdb.json", "build record"), ref(CN / "tdb/step1_oneshot.tdb", "step-1 base with VV symbols"), ref(CN / "tdb/step1_oneshot_noSex.tdb")],
        results={"solid_L_J_mol": ot["solid_L_J_mol"], "liquid_a_J_mol": ot["liquid_a_J_mol"], "liquid_b_from_Sex_J_mol_K": ot["liquid_b_from_Sex_J_mol_K"]},
        trajectory={"status": "not_recorded", "reason": "deterministic build"}, converted_from=[ref(CN1 / "results/oneshot_tdb.json")])))
    steps = [("step1_oneshot", "oneshot_diagram", "accepted"), ("step2_liquidus", "fit_liquidus", "accepted"), ("step3_thermo", "fit_thermo", "failed"),
             ("step3b_thermo_crni2free", "fit_thermo", "accepted"), ("step4_solid", "fit_solid", "accepted")]
    logs = {"step1_oneshot": None, "step2_liquidus": "step2", "step3_thermo": "step3", "step3b_thermo_crni2free": "step3b", "step4_solid": "step4"}
    for name, gstep, role in steps:
        D = CN / "steps" / name
        rc = json.loads((D / "run_card.json").read_text())
        if "config" not in rc:   # step 1: no fit; the config file carries the start TDB
            rc["config"] = json.loads((CN / "steps/configs" / (name + ".json")).read_text())
            rc["start_tdb"] = rc["config"]["start_tdb"]
        ms = json.loads((D / "multistart.json").read_text())
        ev = json.loads((D / "evaluation.json").read_text()) if (D / "evaluation.json").exists() else {}
        evs = {e["start"]: e for e in ev.get("evaluations", [])}
        inputs = [ref(CN / rc["start_tdb"], "start TDB") if (CN / rc["start_tdb"]).exists() else None, ref(CN / "steps/configs" / (name + ".json"), "step config")]
        inputs = [i for i in inputs if i]
        if rc["config"].get("hinge"):
            inputs.append(ref(CN / rc["config"]["hinge"], "hinge sidecar"))
        for f in rc.get("data_files", []):
            inputs.append({"path": op.tilde(f["path"]), "sha256": f["sha256"], "storage_class": "local", "role": "data file read by the objective (hash from run_card.json)"})
        for code in ("fit.py", "model.py", "evaluate.py", "pd4.py"):
            inputs.append(code_ref("crni-paper-fit-step4-s1", CN / "scripts" / code))
        outputs = [ref(D / "multistart.json", "all starts"), ref(D / "run_card.json", "campaign run card")]
        if (D / "evaluation.json").exists():
            outputs.append(ref(D / "evaluation.json", "evaluation and ranking"))
        outputs += [ref(t, "start TDB") for t in sorted(D.glob("*.tdb"))]
        pickf = CN / "tdb" / f"{name}_pick.tdb"
        if pickf.exists():
            outputs.append(ref(pickf, "pick TDB"))
        if name == "step4_solid":
            outputs.append(ref(CN / "tdb/CrNi_paper_fit_FINAL_step4_s1.tdb", "the pick (artifact)"))
        results = {}
        for m in ms:
            e = evs.get(m["start"], {})
            results[m["start"]] = {"logpost": m["logpost"], "log_prior": m.get("log_prior"), "components": m["parts"], "termination": m["final"],
                                   "messages": m.get("messages"), "n_eval": m["nfev"], "wall_s": round(m["seconds"], 1) if m.get("seconds") is not None else None, "grad_norm_q": m.get("grad_norm_q"),
                                   "n_nonfinite": m.get("n_nonfinite"), "topology": e.get("topology"), "plausible": e.get("plausible"),
                                   "plausibility_notes": e.get("plausibility_notes"), "max_abs_shift_sigma": e.get("max_abs_shift_sigma")}
        lg = logs[name]
        pid = [int((CN / f"logs/{lg}.pid").read_text().strip())] if lg and (CN / f"logs/{lg}.pid").exists() else []
        conv = [ref(D / "run_card.json", "campaign run card"), ref(D / "multistart.json", "campaign multistart record")]
        if lg:
            conv.append(code_ref("crni-paper-fit-step4-s1", CN / f"logs/{lg}.log", "run log"))
        ids.append(write(card(
            f"crni-{name}", f"Cr-Ni {name}: {len(ms)} starts, pick {ev.get('pick', 'n/a')}", CRNI_SP, gstep, "complete" if role != "failed" else "failed",
            status_note=f"role in the specific protocol: {role}", host=rc["host"], hardware_class="Mac Studio M1 Max (10 cores)", pids=pid + ([rc["pid"]] if rc.get("pid") and rc.get("pid") not in pid else []),
            started=rc.get("started_utc", "2026-11-06"), finished=rc.get("finished_utc") or {"status": "pending", "reason": "not recorded"},
            interpreter=op.tilde(rc["python"]), packages={"espei": rc["espei_version"], "pycalphad": rc["pycalphad_version"]},
            command=f"cd {op.tilde(CN)} && " + ("EXTRA_STARTS=steps/configs/extra_step2.json " if name == "step2_liquidus" else "") + f"PYTHONPATH=<home>/src/PhaseForgePlus/src {FITPY} scripts/fit.py steps/configs/{name}.json {rc.get('nproc', 4)}; {FITPY} scripts/evaluate.py {name}" + (" s7_perturbed" if name == "step2_liquidus" else ""),
            threads=f"{rc.get('nproc', 4)} worker processes", config=rc["config"],
            seeds={"rule": "s0 = start TDB; s1..s7 a(1 + 0.1 N(0,1)) [+ N(0, 2 kJ) where a = 0], b + N(0, 3 J/K), seed 1000 + k (fit.py)", "starting_vectors": rc.get("starts")},
            inputs=inputs, outputs=outputs, results=results,
            trajectory={"status": "not_recorded", "reason": "fit.py of 6 Nov kept only theta0 and theta per start (multistart.json); the rerun agents now record trajectories"},
            ranking={"pick": ev.get("pick"), "rule": ev.get("pick_rule"), "order": ev.get("ranking")},
            converted_from=conv,
            notes=(["first step-2 launch stopped after 5 s (own PIDs) to remove SETUPTOOLS_SCM_PRETEND_VERSION; moved to attic/step2_stopped_version_string",
                    "the pick is s7_perturbed, the converged best start of the single mode; the mechanical ranker's s2 rested on a 1-temperature grid difference and |g| 0.011 (PLAN.md run log)"] if name == "step2_liquidus" else []) +
                  (["CRNI2 fixed at its one-shot value: broke the topology (CRNI2 stable to 1828 K, above the liquidus); reported, not continued; led to the PI rule 'held never means fixed'",
                    "first step-3 launch failed on a start-TDB file name (attic/step3_failed_start_tdb_name.log) and was relaxed"] if name == "step3_thermo" else []))))
    # Laplace mixture UQ
    U = CN / "results/uq"
    cl = json.loads((U / "classified_mixture_draws.json").read_text())
    lp = json.loads((U / "laplace_step4.json").read_text())
    ids.append(write(card(
        "crni-uq-laplace-step4", "Cr-Ni UQ: Laplace mixture at the step-4 modes, 1000 classified draws", CRNI_SP, "laplace", "complete",
        host=STUDIO, started="2026-11-06", finished="2026-11-06", pids=[int((CN / "logs/laplace.pid").read_text().strip())],
        interpreter=FITPY, packages={"espei": "0.8.11.dev82+g9039ea215"},
        command=f"cd {op.tilde(CN)} && PYTHONPATH=<home>/src/PhaseForgePlus/src {FITPY} scripts/laplace.py steps/configs/step4_solid.json results/uq/modes_step4.json results/uq/laplace_step4.json 1000 && {FITPY} scripts/classify_draws.py results/uq/laplace_step4.draws.npy results/uq/classified_mixture_draws.json",
        seeds={"draws": "numpy default_rng(20261106) for the mixture draws and default_rng(20261106) for the independent-marginal permutation (scripts/laplace.py lines 122 and 143)"},
        inputs=[ref(U / "modes_step4.json", "modes"), ref(CN / "steps/configs/step4_solid.json"), code_ref("crni-paper-fit-step4-s1", CN / "scripts/laplace.py"), code_ref("crni-paper-fit-step4-s1", CN / "scripts/classify_draws.py")],
        outputs=[ref(U / "laplace_step4.json"), ref(U / "laplace_step4.draws.npy"), ref(U / "classified_mixture_draws.json")],
        results={"modes": [{"name": m["name"], "logpost": m["logpost"], "positive_definite_fd": m.get("positive_definite_fd"), "log_evidence": m.get("log_evidence")} for m in lp["modes"]],
                 **{k: v for k, v in cl.items() if k != "draws"}},
        trajectory={"status": "not_recorded", "reason": "not a fit"}, converted_from=[code_ref("crni-paper-fit-step4-s1", CN / "logs/laplace.log", "run log"), ref(U / "laplace_step4.json")])))
    return ids


if __name__ == "__main__":
    ids = cuzr() + crni()
    changed = WRITES.commit()
    print(len(ids), "run cards:", ", ".join(ids), f"({len(changed)} changed)")
