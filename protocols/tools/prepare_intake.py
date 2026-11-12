#!/usr/bin/env python3
"""Prepare (NOT deliver) the ORCHID intake of an assessment's evidence for the next release (v2027.01).
  python3 prepare_intake.py assessments/<artifact> [--version V] [--bundle B]
Writes assessments/<artifact>/intake/intake_manifest.json and README.md (or, with --version V, intake_manifest@V.json and
README@V.md) listing what must enter ORCHID so the evidence is citable by release: (1) ORC ids used but absent from the Y25
registry; (2) dataset files without any ORC id (e.g. Cr-Ni set E); (3) campaign-added exclusions (hinge cells) with their basis
and certainty tier; (4) computed observations (one-shot MLIP energies, liquid S_ex) with produced_by = the specific protocol;
versioned manifests also list (5) the ZPF records with their compositions and the tiers the fit used. Status of every item:
prepared (not delivered). The evidence bundle read is MANIFEST@B.json (--bundle), else the latest version.

Frozen (7 Nov 2026, crni-paper-fit-step4c-b@1.0.4): an intake manifest a specific protocol pins is never overwritten. If the
output file exists and its content differs (the `created` date aside), nothing is written and the script exits 2; build a new
--version instead. (Until 7 Nov this script rewrote intake_manifest.json on every run, so the pinned intake of an assessment
changed whenever its bundle did.)"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import frozen  # noqa: E402
A = Path(sys.argv[1]); E = A / "evidence"
V = sys.argv[sys.argv.index("--version") + 1] if "--version" in sys.argv else None
B = sys.argv[sys.argv.index("--bundle") + 1] if "--bundle" in sys.argv else None
_v = sorted(E.glob("MANIFEST@*.json"), key=lambda p: tuple(int(x) for x in p.stem.split("@")[1].split(".")))
mp = (E / f"MANIFEST@{B}.json") if B else (_v[-1] if _v else E / "MANIFEST.json")
M = json.loads(mp.read_text())
S = json.loads((E / (f"states@{M['version']}.json" if "@" in mp.name else "states.json")).read_text())
unmapped = sorted({i for f in M["files"] for i in f.get("unmapped_orchid_ids", [])})
no_ids = [f["path"].split("/")[-1] for f in M["files"] if f["kind"] == "espei_dataset" and f.get("orchid_link", "missing" if not f["orchid_ids"] else "present") == "missing"]
excl = [{"source_file": s["source_file"], "row": s["row"], "T_K": s["T_K"], "x": s["x"], "expected": s["expected"], "excluded": s.get("excluded"),
         "basis": s.get("exclusion_basis"), "exclusions": s.get("exclusions"), "orchid_ids": s.get("orchid_ids"), "state_ids": s.get("state_ids"),
         **({"observed_state": s["observed_state"]} if V and "observed_state" in s else {}),
         **({k: s[k] for k in ("phase_assignment", "second_reading") if V and s.get(k)})} for s in S["states"] if s.get("source") == "hinge"]
comp = [f["path"] for f in M["files"] if f["kind"] == "oneshot_observations"]
out = {"artifact": A.name, "target_release": "v2027.01", "status": "prepared, NOT delivered (needs PI go and the coordinator's review)",
       "created": time.strftime("%Y-%m-%d"), "evidence_bundle": {"version": M.get("version"), "bundle_sha256": M.get("bundle_sha256")},
       "link_coverage": M.get("link_coverage"),
       "items": {"orc_ids_not_in_registry": unmapped, "datasets_without_orchid_ids": no_ids, "campaign_added_exclusions": excl,
                 "computed_observations": [{"file": c, "produced_by": f"specific protocol of {A.name}"} for c in comp]},
       "counts": {"orc_ids_not_in_registry": len(unmapped), "datasets_without_orchid_ids": len(no_ids), "campaign_added_exclusions": len(excl), "computed_observation_files": len(comp)}}
if V:
    out = {"version": V, **out}
    out["items"]["zpf_records"] = [{"source_file": s["source_file"], "T_K": s["T_K"], "x": s["x"], "element": s.get("element"), "vertices": s.get("vertices"),
                                    "expected": s["expected"], "zpf_certainty": s.get("zpf_certainty"), "orchid_ids": s.get("orchid_ids")}
                                   for s in S["states"] if s.get("source") == "zpf"]
    out["counts"]["zpf_records"] = len(out["items"]["zpf_records"])
d = A / "intake"; d.mkdir(exist_ok=True)
mf = d / (f"intake_manifest@{V}.json" if V else "intake_manifest.json")
if mf.exists():
    old = json.loads(mf.read_text())
    if {k: v for k, v in old.items() if k != "created"} == {k: v for k, v in out.items() if k != "created"}:
        print(A.name, "unchanged:", mf.name); sys.exit(0)
    print(f"FROZEN: {mf} exists with different content; nothing written (build a new --version)"); sys.exit(2)
W = frozen.Writes("prepare_intake.py")   # manifest and README: all or none
W.add(mf, json.dumps(out, indent=1))
W.add(d / (f"README@{V}.md" if V else "README.md"),
    f"# ORCHID intake for {A.name} (prepared, not delivered)" + (f", version {V}" if V else "") + "\n\n"
    + (f"Evidence bundle {M.get('version')} (`{mp.name}`). " if V else "")
    + f"Target release v2027.01 (freeze 15 Jan 2027). Counts: {json.dumps(out['counts'])}.\n\n"
    "Delivery: export each item through the orchid-data-next contribution tools (schema and id generator), review, then merge into `next`. "
    "Records from private exports enter as derived facts with their source DOI, page and a quote of at most 500 characters; no publisher text is copied here.\n")
W.commit()
print(A.name, mf.name, json.dumps(out["counts"]))
