#!/usr/bin/env python3
"""Expected vs calculated phase assemblage at every observed state of an evidence bundle (protocol step evaluate_states).

  PYTHON evaluate_states.py PICK.tdb states.json OUT.json [--nproc 4]       (needs pycalphad; e.g. fit_python of local/config.json)

For each state (T, overall x of the bundle's element, P = 101325 Pa) one pycalphad equilibrium over every phase of the TDB
(default point density, phases with fraction > 1e-6 counted). States without a composition are skipped and listed.
match = (calculated phase set == expected phase set). Partial tie lines (a vertex without composition) are evaluated at
the known vertex's composition, so they are also scored as `contains_expected` (the known phase is present).
Deterministic: same TDB + states + pycalphad build -> same output (no random sampling)."""
import json
import sys
import time
from multiprocessing import get_context
from pathlib import Path


def _init(tdb):
    global DB, PHASES, COMPS
    from pycalphad import Database
    DB = Database(tdb)
    PHASES = sorted(DB.phases)
    COMPS = sorted(c for c in DB.elements if c not in ("/-",))


def _one(args):
    i, T, x, el = args
    import warnings
    warnings.filterwarnings("ignore")
    from pycalphad import equilibrium, variables as v
    try:
        eq = equilibrium(DB, COMPS, PHASES, {v.T: T, v.P: 101325, v.N: 1, v.X(el): x})
        ph = eq.Phase.values.ravel(); nf = eq.NP.values.ravel()
        got = sorted({str(p) for p, f in zip(ph, nf) if p and f == f and f > 1e-6})
        return i, got, None
    except Exception as e:  # noqa: BLE001
        return i, None, str(e)[:200]


def main():
    tdb, sj, out = sys.argv[1], sys.argv[2], sys.argv[3]
    nproc = int(sys.argv[sys.argv.index("--nproc") + 1]) if "--nproc" in sys.argv else 4
    S = json.loads(Path(sj).read_text())
    states = S["states"]
    jobs, skipped = [], []
    for i, s in enumerate(states):
        x = s.get("x")
        if x is None and s.get("kind") == "partial_tie_line":
            known = [vx for _, vx in s.get("vertices", []) if vx is not None]
            x = known[0] if known else None
        if x is None or not (0 < x < 1):
            skipped.append(i); continue
        jobs.append((i, float(s["T_K"]), min(max(float(x), 1e-6), 1 - 1e-6), s["element"]))
    t0 = time.time()
    with get_context("spawn").Pool(nproc, initializer=_init, initargs=(tdb,)) as pool:
        res = dict((i, (g, e)) for i, g, e in pool.map(_one, jobs, chunksize=4))
    rows = []
    for i, s in enumerate(states):
        g, e = res.get(i, (None, "skipped: no composition" if i in skipped else None))
        exp = s["expected"]
        rows.append({"index": i, "source_file": s["source_file"], "row": s["row"], "kind": s["kind"], "T_K": s["T_K"], "x": s.get("x"),
                     "expected": exp, "calculated": g, "match": (g == exp) if g is not None else None,
                     "contains_expected": (set(exp) <= set(g)) if g is not None else None,
                     "excluded_present": sorted(set(s.get("excluded", [])) & set(g or [])) or None,
                     "orchid_ids": s.get("orchid_ids", []), "state_ids": s.get("state_ids", []),
                     "zpf_certainty": s.get("zpf_certainty") or ({"certainty_tier": s["certainty_tier"]} if s.get("certainty_tier") else None),
                     "exclusions": s.get("exclusions"), "error": e})
    import pycalphad
    ok = [r for r in rows if r["match"] is not None]
    summary = {"n_states": len(rows), "evaluated": len(ok), "match": sum(r["match"] for r in ok), "contains_expected": sum(r["contains_expected"] for r in ok),
               "excluded_phase_present": sum(1 for r in ok if r["excluded_present"]), "skipped": len(rows) - len(ok),
               "by_kind": {k: {"n": sum(1 for r in ok if r["kind"] == k), "match": sum(1 for r in ok if r["kind"] == k and r["match"])} for k in sorted({r["kind"] for r in ok})}}
    # path-independent output (SCHEMA_GAPS G1): only base names and content hashes, never the argument paths
    import hashlib
    Path(out).write_text(json.dumps({"tdb": Path(tdb).name, "tdb_sha256": hashlib.sha256(Path(tdb).read_bytes()).hexdigest(),
                                     "states": Path(sj).name, "states_sha256": hashlib.sha256(Path(sj).read_bytes()).hexdigest(),
                                     "pycalphad": pycalphad.__version__, "summary": summary, "rows": rows}, indent=1))
    print(json.dumps(summary), "wall_s", round(time.time() - t0, 1), file=sys.stderr)


if __name__ == "__main__":
    main()
