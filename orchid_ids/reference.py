"""SGTE reference states (PI 6 Nov 2026): ORCHID states are on the SGTE stable element reference (SER).

"The whole point of ORCHID is that we use SGTE reference states to guarantee compatibility with other CALPHAD
databases." The id descriptor of every state carries the SER of the system's elements, in the form of the literature
field `reference_state` ({EL: {phase, fixed_state_variables}}). A value printed on another reference is converted to
SER before it enters (the original value and reference stay as provenance: `reference_state_stored`,
`corrections[].evidence.conversion`, literature/SCHEMA.md); a value that cannot be converted is flagged, never given
another reference in its id.

Data: the ELEMENT lines (SER phase of each element) and the pure-element phases with a Gibbs-energy parameter
G(PHASE,EL) in the SGTE Unary Database V5.0 (2 June 2009, Hallstedt reformatting; open-tdb
databases/sgte-binary/unary50_bengt.tdb). Element names and phase names are facts, listed here without the functions.
"""
from __future__ import annotations

SGTE_UNARY = "SGTE Unary Database V5.0"
SER_T_K = 298.15
SER_P_PA = 100000
SER_PHASE = {"AG": "FCC_A1", "AL": "FCC_A1", "AM": "DHCP", "AS": "RHOMBOHEDRAL_A7", "AU": "FCC_A1", "B": "BETA_RHOMBO_B", "BA": "BCC_A2", "BE": "HCP_A3", "BI": "RHOMBOHEDRAL_A7", "BR": "1/2_MOLE_BR2(LIQ)", "C": "GRAPHITE", "CA": "FCC_A1", "CD": "HCP_A3", "CE": "FCC_A1", "CL": "1/2_MOLE_CL2(G)", "CO": "HCP_A3", "CR": "BCC_A2", "CS": "BCC_A2", "CU": "FCC_A1", "DY": "HCP_A3", "ER": "HCP_A3", "EU": "BCC_A2", "F": "1/2_MOLE_F2(G)", "FE": "BCC_A2", "GA": "ORTHORHOMBIC_A11", "GD": "HCP_A3", "GE": "DIAMOND_A4", "H": "1/2_MOLE_H2(G)", "HF": "HCP_A3", "HG": "LIQUID", "HO": "HCP_A3", "I": "ORTHORHOMBIC_?", "IN": "TETRAGONAL_A6", "IR": "FCC_A1", "K": "BCC_A2", "LA": "DHCP", "LI": "BCC_A2", "LU": "HCP_A3", "MG": "HCP_A3", "MN": "CBCC_A12", "MO": "BCC_A2", "N": "1/2_MOLE_N2(G)", "NA": "BCC_A2", "NB": "BCC_A2", "ND": "DHCP", "NI": "FCC_A1", "NP": "ORTHO_AC", "O": "1/2_MOLE_O2(G)", "OS": "HCP_A3", "P": "WHITE_P", "PA": "BCT_AA", "PB": "FCC_A1", "PD": "FCC_A1", "PR": "DHCP", "PT": "FCC_A1", "PU": "ALPHA_PU", "RB": "BCC_A2", "RE": "HCP_A3", "RH": "FCC_A1", "RU": "HCP_A3", "S": "ORTHORHOMBIC_S", "SB": "RHOMBOHEDRAL_A7", "SC": "HCP_A3", "SE": "HEXAGONAL_A8", "SI": "DIAMOND_A4", "SM": "RHOMB_C19", "SN": "BCT_A5", "SR": "FCC_A1", "TA": "BCC_A2", "TB": "HCP_A3", "TC": "HCP_A3", "TE": "HEXAGONAL_A8", "TH": "FCC_A1", "TI": "HCP_A3", "TL": "HCP_A3", "TM": "HCP_A3", "U": "ORTHORHOMBIC_A20", "V": "BCC_A2", "W": "BCC_A2", "Y": "HCP_A3", "YB": "FCC_A1", "ZN": "HCP_A3", "ZR": "HCP_A3"}
UNARY_PHASES = {"AG": ["BCC_A2", "BCT_A5", "CUB_A13", "DHCP", "DIAMOND_A4", "FCC_A1", "HCP_A3", "LIQUID"], "AL": ["ALPHA_PU", "BCC_A2", "BCT_A5", "BETA_RHOMBO_B", "CBCC_A12", "CUB_A13", "DHCP", "DIAMOND_A4", "FCC_A1", "GAMMA_PU", "HCP_A3", "LIQUID", "ORTHORHOMBIC_A20", "RHOMB_C19", "TETRAGONAL_A6", "TETRAGONAL_U"], "AM": ["ALPHA_PU", "BCC_A2", "BETA_PU", "DHCP", "FCC_A1", "GAMMA_PU", "HCP_A3", "LIQUID", "ORTHORHOMBIC_A20", "ORTHO_AC", "TETRAGONAL_A6", "TETRAGONAL_U", "TETRAG_AD"], "AS": ["BCC_A2", "DIAMOND_A4", "FCC_A1", "HCP_A3", "LIQUID", "ORTHORHOMBIC_A20", "RED_P", "RHOMBOHEDRAL_A7", "TETRAGONAL_U"], "AU": ["BCC_A2", "BCT_A5", "DHCP", "DIAMOND_A4", "FCC_A1", "HCP_A3", "LIQUID", "RHOMBOHEDRAL_A7"], "B": ["ALPHA_RHOMBO_B", "BCC_A2", "BETA_RHOMBO_B", "DIAMOND_A4", "FCC_A1", "GRAPHITE", "HCP_A3", "LIQUID"], "BA": ["BCC_A2", "FCC_A1", "HCP_A3", "LIQUID", "RHOMBOHEDRAL_A7"], "BE": ["BCC_A2", "FCC_A1", "HCP_A3", "LIQUID"], "BI": ["BCC_A2", "BCT_A5", "DHCP", "DIAMOND_A4", "FCC_A1", "HCP_A3", "LIQUID", "ORTHORHOMBIC_A20", "RHOMBOHEDRAL_A7", "RHOMBO_A10", "TETRAGONAL_A6", "TETRAGONAL_U", "TET_ALPHA1_A6"], "C": ["DIAMOND_A4", "GRAPHITE", "LIQUID"], "CA": ["BCC_A2", "BCT_A5", "FCC_A1", "HCP_A3", "LIQUID"], "CD": ["BCC_A2", "BCT_A5", "DHCP", "FCC_A1", "HCP_A3", "HCP_IM_A3", "LIQUID", "RHOMBO_A10", "TETRAGONAL_A6"], "CE": ["BCC_A2", "CUB_A13", "DHCP", "FCC_A1", "HCP_A3", "LIQUID"], "CO": ["BCC_A2", "CBCC_A12", "CUB_A13", "DHCP", "FCC_A1", "HCP_A3", "LIQUID", "RHOMB_C19"], "CR": ["BCC_A2", "CBCC_A12", "CUB_A13", "DIAMOND_A4", "FCC_A1", "HCP_A3", "LIQUID", "TETRAGONAL_U"], "CS": ["BCC_A2", "FCC_A1", "HCP_A3", "LIQUID"], "CU": ["ALPHA_PU", "BCC_A2", "BCT_A5", "BETA_PU", "BETA_RHOMBO_B", "CBCC_A12", "CUB_A13", "FCC_A1", "GAMMA_PU", "HCP_A3", "LIQUID", "ORTHORHOMBIC_A20", "TETRAGONAL_A6", "TETRAGONAL_U"], "DY": ["BCC_A2", "CBCC_A12", "CUB_A13", "FCC_A1", "HCP_A3", "LIQUID"], "ER": ["BCC_A2", "FCC_A1", "HCP_A3", "LIQUID"], "EU": ["BCC_A2", "FCC_A1", "LIQUID", "TETRAGONAL_A6"], "FE": ["ALPHA_PU", "BCC_A2", "BETA_PU", "CBCC_A12", "CUB_A13", "DHCP", "DIAMOND_A4", "FCC_A1", "GAMMA_PU", "HCP_A3", "LIQUID", "ORTHORHOMBIC_A20", "ORTHO_AC", "RHOMBOHEDRAL_A7", "RHOMB_C19", "TETRAGONAL_A6", "TETRAGONAL_U", "TETRAG_AD"], "GA": ["ALPHA_PU", "BCC_A2", "BCT_A5", "DHCP", "DIAMOND_A4", "FCC_A1", "GAMMA_PU", "HCP_A3", "LIQUID", "ORTHORHOMBIC_A11", "ORTHORHOMBIC_A20", "TETRAGONAL_A6", "TETRAGONAL_U"], "GD": ["BCC_A2", "FCC_A1", "HCP_A3", "LIQUID", "RHOMB_C19"], "GE": ["BCC_A2", "BCT_A5", "CUB_A13", "DIAMOND_A4", "FCC_A1", "HCP_A3", "LIQUID", "RHOMBOHEDRAL_A7"], "H": ["GAS", "LIQUID"], "HF": ["BCC_A2", "CBCC_A12", "CUB_A13", "FCC_A1", "HCP_A3", "LIQUID"], "HG": ["BCC_A2", "FCC_A1", "GAMMA_PU", "HCP_A3", "LIQUID", "RHOMBO_A10", "TETRAGONAL_A6"], "HO": ["BCC_A2", "CBCC_A12", "CUB_A13", "FCC_A1", "HCP_A3", "LIQUID"], "IN": ["BCC_A2", "BCT_A5", "CBCC_A12", "CUB_A13", "DHCP", "DIAMOND_A4", "FCC_A1", "GAMMA_PU", "HCP_A3", "LIQUID", "RHOMBOHEDRAL_A7", "RHOMBO_A10", "TETRAGONAL_A6", "TET_ALPHA1_A6"], "IR": ["BCC_A2", "FCC_A1", "HCP_A3", "LIQUID"], "K": ["BCC_A2", "FCC_A1", "HCP_A3", "LIQUID"], "LA": ["BCC_A2", "CBCC_A12", "CUB_A13", "DHCP", "FCC_A1", "HCP_A3", "HEXAGONAL_A8", "LIQUID", "TETRAGONAL_A6"], "LI": ["BCC_A2", "CBCC_A12", "CUB_A13", "FCC_A1", "HCP_A3", "LIQUID", "TETRAGONAL_A6"], "LU": ["FCC_A1", "HCP_A3", "LIQUID"], "MG": ["ALPHA_PU", "BCC_A2", "BETA_PU", "CBCC_A12", "CUB_A13", "DHCP", "DIAMOND_A4", "FCC_A1", "GAMMA_PU", "HCP_A3", "LIQUID", "RHOMB_C19", "TETRAGONAL_A6"], "MN": ["BCC_A2", "CBCC_A12", "CUB_A13", "DHCP", "DIAMOND_A4", "FCC_A1", "HCP_A3", "LIQUID", "RHOMB_C19", "TETRAGONAL_U"], "MO": ["BCC_A2", "BETA_RHOMBO_B", "CBCC_A12", "CUB_A13", "FCC_A1", "HCP_A3", "LIQUID", "OMEGA_C32", "ORTHORHOMBIC_A20", "TETRAGONAL_U"], "N": ["LIQUID"], "NA": ["BCC_A2", "FCC_A1", "HCP_A3", "LIQUID", "TETRAGONAL_A6"], "NB": ["BCC_A2", "CBCC_A12", "CUB_A13", "DIAMOND_A4", "FCC_A1", "HCP_A3", "LIQUID", "OMEGA_C32", "ORTHORHOMBIC_A20", "RHOMBOHEDRAL_A7", "TETRAGONAL_U"], "ND": ["BCC_A2", "DHCP", "FCC_A1", "HCP_A3", "LIQUID", "RHOMBOHEDRAL_A7"], "NI": ["BCC_A2", "BCT_A5", "CBCC_A12", "CUB_A13", "DHCP", "DIAMOND_A4", "FCC_A1", "HCP_A3", "LIQUID", "ORTHORHOMBIC_A20", "TETRAGONAL_U"], "NP": ["ALPHA_PU", "BCC_A2", "BETA_PU", "DHCP", "FCC_A1", "GAMMA_PU", "HCP_A3", "LIQUID", "ORTHORHOMBIC_A20", "ORTHO_AC", "TETRAGONAL_A6", "TETRAGONAL_U", "TETRAG_AD"], "O": ["BCC_A2", "DIAMOND_A4", "FCC_A1", "HCP_A3", "LIQUID"], "OS": ["BCC_A2", "FCC_A1", "HCP_A3", "LIQUID"], "P": ["BCC_A2", "CBCC_A12", "CUB_A13", "DIAMOND_A4", "FCC_A1", "LIQUID", "RED_P", "RHOMBOHEDRAL_A7", "WHITE_P"], "PA": ["BCC_A2", "BCT_AA", "LIQUID"], "PB": ["BCC_A2", "BCT_A5", "DIAMOND_A4", "FCC_A1", "HCP_A3", "LIQUID", "ORTHORHOMBIC_A20", "RHOMBOHEDRAL_A7", "RHOMBO_A10", "TETRAGONAL_A6", "TETRAGONAL_U", "TET_ALPHA1_A6"], "PD": ["BCC_A2", "BCT_A5", "CBCC_A12", "CUB_A13", "DIAMOND_A4", "FCC_A1", "HCP_A3", "LIQUID", "RHOMBOHEDRAL_A7", "RHOMB_C19"], "PR": ["BCC_A2", "DHCP", "FCC_A1", "HCP_A3", "LIQUID"], "PT": ["BCC_A2", "FCC_A1", "HCP_A3", "LIQUID", "RHOMBOHEDRAL_A7", "TETRAGONAL_A6"], "PU": ["ALPHA_PU", "BCC_A2", "BETA_PU", "DHCP", "FCC_A1", "GAMMA_PU", "HCP_A3", "LIQUID", "ORTHORHOMBIC_A20", "ORTHO_AC", "TETRAGONAL_A6", "TETRAGONAL_U", "TETRAG_AD"], "RB": ["BCC_A2", "FCC_A1", "HCP_A3", "LIQUID"], "RE": ["BCC_A2", "FCC_A1", "HCP_A3", "LIQUID", "TETRAGONAL_U"], "RH": ["BCC_A2", "FCC_A1", "HCP_A3", "LIQUID"], "RU": ["BCC_A2", "DIAMOND_A4", "FCC_A1", "HCP_A3", "LIQUID", "TETRAGONAL_U"], "S": ["BCC_A2", "BCT_A5", "DIAMOND_A4", "FCC_A1", "HCP_A3", "HEXAGONAL_A8", "LIQUID", "MONOCLINIC", "ORTHORHOMBIC_S"], "SB": ["BCC_A2", "BCT_A5", "CBCC_A12", "CUB_A13", "DHCP", "DIAMOND_A4", "FCC_A1", "HCP_A3", "HEXAGONAL_A8", "LIQUID", "RHOMBOHEDRAL_A7", "TETRAGONAL_A6"], "SC": ["BCC_A2", "BETA_RHOMBO_B", "DHCP", "FCC_A1", "HCP_A3", "LIQUID"], "SE": ["FCC_A1", "HEXAGONAL_A8", "LIQUID", "MONOCLINIC_S", "ORTHORHOMBIC_A16"], "SI": ["BCC_A2", "BETA_RHOMBO_B", "CBCC_A12", "CUB_A13", "DIAMOND_A4", "FCC_A1", "HCP_A3", "LIQUID", "ORTHORHOMBIC_A20", "TETRAGONAL_U"], "SM": ["BCC_A2", "CBCC_A12", "CUB_A13", "FCC_A1", "HCP_A3", "LIQUID", "RHOMB_C19"], "SN": ["BCC_A2", "BCT_A5", "CBCC_A12", "CUB_A13", "DHCP", "DIAMOND_A4", "FCC_A1", "HCP_A3", "LIQUID", "ORTHORHOMBIC_A16", "ORTHORHOMBIC_A20", "RHOMBOHEDRAL_A7", "TETRAGONAL_A6", "TETRAGONAL_U", "TET_ALPHA1_A6"], "SR": ["BCC_A2", "BCT_A5", "DHCP", "DIAMOND_A4", "FCC_A1", "HCP_A3", "LIQUID"], "TA": ["BCC_A2", "CBCC_A12", "CUB_A13", "DIAMOND_A4", "FCC_A1", "HCP_A3", "LIQUID"], "TB": ["BCC_A2", "FCC_A1", "HCP_A3", "LIQUID"], "TC": ["BCC_A2", "FCC_A1", "HCP_A3", "LIQUID"], "TE": ["BCC_A2", "DHCP", "FCC_A1", "HCP_A3", "HEXAGONAL_A8", "LIQUID", "RHOMBOHEDRAL_A7"], "TH": ["BCC_A2", "FCC_A1", "HCP_A3", "LIQUID", "ORTHORHOMBIC_A20", "TETRAGONAL_A6", "TETRAGONAL_U"], "TI": ["BCC_A2", "BCT_A5", "BETA_RHOMBO_B", "CBCC_A12", "CUB_A13", "DHCP", "DIAMOND_A4", "FCC_A1", "HCP_A3", "LIQUID", "OMEGA_C32", "ORTHORHOMBIC_A20", "RHOMB_C19", "TETRAGONAL_U"], "TL": ["BCC_A2", "DIAMOND_A4", "FCC_A1", "HCP_A3", "LIQUID"], "TM": ["BCC_A2", "FCC_A1", "HCP_A3", "LIQUID", "RHOMBOHEDRAL_A7"], "U": ["ALPHA_PU", "BCC_A2", "BCT_A5", "BETA_PU", "CUB_A13", "DHCP", "FCC_A1", "GAMMA_PU", "HCP_A3", "LIQUID", "ORTHORHOMBIC_A11", "ORTHORHOMBIC_A20", "ORTHO_AC", "RHOMBOHEDRAL_A7", "TETRAGONAL_A6", "TETRAGONAL_U", "TETRAG_AD"], "V": ["BCC_A2", "CBCC_A12", "CUB_A13", "FCC_A1", "HCP_A3", "LIQUID", "OMEGA_C32", "TETRAGONAL_U"], "W": ["BCC_A2", "CBCC_A12", "CUB_A13", "FCC_A1", "HCP_A3", "LIQUID", "TETRAGONAL_U"], "Y": ["BCC_A2", "DHCP", "FCC_A1", "HCP_A3", "LIQUID"], "YB": ["BCC_A2", "DIAMOND_A4", "FCC_A1", "HCP_A3", "LIQUID", "RHOMBOHEDRAL_A7", "TETRAGONAL_A6"], "ZN": ["BCC_A2", "BCT_A5", "CBCC_A12", "CUB_A13", "DHCP", "DIAMOND_A4", "FCC_A1", "HCP_A3", "LIQUID", "RHOMBOHEDRAL_A7", "RHOMBO_A10", "RHOMB_C19", "TETRAGONAL_A6"], "ZR": ["ALPHA_PU", "BCC_A2", "BETA_PU", "CBCC_A12", "CUB_A13", "DHCP", "FCC_A1", "GAMMA_PU", "HCP_A3", "LIQUID", "OMEGA_C32", "ORTHORHOMBIC_A20", "ORTHO_AC", "TETRAGONAL_A6", "TETRAGONAL_U", "TETRAG_AD"]}
# properties whose value depends on the reference state (contributions/SCHEMA.md: formation, mixing, partial
# quantities, chemical potentials; activities and EMF are relative to the reference of the component)
REFERENCE_DEPENDENT = ("HM_FORM", "GM_FORM", "SM_FORM", "HM_MIX", "GM_MIX", "SM_MIX", "PARTIAL_ENTHALPY",
                       "G_EXCESS_PARTIAL", "CHEMICAL_POTENTIAL", "ACTIVITY", "ACTIVITY_COEFFICIENT", "EMF")
