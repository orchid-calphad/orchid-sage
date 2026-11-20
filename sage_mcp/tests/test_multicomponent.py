"""Assessments above two components (local multicomponent branch). Records, decisions and external runs work, and the
binary-only evidence builder is never run on them."""

import json
import os
import tempfile
from pathlib import Path

from sage_mcp import fresh as F
from sage_mcp import reproduce as R
from sage_mcp import runner
from sage_mcp.repo import SageError
from sage_mcp.tests.helpers import SageTestCase, orchid_data_dir


class Ternary(SageTestCase):
    def setUp(self):
        super().setUp()
        os.environ["ORCHID_DATA_DIR"] = str(orchid_data_dir(self.tmp))
        self.root = self.tmp / "alcti"
        self.a = "alcti-test"
        self.new = F.new_assessment("AL-C-TI", self.a, str(self.root))

    def _req(self, key):
        st = F.load_state(self.root)
        return next(r for r in st["decision_requests"] if r["key"] == key and r["status"] == "open")

    def test_new_assessment(self):
        keys = {r["key"] for r in self.new["open_decision_requests"]}
        self.assertEqual(keys, {"read_established_practice", "model_phases", "t_range", "unaries", "subsystems"})
        self.assertTrue(self.new["validation"]["ok"], self.new["validation"])
        sub = self._req("subsystems")
        for s in ("AL-C", "AL-TI", "C-TI"):
            self.assertIn(s, sub["question"])
        self.assertIn("build_oneshot_tdb", sub["blocks"])
        _, spec = F.current_spec(self.root)
        self.assertEqual(spec["system"], "AL-C-TI")
        self.assertTrue(any("binary systems" in x and "AL-C, AL-TI, C-TI" in x for x in spec["limitations"]))

    def test_bad_systems_refused(self):
        for i, bad in enumerate(("AL-TI-C", "AL-AL-TI", "AL", "AL--TI", "al-c-ti-")):
            with self.assertRaises(SageError, msg=bad):
                F.new_assessment(bad, f"bad{i}", str(self.tmp / f"bad{i}"))

    def test_evidence_steps_are_external(self):
        seq = {x["id"]: x for x in F.sequence(self.root)}
        for sid in F.GATHER_STEPS:
            self.assertEqual(seq[sid]["mode"], "external")
            self.assertFalse(seq[sid]["executable"])
        # <EL> is the binary composition axis, so above two components it stays unbound and is never guessed
        self.assertIn("EL", seq["evidence_ledger"]["unbound"])
        b = F._bindings(self.root, F.current_spec(self.root)[1], F.load_state(self.root))
        self.assertEqual((b["elements"], b["n_components"]), ("AL,C,TI", "3"))
        self.assertNotIn("EL", b)
        out = R.run_step(self.a, "build_datasets", str(self.root), confirm=True)
        self.assertTrue(out.get("refused"), out)

    def test_gather_evidence_reports_only(self):
        g = F.gather_evidence(self.a)
        self.assertTrue(g["preview"])
        self.assertFalse(g["frozen"])
        self.assertEqual([h["system"] for h in g["orchid_holdings"]], ["AL-C-TI", "AL-C", "AL-TI", "C-TI"])
        self.assertFalse((self.root / "evidence" / "MANIFEST.json").exists())
        st = F.load_state(self.root)
        for sid in F.GATHER_STEPS:
            self.assertNotEqual(st["steps"].get(sid, {}).get("status"), "done")

    def test_external_run_and_decision(self):
        F.record_decision(self.a, self._req("subsystems")["id"], "evaluated binaries enter as written", who="PI (test)",
                          why="test fixture", bindings={"subsystem_tdbs": {"AL-C": "a.tdb", "AL-TI": "b.tdb", "C-TI": "c.tdb"}})
        self.assertEqual(F.load_state(self.root)["bindings"]["subsystem_tdbs"]["AL-TI"], "b.tdb")
        with tempfile.TemporaryDirectory(prefix="ext-") as d:
            ext = Path(d)
            (ext / "run_cards").mkdir()
            log = ext / "build.log"
            log.write_text("ternary evidence built by the system's own tool\n")
            rec = {"command": "python3 build_tialc_evidence.py", "returncode": 0, "started": runner.now(), "finished": runner.now(),
                   "wall_s": 1.0, "log": str(log)}
            _, spec = F.current_spec(self.root)
            card = runner.write_run_card(ext, f"{self.a}-build_datasets-ext", f"{spec['id']}@{spec['version']}",
                                         spec["instantiates"][0]["protocol"], "build_datasets", rec, None, [], [log])
            out = F.record_external_run(self.a, "build_datasets", str(card))
        self.assertTrue(out["recorded"])
        self.assertEqual(F.load_state(self.root)["steps"]["build_datasets"]["status"], "done")
        self.assertEqual(json.loads(Path(out["run_card"]).read_text())["executes"]["step"], "build_datasets")
        self.assertTrue(F.validate_assessment(self.a)["ok"], F.validate_assessment(self.a))


class Quaternary(SageTestCase):
    def test_subsystems(self):
        os.environ["ORCHID_DATA_DIR"] = str(orchid_data_dir(self.tmp))
        F.new_assessment("AL-C-TI-ZR", "alctizr-test", str(self.tmp / "q"))
        st = F.load_state(self.tmp / "q")
        rq = next(r for r in st["decision_requests"] if r["key"] == "subsystems")
        subs = F._subsystems(["AL", "C", "TI", "ZR"])
        self.assertEqual(len(subs), 10)   # 6 binaries and 4 ternaries
        self.assertEqual(subs[:6], ["AL-C", "AL-TI", "AL-ZR", "C-TI", "C-ZR", "TI-ZR"])
        self.assertEqual(subs[6:], ["AL-C-TI", "AL-C-ZR", "AL-TI-ZR", "C-TI-ZR"])
        for s in subs:
            self.assertIn(s, rq["question"])
        self.assertTrue(F.validate_assessment("alctizr-test")["ok"])


class BinaryUnchanged(SageTestCase):
    def test_binary_keeps_el_and_internal_steps(self):
        os.environ["ORCHID_DATA_DIR"] = str(orchid_data_dir(self.tmp))
        out = F.new_assessment("AL-CU", "alcu-b", str(self.tmp / "b"))
        self.assertNotIn("subsystems", {r["key"] for r in out["open_decision_requests"]})
        root = self.tmp / "b"
        _, spec = F.current_spec(root)
        self.assertEqual(spec["limitations"], [])
        b = F._bindings(root, spec, F.load_state(root))
        self.assertEqual(b["EL"], "CU")
        seq = {x["id"]: x for x in F.sequence(root)}
        for sid in F.GATHER_STEPS:
            self.assertEqual(seq[sid]["mode"], "internal")
