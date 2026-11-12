"""orchid_ids: compute and check ORCHID identifiers offline (standard library only).

  ORC-  record (observation) id from its persistent locator (pid)          locator.compute_orc_id
  C-    state-class id, S- state id from the canonical state                 state.compute_state_id
        (coord-rule/3, PI 6 Nov 2026: own invariant T, SGTE reference, decimal rounding; coord-rule/2 reproduces
        the v2027.01-candidate registry)
  local:<ORCID>/<dataset-uuid>  provisional namespace for unpublished data   locator.make_provisional_namespace
  alias records provisional -> published, never rewritten                  alias.build_alias_record

Design and test vectors: docs/ID_SCHEME.md. Vendored copies (orchid-mcp) keep this file set unchanged.
"""
from __future__ import annotations

from .alias import build_alias_record, build_state_alias, merged_fields
from .locator import (build_pid, check_link, compact, compute_orc_id, make_provisional_namespace, new_dataset_uuid,
                      orcid_ok, parse_pid, validate_id, value_suffix)
from .reference import SER_PHASE, SGTE_UNARY, reference_status, ser_reference_state
from .state import (RULE3, PhaseRegistry, RULE_VERSION, compute_state_id, contribution_to_record, descriptor_id,
                    state_descriptors, state_descriptors_3)

__version__ = "0.2.0"
ID_RULES = {"record": "asset_ids.py tools-release-v2.1.18 (v2026.10)", "state": RULE3,
            "state_reference": f"SGTE SER ({SGTE_UNARY})", "state_candidate_registry": RULE_VERSION}


def compute_ids(pid: str | None = None, locator: dict | None = None, state: dict | None = None,
                observation_key: str | None = None, phase_registry: PhaseRegistry | None = None, rule: str = RULE3) -> dict:
    """Both ids of one observation. pid: full locator, or locator: the parts of build_pid() (source or doi / orcid +
    dataset_uuid, kind, page, label, row | series + point, datum_type). state: a literature-form record (system,
    observation_type, property, phases, temperature_K, pressure_Pa, pressure_basis, overall_composition,
    transition_kind, reference_state). rule: coord-rule/3 (default, PI 6 Nov 2026) or coord-rule/2 (candidate registry)."""
    out: dict = {"rules": ID_RULES, "library_version": __version__}
    record_id = None
    if pid is not None or locator:
        rec = compute_orc_id(pid, observation_key=observation_key, **(locator or {}))
        out["record"] = rec
        record_id = rec["id"]
    if state is not None:
        st = dict(state)
        if record_id and not st.get("id"):
            st["id"] = record_id
        out["state"] = compute_state_id(st, phase_registry, observation_id=st.get("id"), rule=rule)
    if "record" not in out and "state" not in out:
        raise ValueError("give pid, locator or state")
    return out


def check_provisional_link(link: dict, observation_key: str | None = None) -> list[str]:
    """Errors of an ``orchid_link: provisional`` link item {id, pid[, state_id, state_class_id]}: the locator follows the
    grammar, its namespace is local:<ORCID>/<uuid> (provisional) or doi: (a deposited dataset, not yet in an ORCHID
    release), and the id recomputes from the locator."""
    errs = []
    if not isinstance(link, dict) or not link.get("id") or not link.get("pid"):
        return ["a provisional link needs id and pid (the full locator it is computed from)"]
    res = check_link(link["id"], link["pid"], observation_key)
    errs += res["errors"]
    if res.get("namespace") not in (None, "local", "doi"):
        errs.append(f"{link['pid']}: a provisional link's namespace is local:<ORCID>/<uuid> or a dataset doi:, not {res['namespace']}:")
    for key, kind in (("state_id", "state"), ("state_class_id", "state_class")):
        if link.get(key) and validate_id(link[key]).get("kind") != kind:
            errs.append(f"{key} {link[key]!r} is not a {kind} id")
    return errs


__all__ = [
    "PhaseRegistry", "RULE3", "RULE_VERSION", "SER_PHASE", "reference_status", "ser_reference_state", "state_descriptors_3", "build_alias_record", "build_pid", "build_state_alias", "check_link",
    "check_provisional_link", "compact", "compute_ids", "compute_orc_id", "compute_state_id", "contribution_to_record",
    "descriptor_id", "make_provisional_namespace", "merged_fields", "new_dataset_uuid", "orcid_ok", "parse_pid",
    "state_descriptors", "validate_id", "value_suffix",
]
