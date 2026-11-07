"""One JSON snapshot for UI, maps, statistics and exports."""
from copy import deepcopy
from datetime import datetime, timezone
from importlib.metadata import version
from itertools import product
import json
from math import isclose
from time import perf_counter
import quantum_optimizer as qo
from railway_incidents import scenario, connectivity, reconstruct


def references(routes, budget, penalty):
    if not routes:
        plan=dict(bits=[],bitstring='',ids_rute=[],rute=[],cost_total=0,valoare_totala=0,
                  valid=True,energie=float(penalty*budget**2))
        return [plan],plan,plan
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
        if n:
            qo.decode_key(key, n)
        elif key != '':
            raise ValueError('The empty decision space has only the empty plan.')
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
                   maxiter=30, restarts=1, mode='ideal', incidents=(), scenario_time=0):
    routes = deepcopy(routes)
    limits = {'budget':(budget,0,100), 'p':(p,1,3), 'shots':(shots,1,8192),
              'maxiter':(maxiter,5,100), 'restarts':(restarts,1,4), 'seed':(seed,0,2**32-1)}
    for name,(value,low,high) in limits.items():
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f'{name} must be an integer in [{low}, {high}].')
    if mode not in ('ideal','compare'):
        raise ValueError('Select ideal or compare (ideal plus synthetic noisy).')
    qo._problem(routes,budget,penalty)
    original_routes=deepcopy(routes)
    state=scenario(routes,incidents,scenario_time)
    routes=state['available_routes']
    if mode=='compare' and len(routes)>8:
        raise ValueError('Noisy comparison supports at most 8 decisions.')
    started = perf_counter()
    plans, classical, minimum = references(routes,budget,penalty)
    if routes:
        q = qo.optimizeaza_qaoa(routes,budget,penalty,p=p,shots=shots,seed=seed,maxiter=maxiter,restarts=restarts)
    else:
        q=dict(status='no_available_routes',counts={},unghiuri_optime=[],
               optimizare={'history':[]},statistici={'numar_qubiti':0,'qaoa_depth':0,
               'adancime_circuit':0,'porti_doi_qubiti':0,'backend':'deterministic_empty_plan',
               'shots':0,'requested_shots':shots},ids_rute_recomandate=[],bitstring_recomandat='',
               valoare_totala=0,cost_total=0)
    samples = {'ideal': summarize(q['counts'] if routes else {'':1},plans)}
    if not routes:
        # Unit probability mass is mathematical, not a fabricated measurement.
        samples['ideal']['distribution'][0]['count']=0
    resources = {'ideal':q['statistici']}
    if mode=='compare' and routes:
        qubo = qo.construct_qubo(routes,budget,penalty)
        circuit, params = qo.parameterized_qaoa(qubo,p)
        bound = circuit.assign_parameters(dict(zip(params,q['unghiuri_optime'])))
        counts, resource = qo._sample_counts(bound,shots,seed,'noisy')
        samples['noisy'] = summarize(counts,plans)
        resources['noisy'] = resource
    active_ids=[r['id'] for r in routes]; original_ids=[r['id'] for r in original_routes]
    for plan in plans:
        plan['full_bits']=reconstruct(plan['bits'],active_ids,original_ids)
        plan['full_bitstring']=''.join(map(str,reversed(plan['full_bits'])))
    for sample in samples.values():
        for plan in sample['distribution']:
            plan['full_bits']=reconstruct(plan['bits'],active_ids,original_ids)
            plan['full_bitstring']=''.join(map(str,reversed(plan['full_bits'])))
    result = dict(created_utc=datetime.now(timezone.utc).isoformat(), routes=routes,
        original_routes=original_routes,scenario=state,connectivity=connectivity(state),
        decision_map={'active_ids':active_ids,'original_ids':original_ids},
        feasible_plan_count=sum(p['valid'] for p in plans),
        config=dict(budget=budget,penalty=penalty,p=p,shots=shots,seed=seed,maxiter=maxiter,
                    restarts=restarts,mode=mode,optimizer='COBYLA',objective='additive construction score'),
        classical=classical, qubo_minimum=minimum, plan_count=len(plans),
        samples=samples, quantum=q, resources=resources, runtime_seconds=perf_counter()-started,
        versions={name:version(name) for name in ('qiskit','qiskit-aer','numpy','scipy','streamlit','plotly')})
    return json.loads(json.dumps(result,allow_nan=False))
