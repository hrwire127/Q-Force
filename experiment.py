"""One JSON snapshot for UI, maps, statistics and exports."""
from copy import deepcopy
from datetime import datetime, timezone
from importlib.metadata import version
from itertools import product
import json
from math import isclose
from time import perf_counter
import quantum_optimizer as qo


def references(routes, budget, penalty):
    model = qo.construct_qubo(routes, budget, penalty)  # validates before enumeration
    if len(routes) > 10:
        raise ValueError('Interactive experiments support at most 10 decisions.')
    plans = [qo.analyse_plan(bits, routes, budget, penalty)
             for bits in product((0, 1), repeat=len(routes))]
    valid = [p for p in plans if p['valid']]
    classical = min(valid, key=lambda p: (-p['valoare_totala'], p['cost_total'], p['bitstring']))
    minimum = min(plans, key=lambda p: (p['energie'], p['bitstring']))
    return plans, classical, minimum


def summarize(counts, plans):
    n = len(plans[0]['bits'])
    by_key = {p['bitstring']: p for p in plans}
    total = sum(counts.values())
    if total <= 0 or any(type(c) is not int or c < 0 for c in counts.values()):
        raise ValueError('Expected positive measurement total and nonnegative integer counts.')
    rows = []
    for key, count in counts.items():
        qo.decode_key(key, n)
        if count:
            rows.append(dict(by_key[key], count=count, probability=count/total))
    rows.sort(key=lambda r: (-r['count'], r['bitstring']))
    feasible = [p for p in rows if p['valid']]
    target = max(p['valoare_totala'] for p in plans if p['valid'])
    minimum = min(p['energie'] for p in plans)
    return dict(distribution=rows, most_frequent=rows[0],
        best_feasible=min(feasible, key=lambda r: (-r['valoare_totala'], r['cost_total'], r['bitstring']), default=None),
        p_feasible=sum(r['probability'] for r in feasible),
        p_optimal_feasible=sum(r['probability'] for r in feasible if r['valoare_totala']==target),
        p_model_minimum=sum(r['probability'] for r in rows if isclose(r['energie'], minimum, abs_tol=1e-9)),
        over_budget_rate=sum(r['probability'] for r in rows if not r['valid']),
        mean_true_score=sum(r['probability']*r['valoare_totala'] for r in rows),
        expected_energy=sum(r['probability']*r['energie'] for r in rows))


def run_experiment(routes, budget=7, penalty=.7, p=1, shots=2048, seed=2026,
                   maxiter=30, restarts=1, mode='ideal'):
    routes = deepcopy(routes)
    limits = {'budget':(budget,0,100), 'p':(p,1,3), 'shots':(shots,1,8192),
              'maxiter':(maxiter,5,100), 'restarts':(restarts,1,4), 'seed':(seed,0,2**32-1)}
    for name,(value,low,high) in limits.items():
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f'{name} must be an integer in [{low}, {high}].')
    if mode not in ('ideal','compare'):
        raise ValueError('Select ideal or compare (ideal plus synthetic noisy).')
    if mode=='compare' and len(routes)>8:
        raise ValueError('Noisy comparison supports at most 8 decisions.')
    started = perf_counter()
    plans, classical, minimum = references(routes,budget,penalty)
    q = qo.optimizeaza_qaoa(routes,budget,penalty,p=p,shots=shots,seed=seed,maxiter=maxiter,restarts=restarts)
    samples = {'ideal': summarize(q['counts'],plans)}
    resources = {'ideal':q['statistici']}
    if mode=='compare':
        qubo = qo.construct_qubo(routes,budget,penalty)
        circuit, params = qo.parameterized_qaoa(qubo,p)
        bound = circuit.assign_parameters(dict(zip(params,q['unghiuri_optime'])))
        counts, resource = qo._sample_counts(bound,shots,seed,'noisy')
        samples['noisy'] = summarize(counts,plans)
        resources['noisy'] = resource
    result = dict(created_utc=datetime.now(timezone.utc).isoformat(), routes=routes,
        config=dict(budget=budget,penalty=penalty,p=p,shots=shots,seed=seed,maxiter=maxiter,
                    restarts=restarts,mode=mode,optimizer='COBYLA',objective='additive construction score'),
        classical=classical, qubo_minimum=minimum, plan_count=len(plans),
        samples=samples, quantum=q, resources=resources, runtime_seconds=perf_counter()-started,
        versions={name:version(name) for name in ('qiskit','qiskit-aer','numpy','scipy','streamlit','plotly')})
    return json.loads(json.dumps(result,allow_nan=False))
