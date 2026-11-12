import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from calphad_model_guide import audit, compare, library, plan, recommend, validate, search
ROOT=Path(__file__).resolve().parents[1]
def example(n):return json.loads((ROOT/'examples'/f'{n}.json').read_text())
class Tests(unittest.TestCase):
 def test_catalog_search(self):
  r=search(topic='vacancies')
  self.assertGreaterEqual(r['count'],3)
  self.assertTrue(r['sources'])
  self.assertEqual(search('nonexistent-search-token')['count'],0)
 def test_ionic_input_rejected(self):
  s=example('substitutional');s['elements']=['Cu+1','Ni']
  s['sublattices'][0]['constituents']=['Cu+1','Ni']
  self.assertTrue(validate(s))
 def test_incomplete_compatibility(self):
  s=example('vacancy')
  self.assertEqual(compare(s,s)['status'],'requires_reconciliation')
 def test_reported_evidence_not_promoted(self):
  s=example('sigma');s['evidence'][0]['status']='reported'
  r=next(x for x in recommend(s)['candidates'] if x['id']=='cef-baseline')
  self.assertIn('crystallography',r['missing_verified_evidence'])
 def test_sigma(self):
  p=plan(example('sigma'),2)
  self.assertEqual(p['formal_endmembers'],1024);self.assertEqual(len(p['preview']),2)
  self.assertTrue(p['truncated']);self.assertIsNone(p['calculation_count'])
 def test_ebef_not_claimed(self):
  e=next(x for x in recommend(example('sigma'))['candidates'] if x['id']=='ebef-multisite')
  self.assertEqual(e['screening_status'],'needs_evidence');self.assertIn('endmember_energies',e['missing_verified_evidence'])
  self.assertEqual(e['implementation_status'],'advisory_screening_only')
 def test_vacancies(self):
  p=plan(example('vacancy'),20)
  self.assertEqual(p['nonempty_endmembers'],8)
  for x in p['preview']:self.assertAlmostEqual(sum(x['atomic_fractions'].values()),1)
  self.assertFalse(audit(example('vacancy'))['metadata_ready'])
 def test_conflict(self):
  s=example('sigma')
  for kind in ('endmember_energies','phase_equilibria'):
   s['evidence'].append(dict(kind=kind,source='test',locator='test',status='verified'))
  s['evidence'].append(dict(kind='endmember_energies',source='test2',locator='test',status='conflicting'))
  e=next(x for x in recommend(s)['candidates'] if x['id']=='ebef-multisite')
  self.assertEqual(e['screening_status'],'needs_evidence')
 def test_bad_input(self):
  for field in example('sigma'):
   s=example('sigma');s[field]=None;self.assertTrue(validate(s))
  for value in (0,-1,float('nan'),True):
   s=example('sigma');s['sublattices'][0]['site_ratio']=value;self.assertTrue(validate(s))
 def test_comparison(self):
  a=example('sigma');b=copy.deepcopy(a);b['sublattices'].reverse()
  self.assertEqual(compare(a,b)['status'],'structural_preflight_only')
  self.assertFalse(compare(a,b)['thermodynamic_equivalence_proven'])
  a['energy_basis']=b['energy_basis']='J/mol_formula'
  for sl in b['sublattices']:sl['site_ratio']*=2
  self.assertEqual(compare(a,b)['status'],'requires_reconciliation')
 def test_bounded(self):
  s=example('sigma');s['sublattices']=[dict(id=str(i),site_ratio=1,constituents=s['elements']) for i in range(30)]
  self.assertEqual(len(plan(s,1)['preview']),1)
  with self.assertRaises(ValueError):plan(s,1001)
 def test_sources(self):
  lib=library();ids={s['id'] for s in lib['sources']}
  self.assertEqual(len(ids),len(lib['sources']))
  self.assertEqual(len({r['id'] for r in lib['recipes']}),len(lib['recipes']))
  for r in lib['recipes']:
   self.assertTrue(set(r['source_ids'])<=ids);self.assertTrue(r['validation_tests']);self.assertTrue(r['limitations'])
 def test_cli(self):
  p=subprocess.run([sys.executable,'-m','calphad_model_guide','plan','examples/sigma.json','--limit','1'],cwd=ROOT,text=True,capture_output=True)
  self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout)['formal_endmembers'],1024)
  p=subprocess.run([sys.executable,'-m','calphad_model_guide','validate','missing.json'],cwd=ROOT,text=True,capture_output=True)
  self.assertEqual(p.returncode,2);self.assertIn('error',json.loads(p.stderr))
if __name__=='__main__':unittest.main()
