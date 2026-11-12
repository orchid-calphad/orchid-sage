#!/usr/bin/env python3
"""Sync tools/palette.json from the ORCHID brand tokens (source of truth: design-system/tokens.json of the orchid-brand
repository, a sibling checkout or 'siblings' in local/config.json;
PI 6 Nov 2026). The brand wins wherever both define a value; the palette keeps only what the brand does not define
(status and topology-class marker rules, the dark neutral inks, the step ramp, the start markers), labelled as such.
Prints every difference it resolves.   python3 tools/sync_palette.py"""
import hashlib, json, subprocess, sys
from pathlib import Path
T = Path(__file__).resolve().parent
sys.path.insert(0, str(T))
import localpaths  # noqa: E402
import frozen  # noqa: E402
BR = localpaths.sibling("orchid-brand"); BRT = localpaths.tilde(BR)    # BRT: the brand repository as the palette records it
B = BR / "design-system/tokens.json"
tok = {t["name"]: t["value"] for t in json.loads(B.read_text())["color"]["tokens"]}
P = json.loads((T / "palette.json").read_text())
diffs = []
def setv(path, new):
    d = P
    for k in path[:-1]:
        d = d.setdefault(k, {})
    old = d.get(path[-1])
    if old is not None and str(old).lower() != str(new).lower():
        diffs.append(f"{'.'.join(path)}: palette {old} -> brand {new}")
    d[path[-1]] = new
UI = {"bg": "surface", "card": "card", "fg": "ink", "muted": "muted", "line": "line", "accent": "accent", "accent2": "accent-soft", "ok": "ok"}
for th in ("light", "dark"):
    for k, b in UI.items():
        setv(["ui", th, k], tok[b][th])
EV = {"experimental": "exp", "model": "model", "dft": "dft-mp", "oqmd": "oqmd", "lit_dft": "lit-dft", "assessed": "assessed", "unspecified": "unspecified"}
for k, b in EV.items():
    for th in ("light", "dark"):
        setv(["data", k, th], tok[b][th])
for th in ("light", "dark"):
    setv(["data", "orchid", th], tok["accent"][th])
for k, b in (("ink2", "fig-ink2"), ("grey_m", "fig-grey-m"), ("grey_l", "fig-grey-l")):
    setv(["neutral", k, "light"], tok[b])
try:
    commit = subprocess.run(["git", "-C", str(B.parent.parent), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
except Exception:
    commit = None
P["version"] = "1.2.0"
P["sources"]["source_of_truth"] = {"path": f"{BRT}/design-system/tokens.json", "sha256": hashlib.sha256(B.read_bytes()).hexdigest(), "commit": commit,
                                   "rule": "brand wins (PI 6 Nov 2026); this file adds only dashboard rules the brand does not define: status/topology markers, dark neutral inks, step ramp, start markers"}
P["sources"]["fonts"] = f"{BRT}/design-system/fonts/ (copies in tools/assets/, identical sha256)"
P["sources"]["logo"] = f"{BRT}/design-system/assets/Logos/orchid-icon.svg and orchid-icon-512.png (copies in tools/assets/, identical)"
P["sync_differences"] = diffs
frozen.write(T / "palette.json", json.dumps(P, indent=1, ensure_ascii=False))   # refuses a frozen file
print(len(diffs), "differences resolved in favour of the brand"); print("\n".join(diffs))
