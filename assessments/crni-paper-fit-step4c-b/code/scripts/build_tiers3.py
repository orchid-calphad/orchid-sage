"""Certainty tiers PER EXCLUDED PHASE (fit_protocol items 8 and 10a, PI decisions 6 Nov; supersedes build_tiers.py).
Implemented here because the orchid-sage bundle classifier (build_evidence_bundle.py classify_certainty) had not yet been
changed to this rule at launch time (file dated 08:26 CST, per-state rule).

Exclusion of phase p at an observed state s (sigma_T, sigma_x of s):
  P_p = observed points where p is present: the known-composition vertices of every ZPF row whose phase set contains p, every
        observed state whose expected (present) phases contain p (hinge-cell states: thermochemistry, Pugliese, Curie, ZPF states),
        and, for tiering only (not fitted), the Hao et al. 2021 Fig. 16 records whose phase set contains p (CrNi2+bcc / CrNi2+fcc
        marks and the CrNi2 ordering marks with a composition; single-reader extraction, experimental).
  d = min over P_p of sqrt(((T - T_b)/sigma_T)^2 + ((x - x_b)/sigma_x)^2)
  d <= 1: 100 (adjacent, or a source reports p at the state: contested);  1 < d <= 3: 50;  d > 3: 10, except single-source states
  (Pugliese: phase from the paper's own Table III limits) -> 50.  Diagram-assumed exclusions: 100 (none here: all at observed states).
ZPF records (phases present): 100 for boundary / tie-line records; 50 when replicated by an independent source (another source's
  known vertex of the same phase set within 1 sigma of a known vertex of this row). One ESPEI file per row, weight = 1000 / tier.
State uncertainties: Curie marks: record sigma_effective (K) and 0.011; others ORCHID 'unknown' class T 16 K, x 0.011.
Observed states: confidence 1.0; tau 100.
PI ruling 6 Nov (source caveats, linkage readers): Karmazin 1982 p. 255 (gamma/(gamma+alpha) below 572 C probably not at
equilibrium; the 550 C row, ORC-SI5MM4H42G) and Zhang 2014 (interface compositions never called equilibrium compositions; the
tie-line reading is the dataset's) stay in the fit at the weakest tier, 100 J/mol-atom, labelled with the authors' caveat
(rows and the exclusions at those states).
Outputs: data/hinge/step4_hinge_tiers3.json, data/liq_tier3/, data/solid_tier3/, results/tiers3.json (+ states3.json)."""
CAVEAT = {("karmazin1982lattice", 826.0): "Karmazin 1982 p. 255: boundary below 572 C probably not at equilibrium (ORC-SI5MM4H42G); PI 6 Nov: weakest tier",
          ("zhang2014impurity", None): "Zhang 2014: interface compositions not stated to be equilibrium; tie-line reading is the dataset's; PI 6 Nov: weakest tier"}


def caveat(name, T):
    for (src, Tc), why in CAVEAT.items():
        if src in name and (Tc is None or abs(float(T) - Tc) < 1.0):
            return why
    return None
import copy
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model

R = model.RUN
HAO = Path.home() / "data/private/crni-assessment-export-20261105/records.jsonl"
TIER = {"certain": 10.0, "less_certain": 50.0, "uncertain": 100.0}
SRC_OF = lambda name: name.replace("zpf_single_", "zpf_").split("-")[-1].replace(".json", "")


def zpf_points():
    pts = []   # (phase_set, phase, T, x, source, file, row)
    for g in ("liq", "solid"):
        for f in sorted((R / "data" / g).glob("zpf*.json")):
            d = json.loads(f.read_text())
            for i, (T, row) in enumerate(zip(d["conditions"]["T"], d["values"])):
                ps = tuple(sorted(v[0] for v in row))
                for v in row:
                    if v[2][0] is not None:
                        x = v[2][0] if v[1] == ["NI"] else 1 - v[2][0]
                        pts.append((ps, v[0], float(T), float(x), SRC_OF(f.name), f"{g}/{f.name}", i))
    return pts


def hao_points():
    pts = []
    for l in HAO.read_text().splitlines():
        r = json.loads(l)
        ph = [p.get("model_phase") for p in (r.get("phases") or [])]
        if "CRNI2" not in ph or r.get("temperature_K") is None:
            continue
        xs = [pc["composition"]["NI"] for pc in (r.get("phase_compositions") or [])]
        if r.get("overall_composition"):
            xs.append(r["overall_composition"]["NI"])
        for x in xs:
            for p in ph:
                pts.append((p, float(r["temperature_K"]), float(x), r["id"]))
    return pts


