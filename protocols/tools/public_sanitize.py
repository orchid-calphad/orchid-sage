#!/usr/bin/env python3
"""Public copies of records that carry local information (standard library only).

Frozen records are never edited. A published copy (an RO-Crate, a public export) holds a sanitized copy instead, and a
mapping file records, per file, the original's path and sha256 and the sanitized copy's sha256, so anyone with the
original can recompute the copy (the rules below are deterministic and change nothing else).

  public_sanitize.py text FILE                  print the sanitized text of FILE
  public_sanitize.py proof ORIGINAL SANITIZED   check that SANITIZED == sanitize(ORIGINAL)
  public_sanitize.py export OUT_DIR             the public copy of this repository: every tracked file except those matched
                                                by .public-exclude (which is not exported either), sanitized, under sanitized names, with OUT_DIR/
                                                PUBLIC_SUBSTITUTES.json (original sha256 -> sanitized sha256 per changed
                                                file); OUT_DIR must not exist. Refuses when a binary file holds a match.

Rules (applied in this order; the same mapping is applied to file and directory names inside a published copy). Names
of this machine (host names, user names, address prefixes) are not written here: they come from local/config.json
('hosts': label -> host name, 'private': usernames, other_hosts, ip_prefixes; see local.example/config.json).
  /Users/<name>/ , /home/<name>/      -> the tilde form of the home directory (Mac Studio or DGX Spark), then <home>/
  /private/tmp/claude-<uid>/<...>     -> <scratch>  (agent session scratch; the session id goes too)
  /private/var/folders/<..>/T          -> <tmp>
  claude-<uid>                         -> claude-<uid>
  configured user names                -> <user>
  configured host names                -> their machine labels (studio -> mac-studio; spark1..spark4 for the four NVIDIA
                                          DGX Spark nodes, aarch64 Linux; one label per node, so 'same node' comparisons
                                          in the records keep their meaning); 'spark-'/'dgx-' prefixed forms included
  configured other hosts               -> their labels
  configured address prefixes          -> <ip>
  configured compute accounts          -> <hpc-account>
  Claude session ids                   -> <session>
then, in text files, the home-relative paths of the records become named placeholders (PI, 7 Nov 2026: nothing
disseminated carries a home path or a machine-specific location):
  <home>/.venvs/espei-pr268/bin/python   -> <fit-python>   (the fit interpreter, given by the operator: --python)
  <home>/.venvs/espei-pr268              -> <fit-env>      (its virtual environment)
  <home>/projects/orchid-sage            -> <orchid-sage>  (this repository, wherever it is checked out)
  any other <home>/...                   -> <home>/...     (the home directory of the machine that wrote the record)
(each rule above matches the tilde form of the home directory). In HTML text outside <script> the placeholders are
written as character references (&lt;home&gt;) so that a browser shows them.
JSON files stay valid JSON: the replacements contain no quote or backslash and never touch numbers.
"""
import getpass
import hashlib
import json
import os
import re
import sys
from pathlib import Path

GENERIC = [
    (re.compile(r"/private/tmp/claude-\d+/[A-Za-z0-9._-]+/[0-9a-f-]{36}"), "<scratch>"),
    (re.compile(r"/private/tmp/claude-\d+(?:/[A-Za-z0-9._-]+)?"), "<scratch>"),
    (re.compile(r"(?<!/private)/tmp/claude-\d+"), "<scratch>"),
    (re.compile(r"/private/var/folders/[A-Za-z0-9_]+/[A-Za-z0-9_+-]+/T"), "<tmp>"),
    (re.compile(r"/Users/(?!runner\b|you\b|<)[A-Za-z0-9._-]+"), "~"),
    (re.compile(r"/home/(?!runner\b)[A-Za-z0-9._-]+"), "~"),
    (re.compile(r"\bclaude-\d{3,}\b"), "claude-<uid>"),
]
TAIL = [(re.compile(r"\bsession_[A-Za-z0-9]{16,}\b"), "<session>")]
_T = r"(?<![\w<])~"                                      # the home directory as the records write it (tilde)
PLACEHOLDERS = [
    (re.compile(_T + r"/\.venvs/espei-pr268/bin/python(?![\w-]|\.\w)"), "fit-python"),
    (re.compile(_T + r"/\.venvs/espei-pr268(?![\w-]|\.\w)"), "fit-env"),
    (re.compile(_T + r"/projects/orchid-sage(?![\w-]|\.\w)"), "orchid-sage"),
    (re.compile(_T + r"(?=/)"), "home"),
]
_SCRIPT = re.compile(r"<script\b.*?</script>", re.S | re.I)


