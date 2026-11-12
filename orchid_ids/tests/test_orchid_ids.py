"""orchid_ids: test vectors from released records (ORC) and from the v2027.01 candidate registry (S-/C-).

  python3 -m unittest discover -s orchid_ids/tests -t .
Optional full check against a data checkout: ORCHID_IDS_FULL_DATA=<path to an orchid-data checkout> (all 73,542 records).
"""
import gzip
import json
import os
import unittest
from pathlib import Path

import orchid_ids as I
from orchid_ids import locator as L
from orchid_ids import state as S

V = json.loads((Path(__file__).with_name("vectors.json")).read_text(encoding="utf-8"))
ORCID = "0000-0002-1825-0097"  # ORCID's documented example iD (Josiah Carberry)
UUID = "3f2504e0-4f89-41d3-9a0c-0305e82c3301"


def registry():
    return S.PhaseRegistry(V["phase_registry_subset"], V["phase_systems_subset"])


class OrcIds(unittest.TestCase):
    def test_released_vectors_recompute_from_pid(self):
        self.assertEqual(len(V["orc_vectors"]), 20)
        for v in V["orc_vectors"]:
            with self.subTest(v["id"]):
                self.assertEqual(I.compute_orc_id(v["pid"])["id"], v["id"].split(".")[0])
                self.assertTrue(I.check_link(v["id"], v["pid"])["ok"])
                self.assertTrue(I.validate_id(v["id"])["ok"])

    def test_released_vectors_from_parts(self):
        """A table row rebuilt from locator.asset + row + the pid's datum token gives the released id."""
        n = 0
        for v in V["orc_vectors"]:
            loc = v["locator"]
            if loc["artifact"] != "table" or "/r-unplaced" in v["pid"]:
                continue
            datum = v["pid"].rsplit("#", 1)[1]
            pid = L.datum_id(L.row_id(loc["asset"], loc["row"]), datum)
            if pid == v["pid"]:
                n += 1
                self.assertEqual(L.compact(pid), v["id"].split(".")[0])
        self.assertGreaterEqual(n, 10)

    def test_build_pid_doi_source(self):
        v = next(x for x in V["orc_vectors"] if x["pid"].startswith("doi:") and x["locator"]["artifact"] == "table"
                 and "/r-unplaced" not in x["pid"])
        p = L.parse_pid(v["pid"])
        doi = p["source"][4:]
        page = int(v["locator"]["page"])
        label = p["asset"].rsplit("/tab-", 1)[1]
        row = int(p["element"][1:])
        built = I.build_pid(doi="https://doi.org/" + doi.upper(), page=page, label=label, row=row,
                            datum_type=v["pid"].rsplit("#", 1)[1])
        self.assertEqual(built, v["pid"])

    def test_suffix_rule(self):
        for v in V["orc_suffix_vectors"]:
            self.assertEqual(I.compute_orc_id(v["pid"], observation_key=v["internal_observation_id"])["id"], v["id"])
            self.assertTrue(I.check_link(v["id"], v["pid"], v["internal_observation_id"])["ok"])
        self.assertFalse(I.check_link(V["orc_suffix_vectors"][0]["id"], V["orc_suffix_vectors"][0]["pid"], "other-key")["ok"])

    def test_corrected_pid_keeps_issued_id(self):
        for v in V["orc_corrected_pid_vectors"]:
            self.assertEqual(L.compact(v["pid_at_issue"]), v["id"].split(".")[0])
            self.assertNotEqual(L.compact(v["pid"]), v["id"].split(".")[0])

    @unittest.skipUnless(os.environ.get("ORCHID_IDS_RELEASE_DATA"), "set ORCHID_IDS_RELEASE_DATA to a v2026.10 checkout")
    def test_full_release(self):
        d = Path(os.environ["ORCHID_IDS_RELEASE_DATA"]).expanduser()
        n = ok = corrected = 0
        with gzip.open(d / "literature/orchid-literature.jsonl.gz", "rt") as fh:
            for line in fh:
                r = json.loads(line)
                n += 1
                L.parse_pid(r["pid"])
                if I.check_link(r["id"], r["pid"])["ok"]:
                    ok += 1
                elif any(c.get("field") == "pid" and L.compact(c["before"]) == r["id"].split(".")[0]
                         for c in r.get("corrections") or []):
                    corrected += 1
        self.assertEqual(ok + corrected, n)

    def test_bad_ids_and_locators(self):
        for bad in ("ORC-abc", "ORC-0000000000", "S-ABCDEF0123", "C-12345", "ORC-AAAAAAAAAA.12345"):
            self.assertFalse(I.validate_id(bad)["ok"], bad)
        self.assertEqual(I.validate_id("ORC-CAAAAAAAAAA")["kind"], "contributed_record")
        for bad in ("http://x/p1/tab-1/r01", "doi:10.1/x", "doi:10.1/x/p1/tab-1/row1#a", "doi:10.1/x/p1/tab-1/r01#A B"):
            with self.assertRaises(ValueError):
                L.parse_pid(bad)
        self.assertFalse(I.check_link("ORC-AAAAAAAAAA", V["orc_vectors"][0]["pid"])["ok"])


