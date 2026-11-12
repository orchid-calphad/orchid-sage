"""crni-paper-fit-step4c-b@1.0.1: the 10a pick of a rerun, named by the rule and never by a start label, and its comparison with the
recorded pick. Read only (standard library); nothing is refitted.

  pick10a.py CHECK10A_JSON EVALUATION_JSON STEP_DIR REFERENCE_PICK_TDB REFERENCE_MODES_JSON OUT_JSON OUT_TDB OUT_START_TXT TOL_A TOL_B

1. The pick is the one check10a_ms.py already made by fit_protocol 10a: among the eligible starts (smooth or kink-stationary, every
   on-boundary data point within its own uncertainty, no failed equilibrium), the highest objective. It is read from CHECK10A_JSON
   ("pick"); its start name is written to OUT_START_TXT (for the 10c item) and its TDB (STEP_DIR/<pick>.tdb, written by evaluate.py)
   is copied byte for byte to OUT_TDB (for the diagram, pure-element and phase-sequence items).
2. Predictions of the pick: objective and 10a kind (CHECK10A_JSON), topology, eutectic (T_liquid_min) and CrNi2 top (T_CrNi2_max)
   from EVALUATION_JSON.
3. Parameters (fit_protocol 10b): every VVnnnn of OUT_TDB against REFERENCE_PICK_TDB, absolute tolerance TOL_A on a-terms (even
   VV index) and TOL_B on b-terms (odd index). A symbol is UNDETERMINED at these tolerances when the two recorded minima of the same
   basin (REFERENCE_MODES_JSON: the main mode and its flat neighbour, theta in VV order) differ by more than its tolerance; such a
   symbol is reported with its difference, never as a failure. Every other symbol must lie within its tolerance, and every non-VV,
   non-comment line of the two TDBs must be identical.
"""
import json
import re
import shutil
import sys
from pathlib import Path

VV = re.compile(r"FUNCTION\s+(VV\d{4})\s+298\.15\s+([-+.\dEe]+);")


def vv(tdb):
    return {m.group(1): float(m.group(2)) for m in VV.finditer(Path(tdb).read_text())}


def other_lines(tdb):
    return [ln for ln in Path(tdb).read_text().splitlines() if not re.match(r"\s*FUNCTION\s+VV\d{4}\s", ln) and not ln.startswith("$")]


def main():
    c10a, evf, step_dir, ref_tdb, modes_f, out_json, out_tdb, out_txt = sys.argv[1:9]
    tol_a, tol_b = float(sys.argv[9]), float(sys.argv[10])
    c = json.loads(Path(c10a).read_text())
    pick = c.get("pick")
    out = {"rule": "fit_protocol 10a: eligible starts (smooth or kink-stationary, on-boundary points within own sigma, no failed equilibria), "
                   "then the highest objective (scripts/check10a_ms.py); never a start label",
           "check10a": str(Path(c10a)), "pick": pick, "n_eligible": c.get("n_eligible"), "kinds": c.get("kinds")}
    if pick is None:
        out["pick_found"] = False
        Path(out_json).write_text(json.dumps(out, indent=1))
        sys.exit("no eligible start: 10a pick undefined (reported, never loosened)")
    row = next(r for r in c["rows"] if r["start"] == pick)
    ev = next(e for e in json.loads(Path(evf).read_text())["evaluations"] if e["start"] == pick)
    src = Path(step_dir) / f"{pick}.tdb"
    Path(out_tdb).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, out_tdb)
    Path(out_txt).write_text(pick + "\n")
    tol = lambda k: tol_b if int(k[2:]) % 2 else tol_a  # noqa: E731
    A, B = vv(ref_tdb), vv(out_tdb)
    modes = json.loads(Path(modes_f).read_text())
    names = sorted(A)
    m0, m1 = modes[0]["theta"], modes[1]["theta"]
    flat = {k for i, k in enumerate(names) if abs(m0[i] - m1[i]) > tol(k)}
    params, outside_det, outside_undet = {}, [], []
    for k in names:
        d = B[k] - A[k]
        st = "undetermined" if k in flat else ("within" if abs(d) <= tol(k) else "outside")
        params[k] = {"reference": A[k], "rerun": B[k], "diff": d, "tol": tol(k), "diff_over_tol": abs(d) / tol(k), "status": st}
        if st == "outside":
            outside_det.append(k)
        if k in flat and abs(d) > tol(k):
            outside_undet.append(k)
    near = {m["name"]: max(abs(B[k] - m["theta"][i]) / tol(k) for i, k in enumerate(names)) for m in modes}
    out.update({
        "pick_found": True, "pick_logpost": row["logpost"], "pick_kind": row["kind"], "pick_eligible": row["eligible"],
        "pick_n_boundary_points": row["n_boundary_points"], "pick_n_failed_equilibria": row["n_failed_equilibria"],
        "gap_to_runner_up": c.get("gap_to_runner_up"),
        "topology": {k: ev["topology"].get(k) for k in ("ok", "n_bad", "T_liquid_min", "T_CrNi2_max", "spurious_severity")},
        "T_liquid_min": ev["topology"]["T_liquid_min"], "T_CrNi2_max": ev["topology"]["T_CrNi2_max"],
        "pick_tdb": {"source": str(src), "copy": str(out_tdb)},
        "parameters": {"reference_tdb": str(ref_tdb), "reference_modes": str(modes_f), "tol_a": tol_a, "tol_b": tol_b,
                       "undetermined_rule": "symbols where the two recorded minima of the basin (" + " and ".join(m["name"] for m in modes)
                                            + ") differ by more than the 10b tolerance; reported, not failed",
                       "undetermined": sorted(flat), "undetermined_beyond_tol": outside_undet,
                       "determined_outside_tol": outside_det, "determined_within_tol": not outside_det,
                       "max_determined_diff_over_tol": max((p["diff_over_tol"] for k, p in params.items() if k not in flat), default=0.0),
                       "max_diff_over_tol_to_each_recorded_mode": near, "symbols": params},
        "other_tdb_lines_identical": other_lines(ref_tdb) == other_lines(out_tdb),
    })
    Path(out_json).write_text(json.dumps(out, indent=1))
    print("10a pick", pick, "logpost %.7f" % row["logpost"], row["kind"], "Teut", out["T_liquid_min"], "TCrNi2", out["T_CrNi2_max"],
          "determined within tol", not outside_det, "undetermined", sorted(flat), "nearest mode", min(near, key=near.get))


if __name__ == "__main__":
    main()
