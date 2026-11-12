"""Step-4 combined run (PI decisions 6 Nov, fit_protocol item 8): data for step4c.

ZPF: every row one ESPEI file, weight = 1000 / max(sigma_conv, tier) with sigma_conv the T2a conversion (results/zpf_sigma_conversion.json,
     ADOPTED as default) and tier from results/tiers3.json (100; 50 when replicated; Karmazin 550 C and Zhang 2014 at 100, labelled).
     Kinetic rule (PI: "maybe those experiments were not really at equilibrium and the intermetallic did not have time to precipitate"):
     bcc+fcc rows below 900 K at short-anneal or unstated-anneal states where Hao Fig. 16 reports CrNi2 (Jette 1934 797 K, Karmazin 1982
     826/875 K) enter as METASTABLE bcc+fcc equilibria with CRNI2 suspended: they go to data/zpf_susp/ and are evaluated by model2.py
     against the same TDB without the CRNI2 phase (same symbols). ESPEI's ZPF has no per-record phase switch; this is exact for these rows.
Hinge: results/tiers3 cells (per excluded phase; confidence 1.0; tau 100), minus the CRNI2 exclusions at states below 900 K where CrNi2
     is sluggish and the anneal is short or unstated (the 6 Jette/Karmazin ZPF-state cells and the 11 fcc Curie marks, 324-572 K).
One-shot: data/oneshot_relax (relaxation midpoint rule stays). Thermochemistry: data/thermo unchanged.
Writes data/liq_c, data/solid_c, data/zpf_susp, data/hinge/step4c_hinge.json, results/step4c_build.json."""
import copy
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
T_KIN = 900.0
TIER = {"certain": 10.0, "less_certain": 50.0, "uncertain": 100.0}


def main():
    conv = {(r["file"], r["row"]): r for r in json.loads((R / "results/zpf_sigma_conversion.json").read_text())["rows"]}
    t3 = {(z["file"], z["row"]): z for z in json.loads((R / "results/tiers3.json").read_text())["zpf_rows"]}
    log = {"zpf_rows": [], "suspended_rows": [], "dropped_crni2_exclusions": []}
    for g in ("liq", "solid"):
        (R / "data" / f"{g}_c").mkdir(parents=True, exist_ok=True)
    (R / "data/zpf_susp").mkdir(parents=True, exist_ok=True)
    for g in ("liq", "solid"):
        for f in sorted((R / "data" / g).glob("zpf*.json")):
            d = json.loads(f.read_text())
            for i, (T, row) in enumerate(zip(d["conditions"]["T"], d["values"])):
                key = (f"{g}/{f.name}", i)
                c, t = conv[key], t3[key]
                sig = max(c["sigma_DF"], TIER[t["tier"]])
                ps = sorted({v[0] for v in row})
                susp = (float(T) < T_KIN and set(ps) <= {"BCC_A2", "FCC_A1"} and ("jette1934" in f.name or "karmazin1982" in f.name))
                d1 = copy.deepcopy(d)
                d1["values"] = [row]
                d1["conditions"] = dict(d["conditions"], T=[T])
                d1["phases"] = ps
                d1["weight"] = 1000.0 / sig
                d1["comment"] = d.get("comment", "") + (f" | step4c: sigma_DF = max(converted {c['sigma_DF']:.0f}, tier {t['tier']} {TIER[t['tier']]:.0f}) = {sig:.0f} J/mol"
                                                         + ("; METASTABLE bcc+fcc, CRNI2 suspended (PI 6 Nov kinetic rule)" if susp else ""))
                dst = (R / "data/zpf_susp") if susp else (R / "data" / f"{g}_c")
                (dst / f"{f.stem}__r{i:03d}.json").write_text(json.dumps(d1, indent=1))
                rec = {"file": key[0], "row": i, "T": T, "phases": ps, "sigma_conv": c["sigma_DF"], "tier": t["tier"], "sigma_used": sig,
                       "weight": 1000.0 / sig, "floor_active": TIER[t["tier"]] > c["sigma_DF"], "suspended_CRNI2": susp}
                log["zpf_rows"].append(rec)
                if susp:
                    log["suspended_rows"].append(rec)
    H = json.loads((R / "data/hinge/step4_hinge_tiers3.json").read_text())
    for c in H["cells"]:
        o = c["orchid"]
        if "CRNI2" in c["penalize"] and c["T"] < T_KIN:
            src = str(o.get("dataset") or o.get("reference") or "")
            if any(s in src for s in ("jette1934", "karmazin1982", "Curie")):
                c["penalize"] = [p for p in c["penalize"] if p != "CRNI2"]
                c["sigma"] = {p: v for p, v in c["sigma"].items() if p != "CRNI2"}
                o["crni2_exclusion_dropped"] = ("PI 6 Nov: below 900 K CrNi2 is sluggish; anneal short or unstated"
                                                + ("; Hao Fig. 16 reports CrNi2 here" if "Curie" not in src else "") + "; CRNI2 exclusion not applied")
                log["dropped_crni2_exclusions"].append({"state": o.get("record") or f"{o.get('dataset')}#{o.get('index')}", "T": c["T"], "x": c["x"],
                                                        "expected": c["expected"], "remaining_penalize": c["penalize"]})
    H["cells"] = [c for c in H["cells"] if c["penalize"]]
    H["step4c_rule"] = "tiers3 per excluded phase; CRNI2 exclusions dropped below 900 K at kinetically limited states; smooth onset applied in model2.py"
    (R / "data/hinge/step4c_hinge.json").write_text(json.dumps(H, indent=1))
    from collections import Counter
    log["summary"] = {"zpf_rows": len(log["zpf_rows"]), "zpf_by_sigma_basis": dict(Counter("tier floor" if r["floor_active"] else "converted" for r in log["zpf_rows"])),
                      "zpf_by_tier": dict(Counter(r["tier"] for r in log["zpf_rows"])), "suspended_rows": len(log["suspended_rows"]),
                      "dropped_crni2_exclusions": len(log["dropped_crni2_exclusions"]), "hinge_cells": len(H["cells"]),
                      "exclusions_by_tier": dict(Counter(H_t for c in H["cells"] for H_t in [c["orchid"]["tiers"][p]["tier"] for p in c["penalize"]]))}
    (R / "results/step4c_build.json").write_text(json.dumps(log, indent=1, default=float))
    print(json.dumps(log["summary"], indent=1))
    for r in log["suspended_rows"]:
        print("suspended", r["file"][-40:], r["row"], r["T"])
    for r in log["dropped_crni2_exclusions"]:
        print("dropped CRNI2 excl", r["state"][:45], r["T"], round(r["x"], 3))


if __name__ == "__main__":
    main()
