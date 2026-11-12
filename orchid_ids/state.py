"""S- state ids and C- state-class ids, as the ORCHID state registry computes them (rule ``coord-rule/2``).

Port of orchid-data ``graph/tools/build_registry.py`` (branch Y25/coord-rule-2, c987995dd5, 5 Nov 2026) and of the
helpers it imports from the Y14 prototype (``build_state_registry.py``: phase resolution, equilibrium type, pressure class,
composition). Standard library only.

The id rule itself is a pure hash:  id = prefix + first 10 lowercase hex of SHA-256(canonical JSON of the descriptor),
canonical JSON = ``json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False)``;
C- descriptor = {system, phases, pressure_class[, unresolved_observation]};
S- descriptor = C- descriptor + {coordinates, assignment_rule}.

What a single record does NOT determine (the registry does, from its ledger; see docs/ID_SCHEME.md):
  * invariant / transition readings on a phase set with more than one reaction group get ``reaction_group``
    {kind, founding_T_K} from the ledger (the T of the group's first reading, frozen at issue);
  * a boundary state whose cell equals a field-point state's is issued under the field-point rule;
  * near-identical readings may merge (dT <= 0.5 K, dx <= 0.001, same paper, source, property and value);
  * a hash collision takes descriptor + "#1", "#2", ... (never needed so far at 10 hex).
compute_state_id() reports these as ``registry_dependent`` so that the caller knows the id is provisional until intake.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

RULE_VERSION = "coord-rule/2"
R_INVARIANT = RULE_VERSION + ":invariant-or-transition"
R_ENVELOPE = RULE_VERSION + ":calculated-field-envelope"
R_NONE = RULE_VERSION + ":no-coordinates"
R_BOUNDARY = RULE_VERSION + ":boundary-5K-0.02x"
R_FIELD = RULE_VERSION + ":field-point-10K-0.02x"
R_COMPOUND = RULE_VERSION + ":compound-1K-exact-x"
R_SOLUTION = RULE_VERSION + ":solution-exact"
R_ZERO = RULE_VERSION + ":0K-exact-x"
ID_HEX_LENGTH = 10
PLAUSIBLE_T_K = (1.0, 6000.0)
INVARIANT_GAP_K = 46.0
UNSTATED_KINDS = {None, "", "other", "none", "None"}

UNKNOWN_LABEL = re.compile(r"^label:(|unknown|none|na|n/a|\?|\d+|eutectic|peritectic|eutectoid|peritectoid|monotectic|syntectic|solidus|liquidus|solvus|matrix|polymorphic|other|secondphase|solidphase|phase|solid|overall|overalledx|sampleoverallcomposition|samplenominal|chemicalanalysisbulk|zero|gap|half|all|magnetic|congruent|unspecifiedinvariantpoint|aircorrosiondiscarded|tungstenphase|melting|.*richphase.*|oxidephase.*|phase[0-9].*|(single|unidentified|reactive|first|second|third|primary|secondary|new)phase.*|sample[0-9].*|alloy.*|.*alloy|.*withmagnetic|.*(solidus|liquidus|solvus|eutectic|eutectoid|peritectic|peritectoid|monotectic|syntectic|allotropic|polymorphic).*)$")
CONFIG_TERM = re.compile(r"(?<![a-z0-9])(l1[_ ]?[0-2]|d0[_ ]?\d+[a-z]?|b2|b32|c11[_ ]?b|sqs|disordered|ordered)(?![a-z0-9])", re.I)
ORDER_START = re.compile(r"^(b2|b32|l1[02]|l2[1-9]|d0\d+|d8|c[0-9]+)")
ORDER_ANYWHERE = re.compile(r"sigma|laves|4sl")
ORDER_WORD = re.compile(r"^(mu|chi)(phase|d[0-9]+)?$")
CRYSTAL_PREFIX = re.compile(r"^(fcc|bcc|hcp|bct|dhcp|alpha|beta|gamma|delta|epsilon)")
STRUCTURE_SUFFIX = re.compile(r"[a-z][0-9]+[a-z]?$")
SOLUTION_NAME = re.compile(r"^(fcc|bcc|hcp|bct|dhcp|cbcc|cub|rhomb|tetrag|ortho|hexag|diamond|graphite|gas|liquid|ion|melt|a[0-9]+)")
TYPE_SUFFIX = re.compile(r"[a-z]?type$")
ALL_ELEMENTS = sorted("h he li be b c n o f ne na mg al si p s cl ar k ca sc ti v cr mn fe co ni cu zn ga ge as se br kr rb sr y zr nb mo tc ru rh pd ag cd in sn sb te i xe cs ba la ce pr nd pm sm eu gd tb dy ho er tm yb lu hf ta w re os ir pt au hg tl pb bi po at rn fr ra ac th pa u np pu am cm".split(), key=len, reverse=True)
GREEK_SUFFIX = re.compile(r"(alpha|beta|gamma|delta|epsilon|eps|eta|theta|lambda|tau|zeta|kappa|phi|psi|omega|xi|rho)[0-9]*$")
ASSUMED_RANDOM = {"configuration": "random", "basis": "assumed_default_not_printed"}


# ------------------------------------------------------------------ hashing
def cjson(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def descriptor_id(prefix: str, descriptor: Any, attempt: int = 0) -> str:
    """prefix + first 10 hex of SHA-256(canonical JSON); attempt > 0 is the registry's collision fallback (descriptor#n)."""
    text = descriptor if isinstance(descriptor, str) else cjson(descriptor)
    material = text if attempt == 0 else f"{text}#{attempt}"
    return prefix + hashlib.sha256(material.encode("utf-8")).hexdigest()[:ID_HEX_LENGTH]


