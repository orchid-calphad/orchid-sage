"""Detached job wrapper (start/status pattern of sage_mcp; no tool call has to stay open while a long item runs).

Started by runner.start_detached in its own session:  python -I jobwrap.py <run_root>/jobs/<item>.json
It runs the job's command exactly as runner.run_command does (shell, working directory, environment, combined log), and
records what happened next to the job file, atomically:
  <item>.started.json  {"wrapper_pid", "pid", "started"}         when the command has started
  <item>.done.json     {"returncode", "finished", "wall_s"}      when it has ended
The server (step_status) reads these files and writes the run card. Standard library only.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _write(p: Path, obj: dict) -> None:
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1))
    os.replace(tmp, p)


def main(job_path: str) -> int:
    jp = Path(job_path)
    job = json.loads(jp.read_text())
    stem = jp.name[: -len(".json")]
    env = dict(os.environ)
    env.update({k: str(v) for k, v in (job.get("env") or {}).items()})
    log = Path(job["log"])
    log.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    started = _now()
    rc = -1
    try:
        with open(log, "w") as lf:
            p = subprocess.Popen(job["command"], shell=True, cwd=job["cwd"], env=env, stdout=lf, stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL)
            _write(jp.with_name(stem + ".started.json"), {"wrapper_pid": os.getpid(), "pid": p.pid, "started": started})
            rc = p.wait()
    finally:
        _write(jp.with_name(stem + ".done.json"), {"returncode": rc, "finished": _now(), "wall_s": round(time.time() - t0, 2)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
