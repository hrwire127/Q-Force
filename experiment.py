"""One JSON snapshot for UI, maps, statistics and exports."""
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
from itertools import product
import json
from math import isclose
from time import perf_counter
from typing import Any, NotRequired, TypedDict
from uuid import uuid4
import quantum_optimizer as qo
from railway_incidents import scenario, connectivity, reconstruct
from classical_bridge import (optimize_shared_routes,build_analysis,
                              evaluate_shared_distribution,evaluate_shared_plan)


@dataclass(frozen=True)
class RailwayScenario:
    """Route list order defines original decisions; IDs preserve physical identity."""
    routes: list[dict[str, Any]]
    incidents: list[dict[str, Any]] = field(default_factory=list)
    time: int = 0


@dataclass(frozen=True)
class SimulationConfig:
    budget: int = 7
    penalty: float = .7
    p: int = 1
    shots: int = 2048
    seed: int = 2026
    maxiter: int = 30
    restarts: int = 1
    mode: str = 'ideal'
    optimizer: str = 'COBYLA'
    optimizer_tol: float = 1e-4
    transpilation_level: int = 1
    objective: str = 'additive construction score'


class ExperimentResult(TypedDict):
    """JSON snapshot contract; numerical models and bit maps belong to this run."""
    experiment_id: str
    scenario_id: str
    created_utc: str
    routes: list[dict[str, Any]]
    original_routes: list[dict[str, Any]]
    scenario: dict[str, Any]
    connectivity: dict[str, Any]
    decision_map: dict[str, list[int]]
    plan_count: int
    feasible_plan_count: int
    config: dict[str, Any]
    classical: dict[str, Any]
    classical_optima: list[dict[str, Any]]
    qubo_minimum: dict[str, Any]
    qubo_minima: list[dict[str, Any]]
    model: dict[str, Any]
    quantum: dict[str, Any]
    samples: dict[str, Any]
    counts_by_backend: dict[str, dict[str, int]]
    exact_ideal_statistics: dict[str, float]
    classical_analysis: dict[str, Any]
    distribution_audits: dict[str, Any]
    sampled_plan_audits: dict[str, Any]
    resources: dict[str, Any]
    versions: dict[str, str]
    reference_method: str
    reference_seconds: float
    runtime_seconds: float
    baseline_snapshot: NotRequired[dict[str, Any]]
    baseline_metadata: NotRequired[dict[str, Any]]
    baseline_comparison: NotRequired[dict[str, Any]]


def run_railway_optimization(scenario_input: RailwayScenario,
                             config: SimulationConfig) -> ExperimentResult:
    """Typed application entry point; reuse the zus engine through one orchestrator."""
    from dataclasses import asdict
    if not isinstance(scenario_input,RailwayScenario) or not isinstance(config,SimulationConfig):
        raise TypeError('Supply RailwayScenario and SimulationConfig instances.')
    options=asdict(config)
    if options.pop('objective')!='additive construction score':
        raise ValueError('Only the documented additive construction objective is supported.')
    return run_experiment(scenario_input.routes,**options,incidents=scenario_input.incidents,
                          scenario_time=scenario_input.time)


def references(routes, budget, penalty):
    if len(routes)>10:
        raise ValueError('Interactive experiments support at most 10 decisions.')
    if not routes:
        plan=dict(bits=[],bitstring='',ids_rute=[],rute=[],cost_total=0,valoare_totala=0,
                  valid=True,energie=float(penalty*budget**2))
        return [plan],plan,plan
    model = qo.construct_qubo(routes, budget, penalty)  # validates before enumeration
    plans = [qo.analyse_plan(bits, routes, budget, penalty)
             for bits in product((0, 1), repeat=len(routes))]
    valid = [p for p in plans if p['valid']]
    exact=optimize_shared_routes(routes,budget)
    classical = next(p for p in valid if p['bits']==exact['vector_binar'])
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
        p_model_minimum=sum(r['probability'] for r in rows if isclose(r['energie'], minimum, rel_tol=0, abs_tol=1e-9)),
        over_budget_rate=sum(r['probability'] for r in rows if not r['valid']),
        mean_true_score=sum(r['probability']*r['valoare_totala'] for r in rows),
        expected_energy=sum(r['probability']*r['energie'] for r in rows))