# ------------------------------------------------------------------ small helpers (Y14 prototype)
def norm_label(value: Any) -> str:
    text = str(value or "").strip().upper()
    text = {"L": "LIQUID", "LIQ": "LIQUID", "LIQUIDUS": "LIQUID"}.get(text, text)
    return re.sub(r"[^A-Z0-9]+", "", text)


def qround(value: float | None, step: float) -> float | None:
    """Cell centre: round(v / step) * step (Python round: half to even), then 8 decimals."""
    if value is None or not math.isfinite(float(value)):
        return None
    return round(round(float(value) / step) * step, 8)


def exact(value: Any, digits: int) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return round(number, digits) if math.isfinite(number) else None


def pressure_class(value: Any) -> str:
    """ambient 0.8e5..1.2e5 Pa; subambient below; elevated up to 1e7 Pa; high above; unknown when absent."""
    if value is None:
        return "unknown"
    p = float(value)
    if 8.0e4 <= p <= 1.2e5:
        return "ambient"
    if p < 8.0e4:
        return "subambient"
    if p <= 1.0e7:
        return "elevated"
    return "high"


def composition_dict(record: dict) -> dict[str, float]:
    overall = record.get("overall_composition")
    if isinstance(overall, dict):
        return {str(k).upper(): float(v) for k, v in overall.items() if v is not None}
    if isinstance(overall, list):
        out = {}
        for item in overall:
            if isinstance(item, dict) and item.get("element") is not None:
                val = item.get("value", item.get("x"))
                if val is not None:
                    out[str(item["element"]).upper()] = float(val)
        return out
    return {}


def equilibrium_type(record: dict, n_phases: int) -> str:
    obs = str(record.get("observation_type") or record.get("record_type") or "unknown").lower()
    prop = str(record.get("property") or "").upper()
    labels = " ".join(str(p.get("label", "")) for p in record.get("phases") or [] if isinstance(p, dict)).lower()
    if obs == "invariant_reaction" or "INVARIANT" in prop:
        return "invariant"
    if obs == "phase_transition" or "TRANSITION" in prop:
        for kind in ("liquidus", "solidus", "solvus"):
            if kind in labels:
                return kind
        return "transition"
    if obs in {"phase_region_vertex_set", "phase_assemblage_node", "assessed_phase_assemblage"}:
        return "two_phase_field" if n_phases == 2 else "single_phase_field" if n_phases == 1 else "phase_field"
    return "property_state"


def canonical_x(system: str, comp: dict[str, float]) -> dict[str, float]:
    """One form for one composition: mole fractions without the system's first element when it is implied."""
    elements = system.split("-")
    comp = {str(k).upper(): float(v) for k, v in comp.items() if v is not None}
    if not comp:
        return {}
    if len(elements) == 2 and len(comp) == 1 and set(comp) <= set(elements):
        key = next(iter(comp))
        return {elements[1]: comp[key] if key == elements[1] else 1.0 - comp[key]}
    if set(comp) == set(elements) and abs(sum(comp.values()) - 1.0) <= 0.01:
        return {k: v for k, v in sorted(comp.items()) if k != elements[0]}
    return dict(sorted(comp.items()))


