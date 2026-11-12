import unittest

from sage_mcp import reproduce as R
from sage_mcp.tests.helpers import CRNI, CUZR, HAS_CUZR, SageTestCase


class ReadTools(SageTestCase):
    def test_list_protocols(self):
        refs = {p["ref"]: p for p in R.list_protocols()["protocols"]}
        self.assertIn("orchid-calphad-fit@2.0.0", refs)
        self.assertIn(CRNI, refs)
        if HAS_CUZR:
            self.assertIn(CUZR, refs)
        self.assertEqual(refs[CRNI]["reproduce_plan"][:3], ["step2", "step3b", "step4"])
        self.assertIn("evaluate_states", refs[CRNI]["reproduce_plan"])   # deterministic items declared by the protocol (6 Nov)
        self.assertEqual(refs["orchid-calphad-fit@2.0.0"]["type"], "general_protocol")

    def test_get_protocol_summary_and_full(self):
        s = R.get_protocol(CRNI)["summary"]
        self.assertEqual(s["system"], "CR-NI")
        self.assertTrue(any(r["run_id"] == "crni-step4_solid" for r in s["run_sequence"]))
        full = R.get_protocol("orchid-calphad-fit@2.0.0", fields="full")["document"]
        self.assertEqual(full["type"], "general_protocol")

    def test_steps_and_step(self):
        st = R.get_steps(CRNI)
        ids = {s["id"] for s in st["steps"]}
        self.assertTrue({"fit_liquidus", "pick_liquidus", "evaluate_states", "tdb_header"} <= ids)
        items = [i["id"] for i in st["reproduce_items"]]
        self.assertEqual(items[:2], ["stage", "environment_check"])
        self.assertIn("step4", items)
        sec = R.get_steps(CRNI, section="s1_evidence")
        self.assertTrue(all(s["section"] == "s1_evidence" for s in sec["steps"]))
        if HAS_CUZR:
            one = R.get_step(CUZR, "cuzr_fit_h2")
            self.assertEqual(one["kind"], "numerical")
            self.assertIn("run_step.sh stepH2_hinge_thermo 8", one["command"])
            self.assertTrue(one["tolerances"])
            self.assertEqual(one["origin"], CUZR)
        item = R.get_step(CRNI, "step4")["reproduce_item"]
        self.assertIn("scripts/fit.py steps/configs/step4_solid.json", item["command"])
        jud = R.get_step(CRNI, "pick_liquidus")
        self.assertEqual(jud["kind"], "judgement")
        picks = jud["recorded_decision"]["picks_in_run_sequence"]
        self.assertTrue(any(p.get("pick") == "s7_perturbed" for p in picks))

    def test_run_cards_decisions_evidence_dashboard_questions(self):
        rc = R.get_run_cards(CRNI)
        self.assertTrue(any(r.get("run_card", {}).get("exists") for r in rc["runs"]))
        dec = R.get_decisions(CRNI)
        self.assertTrue(dec["decisions"] and dec["overrides"])
        man = R.get_evidence_manifest("crni-paper-fit-step4-s1", limit=5)
        self.assertEqual(len(man["files"]), 5)
        self.assertIn("espei_dataset", man["kinds"])
        self.assertEqual(man["version"], "2.0.0")
        lk = R.get_evidence_links("crni-paper-fit-step4-s1", link="missing", limit=3)
        self.assertEqual(lk["bundle_version"], "2.0.0")
        self.assertTrue(all(s["missing_reason"] and s["intake_ref"] for s in lk["states"]))
        self.assertEqual(lk["link_coverage"]["orc_ids_unresolved"], 29)
        if HAS_CUZR:
            cz = R.get_evidence_links("cuzr-oneshot-h2-s7", link="present", limit=2)
            self.assertTrue(cz["states"][0]["links"][0]["id"].startswith("ORC-"))
        dash = R.get_dashboard_data("crni-paper-fit-step4-s1")
        self.assertIn("trajectory", dash["sections"])
        tr = R.get_dashboard_data("crni-paper-fit-step4-s1", section="trajectory", max_items=2)
        self.assertLessEqual(len(tr["trajectory"]["runs"]), 2)
        oq = R.get_open_questions(["Q35", "Q36"])
        self.assertEqual([q["id"] for q in oq["questions"]], ["Q35", "Q36"])

    def test_validator_passthrough(self):
        v = R.validate()
        self.assertEqual(v["validator"], "protocols/tools/validate.py --quiet")
        self.assertTrue(v["summary"].startswith("documents:"))
        self.assertEqual(v["ok"], not v["errors"])
        one = R.validate(CRNI)
        self.assertTrue(all("crni-paper-fit-step4-s1" in e for e in one["errors"]))

    def test_verify_inputs(self):
        v = R.verify_inputs(CRNI)
        self.assertGreater(v["counts"]["ok"], 10)
        self.assertEqual(len(v["bundle_manifests"]), 2)
        self.assertIn("rerun_ready", v)
        # restricted exports are hashed or listed, never returned as content
        for row in v["restricted_present_ok"] + v["restricted_missing"]:
            self.assertEqual(set(row), {"at", "path", "storage_class", "role"})


