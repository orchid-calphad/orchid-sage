"""crni-paper-fit-step4c-b@1.0.1: thermochemistry of the rerun's 10a pick against the recorded pick (standard library only).

  thermo_compare.py RERUN_PER_DATASET_JSON REFERENCE_PER_DATASET_JSON OUT_JSON TOL_Z [GROUP=thermo]

Both inputs are per_dataset.py outputs (residual / sigma per dataset file). Every reference dataset of GROUP (the thermochemistry
files: calorimetry and activities, data/thermo/) must be present in the rerun, and its rms_z must agree within TOL_Z, i.e. the
rms residual within TOL_Z of the dataset's own uncertainty. Other groups present in either file are listed, not judged.
"""
import json
import sys
from pathlib import Path


def main():
    a, b, out, tol = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
    group = sys.argv[5] if len(sys.argv) > 5 else "thermo"
    A, B = json.loads(Path(a).read_text()), json.loads(Path(b).read_text())
    keys = sorted(k for k in B if k.split("/")[0] == group)
    missing = [k for k in keys if k not in A]
    rows = []
    for k in keys:
        if k in A:
            rows.append({"dataset": k, "type": B[k]["type"], "n": B[k]["n"], "rms_z_reference": B[k]["rms_z"], "rms_z_rerun": A[k]["rms_z"],
                         "diff_rms_z": A[k]["rms_z"] - B[k]["rms_z"], "diff_rms_residual": A[k]["rms_residual"] - B[k]["rms_residual"],
                         "n_equal": A[k]["n"] == B[k]["n"]})
    worst = max((abs(r["diff_rms_z"]) for r in rows), default=None)
    res = {"rule": f"every reference dataset of group {group!r} present, same number of points, |delta rms_z| <= {tol}", "group": group,
           "n_reference": len(keys), "n_compared": len(rows), "missing": missing, "all_present": not missing,
           "all_n_equal": all(r["n_equal"] for r in rows), "max_abs_diff_rms_z": worst, "tol_z": tol,
           "within_tol": bool(rows) and not missing and all(r["n_equal"] for r in rows) and worst <= tol,
           "not_judged": sorted({k.split("/")[0] for k in set(A) | set(B)} - {group}),
           "rows": sorted(rows, key=lambda r: -abs(r["diff_rms_z"]))}
    Path(out).write_text(json.dumps(res, indent=1))
    print("thermochemistry", group, "compared", len(rows), "of", len(keys), "max |d rms_z|", worst, "within", res["within_tol"])


if __name__ == "__main__":
    main()
