#!/usr/bin/env python3
"""Pick the start of a fit step by the protocol rule (fit_protocol item 10a, PI 6 Nov 2026). Standard library only.

  python3 pick_start.py STEP_DIR [--threshold 1e-3] [--out pick.json]

1. Eligible: converged, i.e. gradient norm in the optimiser's scaled coordinates below the threshold stated in the plan
   before fitting (default 1e-3). Cr-Ni fit.py records it as `grad_norm_q` in multistart.json.
2. Among eligible starts the ranking classes of fit_protocol 0.3 apply when the campaign evaluation recorded them
   (plausible, then right topology, from steps/<step>/evaluation.json); within a class the start with the highest
   objective wins. Near-ties are broken by the objective, never by grid quantities.
3. If no start is eligible the result says so (pick = null). The threshold is never loosened.
Deterministic: same inputs -> same output (ties on the objective fall back to the start name)."""
import json
import sys
from pathlib import Path


def main():
    a = sys.argv; d = Path(a[1])
    thr = float(a[a.index("--threshold") + 1]) if "--threshold" in a else 1e-3
    out = Path(a[a.index("--out") + 1]) if "--out" in a else d / "pick_protocol_10a.json"
    ms = json.loads((d / "multistart.json").read_text())
    ev = {}
    if (d / "evaluation.json").exists():
        ev = {e["start"]: e for e in json.loads((d / "evaluation.json").read_text()).get("evaluations", [])}
    rows = []
    for m in ms:
        g = m.get("grad_norm_q")
        e = ev.get(m["start"], {})
        rows.append({"start": m["start"], "objective": m["logpost"], "grad_norm_q": g, "eligible": g is not None and g < thr,
                     "plausible": e.get("plausible"), "topology_ok": (e.get("topology") or {}).get("ok"),
                     "no_wrong_temperatures": ((e.get("topology") or {}).get("n_bad") == 0) if e.get("topology") else None})
    el = [r for r in rows if r["eligible"]]
    # topology CLASS first (0.3): fully right, then 'no wrong temperatures on the declared range' (a categorical test, not a
    # count compared between starts), then the objective; no finer grid quantity is ever used to break a tie (10a)
    key = lambda r: (bool(r["plausible"]), bool(r["topology_ok"]), bool(r["no_wrong_temperatures"]), r["objective"], r["start"])  # noqa: E731
    pick = max(el, key=key) if el else None
    res = {"step": d.name, "rule": "fit_protocol 10a: eligible if grad_norm_q < threshold; rank plausible, topology class (ok; no wrong temperatures), then objective (no grid tie-breaks)",
           "threshold": thr, "n_starts": len(rows), "n_eligible": len(el), "pick": pick["start"] if pick else None,
           "pick_objective": pick["objective"] if pick else None,
           "note": None if pick else "no start converged below the threshold; the threshold is not loosened (PI rule): refit with tighter convergence or report",
           "starts": sorted(rows, key=lambda r: -r["objective"])}
    out.write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ("step", "threshold", "n_starts", "n_eligible", "pick", "pick_objective")}))


if __name__ == "__main__":
    main()
