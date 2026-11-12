"""Q40 probe: the write/read race in model2.no_crni2_tdb alone. NPROC spawned processes each loop ITER times over exactly what
GradTarget does for the zpf_susp category: path = model2.no_crni2_tdb(start_tdb) (truncate + rewrite of the shared cache file), then
pycalphad.Database(path); counts the reads that see no phases (empty file) or fewer phases than expected (4 - CRNI2 = 3).
  probe_race.py ROOT NPROC ITER"""
import sys
from multiprocessing import get_context
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
NPROC, ITER = int(sys.argv[2]), int(sys.argv[3])


def loop(i):
    sys.path.insert(0, str(ROOT / "scripts"))
    import model2
    from pycalphad import Database
    tdb = ROOT / "tdb/step3b_thermo_crni2free_pick.tdb"
    n_empty = n_partial = n_err = 0
    for _ in range(ITER):
        try:
            db = Database(model2.no_crni2_tdb(tdb))
            n = len(db.phases)
            n_empty += n == 0
            n_partial += 0 < n < 3
        except Exception:  # noqa
            n_err += 1
    return {"proc": i, "iter": ITER, "empty": n_empty, "partial": n_partial, "parse_error": n_err}


if __name__ == "__main__":
    with get_context("spawn").Pool(NPROC) as p:
        rows = p.map(loop, range(NPROC))
    for r in rows:
        print(r)
    print("SUMMARY reads", NPROC * ITER, "empty", sum(r["empty"] for r in rows), "partial", sum(r["partial"] for r in rows),
          "parse_error", sum(r["parse_error"] for r in rows))
