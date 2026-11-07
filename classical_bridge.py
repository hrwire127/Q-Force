"""Adapt the shared route contract to Sabina's existing classical API.

There is no second optimization engine here. Closed decisions are already
removed by the scenario pipeline; physical IDs are preserved as metadata.
"""
from classical_optimizer import (optimize_routes, analizeaza_planuri, analyze_budgets,
    get_alternative_plans, get_pareto_plans, explain_classical_solution,
    evaluate_plan, evaluate_qaoa_distribution)


def classical_routes(routes):
    return [{'id':r['id'],'nume':' — '.join(r['cities']),
             'cost':r['cost'],'puncte':r['value']} for r in routes]


def optimize_shared_routes(routes,budget):
    return optimize_routes(classical_routes(routes),budget)


def build_analysis(routes,budget,result):
    """Compute Sabina's explanation, alternatives and sensitivity for this run."""
    adapted=classical_routes(routes)
    max_budget=min(100,max(budget+1,sum(r['cost'] for r in routes)))
    return dict(result=result,
        explanation=explain_classical_solution(adapted,budget,result),
        audit=analizeaza_planuri(adapted,budget),
        alternatives=get_alternative_plans(adapted,budget,top_k=3),
        pareto=get_pareto_plans(adapted,budget),
        budget_profile=analyze_budgets(adapted,max_budget),
        decision_ids=[r['id'] for r in routes],
        tie_policy='maximum score, minimum cost, lexicographic input-order bit vector')


def evaluate_shared_distribution(routes,budget,counts):
    return evaluate_qaoa_distribution(classical_routes(routes),budget,counts,bit_order='qiskit')


def evaluate_shared_plan(routes,budget,bits):
    return evaluate_plan(classical_routes(routes),budget,bits)
