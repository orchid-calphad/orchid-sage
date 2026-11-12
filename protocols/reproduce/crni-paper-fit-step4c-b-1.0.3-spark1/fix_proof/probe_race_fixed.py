"""Q40 fix proof (2): the race can no longer drop data.
NPROC spawned processes; each loops ITER times. Even-numbered processes do what model3.GradTarget does for zpf_susp
(Database.from_string(model3.no_crni2_text(start_tdb))); odd-numbered processes, when MIX is set, do what model2 did (rewrite the
shared cache file data/cache/<start>_noCRNI2.tdb with Path.write_text, then Database(path)) - the hostile writer and a positive
control in the same run. Counts reads with no phases, with fewer than the 3 expected phases, and parse errors, per process.
  probe_race_fixed.py ROOT NPROC ITER [MIX]"""
import sys
from multiprocessing import get_context
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
NPROC, ITER = int(sys.argv[2]), int(sys.argv[3])
MIX = len(sys.argv) > 4 and sys.argv[4] == "MIX"


def loop(i):
    sys.path.insert(0, str(ROOT / "scripts"))
    from pycalphad import Database
    tdb = ROOT / "tdb/step3b_thermo_crni2free_pick.tdb"
    use_old = MIX and i % 2 == 1
    if use_old:
        import model2 as m
        build = lambda: Database(m.no_crni2_tdb(tdb))  # noqa: E731
    else:
        import model3 as m
        build = lambda: Database.from_string(m.no_crni2_text(tdb), fmt="tdb")  # noqa: E731
    n_empty = n_partial = n_err = 0
    for _ in range(ITER):
        try:
            n = len(build().phases)
            n_empty += n == 0
            n_partial += 0 < n < 3
        except Exception:  # noqa
            n_err += 1
    return {"proc": i, "code": "model2 (shared file)" if use_old else "model3 (in memory)", "iter": ITER, "empty": n_empty,
            "partial": n_partial, "parse_error": n_err}


if __name__ == "__main__":
    import json
    with get_context("spawn").Pool(NPROC) as p:
        rows = p.map(loop, range(NPROC))
    for r in rows:
        print(r)
    new = [r for r in rows if r["code"].startswith("model3")]
    s = {"nproc": NPROC, "iter": ITER, "mix": MIX, "rows": rows,
         "model3_reads": sum(r["iter"] for r in new), "model3_bad": sum(r["empty"] + r["partial"] + r["parse_error"] for r in new),
         "model2_reads": sum(r["iter"] for r in rows if r not in new),
         "model2_bad": sum(r["empty"] + r["partial"] + r["parse_error"] for r in rows if r not in new)}
    print("SUMMARY", json.dumps({k: v for k, v in s.items() if k != "rows"}))
    print("JSON", json.dumps(s))