def norm_designator(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


# ------------------------------------------------------------------ phase registry
class PhaseRegistry:
    """Phase resolution through the ORCHID phase registry (phases/registry.json, public in every release), plus the facts
    the configuration rule needs: stoichiometric phases, registry structure designators, why a name implies order."""

    def __init__(self, registry: dict | None = None, systems: list[dict] | None = None):
        self.by_system: dict[str, dict[str, str]] = {}
        self.stoichiometric: set[str] = set()
        self.structure: dict[str, set[str]] = {}
        self.reason: dict[str, str] = {}
        self.loaded = registry is not None
        self.version = {k: (registry or {}).get(k) for k in ("registry_version", "release")} if registry is not None else None
        self.systems_loaded = systems is not None
        phases = (registry or {}).get("phases") or []
        for phase in phases:
            table = self.by_system.setdefault(phase["system"], {})
            tokens = [phase.get("preferred_name"), *(phase.get("tdb_names") or [])]
            for name in phase.get("names") or []:
                tokens.append(str(name).rsplit(":", 1)[-1])
            for token in tokens:
                key = norm_label(token)
                if key:
                    table.setdefault(key, phase["id"])
            if phase.get("stoichiometry"):
                self.stoichiometric.add(phase["id"])
            st = phase.get("structure") or {}
            sg = st.get("space_group") or {}
            self.structure[phase["id"]] = {norm_designator(v) for v in (st.get("pearson"), st.get("prototype"),
                                           st.get("strukturbericht"), sg.get("symbol"), sg.get("number")) if v}
        for phase in phases:
            name = str(phase.get("preferred_name") or "").upper()
            if phase.get("stoichiometry"):
                self.reason[phase["id"]] = "stoichiometric_or_line_compound"
            elif not name.startswith(("LIQUID", "GAS", "ION")) and "GAS" not in name:
                letter = str((phase.get("structure") or {}).get("strukturbericht") or "")[:1]
                if letter and letter not in {"A", "N"}:
                    self.reason[phase["id"]] = "named_ordered_structure"
        for payload in systems or []:
            for phase in payload.get("phases") or []:
                name = str(phase.get("preferred_name") or "").upper()
                if phase["id"] in self.reason or name.startswith(("LIQUID", "GAS", "ION")) or "GAS" in name:
                    continue
                for model in phase.get("models") or []:
                    substitutional = [sub for sub in model.get("sublattices") or []
                                      if not any(str(c).upper() == "VA" for c in (sub.get("constituents") or []))]
                    if model.get("disordered_part") or len(substitutional) >= 2:
                        self.reason[phase["id"]] = "sublattice_ordered_model"
                        break
                    if model.get("stoichiometric"):
                        self.reason[phase["id"]] = "stoichiometric_or_line_compound"

    @classmethod
    def load(cls, data_dir: str | Path, systems: bool = True) -> "PhaseRegistry":
        """data_dir: an ORCHID data checkout or download (needs phases/registry.json; phases/systems/*.json for the
        sublattice-model reason, about 70 MB, read once)."""
        d = Path(data_dir).expanduser()
        reg = json.loads((d / "phases/registry.json").read_text(encoding="utf-8"))
        sys_payloads = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((d / "phases/systems").glob("*.json"))] if systems else None
        return cls(reg, sys_payloads)

    def resolve(self, system: str, phase: dict | str) -> tuple[str, str]:
        if isinstance(phase, str):
            label, model = phase, None
        else:
            label, model = phase.get("label"), phase.get("model_phase")
        mapping = self.by_system.get(system, {})
        for candidate in (model, label):
            key = norm_label(candidate)
            if key and key in mapping:
                return mapping[key], "phase_registry"
        if model:
            return "model:" + norm_label(model).lower(), "model_phase_fallback"
        return "label:" + norm_label(label).lower(), "printed_label_fallback"

    # -- configuration rule (PI ruling 1 Nov 2026)
    def distinguishing(self, designators: dict, token: str) -> dict[str, str]:
        known = self.structure.get(token, set())
        return {k: str(v) for k, v in sorted(designators.items()) if v not in (None, "", []) and norm_designator(v) not in known}

    def phase_order_reason(self, token: str, system: str) -> str | None:
        if token.startswith("phase-candidate:"):
            return "dft_entry_structure"
        if token in self.reason:
            return self.reason[token]
        if token.startswith(("label:", "model:", "phase:")) and not re.search(r"(liquid|gas|ion)$", token):
            name = token.split(":", 1)[1] if not token.startswith("phase:") else token.rsplit(":", 1)[-1]
            name = re.sub(r"^hb-(.*)-[0-9a-f]{12}$", r"\1", name)
            flat = name.lower().replace("_", "").replace("-", "")
            bare = CRYSTAL_PREFIX.sub("", flat)
            if ORDER_ANYWHERE.search(flat) or ORDER_START.search(bare) or ORDER_START.search(flat) or ORDER_WORD.match(flat):
                return "named_ordered_structure"
            if SOLUTION_NAME.search(flat):
                return None
            if _is_formula(name, system):
                return "stoichiometric_or_line_compound"
        return None


