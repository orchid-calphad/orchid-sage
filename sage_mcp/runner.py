"""Execute one command in a run root and write its run card (orchid-assessment-schema run_card)."""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

from .repo import SageError, schema_errors, sha256_file, tilde
from .safety import check_command

SCHEMA_VERSION = "orchid-assessment-schema@1.0.0-draft"


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def tail(path: Path, n: int = 40) -> str:
    try:
        lines = path.read_text(errors="replace").splitlines()
    except FileNotFoundError:
        return ""
    return "\n".join(lines[-n:])


def run_command(cmd: str, root: Path, cwd: Path, log: Path, env_extra: dict | None = None, timeout: float | None = None) -> dict:
    _check_launch(cmd, root, cwd)
    env = dict(os.environ)
    env.update({k: str(v) for k, v in (env_extra or {}).items()})
    log.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    started = now()
    with open(log, "w") as lf:
        try:
            r = subprocess.run(cmd, shell=True, cwd=cwd, env=env, stdout=lf, stderr=subprocess.STDOUT, timeout=timeout)
            rc = r.returncode
        except subprocess.TimeoutExpired:
            rc = -9
    return {"command": cmd, "cwd": str(cwd), "returncode": rc, "started": started, "finished": now(),
            "wall_s": round(time.time() - t0, 2), "log": str(log), "log_tail": tail(log)}


MAX_WAIT_S = float(os.environ.get("SAGE_MCP_MAX_WAIT_S", "900"))   # longest a step_status call blocks (server side)
_LAUNCHED: dict[int, subprocess.Popen] = {}   # wrappers started by this server process (kept so they are reaped, not orphaned objects)


def _check_launch(cmd: str, root: Path, cwd: Path) -> None:
    problems = check_command(cmd, root)
    if problems:
        raise SageError("refused: " + "; ".join(problems))
    try:
        cwd.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise SageError(f"refused: working directory {cwd} is outside the run root") from exc


def job_files(root: Path, item: str) -> dict[str, Path]:
    j = root / "jobs"
    return {"job": j / f"{item}.json", "started": j / f"{item}.started.json", "done": j / f"{item}.done.json",
            "recorded": j / f"{item}.recorded.json"}


def pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    if pid in _LAUNCHED:
        return _LAUNCHED[pid].poll() is None
    try:
        got, _ = os.waitpid(pid, os.WNOHANG)   # reaps the wrapper if this server started it and it has ended
        return got == 0
    except ChildProcessError:
        pass
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _read(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def job_state(root: Path, item: str) -> dict:
    """State of a detached job: none | running | finished | lost (wrapper gone without a done record)."""
    f = job_files(root, item)
    job = _read(f["job"])
    if job is None:
        return {"state": "none"}
    started, done, recorded = _read(f["started"]), _read(f["done"]), _read(f["recorded"])
    out = {"job": job, "started": started, "done": done, "recorded": recorded}
    if done is not None:
        return {"state": "finished", **out}
    if pid_alive(job.get("wrapper_pid")):
        return {"state": "running", **out}
    done = _read(f["done"])   # the wrapper may have ended between the two reads
    if done is not None:
        return {"state": "finished", **out, "done": done}
    return {"state": "lost", **out}


def start_detached(cmd: str, root: Path, cwd: Path, log: Path, item: str, env_extra: dict | None = None, meta: dict | None = None) -> dict:
    """Start cmd in its own session through jobwrap.py and return at once. The job record is <root>/jobs/<item>.json."""
    _check_launch(cmd, root, cwd)
    f = job_files(root, item)
    f["job"].parent.mkdir(parents=True, exist_ok=True)
    job = {"item": item, "command": cmd, "cwd": str(cwd), "log": str(log), "env": {k: str(v) for k, v in (env_extra or {}).items()},
           "launched": now(), "launched_by": "sage_mcp start/status (detached; the run card is written by step_status)", **(meta or {})}
    f["job"].write_text(json.dumps(job, indent=1))
    env = dict(os.environ)
    p = subprocess.Popen([sys.executable, "-I", str(Path(__file__).resolve().parent / "jobwrap.py"), str(f["job"])],
                         cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    _LAUNCHED[p.pid] = p
    job["wrapper_pid"] = p.pid
    f["job"].write_text(json.dumps(job, indent=1))
    t_end = time.time() + 10
    while time.time() < t_end and not f["started"].is_file() and p.poll() is None:
        time.sleep(0.05)
    return {**job, "job_file": str(f["job"]), "started": _read(f["started"])}


def wait_job(root: Path, item: str, wait_s: float = 0) -> dict:
    """job_state, blocking up to min(wait_s, MAX_WAIT_S) seconds while the job runs (polls every 5 s at most)."""
    t_end = time.time() + max(0.0, min(float(wait_s or 0), MAX_WAIT_S))
    st = job_state(root, item)
    while st["state"] == "running" and time.time() < t_end:
        time.sleep(min(5.0, max(0.05, t_end - time.time())))
        st = job_state(root, item)
    return st


def interpreter_packages(py: str) -> dict:
    code = ("import json,importlib.metadata as m\n"
            "out={}\n"
            "for p in ('espei','pycalphad','numpy','scipy','symengine'):\n"
            "    try: out[p]=m.version(p)\n"
            "    except Exception: pass\n"
            "print(json.dumps(out))")
    try:
        r = subprocess.run([py, "-I", "-c", code], capture_output=True, text=True, timeout=60)
        return json.loads(r.stdout.strip() or "{}")
    except Exception:  # noqa: BLE001
        return {}


def file_ref(p: Path, role: str, storage_class: str = "local") -> dict:
    return {"path": tilde(p), "sha256": sha256_file(p), "storage_class": storage_class, "role": role}


def write_run_card(root: Path, run_id: str, specific: str, general: str, step: str, exec_rec: dict, py: str | None,
                   inputs: list[Path], outputs: list[Path], seeds: dict | None = None, results: dict | None = None,
                   trajectory: dict | None = None, code_commit: str | None = None, notes: list[str] | None = None,
                   pids: list[int] | None = None) -> Path:
    """Write <root>/run_cards/<run_id>.json and check it against the schema. Returns its path."""
    py = py or sys.executable
    card = {
        "type": "run_card", "schema_version": SCHEMA_VERSION, "id": run_id, "version": "1.0.0",
        "title": f"{step} ({specific})", "status": "complete" if exec_rec.get("returncode") == 0 else "failed",
        "status_note": "native run recorded by sage_mcp (not converted from campaign records)",
        "run_id": run_id,
        "executes": {"specific_protocol": specific, "general_protocol": general, "step": step},
        "host": platform.node(), "hardware_class": f"{platform.system()} {platform.machine()} CPU",
        "started": exec_rec["started"], "finished": exec_rec["finished"],
        "interpreter": tilde(py), "packages": {k: str(v) for k, v in interpreter_packages(py).items()},
        "command": exec_rec["command"], "threads": os.environ.get("OMP_NUM_THREADS", "unset"),
        "seeds": seeds or {"note": "no random seed in this step"},
        "inputs": [file_ref(p, "input") for p in inputs if Path(p).is_file()],
        "outputs": [file_ref(p, "output") for p in outputs if Path(p).is_file()],
        "results": {"returncode": exec_rec.get("returncode"), "wall_s": exec_rec.get("wall_s"), **(results or {})},
        "trajectory": trajectory or {"status": "not_recorded", "reason": "not a fit step (no per-evaluation history)"},
        "converted_from": [file_ref(Path(exec_rec["log"]), "run log written by sage_mcp (native run; see SCHEMA_GAPS G3)")],
        "notes": (notes or []) + ([f"code commit {code_commit}"] if code_commit else []),
    }
    if pids:
        card["pids"] = [int(x) for x in pids]
    errs = schema_errors(card)
    if errs:
        raise SageError(f"run card for {run_id} is not schema-valid: {errs[:5]}")
    out = root / "run_cards" / f"{run_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(card, indent=1, ensure_ascii=False))
    return out
