#!/usr/bin/env python3
"""Fail on local information in files that will be published (standard library only).

  check_public.py [PATH ...] [--allow FILE] [--history] [--max N] [--quiet]

PATH: files or directories (default: the current directory). Inside a git work tree the tracked and the untracked,
not ignored files are scanned (git ls-files --cached --others --exclude-standard), otherwise every file under PATH; .git, __pycache__ and .DS_Store are skipped. Binary files (PDF, PNG,
...) are scanned as bytes, because PDF and PNG metadata can carry paths. Exit status 1 when anything is found.

--history   also scan the git history (git log -p --all, commit messages included) of the repository at each PATH;
            history hits are reported but do not change the exit status (rewriting history is a decision for the owner)
--allow F   allowlist: one rule per line, "REGEX" (a matched text that also matches REGEX is accepted) or
            "path-glob::REGEX" (only in files matching the glob); '#' starts a comment. Default: .public-allow at the
            root of each PATH when present.

What counts as local information: absolute home and scratch paths (/Users/<name>, /home/<name>, /private/tmp,
/private/var/folders, /tmp/claude-<uid>), home-relative paths in code, records and docs (Path.home(), expanduser("~..."),
$HOME, a tilde-slash path), user names (claude-<uid>, the current user, the configured ones), host names (DGX node names b<NNN>, spark-*,
dgx-*, *.local, the configured hosts), private and configured IPv4 addresses, e-mail addresses other than
rarroyave@tamu.edu and noreply@anthropic.com, Claude session ids and links, AI-tool attribution lines
(a Co-Authored-By trailer naming Claude, a Claude-Session trailer, a "Generated with" Claude Code footer), and credential patterns (API keys, tokens, private
keys). The names of this machine are read from the local config, never written in this file. Machine classes ("Mac Studio (arm64, macOS)",
"NVIDIA DGX Spark (aarch64, Linux)") are fine and are not matched.

Files that look like restricted publisher material (*.pdf or images whose names say page/crop/render/screenshot, and
JSON string values longer than 500 characters under a quote/excerpt/text key) are listed as "restricted?" so a person
can confirm them; listed paths can be accepted in the allowlist with "path-glob::restricted".
"""
import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path

PATTERNS = [
    ("home_path", r"/Users/(?!runner\b)[A-Za-z0-9._-]+|/home/(?!runner\b)[A-Za-z0-9._-]+"),        # CI runners' homes are not local
    ("scratch_path", r"/private/tmp\b|/private/var/folders\b|/var/folders/[A-Za-z0-9_]{2}/|/tmp/claude-\d+"),
    ("username", r"\bclaude-\d{3,}\b"),
    # generic host forms (DGX node names b<NNN>, spark-*/dgx-* aliases, mDNS *.local); the names of this machine's hosts
    # come from local/config.json (see private_patterns)
    ("host", r"(?<![A-Za-z0-9+/=])(?:dgx-|spark-)?b\d{3}(?![A-Za-z0-9+/=])|\bspark-[A-Za-z0-9]+\b|\bdgx-[A-Za-z0-9]+\b|\b[A-Za-z0-9-]+\.local\b"),
    # IPv4: private, carrier-grade NAT and campus ranges (four-part version numbers such as 10.8.0.43 in a
    # *_VERSION= line are accepted in .public-allow by file)
    ("ipv4", r"(?<![\w.])(?:10|192\.168|172\.(?:1[6-9]|2\d|3[01])|100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7]))"
             r"(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}(?![\w.])"),
    # e-mail: domain labels start with a letter and the last one is not a file extension (states@1.1.0.json is a file name)
    ("email", r"[A-Za-z0-9._%+-]*[A-Za-z0-9]@[A-Za-z][A-Za-z0-9-]*(?:\.[A-Za-z0-9-]+)*\.(?!(?:json|md|ya?ml|py|txt|html?|log|csv|tdb|png|pdf|array|sh|toml|tex)\b)[A-Za-z]{2,}\b"),
    ("session_id", r"\bsession_[A-Za-z0-9]{16,}\b|claude\.ai/code/session"),
    # AI-tool attribution lines and session links (PI, 7 Nov 2026: none in the public repository, files or commit messages)
    ("ai_attribution", r"claude\.ai/code/session_|Co-Authored-By:\s*Claude|Generated with \[?Claude Code|Claude-Session:"),
    # home-relative paths: in code, configs, CI and docs no path may depend on the machine's home layout
    # (Path.home(), expanduser("~..."), $HOME, a tilde-slash path); expanding a path a user or a config gives is fine; the
    # public records name such locations by placeholder (<home>, <orchid-sage>, <fit-python>, <fit-env>: public_sanitize.py)
    ("home_relative", r"Path\.home\(\)|expanduser\(\s*[\"']~|\$\{?HOME\b|os\.environ(?:\.get)?\(?\[?[\"']HOME[\"']|(?<![\w/.~-])~/[A-Za-z0-9._-]+"),
    ("credential", r"sk-ant-[A-Za-z0-9_-]{10,}|\bgh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|\bAKIA[0-9A-Z]{16}\b"
                   r"|xox[abpr]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
                   r"|(?i:(?:api[_-]?key|apikey|x-els-apikey|access[_-]?token|secret|passwd|password)[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{16,})"),
]
DEFAULT_ALLOW = [
    r"^rarroyave@tamu\.edu$", r"^noreply@anthropic\.com$", r"^git@github\.com$",
    r"^(?:0\.0\.0\.0|127\.0\.0\.1)$",
]
RESTRICTED_NAME = re.compile(r"(?i)(page[-_]?\d|crop|render|screenshot|scan)")
QUOTE_KEYS = {"quote", "quotes", "excerpt", "text_excerpt", "verbatim", "source_text"}
SKIP_PARTS = {".git", "__pycache__", ".DS_Store", ".pytest_cache", ".mypy_cache"}


