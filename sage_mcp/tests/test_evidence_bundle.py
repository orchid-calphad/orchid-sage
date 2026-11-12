"""protocols/tools/build_evidence_bundle.py: vertex compositions and exclusion tiers (fixes of 7 Nov 2026, bundle 1.1.0 of
crni-paper-fit-step4c-b). Standard library only; no files are written."""

import importlib.util
import unittest

from sage_mcp.tests.helpers import REPO

_spec = importlib.util.spec_from_file_location("build_evidence_bundle", REPO / "protocols/tools/build_evidence_bundle.py")
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)


def zpf(T, values):
    return {"components": ["CR", "NI"], "phases": sorted({v[0] for r in values for v in r}), "output": "ZPF",
            "conditions": {"T": T, "P": [101325.0]}, "values": values, "reference": "test"}


class VertexComposition(unittest.TestCase):
    def test_cr_given_vertex_converted_to_ni(self):
        # Svechnikov row 11: bcc at x(CR) 0.662 is x(NI) 0.338, not x(NI) 0.662 (the 1.0.0 bug)
        s = B.states_from_zpf(zpf([1669], [[["BCC_A2", ["CR"], [0.662]], ["LIQUID", ["CR"], [None]]]]), "f.json", "liq_c", "NI")[0]
        self.assertEqual(s["vertices"], [["BCC_A2", 0.338], ["LIQUID", None]])
        self.assertEqual(s["x"], 0.338)
        self.assertEqual(s["kind"], "partial_tie_line")

    def test_ni_given_vertex_unchanged(self):
        s = B.states_from_zpf(zpf([1500], [[["BCC_A2", ["NI"], [0.058]], ["FCC_A1", ["NI"], [0.4]]]]), "f.json", "solid_c", "NI")[0]
        self.assertEqual(s["vertices"], [["BCC_A2", 0.058], ["FCC_A1", 0.4]])

    def test_mixed_components_in_one_record(self):
        s = B.states_from_zpf(zpf([1500], [[["BCC_A2", ["CR"], [0.9]], ["FCC_A1", ["NI"], [0.6]]]]), "f.json", "solid_c", "NI")[0]
        self.assertEqual(s["vertices"], [["BCC_A2", 0.1], ["FCC_A1", 0.6]])

    def test_unknown_vertex_stays_unknown(self):
        s = B.states_from_zpf(zpf([1669], [[["BCC_A2", ["CR"], [0.662]], ["LIQUID", ["NI"], [None]]]]), "f.json", "liq_c", "NI")[0]
        self.assertIsNone(dict(s["vertices"])["LIQUID"])
        st = [dict(s, source="zpf", excluded=[])]
        B.classify(st)
        # the unknown LIQUID vertex is not placed anywhere: LIQUID has no field point, so an exclusion of LIQUID elsewhere is
        # graded as "not observed", not as adjacent to this record's other composition (the 1.0.0 bug)
        far = {"source": "hinge", "source_file": "hinge/h.json", "row": 0, "kind": "single_phase", "T_K": 1669.0, "x": 0.338,
               "element": "NI", "expected": ["BCC_A2"], "excluded": ["LIQUID"], "vertices": [], "sigma_T_K": 16.0, "sigma_x": 0.011,
               "reference": "other"}
        st = [dict(s, source="zpf"), far]
        B.classify(st)
        self.assertIsNone(st[1]["exclusions"][0]["distance_sigma"])


class ExclusionTiers(unittest.TestCase):
    def state(self, tiers):
        return {"source": "hinge", "source_file": "hinge/h.json", "row": 3, "kind": "single_phase", "T_K": 1721.0, "x": 0.2045,
                "element": "NI", "expected": ["BCC_A2"], "excluded": ["CRNI2", "FCC_A1"], "vertices": [], "sigma_T_K": 16.0,
                "sigma_x": 0.011, "reference": "bechtoldt1961redetermination",
                "_fit_tiers": tiers, "_fit_tiers_src": "hinge/h.json cells[3].orchid.tiers"}

    def test_tiers_copied_from_hinge_file(self):
        tiers = {"FCC_A1": {"tier": "certain", "distance_sigma": 15.985, "basis": "nearest presence of FCC_A1 at 16.0 sigma"},
                 "CRNI2": {"tier": "uncertain", "distance_sigma": 60.34, "basis": "held at the weakest tier (PI caveat)"}}
        st = [self.state(tiers)]
        B.classify(st)
        E = {e["phase"]: e for e in st[0]["exclusions"]}
        # alone in the bundle the classifier would say "single source" (50) for both; the fit's tiers are kept as read
        self.assertEqual(E["FCC_A1"]["certainty_tier"], "certain")
        self.assertEqual(E["FCC_A1"]["energy_scale_J_per_mol_atom"], 10.0)
        self.assertEqual(E["CRNI2"]["certainty_tier"], "uncertain")
        self.assertEqual(E["CRNI2"]["energy_scale_J_per_mol_atom"], 100.0)
        self.assertEqual(E["FCC_A1"]["distance_sigma"], 15.985)
        self.assertTrue(E["CRNI2"]["certainty_basis"].startswith("tier used by the fit (hinge/h.json cells[3].orchid.tiers): held"))
        self.assertNotIn("_fit_tiers", st[0]); self.assertNotIn("_fit_tiers_src", st[0])
        self.assertEqual(st[0]["certainty_rule"], B.RULE3)
        # only schema fields (common.schema.json exclusion_entry)
        allowed = {"phase", "certainty_tier", "energy_scale_J_per_mol_atom", "certainty_basis", "distance_sigma", "n_independent_sources"}
        self.assertTrue(all(set(e) <= allowed for e in st[0]["exclusions"]))

    def test_classifier_only_without_recorded_tier(self):
        st = [self.state({"FCC_A1": {"tier": "certain", "distance_sigma": 15.985, "basis": "b"}})]
        B.classify(st)
        E = {e["phase"]: e for e in st[0]["exclusions"]}
        self.assertTrue(E["FCC_A1"]["certainty_basis"].startswith("tier used by the fit"))
        self.assertFalse(E["CRNI2"]["certainty_basis"].startswith("tier used by the fit"))
        # no automatic single-source rule (PI 7 Nov 2026): alone in the bundle, with CRNI2 never observed, the absence is
        # certain (10), not "single source" (50) as under the 3-sigma-neighbour reading
        self.assertEqual(E["CRNI2"]["certainty_tier"], "certain")
        self.assertNotIn("n_independent_sources", E["CRNI2"])