class Provisional(unittest.TestCase):
    def test_namespace(self):
        ns = I.make_provisional_namespace("https://orcid.org/" + ORCID, UUID.upper())
        self.assertEqual(ns, f"local:{ORCID}/{UUID}")
        with self.assertRaises(ValueError):
            I.make_provisional_namespace("0000-0002-1825-0098", UUID)  # checksum
        with self.assertRaises(ValueError):
            I.make_provisional_namespace(ORCID, "not-a-uuid")
        self.assertTrue(I.orcid_ok("0000-0002-1694-233X"))

    def test_local_record_id_and_link(self):
        r = I.compute_orc_id(orcid=ORCID, dataset_uuid=UUID, kind="supplement", label="DSC runs.csv", row=3)
        self.assertEqual(r["pid"], f"local:{ORCID}/{UUID}/supp-dsc-runs.csv/r03#equilibrium_property")
        self.assertTrue(r["provisional"])
        self.assertEqual(r["id"], L.compact(r["pid"]))
        self.assertEqual(I.check_provisional_link({"id": r["id"], "pid": r["pid"]}), [])
        self.assertTrue(I.check_provisional_link({"id": "ORC-AAAAAAAAAA", "pid": r["pid"]}))
        with self.assertRaises(ValueError):
            L.parse_pid(f"local:{ORCID}/{UUID.upper()}/supp-a/r01#x")
        with self.assertRaises(ValueError):
            L.parse_pid(f"local:0000-0002-1825-0098/{UUID}/supp-a/r01#x")
        # a figure point in a local dataset
        f = I.compute_orc_id(orcid=ORCID, dataset_uuid=UUID, kind="figure", page=1, label="3", series="run a", point=7)
        self.assertEqual(f["pid"], f"local:{ORCID}/{UUID}/p1/fig-3/s-run-a/pt-007#equilibrium_property")

    def test_dataset_doi_is_not_provisional(self):
        r = I.compute_orc_id(doi="10.5281/zenodo.1234567", kind="supplement", label="data.csv", row=1)
        self.assertFalse(r["provisional"])
        self.assertEqual(I.check_provisional_link({"id": r["id"], "pid": r["pid"]}), [])

    def test_alias(self):
        p = I.compute_orc_id(orcid=ORCID, dataset_uuid=UUID, kind="supplement", label="data.csv", row=1)
        q = I.compute_orc_id(doi="10.5281/zenodo.1234567", kind="supplement", label="data.csv", row=1)
        a = I.build_alias_record(p["id"], p["pid"], q["id"], q["pid"], release="2027.01")
        self.assertEqual((a["id"], a["status"], a["superseded_by"], a["first_release"]), (p["id"], "superseded", q["id"], "2027.01"))
        self.assertEqual(a["lineage_note"]["published_pid"], q["pid"])
        with self.assertRaises(ValueError):
            I.build_alias_record(q["id"], q["pid"], p["id"], p["pid"])  # wrong direction
        with self.assertRaises(ValueError):
            I.build_alias_record(p["id"], p["pid"], "ORC-AAAAAAAAAA", q["pid"])  # does not recompute
        m = I.merged_fields({"merged_ids": ["ORC-X"]}, p["id"], p["pid"])
        self.assertEqual(m["merged_ids"], ["ORC-X", p["id"]])


