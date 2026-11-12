"""crni-paper-fit-step4c-b@1.0.4: a new version of the hinge sidecar the fit read, with the exclusion basis label corrected to
the observed-state basis. Record fix only: nothing the objective reads changes. Standard library only.

  relabel_hinge_observed.py HINGE_IN.json HINGE_OUT.json PROOF_OUT.json

Why. All 366 cells of data/hinge/step4c_hinge_floor.json sit at OBSERVED states and enter at confidence 1.0 with the hinge floor
(build_tiers3.py: "Diagram-assumed exclusions: 100 (none here: all at observed states)"; build_hinge_observed.py: "exclusions at
OBSERVED states enter at confidence 1.0 ... option C stays only for exclusions assumed from a diagram at non-observed states (none
in this hinge)"). The cells still carry the basis text of their first build, set D/E option C (sigma 1000, tau 100, confidence
0.5): "assumed_from_diagram (option C)" on 290 set E cells, "...; option C" on 76 campaign cells. Those builders changed sigma
and confidence but never the label, and the evidence bundle (1.0.0, 1.1.0) read the stale label as "not an observed state".

What changes (in each cell's `orchid` block only, never a key the objective reads):
  basis            -> "observed state: ..." (the basis the fit applied)
  observed_state   -> true (new, explicit; the bundle reads it instead of parsing the text)
  basis_superseded -> the old text, kept verbatim
  phase_assignment -> for the 76 campaign cells whose old text also said how the present phase was assigned (Pugliese
                      Table III limits, export phase lists), that text without "option C"; it is an interpretation of the
                      expected phase, not of the exclusion, and stays labelled
  second_reading   -> for the three Dench 1963 50 at.% Cr HM_FORM states (cells 246-248), the disagreement of the second
                      reading (single- vs two-phase), kept as fitted (PI, 7 Nov 2026)
and one top-level block `relabel` naming this script, the input sha256 and the rule.
Proof (PROOF_OUT): (1) the projection the objective reads (model3.GradTarget: cells[*] keys T, x, expected, sigma, tie_line,
confidence, penalize; element; margin_J_per_mol_atom) serialises to identical bytes; (2) every number, boolean and null anywhere in the
file, as (JSON path, repr), is identical (the added label keys left out); (3) the files are equal once the changed and
added label keys are removed.
"""
import hashlib
import json
import sys
from pathlib import Path

FIT_KEYS = ("T", "x", "expected", "sigma", "tie_line", "confidence", "penalize")
ADDED = ("observed_state", "basis_superseded", "phase_assignment", "second_reading")
BASIS = ("observed state: exclusion at a state where the phases present were observed; confidence 1.0, tau = margin 100 J/mol-atom, "
         "sigma = max(per-excluded-phase tier, converted state uncertainty) (fit_protocol item 8; build_tiers3.py, build_hinge_observed.py, "
         "build_step4c_floor.py)")
DENCH = {8: ("ORC-ULZ3WSQMGP", "ORC-CWXWUTWKUD"), 9: ("ORC-SX7CMLVTNV", "ORC-4LB5RWNK6H"), 10: ("ORC-YU2SE3QZOA", "ORC-DXELDQEPGJ")}
DENCH_FILE = "non-equilibrium-thermochemical_FCC_A1_HM_CR-NI-HM_FORM-FCC_A1-dench1963adiabatic.json"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def fit_projection(h):
    return {"element": h["element"], "margin_J_per_mol_atom": h["margin_J_per_mol_atom"],
            "cells": [{k: c[k] for k in FIT_KEYS if k in c} for c in h["cells"]]}


def scalars(o, path="$", skip=()):
    if isinstance(o, dict):
        for k in sorted(o):
            if k not in skip:
                yield from scalars(o[k], f"{path}.{k}", skip)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from scalars(v, f"{path}[{i}]", skip)
    elif isinstance(o, bool) or isinstance(o, (int, float)) or o is None:
        yield (path, repr(o))


def strip(h, keys):
    h = json.loads(json.dumps(h))
    for c in h["cells"]:
        for k in keys:
            c["orchid"].pop(k, None)
    h.pop("relabel", None)
    return h