def run_experiment(routes, budget=7, penalty=.7, p=1, shots=2048, seed=2026,
                   maxiter=30, restarts=1, mode='ideal', incidents=(), scenario_time=0,
                   optimizer='COBYLA', optimizer_tol=1e-4, transpilation_level=1) -> ExperimentResult:
    routes = deepcopy(routes)
    limits = {'budget':(budget,0,100), 'p':(p,1,3), 'shots':(shots,1,8192),
              'maxiter':(maxiter,5,100), 'restarts':(restarts,1,4), 'seed':(seed,0,2**32-1)}
    for name,(value,low,high) in limits.items():
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f'{name} must be an integer in [{low}, {high}].')
    if maxiter<2*p+2:
        raise ValueError('COBYLA needs at least 2*p+2 evaluations per restart for this depth.')
    if mode not in ('ideal','compare'):
        raise ValueError('Select ideal or compare (ideal plus synthetic noisy).')
    if optimizer!='COBYLA':
        raise ValueError('Only COBYLA is currently supported.')
    if type(transpilation_level) is not int or not 0<=transpilation_level<=3:
        raise ValueError('transpilation_level must be an integer in [0,3].')
    optimizer_tol=qo._penalty(optimizer_tol)
    qo._problem(routes,budget,penalty)
    original_routes=deepcopy(routes)
    state=scenario(routes,incidents,scenario_time)
    routes=state['available_routes']
    if mode=='compare' and len(routes)>8:
        raise ValueError('Noisy comparison supports at most 8 decisions.')
    started = perf_counter()
    reference_started=perf_counter()
    plans, classical, minimum = references(routes,budget,penalty)
    sabina_result=optimize_shared_routes(routes,budget)
    if sabina_result['planuri_evaluate']!=len(plans):
        raise RuntimeError('Classical modules disagree on the current decision space.')
    classical_analysis=build_analysis(routes,budget,sabina_result)
    if classical_analysis['audit']['planuri_valide']!=sum(plan['valid'] for plan in plans):
        raise RuntimeError('Classical feasibility audits disagree.')
    reference_seconds=perf_counter()-reference_started
    qubo=qo.construct_qubo(routes,budget,penalty) if routes else {'linear':[], 'quadratic':[], 'offset':float(penalty*budget**2)}
    ising=qo.qubo_to_ising(qubo) if routes else {'h':[], 'J':[], 'constant':float(penalty*budget**2)}
    if routes:
        q = qo.optimizeaza_qaoa(routes,budget,penalty,p=p,shots=shots,seed=seed,maxiter=maxiter,restarts=restarts,
            transpilation_level=transpilation_level,optimizer_tol=optimizer_tol,return_probabilities=True)
        dp=q['referinta_clasica']
        if (dp['valoare_optima'],dp['cost_total'])!=(classical['valoare_totala'],classical['cost_total']):
            raise RuntimeError('Exact enumeration disagrees with the zus DP reference.')
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
    counts_by_backend={'ideal':dict(q['counts'])}
    if mode=='compare' and routes:
        circuit, params = qo.parameterized_qaoa(qubo,p)
        bound = circuit.assign_parameters(dict(zip(params,q['unghiuri_optime'])))
        noisy_started=perf_counter()
        counts, resource = qo._sample_counts(bound,shots,seed,'noisy',optimization_level=transpilation_level)
        samples['noisy'] = summarize(counts,plans)
        resources['noisy'] = dict(resource,shots=shots,sampling_seconds=perf_counter()-noisy_started)
        counts_by_backend['noisy']=counts
    active_ids=[r['id'] for r in routes]; original_ids=[r['id'] for r in original_routes]
    def enrich_classical_tree(node):
        if isinstance(node,dict):
            if 'vector_binar' in node:
                node['full_bits']=reconstruct(node['vector_binar'],active_ids,original_ids)
                node['ids_rute']=[rid for bit,rid in zip(node['vector_binar'],active_ids) if bit]
            for value in node.values(): enrich_classical_tree(value)
        elif isinstance(node,list):
            for value in node: enrich_classical_tree(value)
    enrich_classical_tree(classical_analysis)
    for plan in plans:
        plan['full_bits']=reconstruct(plan['bits'],active_ids,original_ids)
        plan['full_bitstring']=''.join(map(str,reversed(plan['full_bits'])))
    for sample in samples.values():
        for plan in sample['distribution']:
            plan['full_bits']=reconstruct(plan['bits'],active_ids,original_ids)
            plan['full_bitstring']=''.join(map(str,reversed(plan['full_bits'])))
    # Enrich the reused zus result too, so no consumer needs another index convention.
    def full_plan(plan):
        if plan is not None:
            plan['full_bits']=reconstruct(plan['bits'],active_ids,original_ids)
            plan['full_bitstring']=''.join(map(str,reversed(plan['full_bits'])))
    for plan in q.get('top_planuri',[]): full_plan(plan)
    full_plan(q.get('cel_mai_frecvent_plan'))
    if routes:
        dp=q['referinta_clasica']
        dp['full_bits']=reconstruct(qo.decode_key(dp['bitstring'],len(routes)),active_ids,original_ids)
        dp['full_bitstring']=''.join(map(str,reversed(dp['full_bits'])))
    q['full_recommended_bits']=reconstruct(qo.decode_key(q['bitstring_recomandat'],len(routes)),active_ids,original_ids) if routes and q['bitstring_recomandat'] is not None else ([0]*len(original_ids) if not routes else None)
    classical_optima=[plan for plan in plans if plan['valid'] and plan['valoare_totala']==classical['valoare_totala']]
    qubo_minima=[plan for plan in plans if isclose(plan['energie'],minimum['energie'],rel_tol=0,abs_tol=1e-9)]
    exact_probs=q.get('statevector_probabilities') or {'':1.}
    exact_statistics={
        'p_feasible':sum(exact_probs[plan['bitstring']] for plan in plans if plan['valid']),
        'p_optimal_feasible':sum(exact_probs[plan['bitstring']] for plan in classical_optima),
        'p_model_minimum':sum(exact_probs[plan['bitstring']] for plan in qubo_minima),
        'expected_energy':sum(exact_probs[plan['bitstring']]*plan['energie'] for plan in plans),
        'mean_true_score':sum(exact_probs[plan['bitstring']]*plan['valoare_totala'] for plan in plans)}
    exact_statistics['over_budget_rate']=1-exact_statistics['p_feasible']
    distribution_audits={}
    sampled_plan_audits={}
    for backend,counts in counts_by_backend.items():
        if not counts: continue
        audit=evaluate_shared_distribution(routes,budget,counts)
        canonical=samples[backend]
        pairs={'p_feasible':'probabilitate_planuri_valide',
               'p_optimal_feasible':'probabilitate_solutii_optime',
               'mean_true_score':'punctaj_mediu'}
        for field,source in pairs.items():
            if not isclose(canonical[field],audit[source],rel_tol=1e-9,abs_tol=1e-9):
                raise RuntimeError(f'Sabina analysis disagrees with {backend} {field}.')
            canonical[field]=audit[source]
        canonical['mean_construction_cost']=audit['cost_mediu']
        audit['most_frequent_tie_policy']='lexicographic input-order bit vector; the main QAOA panel retains its Qiskit-key tie rule'
        distribution_audits[backend]=audit
        best=canonical['best_feasible']
        sampled_plan_audits[backend]={
            'most_frequent':evaluate_shared_plan(routes,budget,canonical['most_frequent']['bits']),
            'best_feasible':evaluate_shared_plan(routes,budget,best['bits']) if best else None}
    enrich_classical_tree(sampled_plan_audits)
    scenario_id=sha256(json.dumps([original_routes,state['incidents'],scenario_time],sort_keys=True).encode()).hexdigest()[:16]
    result = dict(created_utc=datetime.now(timezone.utc).isoformat(), routes=routes,
        experiment_id=str(uuid4()),scenario_id=scenario_id,
        original_routes=original_routes,scenario=state,connectivity=connectivity(state),
        decision_map={'active_ids':active_ids,'original_ids':original_ids},
        feasible_plan_count=sum(p['valid'] for p in plans),
        config=dict(budget=budget,penalty=penalty,p=p,shots=shots,seed=seed,maxiter=maxiter,
                    restarts=restarts,mode=mode,optimizer=optimizer,optimizer_tol=optimizer_tol,
                    transpilation_level=transpilation_level,objective='additive construction score',
                    scenario_id=scenario_id,selected_route_ids=original_ids,active_route_ids=active_ids,
                    active_incident_ids=[i['incident_id'] for i in state['active_incidents']]),
        classical=classical, qubo_minimum=minimum, plan_count=len(plans),
        classical_optima=classical_optima,qubo_minima=qubo_minima,
        classical_analysis=classical_analysis,distribution_audits=distribution_audits,
        sampled_plan_audits=sampled_plan_audits,
        model={'energy_formula':'-value + penalty * (construction_cost - budget)^2',
               'qubo':{k:v.tolist() if hasattr(v,'tolist') else v for k,v in qubo.items()},
               'ising':{k:v.tolist() if hasattr(v,'tolist') else v for k,v in ising.items()}},
        exact_ideal_statistics=exact_statistics,counts_by_backend=counts_by_backend,
        reference_method='Sabina exact enumeration + QUBO audit; cross-checked with zus exact DP' if routes else 'Sabina exact deterministic empty plan',reference_seconds=reference_seconds,
        samples=samples, quantum=q, resources=resources, runtime_seconds=perf_counter()-started,
        versions={name:version(name) for name in ('qiskit','qiskit-aer','numpy','scipy','streamlit','plotly')})
    return json.loads(json.dumps(result,allow_nan=False))