class Plans(SageTestCase):
    def test_plan_both_specific_protocols(self):
        for ref, fits in ((CRNI, ["step2", "step3b", "step4", "evaluate_states", "tdb_header", "phase_sequence", "pure_elements", "polish_step3b", "pick_rule_step3b", "laplace_weights"]),
                          ("crni-paper-fit-step4c-b@0.2.0-draft", ["step4c_b", "evaluate_states", "phase_sequence", "pure_elements", "laplace_weights"]),
                          *([(CUZR, ["step2_s1", "h1_s1", "h2_s7", "polish_chain_h1_h2", "evaluate_states", "tdb_header", "phase_sequence", "pure_elements"])] if HAS_CUZR else [])):
            pl = R.plan_reproduction(ref, run_root=str(self.tmp / "rr"))
            self.assertTrue(pl["nothing_was_run"])
            self.assertEqual(pl["order"][:2], ["stage", "environment_check"])
            self.assertEqual(pl["order"][-len(fits):], fits)
            for it in pl["items"]:
                self.assertIn(it["kind"], ("deterministic", "numerical"))
                self.assertIn("class", it["compute"])
                self.assertNotIn("{PY}", it["command"])
            numerical = [i for i in pl["items"] if i["kind"] == "numerical"]
            self.assertTrue(all(i["tolerances"] for i in numerical))
            self.assertFalse((self.tmp / "rr").exists())

    def test_pfp_pin_from_protocol(self):
        # 1.0.1 declares the source-only PhaseForge+ pin (code entry phaseforgeplus, file id source_pin); 1.0.0 keeps the 6 Nov list
        new = R.pfp_pin(R.find_protocol("crni-paper-fit-step4c-b@1.0.1")[1])
        old = R.pfp_pin(R.find_protocol("crni-paper-fit-step4c-b@1.0.0")[1])
        # pin lists are named after the DGX Spark node whose copy they list (the same node for both)
        self.assertTrue(new.name.endswith("_phaseforgeplus_src_files.sha256") and old.name.endswith("_phaseforgeplus_files.sha256"))
        self.assertEqual(new.name.split("_")[0], old.name.split("_")[0])
        self.assertTrue(new.is_file() and old.is_file())
        lines = [ln.split("  ", 1)[1] for ln in new.read_text().splitlines() if "  " in ln]
        self.assertEqual(len(lines), 10)
        self.assertFalse(any("cache" in ln or "/.git" in ln for ln in lines))

    def test_plan_refuses_general(self):
        with self.assertRaises(Exception):
            R.plan_reproduction("orchid-calphad-fit@2.0.0")


if __name__ == "__main__":
    unittest.main()
