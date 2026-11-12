#!/usr/bin/env python3
"""orchid reproduce: rebuild an artifact from its specific protocol and compare (standard library only).

  python3 orchid_reproduce.py SPEC.yaml --root NEW_DIR [--python PY] [--pfp PFP_SRC] [--nproc N] [--only id1,id2] [--stage-only] [--no-stage]
                                       [--compare-only] [--report OUT.json]

1. STAGE: copy, by hash, the code snapshot (assessments/<id>/code/) and the evidence bundle (assessments/<id>/evidence/)
   into a fresh run root using the `reproduce.stage` map of the specific protocol; every staged file is checked against
   the bundle manifests (sha256). The root must not exist or must be empty (no overwriting).
2. ENVIRONMENT: run `reproduce.environment_check` with --python and compare the printed versions with the lock.
3. RUN: execute `reproduce.plan` in order (each item: id, step, command run in the root with PY, NPROC and PFP
   substituted, env vars from the item), logging stdout/stderr to <root>/reproduce_logs/<id>.log.
4. COMPARE: every item's `expect` entries:
     byte       sha256 of the produced file equals the recorded one
     tdb_tol    every FUNCTION VVnnnn of the produced TDB within rel_tol (relative) of the reference TDB; other lines identical
     tdb_abs    every VVnnnn within an absolute tolerance in its own unit (abs_tol: {default, VVnnnn, ranges {"lo:hi:even|odd|all": tol}});
                use this for fitted parameters: soft directions move by physically negligible amounts (6 Nov test)
     json_tol   a numeric value at a JSON path (list items selected by key=value) within abs_tol of the reference value
     json_equal values at json_paths equal in the produced file and reference_path (or reference_value)
     files_equal  produced file byte-identical to reference_path (inside the root)
     sequence_equal  phase sequences (phase_sequence.py) with identical labels and transition temperatures within abs_tol K
   Plan items may carry `copy` (repo file -> root path, hash-checked), `cwd` and `expected` (pass/fail/partial with reason:
   an expected FAIL is reported as such). The PhaseForge+ source given by --pfp is hash-checked before anything runs
   against the pin list the spec declares (code entry `phaseforgeplus`, file id `source_pin`), or, when it declares none,
   against protocols/environment/pins/spark1_phaseforgeplus_files.sha256 (the full checkout of 6 Nov).
   and write the comparison report (JSON + Markdown): per check reference, rerun, difference, tolerance, pass/fail.
Verdict (PI, 6 Nov 2026, on the 1.0.0 Cr-Ni rerun: "this is too strict"): the overall PASS is judged by the plan's checks only -
predictions within their tolerances, plus the byte checks that matter for data identity (staged inputs, copies, evidence,
evaluated states) and every command's exit code. The environment check and the PhaseForge+ source check are reported as notes,
never as failures. Exit code 0 only if the verdict is PASS. Paths in the YAML are relative to the repo (assessments/...) or to the root.
"""
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import localpaths  # noqa: E402
import yamlmini  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def vv(tdb):
    return {m.group(1): float(m.group(2)) for m in re.finditer(r"FUNCTION\s+(VV\d{4})\s+298\.15\s+([-+.\dEe]+);", Path(tdb).read_text())}


def non_vv_lines(tdb):
    return [l for l in Path(tdb).read_text().splitlines() if not re.match(r"\s*FUNCTION\s+VV\d{4}\s", l) and not l.startswith("$")]


def jget(obj, path):
    """path like 'evaluations[start=s1_perturbed].logpost' or '[start=s7_perturbed].logpost'."""
    for part in re.findall(r"[^.\[\]]+|\[[^\]]+\]", path):
        if part.startswith("[") and "=" not in part:
            obj = obj[int(part[1:-1])]
        elif part.startswith("["):
            k, v = part[1:-1].split("=")
            obj = next(o for o in obj if str(o.get(k)) == v)
        else:
            obj = obj[part]
    return obj


_PUB = None


