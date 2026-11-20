"""Record-and-report tracing preserves the scientific evidence and its source history."""

import json
import os
from pathlib import Path

from sage_mcp import fresh as F
from sage_mcp import server
from sage_mcp import trace as T
from sage_mcp.repo import evidence_bundle_module
from sage_mcp.repo import SageError
from sage_mcp.tests.helpers import SageTestCase

ASSESS = "10.1000/assessment"
ORIG = "10.2000/measured"


def _fixture(base: Path) -> Path:
    """A phase-mapped measurement and a measurement without local source verification."""
    inv = base / "od" / "espei" / "invariants" / "AL-TI"
    exp = base / "od" / "espei" / "experimental" / "AL-TI"
    inv.mkdir(parents=True)
    exp.mkdir(parents=True)
    via = {"components": ["AL", "TI", "VA"], "phases": ["HCP_A3", "LIQUID"], "conditions": {"P": 101325, "T": [1715.0]}, "output": "ZPF",
           "values": [[["LIQUID", ["TI"], [0.55]], ["HCP_A3", ["TI"], [0.60]]]], "reference": f"Assessor 2008, doi:{ASSESS}",
           "tags": ["experimental", "invariant_table", "via_assessment", "orchid"],
           "orchid": {"evidence_class": "experimental", "observations": [{"id": "ORC-AAAAAAAAAA", "paper": f"doi:{ASSESS}"}],
                      "papers": [f"doi:{ASSESS}", f"doi:{ORIG}"]}}
    plain = {"components": ["AL", "TI", "VA"], "phases": ["HCP_A3"], "conditions": {"P": 101325, "T": [1200.0]}, "output": "ZPF",
             "values": [[["HCP_A3", ["TI"], [0.80]]]], "reference": "fixture", "comment": "ORC-BBBBBBBBBB"}
    (inv / "via.zpf-00.json").write_text(json.dumps(via))
    (exp / "plain.zpf-00.json").write_text(json.dumps(plain))
    asm = base / "od" / "espei" / "assessed" / "AL-TI"
    asm.mkdir(parents=True)
    (asm / "calc.zpf-00.json").write_text(json.dumps(dict(plain, reference="Assessor 2008 calculated diagram", tags=["model"])))
    return base / "od"


