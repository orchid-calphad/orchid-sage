import json
import unittest
from pathlib import Path

from sage_mcp import reproduce as R
from sage_mcp import safety
from sage_mcp.repo import SageError, load_doc, schema_errors
from sage_mcp.tests.helpers import CRNI, CUZR, FIT_PY, HAS_CUZR, REPO, SageTestCase, localpaths


class Refusals(SageTestCase):
    def test_run_root_locations(self):
        home = localpaths.user_home()
        for bad in (str(REPO / "tmp-run"), str(REPO / "assessments" / "x"), str(localpaths.setting("runs_root") / "x"),
                    str(localpaths.setting("restricted_dir") / "x"), "relative/dir", str(home), "/"):
            with self.subTest(bad=bad):
                with self.assertRaises(SageError):
                    R.run_step(CRNI, "stage", bad, confirm=True)

    def test_non_empty_root_refused_at_stage(self):
        r = self.tmp / "full"
        r.mkdir()
        (r / "something").write_text("x")
        with self.assertRaises(SageError) as cm:
            R.run_step(CRNI, "stage", str(r), confirm=True)
        self.assertIn("not empty", str(cm.exception))

    def test_unmarked_root_refused(self):
        r = self.tmp / "unmarked"
        r.mkdir()
        with self.assertRaises(SageError) as cm:
            R.run_step(CRNI, "environment_check", str(r), confirm=True, python="/usr/bin/python3")
        self.assertIn("not a run root created by sage_mcp", str(cm.exception))

    @unittest.skipUnless(HAS_CUZR, "Cu-Zr draft assessment not in this copy")
    def test_long_step_needs_flag(self):
        # Cu-Zr fits have no measured wall time on record: long by default (fail closed)
        out = R.run_step(CUZR, "h2_s7", str(self.tmp / "rr"), confirm=True)
        self.assertTrue(out["refused"])
        self.assertIn("allow_long", out["reason"])
        self.assertFalse((self.tmp / "rr").exists())

    def test_confirm_required(self):
        out = R.run_step(CRNI, "stage", str(self.tmp / "rr"), confirm=False)
        self.assertTrue(out["dry_run"])
        self.assertFalse((self.tmp / "rr").exists())

    def test_judgement_never_executed(self):
        out = R.run_step(CRNI, "pick_solid", str(self.tmp / "rr"), confirm=True)
        self.assertFalse(out["executed"])
        self.assertIn("recorded_decision", out)

    def test_command_writes_outside_root(self):
        root = self.tmp / "root"
        root.mkdir()
        bad = ["python3 x.py > /etc/out.txt", "cp a.txt /tmp/elsewhere.txt", "python3 x.py --out ../escape.json", "rm -f x",
               "cd / && ls", "ssh host ls", "docker run img"]
        for cmd in bad:
            with self.subTest(cmd=cmd):
                self.assertTrue(safety.check_command(cmd, root))
        self.assertEqual(safety.check_command("python3 /abs/tool.py in.json results/out.json --out results/x.json", root), [])


@unittest.skipUnless(FIT_PY.exists(), "fit interpreter (fit_python) not configured on this host")
class DeterministicRerun(SageTestCase):
    """Stage the Cr-Ni pick, run its cheap deterministic items for real and compare (about 20 s)."""

    def test_stage_run_compare(self):
        root = str(self.tmp / "rerun")
        st = R.run_step(CRNI, "stage", root, confirm=True)
        self.assertTrue(st["executed"])
        self.assertTrue((Path(root) / safety.MARKER).is_file())
        self.assertTrue((Path(root) / "scripts" / "fit.py").is_file())
        env = R.run_step(CRNI, "environment_check", root, confirm=True, python=str(FIT_PY))
        self.assertTrue(env["pass"], env)
        ev = R.run_step(CRNI, "evaluate_states", root, confirm=True, python=str(FIT_PY))
        self.assertEqual(ev["returncode"], 0, ev.get("log_tail"))
        ran = ["stage", "environment_check", "evaluate_states"]
        if True:   # tdb_header reads the pick from the bundle copy (no campaign file needed)
            hd = R.run_step(CRNI, "tdb_header", root, confirm=True)
            self.assertEqual(hd["returncode"], 0, hd.get("log_tail"))
            ran.append("tdb_header")
        for card in (Path(root) / "run_cards").glob("*.json"):
            self.assertEqual(schema_errors(json.loads(card.read_text())), [], card.name)
        cmp_ = R.compare_outputs(CRNI, root)
        det = [c for c in cmp_["checks"] if c.get("item") in ran[2:] and "pass" in c]
        self.assertTrue(det)
        for c in det:
            self.assertTrue(c["pass"], c)
        self.assertIn("step4", cmp_["not_run"])
        self.assertTrue((Path(root) / "comparison" / "comparison.md").is_file())


if __name__ == "__main__":
    unittest.main()