def public_copies():
    """In a public copy (PUBLIC_SUBSTITUTES.json at the repository root, written by public_sanitize.py export): path ->
    (original sha256, sanitized sha256). A staged file that is the sanitized copy of the pinned original is accepted;
    the sanitizing rules change only machine names and home paths in text, never numbers."""
    global _PUB
    if _PUB is None:
        m = REPO / "PUBLIC_SUBSTITUTES.json"
        _PUB = {r["path"]: (r["original_sha256"], r["sanitized_sha256"]) for r in json.loads(m.read_text())["files"]} if m.is_file() else {}
    return _PUB


def as_original(b):
    """Bytes of a rerun output with the sha256 of every public copy read as its original's: in a public copy the staged
    inputs are the sanitized copies (PUBLIC_SUBSTITUTES.json), so an output that records the sha256 of an input it read
    (states_evaluated records states_sha256) names the copy where the original run named the original. Only listed
    sha256 values are replaced; no other byte changes."""
    for o, s in public_copies().values():
        if o != s:
            b = b.replace(s.encode(), o.encode())
    return b


def stage(spec, root):
    st = spec["reproduce"]["stage"]
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        sys.exit(f"root {root} is not empty; choose a fresh directory (nothing is overwritten)")
    manifests = {}
    for m in st.get("manifests", []):
        d = json.loads((REPO / m).read_text())
        for f in d["files"]:
            manifests[str((REPO / m).parent / f["path"])] = f["sha256"]
    n = 0
    for src_dir, dst in st["copy"].items():
        src = REPO / src_dir
        files = [src] if src.is_file() else sorted(p for p in src.rglob("*") if p.is_file())
        for f in files:
            rel = f.name if src.is_file() else f.relative_to(src)
            d = root / dst / rel if not src.is_file() else root / dst
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, d)
            want = manifests.get(str(f))
            if want and sha(d) != want and public_copies().get(str(f.relative_to(REPO))) != (want, sha(d)):
                sys.exit(f"hash mismatch while staging {f}")
            n += 1
    for d in st.get("mkdirs", []):
        (root / d).mkdir(parents=True, exist_ok=True)
    return n


def pfp_git(pfroot):
    """Commit and tree of a PhaseForge+ git checkout given as --pfp, and the recorded commits with the same tree
    (environment/pins/phaseforgeplus_equivalence.json): equal trees are the same source. A note, never a failure."""
    try:
        c, t = subprocess.run(["git", "-C", str(pfroot), "rev-parse", "HEAD", "HEAD^{tree}"], capture_output=True, text=True, check=True).stdout.split()
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return {}
    eq = REPO / "protocols/environment/pins/phaseforgeplus_equivalence.json"
    same = []
    if eq.is_file():
        e = json.loads(eq.read_text())
        same = [x["commit"][:7] for x in e["commits"]] if e.get("tree") == t else []
    return {"git_commit": c, "git_tree": t, "same_tree_as": same}


DEFAULT_PFP_PIN = "protocols/environment/pins/spark1_phaseforgeplus_files.sha256"


def pfp_pin(spec):
    """The PhaseForge+ pin list the spec declares: the file with id `source_pin` of its `phaseforgeplus` code entry (hash-checked);
    a spec without one keeps the full-checkout list of 6 Nov (DEFAULT_PFP_PIN), so earlier specs behave as before."""
    for c in spec.get("code", []) or []:
        if c.get("id") != "phaseforgeplus":
            continue
        for f in c.get("files", []) or []:
            if f.get("id") == "source_pin":
                p = Path(os.path.expanduser(f["path"]))
                p = p if p.is_absolute() else REPO / p
                if not p.is_file() or sha(p) != f["sha256"]:
                    sys.exit(f"PhaseForge+ pin file {f['path']} missing or its sha256 differs from the spec")
                return p
    return REPO / DEFAULT_PFP_PIN


def env_check(spec, py):
    ec = spec["reproduce"]["environment_check"]
    out = subprocess.run([py, "-I", "-c", ec["code"]], capture_output=True, text=True)
    got = out.stdout.strip()
    return {"command": ec["code"], "expected": ec["expected"], "got": got, "pass": got == ec["expected"], "stderr": out.stderr[-300:]}


