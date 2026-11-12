#!/usr/bin/env python3
"""Run a campaign script with the clock fixed to a recorded date, so a script that writes the generation date into its
output (e.g. crni-phaseforge build_tdb.py: '$ ... generated YYYY-MM-DD') rebuilds byte-identically. The script itself is
not modified (it stays byte-identical to the snapshot).

  PY run_with_fixed_date.py --date 2026-11-06 SCRIPT.py [args ...]

Patches time.strftime called without a time argument (the 'today' formatting) to the given date at 12:00:00 UTC, then executes SCRIPT as __main__."""
import calendar
import datetime as _dt
import runpy
import sys
import time

i = sys.argv.index("--date"); day = sys.argv[i + 1]; del sys.argv[i:i + 2]
T0 = calendar.timegm(time.strptime(day + " 12:00:00", "%Y-%m-%d %H:%M:%S"))
_strftime, _gmtime = time.strftime, time.gmtime
time.strftime = lambda fmt, t=None: _strftime(fmt, _gmtime(T0) if t is None else t)
# Only the default-argument strftime (the "current date" formatting) is patched. Patching time.time/localtime as well
# crashed native extensions (segfault in the pycalphad/numpy stack, 6 Nov test), and wall-clock values written to JSON
# side files (e.g. created_unix) are not part of the compared TDB.
script = sys.argv[1]; sys.argv = sys.argv[1:]
sys.path.insert(0, str(__import__("pathlib").Path(script).resolve().parent))
runpy.run_path(script, run_name="__main__")
