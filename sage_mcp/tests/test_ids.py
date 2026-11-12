"""compute_ids tool and the orchid_link: provisional schema rule (PI 6 Nov 2026)."""
import json
import sys
import unittest

from sage_mcp import server
from sage_mcp.tests.helpers import REPO, SageTestCase

sys.path.insert(0, str(REPO / "protocols" / "tools"))
import orchidproto as op  # noqa: E402

ORCID = "0000-0002-1825-0097"
UUID = "3f2504e0-4f89-41d3-9a0c-0305e82c3301"
RELEASED = ("ORC-GTMRAZEGO6", "doi:10.1016/0001-6160(88)90152-6/p5/tab-1/r09#equilibrium_property")  # v2026.10 AL-NI record


def link_errors(doc):
    errs = []
    v = op.SchemaValidator()
    v._v(doc, {"$ref": "common.schema.json#/$defs/orchid_link"}, "common.schema.json", "$", errs)
    return errs


class ComputeIds(SageTestCase):
    def test_released_record(self):
        r = server.compute_ids(pid=RELEASED[1], check_id=RELEASED[0])
        self.assertEqual(r["record"]["id"], RELEASED[0])
        self.assertTrue(r["check"]["ok"])
        self.assertFalse(r["record"]["provisional"])

    def test_namespace_and_local_record(self):
        r = server.compute_ids(orcid=ORCID, dataset_uuid=UUID)
        self.assertEqual(r["namespace"], f"local:{ORCID}/{UUID}")
        n = server.compute_ids(orcid=ORCID, new_namespace=True)
        self.assertTrue(n["namespace"].startswith(f"local:{ORCID}/"))
        p = server.compute_ids(locator={"kind": "supplement", "label": "dsc.csv", "row": 2}, orcid=ORCID, dataset_uuid=UUID)
        self.assertEqual(p["record"]["pid"], f"local:{ORCID}/{UUID}/supp-dsc.csv/r02#equilibrium_property")
        self.assertTrue(p["record"]["provisional"])
        self.assertIn("error", server.compute_ids(orcid="0000-0002-1825-0098", dataset_uuid=UUID))
        self.assertIn("error", server.compute_ids(pid="http://example.org/x"))

    def test_state_without_registry(self):
        st = {"system": "CU-ZR", "observation_type": "equilibrium_property", "property": "HM_MIX", "phases": [{"label": "liquid"}],
              "temperature_K": 1500, "pressure_Pa": 101325, "overall_composition": {"ZR": 0.4}}
        r = server.compute_ids(pid=f"local:{ORCID}/{UUID}/supp-a.csv/r01#equilibrium_property", state=st,
                               orchid_data_dir=str(self.tmp / "no-data"))
        self.assertTrue(r["state"]["state_id"].startswith("S-") and r["state"]["state_class_id"].startswith("C-"))
        self.assertIsNone(r["phase_registry"])
        self.assertTrue(any("no phase registry" in n for n in r["state"]["notes"]))
        self.assertEqual(r["state"]["rule_version"], "coord-rule/3")
        self.assertEqual(r["state"]["class_descriptor"]["reference_state"]["ZR"]["phase"], "HCP_A3")
        r2 = server.compute_ids(state=st, orchid_data_dir=str(self.tmp / "no-data"), rule="coord-rule/2")
        self.assertNotEqual(r2["state"]["state_id"], r["state"]["state_id"])
        self.assertIn("error", server.compute_ids(state=st, rule="coord-rule/9"))

    def test_tool_listed(self):
        names = {t["name"] for t in server.tool_descriptions()}
        self.assertIn("compute_ids", names)


class ProvisionalLinkSchema(unittest.TestCase):
    def test_schema(self):
        pid = f"local:{ORCID}/{UUID}/supp-a.csv/r01#equilibrium_property"
        oid = server.compute_ids(pid=pid)["record"]["id"]
        self.assertEqual(link_errors({"orchid_link": "provisional", "orchid_links": [{"id": oid, "pid": pid}]}), [])
        self.assertTrue(link_errors({"orchid_link": "provisional"}))
        self.assertTrue(link_errors({"orchid_link": "provisional", "orchid_links": [{"id": oid}]}))
        self.assertTrue(link_errors({"orchid_link": "provisional", "orchid_links": [{"id": oid, "pid": "sha256:0123456789abcdef/p1/tab-1/r01"}]}))
        self.assertEqual(link_errors({"orchid_link": "present"}), [])

    def test_recompute_check(self):
        import orchid_ids
        pid = f"local:{ORCID}/{UUID}/supp-a.csv/r01#equilibrium_property"
        oid = orchid_ids.compact(pid)
        self.assertEqual(orchid_ids.check_provisional_link({"id": oid, "pid": pid}), [])
        self.assertTrue(orchid_ids.check_provisional_link({"id": RELEASED[0], "pid": pid}))
        self.assertTrue(orchid_ids.check_provisional_link({"id": RELEASED[0], "pid": RELEASED[1].replace("doi:", "isbn:")}))


if __name__ == "__main__":
    unittest.main()
