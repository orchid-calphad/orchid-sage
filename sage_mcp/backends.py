"""Executor backends.

`local` is the only backend that executes anything: CPU commands on this machine, in a run root. GPU steps (the
PhaseForge one-shot relaxations and the liquid MD) are never executed by this server: run_step returns their job spec
(container image and digest status, command, MLIP weights with hashes, seeds, mounts) and writes it to
<run_root>/jobs/<step>.json for an executor.

Remote hosts (e.g. the DGX Sparks) are *configured* backends, disabled by default and never enabled by the server.
A user enables one by writing the backend file (SAGE_MCP_BACKENDS, or 'backends_file' in local/config.json; default
local/backends.json in the checkout, gitignored; template local.example/backends.json), e.g.

    {"gpu1": {"kind": "ssh", "host": "<ssh host alias>", "workdir": "sage-runs", "gpu": true, "enabled": true}}

and by naming it explicitly in run_step(..., backend="gpu1"). Host names live only in that file. Even then this version does not connect to the host:
it writes the job spec and returns the submission command for the user to run (submission by the server is not
implemented, so no test or agent can launch a remote job through it).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .repo import SageError, localpaths


def config_path() -> Path:
    return localpaths().setting("backends_file")


def configured() -> dict:
    p = config_path()
    if not p.is_file():
        return {}
    try:
        d = json.loads(p.read_text())
    except json.JSONDecodeError as exc:
        raise SageError(f"backend config {p} is not valid JSON: {exc}") from exc
    return {k: v for k, v in d.items() if isinstance(v, dict)} if isinstance(d, dict) else {}   # "_note" etc. skipped


def describe() -> dict:
    remote = {k: {**v, "enabled": bool(v.get("enabled", False))} for k, v in configured().items()}
    return {"local": {"kind": "local", "executes": "CPU commands in a run root", "gpu": False, "enabled": True},
            **remote, "config_file": str(config_path())}


def get(name: str) -> dict:
    if name == "local":
        return {"name": "local", "kind": "local", "gpu": False, "enabled": True}
    cfg = configured().get(name)
    if cfg is None:
        raise SageError(f"unknown backend {name!r}; configured: {sorted(configured())} (see {config_path()})")
    if not cfg.get("enabled", False):
        raise SageError(f"backend {name!r} is configured but disabled (set \"enabled\": true in {config_path()})")
    return {"name": name, **cfg}


def submission_hint(backend: dict, job_file: Path) -> str | None:
    if backend["kind"] == "local":
        return None
    host = backend.get("host", backend["name"])
    wd = backend.get("workdir", "sage-runs")             # relative: the login directory on the host
    return (f"# not run by the server; review, then run yourself:\n"
            f"scp {job_file} {host}:{wd}/ && ssh {host} 'cd {wd} && cat {job_file.name}'   # then launch its `command`")
