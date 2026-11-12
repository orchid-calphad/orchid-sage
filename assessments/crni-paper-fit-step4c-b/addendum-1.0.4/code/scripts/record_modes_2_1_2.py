"""crni-paper-fit-step4c-b@1.0.4: re-record the Laplace mode list under the names the general modes command gives, as a new version
of the recorded file. Standard library only; nothing is refitted.

  record_modes_2_1_2.py REPO OUT_MODES_JSON PROOF_JSON

The `modes` step command of orchid-calphad-fit@2.1.2 is run VERBATIM from the YAML (interpreter replaced by this one, <step> by
step4c_b_hingefloor, the tolerance placeholder by the 10b tolerances of the specific protocol) on the recorded multistart
(evidence reference_outputs/steps/step4c_b_hingefloor/multistart.json) in a fresh temporary directory. Its output is written,
byte for byte, to OUT_MODES_JSON. The proof checks that the modes are those of the recorded modes_step4c_b.json (1.0.0, hand
labels A_s4 / A2_s5_flat): same number, same starts, theta bit-identical in order. Only the names differ (A_s4_perturbed /
B_s5_perturbed) and three fields are added (start, logpost, grad_norm_q); laplace3.py reads name and theta only, so the
mixture weights cannot change. A strict comparison of a rerun of the command on the recorded multistart with this file is
therefore exact (names included)."""
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(sys.argv[1]).resolve(); OUT = Path(sys.argv[2]); PROOF = Path(sys.argv[3])
sys.path.insert(0, str(REPO / "protocols/tools"))
import orchidproto as op  # noqa: E402

EV = REPO / "assessments/crni-paper-fit-step4c-b/evidence/reference_outputs"
MS = EV / "steps/step4c_b_hingefloor/multistart.json"
REC = EV / "results/uq/modes_step4c_b.json"
GEN = REPO / "protocols/general/orchid-calphad-fit@2.1.2.yaml"
TOL = [0.03 if i % 2 else 50.0 for i in range(14)]   # 10b: 50 J/mol a-terms (even VV), 0.03 J/mol/K b-terms (odd VV)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


g = op.load_doc(GEN)
st = next(s for sec in g["sections"] for s in sec["steps"] if s["id"] == "modes")
cmd = st["tool"]["command"].replace("<fit-python>", sys.executable).replace("<step>", "step4c_b_hingefloor")
cmd = re.sub(r"'<mode_tolerances[^>]*>'", "'" + json.dumps(TOL) + "'", cmd)
d = Path(tempfile.mkdtemp()); (d / "steps/step4c_b_hingefloor").mkdir(parents=True); (d / "results/uq").mkdir(parents=True)
shutil.copy(MS, d / "steps/step4c_b_hingefloor/multistart.json")
subprocess.run(cmd, shell=True, cwd=d, check=True)
produced = d / "results/uq/modes_step4c_b_hingefloor.json"
got, rec, ms = json.loads(produced.read_text()), json.loads(REC.read_text()), json.loads(MS.read_text())
start_of = lambda th: next(x["start"] for x in ms if x["theta"] == th)  # noqa: E731
same = len(got) == len(rec) and all(a["theta"] == b["theta"] for a, b in zip(got, rec))
if not same:
    raise SystemExit("the 2.1.2 command does not reproduce the recorded modes; nothing written")
if OUT.exists() and OUT.read_bytes() != produced.read_bytes():
    raise SystemExit(f"FROZEN: {OUT} exists with different content")
OUT.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(produced, OUT)
PROOF.write_text(json.dumps({
    "general_protocol": "orchid-calphad-fit@2.1.2", "general_sha256": sha(GEN), "command": cmd.replace(sys.executable, "PY"),
    "multistart": str(MS.relative_to(REPO)), "multistart_sha256": sha(MS), "recorded_modes": str(REC.relative_to(REPO)), "recorded_sha256": sha(REC),
    "new_modes": str(OUT.relative_to(REPO)) if OUT.is_relative_to(REPO) else str(OUT), "new_sha256": sha(OUT),
    "names_recorded": [m["name"] for m in rec], "names_new": [m["name"] for m in got],
    "starts_recorded": [start_of(m["theta"]) for m in rec], "starts_new": [m["start"] for m in got],
    "theta_bit_identical_in_order": same, "fields_new": sorted(got[0]), "fields_recorded": sorted(rec[0]),
    "note": "laplace3.py reads name and theta only; the weights depend on theta only (seeded draws, default_rng(20261106))"}, indent=1))
print("modes", [m["name"] for m in got], "theta identical to recorded:", same)
