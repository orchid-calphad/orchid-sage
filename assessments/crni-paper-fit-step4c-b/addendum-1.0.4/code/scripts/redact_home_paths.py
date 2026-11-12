"""crni-paper-fit-step4c-b@1.0.4: new versions of record files that carry a personal home path (/Users/<name>/), with the path
written as <home>/ instead. The originals stay unchanged; standard library only.

  redact_home_paths.py PROOF_OUT.json ORIGINAL=NEW [ORIGINAL=NEW ...]      (paths relative to the repository root)

For each pair: NEW = ORIGINAL with every "/Users/<name>/" replaced by "<home>/". Proof per pair: the changed lines (old, new); for JSON
files, every number, boolean and null (JSON path, repr) is identical and the parsed documents are equal once each changed string is
mapped back; nothing else differs. A NEW file that exists with different content is never overwritten."""
import hashlib
import json
import re
import sys
from pathlib import Path

HOME = re.compile(r"/Users/[A-Za-z0-9._-]+/")
REPO = Path(__file__).resolve().parents[5]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def scalars(o, path="$"):
    if isinstance(o, dict):
        for k in sorted(o):
            yield from scalars(o[k], f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from scalars(v, f"{path}[{i}]")
    elif not isinstance(o, str):
        yield (path, repr(o))


def back(o):
    if isinstance(o, dict):
        return {k: back(v) for k, v in o.items()}
    if isinstance(o, list):
        return [back(v) for v in o]
    return o


def main():
    proof = Path(sys.argv[1]); rows = []
    for pair in sys.argv[2:]:
        a, b = pair.split("=", 1); A, B = REPO / a, REPO / b
        raw = A.read_bytes(); txt = raw.decode()
        homes = sorted(set(HOME.findall(txt)))
        new = HOME.sub("<home>/", txt).encode()
        # the proof itself names no home path: the old prefix is written as <home>/
        changed = [{"line": i + 1, "old": HOME.sub("<home>/", o), "new": n} for i, (o, n) in enumerate(zip(txt.splitlines(), new.decode().splitlines())) if o != n]
        r = {"original": a, "original_sha256": sha(raw), "new": b, "new_sha256": sha(new), "home_prefixes_replaced": len(homes),
             "n_lines_changed": len(changed), "changed_lines": changed, "line_count_equal": len(txt.splitlines()) == len(new.decode().splitlines())}
        if A.suffix == ".json":
            j0, j1 = json.loads(raw), json.loads(new)
            r["json_scalars_identical"] = list(scalars(j0)) == list(scalars(j1))
            r["json_equal_after_mapping_back"] = json.loads(HOME.sub("<home>/", json.dumps(back(j0)))) == j1
        r["ok"] = r["line_count_equal"] and not HOME.search(new.decode()) and r.get("json_scalars_identical", True) and r.get("json_equal_after_mapping_back", True)
        if not r["ok"]:
            raise SystemExit(f"proof failed for {a}")
        if B.exists() and B.read_bytes() != new:
            raise SystemExit(f"FROZEN: {b} exists with different content")
        B.parent.mkdir(parents=True, exist_ok=True); B.write_bytes(new)
        rows.append(r)
        print(a, "->", b, r["n_lines_changed"], "line(s);", "ok")
    proof.write_text(json.dumps({"by": "assessments/crni-paper-fit-step4c-b/addendum-1.0.4/code/scripts/redact_home_paths.py", "rule": "/Users/<name>/ -> <home>/ ; nothing else changes", "files": rows}, indent=1))


if __name__ == "__main__":
    main()
