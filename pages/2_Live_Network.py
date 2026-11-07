"""Q-FORCE 2.0 — centru de control pentru o rețea feroviară fictivă."""
from __future__ import annotations

import csv
import io
import json
import time
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from railway_data import DEFAULT_BUDGET, DEMO_IDS, POSITIONS, ROUTES
from railway_map import calculeaza_plan, deseneaza_harta, recomandare_din_masuratori, starea_rutei
from railway_scenarios import block_route, compare_states, restore_route
from railway_simulation import DURATION, SPEEDS, NetworkState, SimulationEngine, state_at_time

st.set_page_config(page_title="Q-FORCE | Quantum Railways 2.0", page_icon="🚆", layout="wide")
st.markdown("""<style>
.stApp,[data-testid="stSidebar"]{background:#0B1220;color:#F8FAFC}
[data-testid="stSidebar"]{border-right:1px solid #263A55}
.block-container{max-width:1600px;padding-top:1.4rem}
h1,h2,h3{color:#F8FAFC;letter-spacing:-.025em}
.hero{background:linear-gradient(115deg,#111C2E,#142B41 62%,#0B3037);border:1px solid #284761;
border-radius:18px;padding:1.15rem 1.5rem;margin-bottom:1rem;box-shadow:0 12px 38px #02071366}
.eyebrow{color:#38BDF8;font-size:.8rem;font-weight:800;letter-spacing:.16em}
.hero h1{margin:.1rem 0;font-size:clamp(1.7rem,2.6vw,2.6rem)}.hero p{color:#94A3B8;margin:.2rem 0}
.pill{display:inline-block;border:1px solid #10B981;border-radius:30px;padding:.3rem .7rem;
background:#063b33;color:#86efca;font-size:.78rem;font-weight:800;letter-spacing:.08em}
.paused{border-color:#F59E0B;background:#433013;color:#fcd34d}
.no-motion{animation:none!important}
[data-testid="stMetric"]{background:#111C2E;border:1px solid #263A55;border-radius:14px;
padding:.7rem 1rem;min-height:104px;box-shadow:0 6px 24px #02071344}
[data-testid="stMetricLabel"]{color:#94A3B8}[data-testid="stMetricValue"]{color:#F8FAFC}
[data-testid="stPlotlyChart"]{background:#111C2E;border:1px solid #263A55;border-radius:16px;overflow:hidden}
.event{border-left:3px solid #38BDF8;background:#111C2E;border-radius:0 10px 10px 0;
padding:.5rem .8rem;margin:.3rem 0;color:#cbd5e1}.incident{border-color:#EF4444;background:#381d2a}
.timeline-title{color:#38BDF8;font-weight:800;letter-spacing:.12em;font-size:.85rem}
.stButton button[kind="primary"]{background:#10B981;color:#06291f;border:0;font-weight:750}
@media(prefers-reduced-motion:no-preference){.pill:not(.paused){animation:pulse 2.6s infinite}}
@keyframes pulse{50%{box-shadow:0 0 16px #10B98166}}
</style>""", unsafe_allow_html=True)


@st.cache_data
def qaoa_results() -> dict:
    return json.loads((Path(__file__).resolve().parents[1] / "railway_results.json").read_text(encoding="utf-8"))


def qaoa_recommendation() -> list[int]:
    return recomandare_din_masuratori(qaoa_results()["ideal_counts"], ROUTES, DEMO_IDS, DEFAULT_BUDGET)


SCENARIOS = {"Rețeaua completă": ([], [], 7), "Rute recomandate": (None, [], 7),
             "Blocaj feroviar": (None, [6], 7), "Buget modificat": (None, [], 5)}
ROUTE_IDS = {r["id"] for r in ROUTES}
LABELS = {r["id"]: f"{r['id']:02d} · {r['cities'][0]} → {r['cities'][1]}" for r in ROUTES}


def baseline() -> NetworkState:
    return NetworkState(tuple(st.session_state.selected_ids), tuple(st.session_state.blocked_ids),
                        st.session_state.budget)


