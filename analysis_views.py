"""Presentation tables derived from frozen results; no new optimizations."""

OUTCOME_CATEGORIES=['Optim fezabil','Fezabil suboptim','Nefezabil']
OUTCOME_COLORS=['#3B82F6','#10B981','#EF4444']


def plan_probability_histogram(result,backend='ideal',classical=False,limit=64):
    """Empirical quantum samples vs the actual deterministic classical output.

    Zero-height reference bins share original decision order. No classical shots
    or arbitrary uniform sampling over tied solutions are invented.
    """
    sample=result['samples'][backend]
    classical_plan=result['classical']
    by_key={p.get('full_bitstring',p['bitstring']):p for p in sample['distribution']}
    chosen_key=classical_plan.get('full_bitstring',classical_plan['bitstring'])
    by_key.setdefault(chosen_key,classical_plan)
    keys=list(by_key)
    if limit is not None and len(keys)>limit:
        keys=sorted(keys,key=lambda k:(-by_key[k].get('probability',0),k))[:limit]
        if chosen_key not in keys: keys[-1]=chosen_key
    rows=[]
    for key in sorted(keys):
        plan=by_key[key]
        category=2 if not plan['valid'] else 0 if plan['valoare_totala']==classical_plan['valoare_totala'] else 1
        rows.append({'Plan':key or '∅','Probabilitate':float(key==chosen_key) if classical else plan.get('probability',0.),
                     'Categorie':OUTCOME_CATEGORIES[category],
                     'Măsurări':None if classical else plan.get('count',0),
                     'Cost':plan['cost_total'],'Scor':plan['valoare_totala'],'Energie':plan['energie'],
                     'Rute':', '.join(map(str,plan['ids_rute'])) or 'Niciuna'})
    return rows


def outcome_histogram(result,backend='ideal',classical=False):
    """Disjoint outcome categories; classical counts are states, quantum counts are shots."""
    if classical:
        optimal=len(result['classical_optima'])
        valid=result['feasible_plan_count']
        counts=[optimal,valid-optimal,result['plan_count']-valid]
    else:
        counts=[0,0,0]
        for plan in result['samples'][backend]['distribution']:
            category=2 if not plan['valid'] else 0 if plan['valoare_totala']==result['classical']['valoare_totala'] else 1
            counts[category]+=plan['count']
    total=sum(counts)
    return [{'Rezultat':name,'Număr':count,'Proporție':count/total if total else 0}
            for name,count in zip(OUTCOME_CATEGORIES,counts)]


def probability_rows(result):
    rows=[{'Source':mode+' finite-shot estimate','Feasible':s['p_feasible'],
           'Infeasible':s['over_budget_rate'],'Optimal feasible':s['p_optimal_feasible'],
           'Model minimum':s['p_model_minimum']} for mode,s in result['samples'].items()]
    exact=result.get('exact_ideal_statistics')
    if exact is None: return rows  # historical schema remains exportable
    rows.append({'Source':'exact ideal statevector' if result['routes'] else 'exact empty plan',
                 'Feasible':exact['p_feasible'],'Infeasible':exact['over_budget_rate'],
                 'Optimal feasible':exact['p_optimal_feasible'],'Model minimum':exact['p_model_minimum']})
    if not result['routes']: rows=rows[-1:]
    return rows


def score_rows(result):
    rows=[{'Method':'Exact classical','Score':result['classical']['valoare_totala'],
           'Cost':result['classical']['cost_total']}]
    for mode,s in result['samples'].items():
        best=s['best_feasible']
        rows.append({'Method':mode+' best observed feasible' if result['routes'] else 'deterministic empty plan',
                     'Score':best['valoare_totala'] if best else None,'Cost':best['cost_total'] if best else None})
    return rows


def resource_rows(result):
    return [{'Backend':mode,'Compiled depth':s['adancime_circuit'],
             'Two-qubit gates':s['porti_doi_qubiti'],'Shots':s.get('shots',0)}
            for mode,s in result['resources'].items()]


def distribution_rows(before,after):
    """Align probabilities by full original bits only if original order matches."""
    same=before['decision_map']['original_ids']==after['decision_map']['original_ids']
    rows=[]
    for name,result in [('baseline',before),('disrupted',after)]:
        for row in result['samples']['ideal']['distribution']:
            key=row['full_bitstring'] or '(empty)'
            if not same: key=f"{result['decision_map']['original_ids']}: {key}"
            rows.append({'Original plan':key,'Scenario':name,'Probability':row['probability']})
    return rows
