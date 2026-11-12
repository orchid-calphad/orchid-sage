"""Machine-specific locations, read from the environment or a local config file, never written in code (standard library only).

Every location outside this repository (data checkouts, interpreters, campaign directories, other repositories) and every host
name comes from, in this order: an environment variable, the local config file, a default inside the repository. The
local config is ``local/config.json`` at the repository root (gitignored; ``ORCHID_SAGE_CONFIG`` names another file); the
template ``local.example/config.json`` is committed. A clean clone needs no config: data default to ``data/`` and state to
``local/`` inside the checkout, host labels default to the machine labels used in the public records (spark1..spark4 for
the four NVIDIA DGX Spark nodes, aarch64 Linux; studio for the Mac Studio, arm64 macOS).

  setting(key)       env var > local config > default (a path setting is returned as a Path, '~' expanded)
  host(label)        the host name for a machine label (local config 'hosts'), else the label itself
  expand(p)          a path as written in a record or given by a user: '<orchid-sage>/...' (this repository, wherever it
                     was checked out when the record was written) -> this checkout; other '<home>/...' -> record_home();
                     '~' or a tilde-slash path given by a user -> that user's home; a relative path -> relative to the repository root
  tilde(p)           the inverse for writing records: this checkout as '<orchid-sage>', the home directory as '<home>'
  record_home()      the directory that '<home>' means in the records: ORCHID_RECORD_HOME, config 'record_home', else the
                     current user's home directory (the one place the home directory is looked up)

The public records name machine-specific locations by placeholder only (protocols/tools/public_sanitize.py):
<orchid-sage> this repository, <home> the home directory of the machine that wrote the record, <fit-python> the fit
interpreter (given by the operator) and <fit-env> its virtual environment.
"""
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REPO_ALIASES = ("<orchid-sage>",)                 # how the records name this repository
RECORD_HOME = "<home>"                              # how the records name the home directory of the machine that wrote them
# how the records name campaign directories, restricted material and the fit interpreter; these are strings to recognise
# in records, not locations to use (those come from setting())
RECORD_CAMPAIGN_PREFIXES = ("<home>/ScientificRuns", "<home>/data/private")
RECORD_FIT_PYTHON = "<fit-python>"

# key -> (environment variable, default; a str default is relative to the repository root, None = not available)
SETTINGS = {
    "record_home": ("ORCHID_RECORD_HOME", None),
    "orchid_data_dir": ("ORCHID_DATA_DIR", "data/orchid-data"),             # ORCHID data release checkout
    "orchid_data_next": ("ORCHID_DATA_NEXT", "data/orchid-data-next"),      # ORCHID data 'next' branch checkout
    "orchid_mcp_src": ("ORCHID_MCP_SRC", None),                            # orchid-mcp package source (optional context)
    "site_data_dir": ("ORCHID_SITE_DATA_DIR", None),                       # orchid-project.org data/ (optional context)
    "phaseforgeplus_src": ("PHASEFORGEPLUS_SRC", None),                    # PhaseForgePlus src/ (fits)
    "paper_repo": ("CRNI_PAPER_REPO", None),                               # the Cr-Ni paper repository (figure style)
    "brand_repo": ("ORCHID_BRAND_REPO", None),                             # orchid-brand repository (palette sync)
    "runs_root": ("ORCHID_RUNS_ROOT", "data/runs"),                        # campaign directories
    "restricted_dir": ("ORCHID_RESTRICTED_DIR", "data/private"),           # restricted material (never published)
    "fit_python": ("ORCHID_FIT_PYTHON", None),                             # interpreter with ESPEI (gradient PR) + pycalphad
    "mlip_python": ("ORCHID_MLIP_PYTHON", None),                           # interpreter for the MLIP cross-check
    "state_dir": ("SAGE_MCP_STATE_DIR", "local/state"),                    # orchid-sage MCP server state
    "backends_file": ("SAGE_MCP_BACKENDS", "local/backends.json"),         # orchid-sage MCP executor backends
}
_cfg = None


def config():
    global _cfg
    if _cfg is None:
        p = Path(os.environ.get("ORCHID_SAGE_CONFIG") or REPO / "local" / "config.json")
        _cfg = json.loads(p.read_text()) if p.is_file() else {}
    return _cfg


def _path(v):
    q = Path(os.path.expanduser(str(v)))        # '~' in a local config or an environment variable means this user's home
    return q if q.is_absolute() else REPO / q


def setting(key, default=...):
    env, dflt = SETTINGS[key]
    v = os.environ.get(env) if env else None
    if v is None:
        v = config().get(key)
    if v is None:
        v = dflt if default is ... else default
    return None if v is None else _path(v)


def python(key):
    """An interpreter setting (fit_python, mlip_python); the running interpreter when none is configured."""
    return str(setting(key) or sys.executable)


def protected_paths():
    """Directories the MCP server never writes into (config 'protected_paths', SAGE_MCP_FORBIDDEN): live campaigns,
    restricted material, source checkouts. The restricted directory and the runs root are always included."""
    ps = [_path(p) for p in config().get("protected_paths", [])]
    ps += [_path(p) for p in os.environ.get("SAGE_MCP_FORBIDDEN", "").split(os.pathsep) if p]
    return ps + [setting("restricted_dir"), setting("runs_root")]


DEFAULT_LABELS = {"studio": "mac-studio"}            # the labels of public_sanitize.py


def host(label):
    """Host name of a machine label (studio, spark1..spark4; spark1_ssh etc. for an ssh alias); without a local config the
    label as the public records write it (mac-studio, spark1, ...)."""
    hs = config().get("hosts") or {}
    if label in hs:
        return hs[label]
    if label.endswith("_ssh"):
        return host(label[:-4])
    return DEFAULT_LABELS.get(label, label)


def sibling(name):
    """Another repository checked out next to this one (config 'siblings'[name], else ../name)."""
    v = (config().get("siblings") or {}).get(name)
    return _path(v) if v else REPO.parent / name


def remote_home():
    """The home directory on the DGX Spark nodes as their own records write it (config 'spark_home'); used only to
    recognise and shorten paths in those records."""
    return config().get("spark_home") or "<spark_home>"


def record_home():
    v = os.environ.get("ORCHID_RECORD_HOME") or config().get("record_home")
    return Path(os.path.expanduser(v)) if v else user_home()


def user_home():
    """The current user's home directory: used only to read '<home>' in records, '~' in a user's path, and to refuse it as a run root."""
    return Path(os.path.expanduser("~"))


def expand(p):
    s = str(p)
    for a in REPO_ALIASES:
        if s == a or s.startswith(a + "/"):
            return REPO / s[len(a) + 1:] if s != a else REPO
    if s == RECORD_HOME or s.startswith(RECORD_HOME + "/"):
        return record_home() / s[len(RECORD_HOME) + 1:] if s != RECORD_HOME else record_home()
    if s == "~" or s.startswith("~/"):                        # a path a user gives: that user's home
        return user_home() / s[2:] if s != "~" else user_home()
    q = Path(s)
    return q if q.is_absolute() else REPO / q


def tilde(p):
    s = str(p); h = str(record_home())
    if s == str(REPO) or s.startswith(str(REPO) + os.sep):
        return REPO_ALIASES[0] + s[len(str(REPO)):]
    return RECORD_HOME + s[len(h):] if s == h or s.startswith(h + os.sep) else s


if __name__ == "__main__":      # python3 localpaths.py KEY  -> the setting (interpreters: the running one when not configured)
    k = sys.argv[1]
    print(python(k) if k.endswith("_python") else (setting(k) or ""))
