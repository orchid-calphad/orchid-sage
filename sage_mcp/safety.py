"""Run-root rules (the safety model of run_step).

A run root is a directory the server created itself: fresh (absent or empty) when it was created, outside the repository,
outside every live campaign directory and outside the restricted-material directory (protected paths: localpaths.protected_paths). The server marks it with .sage_run_root.json and runs
commands only with that directory as the working directory. Commands are the protocol's own; before a command runs, its
absolute paths are checked: a path that is written to (an output redirection, a cp/mv/tee target, or --out/--report/-o)
must lie inside the run root. This is a static check plus confinement of the working directory, not an operating-system
sandbox: a protocol script that opens an absolute path itself is trusted to the extent that its code is pinned by hash.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import time
from pathlib import Path

from .repo import SageError, localpaths, repo_root

MARKER = ".sage_run_root.json"


def _home() -> Path:
    return localpaths().user_home().resolve()


def forbidden_roots() -> list[tuple[Path, str]]:
    """Directories a run root may never be in (or contain): the repository, the ORCHID data checkouts, the campaign
    and restricted-material directories and every protected path of the local config or SAGE_MCP_FORBIDDEN."""
    lp = localpaths()
    out = [
        (repo_root().resolve(), "the orchid-sage repository (protocols/ and assessments/ are frozen inputs)"),
        (lp.setting("runs_root").resolve(), "live campaign directories (runs_root)"),
        (lp.setting("restricted_dir").resolve(), "restricted material (restricted_dir)"),
        (lp.setting("orchid_data_dir").resolve(), "the ORCHID data checkout"),
        (lp.setting("orchid_data_next").resolve(), "the ORCHID data checkout (next)"),
    ]
    if lp.setting("phaseforgeplus_src"):
        out.append((lp.setting("phaseforgeplus_src").resolve().parent, "source checkouts (pinned code)"))
    return out + [(p.resolve(), "protected path (local config protected_paths or SAGE_MCP_FORBIDDEN)") for p in lp.protected_paths()[:-2]]


def _inside(p: Path, root: Path) -> bool:
    try:
        p.relative_to(root)
        return True
    except ValueError:
        return False


def check_root_location(run_root: str) -> Path:
    if not run_root or not str(run_root).strip():
        raise SageError("run_root is required")
    r = Path(os.path.expanduser(run_root))
    if not r.is_absolute():
        raise SageError(f"run_root must be an absolute path, got {run_root!r}")
    r = r.resolve()
    h = _home()
    if r in (Path("/"), h, h.parent) or len(r.parts) < 3:
        raise SageError(f"refused: run_root {r} is a top-level or home directory")
    for bad, why in forbidden_roots():
        if _inside(r, bad) or _inside(bad, r):
            raise SageError(f"refused: run_root {r} is inside (or contains) {bad}: {why}")
    return r


def create_fresh_root(run_root: str, mode: str, ident: str, allow_existing_marker: bool = False) -> Path:
    """Create (or adopt an empty) run root and write the marker. Never adopts a non-empty directory."""
    r = check_root_location(run_root)
    if r.exists():
        if not r.is_dir():
            raise SageError(f"refused: {r} exists and is not a directory")
        content = [p for p in r.iterdir()]
        if content and not (allow_existing_marker and (r / MARKER).exists()):
            raise SageError(f"refused: run_root {r} is not empty; choose a fresh directory (nothing is overwritten)")
    r.mkdir(parents=True, exist_ok=True)
    return r


def write_marker(r: Path, mode: str, ident: str) -> None:
    (r / MARKER).write_text(json.dumps({"created_by": "sage_mcp", "mode": mode, "protocol_or_assessment": ident,
                                        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z")}, indent=1))


def require_marked_root(run_root: str) -> tuple[Path, dict]:
    r = check_root_location(run_root)
    m = r / MARKER
    if not m.is_file():
        raise SageError(f"refused: {r} is not a run root created by sage_mcp (no {MARKER}); stage it first")
    return r, json.loads(m.read_text())


WRITE_FLAGS = {"--out", "--report", "-o", "--output", "--root"}


def check_command(cmd: str, root: Path, read_ok: list[Path] | None = None) -> list[str]:
    """Static check of a command line before it runs in `root`. Returns a list of problems (empty = allowed)."""
    problems = []
    if re.search(r"(^|[\s;&|])rm\s", cmd):
        problems.append("the command contains rm (never run by this server)")
    if re.search(r"(^|[\s;&|])(sudo|ssh|scp|rsync|curl|wget|docker|git\s+push)\b", cmd):
        problems.append("the command calls sudo/ssh/scp/rsync/curl/wget/docker/git push (local, offline, no containers)")
    try:
        toks = shlex.split(cmd.replace("&&", " && ").replace(";", " ; "), posix=True)
    except ValueError as exc:
        return problems + [f"cannot parse the command: {exc}"]

    def outside(t: str) -> bool:
        p = Path(os.path.expanduser(t))
        if not p.is_absolute():
            p = root / p
        p = p.resolve()
        return not _inside(p, root)

    for i, t in enumerate(toks):
        nxt = toks[i + 1] if i + 1 < len(toks) else None
        if t in (">", ">>", "2>", "&>") and nxt and outside(nxt):
            problems.append(f"writes outside the run root: {t} {nxt}")
        for flag in WRITE_FLAGS:
            if t == flag and nxt and outside(nxt):
                problems.append(f"writes outside the run root: {flag} {nxt}")
            if t.startswith(flag + "=") and outside(t.split("=", 1)[1]):
                problems.append(f"writes outside the run root: {t}")
        if t in ("cp", "mv", "tee", "ln", "install"):
            # the last argument of this simple command is the target
            j = i + 1
            args = []
            while j < len(toks) and toks[j] not in ("&&", ";", "|", "||"):
                args.append(toks[j]); j += 1
            targets = [a for a in args if not a.startswith("-")]
            if t == "tee":
                bad = [a for a in targets if outside(a)]
            else:
                bad = [targets[-1]] if targets and outside(targets[-1]) else []
            for b in bad:
                problems.append(f"{t} writes outside the run root: {b}")
        if t == "cd" and nxt and outside(nxt):
            problems.append(f"changes directory out of the run root: cd {nxt}")
    return problems
