import ast
import copy
import itertools
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.quantum_info import Statevector

import quantum_optimizer as qo
from examples.demo_qaoa import DEMO_ROUTES, extended_routes


def configurations(n):
    return itertools.product((0, 1), repeat=n)


class ValidationTests(unittest.TestCase):
    def test_invalid_arguments(self):
        for name in ('p', 'shots', 'maxiter', 'restarts'):
            for value in (0, -1, 1.5, True, None):
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    qo.optimizeaza_qaoa(DEMO_ROUTES, 7, **{name: value})
        for budget in (-1, True, 1.2, None, 2**51):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                qo.optimizeaza_qaoa(DEMO_ROUTES, budget)
        for penalty in (0, -1, True, float('nan'), float('inf'), '4', 1e308):
            with self.subTest(penalty=penalty), self.assertRaises(ValueError):
                qo.optimizeaza_qaoa(DEMO_ROUTES, 7, penalty)
        for seed in (-1, True, 1.5, 2**32):
            with self.subTest(seed=seed), self.assertRaises(ValueError):
                qo.optimizeaza_qaoa(DEMO_ROUTES, 7, seed=seed)
        for mode in ('hardware', None, []):
            with self.assertRaises(ValueError):
                qo.optimizeaza_qaoa(DEMO_ROUTES, 7, backend_mode=mode)

    def test_invalid_routes(self):
        for routes in ([], None, 'routes', [{}], [1], [DEMO_ROUTES[0]]*2):
            with self.subTest(routes=routes), self.assertRaises(ValueError):
                qo.construct_qubo(routes, 7, 1)
        for field in ('id', 'cities', 'cost', 'value'):
            route = dict(DEMO_ROUTES[0])
            del route[field]
            with self.assertRaises(ValueError):
                qo.construct_qubo([route], 7, 1)
        bad = [('id', []), ('id', True), ('id', ''), ('cities', 'AB'),
               ('cities', ('A', '')), ('cities', ('A',)), ('cost', -1),
               ('cost', 1.2), ('value', float('nan')), ('value', -1),
               ('value', 2**51), ('border_cost', 3), ('border_cost', -1),
               ('international', 'yes')]
        for field, value in bad:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                qo.construct_qubo([{**DEMO_ROUTES[0], field: value}], 7, 1)

    def test_resource_limits(self):
        routes = [{**DEMO_ROUTES[0], 'id': i} for i in range(21)]
        with self.assertRaisesRegex(ValueError, 'resource limit'):
            qo.optimizeaza_qaoa(routes, 20)
        with self.assertRaisesRegex(ValueError, 'noisy'):
            qo.optimizeaza_qaoa(extended_routes(), 20, backend_mode='noisy')
        with self.assertRaises(ValueError):
            qo.parameterized_qaoa(qo.construct_qubo(DEMO_ROUTES, 7, 1), p=101)

    def test_malformed_coefficients(self):
        q = qo.construct_qubo(DEMO_ROUTES, 7, 1)
        for change in ({'offset': float('inf')}, {'linear': [1]},
                       {'quadratic': np.eye(5)}, {'linear': [float('nan')]*5}):
            with self.assertRaises(ValueError):
                qo.qubo_to_ising({**q, **change})

    def test_international_cost_and_order(self):
        routes = [dict(id=90, cities=('A', 'B'), cost=5, value=9,
                       border_cost=2, international=True), DEMO_ROUTES[0]]
        original = copy.deepcopy(routes)
        plan = qo.analyse_plan([1, 0], routes, 5, 1)
        self.assertEqual(plan['cost_total'], 5)
        self.assertEqual(plan['ids_rute'], [90])
        self.assertTrue(plan['valid'])
        self.assertEqual(plan['bitstring'], '01')
        self.assertEqual(qo.analyse_plan([0, 1], routes, 5)['ids_rute'], [0])
        self.assertEqual(routes, original)

    def test_decoding(self):
        self.assertEqual(qo.decode_key('10 001', 5), [1, 0, 0, 0, 1])
        for key in ('0x1', '12', '1', '', 10):
            with self.assertRaises(ValueError):
                qo.decode_key(key, 2)
        with self.assertRaises(ValueError):
            qo.analyse_plan([1], DEMO_ROUTES, 7)


