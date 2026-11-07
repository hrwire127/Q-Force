"""Shared, reproducible Quantum Railways experiment pipeline."""
from __future__ import annotations

from itertools import product
from time import perf_counter

from quantum_optimizer import analyse_plan, construct_qubo, optimizeaza_qaoa, qubo_energy


def classical_routes(routes, blocked_ids=()):
    blocked = set(blocked_ids)
    return [{"nume": f"{r['cities'][0]} – {r['cities'][1]}", "cost": r["cost"],
             "puncte": r["value"], "blocata": r["id"] in blocked} for r in routes]


def run_experiment(routes, *, budget=7, penalty=.7, depth=1, shots=2048,
                   seed=2026, maxiter=30, restarts=1, noisy=False, blocked_ids=()):
    """Run exact reference and QAOA over one immutable decision-space snapshot."""
    if not routes or len(routes) > 10:
        raise ValueError("Alege între 1 și 10 rute; simularea locală este limitată intenționat.")
    blocked = set(blocked_ids)
    qroutes = [{**r, "blocata": r["id"] in blocked} for r in routes]
    active = [r for r in qroutes if not r["blocata"]]
    if not active:
        raise ValueError("Cel puțin o rută trebuie să fie disponibilă.")
    from classical_optimizer import optimize_routes
    started = perf_counter()
    classical = optimize_routes(classical_routes(active), budget)
    quantum = optimizeaza_qaoa(active, budget, penalty, p=depth, shots=shots,
                                seed=seed, maxiter=maxiter, restarts=restarts,
                                backend_mode="noisy" if noisy else "ideal")
    qubo = construct_qubo(active, budget, penalty)
    all_plans = [analyse_plan(bits, active, budget, penalty)
                 for bits in product((0, 1), repeat=len(active))]
    model_min = min(all_plans, key=lambda plan: (plan["energie"], plan["bitstring"]))
    counts = quantum["counts"]
    min_probability = sum(counts.get(plan["bitstring"], 0) for plan in all_plans
                          if abs(plan["energie"] - model_min["energie"]) < 1e-9) / shots
    return {"config": {"budget": budget, "penalty": penalty, "depth": depth, "shots": shots,
                        "seed": seed, "maxiter": maxiter, "restarts": restarts, "noisy": noisy,
                        "route_ids": [r["id"] for r in active], "blocked_ids": sorted(blocked)},
            "routes": active, "classical": classical, "quantum": quantum,
            "qubo_minimum": model_min, "qubo": qubo,
            "statistics": {"p_feasible": quantum["rata_planuri_valide"],
                           "p_optimal_feasible": quantum["probabilitate_optim_valid"],
                           "p_model_minimum": min_probability,
                           "over_budget_rate": 1 - quantum["rata_planuri_valide"],
                           "expected_energy": quantum["energie_medie_masurata"],
                           "runtime_seconds": perf_counter() - started}}
