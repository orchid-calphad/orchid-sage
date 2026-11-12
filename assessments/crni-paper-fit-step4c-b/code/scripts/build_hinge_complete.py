"""Complete the step-4 exclusions by the rule now required at every observed state (PI 6 Nov; protocol 0, item 8):
phases stable elsewhere in Cr-Ni (BCC_A2, FCC_A1, LIQUID, CRNI2) but not in the observed state are excluded, option C
(sigma 1000, tau 100, confidence 0.5), labelled `crni-paper-fit-20261106 completion`.

Starts from data/hinge/step4_hinge.json (set E 290 cells with CRNI2 added at T >= 895 K, 17 Pugliese gamma, 11 Curie) and:
 1. audits every observed experimental state of the step-4 data (ZPF rows, liquid thermochemistry, HM_FORM, Pugliese activities,
    the eutectic and CrNi2 ordering records, the Curie marks) for a cell;
 2. adds CRNI2 to the cells of states below 895 K that lack it (stable elsewhere; the observation lists other phases);
 3. adds cells for the Pugliese rows not yet covered: alpha-field rows (x_Cr above the paper's Table III alpha limit: expected
    BCC_A2) and two-phase rows (between the limits: expected BCC_A2 + FCC_A1 with the Table III limits as tie-line ends),
    penalizing LIQUID and CRNI2 (T >= 895 K for CRNI2 is not required here: CRNI2 is not in these states at any T);
 4. lists the states that still lack a cell and why (rule 0.4a liquid thermochemical states not above every liquidus observation;
    hinge limits: three expected phases, stoichiometric expected phase without a partner composition; T < 298.15 K).
Writes data/hinge/step4_hinge_complete.json and results/exclusion_audit.json."""
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
SR = Path.home() / "ScientificRuns"
CH = SR / "cr-ni-rebuild-20261105/inputs/chapter-input-data"
SETD_LOG = SR / "cr-ni-rebuild-20261105/inputs/derived/setD_twophase_hinge/BUILD_LOG.json"
PUG = Path.home() / "data/private/crni-pugliese-export-20261105/records.jsonl"
HAO = Path.home() / "data/private/crni-assessment-export-20261105/records.jsonl"
SIG, CONF = 1000.0, 0.5
TAG = "crni-paper-fit-20261106 completion"
MODEL = ["BCC_A2", "CRNI2", "FCC_A1", "LIQUID"]