def placeholders(s, html=False):
    """Home-relative record paths -> named placeholders (<fit-python>, <fit-env>, <orchid-sage>, <home>/...); in HTML
    text outside <script> as &lt;name&gt;."""
    def sub(x, esc):
        for rx, name in PLACEHOLDERS:
            x = rx.sub(f"&lt;{name}&gt;" if esc else f"<{name}>", x)
        return x
    if not html:
        return sub(s, False)
    out, i = [], 0
    for m in _SCRIPT.finditer(s):
        out += [sub(s[i:m.start()], True), sub(m.group(0), False)]; i = m.end()
    return "".join(out + [sub(s[i:], True)])


def _config():
    p = os.environ.get("ORCHID_SAGE_CONFIG") or str(Path(__file__).resolve().parents[2] / "local" / "config.json")
    return json.loads(Path(p).read_text()) if Path(p).is_file() else {}


def _alt(names):
    return "|".join(re.escape(n) for n in sorted(set(names), key=len, reverse=True))


def build_rules(cfg=None):
    cfg = _config() if cfg is None else cfg
    priv = cfg.get("private") or {}
    users = [u for u in priv.get("usernames", []) + [getpass.getuser()] if u and u not in ("runner", "root")]
    host_label = {}
    for lab, name in (cfg.get("hosts") or {}).items():
        base = re.sub(r"_(ssh|dgx)$", "", lab); label = {"studio": "mac-studio"}.get(base, base)
        if name and name != label:
            host_label[name] = label
            if re.fullmatch(r"[A-Za-z]\d+", name):           # a bare node name: its spark-/dgx- forms too
                host_label.setdefault(f"spark-{name}", label); host_label.setdefault(f"dgx-{name}", label)
    host_label.update(priv.get("other_hosts") or {})
    rules = list(GENERIC)
    if users:
        rules.append((re.compile("-Users-(?:" + _alt(u.replace(".", "-") for u in users) + ")-"), "-home-"))   # Claude project-folder names
        rules.append((re.compile(r"(?<!\w)(?:" + _alt(users) + r")(?!\w)"), "<user>"))
    if host_label:
        rx = re.compile(r"(?<![A-Za-z0-9])(?:" + _alt(host_label) + r")(?![A-Za-z0-9])")      # '_' separates: spark1_container.txt
        rules.append((rx, lambda m: host_label[m.group(0)]))
    if priv.get("accounts"):                              # compute allocation accounts (before the user names they may contain)
        rules.insert(len(GENERIC), (re.compile(r"(?<!\w)(?:" + _alt(priv["accounts"]) + r")(?!\w)"), "<hpc-account>"))
    if priv.get("ip_prefixes"):
        rules.append((re.compile(r"(?<![\w.])(?:" + _alt(priv["ip_prefixes"]) + r")(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){2}(?![\w.])"), "<ip>"))
    return rules + TAIL, host_label


RULES, HOST_LABEL = build_rules()
TEXT_SUFFIXES = {".json", ".yaml", ".yml", ".md", ".html", ".txt", ".log", ".py", ".sh", ".csv", ".tdb", ".toml", ".cfg", ".ini",
                 ".tsv", ".sha256", ".lock", ".out", ".err", ".xml", ".svg", ".js", ".css", ".tex", ".bib", ".dat", ".in",
                 ".extxyz", ".xyz", ".sbatch", ".slurm", ".cif", ".vasp", ".jsonl", ".ipynb", ""}


