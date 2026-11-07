import pytest

from railway_simulation import (NetworkState, SimulationEngine, SimulationEvent,
                                demo_events, state_at_time)


def test_start_pause_resume_speed_and_reset():
    engine = SimulationEngine.create(NetworkState((0, 6), (), 7), (0, 6), seed=42)
    engine.start(100.0)
    assert engine.advance(110.0) == 10
    engine.pause(112.0)
    assert engine.advance(150.0) == 12
    engine.set_speed(5.0, 150.0)
    engine.resume(200.0)
    assert engine.advance(202.0) == 22
    engine.reset()
    assert engine.position == 0 and not engine.running
    assert engine.state() == engine.initial_state


def test_timeline_rewind_replay_deterministic_and_no_duplicates():
    initial = NetworkState((0, 6), (), 7)
    engine = SimulationEngine.create(initial, (6,), seed=2026)
    original = tuple(engine.events)
    assert demo_events(2026, (6,)) == original
    assert state_at_time(initial, original, 299).blocked_ids == ()
    assert state_at_time(initial, original, 300).blocked_ids == (6,)
    assert state_at_time(initial, original, 600).blocked_ids == ()
    engine.seek(320)
    assert engine.state().blocked_ids == (6,)
    engine.seek(100)
    assert engine.state() == initial
    engine.replay(500)
    assert engine.position == 0 and engine.running
    assert tuple(engine.events) == original
    assert len({event.event_id for event in engine.events}) == len(engine.events)


def test_same_timestamp_order_and_validation():
    initial = NetworkState((1,), (), 7)
    events = [SimulationEvent("a", 4, "ROUTE_BLOCKED", "Blocare", 1),
              SimulationEvent("b", 4, "ROUTE_RESTORED", "Restabilire", 1)]
    assert state_at_time(initial, events, 4).blocked_ids == ()
    with pytest.raises(ValueError):
        state_at_time(initial, events, -1)
