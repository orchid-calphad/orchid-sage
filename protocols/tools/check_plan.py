#!/usr/bin/env python3
"""Check that a campaign PLAN.md has the sections the general protocol requires and that it predates every run card.
  python3 check_plan.py PLAN.md [RUN_CARD.json ...]"""
import json, os, re, sys
from pathlib import Path
p = Path(sys.argv[1]); t = p.read_text()
need = ["Established practice", "Inputs", "Model", "free", "Ranking thresholds", "wall"]
miss = [n for n in need if n.lower() not in t.lower()]
late = []
for rc in sys.argv[2:]:
    s = json.loads(Path(rc).read_text()).get("started_utc") or json.loads(Path(rc).read_text()).get("started")
    if s and os.path.getmtime(p) > __import__("calendar").timegm(__import__("time").strptime(s[:19], "%Y-%m-%dT%H:%M:%S")):
        late.append(rc)
print(json.dumps({"plan": str(p), "missing_sections": miss, "run_cards_older_than_plan_edit": late}))
sys.exit(1 if miss else 0)