def apply_scenario() -> None:
    selected, blocked, budget = SCENARIOS[st.session_state.scenario]
    st.session_state.selected_ids = list(qaoa_recommendation() if selected is None else selected)
    st.session_state.blocked_ids = list(blocked)
    st.session_state.budget = budget
    st.session_state.engine = None


def reset_scenario() -> None:
    st.session_state.scenario = "Rute recomandate"
    apply_scenario()


def start_live() -> None:
    engine = SimulationEngine.create(baseline(), tuple(DEMO_IDS), seed=st.session_state.seed)
    engine.speed = st.session_state.speed
    engine.start(time.monotonic())
    st.session_state.engine = engine


def seek_timeline() -> None:
    engine = st.session_state.engine
    if engine:
        engine.seek(st.session_state.timeline_position, time.monotonic())


def change_speed() -> None:
    engine = st.session_state.engine
    if engine:
        engine.set_speed(st.session_state.speed, time.monotonic())


def clock(seconds: float) -> str:
    minute, second = divmod(int(seconds), 60)
    return f"{8 + minute // 60:02d}:{minute % 60:02d}:{second:02d}"


def active_incidents(engine: SimulationEngine) -> dict:
    incidents = {}
    for _, event in sorted(enumerate(engine.events), key=lambda pair: (pair[1].timestamp, pair[0])):
        if event.timestamp > engine.position:
            break
        if event.event_type == "ROUTE_BLOCKED":
            incidents[event.route_id] = event
        elif event.event_type == "ROUTE_RESTORED":
            incidents.pop(event.route_id, None)
    return incidents


for key, initial in (("scenario", "Rute recomandate"), ("selected_ids", qaoa_recommendation()),
                     ("blocked_ids", []), ("budget", 7), ("engine", None),
                     ("speed", 1.0), ("seed", 2026), ("reduced_motion", False),
                     ("map_revision", 0)):
    if key not in st.session_state:
        st.session_state[key] = initial

with st.sidebar:
    st.markdown("### ⚡ Q-FORCE")
    st.caption("SCENARIO CONTROL")
    locked = st.session_state.engine is not None
    st.selectbox("Scenariu", list(SCENARIOS), key="scenario", on_change=apply_scenario, disabled=locked)
    st.button("Aplică recomandarea QAOA", on_click=lambda: st.session_state.update(
        selected_ids=qaoa_recommendation()), width="stretch", disabled=locked)
    st.multiselect("Rute selectate", list(LABELS), format_func=LABELS.get,
                   key="selected_ids", disabled=locked)
    st.multiselect("Rute blocate", list(LABELS), format_func=LABELS.get,
                   key="blocked_ids", disabled=locked)
    st.number_input("Buget · unități", min_value=0, max_value=100, step=1,
                    key="budget", disabled=locked)
    if locked:
        st.caption("Selecția inițială este păstrată. Folosește Incident Manager sau resetează simularea.")
    st.divider()
    st.caption("LIVE SIMULATION")
    st.number_input("Seed demonstrație", min_value=0, max_value=999999, step=1,
                    key="seed", disabled=locked)
    st.select_slider("Viteză", options=SPEEDS, format_func=lambda x: f"{x:g}×",
                     key="speed", on_change=change_speed)
    st.button("START LIVE SIMULATION", on_click=start_live, type="primary",
              width="stretch", disabled=locked)
    st.button("Reset Simulation", on_click=lambda: st.session_state.update(engine=None),
              width="stretch", disabled=not locked)
    st.button("Reset Scenario", on_click=reset_scenario, width="stretch")
    st.divider()
    st.caption("DISPLAY")
    show_unselected = st.toggle("Arată rutele nealese", value=True)
    use_tiles = st.toggle("Fundal cartografic online", value=True)
    st.toggle("Reduced Motion", key="reduced_motion")
    st.button("Recentrează harta", on_click=lambda: st.session_state.update(
        map_revision=st.session_state.map_revision + 1), width="stretch")
    inspected = st.selectbox("Inspectează ruta", [None, *LABELS],
                             format_func=lambda i: "Nicio rută" if i is None else LABELS[i])
    st.caption("LIVE SIMULATION — SYNTHETIC DATA. Liniile sunt conexiuni schematice.")


