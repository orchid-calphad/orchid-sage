"""General-protocol modes command (2.1.2, and 2.1.1 for contrast) run VERBATIM from the YAML on the recorded Cr-Ni step-4c-b
multistart (evidence bundle reference_outputs copy), compared with the recorded modes_step4c_b.json (which mode starts, theta
bit-identical). Standard library only.
  modes_check.py REPO OUT_JSON"""
import json, re, shutil, subprocess, sys, tempfile
from pathlib import Path
REPO = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(REPO / "protocols/tools"))
import orchidproto as op  # noqa: E402
EV = REPO / "assessments/crni-paper-fit-step4c-b/evidence/reference_outputs"
rec = json.loads((EV / "results/uq/modes_step4c_b.json").read_text())
ms = json.loads((EV / "steps/step4c_b_hingefloor/multistart.json").read_text())
TOL = [0.03 if i % 2 else 50.0 for i in range(14)]   # 10b: 50 J/mol a-terms (even VV), 0.03 J/mol/K b-terms (odd VV)
out = {"multistart": str((EV / "steps/step4c_b_hingefloor/multistart.json").relative_to(REPO)), "multistart_sha256": op.sha256_file(EV / "steps/step4c_b_hingefloor/multistart.json"),
       "recorded_modes": str((EV / "results/uq/modes_step4c_b.json").relative_to(REPO)), "tolerances": TOL, "versions": {}}
for ver in ("2.1.1", "2.1.2"):
    g = op.load_doc(REPO / f"protocols/general/orchid-calphad-fit@{ver}.yaml")
    st = next(s for sec in g["sections"] for s in sec["steps"] if s["id"] == "modes")
    cmd = st["tool"]["command"].replace("<fit-python>", sys.executable).replace("<step>", "step4c_b_hingefloor")
    cmd = re.sub(r"'<mode_tolerances[^>]*>'", "'" + json.dumps(TOL) + "'", cmd)
    d = Path(tempfile.mkdtemp()); (d / "steps/step4c_b_hingefloor").mkdir(parents=True); (d / "results/uq").mkdir(parents=True)
    shutil.copy(EV / "steps/step4c_b_hingefloor/multistart.json", d / "steps/step4c_b_hingefloor/multistart.json")
    subprocess.run(cmd, shell=True, cwd=d, check=True)
    got = json.loads((d / "results/uq/modes_step4c_b_hingefloor.json").read_text())
    starts = [next(x["start"] for x in ms if x["theta"] == m["theta"]) for m in got]
    rec_starts = [next(x["start"] for x in ms if x["theta"] == m["theta"]) for m in rec]
    same = len(got) == len(rec) and all(a["theta"] == b["theta"] for a, b in zip(got, rec))
    out["versions"][ver] = {"command": cmd.replace(sys.executable, "PY"), "n_modes": len(got), "names": [m["name"] for m in got], "starts": starts,
                            "recorded_names": [m["name"] for m in rec], "recorded_starts": rec_starts, "theta_bit_identical_to_recorded_in_order": same}
Path(sys.argv[2]).write_text(json.dumps(out, indent=1))
for v, r in out["versions"].items():
    print(v, r["n_modes"], r["starts"], "recorded", r["recorded_starts"], "identical", r["theta_bit_identical_to_recorded_in_order"])
