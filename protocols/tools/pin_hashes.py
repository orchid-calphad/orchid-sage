#!/usr/bin/env python3
"""Fill (or refresh) `sha256:` in a protocol YAML from the file named by the `path` of the same mapping (block or flow
style), and print the evidence digest of a run card.  Hashes of campaign files are filled only when null; hashes of files under protocols/ are refreshed. Never changes anything else.

  python3 tools/pin_hashes.py FILE.yaml [FILE2.yaml ...]
  python3 tools/pin_hashes.py --digest run_cards/<card>.json
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orchidproto as op  # noqa: E402
import frozen  # noqa: E402

WRITES = frozen.Writes("pin_hashes.py")   # every YAML of one call: all or none (an approved protocol or a pinned file is frozen)

FLOW = re.compile(r"\{path: (?P<q>'?)(?P<p>[^,']+)(?P=q), sha256: (?:null|[0-9a-f]{64})")


def own(p):
    """Only files under protocols/ (generated here) are re-pinned; a campaign file keeps its pinned hash, so a later
    change in a campaign directory shows up as a validator error instead of being absorbed."""
    q = op.expand(p).resolve()
    for base in (op.ROOT.resolve(), (op.ROOT.parent / "assessments").resolve()):
        try:
            q.relative_to(base); return True
        except ValueError:
            pass
    return False


def pin(path):
    lines = Path(path).read_text().split("\n")
    n = 0
    last_path = {}
    for i, l in enumerate(lines):
        if FLOW.search(l):
            def sub(m):
                nonlocal n
                if not m.group(0).endswith("null") and not own(m.group("p")):
                    return m.group(0)
                if not op.expand(m.group("p")).exists():
                    print(f"  {path}:{i + 1}: not on disk yet, left null: {m.group('p')}"); return m.group(0)
                n += 1
                return "{path: " + m.group("q") + m.group("p") + m.group("q") + ", sha256: " + op.sha256_file(m.group("p"))
            lines[i] = FLOW.sub(sub, l)
            continue
        b = re.match(r"^(\s*)(- )?path: '?([^'#]+?)'?\s*$", l)
        if b:
            ind = len(b.group(1)) + (2 if b.group(2) else 0)
            last_path[ind] = b.group(3)
            continue
        s = re.match(r"^(\s*)sha256: (?:null|[0-9a-f]{64})\s*$", l)
        if s and not l.rstrip().endswith("null") and not own(last_path.get(len(s.group(1)), "")):
            continue
        if s and len(s.group(1)) in last_path and not op.expand(last_path[len(s.group(1))]).exists():
            print(f"  {path}:{i + 1}: not on disk yet, left null: {last_path[len(s.group(1))]}"); continue
        if s and len(s.group(1)) in last_path:
            lines[i] = s.group(1) + "sha256: " + op.sha256_file(last_path[len(s.group(1))])
            n += 1
    # reproduce.plan `copy:` entries - {repo/path: {to: root/path, sha256: H}} - always follow the repo file (own files only)
    CP = re.compile(r"(?P<src>[A-Za-z0-9_@./-]+): \{to: (?P<to>[^,]+), sha256: (?P<h>null|[0-9a-f]{64})\}")
    for i, l in enumerate(lines):
        if l.lstrip().startswith("copy: {"):
            def _f(m):
                q = op.ROOT.parent / m.group("src")
                return f"{m.group('src')}: {{to: {m.group('to')}, sha256: {op.sha256_file(q)}}}" if q.exists() and own(q) else m.group(0)
            new = CP.sub(_f, l)
            if new != l:
                lines[i] = new; n += 1
    WRITES.add(path, "\n".join(lines))
    print(f"{path}: pinned {n} hashes")


if __name__ == "__main__":
    if sys.argv[1] == "--digest":
        rc = op.load_doc(sys.argv[2])
        refs = [r for r in rc["inputs"] if str(r.get("role", "")).startswith("data file")]
        print(op.evidence_digest(refs), len(refs))
    else:
        for f in [a for a in sys.argv[1:] if not a.startswith("--")]:
            pin(f)
        WRITES.commit()
