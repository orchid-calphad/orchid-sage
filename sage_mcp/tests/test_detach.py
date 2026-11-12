"""Start/status pattern: long reproduce items run detached; step_status writes the run card (no fit is run)."""

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

from sage_mcp import reproduce as R
from sage_mcp import runner, safety, server
from sage_mcp.repo import find_protocol, schema_errors
from sage_mcp.tests.helpers import CRNI, REPO, SageTestCase

OUT_TEXT = "fit done\n"
SLOW = ("{PY} -c \"import pathlib,time; time.sleep(%s); pathlib.Path('results').mkdir(exist_ok=True); "
        "pathlib.Path('results/out.txt').write_text('fit done\\n'); print('converged')\"")


def _item(iid: str, long: bool, sleep: float = 1.5, rc: int = 0) -> dict:
    cmd = SLOW % sleep if rc == 0 else "{PY} -c \"import sys; print('boom'); sys.exit(%d)\"" % rc
    return {"id": iid, "step": "step4", "kind": "numerical" if long else "deterministic", "source": "sage_mcp test item",
            "command": cmd, "env": {"SAGE_TEST_ENV": "1"}, "copy": {}, "copy_sha256": {}, "cwd": None, "mkdirs": [],
            "compute": {"class": "CPU", "estimate_s": 2, "long": long},
            "expect": [{"rule": "byte", "path": "results/out.txt", "sha256": hashlib.sha256(OUT_TEXT.encode()).hexdigest()}]}