class MathematicsTests(unittest.TestCase):
    def test_all_direct_qubo_ising_energies(self):
        rng = np.random.default_rng(35)
        scenarios = [(DEMO_ROUTES, 7, 0.7), (DEMO_ROUTES, 0, 4)]
        for n in range(1, 6):
            routes = [dict(id=i, cities=('A', 'B'), cost=int(rng.integers(0, 6)),
                           value=int(rng.integers(0, 10))) for i in range(n)]
            scenarios.append((routes, 4, 1.3))
        for routes, budget, penalty in scenarios:
            q = qo.construct_qubo(routes, budget, penalty)
            ising = qo.qubo_to_ising(q)
            for bits in configurations(len(routes)):
                energy = qo.model_energy(bits, routes, budget, penalty)
                self.assertAlmostEqual(energy, qo.qubo_energy(bits, q), places=10)
                self.assertAlmostEqual(energy, qo.ising_energy(bits, ising), places=10)

    def test_original_counterexample(self):
        plan = qo.analyse_plan([1, 0, 1, 1, 0], DEMO_ROUTES, 7, 0.7)
        self.assertAlmostEqual(plan['energie'], -17.3)
        self.assertEqual(plan['cost_total'], 8)
        self.assertFalse(plan['valid'])
        reference = qo.classical_reference(DEMO_ROUTES, 7)
        self.assertEqual(reference['valoare_optima'], 15)
        self.assertEqual(reference['cost_total'], 7)

    def test_cost_layer_phase_including_pairs(self):
        q = qo.construct_qubo(DEMO_ROUTES, 7, 0.7)
        ising = qo.qubo_to_ising(q)
        circuit = QuantumCircuit(5)
        circuit.h(range(5))
        gamma = 0.31
        qo.add_cost(circuit, gamma, ising)
        state = Statevector.from_instruction(circuit).data
        scale = max(1, np.abs(ising['h']).max(), np.abs(ising['J']).max())
        energy = [qo.qubo_energy(qo.decode_key(format(k, '05b'), 5), q) for k in range(32)]
        expected = np.exp(-1j*gamma*np.array(energy)/scale)
        np.testing.assert_allclose(state/state[0], expected/expected[0], atol=1e-12)
        np.testing.assert_allclose(np.abs(state)**2, np.full(32, 1/32), atol=1e-12)

    def test_mixer(self):
        circuit = QuantumCircuit(1)
        qo.add_mixer(circuit, 0.3)
        self.assertAlmostEqual(Statevector.from_instruction(circuit).probabilities()[1], np.sin(0.3)**2)

    def test_parameters_layers_and_uniform_zero_angles(self):
        q = qo.construct_qubo(DEMO_ROUTES, 7, 0.7)
        for p in (1, 2):
            circuit, parameters = qo.parameterized_qaoa(q, p)
            self.assertEqual(len(parameters), 2*p)
            self.assertEqual(len(circuit.parameters), 2*p)
            self.assertTrue(all(isinstance(v, Parameter) for v in parameters))
            self.assertEqual(circuit.count_ops()['rx'], 5*p)
            self.assertEqual(circuit.count_ops()['rzz'], 10*p)
            bound = circuit.assign_parameters(dict.fromkeys(parameters, 0))
            np.testing.assert_allclose(Statevector.from_instruction(bound).probabilities(), np.full(32, 1/32))
        measured, _ = qo.parameterized_qaoa(q, measure=True)
        self.assertEqual(measured.cregs[0].name, 'plan')
        self.assertEqual(measured.count_ops()['measure'], 5)

    def test_zero_cost_zero_hamiltonian(self):
        routes = [dict(id='free', cities=('A', 'B'), cost=0, value=0)]
        q = qo.construct_qubo(routes, 0, 1)
        circuit, params = qo.parameterized_qaoa(q)
        bound = circuit.assign_parameters(dict.fromkeys(params, 0.4))
        np.testing.assert_allclose(Statevector.from_instruction(bound).probabilities(), [0.5, 0.5])

    def test_vectorized_basis_energies(self):
        costs, values = qo._basis_totals(DEMO_ROUTES)
        for k in range(32):
            plan = qo.analyse_plan(qo.decode_key(format(k, '05b'), 5), DEMO_ROUTES, 7)
            self.assertEqual(costs[k], plan['cost_total'])
            self.assertEqual(values[k], plan['valoare_totala'])