def _parses_as_compound(text: str, elements: list[str]) -> bool:
    seen, i = set(), 0
    while i < len(text):
        for e in elements:
            if text.startswith(e, i):
                seen.add(e)
                i += len(e)
                break
        else:
            if text[i].isdigit() or text[i] == ".":
                i += 1
            else:
                return False
    return len(seen) >= 2


def _is_formula(text: str, system: str) -> bool:
    elements = sorted((e.lower() for e in system.split("-")), key=len, reverse=True)
    text = re.sub(r"[^a-z0-9.]", "", text.lower())
    base = {text, STRUCTURE_SUFFIX.sub("", text), GREEK_SUFFIX.sub("", text), TYPE_SUFFIX.sub("", text), text.removesuffix("type")}
    candidates = base | {t[1:] for t in base if t} | {t[:-1] for t in base if t}
    if any(_parses_as_compound(t, elements + ["m"]) for t in candidates if t):
        return True
    return any(any(ch.isdigit() for ch in t) and _parses_as_compound(t, ALL_ELEMENTS)
               for t in (text, text.removesuffix("type"), STRUCTURE_SUFFIX.sub("", text)) if t)


def phases_unknown(phases: list[str]) -> bool:
    return not phases or any(UNKNOWN_LABEL.match(token) for token in phases)


# ------------------------------------------------------------------ coord-rule/2
def _state_coordinates(kind: str, system: str, temperature: Any, comp: dict[str, float]) -> dict:
    x = canonical_x(system, comp)
    if kind == R_BOUNDARY:
        return {"T_cell_K": qround(temperature, 5.0), "x_cells": {k: qround(v, 0.02) for k, v in x.items()}}
    if kind == R_FIELD:
        return {"T_cell_K": qround(temperature, 10.0), "x_cells": {k: qround(v, 0.02) for k, v in x.items()}}
    if kind == R_COMPOUND:
        return {"T_cell_K": qround(temperature, 1.0), "x": {k: exact(v, 4) for k, v in x.items()}}
    return {"T_K": exact(temperature, 2), "x": {k: exact(v, 4) for k, v in x.items()}}


def _coord_rule_2(record: dict, eq: str, system: str, phases: list[str], reg: PhaseRegistry) -> tuple[dict, str]:
    if eq in {"invariant", "transition"}:
        return {}, R_INVARIANT
    temperature = record.get("temperature_K", record.get("T_K"))
    comp = composition_dict(record)
    if not comp and record.get("x") is not None and record.get("x_component"):
        comp = {str(record["x_component"]).upper(): float(record["x"])}
    if any(record.get(k) not in (None, "", [], {}) for k in ("temperature_range_K", "T_range", "composition_range", "x_range")):
        return {}, R_NONE
    if temperature is None and not comp:
        return {}, R_NONE
    if temperature is not None and float(temperature) == 0.0:
        kind = R_ZERO
    elif record.get("observation_type") == "phase_assemblage_node":
        kind = R_FIELD
    elif eq in {"liquidus", "solidus", "solvus", "two_phase_field", "single_phase_field", "phase_field"}:
        kind = R_BOUNDARY
    else:
        kind = R_COMPOUND if len(phases) == 1 and phases[0] in reg.stoichiometric else R_SOLUTION
    return _state_coordinates(kind, system, temperature, comp), kind


