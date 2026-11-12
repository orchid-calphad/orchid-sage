"""Command line: compute ORCHID ids offline.

  python -m orchid_ids namespace --orcid 0000-0002-1825-0097 [--uuid <uuid>]     # new provisional namespace
  python -m orchid_ids record --pid 'local:0000-0002-1825-0097/<uuid>/supp-data.csv/r01#equilibrium_property'
  python -m orchid_ids state --record state.json [--data ORCHID_DATA_DIR]             # S-/C- (phase registry from --data)
  python -m orchid_ids file records.json [--data DIR]                               # {"records": [...]} with pid / state
  python -m orchid_ids check --id ORC-... --pid '...'
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import PhaseRegistry, check_link, compute_ids, compute_orc_id, make_provisional_namespace, new_dataset_uuid


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="orchid_ids", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("namespace"); a.add_argument("--orcid", required=True); a.add_argument("--uuid")
    a = sub.add_parser("record"); a.add_argument("--pid", required=True); a.add_argument("--observation-key")
    a = sub.add_parser("state"); a.add_argument("--record", required=True); a.add_argument("--data")
    a.add_argument("--rule", default="coord-rule/3", choices=["coord-rule/3", "coord-rule/2"])
    a = sub.add_parser("file"); a.add_argument("path"); a.add_argument("--data")
    a = sub.add_parser("check"); a.add_argument("--id", required=True); a.add_argument("--pid", required=True)
    a.add_argument("--observation-key")
    args = ap.parse_args(argv)
    reg = PhaseRegistry.load(args.data) if getattr(args, "data", None) else None
    if args.cmd == "namespace":
        out = {"namespace": make_provisional_namespace(args.orcid, args.uuid or new_dataset_uuid())}
    elif args.cmd == "record":
        out = compute_orc_id(args.pid, observation_key=args.observation_key)
    elif args.cmd == "state":
        out = compute_ids(state=json.loads(Path(args.record).read_text()), phase_registry=reg, rule=args.rule)
    elif args.cmd == "file":
        recs = json.loads(Path(args.path).read_text())
        recs = recs.get("records", recs) if isinstance(recs, dict) else recs
        out = {"records": [compute_ids(pid=r.get("pid"), state=r if r.get("system") else None,
                                       observation_key=r.get("observation_key"), phase_registry=reg) for r in recs]}
    else:
        out = check_link(args.id, args.pid, args.observation_key)
    json.dump(out, sys.stdout, indent=1, ensure_ascii=False, default=str)
    print()
    return 0 if out.get("ok", True) else 1


if __name__ == "__main__":
    sys.exit(main())
