"""Guard against overwriting frozen records (standard library only).

A record is FROZEN when it exists and
  - its sha256 is pinned by a protocol (protocols/general/*.yaml, protocols/specific/*.yaml), a run card, a dashboard's data
    or figure manifest (they pin the code that made them), a crate (protocols/crates/*/ro-crate-metadata.json) or a
    manifest of the assessments (assessments/*/{code,evidence,intake}/*.json);
  - or it is a protocol YAML whose status is not draft (approved, final, ...).
A builder may rewrite a frozen record with identical bytes; it may never change it. Every builder writes through this
module: `Writes` collects a builder's outputs and commits them all or none, so a refusal writes nothing.

On a refusal the builder prints one 'FROZEN:' line per file to stderr, appends them to $ORCHID_FROZEN_LOG when that is
set (tools/build_all.sh reads it) and exits with status 3. With --check (or ORCHID_FROZEN_CHECK=1) a builder computes its
outputs, reports what it would refuse and what it would change, and writes nothing.

  python3 tools/frozen.py PATH ...      -> is each file frozen, and by what (exit 0)
  python3 tools/frozen.py install SRC DST  -> copy SRC to DST through the guard (exit 3 if DST is frozen and would change)

Some builders are frozen records themselves (a dashboard's data pins the sha256 of the extractor that made it), so they
cannot be edited to call this module; build_all.sh runs them into local/state/build_tmp/ and installs the result here.
"""
import glob
import hashlib
import io
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # protocols/
REPO = ROOT.parent
EXIT_FROZEN = 3
HEX = re.compile(rb"\b[0-9a-f]{64}\b")
STATUS = re.compile(rb"^status:\s*'?([A-Za-z_-]+)", re.M)
PIN_SOURCES = ("protocols/general/*.yaml", "protocols/specific/*.yaml", "protocols/run_cards/*.json", "protocols/dashboards/*/dashboard_data.json",
               "protocols/figures/*/figures_manifest.json", "protocols/crates/*/ro-crate-metadata.json",
               "assessments/*/code/MANIFEST*.json", "assessments/*/evidence/MANIFEST*.json", "assessments/*/intake/*.json")
_pins = None


def check_mode():
    return os.environ.get("ORCHID_FROZEN_CHECK") == "1" or "--check" in sys.argv


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _rel(p):
    try:
        return str(Path(p).resolve().relative_to(REPO.resolve()))
    except ValueError:
        return str(p)


def pins(repo=None):
    """sha256 -> the first file that pins it (read once per process)."""
    global _pins
    if _pins is None or repo is not None:
        base = Path(repo) if repo is not None else REPO
        found = {}
        for pat in PIN_SOURCES:
            for f in sorted(glob.glob(str(base / pat))):
                for h in HEX.findall(Path(f).read_bytes()):
                    found.setdefault(h.decode(), _rel(f))
        if repo is not None:
            return found
        _pins = found
    return _pins


def frozen_reason(path, pinmap=None):
    """Why the existing file at path is frozen, or None (also None when it does not exist)."""
    p = Path(path)
    if not p.is_file():
        return None
    data = p.read_bytes()
    if p.suffix == ".yaml" and p.parent.name in ("general", "specific"):
        m = STATUS.search(data)
        if m and m.group(1).decode() != "draft":
            return f"protocol with status {m.group(1).decode()}"
    by = (pinmap if pinmap is not None else pins()).get(sha(data))
    if by and Path(REPO / by).resolve() != p.resolve():
        return f"sha256 pinned by {by}"
    return None


def _bytes(data):
    return data.encode() if isinstance(data, str) else bytes(data)


class Writes:
    """Collect a builder's outputs; commit() writes all of them or none."""

    def __init__(self, who):
        self.who, self.items = who, {}

    def add(self, path, data):
        self.items[Path(path)] = _bytes(data)

    def copy(self, src, dst):
        self.add(dst, Path(src).read_bytes())

    def refusals(self):
        out = []
        for p, data in self.items.items():
            if p.is_file() and p.read_bytes() != data:
                r = frozen_reason(p)
                if r:
                    out.append((p, r))
        return out

    def commit(self):
        bad = self.refusals()
        changed = [p for p, d in self.items.items() if not p.is_file() or p.read_bytes() != d]
        if bad:
            refuse(self.who, bad)
        if check_mode():
            print(f"{self.who} --check: {len(self.items)} outputs, {len(changed)} would change, none frozen", file=sys.stderr)
            for p in changed:
                print(f"  would write {_rel(p)}", file=sys.stderr)
            return changed
        for p, d in self.items.items():
            if p in changed:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(d)
        return changed


def refuse(who, bad):
    lines = [f"FROZEN: {_rel(p)} ({r}): its content would change; {who} wrote nothing" for p, r in bad]
    msg = "\n".join(lines)
    print(msg, file=sys.stderr)
    log = os.environ.get("ORCHID_FROZEN_LOG")
    if log:
        with open(log, "a") as f:
            f.write(msg + "\n")
    sys.exit(EXIT_FROZEN)


def write(path, data, who=None):
    """Write one file through the guard (refuses a frozen file whose content would change)."""
    w = Writes(who or Path(sys.argv[0]).name)
    w.add(path, data)
    w.commit()


def copy(src, dst, who=None):
    write(dst, Path(src).read_bytes(), who)


def render(fig, fmt, **kw):
    """The bytes matplotlib would write for fig in format fmt (nothing written)."""
    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, **kw)
    return buf.getvalue()


def savefig(fig, path, who=None, **kw):
    """matplotlib savefig through the guard (rendered to memory first)."""
    write(path, render(fig, Path(path).suffix.lstrip("."), **kw), who)


if __name__ == "__main__":
    if sys.argv[1:2] == ["install"]:          # frozen.py install SRC DST: copy through the guard (for a builder that is
        copy(sys.argv[2], sys.argv[3], "frozen.py install")   # itself a frozen record and so cannot be edited)
    else:
        for a in sys.argv[1:]:
            print(f"{a}: {frozen_reason(a) or 'not frozen'}")