def _record_configuration(record: dict, tokens: list[str], reg: PhaseRegistry) -> dict:
    out: dict = {}
    phases = [p for p in record.get("phases") or [] if isinstance(p, dict)]
    for phase, token in zip(phases, tokens):
        found: dict = {}
        if phase.get("structure_basis") == "printed_source_page":
            found.update(reg.distinguishing({"pearson": phase.get("pearson_symbol"), "prototype": phase.get("prototype")}, token))
        label = str(phase.get("label") or "")
        terms = sorted({norm_designator(m.group(1)) for m in CONFIG_TERM.finditer(label)} - reg.structure.get(token, set()))
        if terms:
            found["label_terms"] = terms
        if ":" in label:
            found["sublattice_label"] = label
        if found:
            out[token] = found
    structure = record.get("structure")
    if isinstance(structure, dict):
        target = tokens[0] if len(tokens) == 1 else ""
        found = reg.distinguishing({k: structure.get(k) for k in ("pearson_symbol", "prototype", "space_group", "strukturbericht")}, target)
        if found:
            out["structure"] = found
    return out


def _finalize_configuration(coordinates: dict, phases: list[str], system: str, reg: PhaseRegistry) -> dict:
    if phases_unknown(phases):
        return coordinates
    config = dict(coordinates.get("configuration") or {})
    if config.get("space_group") is not None:
        return coordinates
    printed = set(config) | ({phases[0]} if "structure" in config and len(phases) == 1 else set())
    assumed = sorted(t for t in set(phases) if t not in printed and reg.phase_order_reason(t, system) is None)
    if assumed:
        config["assumed"] = {**ASSUMED_RANDOM, "phases": assumed}
        coordinates = {**coordinates, "configuration": config}
    return coordinates


def _coordinate_missing(rule: str, coordinates: dict, system: str, raw_T: Any) -> bool:
    rule = rule or R_NONE
    if rule == R_INVARIANT and raw_T is None:
        return True  # an invariant or transition printed without temperature stands alone
    if rule in {R_INVARIANT, R_ENVELOPE}:
        return False
    if rule == R_NONE:
        return True
    unary = len(system.split("-")) == 1
    c = coordinates
    return c.get("T_K", c.get("T_cell_K")) is None or (not (c.get("x") or c.get("x_cells")) and not unary)


def state_descriptors(record: dict, registry: PhaseRegistry | None = None, observation_id: str | None = None) -> dict:
    """Class and state descriptors of one observation in literature-record form (literature/SCHEMA.md fields: system,
    observation_type, property, phases[{label, model_phase, ...}], temperature_K, pressure_Pa, overall_composition,
    transition_kind, structure). observation_id: the record's ORC id (enters only an unresolved state)."""
    reg = registry or PhaseRegistry()
    system = str(record.get("system") or "UNKNOWN")
    tokens_all = [reg.resolve(system, p) for p in record.get("phases") or [] if isinstance(p, (dict, str))]
    phases = sorted({t for t, _ in tokens_all})
    bases = sorted({b for _, b in tokens_all})
    eq = equilibrium_type(record, len(phases))
    pclass = pressure_class(record.get("pressure_Pa") or record.get("P_Pa"))
    coordinates, rule = _coord_rule_2(record, eq, system, phases, reg)
    configuration = _record_configuration(record, [t for t, _ in tokens_all], reg)
    if configuration:
        coordinates = {**coordinates, "configuration": configuration}
    coordinates = _finalize_configuration(coordinates, phases, system, reg)
    temperature = record.get("temperature_K")
    raw_T = float(temperature) if temperature is not None else None
    dependent = []
    if rule == R_INVARIANT and raw_T is not None:
        low, high = PLAUSIBLE_T_K
        if not low < raw_T <= high:
            coordinates = {**coordinates, "reading_alone": str(observation_id or record.get("id"))}
            dependent.append("invariant_ledger")  # a new reading outside 1 < T <= 6000 K stands alone; a ledger one keeps its issued id
        else:
            dependent.append("invariant_reaction_group")
    if rule == R_BOUNDARY:
        dependent.append("boundary_vs_field_point_reconciliation")
    if rule not in {R_INVARIANT, R_ENVELOPE, R_NONE}:
        dependent.append("near_identical_merge")
    cls: dict = {"system": system, "phases": phases, "pressure_class": pclass}
    unresolved = phases_unknown(phases) or _coordinate_missing(rule, coordinates, system, raw_T)
    if unresolved:
        cls["unresolved_observation"] = str(observation_id or record.get("id"))
        dependent = [d for d in dependent if d != "near_identical_merge"]
    state = {**cls, "coordinates": coordinates, "assignment_rule": rule}
    out = {"class_descriptor": cls, "state_descriptor": state, "assignment_rule": rule, "equilibrium_type": eq,
           "phase_resolution": bases, "unresolved": unresolved, "registry_dependent": dependent,
           "phase_registry_loaded": reg.loaded, "phase_registry_version": reg.version}
    if "invariant_reaction_group" in dependent and not unresolved:
        # a NEW reading (build_registry.assign_new_readings) takes the id of a compatible group within 46 K (the
        # ungrouped id when the phase set has one group), or, when the phase set already has groups and none is near,
        # founds its own group at its own temperature
        kind = record.get("transition_kind")
        kind = "unstated" if kind in UNSTATED_KINDS else kind
        founded = {**state, "coordinates": {**coordinates, "reaction_group": {"kind": kind, "founding_T_K": exact(raw_T, 2)}}}
        out["alternative_state_descriptors"] = [founded]
    return out