def main():
    a = sys.argv
    spec_path = Path(a[1]); spec = yamlmini.load(spec_path)
    root = Path(a[a.index("--root") + 1]).expanduser().resolve()
    py = a[a.index("--python") + 1] if "--python" in a else sys.executable
    pfp = a[a.index("--pfp") + 1] if "--pfp" in a else str(localpaths.setting("phaseforgeplus_src") or "<PhaseForgePlus src: --pfp, PHASEFORGEPLUS_SRC or local/config.json>")
    nproc = a[a.index("--nproc") + 1] if "--nproc" in a else "4"
    only = set(a[a.index("--only") + 1].split(",")) if "--only" in a else None
    rep_path = Path(a[a.index("--report") + 1]) if "--report" in a else root / "reproduce_report.json"
    report = {"specific_protocol": f"{spec['id']}@{spec['version']}", "spec_sha256": sha(spec_path), "root": str(root), "host": platform.node(),
              "machine": platform.machine(), "python": py, "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "items": []}
    if "--compare-only" not in a and "--no-stage" not in a:
        report["staged_files"] = stage(spec, root)
        if "--stage-only" in a:
            print("staged", report["staged_files"], "files into", root); return
    report["environment"] = env_check(spec, py)
    pin = pfp_pin(spec)
    pfroot = Path(pfp).expanduser().resolve().parent
    if pin.exists() and pfroot.exists():
        want = {l.split("  ", 1)[1]: l.split("  ", 1)[0] for l in pin.read_text().splitlines() if "  " in l}
        bad = [rel for rel, h in want.items() if not (pfroot / rel).exists() or sha(pfroot / rel) != h]
        report["phaseforgeplus"] = {"path": str(pfroot), "pin": str(pin.relative_to(REPO)) if pin.is_relative_to(REPO) else str(pin),
                                    "pinned_files": len(want), "mismatch": bad[:10], "pass": not bad, **pfp_git(pfroot)}
    else:
        report["phaseforgeplus"] = {"path": str(pfroot), "pass": None, "note": "pin file or source not found"}
    allpass = True   # environment and PhaseForge+ checks are notes (PI 6 Nov); the verdict comes from the plan's checks
    report["notes"] = [f"{k}: {'match' if report[k]['pass'] else ('not checked' if report[k]['pass'] is None else 'differs')} (note, not a failure)"
                       for k in ("environment", "phaseforgeplus")]
    logs = root / "reproduce_logs"; logs.mkdir(exist_ok=True)
    for it in spec["reproduce"]["plan"]:
        if only and it["id"] not in only:
            continue
        rec = {"id": it["id"], "step": it["step"], "kind": it.get("kind", "numerical"), "checks": []}
        for src, c in (it.get("copy") or {}).items():
            dst = root / c["to"]; dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.copy2(REPO / src, dst)
            if sha(dst) != c["sha256"] and public_copies().get(src) != (c["sha256"], sha(dst)):
                rec["checks"].append({"check": "copy hash", "path": c["to"], "pass": False}); allpass = False
        if it.get("expected"):
            rec["expected"] = it["expected"]
        if "--compare-only" not in a and it.get("command"):
            cmd = it["command"].replace("{PY}", py).replace("{NPROC}", nproc).replace("{PFP}", pfp).replace("{REPO}", str(REPO))
            env = dict(os.environ); env.update({k: str(v).replace("{PFP}", pfp) for k, v in (it.get("env") or {}).items()})
            t0 = time.time()
            with open(logs / f"{it['id']}.log", "w") as lf:
                r = subprocess.run(cmd, shell=True, cwd=root / it.get("cwd", "."), env=env, stdout=lf, stderr=subprocess.STDOUT)
            rec.update(command=cmd, returncode=r.returncode, wall_s=round(time.time() - t0, 1))
            if r.returncode != 0:
                rec["checks"].append({"check": "command exit code", "pass": False}); allpass = False
                rec["pass"] = False      # a failed command fails its item (before 7 Nov the item had no verdict, so the overall verdict missed it)
                if it.get("expected", {}).get("result") in ("fail", "partial"):
                    rec["notes"] = "the command itself failed, so this is not the expected " + it["expected"]["result"]
                report["items"].append(rec); json.dump(report, open(rep_path, "w"), indent=1); continue
        for ex in it.get("expect", []):
            p = root / ex["path"]; c = {"check": ex["rule"], "path": ex["path"]}
            if not p.exists():
                c.update({"pass": False, "note": "not produced"})
            elif ex["rule"] == "byte":
                got = sha(p); alt = hashlib.sha256(as_original(p.read_bytes())).hexdigest() if got != ex["sha256"] else got
                c.update(reference=ex["sha256"], rerun=got, pass_=ex["sha256"] in (got, alt))
                if got != ex["sha256"] and alt == ex["sha256"]:
                    c["note"] = "identical once the sha256 of the public copies it records are read as the originals'"
            elif ex["rule"] == "tdb_tol":
                ref = REPO / ex["reference"]; A, B = vv(ref), vv(p)
                worst = max((abs(A[k] - B.get(k, float("nan"))) / max(abs(A[k]), 1e-12) for k in A), default=0.0)
                same_other = non_vv_lines(ref) == non_vv_lines(p)
                c.update(reference=f"{ex['reference']} (sha256 {sha(ref)[:16]})", rerun_sha256=sha(p), byte_identical=sha(ref) == sha(p),
                         max_rel_diff=worst, rel_tol=ex["rel_tol"], other_lines_identical=same_other, pass_=(worst <= ex["rel_tol"] and same_other),
                         params={k: [A[k], B.get(k)] for k in sorted(A)})
            elif ex["rule"] == "tdb_abs":
                ref = REPO / ex["reference"]; A, B = vv(ref), vv(p); tolmap = ex["abs_tol"]
                def tol(k):
                    if k in tolmap: return tolmap[k]
                    n = int(k[2:])
                    for rng, t in tolmap.get("ranges", {}).items():
                        lo, hi, par = rng.split(":")
                        if int(lo) <= n <= int(hi) and (par == "all" or (par == "even") == (n % 2 == 0)): return t
                    return tolmap["default"]
                worst = max((abs(A[k] - B[k]) / tol(k) for k in A if k in B), default=0.0)
                same_other = non_vv_lines(ref) == non_vv_lines(p)
                c.update(reference=f"{ex['reference']} (sha256 {sha(ref)[:16]})", rerun_sha256=sha(p), byte_identical=sha(ref) == sha(p),
                         worst_diff_over_tol=worst, other_lines_identical=same_other, pass_=(worst <= 1.0 and same_other and set(A) == set(B)),
                         params={k: [A[k], B.get(k), tol(k)] for k in sorted(A)})
            elif ex["rule"] == "files_equal":
                q = root / ex["reference_path"]
                same = q.exists() and sha(q) == sha(p)
                alt = (not same) and q.exists() and as_original(p.read_bytes()) == q.read_bytes()
                c.update(reference=ex["reference_path"], rerun=sha(p), pass_=same or alt)
                if alt:
                    c["note"] = "identical once the sha256 of the public copies it records are read as the originals'"
            elif ex["rule"] == "json_equal":
                A_ = json.loads(p.read_text()); B_ = json.loads((root / ex["reference_path"]).read_text()) if ex.get("reference_path") else None
                diffs = []
                for jp in ex.get("json_paths", []):
                    va = jget(A_, jp)
                    vb = jget(B_, jp) if B_ is not None else ex.get("reference_value")
                    if va != vb:
                        diffs.append({"path": jp, "rerun": va, "reference": vb})
                c.update(reference=ex.get("reference_path", ex.get("reference_value")), differences=diffs[:10], pass_=not diffs)
            elif ex["rule"] == "sequence_equal":
                A_ = json.loads(p.read_text())["sequence"]; B_ = json.loads((root / ex["reference_path"]).read_text())["sequence"]
                tol = ex.get("abs_tol", 10); bad = []
                for x in sorted(set(A_) | set(B_)):
                    la, lb = A_.get(x, []), B_.get(x, [])
                    if [q[1] for q in la] != [q[1] for q in lb] or any(abs(q1[0] - q2[0]) > tol for q1, q2 in zip(la, lb)):
                        bad.append(x)
                c.update(reference=ex["reference_path"], abs_tol_K=tol, compositions=len(set(A_) | set(B_)), differing_compositions=bad[:20], n_differing=len(bad), pass_=not bad)
            elif ex["rule"] == "json_tol":
                got = jget(json.loads(p.read_text()), ex["json_path"]); ref = ex["reference_value"]
                c.update(reference=ref, rerun=got, diff=None if got is None else got - ref, abs_tol=ex["abs_tol"], pass_=got is not None and abs(got - ref) <= ex["abs_tol"])
            c["pass"] = c.pop("pass_", c.get("pass", False))
            allpass &= c["pass"]; rec["checks"].append(c)
        rec["pass"] = all(c["pass"] for c in rec["checks"]) if rec["checks"] else None
        if it.get("expected", {}).get("result") in ("fail", "partial") and rec["pass"] is False:
            rec["outcome"] = "expected " + it["expected"]["result"] + ": " + it["expected"].get("reason", "")
            allpass = allpass and all(c["pass"] for c in rec["checks"] if c["check"] == "command exit code")
        report["items"].append(rec)
        json.dump(report, open(rep_path, "w"), indent=1)
    ok_items = all((i.get("pass") is not False) or (i.get("outcome", "").startswith("expected") and all(c["pass"] for c in i["checks"] if c["check"] in ("command exit code", "copy hash")))
                   for i in report["items"])
    report["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    report["pass"] = bool(ok_items)   # predictions and data-identity checks only; environment and pins are notes
    report["unexpected_failures"] = [i["id"] for i in report["items"] if i.get("pass") is False and not i.get("outcome")]
    report["expected_failures"] = [i["id"] for i in report["items"] if i.get("outcome")]
    json.dump(report, open(rep_path, "w"), indent=1)
    md = [f"# Reproduce report: {report['specific_protocol']}", "", f"host {report['host']} ({report['machine']}), python {py}, root `{root}`",
          f"started {report['started']}, finished {report['finished']}; environment {'PASS' if report['environment']['pass'] else 'FAIL'} ({report['environment']['got']})", "",
          "| item | step | check | reference | rerun | tolerance | result |", "|---|---|---|---|---|---|---|"]
    for it in report["items"]:
        for c in it["checks"]:
            refv = c.get("reference", ""); rr = c.get("rerun", c.get("rerun_sha256", "")); tol = c.get("rel_tol", c.get("abs_tol", "per-symbol abs" if "worst_diff_over_tol" in c else "byte"))
            extra = f" (max rel diff {c['max_rel_diff']:.2e}{', byte-identical' if c.get('byte_identical') else ''})" if "max_rel_diff" in c else (f" (worst |diff|/tol {c['worst_diff_over_tol']:.2e}{', byte-identical' if c.get('byte_identical') else ''})" if "worst_diff_over_tol" in c else "")
            res_ = 'PASS' if c['pass'] else ('FAIL (expected)' if it.get('outcome') else 'FAIL')
            md.append(f"| {it['id']} | {it['step']} | {c['check']} `{c.get('path', '')}` | {str(refv)[:40]} | {str(rr)[:40]}{extra} | {tol} | {res_} |")
    md += ["", f"PhaseForge+ source check (note): {report.get('phaseforgeplus')}", f"Notes: {report['notes']}", f"Expected failures: {report['expected_failures']}; unexpected failures: {report['unexpected_failures']}",
           "", f"**Overall: {'PASS' if report['pass'] else 'FAIL'}** (predictions and data-identity checks; environment and pins are notes; an item marked expected=fail does not fail the run when it fails as declared)"]
    Path(str(rep_path).replace(".json", ".md")).write_text("\n".join(md) + "\n")
    print("overall", "PASS" if report["pass"] else "FAIL", "->", rep_path)
    sys.exit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