def private_patterns(roots=()):
    """Names of this machine, never written in code: user names, host names and address prefixes from the local config
    (CHECK_PUBLIC_CONFIG, ORCHID_SAGE_CONFIG, local/config.json next to this tool's repository or a scanned root),
    plus the current user name. In CI there is no config and only the generic patterns apply."""
    import getpass
    cands = [os.environ.get("CHECK_PUBLIC_CONFIG"), os.environ.get("ORCHID_SAGE_CONFIG"), str(Path(__file__).resolve().parents[2] / "local" / "config.json")]
    cands += [str(Path(r) / "local" / "config.json") for r in roots]
    cfg = next((json.loads(Path(c).read_text()) for c in cands if c and Path(c).is_file()), {})
    priv = cfg.get("private") or {}
    users = [u for u in priv.get("usernames", []) + [getpass.getuser()] if u and u not in ("runner", "root")]
    hosts = [h for h in (cfg.get("hosts") or {}).values() if h] + list((priv.get("other_hosts") or {}))
    hosts = [h for h in hosts if not re.fullmatch(r"(?:spark\d|mac-studio|studio)", h)]
    CONFIGURED_HOSTS.update(hosts + [p + h for h in hosts for p in ("spark-", "dgx-")])
    out = []
    alt = lambda xs: "|".join(re.escape(x) for x in sorted(set(xs), key=len, reverse=True))  # noqa: E731
    if users:
        out.append(("username", r"(?<!\w)(?:" + alt(users) + r")(?!\w)"))
    if hosts:
        out.append(("host", r"(?<![A-Za-z0-9])(?:" + alt(hosts) + r")(?![A-Za-z0-9])"))
    if priv.get("accounts"):
        out.append(("account", r"(?<!\w)(?:" + alt(priv["accounts"]) + r")(?!\w)"))
    if priv.get("ip_prefixes"):
        out.append(("ipv4", r"(?<![\w.])(?:" + alt(priv["ip_prefixes"]) + r")(?:\.\d{1,3}){2}(?![\w.])"))
    return out


RX = [(n, re.compile(p)) for n, p in PATTERNS]
CONFIGURED_HOSTS = set()


def load_allow(paths):
    rules = []
    for p in paths:
        if p and Path(p).exists():
            for line in Path(p).read_text().splitlines():
                line = line.split(" #", 1)[0].strip() if not line.lstrip().startswith("#") else ""
                if line:
                    g, _, r = line.rpartition("::")
                    rules.append((g or None, re.compile(r)))
    return rules + [(None, re.compile(r)) for r in DEFAULT_ALLOW]


def allowed(rules, rel, text):
    return any((g is None or fnmatch.fnmatch(rel, g)) and r.search(text) for g, r in rules)