# spellings of the same pure-element phase in other TDB files (structure designator first, or the element's own
# structure name); only names that denote the same SGTE unary phase
PHASE_ALIASES = {"A1_FCC": "FCC_A1", "A2_BCC": "BCC_A2", "A3_HCP": "HCP_A3", "DIA_A4": "DIAMOND_A4", "DIAMOND": "DIAMOND_A4",
                 "GRAPHITE_A9": "GRAPHITE", "ORTHORHOMBIC_GA": "ORTHORHOMBIC_A11", "LIQ": "LIQUID", "L": "LIQUID"}
_SER_WORDS = ("stable element reference", "(ser)", " ser ", "ghser", "ser,", "ser)")


def ser_reference_state(system: str) -> dict | None:
    """SER of every element of a system, as the descriptor's reference_state; None when an element has no SGTE SER."""
    els = [e for e in str(system).upper().split("-") if e]
    if not els or any(e not in SER_PHASE for e in els):
        return None
    return {e: {"phase": SER_PHASE[e], "fixed_state_variables": {"P": SER_P_PA, "T": SER_T_K}} for e in els}


def reference_dependent(prop) -> bool:
    p = str(prop or "").upper()
    return p in REFERENCE_DEPENDENT or p.startswith(("ACR_", "MU_", "HM_PARTIAL", "GM_PARTIAL"))


