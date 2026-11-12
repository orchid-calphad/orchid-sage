import copy
import json
from pathlib import Path
import unittest
from calphad_model_guide.linear import basis, reciprocal

ROOT = Path(__file__).resolve().parents[1]

class LinearTests(unittest.TestCase):
    def test_binary_ordering_has_more_occupancy_than_composition_dimensions(self):
        s = json.loads((ROOT/'examples/substitutional.json').read_text())
        s['elements'] = ['Al','Ni']
        s['sublattices'] = [{'id': str(i), 'site_ratio': 1, 'constituents': ['Al','Ni']} for i in range(2)]
        result = basis(s)
        self.assertEqual((result['composition_rank'], result['occupancy_rank']), (2,3))
        self.assertEqual(result['composition_columns'][1], result['composition_columns'][2])
        self.assertIsNone(result['independent_energy_parameters'])
        for site in s['sublattices']:
            site['site_ratio'] = 0.5
        self.assertEqual(basis(s)['composition_rank'], 2)

    def test_sigma_and_limit(self):
        s=json.loads((ROOT/'examples/sigma.json').read_text())
        r=basis(s)
        self.assertEqual((r['formal_corner_count'],r['composition_rank'],r['occupancy_rank']), (1024,4,16))
        with self.assertRaises(ValueError): basis(s, 100)

    def test_reciprocal_all_positions_and_residual(self):
        s={'energies': {'AC':'1/3','BD':'5/3','AD':1,'BC':1}, 'delta':0,
           'energy_basis':'J/mol_formula','reference_state':'common SER at 298.15 K',
           'assumption':'Illustrative zero reciprocal energy, not a symmetry claim'}
        for name in s['energies']:
            c=copy.deepcopy(s); c['energies'][name]=None
            r=reciprocal(c)
            self.assertTrue(r['exactly_consistent'])
            self.assertEqual(r['energies'][name], str(s['energies'][name]))
        s['delta']=2
        self.assertEqual(reciprocal(s)['residual'], '-2')
        s['energies']['AC']=None
        self.assertEqual(reciprocal(s)['energies']['AC'], '7/3')

    def test_reciprocal_rejects_implicit_or_bad_constraints(self):
        s={'energies':{'AC':None,'BD':1,'AD':2,'BC':3}, 'delta':0,
           'energy_basis':'J/mol_formula','reference_state':'SER', 'assumption':'explicit'}
        for key,value in [('delta',None),('delta',float('nan')),('delta',True),
                          ('energy_basis','J/mol_atoms'),('assumption',''),('reference_state','unknown')]:
            c=copy.deepcopy(s); c[key]=value
            with self.assertRaises(ValueError): reciprocal(c)
        s['energies']['BD']=None
        with self.assertRaises(ValueError): reciprocal(s)

if __name__ == '__main__': unittest.main()