def main():
    src, dst, proof = map(Path, sys.argv[1:4])
    raw = src.read_bytes(); h0 = json.loads(raw)
    h = json.loads(raw)
    n_set_e = n_camp = 0
    for i, c in enumerate(h["cells"]):
        o = c["orchid"]
        old = str(o.get("basis", ""))
        if not (c.get("confidence") == 1.0 and ("option C" in old or old.startswith("assumed"))):
            raise SystemExit(f"cell {i}: unexpected basis/confidence {old!r} {c.get('confidence')!r}; not relabelled")
        o["basis_superseded"] = old
        o["basis"] = BASIS
        o["observed_state"] = True
        if old != "assumed_from_diagram (option C)":
            o["phase_assignment"] = old.replace("; option C", "").strip()
            n_camp += 1
        else:
            n_set_e += 1
        if o.get("dataset") == DENCH_FILE and o.get("index") in DENCH:
            orc, second = DENCH[o["index"]]
            o["second_reading"] = {"status": "disagree", "on": "phase",
                                   "dataset": "FCC_A1 single phase (this cell: FCC_A1 expected, BCC_A2 excluded)",
                                   "paper": "Dench 1963 p. 1288 (PDF 10): alloys heterogeneous between 49 and 66 at.% Cr at 1265 C, i.e. two-phase",
                                   "value_agrees": True, "record_ids": [orc], "second_reading_id": second,
                                   "source": "<home>/data/private/crni-ill-second-reading-20261106/comparison.csv (restricted; hash only)",
                                   "decision": "kept as fitted, noted in the record; corrected in ORCHID v2027.01 (PI, 7 Nov 2026)"}
    h["relabel"] = {"by": "assessments/crni-paper-fit-step4c-b/addendum-1.0.4/code/scripts/relabel_hinge_observed.py",
                    "version": "1.1.0", "input": "data/hinge/step4c_hinge_floor.json", "input_sha256": sha(raw),
                    "rule": "label fix only (crni-paper-fit-step4c-b@1.0.4, 7 Nov 2026): every cell is at an observed state; basis set to the "
                            "observed-state basis the fit applied, old text kept in basis_superseded; no key the objective reads changes",
                    "counts": {"cells": len(h["cells"]), "set_e_option_c": n_set_e, "campaign_with_phase_assignment": n_camp,
                               "dench_second_reading_disagree": sum(1 for c in h["cells"] if "second_reading" in c["orchid"])}}
    out = json.dumps(h, indent=1).encode()
    # proof
    p0, p1 = json.dumps(fit_projection(h0), sort_keys=True).encode(), json.dumps(fit_projection(json.loads(out)), sort_keys=True).encode()
    s0 = list(scalars(h0)); s1 = list(scalars(json.loads(out), skip=("relabel",) + ADDED))
    eq_rest = strip(h0, ("basis",)) == strip(json.loads(out), ("basis",) + ADDED)
    ok = p0 == p1 and s0 == s1 and eq_rest
    pr = {"input": str(src), "input_sha256": sha(raw), "output": str(dst), "output_sha256": sha(out),
          "fit_projection_keys": list(FIT_KEYS) + ["element", "margin_J_per_mol_atom"],
          "fit_projection_sha256": {"input": sha(p0), "output": sha(p1)}, "fit_projection_bytes_identical": p0 == p1,
          "n_scalars_compared": len(s0), "scalars_identical": s0 == s1,
          "n_sigma_values": sum(len(c["sigma"]) for c in h0["cells"]), "n_cells": len(h0["cells"]),
          "rest_identical_without_label_keys": eq_rest, "changed_keys": ["cells[*].orchid.basis"], "added_keys": [f"cells[*].orchid.{k}" for k in ADDED] + ["relabel"],
          "counts": h["relabel"]["counts"], "ok": ok}
    if not ok:
        proof.write_text(json.dumps(pr, indent=1)); raise SystemExit("proof failed: numeric content differs (nothing written)")
    if dst.exists() and dst.read_bytes() != out:
        raise SystemExit(f"FROZEN: {dst} exists with different content")
    dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(out)
    proof.write_text(json.dumps(pr, indent=1))
    print(json.dumps({k: pr[k] for k in ("fit_projection_bytes_identical", "scalars_identical", "n_scalars_compared", "rest_identical_without_label_keys", "counts", "ok")}))


if __name__ == "__main__":
    main()