def reference_status(record: dict) -> dict:
    """How a record's stated reference relates to SER. status:
    not_applicable (property does not depend on a reference) | ser | convertible (every non-SER entry is a pure-element
    phase of the SGTE unary, so the value converts with the unary lattice stabilities at the record's T) |
    needs_reading (printed text only, a phase field holding text, or a missing phase) | not_convertible (a phase the
    unary does not have, or an element without an SGTE SER) | missing (reference-dependent property, no reference)."""
    prop = record.get("property")
    ref = record.get("reference_state")
    if not reference_dependent(prop):
        return {"status": "not_applicable", "entries": {}}
    if not ref:
        return {"status": "missing", "entries": {}}
    if "printed" in ref and len(ref) == 1:
        text = " " + str(ref["printed"]).lower() + " "
        return {"status": "ser" if any(w in text for w in _SER_WORDS) else "needs_reading", "entries": {"printed": ref["printed"]},
                "basis": "printed_text"}
    entries, worst = {}, "ser"
    order = ["ser", "convertible", "needs_reading", "not_convertible"]
    for el, v in ref.items():
        e = str(el).upper()
        ph = str((v or {}).get("phase") or "").upper()
        ph = PHASE_ALIASES.get(ph, ph)
        if e not in SER_PHASE:
            s = "not_convertible"
        elif not ph or ph.startswith("PRINTED"):
            s = "ser" if any(w in " " + ph.lower() + " " for w in _SER_WORDS) else "needs_reading"
        elif ph == SER_PHASE[e]:
            s = "ser"
        elif ph in UNARY_PHASES.get(e, ()):
            s = "convertible"
        else:
            s = "not_convertible"
        entries[e] = {"phase": ph or None, "status": s, "ser_phase": SER_PHASE.get(e)}
        worst = max(worst, s, key=order.index)
    return {"status": worst, "entries": entries}
