"""Exact, budget-constrained route selection for the Streamlit application."""

from __future__ import annotations

from itertools import groupby, product
from math import isclose, isfinite
from numbers import Real
from typing import Mapping, Sequence, TypedDict


class OptimalPlan(TypedDict):
    vector_binar: list[int]
    cost_total: Real
    punctaj_total: Real


class ClassicalResult(OptimalPlan):
    rute_selectate: list[dict[str, object]]
    buget_ramas: Real
    planuri_evaluate: int
    solutii_optime: list[OptimalPlan]


class PlanEvaluation(OptimalPlan):
    respecta_bugetul: bool
    respecta_blocajele: bool
    este_valid: bool


class ClassicalAnalysis(TypedDict):
    planuri_evaluate: int
    planuri_valide: int
    planuri_peste_buget: int
    planuri_cu_rute_blocate: int
    frontiera_pareto: list[OptimalPlan]
    alternative: list[OptimalPlan]


class BudgetPoint(OptimalPlan):
    buget: Real


class BudgetAnalysisPoint(BudgetPoint):
    buget_ramas: Real
    rute_selectate: list[dict[str, object]]
    numar_solutii_optime: int
    castig_marginal: Real
    este_salt_maxim: bool


def _number(value: object, label: str, *, nonnegative: bool = False) -> Real:
    """Validate one finite numeric input without coercing its value."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{label} trebuie să fie un număr finit.")
    try:
        finite = isfinite(value)
    except OverflowError:
        finite = True  # Arbitrarily large integers are finite.
    if not finite:
        raise ValueError(f"{label} trebuie să fie un număr finit.")
    if nonnegative and value < 0:
        raise ValueError(f"{label} nu poate fi negativ.")
    return value


def _validate_routes(
    rute: Sequence[Mapping[str, object]], buget: Real
) -> tuple[list[Mapping[str, object]], list[Real], list[Real], list[bool], Real]:
    """Validate once before enumerating all candidate plans."""
    budget = _number(buget, "Bugetul", nonnegative=True)
    if isinstance(rute, (str, bytes)) or not isinstance(rute, Sequence):
        raise ValueError("Rutele trebuie să fie o listă de dicționare.")

    routes = list(rute)
    costs: list[Real] = []
    scores: list[Real] = []
    blocked: list[bool] = []
    for index, route in enumerate(routes):
        label = f"Ruta {index + 1}"
        if not isinstance(route, Mapping):
            raise ValueError(f"{label} trebuie să fie un dicționar.")
        if not isinstance(route.get("nume"), str) or not route["nume"].strip():
            raise ValueError(f"{label}: «nume» trebuie să fie text nevid.")
        costs.append(_number(route.get("cost"), f"{label}: cost", nonnegative=True))
        scores.append(_number(route.get("puncte"), f"{label}: puncte"))
        is_blocked = route.get("blocata", False)
        if not isinstance(is_blocked, bool):
            raise ValueError(f"{label}: «blocata» trebuie să fie True sau False.")
        blocked.append(is_blocked)

    return routes, costs, scores, blocked, budget


def _evaluate_bits(
    bits: tuple[int, ...], costs: list[Real], scores: list[Real],
    blocked: list[bool], budget: Real
) -> PlanEvaluation:
    cost = sum(costs[i] for i, bit in enumerate(bits) if bit)
    score = sum(scores[i] for i, bit in enumerate(bits) if bit)
    within_budget = cost <= budget
    available = not any(bit and blocked[i] for i, bit in enumerate(bits))
    return {
        "vector_binar": list(bits),
        "cost_total": cost,
        "punctaj_total": score,
        "respecta_bugetul": within_budget,
        "respecta_blocajele": available,
        "este_valid": within_budget and available,
    }


def _all_plans(
    costs: list[Real], scores: list[Real], blocked: list[bool], budget: Real
):
    """Yield all 2**N plans in stable binary-vector order."""
    for bits in product((0, 1), repeat=len(costs)):
        yield _evaluate_bits(bits, costs, scores, blocked, budget)


def _public_plan(plan: PlanEvaluation) -> OptimalPlan:
    return {
        "vector_binar": plan["vector_binar"],
        "cost_total": plan["cost_total"],
        "punctaj_total": plan["punctaj_total"],
    }


def optimize_routes(
    rute: Sequence[Mapping[str, object]], buget: Real
) -> ClassicalResult:
    """Find all highest-score feasible plans and a deterministic main plan.

    Routes require ``nume``, nonnegative ``cost`` and numeric ``puncte``.
    Optional ``blocata=True`` prohibits a route (default False). Bit ``i``
    always refers to input route ``i``. The main plan has minimum cost among
    score ties, then the first vector in binary enumeration order. All 2**N
    vectors are evaluated. Time is O(N * 2**N); space for all optimal ties
    is O(N * 2**N) in the worst case.
    """
    routes, costs, scores, blocked, budget = _validate_routes(rute, buget)
    best_score: Real | None = None
    ties: list[OptimalPlan] = []
    for plan in _all_plans(costs, scores, blocked, budget):
        if not plan["este_valid"]:
            continue
        score = plan["punctaj_total"]
        if best_score is None or score > best_score:
            best_score = score
            ties = []
        if score == best_score:
            ties.append(_public_plan(plan))

    ties.sort(key=lambda plan: plan["cost_total"])  # Stable order breaks equal-cost ties.
    main = ties[0]  # The empty plan is always feasible for a nonnegative budget.
    selected = [dict(route) for route, bit in zip(routes, main["vector_binar"]) if bit]
    return {
        **main,
        "rute_selectate": selected,
        "buget_ramas": budget - main["cost_total"],
        "planuri_evaluate": 2 ** len(routes),
        "solutii_optime": ties,
    }


def optimizeaza_clasic(
    rute: Sequence[Mapping[str, object]], buget: Real
) -> dict[str, object]:
    """Team-facing adapter with the result keys shown in the project brief."""
    result = optimize_routes(rute, buget)
    return {**result, "rute_alese": result["rute_selectate"],
            "puncte_totale": result["punctaj_total"]}


def evalueaza_plan(
    rute: Sequence[Mapping[str, object]], buget: Real, vector_binar: Sequence[int]
) -> PlanEvaluation:
    """Score one QAOA/classical bit vector against the real budget constraint.

    This does not use QUBO energy. A blocked route makes the plan invalid even
    when its cost fits the budget.
    """
    _, costs, scores, blocked, budget = _validate_routes(rute, buget)
    if isinstance(vector_binar, (str, bytes)) or not isinstance(vector_binar, Sequence):
        raise ValueError("Vectorul binar trebuie să fie o secvență de 0 și 1.")
    if len(vector_binar) != len(costs) or any(type(bit) is not int or bit not in (0, 1)
                                                 for bit in vector_binar):
        raise ValueError("Vectorul binar trebuie să conțină câte un bit 0/1 pentru fiecare rută.")
    return _evaluate_bits(tuple(vector_binar), costs, scores, blocked, budget)


def analizeaza_planuri(
    rute: Sequence[Mapping[str, object]], buget: Real, *, limita_alternative: int = 3
) -> ClassicalAnalysis:
    """Return an exact audit, Pareto frontier and best runner-up plans.

    The counters for over-budget and blocked plans may overlap. The Pareto
    frontier keeps one stable representative per nondominated cost/score pair.
    This optional report takes O(N * 2**N log(2**N)) time and
    O(N * 2**N) space; it is intended for small demo instances.
    """
    _, costs, scores, blocked, budget = _validate_routes(rute, buget)
    if type(limita_alternative) is not int or limita_alternative < 0:
        raise ValueError("Limita alternativelor trebuie să fie un întreg nenegativ.")
    plans = list(_all_plans(costs, scores, blocked, budget))
    feasible = [plan for plan in plans if plan["este_valid"]]
    by_cost = sorted(feasible, key=lambda plan: (
        plan["cost_total"], -plan["punctaj_total"], plan["vector_binar"]
    ))
    frontier: list[OptimalPlan] = []
    best_score: Real | None = None
    for plan in by_cost:
        if best_score is None or plan["punctaj_total"] > best_score:
            frontier.append(_public_plan(plan))
            best_score = plan["punctaj_total"]

    maximum = max(plan["punctaj_total"] for plan in feasible)
    runners_up = sorted(
        (plan for plan in feasible if plan["punctaj_total"] < maximum),
        key=lambda plan: (-plan["punctaj_total"], plan["cost_total"], plan["vector_binar"]),
    )[:limita_alternative]
    return {
        "planuri_evaluate": len(plans),
        "planuri_valide": len(feasible),
        "planuri_peste_buget": sum(not plan["respecta_bugetul"] for plan in plans),
        "planuri_cu_rute_blocate": sum(not plan["respecta_blocajele"] for plan in plans),
        "frontiera_pareto": frontier,
        "alternative": [_public_plan(plan) for plan in runners_up],
    }


def profil_bugete(
    rute: Sequence[Mapping[str, object]], bugete: Sequence[Real]
) -> list[BudgetPoint]:
    """Show how the exact optimum changes across chosen budgets.

    The input budget order is preserved. For K budgets, time is
    O(K * N * 2**N), suitable for a short interactive budget sweep.
    """
    if isinstance(bugete, (str, bytes)) or not isinstance(bugete, Sequence):
        raise ValueError("Bugetele trebuie să fie o secvență de numere.")
    _validate_routes(rute, 0)
    profile: list[BudgetPoint] = []
    for buget in bugete:
        result = optimize_routes(rute, buget)
        profile.append({
            "buget": buget,
            "vector_binar": result["vector_binar"],
            "cost_total": result["cost_total"],
            "punctaj_total": result["punctaj_total"],
        })
    return profile


def _with_blocked_routes(
    routes: Sequence[Mapping[str, object]], blocked_routes: Sequence[int | str] | None
) -> list[Mapping[str, object]]:
    """Apply extra blocked route indices or unique names without changing input."""
    validated, _, _, _, _ = _validate_routes(routes, 0)
    if blocked_routes is None:
        return validated
    if isinstance(blocked_routes, (str, bytes)) or not isinstance(blocked_routes, Sequence):
        raise ValueError("Rutele blocate trebuie să fie o listă de indici sau nume.")
    indices: set[int] = set()
    for marker in blocked_routes:
        if type(marker) is int:
            if not 0 <= marker < len(validated):
                raise ValueError(f"Index de rută blocată invalid: {marker}.")
            indices.add(marker)
        elif isinstance(marker, str):
            matches = [i for i, route in enumerate(validated) if route["nume"] == marker]
            if len(matches) != 1:
                raise ValueError(f"Numele rutei blocate trebuie să fie unic și existent: {marker!r}.")
            indices.add(matches[0])
        else:
            raise ValueError("Rutele blocate se identifică prin index sau nume.")
    return [{**route, "blocata": route.get("blocata", False) or i in indices}
            for i, route in enumerate(validated)]


def analyze_budgets(
    routes: Sequence[Mapping[str, object]], max_budget: int,
    blocked_routes: Sequence[int | str] | None = None,
) -> list[BudgetAnalysisPoint]:
    """Exact optimum for every integer budget 0..max_budget, with marginal gains.

    A positive maximum marginal gain is marked ``este_salt_maxim``. Route
    indices in ``blocked_routes`` refer to input/decision order, not physical
    notebook IDs. Time O((max_budget + 1) * N * 2**N).
    """
    if type(max_budget) is not int or max_budget < 0:
        raise ValueError("Bugetul maxim trebuie să fie un întreg nenegativ.")
    active_routes = _with_blocked_routes(routes, blocked_routes)
    rows: list[BudgetAnalysisPoint] = []
    previous_score: Real | None = None
    for budget in range(max_budget + 1):
        result = optimize_routes(active_routes, budget)
        gain = 0 if previous_score is None else result["punctaj_total"] - previous_score
        rows.append({
            "buget": budget,
            "vector_binar": result["vector_binar"],
            "cost_total": result["cost_total"],
            "punctaj_total": result["punctaj_total"],
            "buget_ramas": result["buget_ramas"],
            "rute_selectate": result["rute_selectate"],
            "numar_solutii_optime": len(result["solutii_optime"]),
            "castig_marginal": gain,
            "este_salt_maxim": False,
        })
        previous_score = result["punctaj_total"]
    largest_gain = max(row["castig_marginal"] for row in rows)
    for row in rows:
        row["este_salt_maxim"] = row["buget"] > 0 and largest_gain > 0 and row["castig_marginal"] == largest_gain
    return rows


def _ranked_feasible(
    routes: Sequence[Mapping[str, object]], budget: Real
) -> tuple[list[Mapping[str, object]], list[PlanEvaluation]]:
    validated, costs, scores, blocked, budget = _validate_routes(routes, budget)
    plans = [plan for plan in _all_plans(costs, scores, blocked, budget) if plan["este_valid"]]
    plans.sort(key=lambda plan: (-plan["punctaj_total"], plan["cost_total"], plan["vector_binar"]))
    return validated, plans


def _alternative_row(
    routes: Sequence[Mapping[str, object]], plan: PlanEvaluation,
    budget: Real, optimal_score: Real, reference_cost: Real,
) -> dict[str, object]:
    return {
        **_public_plan(plan),
        "rute_selectate": [dict(route) for route, bit in zip(routes, plan["vector_binar"]) if bit],
        "buget_ramas": budget - plan["cost_total"],
        "pierdere_punctaj": optimal_score - plan["punctaj_total"],
        "economie_cost": reference_cost - plan["cost_total"],
    }


def get_alternative_plans(
    routes: Sequence[Mapping[str, object]], budget: Real, top_k: int = 3,
    blocked_routes: Sequence[int | str] | None = None,
) -> dict[str, object]:
    """Rank distinct feasible plans and identify the best cheaper compromise.

    The ranked list includes optimal ties. All optimal ties are also returned
    separately. Positive ``economie_cost`` means cheaper than the main optimum.
    Time O(N * 2**N log(2**N)); space O(N * 2**N).
    """
    if type(top_k) is not int or top_k < 0:
        raise ValueError("top_k trebuie să fie un întreg nenegativ.")
    active_routes = _with_blocked_routes(routes, blocked_routes)
    validated, ranked = _ranked_feasible(active_routes, budget)
    optimum = optimize_routes(active_routes, budget)
    score = optimum["punctaj_total"]
    cost = optimum["cost_total"]
    to_row = lambda plan: _alternative_row(validated, plan, budget, score, cost)
    cheaper = next((plan for plan in ranked if plan["cost_total"] < cost), None)
    return {
        "planuri": [to_row(plan) for plan in ranked[:top_k]],
        "solutii_optime": [to_row(plan) for plan in ranked if plan["punctaj_total"] == score],
        "alternativa_mai_ieftina": to_row(cheaper) if cheaper is not None else None,
    }


def get_pareto_plans(
    routes: Sequence[Mapping[str, object]], budget: Real,
    blocked_routes: Sequence[int | str] | None = None,
) -> list[dict[str, object]]:
    """Return every feasible plan not strictly dominated on cost and score."""
    active_routes = _with_blocked_routes(routes, blocked_routes)
    validated, plans = _ranked_feasible(active_routes, budget)
    plans.sort(key=lambda plan: (plan["cost_total"], -plan["punctaj_total"], plan["vector_binar"]))
    frontier: list[dict[str, object]] = []
    best_at_lower_cost: Real | None = None
    for _, same_cost in groupby(plans, key=lambda plan: plan["cost_total"]):
        group = list(same_cost)
        best_here = group[0]["punctaj_total"]
        if best_at_lower_cost is None or best_here > best_at_lower_cost:
            frontier.extend({
                **_public_plan(plan),
                "rute_selectate": [dict(route) for route, bit in zip(validated, plan["vector_binar"]) if bit],
                "buget_ramas": budget - plan["cost_total"],
            } for plan in group if plan["punctaj_total"] == best_here)
        if best_at_lower_cost is None or best_here > best_at_lower_cost:
            best_at_lower_cost = best_here
    return frontier


def explain_classical_solution(
    routes: Sequence[Mapping[str, object]], budget: Real,
    result: Mapping[str, object], blocked_routes: Sequence[int | str] | None = None,
) -> dict[str, object]:
    """Explain an exact result using only measured costs, scores and constraints."""
    active_routes = _with_blocked_routes(routes, blocked_routes)
    expected = optimize_routes(active_routes, budget)
    if not isinstance(result, Mapping) or any(result.get(key) != expected[key]
                                               for key in ("vector_binar", "cost_total", "punctaj_total")):
        raise ValueError("Rezultatul furnizat nu corespunde acestor rute și acestui buget.")
    ranked = get_alternative_plans(active_routes, budget, top_k=0)
    cheaper = ranked["alternativa_mai_ieftina"]
    next_result = optimize_routes(active_routes, budget + 1)
    gain = next_result["punctaj_total"] - expected["punctaj_total"]
    names = [route["nume"] for route in expected["rute_selectate"]]
    route_text = ", ".join(names) if names else "nicio rută"
    summary = (
        f"Pentru bugetul {budget} au fost evaluate toate cele "
        f"{expected['planuri_evaluate']} de combinații. Planul selectează {route_text}, "
        f"costă {expected['cost_total']} și oferă {expected['punctaj_total']} puncte; "
        f"rămân {expected['buget_ramas']} unități de buget. Niciun plan valid "
        "nu are punctaj mai mare."
    )
    count = len(expected["solutii_optime"])
    if count > 1:
        summary += f" Există {count} soluții optime la egalitate."
    if cheaper is not None:
        saving = cheaper["economie_cost"]
        loss = cheaper["pierdere_punctaj"]
        summary += (f" O alternativă costă {cheaper['cost_total']} și oferă "
                    f"{cheaper['punctaj_total']} puncte: economisește "
                    f"{saving} {'unitate' if saving == 1 else 'unități'} pentru o pierdere "
                    f"de {loss} {'punct' if loss == 1 else 'puncte'}.")
    summary += (f" Cu o unitate suplimentară de buget, punctajul maxim "
                f"{'crește cu ' + str(gain) + (' punct' if gain == 1 else ' puncte') if gain > 0 else 'nu crește'}.")
    return {
        "rezumat": summary,
        "rute_selectate": names,
        "indicatori": {
            "cost_total": expected["cost_total"],
            "punctaj_total": expected["punctaj_total"],
            "buget_ramas": expected["buget_ramas"],
            "planuri_evaluate": expected["planuri_evaluate"],
            "numar_solutii_optime": count,
            "castig_buget_suplimentar": gain,
        },
        "alternativa_mai_ieftina": cheaper,
    }


def evaluate_plan(
    routes: Sequence[Mapping[str, object]], budget: Real,
    binary_plan: Sequence[int], blocked_routes: Sequence[int | str] | None = None,
) -> dict[str, object]:
    """Compare a bit vector with every feasible classical optimum, not QUBO.

    Score and cost differences are ``candidate - classical reference``; an
    infeasible candidate can therefore have a positive score difference.
    """
    active_routes = _with_blocked_routes(routes, blocked_routes)
    plan = evalueaza_plan(active_routes, budget, binary_plan)
    reference = optimize_routes(active_routes, budget)
    optimal_vectors = {tuple(item["vector_binar"]) for item in reference["solutii_optime"]}
    return {
        **plan,
        "rute_selectate": [dict(route) for route, bit in zip(active_routes, binary_plan) if bit],
        "include_ruta_blocata": not plan["respecta_blocajele"],
        "este_optim_global": plan["este_valid"] and tuple(binary_plan) in optimal_vectors,
        "diferenta_punctaj_fata_de_optim": plan["punctaj_total"] - reference["punctaj_total"],
        "diferenta_cost_fata_de_referinta": plan["cost_total"] - reference["cost_total"],
        "punctaj_optim_clasic": reference["punctaj_total"],
        "numar_solutii_optime": len(optimal_vectors),
    }


def evaluate_qaoa_distribution(
    routes: Sequence[Mapping[str, object]], budget: Real,
    distribution: Mapping[str, Real], *, bit_order: str,
    blocked_routes: Sequence[int | str] | None = None,
) -> dict[str, object]:
    """Assess measured counts or normalized probabilities using true scores.

    ``bit_order='qiskit'`` reverses each displayed key, matching ``decode_key``
    in the project notebook. ``bit_order='route_order'`` uses keys as written.
    Sparse distributions are accepted. Integer values mean counts; otherwise
    values must be finite nonnegative probabilities summing to 1.
    """
    if bit_order not in ("qiskit", "route_order"):
        raise ValueError("bit_order trebuie să fie 'qiskit' sau 'route_order'.")
    active_routes = _with_blocked_routes(routes, blocked_routes)
    _, costs, scores, blocked, budget = _validate_routes(active_routes, budget)
    if not isinstance(distribution, Mapping) or not distribution:
        raise ValueError("Distribuția trebuie să conțină cel puțin un plan.")
    count_format = all(type(weight) is int for weight in distribution.values())
    decoded: list[tuple[PlanEvaluation, Real]] = []
    seen: set[tuple[int, ...]] = set()
    for key, raw_weight in distribution.items():
        if not isinstance(key, str):
            raise ValueError("Cheile distribuției trebuie să fie șiruri binare.")
        compact = key.replace(" ", "")
        if len(compact) != len(costs) or set(compact) - {"0", "1"}:
            raise ValueError(f"Cheie binară invalidă pentru {len(costs)} rute: {key!r}.")
        bits = tuple(int(bit) for bit in (compact[::-1] if bit_order == "qiskit" else compact))
        if bits in seen:
            raise ValueError(f"Plan duplicat în distribuție: {key!r}.")
        seen.add(bits)
        weight = _number(raw_weight, f"Ponderea pentru {key!r}", nonnegative=True)
        decoded.append((_evaluate_bits(bits, costs, scores, blocked, budget), weight))
    total = sum(weight for _, weight in decoded)
    if total <= 0:
        raise ValueError("Distribuția trebuie să aibă masă totală pozitivă.")
    if not count_format and not isclose(total, 1, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError("Probabilitățile trebuie să însumeze 1; pentru numărări folosiți întregi.")
    reference = optimize_routes(active_routes, budget)
    optimal_vectors = {tuple(plan["vector_binar"]) for plan in reference["solutii_optime"]}
    most_frequent = None
    if count_format:
        leader = min(decoded, key=lambda item: (-item[1], item[0]["vector_binar"]))[0]
        most_frequent = {**leader, "este_optim_global": leader["este_valid"]
                         and tuple(leader["vector_binar"]) in optimal_vectors}
    return {
        "format_distributie": "numarari" if count_format else "probabilitati",
        "total_masurari": total if count_format else None,
        "probabilitate_planuri_valide": sum(weight for plan, weight in decoded if plan["este_valid"]) / total,
        "probabilitate_solutii_optime": sum(weight for plan, weight in decoded
                                            if plan["este_valid"] and tuple(plan["vector_binar"]) in optimal_vectors) / total,
        "punctaj_mediu": sum(plan["punctaj_total"] * weight for plan, weight in decoded) / total,
        "cost_mediu": sum(plan["cost_total"] * weight for plan, weight in decoded) / total,
        "cel_mai_frecvent_plan": most_frequent,
    }
