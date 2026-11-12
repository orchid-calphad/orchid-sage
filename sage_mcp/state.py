"""Server state: the registry of fresh assessments and where proposed general-protocol versions are written.

The state directory (SAGE_MCP_STATE_DIR, or 'state_dir' in local/config.json; default local/state in the checkout, gitignored) holds registry.json (assessment id -> run root) and
general/ (proposed general-protocol versions, never merged into protocols/general by this server).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .repo import SageError, localpaths


def state_dir() -> Path:
    return localpaths().setting("state_dir")


def general_dir() -> Path:
    return state_dir() / "general"


def _registry_path() -> Path:
    return state_dir() / "registry.json"


def registry() -> dict:
    p = _registry_path()
    return json.loads(p.read_text()) if p.is_file() else {}


def register(assessment_id: str, run_root: Path) -> None:
    reg = registry()
    if assessment_id in reg and reg[assessment_id] != str(run_root):
        raise SageError(f"assessment {assessment_id!r} already exists at {reg[assessment_id]}")
    reg[assessment_id] = str(run_root)
    state_dir().mkdir(parents=True, exist_ok=True)
    _registry_path().write_text(json.dumps(reg, indent=1, sort_keys=True))


def resolve(assessment: str) -> Path:
    reg = registry()
    if assessment in reg:
        return Path(reg[assessment])
    p = Path(os.path.expanduser(assessment))
    if p.is_absolute() and (p / "sage_state.json").is_file():
        return p
    raise SageError(f"unknown assessment {assessment!r}; known: {sorted(reg)} (or give the run root path)")
