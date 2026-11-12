import json
import os
import unittest
from pathlib import Path

from sage_mcp import fresh as F
from sage_mcp import reproduce as R
from sage_mcp.repo import SageError, schema_errors
from sage_mcp.tests.helpers import SageTestCase, orchid_data_dir

PHASES = ["BCC_A2", "FCC_A1", "LIQUID"]


class FreshAssessment(SageTestCase):
    def setUp(self):
        super().setUp()
        os.environ["ORCHID_DATA_DIR"] = str(orchid_data_dir(self.tmp))
        self.root = self.tmp / "alcu"
        self.a = "alcu-test"
        self.new = F.new_assessment("AL-CU", self.a, str(self.root))

    def _req(self, key):
        st = F.load_state(self.root)
        return next(r for r in st["decision_requests"] if r["key"] == key and r["status"] == "open")

    def _decide_preflight(self, phases=PHASES):
        F.record_decision(self.a, self._req("read_established_practice")["id"], "0.0b rows 1-12 apply; nothing new in the brief",
                          who="PI (test)", why="test fixture")
        F.record_decision(self.a, self._req("model_phases")["id"], "disordered solutions and the liquid", who="PI (test)",
                          why="test fixture", bindings={"phases": phases})
        F.record_decision(self.a, self._req("t_range")["id"], "300-2000 K", who="PI (test)", why="test", bindings={"T_range": [300, 2000]})

    def test_new_assessment(self):
        self.assertEqual(self.new["version"], "0.1.0")
        keys = {r["key"] for r in self.new["open_decision_requests"]}
        self.assertEqual(keys, {"read_established_practice", "model_phases", "t_range", "unaries"})
        self.assertTrue(self.new["validation"]["ok"], self.new["validation"])
        self.assertTrue((self.root / "PLAN.md").is_file())
        self.assertEqual(self.new["next"]["id"], "read_established_practice")
        self.assertEqual(self.new["next"]["mode"], "judgement")
        with self.assertRaises(SageError):
            F.new_assessment("CU-AL", "x", str(self.tmp / "y"))  # not alphabetical
        with self.assertRaises(SageError):
            F.new_assessment("AL-CU", "other", str(self.root))  # not a fresh root

    def test_judgement_blocks_until_decided(self):
        out = R.run_step(self.a, "read_established_practice", str(self.root), confirm=True)
        self.assertFalse(out["executed"])
        self.assertTrue(out["judgement"])
        seq = {x["id"]: x for x in F.sequence(self.root)}
        self.assertTrue(seq["write_plan"]["blockers"])
        blocked = R.run_step(self.a, "write_plan", str(self.root), confirm=True)
        self.assertTrue(blocked["refused"])
        with self.assertRaises(SageError):
            F.record_decision(self.a, out["decision_request"]["id"], "x", who="sage_mcp", why="y")
        with self.assertRaises(SageError):
            F.record_decision(self.a, out["decision_request"]["id"], "x", who="PI", why="")
        self._decide_preflight()
        seq = {x["id"]: x for x in F.sequence(self.root)}
        self.assertEqual(seq["read_established_practice"]["status"], "done")
        self.assertEqual(seq["write_plan"]["blockers"], [])
        wp = R.run_step(self.a, "write_plan", str(self.root), confirm=True)
        self.assertTrue(wp["executed"])
        card = json.loads(Path(wp["run_card"]).read_text())
        self.assertEqual(schema_errors(card), [])
        self.assertEqual(F.next_step(self.a)["next"]["id"], "verify_build")

    def test_gather_evidence(self):
        pre = F.gather_evidence(self.a)
        self.assertTrue(pre["preview"])
        self.assertFalse((self.root / "evidence" / "MANIFEST.json").exists())
        self.assertGreater(pre["n_files"], 0)
        self._decide_preflight()
        g = F.gather_evidence(self.a)
        self.assertFalse(g["preview"])
        man = json.loads((self.root / "evidence" / "MANIFEST.json").read_text())
        self.assertEqual(set(man) >= {"bundle", "version", "builder", "rule", "files", "held", "counts", "bundle_sha256"}, True)
        states = json.loads((self.root / "evidence" / "states.json").read_text())["states"]
        self.assertTrue(states)
        for s in states:   # certainty-tiers@2: ZPF tier per state, a tier per excluded phase (PI 6 Nov 2026)
            self.assertIn(s["zpf_certainty"]["certainty_tier"], ("certain", "less_certain", "uncertain"))
            for e in s.get("exclusions", []):
                self.assertIn(e["energy_scale_J_per_mol_atom"], (10, 50, 100))
            self.assertIn(s["orchid_link"], ("present", "missing"))
            if s["orchid_link"] == "missing":
                self.assertTrue(s["missing_reason"] and s["intake_ref"])
        hinge = json.loads((self.root / "evidence" / "hinge" / "exclusions_every_state.json").read_text())
        for c in hinge["cells"]:
            self.assertEqual(sorted(c["penalize"]), sorted(set(PHASES) - set(c["expected"])))
            self.assertEqual(c["confidence"], 1.0)
            self.assertIn(c["sigma"], (10.0, 50.0, 100.0))
        st = F.load_state(self.root)
        for sid in ("build_datasets", "exclusions_every_state", "classify_certainty"):
            self.assertEqual(st["steps"][sid]["status"], "done")
        self.assertTrue(F.validate_assessment(self.a)["ok"], F.validate_assessment(self.a))
        with self.assertRaises(SageError):
            F.gather_evidence(self.a)  # a current bundle is never overwritten

    def test_gpu_step_writes_job_spec(self):
        self._decide_preflight()
        F.modify_protocol(self.a, {"type": "skip_step", "step": "gen_sqs"}, who="PI (test)", why="cells supplied from an earlier campaign")
        out = R.run_step(self.a, "staged_relax", str(self.root), confirm=True, allow_long=True)
        self.assertFalse(out["executed"])
        self.assertIn("docker run", out["job_spec"]["command"])
        self.assertTrue(Path(out["job_file"]).is_file())
        self.assertIsNone(out["submission"])
        self.assertEqual(F.load_state(self.root)["steps"]["staged_relax"]["status"], "job_spec_written")
        with self.assertRaises(SageError):
            R.run_step(self.a, "staged_relax", str(self.root), confirm=True, backend="gpu1")  # not configured

    def test_documented_modification_and_stale(self):
        self._decide_preflight()
        F.gather_evidence(self.a)
        old_cards = F.load_state(self.root)["steps"]["classify_certainty"]["run_cards"]
        m = F.modify_protocol(self.a, {"type": "parameter_override", "parameter": "hull_tolerance_tau", "value": 50}, who="PI (test)",
                              why="test a tighter state tolerance", evidence=["evidence/states.json"])
        self.assertEqual((m["previous_version"], m["version"]), ("0.1.0", "0.2.0"))
        self.assertFalse(m["override"]["conforms"])
        self.assertEqual(m["override"]["parameter"], "param:hull_tolerance_tau")
        self.assertIn("exclusions_every_state", m["stale"])
        self.assertIn("classify_certainty", m["stale"])
        st = F.load_state(self.root)
        self.assertEqual(st["steps"]["classify_certainty"]["superseded_run_cards"], old_cards)
        for c in old_cards:
            self.assertTrue((self.root / c).is_file())  # superseded, kept
        self.assertTrue((self.root / "protocol" / f"{self.a}@0.1.0.json").is_file())
        g2 = F.gather_evidence(self.a)  # re-run of the stale steps writes a new bundle directory
        self.assertIn("evidence_v2", g2["bundle"])
        # refusals
        for change, who, why in (({"type": "parameter_override", "parameter": "hull_tolerance_tau", "value": 1}, "PI", ""),
                                 ({"type": "parameter_override", "parameter": "sqs_seeds", "value": 3}, "coordinator", "faster"),
                                 ({"type": "parameter_override", "parameter": "no_such", "value": 3}, "PI", "x"),
                                 ({"type": "skip_step", "step": "no_such_step"}, "PI", "x"),
                                 ({"type": "nonsense"}, "PI", "x")):
            with self.subTest(change=change, who=who):
                with self.assertRaises(SageError):
                    F.modify_protocol(self.a, change, who=who, why=why)
        self.assertEqual(F.current_spec(self.root)[1]["version"], "0.2.0")
        tool = F.modify_protocol(self.a, {"type": "tool", "step": "verify_build", "command": "python3 -c \"print('ok')\""}, who="coordinator",
                                 why="no espei on the test host")
        self.assertEqual(tool["version"], "0.3.0")
        seq = {x["id"]: x for x in F.sequence(self.root)}
        self.assertTrue(seq["verify_build"]["command_overridden"])
        run = R.run_step(self.a, "verify_build", str(self.root), confirm=True)
        self.assertEqual(run["returncode"], 0)
        h = F.get_history(self.a)
        self.assertEqual([v["version"] for v in h["versions"]], ["0.1.0", "0.2.0", "0.3.0"])
        self.assertEqual(len(h["overrides"]), 2)
        self.assertTrue(any(e["kind"] == "marked_stale" for e in h["events"]))

    def test_general_minor_version_and_migration(self):
        # orchid-calphad-fit@2.1.0 is a released general version (crni-paper-fit-step4c-b@1.0.1), so the next minor of 2.0.0
        # is refused and the proposal starts from 2.1.0; the fresh assessment still instantiates the default 2.0.0
        self._decide_preflight()
        F.gather_evidence(self.a)
        with self.assertRaises(SageError):  # 2.1.0 exists: never edited in place
            F.propose_general_change({"type": "parameter_default", "parameter": "hull_tolerance_tau", "value": 50}, who="PI (test)", why="x")
        base = "orchid-calphad-fit@2.1.0"
        with self.assertRaises(SageError):
            F.propose_general_change({"type": "parameter_default", "parameter": "hull_tolerance_tau", "value": 50}, who="PI", why="x", bump_kind="patch", base=base)
        p = F.propose_general_change({"type": "parameter_default", "parameter": "hull_tolerance_tau", "value": 50}, who="PI (test)", why="tau 50 by default", base=base)
        self.assertEqual(p["proposed"], "orchid-calphad-fit@2.2.0")
        self.assertTrue(Path(p["path"]).is_file())
        self.assertFalse((Path(R.repo_root()) / "protocols/general/orchid-calphad-fit@2.2.0.yaml").exists())
        with self.assertRaises(SageError):
            F.propose_general_change({"type": "parameter_default", "parameter": "hull_tolerance_tau", "value": 60}, who="PI", why="again", base=base)
        maj = F.propose_general_change({"type": "parameter_default", "parameter": "sqs_seeds", "value": 3}, who="PI", why="frozen -> major", base=base)
        self.assertEqual(maj["proposed"], "orchid-calphad-fit@3.0.0")
        self.assertEqual(F.current_spec(self.root)[1]["instantiates"][0]["protocol"], "orchid-calphad-fit@2.0.0")  # not moved
        mg = F.migrate(self.a, "2.2.0", who="PI (test)", why="adopt tau 50")
        self.assertEqual(mg["changed_parameters"], ["hull_tolerance_tau"])
        self.assertIn("exclusions_every_state", mg["stale"])
        spec = F.current_spec(self.root)[1]
        self.assertEqual(spec["instantiates"][0]["protocol"], "orchid-calphad-fit@2.2.0")
        self.assertEqual(spec["version"], "0.2.0")
        self.assertIn("migrate from orchid-calphad-fit@2.0.0", spec["decisions"][-1]["decision"])
        self.assertTrue(F.validate_assessment(self.a)["ok"])

    def test_package_refuses_without_pick(self):
        out = F.package(self.a)
        self.assertFalse(out["packaged"])
        self.assertTrue(out["missing"])


if __name__ == "__main__":
    unittest.main()
