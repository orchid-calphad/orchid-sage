"""compute_ids: ORCHID record and state ids computed offline (orchid_ids, docs/ID_SCHEME.md)."""
from __future__ import annotations

import functools
import os
import sys
from pathlib import Path
from typing import Any

from .repo import SageError, localpaths, repo_root, tilde


def _lib():
    try:
        import orchid_ids  # installed package or repository checkout on sys.path
    except ImportError:
        sys.path.insert(0, str(repo_root()))
        import orchid_ids
    return orchid_ids


@functools.lru_cache(maxsize=4)
def _registry(data_dir: str):
    return _lib().PhaseRegistry.load(data_dir)


def compute_ids(pid: str | None = None, locator: dict | None = None, state: dict | None = None,
                observation_key: str | None = None, orcid: str | None = None, dataset_uuid: str | None = None,
                new_namespace: bool = False, check_id: str | None = None, orchid_data_dir: str | None = None,
                use_phase_registry: bool = True, rule: str = "coord-rule/3") -> dict[str, Any]:
    I = _lib()
    out: dict[str, Any] = {}
    if new_namespace or (orcid and dataset_uuid and not (pid or locator)):
        out["namespace"] = I.make_provisional_namespace(orcid, dataset_uuid or I.new_dataset_uuid())
        out["namespace_note"] = ("keep the dataset UUID with the data; every id of the dataset uses this namespace until it "
                                 "is published (then alias records point to the published ids)")
        if not (pid or locator or state):
            return out
    loc = dict(locator or {})
    if loc and orcid and dataset_uuid and not any(loc.get(k) for k in ("source", "doi", "isbn", "pdf_sha256", "orcid")):
        loc.update(orcid=orcid, dataset_uuid=dataset_uuid)
    reg = None
    if state is not None and use_phase_registry:
        d = Path(orchid_data_dir).expanduser() if orchid_data_dir else localpaths().setting("orchid_data_dir")
        if (d / "phases/registry.json").is_file():
            reg = _registry(str(d))
            out["phase_registry"] = tilde(d / "phases/registry.json")
        else:
            out["phase_registry"] = None
    if pid or loc or state is not None:
        try:
            out.update(I.compute_ids(pid=pid, locator=loc or None, state=state, observation_key=observation_key, phase_registry=reg, rule=rule))
        except (ValueError, TypeError, KeyError) as exc:
            raise SageError(f"refused: {exc}") from exc
    if check_id:
        if not (pid or (out.get("record") or {}).get("pid")):
            raise SageError("check_id needs the locator (pid or locator) it was computed from")
        out["check"] = I.check_link(check_id, pid or out["record"]["pid"], observation_key)
    if not out:
        raise SageError("give pid, locator, state, or orcid (+ dataset_uuid) for a new namespace")
    return out