class StateIds(unittest.TestCase):
    def test_registry_vectors(self):
        reg = registry()
        rules = set()
        for v in V["state_vectors"]:
            with self.subTest(v["record"]["id"]):
                o = I.compute_state_id(v["record"], reg, rule="coord-rule/2")
                self.assertEqual(o["state_class_id"], v["state_class_id"])
                self.assertEqual(o["state_id"], v["state_id"])
                rules.add(o["assignment_rule"])
        self.assertEqual(len(rules), 7)

    def test_grouped_invariants_are_alternatives(self):
        reg = registry()
        for v in V["state_grouped_invariant_vectors"]:
            o = I.compute_state_id(v["record"], reg, rule="coord-rule/2")
            self.assertEqual(o["state_class_id"], v["state_class_id"])
            self.assertEqual(o["state_id"], v["ungrouped_state_id"])
            self.assertIn(v["state_id"], o["alternative_state_ids"])
            self.assertIn("invariant_reaction_group", o["registry_dependent"])

    def test_descriptor_hash(self):
        self.assertEqual(S.descriptor_id("C-", {"system": "CU-ZR", "phases": ["phase:cu-zr:liquid"], "pressure_class": "ambient"}),
                         S.descriptor_id("C-", '{"phases":["phase:cu-zr:liquid"],"pressure_class":"ambient","system":"CU-ZR"}'))
        self.assertNotEqual(S.descriptor_id("S-", "{}"), S.descriptor_id("S-", "{}", attempt=1))

    def test_source_independent(self):
        """A resolved state's id does not depend on where it was read: provisional and published give one S- id."""
        reg = registry()
        v = next(x for x in V["state_vectors"] if not x["unresolved"] and x["rule"].startswith("solution"))
        a = I.compute_ids(pid=f"local:{ORCID}/{UUID}/supp-a.csv/r01#equilibrium_property", state={**v["record"], "id": None}, phase_registry=reg, rule="coord-rule/2")
        b = I.compute_ids(pid="doi:10.5281/zenodo.1/supp-a.csv/r01#equilibrium_property", state={**v["record"], "id": None}, phase_registry=reg, rule="coord-rule/2")
        self.assertNotEqual(a["record"]["id"], b["record"]["id"])
        self.assertEqual(a["state"]["state_id"], b["state"]["state_id"])
        self.assertEqual(a["state"]["state_id"], v["state_id"])

    def test_quantisation(self):
        self.assertEqual(S.qround(1372.4, 5.0), 1370.0)
        self.assertEqual(S.qround(0.55, 0.02), 0.56)   # 0.55 / 0.02 = 27.500000000000004 in binary floating point
        self.assertEqual(S.qround(0.05, 0.02), 0.04)   # 2.5 rounds half to even
        self.assertEqual(S.canonical_x("CU-ZR", {"CU": 0.36}), {"ZR": 0.64})
        self.assertEqual(S.canonical_x("CU-ZR", {"ZR": 0.64, "CU": 0.36}), {"ZR": 0.64})
        self.assertEqual(S.pressure_class(None), "unknown")
        self.assertEqual(S.pressure_class(101325), "ambient")

    def test_without_registry_warns(self):
        o = I.compute_state_id({"id": "ORC-AAAAAAAAAA", "system": "CU-ZR", "observation_type": "equilibrium_property",
                                "phases": [{"label": "liquid"}], "temperature_K": 1500, "pressure_Pa": 101325,
                                "overall_composition": {"ZR": 0.4}})
        self.assertTrue(any("no phase registry" in n for n in o["notes"]))
        self.assertTrue(o["state_id"].startswith("S-"))

    @unittest.skipUnless(os.environ.get("ORCHID_IDS_FULL_DATA"), "set ORCHID_IDS_FULL_DATA to a v2027.01-candidate checkout")
    def test_full_checkout(self):
        d = Path(os.environ["ORCHID_IDS_FULL_DATA"]).expanduser()
        reg = S.PhaseRegistry.load(d)
        n = cls_ok = st_ok = dep = 0
        with gzip.open(d / "literature/orchid-literature.jsonl.gz", "rt") as fh:
            for line in fh:
                r = json.loads(line)
                if not r.get("state_id"):
                    continue
                o = I.compute_state_id(r, reg, rule="coord-rule/2")
                n += 1
                cls_ok += o["state_class_id"] == r["state_class_id"]
                if o["state_id"] == r["state_id"]:
                    st_ok += 1
                elif o["registry_dependent"] or r["state_id"] in o.get("alternative_state_ids", []):
                    dep += 1
        self.assertEqual(cls_ok, n)
        self.assertEqual(st_ok + dep, n)