def main():
    H = json.loads((R / "data/hinge/step4_hinge.json").read_text())
    cells = H["cells"]
    audit = {"states": [], "added": {"crni2_to_existing": 0, "pugliese_alpha": [], "pugliese_two_phase": []}, "lacking": []}
    keyed = {}
    for c in cells:
        o = c.get("orchid", {})
        k = (o.get("dataset") or o.get("record"), o.get("index"))
        keyed.setdefault(k, []).append(c)
    # 2. CRNI2 at states below 895 K (set E cells)
    for c in cells:
        if "CRNI2" not in c["penalize"] and "CRNI2" not in c["expected"] and c["T"] >= 298.15:
            c["penalize"] = list(c["penalize"]) + ["CRNI2"]
            c.setdefault("orchid", {})["crni2_added"] = f"{TAG}: CRNI2 stable elsewhere, not in the observed state (T {c['T']} K)"
            audit["added"]["crni2_to_existing"] += 1
    # 1. audit ZPF parents (chapter-input-data) and set E thermochemistry
    for f in sorted(CH.glob("zpf_*.json")):
        d = json.loads(f.read_text())
        for i, _ in enumerate(d["values"]):
            ok = bool(keyed.get((f.name, i)))
            audit["states"].append({"dataset": f.name, "index": i, "has_cells": ok})
            if not ok:
                audit["lacking"].append({"dataset": f.name, "index": i, "reason": "no cell (unexpected)"})
    logD = json.loads(SETD_LOG.read_text())["hinge"]
    for s in logD.get("liquid_states_without_exclusion", []):
        audit["lacking"].append({"dataset": s["dataset"], "index": s["index"], "T": s["T"], "x_Ni": s["x_Ni"],
                                 "reason": "rule 0.4a: liquid thermochemical state not above every liquidus observation at that composition ("
                                           + s["reason"] + "); no exclusion added"})
    # 3. Pugliese rows
    recs = [json.loads(l) for l in PUG.read_text().splitlines()]
    lim = {}
    for r in recs:
        if r["property"] == "PHASE_COMPOSITION":
            pc = {p["phase"]: p["composition"]["CR"] for p in r["phase_compositions"]}
            lim[round(r["temperature_K"], 2)] = (pc["α"], pc["γ"])
    have = {c.get("orchid", {}).get("record") for c in cells}
    for r in recs:
        if r["property"] != "ACR_CR" or r["id"] in have:
            continue
        T = round(r["temperature_K"], 2)
        if T not in lim:
            continue
        a, g = lim[T]
        xcr = r["overall_composition"]["CR"]
        base = {"sigma": SIG, "confidence": CONF}
        if xcr > a + 1e-9:
            c = {"T": T, "x": round(1 - xcr, 6), "expected": ["BCC_A2"], "penalize": ["CRNI2", "FCC_A1", "LIQUID"], **base}
            audit["added"]["pugliese_alpha"].append([T, round(1 - xcr, 4), r["id"]])
            rel = "alpha field by Table III alpha limit"
        else:
            c = {"T": T, "x": round(1 - xcr, 6), "expected": ["BCC_A2", "FCC_A1"], "tie_line": {"BCC_A2": round(1 - a, 4), "FCC_A1": round(1 - g, 4)},
                 "penalize": ["CRNI2", "LIQUID"], **base}
            audit["added"]["pugliese_two_phase"].append([T, round(1 - xcr, 4), r["id"]])
            rel = "between Table III alpha and gamma limits (two-phase), tie-line ends = the limits"
        c["orchid"] = {"record": r["id"], "reference": "pugliese1970 Table II state", "relation": "stable_elsewhere",
                       "basis": f"assumed: phase(s) from the same paper's Table III limits ({rel}); option C", "label": TAG}
        cells.append(c)
    # 4. other observed states
    for l in HAO.read_text().splitlines():
        r = json.loads(l)
        ph = [p.get("model_phase") for p in (r.get("phases") or [])]
        if r["property"] == "TRANSITION_TEMPERATURE" and ph == ["FCC_A1"] and r["value"] < 298.15:
            audit["lacking"].append({"record": r["id"], "T": r["value"], "reason": "fcc Curie mark below 298.15 K (SGTE unaries not valid); no cell"})
    audit["lacking"].append({"record": "ORC-SV7H3CNRYS", "reason": "eutectic: three expected phases; the hinge takes one or two (CRNI2 excluded at 1618 K by the neighbouring cells)"})
    audit["lacking"].append({"record": "ORC-X3KVP7D3PO", "reason": "CRNI2 ordering at 863 K: a stoichiometric expected phase needs a partner with a known "
                             "tie-line end (fcc composition not printed); LIQUID/BCC_A2 exclusions not formed"})
    H["cells"] = cells
    H["build_completion"] = {k: (v if isinstance(v, int) else len(v)) for k, v in audit["added"].items()}
    (R / "data/hinge/step4_hinge_complete.json").write_text(json.dumps(H, indent=1))
    audit["n_cells"] = len(cells)
    audit["n_zpf_parent_states"] = sum(1 for s in audit["states"])
    audit["n_zpf_parent_states_without_cells"] = sum(1 for s in audit["states"] if not s["has_cells"])
    (R / "results/exclusion_audit.json").write_text(json.dumps(audit, indent=1))
    print(len(cells), H["build_completion"], "zpf parent states", audit["n_zpf_parent_states"], "without cells", audit["n_zpf_parent_states_without_cells"])
    print("lacking:", len(audit["lacking"]))
    for x in audit["lacking"][:6]:
        print("  ", x)


if __name__ == "__main__":
    main()
