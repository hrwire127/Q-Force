from railway_data import ROUTES
from railway_scenarios import block_route, compare_states, compare_times, restore_route
from railway_simulation import NetworkState, SimulationEngine


def test_emergency_restore_and_original_snapshot():
    initial = NetworkState((0, 6), (), 7)
    engine = SimulationEngine.create(initial, (6,))
    block_route(engine, 6, {r["id"] for r in ROUTES})
    block_route(engine, 6, {r["id"] for r in ROUTES})
    assert len([e for e in engine.events if e.event_id.startswith("USR-")]) == 1
    after = engine.snapshot()
    assert initial.blocked_ids == ()
    assert after.blocked_ids == (6,)
    comparison = compare_states(ROUTES, initial, after)
    assert comparison["cost_delta"] == -4
    assert comparison["benefit_delta"] == -9
    assert comparison["removed_ids"] == [6]
    assert comparison["new_blocked_ids"] == [6]
    restore_route(engine, 6, {r["id"] for r in ROUTES})
    assert engine.state() == initial
    engine.reset()
    assert engine.state() == initial


def test_snapshot_comparison_uses_event_log():
    engine = SimulationEngine.create(NetworkState((6,), (), 7), (6,))
    comparison = compare_times(ROUTES, engine, 0, 350)
    assert comparison["before"]["cost"] == 4
    assert comparison["after"]["cost"] == 0
    assert comparison["removed_ids"] == [6]