# ------------------------------------------------------------------ coord-rule/3 (PI decisions of 6 Nov 2026)
RULE3 = "coord-rule/3"
R3_INVARIANT = RULE3 + ":invariant-5K-kind"
R3_NONE = RULE3 + ":no-coordinates"
R3_BOUNDARY = RULE3 + ":boundary-5K-0.02x"
R3_FIELD = RULE3 + ":field-point-10K-0.02x"
R3_COMPOUND = RULE3 + ":compound-1K-exact-x"
R3_SOLUTION = RULE3 + ":solution-exact"
R3_ZERO = RULE3 + ":0K-exact-x"
INVARIANT_CELL_K = 5.0  # the boundary cell of coord-rule/2 (a proposal: docs/ID_SCHEME.md section 4)
ASSUMED_PRESSURE_BASES = ("assumed", "unstated")


def _dec(value: Any) -> Decimal | None:
    """The decimal value as written: a string as it is, a float by its shortest repr (0.55 -> Decimal('0.55'))."""
    if value is None or isinstance(value, bool):
        return None
    try:
        d = Decimal(value.strip()) if isinstance(value, str) else Decimal(repr(float(value)))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return d if d.is_finite() else None


def dround(value: Any, step: float) -> float | None:
    """Cell centre by decimal round-half-even of value/step (PI 6 Nov 2026: decimal, not binary floating point)."""
    d = _dec(value)
    if d is None:
        return None
    st = Decimal(str(step))
    return float((d / st).to_integral_value(rounding=ROUND_HALF_EVEN) * st)


def dexact(value: Any, digits: int) -> float | None:
    d = _dec(value)
    return None if d is None else float(d.quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_EVEN))


def canonical_x_decimal(system: str, comp: dict) -> dict:
    """canonical_x with the complement 1 - x taken in decimal arithmetic."""
    elements = system.split("-")
    comp = {str(k).upper(): v for k, v in comp.items() if v is not None}
    if not comp:
        return {}
    if len(elements) == 2 and len(comp) == 1 and set(comp) <= set(elements):
        key, v = next(iter(comp.items()))
        return {elements[1]: v if key == elements[1] else str(Decimal(1) - _dec(v))}
    if set(comp) == set(elements) and abs(sum(float(v) for v in comp.values()) - 1.0) <= 0.01:
        return {k: v for k, v in sorted(comp.items()) if k != elements[0]}
    return dict(sorted(comp.items()))


def pressure_class_unassumed(record: dict) -> str:
    """Pressure class, 'unknown' when no pressure is given or the stored one is an assumed default (PI 6 Nov 2026:
    do not assume 101325 Pa)."""
    basis = str(record.get("pressure_basis") or "")
    if basis.startswith(ASSUMED_PRESSURE_BASES):
        return "unknown"
    return pressure_class(record.get("pressure_Pa") if record.get("pressure_Pa") is not None else record.get("P_Pa"))


def reaction_kind(record: dict) -> str:
    kind = record.get("transition_kind")
    return "unstated" if kind in UNSTATED_KINDS else str(kind)


