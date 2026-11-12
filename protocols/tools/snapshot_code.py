#!/usr/bin/env python3
"""Byte-identical snapshot of the code that produced each pick, into assessments/<artifact>/code/, with MANIFEST.json
mapping every copy to its original path, sha256 and mtime. Sources are only read.  python3 protocols/tools/snapshot_code.py
Campaign directories: runs_root of local/config.json; the Spark copy of the Cu-Zr run-1 fit scripts: cuzr_run1_spark_scripts
(local/config.json); host names: local/config.json (machine label spark1). Original paths are recorded with ~ for the home."""
import hashlib, json, os, shutil, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import localpaths  # noqa: E402
import frozen  # noqa: E402
REPO = Path(__file__).resolve().parents[2]; RUNS = localpaths.setting("runs_root"); SP1 = localpaths.host("spark1")
def h(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def tl(p): return localpaths.tilde(p)
CZ = RUNS / "cuzr-protocol-oneshot-20261106"; CN = RUNS / "crni-paper-fit-20261106"; CN1 = RUNS / "crni-phaseforge-20261105"
_snap = localpaths.config().get("cuzr_run1_spark_scripts")
SNAP = localpaths._path(_snap) if _snap else REPO / "data" / "cuzr_run1_spark_scripts"   # scp -p of the DGX Spark (spark1) run-1 fit/scripts/*.py taken 6 Nov 07:47 CST, before run 2 re-syncs it; the copies are in commit 94cc153
PLAN = {
 "cuzr-oneshot-h2-s7": [
  # (dest, source, used_for, note)
  *[(f"scripts/{p.name}", p, "fit, rank, evaluate (run 1)", f"{SP1} copy synced at 04:25 CST for the run-1 fits ({SP1}:<home>/runs/cuzr-protocol-oneshot-20261106/fit/scripts/); the Studio copy was edited for run 2 afterwards" if p.name in ("fit_step.py", "judge.py") else f"{SP1} run-1 copy")
    for p in sorted(SNAP.glob("*.py")) if p.name != "rank_protocol.py"],
  ("scripts/rank_protocol.py", CZ / "scripts/rank_protocol.py", "ranking on the Studio (run 1, 05:17 CST)", f"Studio copy, mtime 05:16 CST, i.e. the version that ranked run 1; the {SP1} copy (04:25) is older"),
  (f"scripts/rank_protocol.{SP1}_0425.py", SNAP / "rank_protocol.py", "superseded", "older ranking key, kept for the record"),
  *[(f"code/{n}", CZ / "code" / n, "one-shot (run 1)", "") for n in ("gen_sqs.py", "relax_solids.py", "launch_solids.sh", "collect.sh", "attic_build_oneshot_run1.py", "run_step.sh", "compare_oneshots.py", "relax_solids_crni_source.py", "analyze_solids_crni_source.py")],
  ("code/cuzr-fresh/Dockerfile", None, "MLIP image recipe", f"copied from {SP1}:<home>/runs/cuzr-fresh-phaseforge-20261104/code/Dockerfile"),
  *[(f"records/{n}", CZ / n, "campaign record (frozen copy)", "") for n in ("PLAN.md", "REPORT.md", "logs/launch_fits.tsv", f"logs/{SP1}/launch_solids.tsv", f"logs/{SP1}/potential_sha256.txt")],
 ],
 "crni-paper-fit-step4-s1": [
  *[(f"scripts/{n}", CN / "scripts" / n, "fit sequence, checks, UQ", "") for n in ("make_base.py", "build_data.py", "pd4.py", "build_hinge.py", "evaluate.py", "data_consistency.py", "fig_steps.py", "laplace.py", "summarize.py", "physics.py", "per_dataset.py", "classify_draws.py")],
  ("scripts/style.py", localpaths.sibling("2026_arroyave_nicr_paper") / "scripts/style.py", "figure style imported by evaluate.py and fig_steps.py", "copied from the Cr-Ni paper repo; evaluate.py inserts that path first, so a staged root without it falls back to this copy"),
  ("scripts/fit.py", CN / "scripts/fit.py", "multistart fit", "EDITED 06:55 CST by the rerun agent (per-evaluation trajectory recording) AFTER the step-4 fit (04:47-05:16); the pre-edit file was not retained. Equivalence is tested by the independent rerun (G)."),
  ("scripts/model.py", CN / "scripts/model.py", "objective", "EDITED 06:55 CST with fit.py (component bookkeeping for the trajectory); pre-edit file not retained; see fit.py note"),
  *[(f"oneshot_code/{n}", CN1 / "code" / n, "one-shot", "") for n in ("gen_sqs.py", "gen_sqs_fullrange.py", "relax_solids.py", "relax_solids_v2.py", "run_liquid.py", "launch_liquid.sh", "collect.sh", "analyze_solids.py", "analyze_liquid.py", "build_tdb.py")],
  *[(f"records/crni-paper-fit/{n}", CN / n, "campaign record (frozen copy)", "") for n in ("PLAN.md", "REPORT.md", "logs/step2.log", "logs/step3.log", "logs/step3b.log", "logs/step4.log", "logs/laplace.log")],
  *[(f"records/crni-phaseforge/{n}", CN1 / n, "campaign record (frozen copy)", "") for n in ("PLAN.md", "results/NOT_USED.md", "provenance/potential_sha256.txt")],
 ],
 # Cr-Ni step-4 pick step4c-b (PI 6 Nov 2026): the launch-time snapshot code_used/step4c_b_hingefloor/ (copied by fit2.py at launch) plus
 # the data builders upstream of it (scripts/, read only); steps 1-3b code is in the crni-paper-fit-step4-s1 snapshot
 "crni-paper-fit-step4c-b": [
  *[(f"scripts/{p.name}", p, "step 4c-b fit, data build, checks, UQ (launch-time copy)", "code_used/step4c_b_hingefloor/ (copied at launch, 6 Nov 17:25 UTC)")
    for p in sorted((CN / "code_used/step4c_b_hingefloor").glob("*.py"))],
  *[(f"scripts/{n}", CN / "scripts" / n, "data build upstream of step 4c-b", "live scripts/ copy (not in the launch snapshot)")
    for n in ("build_data.py", "build_hinge.py", "build_hinge_observed.py", "build_tiers.py", "build_tiers2.py", "data_consistency.py", "model.py", "fit.py", "make_base.py", "classify_draws.py", "summarize.py")
    if not (CN / "code_used/step4c_b_hingefloor" / n).exists()],
  ("scripts/style.py", localpaths.sibling("2026_arroyave_nicr_paper") / "scripts/style.py", "figure style imported by evaluate.py", "copied from the Cr-Ni paper repo"),
  *[(f"records/crni-paper-fit/{n}", CN / n, "campaign record (frozen copy)", "") for n in ("logs/step4c_b_hingefloor.log",) if (CN / n).exists()],
 ],
 # crni-paper-fit-step4c-b@1.0.0 (6 Nov evening): 10a kink-rule checks and the 10c global search, plus their run-card emitter; a separate
 # addendum snapshot so that the 0.2.0-draft snapshot (and its pinned MANIFEST) stays frozen
 "crni-paper-fit-step4c-b/addendum-1.0.0": [
  *[(f"scripts/{n}", CN / "scripts" / n, "10a kink-rule check / 10c global search (1.0.0)", f"live scripts/ copy as run on the Studio and {SP1}")
    for n in ("kink10a.py", "check10a.py", "check10a_ms.py", "run_global_crni.py", "emit_run_cards_10ac.py", "emit_run_cards_10ac_v2.py")],
  *[(f"records/crni-paper-fit/{n}", CN / n, "campaign record (frozen copy, 1.0.0)", "") for n in ("logs/10c_basin_7201.log", "logs/10c_anneal_7201.log") if (CN / n).exists()],
 ],
}
if sys.argv[1:]:   # snapshot only the named artifacts (default: all)
    PLAN = {k: v for k, v in PLAN.items() if k in sys.argv[1:]}
if "cuzr-oneshot-h2-s7" in PLAN and not SNAP.is_dir():
    raise SystemExit(f"snapshot source {SNAP} (cuzr_run1_spark_scripts) missing: the frozen cuzr-oneshot-h2-s7 snapshot is kept unchanged")
for art, items in PLAN.items():
    root = REPO / "assessments" / art / "code"; man = []
    for dest, src, used, note in items:
        d = root / dest; d.parent.mkdir(parents=True, exist_ok=True)
        if src is None:
            if not d.exists():
                os.system(f"scp -q -p {localpaths.host('spark1_ssh')}:<home>/runs/cuzr-fresh-phaseforge-20261104/code/Dockerfile '{d}'")
            src_disp = f"{SP1}:<home>/runs/cuzr-fresh-phaseforge-20261104/code/Dockerfile"; mt = None
        else:
            if d.exists() and h(d) != h(src):
                raise SystemExit(f"FROZEN: {d} differs from its live source {src}; the snapshot is never overwritten (make a new snapshot version instead)")
            if not d.exists():
                shutil.copy2(src, d)
            src_disp = tl(src) if not str(src).startswith(str(SNAP)) else f"{SP1}:<home>/runs/cuzr-protocol-oneshot-20261106/fit/scripts/" + Path(src).name
            mt = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(Path(src).stat().st_mtime))
        man.append({"path": dest, "sha256": h(d), "original": src_disp, "original_mtime": mt, "used_for": used, "note": note})
    old = json.loads((root / "MANIFEST.json").read_text()) if (root / "MANIFEST.json").exists() else {}
    frozen.write(root / "MANIFEST.json", json.dumps({"artifact": art, "created": old.get("created", time.strftime("%Y-%m-%dT%H:%M:%S%z")), "rule": "byte-identical copies of the code that produced the pick; sources only read", "files": man}, indent=1), "snapshot_code.py")
    print(art, len(man), "files")