def sanitize_text(s, suffix=None):
    for rx, rep in RULES:
        s = rx.sub(rep, s)
    return placeholders(s, html=(suffix or "").lower() in (".html", ".htm"))


def sanitize_path(rel):
    """Directory and file names in a published copy (host labels only; names carry no home paths)."""
    if not HOST_LABEL:
        return rel
    rx = re.compile(r"(?<![A-Za-z0-9])(?:" + _alt(HOST_LABEL) + r")(?![A-Za-z0-9])")
    return rx.sub(lambda m: HOST_LABEL[m.group(0)], rel)


def sanitize_bytes(raw, suffix):
    """(new bytes, changed) for a text file; binary files are returned unchanged (changed=None when they hold a match)."""
    try:
        txt = raw.decode("utf-8")
    except UnicodeDecodeError:
        txt = None
    if txt is None or "\0" in txt[:8192] or suffix.lower() not in TEXT_SUFFIXES:
        hit = any(rx.search(raw.decode("latin-1")) for rx, _ in RULES)
        return raw, (None if hit else False)
    new = sanitize_text(txt, suffix)
    return new.encode("utf-8"), new != txt


def sha(b):
    return hashlib.sha256(b).hexdigest()


def export(out, repo=None):
    import fnmatch
    import subprocess
    repo = Path(repo or Path(__file__).resolve().parents[2]); out = Path(out)
    if out.exists():
        raise SystemExit(f"{out} exists: the export goes to a new directory")
    excl = [ln.split(" #")[0].strip() for ln in (repo / ".public-exclude").read_text().splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")] if (repo / ".public-exclude").is_file() else []
    files = subprocess.run(["git", "-C", str(repo), "ls-files", "-z"], capture_output=True, check=True).stdout.decode().split("\0")
    rows, binary, skipped, n = [], [], [], 0
    for rel in sorted(f for f in files if f):
        src = repo / rel
        if not src.is_file():
            continue
        if rel == ".public-exclude" or any(fnmatch.fnmatch(rel, g) for g in excl):   # the exclusion list itself stays private
            skipped.append(sanitize_path(rel)); continue
        prel = sanitize_path(rel); raw = src.read_bytes(); new, changed = sanitize_bytes(raw, src.suffix)
        if changed is None:
            binary.append(rel)
        dst = out / prel; dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(new); n += 1
        if changed or prel != rel:
            rows.append({"path": prel, "original": sanitize_path(rel) if prel == rel else prel + " (renamed: host label)",
                         "original_sha256": sha(raw), "sanitized_sha256": sha(new)})
    if binary:
        raise SystemExit(f"binary files hold local information (not exported safely): {binary}")
    (out / "PUBLIC_SUBSTITUTES.json").write_text(json.dumps({
        "by": "protocols/tools/public_sanitize.py export", "rule": "every file that held local information is its sanitized copy (rules in "
        "protocols/tools/public_sanitize.py); original_sha256 identifies the original kept in the private repository; records that pin "
        "an original's sha256 are satisfied by its copy here (protocols/tools/validate.py reads this file)",
        "n_files": n, "n_changed": len(rows), "files": rows}, indent=1) + "\n")   # only files in this copy; nothing about what was left out
    print(f"{out}: {n} files, {len(rows)} sanitized or renamed, {len(skipped)} excluded (.public-exclude)")


if __name__ == "__main__":
    if sys.argv[1] == "text":
        sys.stdout.write(sanitize_text(Path(sys.argv[2]).read_text(), Path(sys.argv[2]).suffix))
    elif sys.argv[1] == "proof":
        a, b = Path(sys.argv[2]).read_bytes(), Path(sys.argv[3]).read_bytes()
        new, _ = sanitize_bytes(a, Path(sys.argv[2]).suffix)
        print("ok" if new == b else "DIFFERS", sha(a), "->", sha(new), "(file", sha(b) + ")")
        sys.exit(0 if new == b else 1)
    elif sys.argv[1] == "export":
        export(sys.argv[2])