def _coord_rule_3(record: dict, eq: str, system: str, phases: list[str], reg: PhaseRegistry) -> tuple[dict, str]:
    temperature = record.get("temperature_K", record.get("T_K"))
    if eq in {"invariant", "transition"}:
        if temperature is None:
            return {}, R3_INVARIANT
        return {"T_cell_K": dround(temperature, INVARIANT_CELL_K), "reaction_kind": reaction_kind(record)}, R3_INVARIANT
    comp = composition_dict(record)
    if not comp and record.get("x") is not None and record.get("x_component"):
        comp = {str(record["x_component"]).upper(): record["x"]}
    if any(record.get(k) not in (None, "", [], {}) for k in ("temperature_range_K", "T_range", "composition_range", "x_range")):
        return {}, R3_NONE
    if temperature is None and not comp:
        return {}, R3_NONE
    x = canonical_x_decimal(system, comp)
    if temperature is not None and float(temperature) == 0.0:
        kind = R3_ZERO
    elif record.get("observation_type") == "phase_assemblage_node":
        kind = R3_FIELD
    elif eq in {"liquidus", "solidus", "solvus", "two_phase_field", "single_phase_field", "phase_field"}:
        kind = R3_BOUNDARY
    else:
        kind = R3_COMPOUND if len(phases) == 1 and phases[0] in reg.stoichiometric else R3_SOLUTION
    if kind == R3_BOUNDARY:
        return {"T_cell_K": dround(temperature, 5.0), "x_cells": {k: dround(v, 0.02) for k, v in x.items()}}, kind
    if kind == R3_FIELD:
        return {"T_cell_K": dround(temperature, 10.0), "x_cells": {k: dround(v, 0.02) for k, v in x.items()}}, kind
    if kind == R3_COMPOUND:
        return {"T_cell_K": dround(temperature, 1.0), "x": {k: dexact(v, 4) for k, v in x.items()}}, kind
    return {"T_K": dexact(temperature, 2), "x": {k: dexact(v, 4) for k, v in x.items()}}, kind


def _coordinate_missing_3(rule: str, coordinates: dict, system: str, raw_T: Any) -> bool:
    if rule == R3_INVARIANT:
        return raw_T is None
    if rule == R3_NONE:
        return True
    unary = len(system.split("-")) == 1
    c = coordinates
    return c.get("T_K", c.get("T_cell_K")) is None or (not (c.get("x") or c.get("x_cells")) and not unary)


def state_descriptors_3(record: dict, registry: PhaseRegistry | None = None, observation_id: str | None = None) -> dict:
    """coord-rule/3 (PI decisions of 6 Nov 2026), a pure function of the record and the phase-registry release:
    coord-rule/2 plus (1) invariants and transitions keep their own temperature, quantised to a 5 K cell, with the
    printed reaction kind; no ledger groups; (2) the SGTE reference state (SER of the system's elements) in the class
    descriptor; (3) decimal round-half-even; (4) pressure class 'unknown' when no pressure is printed. No boundary /
    field-point reconciliation and no near-identical merges: those become graph edges."""
    from .reference import reference_status, ser_reference_state  # local import: reference.py imports nothing from here
    reg = registry or PhaseRegistry()
    system = str(record.get("system") or "UNKNOWN")
    tokens_all = [reg.resolve(system, p) for p in record.get("phases") or [] if isinstance(p, (dict, str))]
    phases = sorted({t for t, _ in tokens_all})
    eq = equilibrium_type(record, len(phases))
    coordinates, rule = _coord_rule_3(record, eq, system, phases, reg)
    configuration = _record_configuration(record, [t for t, _ in tokens_all], reg)
    if configuration:
        coordinates = {**coordinates, "configuration": configuration}
    coordinates = _finalize_configuration(coordinates, phases, system, reg)
    temperature = record.get("temperature_K")
    raw_T = float(temperature) if temperature is not None else None
    if rule == R3_INVARIANT and raw_T is not None and not PLAUSIBLE_T_K[0] < raw_T <= PLAUSIBLE_T_K[1]:
        coordinates = {k: v for k, v in coordinates.items() if k != "T_cell_K"}
        coordinates["reading_alone"] = str(observation_id or record.get("id"))
    cls: dict = {"system": system, "phases": phases, "pressure_class": pressure_class_unassumed(record),
                 "reference_state": ser_reference_state(system)}
    unresolved = phases_unknown(phases) or _coordinate_missing_3(rule, coordinates, system, raw_T)
    if unresolved:
        cls["unresolved_observation"] = str(observation_id or record.get("id"))
    state = {**cls, "coordinates": coordinates, "assignment_rule": rule}
    ref = reference_status(record)
    flags = []
    if cls["reference_state"] is None:
        flags.append("no_sgte_ser_for_an_element")
    if ref["status"] in ("convertible", "needs_reading", "not_convertible", "missing"):
        flags.append("value_reference_" + ref["status"])
    return {"class_descriptor": cls, "state_descriptor": state, "assignment_rule": rule, "equilibrium_type": eq,
            "phase_resolution": sorted({b for _, b in tokens_all}), "unresolved": unresolved, "registry_dependent": [],
            "phase_registry_loaded": reg.loaded, "phase_registry_version": reg.version,
            "value_reference": ref, "flags": flags}