class Traceability(SageTestCase):
    def setUp(self):
        super().setUp()
        os.environ["ORCHID_DATA_DIR"] = str(_fixture(self.tmp))
        self.root = self.tmp / "alti"
        self.a = "alti-trace"
        F.new_assessment("AL-TI", self.a, str(self.root), phases=["HCP_A3", "LIQUID"], T_range=[300, 2000])
        self.g = F.gather_evidence(self.a)
        self.states = {s["source_file"].split("/")[-1]: s for s in json.loads((self.root / "evidence" / "states.json").read_text())["states"]}

    def _keys(self):
        via = next(s for n, s in self.states.items() if "via" in n)
        plain = next(s for n, s in self.states.items() if "plain" in n)
        return f"{via['source_file']}#{via['row']}", f"{plain['source_file']}#{plain['row']}"

    def test_mapping_tag_preserves_experimental_class(self):
        self.assertEqual(self.g["traceability"], {"traced": 0, "comparison_only": 0, "untraced": 2})
        for s in self.states.values():
            self.assertEqual(s["evidence_class"], "experimental")
            self.assertNotIn("read_from_assessment", s)
            self.assertNotIn("ground_truth", s)
        self.assertEqual(F.traceability(self.a)["evidence_classes"], {"experimental": 2})

    def test_trace_refusals_are_input_checks(self):
        kv, kp = self._keys()
        good = dict(state_keys=[kv], status="traced", who="Reader", why="read source", doi=ORIG, page="3", locator="Table 2")
        for change in ({"who":"sage_mcp"}, {"why":""}, {"doi":None}, {"page":None}, {"locator":None},
                       {"state_keys":["nope#0"]}, {"state_keys":[kv,kv]}, {"status":"ground_truth"}):
            with self.assertRaises(SageError):
                F.record_trace(self.a, **(good | change))
        self.assertEqual(F.traceability(self.a)["counts"]["untraced"], 2)

    def test_same_paper_can_report_own_work(self):
        kv, _ = self._keys()
        F.record_trace(self.a, [kv], "traced", "Reader", "read original result", doi=ASSESS, page="3", locator="Table 2")
        r = F.traceability(self.a)["traced"][0]
        self.assertEqual(r["origin"]["measured_in"], "doi:" + ASSESS)
        self.assertTrue(r["origin"]["own_work_of_paper"])
        self.assertEqual(r["evidence_class"], "experimental")

    def test_external_source_and_supersession_leave_bundle_unchanged(self):
        kv, _ = self._keys()
        paths = [self.root / 'evidence' / n for n in ('states.json','MANIFEST.json')]
        before = [p.read_bytes() for p in paths]
        F.record_trace(self.a, [kv], "traced", "Reader", "read original", doi="HTTPS://DOI.ORG/" + ORIG, page="7", locator="Fig. 2")
        r = F.traceability(self.a)["traced"][0]
        self.assertFalse(r["origin"]["own_work_of_paper"])
        F.record_trace(self.a, [kv], "comparison_only", "Reader", "source attribution needs review")
        self.assertEqual(F.traceability(self.a)["evidence_classes"], {"experimental": 2})
        saved = json.loads((self.root/'traces/TRACES.json').read_text())["traces"][kv]
        self.assertEqual(saved["supersedes"]["origin"]["measured_in"], 'doi:' + ORIG)
        self.assertEqual(before, [p.read_bytes() for p in paths])
        self.assertTrue(F.validate_assessment(self.a)["ok"])

    def test_assessed_source_check_never_promotes_to_experimental(self):
        F.new_assessment("AL-TI", "alti-model", str(self.tmp/"model"), phases=["HCP_A3","LIQUID"], T_range=[300,2000])
        F.gather_evidence("alti-model", evidence_classes=["assessed"])
        root=self.tmp/"model"
        s=json.loads((root/'evidence/states.json').read_text())["states"][0]
        self.assertEqual(s["evidence_class"], 'assessed')
        self.assertEqual(s["zpf_certainty"]["certainty_tier"], 'less_certain')
        F.record_trace("alti-model", [T.state_key(s)], 'traced', 'Reader', 'checked calculated result', doi=ASSESS,page='1',locator='Fig. 1')
        self.assertEqual(F.traceability("alti-model")["evidence_classes"], {'assessed':1})
        for ec in ('dft','derived','model','assessed_phase_diagram'):
            self.assertEqual(T.effective_class({'evidence_class':ec},{'status':'traced'}),ec)

    def test_package_warns_and_runs_with_untraced_states(self):
        final=self.root/'final.tdb'; final.write_text('$ synthetic package fixture\n')
        st=F.load_state(self.root); st['bindings']['final_tdb']=str(final); F.save_state(self.root,st)
        out=F.package(self.a)
        self.assertTrue(out['packaged'],out)
        self.assertEqual(out['traceability_status'],'WARN')
        self.assertEqual(out['crate']['returncode'],0,out['crate'])
        self.assertEqual(json.loads((self.root/'crate/evidence/TRACEABILITY.json').read_text()),out['traceability'])
        self.assertEqual(json.loads(Path(out['traceability_report']).read_text())['counts']['untraced'],2)

    def test_missing_final_tdb_still_blocks(self):
        out=F.package(self.a)
        self.assertFalse(out['packaged'])
        self.assertEqual(out['traceability_status'],'WARN')
        self.assertTrue(any('final pick' in m for m in out['missing']))
        self.assertFalse(any('untraced' in m for m in out['missing']))

    def test_stale_steps_still_block(self):
        st=F.load_state(self.root); st['steps']['build_datasets']['status']='stale'; F.save_state(self.root,st)
        self.assertTrue(any('stale steps' in m for m in F.package(self.a)['missing']))

    def test_missing_states_warns_without_trace_gate(self):
        F.new_assessment('AL-C-TI','ternary-report',str(self.tmp/'ternary'))
        out=F.package('ternary-report')
        self.assertEqual(out['traceability_status'],'WARN')
        self.assertTrue(any('traceability cannot be checked' in w for w in out['warnings']))
        self.assertFalse(any('traceability' in m for m in out['missing']))

    def test_unknown_reporting_paper_keeps_ownership_unknown(self):
        _, kp=self._keys()
        F.record_trace(self.a,[kp],'traced','Reader','read source',doi=ORIG,page='3',locator='Fig. 1')
        self.assertIsNone(F.traceability(self.a)['traced'][0]['origin']['own_work_of_paper'])

    def test_existing_provenance_is_not_a_claim_of_local_review(self):
        root=self.tmp/'provenance'; (root/'evidence').mkdir(parents=True)
        state={'source_file':'x','row':0,'evidence_class':'experimental',
               'origin':{'measured_in':'doi:'+ORIG,'own_work_of_paper':False},'trace':{'status':'traced'}}
        (root/'evidence/states.json').write_text(json.dumps({'states':[state]}))
        out=T.summary(root,{'bindings':{}})
        self.assertEqual(out['counts']['untraced'],1)
        self.assertEqual(out['states'][0]['origin'],state['origin'])
        self.assertEqual(out['evidence_classes'],{'experimental':1})

    def test_server_schema(self):
        tools={t['name']:t for t in server.tool_descriptions()}
        self.assertEqual(tools['record_trace']['inputSchema']['properties']['status']['enum'],['traced','comparison_only'])

    def test_row_provenance_survives_gather_and_manifest(self):
        path=Path(os.environ['ORCHID_DATA_DIR'])/'espei/experimental/AL-TI/plain.zpf-00.json'
        d=json.loads(path.read_text())
        origin={'measured_in':'doi:'+ORIG,'own_work_of_paper':False,'class':'assessed_phase_diagram','basis':'fixture'}
        cited=[{'doi':ORIG,'paper':'doi:'+ORIG,'status':'as supplied'}]
        d['orchid']={'observations':[{'id':'ORC-BBBBBBBBBB','evidence_class':'assessed_phase_diagram','origin':origin,'cited_sources':cited}]}
        path.write_text(json.dumps(d))
        F.new_assessment('AL-TI','provenance-gather',str(self.tmp/'g'),phases=['HCP_A3','LIQUID'],T_range=[300,2000])
        F.gather_evidence('provenance-gather',evidence_classes=['experimental'])
        s=json.loads((self.tmp/'g/evidence/states.json').read_text())['states'][0]
        self.assertEqual(s['origin'],origin)
        self.assertEqual(s['cited_sources'],cited)
        self.assertEqual(s['evidence_class'],'assessed_phase_diagram')
        self.assertEqual(s['zpf_certainty']['certainty_tier'],'less_certain')
        self.assertTrue(F.validate_assessment('provenance-gather')['ok'])

    def test_row_provenance_does_not_bleed_between_observations(self):
        beb=evidence_bundle_module()
        d={'conditions':{'T':[1000,1100]},'values':[[['HCP_A3',['TI'],[0.1]]],[['HCP_A3',['TI'],[0.2]]]],
           'evidence_class':'experimental','origin':{'measured_in':'doi:10.1000/file'},
           'orchid':{'observations':[{'id':'ORC-AAAAAAAAAA','origin':{'measured_in':'doi:10.1000/row0'}},
                                     {'id':'ORC-BBBBBBBBBB','origin':{'measured_in':'doi:10.1000/row1'}}]}}
        states=beb.states_from_zpf(d,'fixture.json','exp','TI')
        self.assertEqual([s['origin']['measured_in'] for s in states],['doi:10.1000/row0','doi:10.1000/row1'])
        states[0]['origin']['measured_in']='changed'
        self.assertEqual(d['orchid']['observations'][0]['origin']['measured_in'],'doi:10.1000/row0')
