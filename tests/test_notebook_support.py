import json
from pathlib import Path
import unittest

import numpy as np

from examples.demo_qaoa import DEMO_ROUTES, extended_routes
from notebook_support import PlanReference, coefficient_energies
from quantum_optimizer import analyse_plan, construct_qubo, decode_key, qubo_to_ising


class NotebookReferenceTests(unittest.TestCase):
    def test_vectors_match_every_small_plan(self):
        for routes in (DEMO_ROUTES, DEMO_ROUTES[:1]):
            ref = PlanReference(routes, 7, 0.7)
            for i in range(len(ref)):
                plan = analyse_plan(decode_key(format(i, f'0{len(routes)}b'), len(routes)), routes, 7, 0.7)
                self.assertEqual(ref[i]['route_ids'], plan['ids_rute'])
                self.assertEqual(ref.costs[i], plan['cost_total'])
                self.assertEqual(ref.values[i], plan['valoare_totala'])
                self.assertAlmostEqual(ref.energies[i], plan['energie'])
            q = construct_qubo(routes, 7, 0.7)
            h = qubo_to_ising(q)
            np.testing.assert_allclose(coefficient_energies(q['linear'], q['quadratic'], q['offset']), ref.energies, atol=1e-10)
            np.testing.assert_allclose(coefficient_energies(h['h'], h['J'], h['constant'], spin=True), ref.energies, atol=1e-10)

    def test_metrics_include_all_tied_optima_and_ignore_zero_counts(self):
        routes = [dict(id=i, cities=('A','B'), cost=1, value=2) for i in range(2)]
        ref = PlanReference(routes, 1, 1)
        metrics = ref.metrics({'01':2, '10':3, '11':5, '00':0}, routes, 1)
        self.assertEqual(metrics['shots'], 10)
        self.assertEqual(metrics['optimal_feasible_probability'], 0.5)
        self.assertEqual(metrics['feasible_rate'], 0.5)
        for counts in ({}, {'00':-1}, {'bad':1}):
            with self.assertRaises(ValueError): ref.metrics(counts, routes, 1)
        with self.assertRaises(ValueError): ref.metrics({'00':1}, routes, 2)

    def test_notebook_regression_nineteen_route_cells(self):
        p = Path(__file__).resolve().parents[1]/'Quantum_Railways_Labb.ipynb'
        nb = json.loads(p.read_text(encoding='utf-8'))
        for i, c in enumerate(nb['cells']):
            if c['cell_type']=='code': compile(''.join(c['source']), f'cell_{i}', 'exec')
        routes = extended_routes()
        ns = dict(np=np, demo_routes=routes, ROUTES=routes, BUDGET=20,
                  N_DECISIONS=19, WEAK_PENALTY=0.7, MATHEMATICAL_DEEP_DIVE=False,
                  display=lambda *a: None, Markdown=lambda s:s)
        exec(''.join(nb['cells'][5]['source']), ns)
        ns['draw_board'] = lambda **kw: None
        ns['plt'] = type('Plots', (), {'show': lambda self: None})()
        for i in (6,8,10,12): exec(''.join(nb['cells'][i]['source']), ns)
        ref = ns['classical_rows']
        self.assertEqual(len(ns['my_plan']),19)
        self.assertEqual(len(ref),524288)
        self.assertEqual(ref.best_valid_plan()['score'],46)
        self.assertEqual(ref.best_valid_plan()['cost'],20)
        for i in (14,16): exec(''.join(nb['cells'][i]['source']), ns)
        np.testing.assert_allclose(ns['ising_energies'],ref.energies,atol=1e-9)


if __name__=='__main__': unittest.main()