class ClassicalTests(unittest.TestCase):
    def test_dp_matches_exhaustive_enumeration(self):
        rng = np.random.default_rng(19)
        for _ in range(40):
            routes = [dict(id=i, cities=('A', 'B'), cost=int(rng.integers(0, 7)),
                           value=int(rng.integers(0, 12))) for i in range(6)]
            budget = int(rng.integers(0, 20))
            plans = [qo.analyse_plan(bits, routes, budget) for bits in configurations(6)]
            best = min((r for r in plans if r['valid']),
                       key=lambda r: (-r['valoare_totala'], r['cost_total'], r['bitstring']))
            reference = qo.classical_reference(routes, budget)
            self.assertEqual(reference['valoare_optima'], best['valoare_totala'])
            self.assertEqual(reference['cost_total'], best['cost_total'])
            self.assertEqual(reference['bitstring'], best['bitstring'])

    def test_extended_data_matches_notebook_and_exact_46(self):
        notebook = Path(__file__).resolve().parents[1] / 'Quantum_Railways_Labb.ipynb'
        cells = json.loads(notebook.read_text(encoding='utf-8'))['cells']
        data = {}
        for cell in cells:
            if cell['cell_type'] != 'code':
                continue
            source = ''.join(cell['source'])
            if 'INTERNATIONAL_EDGES =' not in source:
                continue
            for node in ast.parse(source).body:
                if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                    name = node.targets[0].id
                    if name in ('EDGE_DATA', 'INTERNATIONAL_EDGES'):
                        data[name] = ast.literal_eval(node.value)
        expected = [(u, v, c, value, 0) for u, v, c, value in data['EDGE_DATA']]
        expected += [(u, v, c+b, value, b) for u, v, c, value, b in data['INTERNATIONAL_EDGES']]
        routes = extended_routes()
        foreign = [r for r in routes if r['international']]
        self.assertEqual(len(foreign), 6)
        self.assertTrue(all(r['border_cost'] == 1 for r in foreign))
        self.assertEqual([r['cost'] for r in foreign], [5, 5, 4, 4, 5, 5])
        self.assertTrue(all(r['border_cost'] == 0 for r in routes if not r['international']))
        self.assertEqual([(r['cities'][0], r['cities'][1], r['cost'], r['value'], r['border_cost'])
                          for r in routes], expected)
        reference = qo.classical_reference(routes, 20)
        self.assertEqual(len(routes), 19)
        self.assertEqual(reference['valoare_optima'], 46)
        # Independent vectorized complete enumeration (no quantum optimization).
        costs, values = qo._basis_totals(routes)
        self.assertEqual(int(values[costs <= 20].max()), 46)


class SamplingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = qo.optimizeaza_qaoa(DEMO_ROUTES, 7, 0.7, maxiter=16, shots=256)

    def test_counts_budget_and_classical_comparison(self):
        r = self.result
        self.assertEqual(sum(r['counts'].values()), 256)
        self.assertEqual(r['status'], 'ok')
        self.assertTrue(r['valid'])
        self.assertLessEqual(r['cost_total'], 7)
        self.assertEqual(r['referinta_clasica']['valoare_optima'], 15)
        self.assertLessEqual(r['valoare_totala'], 15)
        self.assertEqual(r['diferenta_valoare'], 15-r['valoare_totala'])
        self.assertIn(r['bitstring_recomandat'], r['counts'])
        valid = [qo.analyse_plan(qo.decode_key(k, 5), DEMO_ROUTES, 7, 0.7) for k in r['counts']]
        best = min((p for p in valid if p['valid']),
                   key=lambda p: (-p['valoare_totala'], p['cost_total'], p['bitstring']))
        self.assertEqual(r['bitstring_recomandat'], best['bitstring'])

    def test_training_metrics_and_json(self):
        r = self.result
        self.assertLessEqual(r['energie_medie'], r['energie_medie_initiala'] + 1e-10)
        self.assertEqual(len(r['gamma']), 1)
        self.assertEqual(len(r['beta']), 1)
        self.assertEqual(r['statistici']['evaluari'], sum(run['evaluari'] for run in r['optimizare']['rulari']))
        self.assertEqual(r['statistici']['evaluari'], 1+r['optimizare']['rulari'][0]['evaluari_scipy'])
        for key in ('rata_planuri_valide', 'probabilitate_optim_valid',
                    'probabilitate_optim_valid_ideala', 'probabilitate_valida_ideala'):
            self.assertGreaterEqual(r[key], 0)
            self.assertLessEqual(r[key], 1+1e-12)
        self.assertEqual(json.loads(json.dumps(r, allow_nan=False)), r)
        q = qo.construct_qubo(DEMO_ROUTES, 7, 0.7)
        circuit, parameters = qo.parameterized_qaoa(q)
        bound = circuit.assign_parameters(dict(zip(parameters, r['unghiuri_optime'])))
        probabilities = Statevector.from_instruction(bound).probabilities()
        energies = [qo.qubo_energy(qo.decode_key(format(k, '05b'), 5), q) for k in range(32)]
        self.assertAlmostEqual(r['energie_medie'], float(probabilities @ energies))
        empirical = sum(r['counts'][k] * qo.model_energy(qo.decode_key(k, 5), DEMO_ROUTES, 7, 0.7)
                        for k in r['counts']) / 256
        self.assertAlmostEqual(r['energie_medie_masurata'], empirical)

    def test_reproducibility(self):
        other = qo.optimizeaza_qaoa(DEMO_ROUTES, 7, 0.7, maxiter=16, shots=256)
        self.assertEqual(self.result['counts'], other['counts'])
        np.testing.assert_allclose(self.result['unghiuri_optime'], other['unghiuri_optime'])

    def test_no_valid_sample_never_falls_back(self):
        with patch.object(qo, '_sample_counts', return_value=({'11111': 8}, {})):
            r = qo.optimizeaza_qaoa(DEMO_ROUTES, 0, maxiter=4, shots=8)
        self.assertEqual(r['status'], 'no_valid_sample')
        self.assertFalse(r['valid'])
        self.assertEqual(r['rute_recomandate'], [])
        self.assertEqual(r['ids_rute_recomandate'], [])
        self.assertIsNone(r['cost_total'])
        self.assertIsNone(r['valoare_totala'])
        self.assertIsNone(r['diferenta_valoare'])
        self.assertEqual(r['referinta_clasica']['valoare_optima'], 0)
        json.dumps(r, allow_nan=False)

    def test_selection_ties_all_optima_and_most_frequent(self):
        routes = [dict(id=i, cities=('A', 'B'), cost=1, value=2) for i in range(2)]
        counts = {'01': 2, '10': 3, '11': 5}
        s = qo._summarize_counts(counts, routes, 1, 1, 2, 10)
        self.assertEqual(s['best']['bitstring'], '01')
        self.assertEqual(s['most_frequent']['bitstring'], '11')
        self.assertFalse(s['most_frequent']['valid'])
        self.assertEqual(s['optimal_rate'], 0.5)
        with patch.object(qo, '_sample_counts', return_value=(counts, {})):
            r = qo.optimizeaza_qaoa(routes, 1, shots=10, maxiter=5)
        self.assertEqual(r['probabilitate_optim_valid'], 0.5)
        q = qo.construct_qubo(routes, 1, 4)
        circuit, params = qo.parameterized_qaoa(q)
        bound = circuit.assign_parameters(dict(zip(params, r['unghiuri_optime'])))
        probabilities = Statevector.from_instruction(bound).probabilities()
        self.assertAlmostEqual(r['probabilitate_optim_valid_ideala'], probabilities[1]+probabilities[2])
        cheaper = [routes[0], {**routes[1], 'cost': 0}]
        s = qo._summarize_counts({'01': 1, '10': 1}, cheaper, 1, 1, 2, 2)
        self.assertEqual(s['best']['bitstring'], '10')

    def test_multilayer_restarts(self):
        r = qo.optimizeaza_qaoa(DEMO_ROUTES[:2], 3, p=2, restarts=2, shots=16, maxiter=6)
        self.assertEqual(len(r['unghiuri_optime']), 4)
        self.assertEqual(len(r['optimizare']['rulari']), 2)
        self.assertAlmostEqual(r['energie_medie'], min(run['energie_finala'] for run in r['optimizare']['rulari']))

    def test_zero_budget_and_free_routes(self):
        routes = [dict(id='free', cities=('A', 'B'), cost=0, value=2)]
        r = qo.optimizeaza_qaoa(routes, 0, shots=64, maxiter=8)
        self.assertEqual(r['referinta_clasica']['valoare_optima'], 2)
        self.assertEqual(r['rata_planuri_valide'], 1)
        self.assertEqual(r['cost_total'], 0)

    def test_empty_measured_plan_is_valid(self):
        with patch.object(qo, '_sample_counts', return_value=({'00000': 8}, {})):
            r = qo.optimizeaza_qaoa(DEMO_ROUTES, 0, maxiter=4, shots=8)
        self.assertEqual(r['status'], 'ok')
        self.assertTrue(r['valid'])
        self.assertEqual(r['rute_recomandate'], [])
        self.assertEqual(r['cost_total'], 0)
        self.assertEqual(r['valoare_totala'], 0)
        self.assertEqual(r['bitstring_recomandat'], '00000')

    def test_bad_counts_rejected(self):
        for counts in ({'00000': 1}, {'00000': -8}, {'bad': 8}):
            with self.assertRaises(ValueError):
                qo._summarize_counts(counts, DEMO_ROUTES, 7, 1, 15, 8)

    def test_noisy_small_local_backend(self):
        with self.assertWarns(RuntimeWarning):
            r = qo.optimizeaza_qaoa(DEMO_ROUTES[:2], 2, backend_mode='noisy', maxiter=6, shots=32)
        self.assertEqual(sum(r['counts'].values()), 32)
        self.assertEqual(r['statistici']['backend'], 'noisy')
        self.assertEqual(r['statistici']['simulare_zgomot'], 'executata')
        self.assertGreater(r['statistici']['porti_doi_qubiti'], 0)
        self.assertGreater(r['statistici']['adancime_circuit'], 0)
        self.assertEqual(r['statistici']['registru_masurare'], 'plan')

    def test_measurement_mapping_with_routing(self):
        from qiskit.providers.fake_provider import GenericBackendV2
        from qiskit import transpile
        from qiskit_aer import AerSimulator
        qc = QuantumCircuit(3)
        qc.x(0)
        qc.cx(0, 2)
        qo._add_measurements(qc)
        backend = GenericBackendV2(3, coupling_map=[[0, 1], [1, 0], [1, 2], [2, 1]], seed=2026)
        isa = transpile(qc, backend, initial_layout=[2, 1, 0], seed_transpiler=2026)
        self.assertGreater(sum(inst.operation.num_qubits == 2 for inst in isa.data), 1)
        counts = AerSimulator().run(isa, shots=16, seed_simulator=2026).result().get_counts()
        self.assertEqual(counts, {'101': 16})
        self.assertEqual(qo.decode_key(next(iter(counts)), 3), [1, 0, 1])


if __name__ == '__main__':
    unittest.main()
