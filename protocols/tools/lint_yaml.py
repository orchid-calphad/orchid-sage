#!/usr/bin/env python3
"""Find lines whose flow collection ({...} or [...]) does not parse as intended in the yamlmini subset (and would be
read differently by PyYAML): prints line number and the parser error.  python3 tools/lint_yaml.py FILE.yaml"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import yamlmini
bad = 0
for i, l in enumerate(Path(sys.argv[1]).read_text().split("\n"), 1):
    s = yamlmini._strip_comment(l).strip()
    s = re.sub(r"^-\s+", "", s)
    m = re.match(r"^[^\s'\"{\[][^:]*:\s+(?P<v>[\[{].*)$", s) or re.match(r"^(?P<v>[\[{].*)$", s)
    if not m:
        continue
    try:
        v = yamlmini._scalar(m.group("v"), i)
        if isinstance(v, dict) and any(re.match(r"^\d", k) or " " in k for k in v):
            bad += 1; print(i, "suspicious key (a comma or colon inside an unquoted value?)", [k for k in v if re.match(r"^\d", k) or " " in k], "|", l.strip()[:100])
    except yamlmini.YamlError as e:
        bad += 1; print(i, e, "|", l.strip()[:120])
print(bad, "problem lines")