class Rule3(unittest.TestCase):
    """coord-rule/3, the PI decisions of 6 Nov 2026."""

    def test_regression_vectors(self):
        reg = registry()
        recs = {v["record"]["id"]: v["record"] for v in V["state_vectors"] + V["state_grouped_invariant_vectors"]}
        for v in V["state_vectors_rule3"]:
            with self.subTest(v["record_id"]):
                o = I.compute_state_id(recs[v["record_id"]], reg)
                self.assertEqual((o["state_class_id"], o["state_id"], o["assignment_rule"]), (v["state_class_id"], v["state_id"], v["rule"]))
                self.assertEqual(o["registry_dependent"], [])

    def _inv(self, T, kind="eutectic", **kw):
        return {"id": "ORC-AAAAAAAAAA", "system": "CU-ZR", "observation_type": "invariant_reaction", "property": "INVARIANT_TEMPERATURE",
                "phases": [{"label": "LIQUID"}, {"label": "CUZR"}, {"label": "CU10ZR7"}], "temperature_K": T,
                "pressure_Pa": 101325, "pressure_basis": "assumed_default_1_atm_not_printed", "transition_kind": kind, **kw}

    def test_invariant_keeps_its_temperature(self):
        a, b, c = (I.compute_state_id(self._inv(T)) for T in (1158.15, 1159.0, 1167.0))
        self.assertEqual(a["state_id"], b["state_id"])          # one 5 K cell (1160)
        self.assertNotEqual(a["state_id"], c["state_id"])       # another cell (1165): a same_reaction_as edge, not one id
        self.assertEqual(a["state_class_id"], c["state_class_id"])
        self.assertNotEqual(a["state_id"], I.compute_state_id(self._inv(1158.15, kind="peritectic"))["state_id"])
        self.assertEqual(a["state_descriptor"]["coordinates"]["T_cell_K"], 1160.0)
        self.assertEqual(a["state_descriptor"]["coordinates"]["reaction_kind"], "eutectic")
        self.assertEqual(I.compute_state_id(self._inv(1158.15, kind=None))["state_descriptor"]["coordinates"]["reaction_kind"], "unstated")

    def test_hand_built_descriptor(self):
        o = I.compute_state_id(self._inv(1158.15))
        ref = {e: {"phase": ph, "fixed_state_variables": {"P": 100000, "T": 298.15}} for e, ph in (("CU", "FCC_A1"), ("ZR", "HCP_A3"))}
        cls = {"system": "CU-ZR", "phases": ["label:cu10zr7", "label:cuzr", "label:liquid"], "pressure_class": "unknown", "reference_state": ref}
        coords = {"T_cell_K": 1160.0, "reaction_kind": "eutectic",
                  "configuration": {"assumed": {"basis": "assumed_default_not_printed", "configuration": "random", "phases": ["label:liquid"]}}}
        text = lambda d: json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        import hashlib
        self.assertEqual(o["state_class_id"], "C-" + hashlib.sha256(text(cls).encode()).hexdigest()[:10])
        self.assertEqual(o["state_id"], "S-" + hashlib.sha256(text({**cls, "coordinates": coords, "assignment_rule": "coord-rule/3:invariant-5K-kind"}).encode()).hexdigest()[:10])

    def test_decimal_rounding(self):
        self.assertEqual(S.dround(0.47, 0.02), 0.48)   # 23.5 -> 24, half to even
        self.assertEqual(S.qround(0.47, 0.02), 0.46)   # binary: 0.47 / 0.02 = 23.499999999999996 -> 23
        self.assertEqual(S.dround(0.05, 0.02), 0.04)   # 2.5 -> 2, half to even
        self.assertEqual(S.dround("1372.5", 5), 1370.0)
        self.assertEqual(S.dexact(0.12345, 4), 0.1234)
        self.assertEqual(S.canonical_x_decimal("CU-ZR", {"CU": 0.7}), {"ZR": "0.3"})

    def test_pressure_unknown_unless_printed(self):
        st = self._inv(1158.15)
        self.assertEqual(I.compute_state_id(st)["class_descriptor"]["pressure_class"], "unknown")
        st2 = {**st, "pressure_basis": "printed", "pressure_Pa": 101325}
        self.assertEqual(I.compute_state_id(st2)["class_descriptor"]["pressure_class"], "ambient")

    def test_sgte_reference(self):
        self.assertEqual(I.SER_PHASE["ZR"], "HCP_A3")
        self.assertIsNone(I.ser_reference_state("CU-XX"))
        hm = {"system": "AL-NI", "property": "HM_MIX", "reference_state": {"AL": {"phase": "LIQUID"}, "NI": {"phase": "LIQUID"}}}
        self.assertEqual(I.reference_status(hm)["status"], "convertible")
        self.assertEqual(I.reference_status({**hm, "reference_state": {"AL": {"phase": "FCC_A1"}, "NI": {"phase": "A1_FCC"}}})["status"], "ser")
        self.assertEqual(I.reference_status({**hm, "reference_state": {"AL": {"phase": "AL3NI_D011"}}})["status"], "not_convertible")
        self.assertEqual(I.reference_status({**hm, "reference_state": {"printed": "none"}})["status"], "needs_reading")
        self.assertEqual(I.reference_status({**hm, "reference_state": None})["status"], "missing")
        self.assertEqual(I.reference_status({"property": "CPM"})["status"], "not_applicable")
        # the id carries SER whatever the value's printed reference; the flag says the value must be converted
        st = {"system": "AL-NI", "observation_type": "equilibrium_property", "property": "HM_MIX", "phases": [{"label": "LIQUID"}],
              "temperature_K": 1873.15, "overall_composition": {"NI": 0.3}, "reference_state": hm["reference_state"]}
        a = I.compute_state_id(st)
        b = I.compute_state_id({**st, "reference_state": {"AL": {"phase": "FCC_A1"}, "NI": {"phase": "FCC_A1"}}})
        self.assertEqual(a["state_id"], b["state_id"])
        self.assertIn("value_reference_convertible", a["flags"])
        self.assertEqual(a["class_descriptor"]["reference_state"]["NI"]["phase"], "FCC_A1")


if __name__ == "__main__":
    unittest.main()
