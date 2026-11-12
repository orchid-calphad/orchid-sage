#!/usr/bin/env python3
"""Check that every start of a fit step recorded a per-evaluation trajectory (gate G5).
  python3 check_trajectory.py steps/<step>     (accepts Cr-Ni trajectory.jsonl and Cu-Zr trace.jsonl)"""
import json, sys
from pathlib import Path
d = Path(sys.argv[1]); rows = []
for s in sorted(p for p in d.iterdir() if p.is_dir()):
    f = s / "trajectory.jsonl" if (s / "trajectory.jsonl").exists() else s / "trace.jsonl"
    n = sum(1 for l in f.open() if l.strip() and '"header"' not in l[:12]) if f.exists() else 0
    rows.append({"start": s.name, "file": f.name if f.exists() else None, "evaluations": n})
ok = all(r["evaluations"] > 0 for r in rows) and rows
print(json.dumps({"step": str(d), "starts": rows, "G5_trajectory_recorded": bool(ok)}))
sys.exit(0 if ok else 1)
