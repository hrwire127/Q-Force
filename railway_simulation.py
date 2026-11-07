"""Ceas virtual și jurnal determinist pentru demonstrația feroviară sintetică."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from random import Random
from typing import Any

SPEEDS = (0.5, 1.0, 2.0, 5.0)
DURATION = 720.0


@dataclass(frozen=True)
class NetworkState:
    selected_ids: tuple[int, ...] = ()
    blocked_ids: tuple[int, ...] = ()
    budget: int = 7


@dataclass(frozen=True)
class SimulationEvent:
    event_id: str
    timestamp: float
    event_type: str
    description: str
    route_id: int | None = None
    severity: str = "INFO"
    data: dict[str, Any] = field(default_factory=dict)


def state_at_time(initial_state: NetworkState, events: tuple[SimulationEvent, ...] | list[SimulationEvent],
                  timestamp: float) -> NetworkState:
    """Reconstituie pur starea; evenimentele de la același timp urmează ordinea jurnalului."""
    if timestamp < 0:
        raise ValueError("Timpul virtual nu poate fi negativ.")
    selected = set(initial_state.selected_ids)
    blocked = set(initial_state.blocked_ids)
    budget = initial_state.budget
    for event in sorted(enumerate(events), key=lambda pair: (pair[1].timestamp, pair[0])):
        item = event[1]
        if item.timestamp > timestamp:
            break
        if item.event_type == "ROUTE_BLOCKED" and item.route_id is not None:
            blocked.add(item.route_id)
        elif item.event_type == "ROUTE_RESTORED" and item.route_id is not None:
            blocked.discard(item.route_id)
        elif item.event_type == "NETWORK_UPDATED":
            if "selected_ids" in item.data:
                selected = set(item.data["selected_ids"])
            if "blocked_ids" in item.data:
                blocked = set(item.data["blocked_ids"])
            if "budget" in item.data:
                budget = item.data["budget"]
    return NetworkState(tuple(sorted(selected)), tuple(sorted(blocked)), budget)


def demo_events(seed: int, route_ids: tuple[int, ...], duration: float = DURATION) -> tuple[SimulationEvent, ...]:
    if not route_ids:
        raise ValueError("Este necesară cel puțin o rută pentru demonstrație.")
    route_id = Random(seed).choice(route_ids)
    return (
        SimulationEvent("SYS-000", 0, "SIMULATION_STARTED", "Simulare sintetică pornită"),
        SimulationEvent("NET-001", 180, "NETWORK_UPDATED", "Rețea operațională"),
        SimulationEvent("INC-001", 300, "ROUTE_BLOCKED", f"Blocaj simulat pe ruta {route_id}", route_id, "HIGH"),
        SimulationEvent("REC-001", 420, "SCENARIO_RECALCULATED", "Indicatorii planului au fost actualizați"),
        SimulationEvent("RES-001", 600, "ROUTE_RESTORED", f"Ruta {route_id} a fost restabilită", route_id),
        SimulationEvent("SYS-999", duration, "SIMULATION_COMPLETED", "Demonstrație încheiată"),
    )


@dataclass
class SimulationEngine:
    initial_state: NetworkState
    events: list[SimulationEvent]
    duration: float = DURATION
    position: float = 0.0
    speed: float = 1.0
    running: bool = False
    last_wall: float | None = None
    next_id: int = 2

    @classmethod
    def create(cls, initial_state: NetworkState, route_ids: tuple[int, ...], seed: int = 2026) -> "SimulationEngine":
        return cls(initial_state, list(demo_events(seed, route_ids)))

    def start(self, wall_time: float) -> None:
        self.position = 0.0
        self.running = True
        self.last_wall = wall_time

    def pause(self, wall_time: float) -> None:
        self.advance(wall_time)
        self.running = False
        self.last_wall = None

    def resume(self, wall_time: float) -> None:
        if self.position >= self.duration:
            self.position = 0.0
        self.running = True
        self.last_wall = wall_time

    def advance(self, wall_time: float) -> float:
        if self.running:
            if self.last_wall is not None:
                self.position = min(self.duration, self.position + max(0.0, wall_time - self.last_wall) * self.speed)
            self.last_wall = wall_time
            if self.position >= self.duration:
                self.running = False
                self.last_wall = None
        return self.position

    def seek(self, timestamp: float, wall_time: float | None = None) -> None:
        self.position = max(0.0, min(self.duration, float(timestamp)))
        self.last_wall = wall_time if self.running else None

    def replay(self, wall_time: float) -> None:
        self.position = 0.0
        self.running = True
        self.last_wall = wall_time

    def reset(self) -> None:
        self.position = 0.0
        self.running = False
        self.last_wall = None
        self.events = [event for event in self.events if event.event_id in
                       {"SYS-000", "NET-001", "INC-001", "REC-001", "RES-001", "SYS-999"}]
        self.next_id = 2

    def set_speed(self, speed: float, wall_time: float) -> None:
        if speed not in SPEEDS:
            raise ValueError("Viteză de simulare invalidă.")
        self.advance(wall_time)
        self.speed = speed

    def add_event(self, event_type: str, description: str, *, route_id: int | None = None,
                  severity: str = "INFO", data: dict[str, Any] | None = None) -> SimulationEvent:
        event = SimulationEvent(f"USR-{self.next_id:03d}", self.position, event_type,
                                description, route_id, severity, dict(data or {}))
        self.next_id += 1
        self.events.append(event)
        return event

    def state(self) -> NetworkState:
        return state_at_time(self.initial_state, self.events, self.position)

    def snapshot(self) -> NetworkState:
        return replace(self.state())
