"""Step-4 hinge sidecar data/hinge/step4_hinge.json (PhaseForge+ hinge; protocol 0, item 8 and 0.4).

1. set E cells (290; cr-ni-rebuild set D rule, option C: sigma 1000, tau 100, confidence 0.5), unchanged, except that CRNI2 (now a
   model phase, stable elsewhere in Cr-Ni below ~863 K) is added to `penalize` at states with T >= 895 K (863 K + 2 sigma_eff of
   ORC-X3KVP7D3PO), where it is not stable by that record; below 895 K CRNI2 is not excluded.
2. NEW (labelled crni-paper-fit-20261106): BCC_A2 exclusions at observed single-phase fcc states.
   a. Pugliese & Fitterer 1970 activity states inside the gamma field by the paper's own Table III gamma limits (x_Cr below the
      limit at the same T): expected FCC_A1; penalize BCC_A2, LIQUID, CRNI2 (T >= 895 K). Assumed from the source's limits: option C.
   b. fcc Curie-temperature marks (Hao et al. 2021 Fig. 13(a); experimental, cited sources; single reader) at T >= 298.15 K:
      expected FCC_A1; penalize the export's stable_elsewhere list (BCC_A2, CRNI2, LIQUID); option C.
"""
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
SR = Path.home() / "ScientificRuns"
SETE = SR / "cr-ni-rebuild-20261105/inputs/derived/setE_orchid_sigmas/hinge/CR-NI/cr-ni-model.json"
PUG = Path.home() / "data/private/crni-pugliese-export-20261105/records.jsonl"
HAO = Path.home() / "data/private/crni-assessment-export-20261105/records.jsonl"
SIG, TAU, CONF = 1000.0, 100.0, 0.5
T_CRNI2 = 863.0 + 2 * 16.0
TAG = "crni-paper-fit-20261106 new"


def main():
    E = json.loads(SETE.read_text())
    cells, log = [], {"setE": 0, "setE_crni2_added": 0, "pugliese_gamma": [], "curie": []}
    for c in E["cells"]:
        c = json.loads(json.dumps(c))
        if c["T"] >= T_CRNI2 and "CRNI2" not in c["expected"]:
            c["penalize"] = list(c["penalize"]) + ["CRNI2"]
            c["orchid"]["crni2_added"] = f"{TAG}: CRNI2 stable elsewhere (below ~863 K, ORC-X3KVP7D3PO), not at T >= {T_CRNI2:.0f} K"
            log["setE_crni2_added"] += 1
        cells.append(c)
        log["setE"] += 1
    recs = [json.loads(l) for l in PUG.read_text().splitlines()]
    lim = {round(r["temperature_K"], 2): next(p["composition"]["CR"] for p in r["phase_compositions"] if p["phase"] == "γ")
           for r in recs if r["property"] == "PHASE_COMPOSITION"}
    for r in recs:
        if r["property"] != "ACR_CR":
            continue
        T = round(r["temperature_K"], 2)
        xcr = r["overall_composition"]["CR"]
        if T in lim and xcr < lim[T] - 1e-9:
            pen = ["BCC_A2", "LIQUID"] + (["CRNI2"] if T >= T_CRNI2 else [])
            cells.append({"T": T, "x": round(1 - xcr, 6), "expected": ["FCC_A1"], "penalize": pen, "sigma": SIG, "confidence": CONF,
                          "orchid": {"record": r["id"], "reference": "pugliese1970 (doi:10.1007/bf02642800) Table II state",
                                     "relation": "stable_elsewhere", "basis": f"assumed: phase from the same paper's Table III gamma limit "
                                     f"x_Cr {lim[T]} at {T} K (Table II prints no phase per row); option C", "label": TAG}})
            log["pugliese_gamma"].append([T, round(1 - xcr, 4), r["id"]])
    for l in HAO.read_text().splitlines():
        r = json.loads(l)
        ph = [p.get("model_phase") for p in (r.get("phases") or [])]
        if r["property"] == "TRANSITION_TEMPERATURE" and ph == ["FCC_A1"] and r["value"] >= 298.15:
            pen = sorted(e["model_phase"] for e in r["excluded_phases"] if e.get("model_phase"))
            cells.append({"T": round(r["value"], 2), "x": round(r["overall_composition"]["NI"], 6), "expected": ["FCC_A1"],
                          "penalize": pen, "sigma": SIG, "confidence": CONF,
                          "orchid": {"record": r["id"], "reference": "Hao et al. 2021 Fig. 13(a) fcc Curie mark, measured in "
                                     f"{r['origin'].get('measured_in')}", "relation": "stable_elsewhere",
                                     "basis": "export excluded_phases (paper's phase list); single reader; option C", "label": TAG}})
            log["curie"].append([round(r["value"], 1), round(r["overall_composition"]["NI"], 4), r["id"]])
    out = {"system": "CR-NI", "tdb": "tdb/step1_oneshot.tdb", "element": "NI", "margin_J_per_mol_atom": TAU,
           "sigma_J_per_mol_atom": SIG, "confidence_option_C": CONF, "cells": cells, "build": log}
    (R / "data/hinge").mkdir(parents=True, exist_ok=True)
    (R / "data/hinge/step4_hinge.json").write_text(json.dumps(out, indent=1))
    print(len(cells), {k: (v if isinstance(v, int) else len(v)) for k, v in log.items()})
    print("pugliese", log["pugliese_gamma"]); print("curie", log["curie"])


if __name__ == "__main__":
    main()