def main():
    Z = zpf_points()
    HP = hao_points()
    H0 = json.loads((R / "data/hinge/step4_hinge_complete.json").read_text())
    curie = {}
    for l in HAO.read_text().splitlines():
        r = json.loads(l)
        if r["property"] == "TRANSITION_TEMPERATURE":
            curie[r["id"]] = r["uncertainty_budget"]["quantities"]["value"]["sigma_effective"]
    # presence points per phase
    pres = {}
    for ps, ph, T, x, src, f, i in Z:
        for p in ps:
            pres.setdefault(p, []).append((T, x, f"ZPF {src} ({'+'.join(ps)})"))
    for c in H0["cells"]:
        for p in c["expected"]:
            pres.setdefault(p, []).append((c["T"], c["x"], "observed state " + str(c["orchid"].get("record") or c["orchid"].get("dataset"))[:40]))
    for p, T, x, rid in HP:
        pres.setdefault(p, []).append((T, x, f"Hao 2021 Fig.16 {rid} (tiering only)"))
    cells, rows = [], []
    for c in H0["cells"]:
        o = c.get("orchid", {})
        rec = o.get("record")
        sT, sx = (curie[rec], 0.011) if rec in curie else (16.0, 0.011)
        sig, basis = {}, {}
        cvs = caveat(str(o.get("dataset", "")), c["T"])
        for p in c["penalize"]:
            best = (math.inf, None)
            for T, x, lab in pres.get(p, []):
                d = math.hypot((c["T"] - T) / sT, (c["x"] - x) / sx)
                if d < best[0]:
                    best = (d, lab)
            d, lab = best
            if d <= 1:
                tier, why = "uncertain", f"{p} present within 1 sigma ({d:.2f}; {lab})"
            elif d <= 3:
                tier, why = "less_certain", f"{p} present within 3 sigma ({d:.2f}; {lab})"
            else:
                tier, why = "certain", f"nearest presence of {p} at {d:.1f} sigma ({lab})"
                if "pugliese" in str(o.get("reference", "")):
                    tier, why = "less_certain", why + "; single source (Pugliese Table III limits)"
            if cvs:
                tier, why = "uncertain", why + "; " + cvs
            sig[p] = TIER[tier]
            basis[p] = {"tier": tier, "distance_sigma": None if d == math.inf else round(d, 3), "basis": why}
            rows.append({"state": rec or f"{o.get('dataset')}#{o.get('index')}", "T": c["T"], "x": c["x"], "expected": c["expected"],
                         "excluded": p, "tier": tier, "sigma_J": TIER[tier], "distance_sigma": None if d == math.inf else d, "basis": why})
        c2 = copy.deepcopy(c)
        c2["sigma"] = sig
        c2["confidence"] = 1.0
        c2["orchid"] = dict(o, tiers=basis, tier_rule="per excluded phase (fit_protocol 8/10a, PI 6 Nov)")
        cells.append(c2)
    H = dict(H0, cells=cells, tier_rule="per excluded phase: 10 / 50 / 100 J/mol-atom; confidence 1.0; tau 100")
    (R / "data/hinge/step4_hinge_tiers3.json").write_text(json.dumps(H, indent=1, default=float))
    # ZPF rows
    zrows = []
    for g in ("liq", "solid"):
        dst = R / "data" / f"{g}_tier3"
        dst.mkdir(parents=True, exist_ok=True)
        for f in sorted((R / "data" / g).glob("zpf*.json")):
            d = json.loads(f.read_text())
            src = SRC_OF(f.name)
            for i, (T, row) in enumerate(zip(d["conditions"]["T"], d["values"])):
                ps = tuple(sorted(v[0] for v in row))
                known = [(v[0], v[2][0] if v[1] == ["NI"] else 1 - v[2][0]) for v in row if v[2][0] is not None]
                rep = []
                for ph, x in known:
                    for ps2, ph2, T2, x2, src2, f2, i2 in Z:
                        if src2 != src and ps2 == ps and ph2 == ph and math.hypot((T - T2) / 16.0, (x - x2) / 0.011) <= 1.0:
                            rep.append(f"{src2} row {i2}")
                tier = "less_certain" if rep else "uncertain"
                cv = caveat(f.name, T)
                if cv:
                    tier, rep = "uncertain", rep + [cv]
                d1 = copy.deepcopy(d)
                d1["values"] = [row]
                d1["conditions"] = dict(d["conditions"], T=[T])
                d1["phases"] = sorted(set(ps))
                d1["weight"] = 1000.0 / TIER[tier]
                d1["comment"] = d.get("comment", "") + f" | tier {tier} ({TIER[tier]:.0f} J/mol): " + (f"replicated by {sorted(set(rep))[:3]}" if rep else "boundary record, not replicated")
                (dst / f"{f.stem}__r{i:03d}.json").write_text(json.dumps(d1, indent=1))
                zrows.append({"file": f"{g}/{f.name}", "row": i, "T": T, "phases": list(ps), "tier": tier, "sigma_J": TIER[tier], "replicated_by": sorted(set(rep))})
    summ = {"rule": "per excluded phase (own implementation; orchid-sage classifier not yet updated at launch)",
            "exclusions_by_tier": dict(Counter(r["tier"] for r in rows)),
            "exclusions_by_phase_and_tier": {p: dict(Counter(r["tier"] for r in rows if r["excluded"] == p)) for p in ("BCC_A2", "FCC_A1", "LIQUID", "CRNI2")},
            "states": len(cells), "zpf_rows_by_tier": dict(Counter(z["tier"] for z in zrows))}
    states = {"rule": summ["rule"], "states": [{"T": c["T"], "x": c["x"], "expected": c["expected"], "excluded": c["penalize"],
                                                "tiers": c["orchid"]["tiers"], "orchid": {k: v for k, v in c["orchid"].items() if k != "tiers"}} for c in cells],
              "zpf_rows": zrows}
    (R / "results/states3.json").write_text(json.dumps(states, indent=1, default=float))
    (R / "results/tiers3.json").write_text(json.dumps({"summary": summ, "exclusions": rows, "zpf_rows": zrows}, indent=1, default=float))
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
