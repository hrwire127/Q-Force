"""Dashboard Streamlit pentru explorarea scenariilor Quantum Railways."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import streamlit as st

from railway_data import DEFAULT_BUDGET, DEMO_IDS, POSITIONS, ROUTES
from railway_map import calculeaza_plan, deseneaza_harta, recomandare_din_masuratori, starea_rutei

st.set_page_config(page_title="Quantum Railways — Network Explorer", page_icon="🚆",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
  .stApp, [data-testid="stSidebar"] { background: #081427; color: #e2e8f0; }
  [data-testid="stSidebar"] { border-right: 1px solid #1e3550; }
  h1, h2, h3 { color: #f8fafc; letter-spacing: -.025em; }
  .hero { padding: 1.25rem 1.5rem; margin-bottom: 1.2rem; border: 1px solid #24465c;
    border-radius: 18px; background: linear-gradient(120deg,#10253d,#0b343e); }
  .hero h1 { margin: 0; font-size: clamp(1.7rem,3vw,2.5rem); }
  .hero p { color: #9ec3d0; margin: .45rem 0 0; }
  [data-testid="stMetric"] { background: #10243b; border: 1px solid #25415b;
    border-radius: 14px; padding: .8rem 1rem; min-height: 115px; }
  [data-testid="stMetricLabel"] { color: #a8c0d0; }
  [data-testid="stMetricValue"] { color: #f8fafc; }
  [data-testid="stPlotlyChart"] { border: 1px solid #25415b; border-radius: 18px;
    overflow: hidden; background: #0b1730; }
  .stButton button[kind="primary"] { background: #10b981; color: #05251d; border: 0; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def read_qaoa_counts() -> dict[str, int]:
    path = Path(__file__).with_name("railway_results.json")
    return json.loads(path.read_text(encoding="utf-8"))["ideal_counts"]


def qaoa_recommendation() -> list[int]:
    return recomandare_din_masuratori(read_qaoa_counts(), ROUTES, DEMO_IDS, DEFAULT_BUDGET)


SCENARIOS = {
    "Rețeaua completă": "Toate cele 12 conexiuni fictive sunt vizibile; niciuna nu este construită implicit.",
    "Rute recomandate": "Cel mai valoros plan fezabil observat în măsurările QAOA salvate, la bugetul inițial de 7 unități.",
    "Blocaj feroviar": "Ruta 6 este blocată ca exemplu. Poți modifica blocajele din selector.",
    "Buget modificat": "Un buget de 5 unități arată imediat dacă planul curent mai este valid; nu rulează o optimizare nouă.",
}


def apply_scenario() -> None:
    scenario = st.session_state.scenario
    st.session_state.selected_ids = qaoa_recommendation() if scenario in (
        "Rute recomandate", "Buget modificat") else []
    st.session_state.blocked_ids = [6] if scenario == "Blocaj feroviar" else []
    st.session_state.budget = 5 if scenario == "Buget modificat" else DEFAULT_BUDGET


def reset_state() -> None:
    st.session_state.scenario = "Rețeaua completă"
    st.session_state.selected_ids = []
    st.session_state.blocked_ids = []
    st.session_state.budget = DEFAULT_BUDGET


for key, initial in (("scenario", "Rețeaua completă"), ("selected_ids", []),
                     ("blocked_ids", []), ("budget", DEFAULT_BUDGET)):
    if key not in st.session_state:
        st.session_state[key] = initial

st.markdown("""
<div class="hero"><h1>Quantum Railways — Network Explorer</h1>
<p>Explorează, optimizează și simulează o rețea feroviară.</p></div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Panou de control")
    st.selectbox("Scenariu", list(SCENARIOS), key="scenario", on_change=apply_scenario)
    left, right = st.columns(2)
    with left:
        st.button("Reset", on_click=reset_state, width="stretch")
    with right:
        st.button("Aplică QAOA", on_click=lambda: st.session_state.update(
            selected_ids=qaoa_recommendation()), width="stretch", type="primary")
    route_labels = {route["id"]: f"{route['id']} · {route['cities'][0]} → {route['cities'][1]}"
                    for route in ROUTES}
    st.multiselect("Rute selectate", list(route_labels), format_func=route_labels.get,
                   key="selected_ids")
    st.multiselect("Rute blocate", list(route_labels), format_func=route_labels.get,
                   key="blocked_ids")
    st.number_input("Buget disponibil · unități", min_value=0, max_value=100,
                    step=1, key="budget")
    st.divider()
    st.subheader("Afișare")
    show_unselected = st.toggle("Arată rutele nealese", value=True)
    use_tiles = st.toggle("Fundal cartografic online", value=True,
                          help="Dezactivează pentru o hartă funcțională fără tile-uri online.")
    st.caption("Liniile sunt conexiuni schematice între orașe, nu geometria infrastructurii feroviare.")

