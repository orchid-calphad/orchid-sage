#!/usr/bin/env python3
"""Dashboard data (assessment_results) of crni-paper-fit-step4c-b@1.0.2: the frozen 1.0.0 dashboard data with its STATES blocks
taken from evidence bundle 1.1.0. Standard library only.

  python3 tools/extract_dashboard_data_crni4cb_v102.py OUT.json

1.0.2 changes only the evidence pins of states and states_evaluated (bundle 1.1.0: ZPF vertices converted to x(NI), exclusion
tiers copied from the hinge file the fit read). So this extractor does not re-read the campaign: it loads the frozen
dashboards/crni-paper-fit-step4c-b-1.0.0/dashboard_data.json (sha256 checked) and replaces states_evaluated, states_summary,
evidence_bundle and the two state-file provenance inputs (extract_dashboard_data.states_block on bundle 1.1.0), then the protocol
reference, decisions, banner and next actions. Every other block is copied unchanged."""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orchidproto as op  # noqa: E402
from extract_dashboard_data import ref, finite, states_block  # noqa: E402

ART = "crni-paper-fit-step4c-b"
OLD, NEW = f"{ART}@1.0.0", f"{ART}@1.0.2"
BASE = op.ROOT / f"dashboards/{ART}-1.0.0/dashboard_data.json"
BASE_SHA = "8f5961a42b8cb9f45bf75dc3526a5ef0b7a5839867949182e36f99d9df5c73b1"   # pinned by crni-paper-fit-step4c-b@1.0.0 and @1.0.1
BUNDLE = "1.1.0"


def crni4cb_v102():
    if op.sha256_file(BASE) != BASE_SHA:
        raise SystemExit(f"{BASE} is not the frozen 1.0.0 dashboard data (sha256 differs)")
    d = json.loads(BASE.read_text())
    E = op.ROOT.parent / "assessments" / ART / "evidence"
    rows, ssum, refs = states_block(ART)
    if ssum.get("evidence_bundle_version") != BUNDLE:
        raise SystemExit(f"latest bundle is {ssum.get('evidence_bundle_version')}, expected {BUNDLE}")
    ssum_old = d["states_summary"]
    d["states_evaluated"], d["states_summary"] = rows, ssum
    d["evidence_bundle"] = ref(E / f"MANIFEST@{BUNDLE}.json", "evidence bundle manifest")
    inputs = [i for i in d["provenance"]["inputs"] if not any(f"/evidence/{n}@1.0.0.json" in i["path"] for n in ("states", "states_evaluated"))]
    assert len(inputs) == len(d["provenance"]["inputs"]) - 2
    d["provenance"]["inputs"] = inputs + refs + [ref(BASE, "frozen 1.0.0 dashboard data (every block except the states blocks)"),
                                                 ref(Path(__file__), "this extractor (1.0.2: states blocks of bundle 1.1.0)")]
    d["specific_protocol"] = NEW
    d["id"] = f"{ART}-1.0.2-results"
    d["title"] = d["title"].replace(" - 1.0.0 (10a kink rule, 10c)", " - 1.0.2 (10a kink rule, 10c; evaluated states corrected)")
    d["generated_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(os.environ["SOURCE_DATE_EPOCH"]) if os.environ.get("SOURCE_DATE_EPOCH") else None))
    d["status_banner"] = (f"1.0.2 (draft until PI approval): evaluated states corrected (bundle {BUNDLE}); pick, data and objective unchanged. "
                          f"{ssum['match']} of {ssum['n_states']} states match the calculated assemblage (bundle 1.0.0: {ssum_old['match']}, with 130 "
                          "ZPF states given in x(Cr) placed at x(Ni) = x(Cr)). " + d["status_banner"].replace("Frozen 1.0.0 (draft until PI approval). ", ""))
    d["snapshot"]["note"] = ("1.0.2 review snapshot: the frozen 1.0.0 snapshot with the evaluated states of evidence bundle 1.1.0 "
                             "(ZPF vertices converted to x(Ni); exclusion tiers as the fit read them). " + d["snapshot"]["note"])
    d["decisions"] = op.load_doc(op.ROOT / f"specific/{NEW}.yaml")["decisions"]
    d["next_actions"] = [a.replace(OLD, NEW) for a in d["next_actions"]] + [
        "PI: definition of 'single source' in item 8 (Pugliese only, as in the fit's tiers, or any state without a second source within 3 sigma).",
        "PI: Cr-rich bcc states (Collins 1988, Dench 1963, Svechnikov 1962) and Jette 1934 fcc states that disagree with the pick at their corrected compositions."]
    return d


if __name__ == "__main__":
    out = Path(sys.argv[1])
    doc = finite(crni4cb_v102())
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False, allow_nan=False))
    print(out, round(out.stat().st_size / 1e6, 2), "MB")