class Detached(SageTestCase):
    def setUp(self):
        super().setUp()
        _, d = find_protocol(CRNI)
        self.ref = f"{d['id']}@{d['version']}"
        self.root = safety.create_fresh_root(str(self.tmp / "rr"), "reproduce", self.ref)
        safety.write_marker(self.root, "reproduce", self.ref)
        self.items = [_item("fake_fit", True), _item("fake_short", False, sleep=0), _item("fake_fail", True, rc=3)]
        self._orig = R.repro_items
        R.repro_items = lambda d: [dict(i) for i in self.items]
        self._max = runner.MAX_WAIT_S

    def tearDown(self):
        R.repro_items = self._orig
        runner.MAX_WAIT_S = self._max
        for item in R._job_items(self.root):   # let the jobs this test started end before the temp dir goes
            runner.wait_job(self.root, item, 30)
        super().tearDown()

    def run_(self, item, **kw):
        return R.run_step(CRNI, item, str(self.root), confirm=True, allow_long=True, python=sys.executable, **kw)

    def test_long_item_detaches_and_status_writes_card(self):
        t0 = time.time()
        out = self.run_("fake_fit")
        self.assertLess(time.time() - t0, 1.4, "the call must return before the item ends")
        self.assertEqual(out["status"], "running")
        self.assertTrue(out["detached"])
        card = self.root / "run_cards" / f"{CRNI.split('@')[0]}-fake_fit.json"
        self.assertFalse(card.exists())
        again = self.run_("fake_fit")
        self.assertTrue(again["refused"])
        self.assertEqual(again["status"], "running")
        busy = self.run_("fake_short")
        self.assertTrue(busy["refused"])
        self.assertEqual(busy["status"], "busy")
        cmp_running = R.compare_outputs(CRNI, str(self.root))
        self.assertIn("fake_fit", cmp_running["running_or_unrecorded"])
        st = R.step_status(CRNI, str(self.root), "fake_fit", wait_s=60)
        self.assertEqual(st["status"], "finished", st)
        self.assertEqual(st["returncode"], 0)
        self.assertIn("converged", st["log_tail"])
        self.assertTrue(card.is_file())
        c = json.loads(card.read_text())
        self.assertEqual(schema_errors(c), [])
        self.assertEqual(c["status"], "complete")
        self.assertEqual(c["results"]["returncode"], 0)
        self.assertEqual(len(c["pids"]), 2)
        self.assertEqual([o["path"].endswith("results/out.txt") for o in c["outputs"]], [True])
        self.assertIn("{PY}", self.items[0]["command"])
        self.assertIn(sys.executable, c["command"])
        mtime = card.stat().st_mtime_ns
        st2 = R.step_status(CRNI, str(self.root), "fake_fit", wait_s=0)
        self.assertEqual(st2["run_card"], st["run_card"])
        self.assertEqual(card.stat().st_mtime_ns, mtime, "the card is written once")
        cmp_ = R.compare_outputs(CRNI, str(self.root))
        chk = [x for x in cmp_["checks"] if x["item"] == "fake_fit"]
        self.assertTrue(chk and all(x["pass"] for x in chk), chk)
        listing = R.step_status(CRNI, str(self.root))
        self.assertEqual([(j["item"], j["status"], j["run_card_written"]) for j in listing["jobs"]], [("fake_fit", "finished", True)])

    def test_failed_item_card_says_failed(self):
        self.run_("fake_fail")
        st = R.step_status(CRNI, str(self.root), "fake_fail", wait_s=60)
        self.assertEqual(st["returncode"], 3)
        c = json.loads(Path(st["run_card"]).read_text())
        self.assertEqual(c["status"], "failed")
        self.assertEqual(schema_errors(c), [])

    def test_short_item_stays_synchronous_and_detach_can_be_forced(self):
        out = self.run_("fake_short")
        self.assertNotIn("detached", out)
        self.assertTrue(Path(out["run_card"]).is_file())
        st = R.step_status(CRNI, str(self.root), "fake_short")
        self.assertEqual(st["status"], "finished")
        forced = self.run_("fake_short", detach=True)
        self.assertEqual(forced["status"], "running")
        self.assertEqual(R.step_status(CRNI, str(self.root), "fake_short", wait_s=60)["status"], "finished")

    def test_wait_is_capped(self):
        runner.MAX_WAIT_S = 0.3
        self.run_("fake_fit")
        t0 = time.time()
        st = R.step_status(CRNI, str(self.root), "fake_fit", wait_s=10_000)
        self.assertLess(time.time() - t0, 1.2)
        self.assertEqual(st["status"], "running")
        self.assertIn("log_tail", st)

    def test_restart_moves_old_job_aside(self):
        self.run_("fake_short", detach=True)
        R.step_status(CRNI, str(self.root), "fake_short", wait_s=60)
        self.run_("fake_short", detach=True)
        R.step_status(CRNI, str(self.root), "fake_short", wait_s=60)
        moved = list((self.root / "jobs" / "superseded").glob("fake_short-*/fake_short.json"))
        self.assertEqual(len(moved), 1)
        self.assertTrue((moved[0].parent / "fake_short.recorded.json").is_file())

    def test_lost_job_reported_without_card(self):
        f = runner.job_files(self.root, "fake_fit")
        f["job"].parent.mkdir(parents=True, exist_ok=True)
        gone = subprocess.Popen([sys.executable, "-c", "pass"])
        gone.wait()
        f["job"].write_text(json.dumps({"item": "fake_fit", "command": "x", "cwd": str(self.root), "log": str(self.root / "x.log"),
                                        "launched": runner.now(), "wrapper_pid": gone.pid}))
        st = R.step_status(CRNI, str(self.root), "fake_fit")
        self.assertEqual(st["status"], "lost")
        self.assertFalse((self.root / "run_cards").exists())

    def test_job_outlives_the_process_that_started_it(self):
        """A job started by a server process that then exits (the MCP session ended) still finishes and records."""
        code = ("import sys; from pathlib import Path; from sage_mcp import runner; "
                "r = Path(sys.argv[1]); runner.start_detached(\"%s -c 'import time; time.sleep(1); print(42)'\" % sys.executable, "
                "r, r, r / 'reproduce_logs' / 'orphan.log', 'orphan')")
        subprocess.run([sys.executable, "-c", code, str(self.root)], cwd=REPO, check=True, timeout=30)
        st = runner.wait_job(self.root, "orphan", 30)
        self.assertEqual(st["state"], "finished")
        self.assertEqual(st["done"]["returncode"], 0)
        self.assertIn("42", (self.root / "reproduce_logs" / "orphan.log").read_text())

    def test_server_exposes_start_status(self):
        tools = {t["name"]: t for t in server.tool_descriptions()}
        self.assertEqual(tools["step_status"]["inputSchema"]["required"], ["protocol", "run_root"])
        self.assertIn("detach", tools["run_step"]["inputSchema"]["properties"])
        self.assertEqual(tools["start_step"]["inputSchema"]["required"], ["protocol", "step_id", "run_root"])
