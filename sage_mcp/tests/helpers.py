"""Shared test setup: an isolated server state dir, no network, local data only."""

import json
import os
import socket
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CRNI = "crni-paper-fit-step4-s1@0.1.0-draft"
CUZR = "cuzr-oneshot-h2-s7@0.1.0-draft"
# the Cu-Zr draft assessment is not in the public copy (only the standard and the Cr-Ni assessment are published)
HAS_CUZR = (REPO / "protocols" / "specific" / f"{CUZR}.yaml").is_file()
sys.path.insert(0, str(REPO / "protocols" / "tools"))
import localpaths  # noqa: E402

FIT_PY = localpaths.setting("fit_python") or Path("/nonexistent/fit_python-not-configured")   # ORCHID_FIT_PYTHON or local/config.json


class NoNetwork:
    def __enter__(self):
        self._orig = socket.socket.connect

        def refuse(*a, **k):  # tests must never touch the network
            raise AssertionError("network access attempted during tests")

        socket.socket.connect = refuse
        return self

    def __exit__(self, *exc):
        socket.socket.connect = self._orig


class SageTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="sage-mcp-test-")
        self.tmp = Path(self._tmp.name).resolve()
        self._env = dict(os.environ)
        os.environ["SAGE_MCP_STATE_DIR"] = str(self.tmp / "state")
        os.environ["SAGE_MCP_BACKENDS"] = str(self.tmp / "backends.json")
        self._nonet = NoNetwork().__enter__()

    def tearDown(self):
        self._nonet.__exit__(None, None, None)
        os.environ.clear()
        os.environ.update(self._env)
        self._tmp.cleanup()


def orchid_fixture(base: Path) -> Path:
    """A two-file ORCHID espei fixture for AG-PD-like checks when no local orchid-data checkout exists."""
    d = base / "orchid-data" / "espei" / "experimental" / "AL-CU"
    d.mkdir(parents=True)
    single = {"components": ["AL", "CU", "VA"], "phases": ["BCC_A2"], "conditions": {"P": 101325, "T": [1082.65]}, "output": "ZPF",
              "values": [[["BCC_A2", ["CU"], [0.82]]]], "reference": "fixture", "comment": "ORC-GOVPCZZH47"}
    tie = {"components": ["AL", "CU", "VA"], "phases": ["FCC_A1", "LIQUID"], "conditions": {"P": 101325, "T": [1300.0]}, "output": "ZPF",
           "values": [[["LIQUID", ["CU"], [0.80]], ["FCC_A1", ["CU"], [0.86]]]], "reference": "fixture", "comment": "ORC-AAAAAAAAAA"}
    (d / "fixture.zpf-00.json").write_text(json.dumps(single))
    (d / "fixture.zpf-01.json").write_text(json.dumps(tie))
    return base / "orchid-data"


def orchid_data_dir(base: Path) -> Path:
    env = os.environ.get("ORCHID_DATA_DIR")
    if env and (Path(env) / "espei" / "experimental" / "AL-CU").is_dir():
        return Path(env)
    local = localpaths.setting("orchid_data_dir")
    if (local / "espei" / "experimental" / "AL-CU").is_dir():
        return local
    return orchid_fixture(base)
