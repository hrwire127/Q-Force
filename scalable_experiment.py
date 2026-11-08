"""Large-selection snapshots using exact cost DP and adaptive QAOA simulation."""
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
import json
from time import perf_counter
from uuid import uuid4

import quantum_optimizer as qo
from railway_incidents import connectivity, reconstruct
from scalable_reference import CostReference


def run_large_experiment(original_routes,state,config):
    started=perf_counter()
    routes=state['available_routes']
    budget,penalty=config['budget'],config['penalty']
    ref=CostReference(routes,budget,penalty)
    analysis=ref.analysis()
    reference_seconds=perf_counter()-started
    qubo=qo.construct_qubo(routes,budget,penalty)
    ising=qo.qubo_to_ising(qubo)
    q=qo.optimizeaza_qaoa(routes,budget,penalty,p=config['p'],shots=config['shots'],seed=config['seed'],
        maxiter=config['maxiter'],restarts=config['restarts'],optimizer_tol=config['optimizer_tol'],
        transpilation_level=config['transpilation_level'],return_probabilities=False)
    if (q['referinta_clasica']['valoare_optima'],q['referinta_clasica']['cost_total']) != (
            ref.classical['valoare_totala'],ref.classical['cost_total']):
        raise RuntimeError('Independent exact DP references disagree.')
    samples={'ideal':ref.summarize(q['counts'])}
    counts_by_backend={'ideal':dict(q['counts'])}
    resources={'ideal':q['statistici']}
    if config['mode']=='compare':
        circuit,parameters=qo.parameterized_qaoa(qubo,config['p'])
        bound=circuit.assign_parameters(dict(zip(parameters,q['unghiuri_optime'])))
        before=perf_counter()
        counts,resource=qo._sample_counts(bound,config['shots'],config['seed'],'noisy',
                                        optimization_level=config['transpilation_level'])
        samples['noisy']=ref.summarize(counts)
        counts_by_backend['noisy']=counts
        resources['noisy']=dict(resource,shots=config['shots'],sampling_seconds=perf_counter()-before)
    active_ids=[r['id'] for r in routes]
    original_ids=[r['id'] for r in original_routes]
    scenario_id=sha256(json.dumps([original_routes,state['incidents'],state['time']],sort_keys=True).encode()).hexdigest()[:16]
    audits={backend:ref.audit_distribution(counts) for backend,counts in counts_by_backend.items()}
    sampled_audits={backend:dict(most_frequent=ref.audit_plan(sample['most_frequent']['bits']),
        best_feasible=ref.audit_plan(sample['best_feasible']['bits']) if sample['best_feasible'] else None)
        for backend,sample in samples.items()}
    result=dict(created_utc=datetime.now(timezone.utc).isoformat(),experiment_id=str(uuid4()),scenario_id=scenario_id,
        routes=routes,original_routes=original_routes,scenario=state,connectivity=connectivity(state),
        decision_map=dict(active_ids=active_ids,original_ids=original_ids),
        feasible_plan_count=ref.feasible_count,plan_count=ref.plan_count,
        classical=ref.classical,qubo_minimum=ref.minimum,classical_optima=ref.optima,qubo_minima=ref.minima,
        classical_optimal_plan_count=ref.optimal_count,qubo_minimum_plan_count=ref.minimum_count,
        reference_details=dict(method='exact cost dynamic programming',states_evaluated=ref.states_evaluated,
            representatives_limit=ref.REPRESENTATIVES,optimal_representatives_complete=len(ref.optima)==ref.optimal_count,
            minimum_representatives_complete=len(ref.minima)==ref.minimum_count),
        classical_analysis=analysis,distribution_audits=audits,sampled_plan_audits=sampled_audits,
        model=dict(energy_formula='-value + penalty * (construction_cost - budget)^2',
            qubo={k:v.tolist() if hasattr(v,'tolist') else v for k,v in qubo.items()},
            ising={k:v.tolist() if hasattr(v,'tolist') else v for k,v in ising.items()}),
        exact_ideal_statistics=q.get('exact_ideal_statistics'),counts_by_backend=counts_by_backend,
        reference_method='Exact cost dynamic programming; cross-checked with independent zus DP',
        reference_seconds=reference_seconds,samples=samples,quantum=q,resources=resources,
        config=dict(config,objective='additive construction score',scenario_id=scenario_id,
                    selected_route_ids=original_ids,active_route_ids=active_ids,
                    active_incident_ids=[i['incident_id'] for i in state['active_incidents']]),
        versions={name:version(name) for name in ('qiskit','qiskit-aer','numpy','scipy','streamlit','plotly')})
    # One consistent mapping for every sampled/reference/analysis plan, including
    # routes removed by incidents. Never expand the complete binary plan space.
    seen=set()
    def enrich(node):
        if isinstance(node,dict):
            if id(node) in seen:return
            seen.add(id(node))
            bits=node.get('bits',node.get('vector_binar'))
            if bits is not None:
                node['full_bits']=reconstruct(bits,active_ids,original_ids)
                node['full_bitstring']=''.join(map(str,reversed(node['full_bits'])))
                node.setdefault('ids_rute',[rid for rid,bit in zip(active_ids,bits) if bit])
            for value in node.values():enrich(value)
        elif isinstance(node,list):
            for value in node:enrich(value)
    enrich(result)
    dp=q['referinta_clasica']
    dp['full_bits']=reconstruct(qo.decode_key(dp['bitstring'],len(routes)),active_ids,original_ids)
    dp['full_bitstring']=''.join(map(str,reversed(dp['full_bits'])))
    q['full_recommended_bits']=reconstruct(qo.decode_key(q['bitstring_recomandat'],len(routes)),active_ids,original_ids) if q['bitstring_recomandat'] else None
    result['runtime_seconds']=perf_counter()-started
    return json.loads(json.dumps(result,allow_nan=False))
