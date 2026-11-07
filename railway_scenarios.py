"""Incidente și comparații de plan independente de interfața Streamlit."""

from __future__ import annotations

from railway_map import calculeaza_plan
from railway_simulation import NetworkState, SimulationEngine, state_at_time


def block_route(engine: SimulationEngine, route_id: int, valid_ids: set[int]) -> None:
    if route_id not in valid_ids:
        raise ValueError(f"Ruta {route_id} nu există.")
    if route_id not in engine.state().blocked_ids:
        engine.add_event("ROUTE_BLOCKED", f"Incident simulat pe ruta {route_id}",
                         route_id=route_id, severity="HIGH")


def restore_route(engine: SimulationEngine, route_id: int, valid_ids: set[int]) -> None:
    if route_id not in valid_ids:
        raise ValueError(f"Ruta {route_id} nu există.")
    if route_id in engine.state().blocked_ids:
        engine.add_event("ROUTE_RESTORED", f"Ruta {route_id} a fost restabilită", route_id=route_id)


def compare_states(routes, before: NetworkState, after: NetworkState) -> dict:
    first = calculeaza_plan(routes, before.selected_ids, before.blocked_ids, before.budget)
    second = calculeaza_plan(routes, after.selected_ids, after.blocked_ids, after.budget)
    active_before = set(first["active_ids"])
    active_after = set(second["active_ids"])
    return {"before": first, "after": second,
            "cost_delta": second["cost"] - first["cost"],
            "benefit_delta": second["beneficiu"] - first["beneficiu"],
            "added_ids": sorted(active_after - active_before),
            "removed_ids": sorted(active_before - active_after),
            "new_blocked_ids": sorted(set(after.blocked_ids) - set(before.blocked_ids))}


def compare_times(routes, engine: SimulationEngine, before_time: float, after_time: float) -> dict:
    return compare_states(routes,
                          state_at_time(engine.initial_state, engine.events, before_time),
                          state_at_time(engine.initial_state, engine.events, after_time))
