"""Presentation workflow for the unified Quantum Railways application."""
from pathlib import Path
import unicodedata
import streamlit as st
from railway_catalog import ROUTES
from railway_data import DEFAULT_BUDGET, DEMO_IDS
from simulation_history import apply_pending_snapshot,persist_session_history

st.set_page_config(page_title="Quantum Railways | Q-FORCE",page_icon="🚆",layout="wide")
try:
    persist_session_history(st.session_state)
except Exception as exc:
    st.warning(f'Istoricul existent nu a putut fi salvat: {exc}')
from incident_ui import render_simple_incidents,render_compact_map
from experiment_ui import render_experiment
apply_pending_snapshot(st.session_state,ROUTES)
st.markdown(f"<style>{Path(__file__).with_name('styles.css').read_text(encoding='utf-8')}</style>",unsafe_allow_html=True)


def reset_selection():
    for route in ROUTES:
        st.session_state[f"selected_route_{route['id']}"]=route['id'] in DEMO_IDS


def clear_selection():
    for route in ROUTES:
        st.session_state[f"selected_route_{route['id']}"]=False


def sync_route_selection(route_id):
    st.session_state[f"selected_route_{route_id}"]=st.session_state[f"route_{route_id}"]


def search_text(value):
    return ''.join(c for c in unicodedata.normalize('NFD',value.casefold()) if not unicodedata.combining(c))


for route in ROUTES:
    st.session_state.setdefault(f"selected_route_{route['id']}",route['id'] in DEMO_IDS)

st.markdown('<div class="qr-hero"><div class="qr-hero-copy"><span class="qr-kicker">Q-FORCE / RAILWAY INTELLIGENCE</span><h1>Quantum Railways</h1><p>Selectează rețeaua, simulează și compară planul cuantic cu soluția clasică.</p></div></div>',unsafe_allow_html=True)
budget_column,count_column,cities_column=st.columns(3)
with budget_column:
    budget=st.slider("Buget disponibil",0,100,DEFAULT_BUDGET,key='budget')

with st.sidebar:
    st.subheader('Alege conexiunile')
    a,b=st.columns(2)
    a.button('↺ Resetează',on_click=reset_selection,width='stretch')
    b.button('Golește',on_click=clear_selection,width='stretch')
    query=st.text_input('Caută rută sau oraș',placeholder='Iași, Brașov, #06',key='route_search')
    for route in ROUTES:
        name=' — '.join(route['cities'])
        if query and search_text(query) not in search_text(name) and query not in f"#{route['id']:02d}":
            continue
        st.session_state[f"route_{route['id']}"]=st.session_state[f"selected_route_{route['id']}"]
        st.checkbox(f"#{route['id']:02d} {name}",key=f"route_{route['id']}",
                    on_change=sync_route_selection,args=(route['id'],))
        st.caption(f"Cost {route['cost']} · scor {route['value']}")

selected_routes=[r for r in ROUTES if st.session_state[f"selected_route_{r['id']}"]]
selected_cities=sorted({city for route in selected_routes for city in route['cities']})
count_column.metric('Total rute bifate',len(selected_routes))
cities_column.metric('Orașe selectate',len(selected_cities))
st.subheader('Rute alese pentru simulare')
if selected_routes:
    st.dataframe([{'ID':r['id'],'Conexiune':' — '.join(r['cities']),'Cost':r['cost'],'Scor':r['value']}
                  for r in selected_routes],hide_index=True,width='stretch')
else:
    st.info('Bifează conexiunile pe care vrei să le analizezi.')
state=render_simple_incidents(selected_routes)
render_compact_map(state,key='configured_network')
render_experiment(selected_routes,budget,state)