@st.fragment(run_every="1s")
def control_center() -> None:
    engine: SimulationEngine | None = st.session_state.engine
    if engine:
        engine.advance(time.monotonic())
        state, incidents = engine.state(), active_incidents(engine)
    else:
        state, incidents = baseline(), {}
    plan = calculeaza_plan(ROUTES, state.selected_ids, state.blocked_ids, state.budget)
    badge = "LIVE" if engine and engine.running else "PAUSED" if engine else "STANDBY"
    pill = "pill" if engine and engine.running else "pill paused"
    if st.session_state.reduced_motion:
        pill += " no-motion"
    current_clock = clock(engine.position if engine else 0)
    st.markdown(f"""<div class="hero"><div class="eyebrow">Q-FORCE / OPERATIONS</div>
    <h1>QUANTUM RAILWAYS 2.0</h1><p>LIVE NETWORK CONTROL CENTER · Rețea didactică a României</p>
    <span class="{pill}">{badge} · LIVE SIMULATION — SYNTHETIC DATA</span>
    <span style="margin-left:1rem;color:#38BDF8;font-weight:800">ORA VIRTUALĂ {current_clock}</span></div>""",
                unsafe_allow_html=True)
    if incidents:
        st.error("INCIDENT ACTIV · " + ", ".join(f"{e.event_id}: ruta {i} blocată"
                                            for i, e in incidents.items()))
    if plan["conflicte"]:
        st.warning("Rutele blocate sunt excluse din plan: " + ", ".join(map(str, plan["conflicte"])))
    if not plan["valid"]:
        st.error(f"Buget depășit cu {plan['cost'] - state.budget:g} unități.")
    metrics = [("Rute active", plan["numar_active"]), ("Rute blocate", plan["numar_blocate"]),
               ("Cost total", f"{plan['cost']:g}"), ("Beneficiu total", f"{plan['beneficiu']:g}"),
               ("Buget", f"{state.budget:g}"), ("Status plan", "VALID" if plan["valid"] else "DEPĂȘIT")]
    for group in (metrics[:3], metrics[3:]):
        for column, (label, value) in zip(st.columns(3), group):
            column.metric(label, value)
    st.progress(min(plan["cost"] / state.budget, 1.0) if state.budget else (1.0 if plan["cost"] else 0.0),
                text=f"Buget utilizat: {plan['cost']:g} / {state.budget:g}")

    tab_live, tab_time, tab_compare, tab_qaoa = st.tabs(
        ["LIVE NETWORK", "TIMELINE & REPLAY", "BEFORE / AFTER", "QAOA INSIGHTS"])
    with tab_live:
        figure = deseneaza_harta(ROUTES, state.selected_ids, state.blocked_ids, POSITIONS,
            fundal_online=use_tiles, arata_nealese=show_unselected, incidente=incidents,
            ruta_inspectata=inspected, reduced_motion=st.session_state.reduced_motion)
        st.plotly_chart(figure, width="stretch", key=f"live_map_{st.session_state.map_revision}",
                        config={"scrollZoom": True, "displaylogo": False})
        left, right = st.columns([2, 1])
        with left:
            st.markdown("#### INCIDENT MANAGER")
            route_id = st.selectbox("Ruta afectată", list(LABELS), format_func=LABELS.get)
            buttons = st.columns(2)
            if buttons[0].button("SIMULATE EMERGENCY", type="primary", width="stretch",
                                 disabled=route_id in state.blocked_ids):
                if engine is None:
                    start_live()
                    engine = st.session_state.engine
                    engine.pause(time.monotonic())
                block_route(engine, route_id, ROUTE_IDS)
                st.rerun()
            if buttons[1].button("RESTORE ROUTE", width="stretch",
                                 disabled=engine is None or route_id not in state.blocked_ids) and engine:
                restore_route(engine, route_id, ROUTE_IDS)
                st.rerun()
        with right:
            st.markdown("#### NETWORK STATUS")
            st.write(f"**{plan['numar_active']}** active · **{plan['numar_blocate']}** blocate")
            st.write("🟢 Activă · ⚪ Disponibilă · 🔴 Blocată · 🔵 Inspectată")
            st.caption("Ora virtuală este separată de ora calculatorului. Datele sunt sintetice.")
        st.markdown("#### ROUTE DETAILS")
        rows = [{"ID": r["id"], "Plecare": r["cities"][0], "Sosire": r["cities"][1],
                 "Cost": r["cost"], "Beneficiu": r["value"],
                 "Stare": starea_rutei(r["id"], state.selected_ids, state.blocked_ids)} for r in ROUTES]
        st.dataframe(rows, width="stretch", hide_index=True)

    with tab_time:
        st.markdown('<div class="timeline-title">SIMULATION TIMELINE</div>', unsafe_allow_html=True)
        if engine is None:
            st.info("Pornește simularea sau creează un incident pentru a activa Timeline.")
        else:
            controls = st.columns(4)
            if controls[0].button("▶ Play / Resume", disabled=engine.running, width="stretch"):
                engine.resume(time.monotonic())
                st.rerun()
            if controls[1].button("Ⅱ Pause", disabled=not engine.running, width="stretch"):
                engine.pause(time.monotonic())
                st.rerun()
            if controls[2].button("↺ Replay", width="stretch"):
                engine.replay(time.monotonic())
                st.rerun()
            if controls[3].button("⟲ Restart", width="stretch"):
                engine.reset()
                st.rerun()
            st.session_state.timeline_position = int(engine.position)
            st.slider("Timp virtual · secunde de la 08:00", 0, int(engine.duration),
                      key="timeline_position", on_change=seek_timeline)
            st.caption(f"Moment: {current_clock} · Viteză: {engine.speed:g}× · "
                       f"{len(engine.events)} evenimente în jurnal")
            for event in sorted((e for e in engine.events if e.timestamp <= engine.position),
                                key=lambda e: e.timestamp, reverse=True)[:10]:
                style = "event incident" if event.severity == "HIGH" else "event"
                st.markdown(f'<div class="{style}"><b>{clock(event.timestamp)} · {event.event_id}</b> · '
                            f'{event.description}</div>', unsafe_allow_html=True)
            markers = go.Figure(go.Scatter(x=[e.timestamp for e in engine.events],
                y=[1] * len(engine.events), mode="markers+text", text=[e.event_id for e in engine.events],
                textposition="top center", marker={"size": 12, "color": ["#EF4444" if e.severity == "HIGH"
                else "#38BDF8" for e in engine.events]}, hovertext=[e.description for e in engine.events],
                hoverinfo="text"))
            markers.add_vline(x=engine.position, line_color="#10B981", line_width=2)
            markers.update_layout(height=160, margin={"l": 10, "r": 10, "t": 30, "b": 10},
                paper_bgcolor="#111C2E", plot_bgcolor="#111C2E", font={"color": "#94A3B8"},
                yaxis={"visible": False}, xaxis={"range": [0, engine.duration], "title": "Secunde simulate"})
            st.plotly_chart(markers, width="stretch", key="timeline_chart")

    with tab_compare:
        st.markdown("#### NETWORK COMPARISON")
        if engine is None:
            st.info("Pornește simularea pentru comparația Before / After.")
        else:
            mode = st.radio("Mod", ["Side by Side", "Snapshot Comparison"], horizontal=True)
            if mode == "Snapshot Comparison":
                t1 = st.slider("Moment Before", 0, int(DURATION), 0)
                t2 = st.slider("Moment After", 0, int(DURATION), int(engine.position))
                before = state_at_time(engine.initial_state, engine.events, t1)
                after = state_at_time(engine.initial_state, engine.events, t2)
            else:
                before, after = engine.initial_state, state
            comparison = compare_states(ROUTES, before, after)
            columns = st.columns(2)
            for column, title, snapshot, summary in (
                (columns[0], "BEFORE", before, comparison["before"]),
                (columns[1], "AFTER", after, comparison["after"])):
                with column:
                    st.markdown(f"### {title}")
                    st.caption(f"Cost {summary['cost']:g} · Beneficiu {summary['beneficiu']:g} · "
                               f"{summary['numar_active']} active · "
                               f"{'Valid' if summary['valid'] else 'Buget depășit'}")
                    snapshot_fig = deseneaza_harta(ROUTES, snapshot.selected_ids, snapshot.blocked_ids,
                        POSITIONS, fundal_online=use_tiles, arata_nealese=show_unselected,
                        reduced_motion=st.session_state.reduced_motion, height=420)
                    st.plotly_chart(snapshot_fig, width="stretch", key=f"comparison_{title}",
                                    config={"scrollZoom": True, "displaylogo": False})
            cards = st.columns(4)
            for column, label, value in zip(cards,
                ("Δ Cost", "Δ Beneficiu", "Rute adăugate", "Rute eliminate / blocate"),
                (f"{comparison['cost_delta']:+g}", f"{comparison['benefit_delta']:+g}",
                 len(comparison["added_ids"]), len(comparison["removed_ids"]))):
                column.metric(label, value)
            st.caption(f"Adăugate: {comparison['added_ids'] or 'niciuna'} · "
                       f"Eliminate: {comparison['removed_ids'] or 'niciuna'} · "
                       f"Blocaje noi: {comparison['new_blocked_ids'] or 'niciunul'}")

    with tab_qaoa:
        result = qaoa_results()
        st.markdown("#### QAOA INSIGHTS")
        st.write(f"**Plan fezabil observat în experimentul salvat:** {qaoa_recommendation()}")
        st.write(f"**Baseline:** buget {result['budget']} · penalizare {result['penalty']} · "
                 f"adâncime {result['local_training']['depth']}")
        st.write(f"**Măsurări ideale:** {sum(result['ideal_counts'].values())} · "
                 f"rata planurilor fezabile {result['metrics']['Ideal']['feasible_rate']:.1%}")
        if state.budget != DEFAULT_BUDGET or state.blocked_ids:
            st.warning("Rezultatul QAOA aparține configurației baseline. Nu reprezintă un optim "
                       "recalculat pentru bugetul sau blocajele curente.")
        st.caption("Maparea x0…x4 folosește ID-urile 0, 1, 2, 6, 8; într-un șir Qiskit x0 este la dreapta.")

    with st.expander("Incident Log și export"):
        if engine:
            st.dataframe([{"Ora": clock(e.timestamp), "ID": e.event_id, "Tip": e.event_type,
                           "Rută": e.route_id, "Severitate": e.severity, "Descriere": e.description}
                          for e in engine.events if e.timestamp <= engine.position],
                         width="stretch", hide_index=True)
        if st.button("Pregătește exportul stării curente"):
            st.session_state.export_html = figure.to_html(full_html=True, include_plotlyjs=True)
            st.session_state.export_label = current_clock
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(["ID", "Plecare", "Sosire", "Cost", "Beneficiu"])
            for route in ROUTES:
                if route["id"] in plan["active_ids"]:
                    writer.writerow([route["id"], *route["cities"], route["cost"], route["value"]])
            st.session_state.export_csv = "\ufeff" + buffer.getvalue()
        if "export_html" in st.session_state:
            st.caption(f"Export pregătit pentru ora virtuală {st.session_state.export_label}.")
            st.download_button("Descarcă harta HTML", st.session_state.export_html,
                               file_name="quantum_railways_map.html", mime="text/html")
            st.download_button("Descarcă planul CSV", st.session_state.export_csv,
                               file_name="quantum_railways_plan.csv", mime="text/csv")


control_center()
