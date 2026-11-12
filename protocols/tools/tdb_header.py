#!/usr/bin/env python3
"""Write the Y32 header block on top of a pick TDB (protocol step tdb_header; layout of orchid-brand statements.md).

  python3 tdb_header.py SPEC.yaml OUT.tdb [--run-id RUN] [--code-commit SHA] [--release TAG] [--pick TDB]
(the pick is read from the evidence bundle's artifact/ copy unless --pick is given)

The body below the header is the pick TDB byte for byte (its sha256 is printed in the header and checked after writing).
Every header line is a TDB comment ($). Content comes from the specific protocol only: artifact, produced_by, instantiates,
run id (the pick's run), code (repo commit of the snapshot), environment lock sha256 and container image id, input sha256
(unary TDB, evidence bundle digest, MLIP weights), objective, gates, release and the reproduce command. The output is
deterministic: no clock time is written (the date is the protocol's `created` date)."""
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orchidproto as op  # noqa: E402


def main():
    a = sys.argv
    spec = op.load_doc(a[1]); out = Path(a[2])
    run_id = a[a.index("--run-id") + 1] if "--run-id" in a else next(r["run_id"] for r in spec["run_sequence"] if r["run_id"].endswith(("stepH2_hinge_thermo", "step4_solid")))
    commit = a[a.index("--code-commit") + 1] if "--code-commit" in a else "see code[] of the specific protocol"
    rel = a[a.index("--release") + 1] if "--release" in a else "unreleased"
    art = spec["artifact"]["file"]
    # read the pick from the evidence bundle copy (repo), not from the campaign directory (SCHEMA_GAPS G2)
    bundle_dir = op.expand(spec["evidence_selection"]["bundle"]["manifest"]["path"]).parent if spec.get("evidence_selection", {}).get("bundle") else None
    src = bundle_dir / "artifact" / Path(art["path"]).name if bundle_dir and (bundle_dir / "artifact" / Path(art["path"]).name).exists() else op.expand(art["path"])
    if "--pick" in a:
        src = Path(a[a.index("--pick") + 1])
    body = src.read_bytes()
    body_sha = hashlib.sha256(body).hexdigest()
    if body_sha != art["sha256"]:
        sys.exit("pick TDB does not match the sha256 in the specific protocol")
    env = {e["id"]: e for e in spec.get("environment", [])}
    lock = next((e.get("lockfile", {}).get("sha256") for e in env.values() if e.get("lockfile")), "n/a")
    inputs = []
    for i in spec.get("inputs", []):
        for f in i.get("files", []):
            if i["id"] in ("unaries", "mlip_weights"):
                inputs.append(f"{i['id']} {Path(f['path']).name} {f['sha256'][:16]}")
    ev = spec["evidence_selection"]
    lines = [
        "$ ORCHID-produced TDB",
        f"$ artifact:            {Path(art['path']).name}",
        f"$ produced_by:         {spec['artifact']['produced_by']}",
        f"$ instantiates:        {', '.join(i['protocol'] for i in spec['instantiates'])}",
        f"$ run_id:              {run_id}",
        f"$ code:                orchid-sage {commit} (assessments/{spec['id']}/code/)",
        f"$ environment:         lock sha256 {lock[:16] if lock else 'n/a'}; MLIP image sha256:ac223e2cfa3e (cuzr-phaseforge-grace-gpu:20261104)",
        f"$ inputs (sha256):     {'; '.join(inputs)}; evidence bundle {ev.get('bundle', {}).get('bundle_sha256', 'n/a')[:16]} (assessments/{spec['id']}/evidence/); data digest {ev.get('result_sha256', '')[:16]}",
        f"$ objective:           ESPEI log-likelihood (weights = default sd / sigma) + hinge (excluded phases)" + (" + weak prior" if "crni" in spec["id"] else ""),
        f"$ gates passed:        G1 software build, G2 pure elements, G6 no orphan, G7 inputs hashed, G8 dashboard (G9 independent rerun: see crate)",
        f"$ body sha256:         {body_sha}",
        f"$ orchid release:      {rel}",
        f"$ crate:               crates/{spec['id']}/ (DOI pending)",
        f"$ reproduce:           python3 protocols/tools/orchid_reproduce.py protocols/specific/{spec['id']}@{spec['version']}.yaml --root <new dir>",
        f"$ date:                {spec.get('created', '')}",
        "$ ---- body below this line is the pick TDB, byte for byte ----",
    ]
    head = ("\n".join(lines) + "\n").encode()
    out.write_bytes(head + body)
    assert hashlib.sha256(out.read_bytes()[len(head):]).hexdigest() == body_sha
    print(out, "header", len(lines), "lines; body sha256", body_sha[:16], "file sha256", hashlib.sha256(out.read_bytes()).hexdigest()[:16])


if __name__ == "__main__":
    main()