selected = st.session_state.selected_ids
blocked = st.session_state.blocked_ids
budget = st.session_state.budget
plan = calculeaza_plan(ROUTES, selected, blocked, budget)

if plan["conflicte"]:
    st.warning("Rutele selectate și blocate simultan sunt afișate cu roșu și excluse din planul activ: "
               + ", ".join(map(str, sorted(plan["conflicte"]))))
if not plan["valid"]:
    st.error(f"Buget depășit cu {plan['cost'] - budget:g} unități. Modifică selecția sau bugetul.")

metric_items = list(zip(
    ("Cost activ", "Buget", "Beneficiu", "Rute active", "Rute blocate", "Plan"),
    (f"{plan['cost']:g}", f"{budget:g}", f"{plan['beneficiu']:g}",
     plan["numar_active"], plan["numar_blocate"], "Valid" if plan["valid"] else "Depășit"),
))
for row in (metric_items[:3], metric_items[3:]):
    for column, (label, value) in zip(st.columns(3), row):
        column.metric(label, value)
st.progress(min(plan["cost"] / budget, 1.0) if budget else (1.0 if plan["cost"] else 0.0),
            text=f"Utilizare buget: {plan['cost']:g} / {budget:g} unități")

fig = deseneaza_harta(ROUTES, selected, blocked, POSITIONS,
                      fundal_online=use_tiles, arata_nealese=show_unselected)
st.plotly_chart(fig, width="stretch", config={"scrollZoom": True, "displaylogo": False})

st.caption("Date didactice din notebookul Quantum Railways. Orașele sunt geografice; "
           "conexiunile, costurile și beneficiile sunt fictive.")

st.subheader("Detalii ale rețelei")
tab_routes, tab_plan, tab_scenario = st.tabs(["Toate rutele", "Plan și blocaje", "Scenariu și legendă"])
with tab_routes:
    rows = [{"ID": route["id"], "Plecare": route["cities"][0],
             "Sosire": route["cities"][1], "Cost": route["cost"],
             "Beneficiu": route["value"],
             "Stare": starea_rutei(route["id"], selected, blocked)} for route in ROUTES]
    st.dataframe(rows, width="stretch", hide_index=True)
with tab_plan:
    st.write("**Rute active:**", ", ".join(map(str, plan["active_ids"])) or "Niciuna")
    if blocked:
        st.write("**Rute blocate:**")
        st.dataframe([row for row in rows if row["ID"] in blocked],
                     width="stretch", hide_index=True)
    else:
        st.write("Nu există rute blocate.")
with tab_scenario:
    st.write(SCENARIOS[st.session_state.scenario])
    st.markdown("🟢 **Verde:** selectată · ⚪ **Gri:** disponibilă · 🔴 **Roșu:** blocată")
    if budget != DEFAULT_BUDGET:
        st.info("Recomandarea QAOA salvată a fost evaluată la bugetul 7. "
                "Bugetul curent actualizează indicatorii, dar nu recalculează optimizerul.")

st.download_button("Descarcă harta HTML", fig.to_html(full_html=True, include_plotlyjs=True),
                   file_name="quantum_railways_map.html", mime="text/html")
csv_buffer = io.StringIO()
writer = csv.writer(csv_buffer)
writer.writerow(["ID", "Plecare", "Sosire", "Cost", "Beneficiu"])
for route in ROUTES:
    if route["id"] in plan["active_ids"]:
        writer.writerow([route["id"], *route["cities"], route["cost"], route["value"]])
st.download_button("Descarcă planul activ CSV", "\ufeff" + csv_buffer.getvalue(),
                   file_name="quantum_railways_plan.csv", mime="text/csv")