def git_root(p):
    try:
        return Path(subprocess.run(["git", "-C", str(p if p.is_dir() else p.parent), "rev-parse", "--show-toplevel"],
                                   capture_output=True, text=True, check=True).stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def files_under(p):
    root = git_root(p)
    if root is not None:
        out = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", str(p.resolve())], capture_output=True, check=True).stdout
        fs = [root / f for f in out.decode().split("\0") if f]
    else:
        fs = [p] if p.is_file() else [q for q in p.rglob("*") if q.is_file()]
    return [f for f in fs if f.is_file() and not (SKIP_PARTS & set(f.parts))]


def scan_text(text, rel, rules):
    hits = []
    for ln, line in enumerate(text.splitlines(), 1):
        seen = set()
        for name, rx in RX:
            for m in rx.finditer(line):
                s = m.group(0)
                if m.span() not in seen and not allowed(rules, rel, s):
                    seen.add(m.span()); hits.append((rel, ln, name, s, line.strip()[:160]))
    return hits


def long_quotes(o, path="$"):
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, str) and k.lower() in QUOTE_KEYS and len(v) > 500:
                yield f"{path}.{k}", len(v)
            else:
                yield from long_quotes(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from long_quotes(v, f"{path}[{i}]")


def scan_file(f, rel, rules):
    raw = f.read_bytes()
    try:
        text = raw.decode("utf-8"); binary = b"\0" in raw[:8192]
    except UnicodeDecodeError:
        text = raw.decode("latin-1"); binary = True
    hits = scan_text(text, rel, rules)
    if binary:   # paths in binary metadata are absolute; tilde-slash and 'b123' byte runs in image data are noise
        hits = [(r, 0, n, s, "(binary file)") for r, _, n, s, _ in hits
                if n != "home_relative" and not (n == "host" and re.fullmatch(r"(?:spark-|dgx-)?b\d{3}", s) and s not in CONFIGURED_HOSTS)]
    restricted = []
    if (f.suffix.lower() == ".pdf" or f.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"} and RESTRICTED_NAME.search(f.name)) \
            and not allowed(rules, rel, "restricted"):
        restricted.append((rel, 0, "restricted?", f.suffix.lower(), "publisher material? confirm or allow"))
    if f.suffix.lower() == ".json" and not binary and not allowed(rules, rel, "restricted"):
        try:
            for jp, n in long_quotes(json.loads(text)):
                restricted.append((rel, 0, "restricted?", jp, f"quote of {n} characters (> 500)"))
        except ValueError:
            pass
    return hits + restricted


def scan_history(root, rules, limit):
    proc = subprocess.Popen(["git", "-C", str(root), "log", "-p", "--all", "--no-color", "--format=commit %H%n%B"], stdout=subprocess.PIPE)
    commit, fname, counts, examples = "?", "(message)", {}, []
    for raw in proc.stdout:
        line = raw.decode("utf-8", "replace").rstrip("\n")
        if line.startswith("commit ") and len(line) == 47:
            commit, fname = line[7:15], "(message)"; continue
        if line.startswith("+++ b/"):
            fname = line[6:]; continue
        if line.startswith(("--- ", "diff --git", "index ", "@@")):
            continue
        for name, rx in RX:
            for m in rx.finditer(line):
                s = m.group(0)
                if not allowed(rules, fname, s):
                    counts[name] = counts.get(name, 0) + 1
                    if len(examples) < limit:
                        examples.append((commit, fname, name, s))
    proc.wait()
    return counts, examples


def main(argv):
    args, allow, history, mx, quiet = [], [], False, 50, False
    it = iter(argv)
    for a in it:
        if a == "--allow":
            allow.append(next(it))
        elif a == "--history":
            history = True
        elif a == "--max":
            mx = int(next(it))
        elif a == "--quiet":
            quiet = True
        else:
            args.append(a)
    paths = [Path(a) for a in (args or ["."])]
    RX.extend((n, re.compile(p)) for n, p in private_patterns([git_root(p) or p for p in paths]))
    total, by = 0, {}
    for p in paths:
        base = git_root(p) or (p if p.is_dir() else p.parent)
        rules = load_allow(allow or [base / ".public-allow"])
        for f in files_under(p):
            try:
                rel = str(f.resolve().relative_to(base.resolve()))
            except ValueError:
                rel = str(f)
            for h in scan_file(f, rel, rules):
                total += 1; by[h[2]] = by.get(h[2], 0) + 1
                if not quiet:
                    print(f"{h[0]}:{h[1]}: [{h[2]}] {h[3]}  | {h[4]}")
        if history and git_root(p) is not None:
            counts, ex = scan_history(git_root(p), rules, mx)
            print(f"history of {git_root(p).name}: " + (", ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "clean"))
            for c, fn, n, s in ex:
                print(f"  history {c} {fn}: [{n}] {s}")
    print("check_public: " + ("clean" if not total else f"{total} finding(s): " + ", ".join(f"{k} {v}" for k, v in sorted(by.items()))))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