def compute_state_id(state: dict, registry: PhaseRegistry | None = None, observation_id: str | None = None,
                     rule: str = RULE3) -> dict:
    """S- and C- ids of a state. ``state``: a literature-form record (see state_descriptors), or already-built
    descriptors {"class_descriptor": ..., "state_descriptor": ...}. rule: "coord-rule/3" (default; PI decisions of
    6 Nov 2026, proposed for v2027.01) or "coord-rule/2" (reproduces the current v2027.01-candidate registry).
    Returns ids, descriptors and what keeps the id provisional."""
    if rule not in (RULE3, RULE_VERSION):
        raise ValueError(f"unknown rule {rule!r}: {RULE3} or {RULE_VERSION}")
    if "state_descriptor" in state and "class_descriptor" in state:
        d = {"class_descriptor": state["class_descriptor"], "state_descriptor": state["state_descriptor"],
             "registry_dependent": [], "phase_registry_loaded": None}
    elif rule == RULE3:
        d = state_descriptors_3(state, registry, observation_id)
    else:
        d = state_descriptors(state, registry, observation_id)
    out = dict(d)
    out["state_class_id"] = descriptor_id("C-", d["class_descriptor"])
    out["state_id"] = descriptor_id("S-", d["state_descriptor"])
    if d.get("alternative_state_descriptors"):
        out["alternative_state_ids"] = [descriptor_id("S-", a) for a in d["alternative_state_descriptors"]]
    out["rule_version"] = rule
    notes = []
    if d.get("phase_registry_loaded") is False:
        notes.append("no phase registry loaded: phases resolve to label:/model: tokens, so ids differ from ORCHID's for "
                     "every phase the registry knows; load phases/registry.json")
    if d.get("registry_dependent"):
        notes.append("the registry may still place this observation differently: " + ", ".join(d["registry_dependent"]))
    if d.get("unresolved"):
        notes.append("unresolved observation (unknown phases, or missing T or composition): the state is this "
                     "observation alone and its descriptor holds the record id")
    if rule == RULE3:
        notes.append("coord-rule/3 is the rule decided on 6 Nov 2026 for v2027.01; the candidate registry is still on "
                     "coord-rule/2 until it is rebuilt")
        if any(f.startswith("value_reference_") for f in d.get("flags") or []):
            notes.append("the value is not on the SGTE reference (" + (d.get("value_reference") or {}).get("status", "") +
                         "): convert it to SER before intake, keeping the original as provenance; the id is SER-based")
    out["notes"] = notes
    return out


def contribution_to_record(row: dict, observation_id: str | None = None) -> dict:
    """A contributed value (contributions/SCHEMA.md row: system, property, state{phases, temperature_K, pressure_Pa,
    overall_composition, ...}) in the form the registry reads it today (build_registry.contributed_claims): no
    observation_type, pressure as given (absent -> pressure class 'unknown'), temperature only from state.temperature_K.
    These differ from orchid_contrib.to_record (101325 Pa default, invariant T from the value): docs/ID_SCHEME.md, gaps."""
    st = row.get("state") or {}
    return {
        "id": observation_id, "system": row["system"], "property": row.get("property"),
        "phases": st.get("phases") or [], "temperature_K": st.get("temperature_K"),
        "pressure_Pa": st.get("pressure_Pa"), "overall_composition": st.get("overall_composition"),
    }
