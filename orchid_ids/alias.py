"""Alias records: a provisional id points to the id ORCHID publishes for the same observation (PI 6 Nov 2026).

Old ids are never rewritten or reused. When data first identified under ``local:<ORCID>/<dataset-uuid>`` are published
(a paper or a dataset DOI), the observation gets the ORC id of its published locator and the provisional id stays
resolvable through an alias record. Field names are the ones the ORCHID release and state registry already use:
``id``, ``pid`` (literature/SCHEMA.md), ``status``, ``superseded_by``, ``first_release``, ``lineage_note``
(graph/SCHEMA.md registry rows), and on the published record ``merged_ids`` / ``merged_pids`` (literature/SCHEMA.md).
Where alias rows are stored in a release is not decided yet (docs/ID_SCHEME.md, gaps).
"""
from __future__ import annotations

from .locator import check_link, compact, parse_pid
from .state import descriptor_id


def build_alias_record(provisional_id: str, provisional_pid: str, published_id: str, published_pid: str,
                       release: str | None = None, basis: str | None = None, observation_key: str | None = None,
                       published_observation_key: str | None = None) -> dict:
    """Alias row for a record id: provisional (local: namespace) -> published. Both ids must recompute from their
    locators; the published locator must not be provisional; the two must differ."""
    errors = []
    p = check_link(provisional_id, provisional_pid, observation_key)
    if not p["ok"]:
        errors += ["provisional: " + e for e in p["errors"]]
    elif not p["provisional"]:
        errors.append(f"{provisional_pid} is not in the provisional local: namespace")
    q = check_link(published_id, published_pid, published_observation_key)
    if not q["ok"]:
        errors += ["published: " + e for e in q["errors"]]
    elif q["provisional"]:
        errors.append(f"{published_pid} is still provisional: publish under a paper or dataset DOI first")
    if provisional_id == published_id:
        errors.append("provisional and published ids are the same")
    if errors:
        raise ValueError("; ".join(errors))
    row = {"id": provisional_id, "pid": provisional_pid, "status": "superseded", "superseded_by": published_id,
           "lineage_note": {"reason": "provisional_namespace_published", "published_pid": published_pid,
                            "provisional_source": parse_pid(provisional_pid)["source"],
                            "published_source": parse_pid(published_pid)["source"],
                            **({"basis": basis} if basis else {})}}
    if release:
        row["first_release"] = release
    return row


def merged_fields(published_record: dict, provisional_id: str, provisional_pid: str) -> dict:
    """The published record's merged_ids / merged_pids with the provisional id added (existing literature fields);
    returns the two lists, never edits the record."""
    ids = list(published_record.get("merged_ids") or [])
    pids = list(published_record.get("merged_pids") or [])
    if provisional_id not in ids:
        ids.append(provisional_id)
    if provisional_pid not in pids:
        pids.append(provisional_pid)
    return {"merged_ids": ids, "merged_pids": pids}


def build_state_alias(old_state_descriptor: dict, new_state_descriptor: dict, release: str | None = None) -> dict:
    """Alias row for an S- id. Needed only when the state descriptor held the provisional record id (an unresolved
    observation: unknown phases, or missing T or composition); a resolved state's id does not depend on the source."""
    old, new = descriptor_id("S-", old_state_descriptor), descriptor_id("S-", new_state_descriptor)
    if old == new:
        raise ValueError("the state id does not change: no alias needed")
    row = {"state_id": old, "status": "superseded", "superseded_by": new,
           "lineage_note": {"reason": "provisional_namespace_published"}}
    if release:
        row["first_release"] = release
    return row


__all__ = ["build_alias_record", "merged_fields", "build_state_alias", "compact"]