class SingleSource(unittest.TestCase):
    """fit_protocol item 8, PI 7 Nov 2026 ("Yes" to "only Pugliese, as the fit used"): a dataset is single source only when
    the plan designates it, with its reason; no automatic 3-sigma-neighbour rule."""

    def state(self, ref, T=1500.0, x=0.2):
        return {"source": "hinge", "source_file": "hinge/h.json", "row": 0, "kind": "single_phase", "T_K": T, "x": x,
                "element": "NI", "expected": ["BCC_A2"], "excluded": ["FCC_A1"], "vertices": [], "sigma_T_K": 16.0,
                "sigma_x": 0.011, "reference": ref}

    def fcc_far(self):
        # FCC_A1 observed far away (x 0.9): every test state is > 3 sigma from the FCC_A1 field
        return {"source": "zpf", "source_file": "solid/f.json", "row": 0, "kind": "single_phase", "T_K": 1500.0, "x": 0.9,
                "element": "NI", "expected": ["FCC_A1"], "vertices": [["FCC_A1", 0.9]], "sigma_T_K": 16.0, "sigma_x": 0.011,
                "reference": "jette1934"}

    PUG = [{"match": "pugliese", "reason": "Table III limits, the only report of these states"}]

    def test_lone_state_not_single_source_without_designation(self):
        st = [self.state("bechtoldt1961redetermination"), self.fcc_far()]
        B.classify(st)
        e = st[0]["exclusions"][0]
        self.assertEqual((e["certainty_tier"], e["energy_scale_J_per_mol_atom"]), ("certain", 10.0))
        self.assertNotIn("single source", e["certainty_basis"])

    def test_designated_dataset_is_single_source(self):
        st = [self.state("pugliese1970activities"), self.fcc_far()]
        B.classify(st, self.PUG)
        e = st[0]["exclusions"][0]
        self.assertEqual((e["certainty_tier"], e["energy_scale_J_per_mol_atom"]), ("less_certain", 50.0))
        self.assertIn("single source (designated in the plan: Table III limits", e["certainty_basis"])

    def test_designation_does_not_spread_to_other_datasets(self):
        st = [self.state("pugliese1970activities"), self.state("bechtoldt1961redetermination", T=1700.0), self.fcc_far()]
        B.classify(st, self.PUG)
        self.assertEqual(st[0]["exclusions"][0]["certainty_tier"], "less_certain")
        self.assertEqual(st[1]["exclusions"][0]["certainty_tier"], "certain")

    def test_distance_tiers_win_over_designation(self):
        # within 3 sigma (50) and adjacent (100) are unchanged by the designation
        near = self.fcc_far(); near["x"] = 0.2 + 2 * 0.011; near["vertices"] = [["FCC_A1", near["x"]]]
        st = [self.state("pugliese1970activities"), near]
        B.classify(st, self.PUG)
        self.assertEqual(st[0]["exclusions"][0]["certainty_tier"], "less_certain")
        self.assertIn("within 3 sigma", st[0]["exclusions"][0]["certainty_basis"])
        adj = self.fcc_far(); adj["x"] = 0.205; adj["vertices"] = [["FCC_A1", 0.205]]
        st = [self.state("pugliese1970activities"), adj]
        B.classify(st, self.PUG)
        self.assertEqual(st[0]["exclusions"][0]["certainty_tier"], "uncertain")

    def test_fit_tiers_still_copied(self):
        s = self.state("pugliese1970activities")
        s["_fit_tiers"] = {"FCC_A1": {"tier": "certain", "distance_sigma": 9.0, "basis": "b"}}
        s["_fit_tiers_src"] = "hinge/h.json cells[0].orchid.tiers"
        st = [s, self.fcc_far()]
        B.classify(st, self.PUG)
        self.assertEqual(st[0]["exclusions"][0]["certainty_tier"], "certain")
        self.assertTrue(st[0]["exclusions"][0]["certainty_basis"].startswith("tier used by the fit"))

    def test_designation_needs_a_reason(self):
        with self.assertRaises(ValueError):
            B.classify([self.state("pugliese1970activities"), self.fcc_far()], [{"match": "pugliese"}])

    def test_crni4cb_plan_designates_only_pugliese(self):
        P = B.plan("crni4cb")
        self.assertEqual([d["match"] for d in P["single_sources"]], ["pugliese"])
        self.assertTrue(all(d["reason"] for d in P["single_sources"]))


if __name__ == "__main__":
    unittest.main()
