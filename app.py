"""Dashboard Streamlit pentru configurarea scenariilor Quantum Railways."""

from collections import defaultdict
from pathlib import Path
import unicodedata

import altair as alt
import streamlit as st

from railway_data import DEFAULT_BUDGET, DEMO_IDS, POSITIONS, ROUTES


st.set_page_config(
    page_title="Quantum Railways | Q-FORCE",
    page_icon="🚆",
    layout="wide",
    initial_sidebar_state="auto",
)


def reset_selection():
    """Revine la rutele selectate inițial în notebook."""
    for route in ROUTES:
        st.session_state[f"selected_route_{route['id']}"] = route["id"] in DEMO_IDS


def clear_selection():
    """Golește eligibilitatea rutelor fără să modifice bugetul."""
    for route in ROUTES:
        st.session_state[f"selected_route_{route['id']}"] = False


def sync_route_selection(route_id):
    """Păstrează selecția chiar dacă filtrul ascunde temporar checkboxul."""
    st.session_state[f"selected_route_{route_id}"] = st.session_state[f"route_{route_id}"]


def route_name(route):
    return f"{route['cities'][0]} – {route['cities'][1]}"


def normalize_search(value):
    """Ignoră majusculele, diacriticele și forma separatorului dintre orașe."""
    normalized = unicodedata.normalize("NFD", value.casefold())
    return " ".join(
        "".join(
            character if character.isalnum() or character == "#" else " "
            for character in normalized if not unicodedata.combining(character)
        ).split()
    )


def filter_routes(routes, query):
    term = normalize_search(query.strip())
    if not term:
        return routes
    return [
        route for route in routes
        if term in normalize_search(route_name(route)) or term in f"#{route['id']:02d}"
    ]


def route_rows(routes):
    """Datele din catalog; costul internațional include deja frontiera."""
    return [
        {
            "ID": route["id"],
            "Rută": route_name(route),
            "Cost": route["cost"],
            "Puncte": route["value"],
            "Tip": "Internațională" if route["international"] else "Națională",
            "Cost frontieră": route["border_cost"],
        }
        for route in routes
    ]


def chart_rows(routes):
    """Separă doar punctele identice, fără să schimbe costul sau punctajul."""
    grouped_ids = defaultdict(list)
    for route in routes:
        grouped_ids[(route["cost"], route["value"])].append(route["id"])

    offsets = {}
    for ids in grouped_ids.values():
        ids.sort()  # Același ID primește mereu aceeași poziție în grup.
        for index, route_id in enumerate(ids):
            offsets[route_id] = (index - (len(ids) - 1) / 2) * 0.2

    return [
        {**row, "Cost vizual": row["Cost"] + offsets[row["ID"]]}
        for row in route_rows(routes)
    ]


def show_route_checks(routes):
    """Păstrează checkbox-urile native și evidențiază discret selecția."""
    for route in routes:
        route_id = route["id"]
        st.session_state[f"route_{route_id}"] = st.session_state[f"selected_route_{route_id}"]
        checked = st.checkbox(
            f"#{route_id:02d}  {route_name(route)}",
            key=f"route_{route_id}",
            on_change=sync_route_selection,
            args=(route_id,),
        )
        border = f" · frontieră {route['border_cost']}" if route["international"] else ""
        selected_class = " is-selected" if checked else ""
        st.markdown(
            f'<div class="qr-route-meta{selected_class}">'
            f"Cost {route['cost']}{border} <span>·</span> {route['value']} puncte</div>",
            unsafe_allow_html=True,
        )


def cost_value_chart(routes):
    """Compară rutele individuale, fără a reprezenta un plan optimizat."""
    # Reperele întregi fac vizibile valori precum 9 puncte, nu doar 8 și 10.
    axis_style = dict(
        gridColor="#2A4059",
        labelColor="#B8C9D8",
        titleColor="#F0F5FF",
        labelFontSize=11,
        titleFontSize=12,
    )
    cost_axis = alt.Axis(values=list(range(max(route["cost"] for route in routes) + 1)), **axis_style)
    points_axis = alt.Axis(
        values=list(range(max(route["value"] for route in routes) + 1)),
        labelOverlap=False,
        **axis_style,
    )
    return (
        alt.Chart({"values": chart_rows(routes)})
        .mark_circle(size=230, opacity=0.9, stroke="#0B1220", strokeWidth=1.5)
        .encode(
            x=alt.X(
                "Cost vizual:Q",
                axis=cost_axis,
                title="Cost total",
                scale=alt.Scale(domain=[0, max(route["cost"] for route in routes) + 0.5]),
            ),
            y=alt.Y(
                "Puncte:Q",
                axis=points_axis,
                title="Punctaj",
                scale=alt.Scale(domain=[0, max(route["value"] for route in routes) + 0.7]),
            ),
            color=alt.Color(
                "Tip:N",
                scale=alt.Scale(
                    domain=["Națională", "Internațională"],
                    range=["#55E6C1", "#83A8FF"],
                ),
                legend=alt.Legend(
                    title=None,
                    orient="top",
                    direction="horizontal",
                    labelColor="#F0F5FF",
                    labelFontSize=12,
                    symbolSize=110,
                ),
            ),
            tooltip=[
                alt.Tooltip("ID:Q", title="ID"),
                alt.Tooltip("Rută:N", title="Rută"),
                alt.Tooltip("Cost:Q", title="Cost total"),
                alt.Tooltip("Puncte:Q", title="Punctaj"),
                alt.Tooltip("Tip:N", title="Categorie"),
                alt.Tooltip("Cost frontieră:Q", title="Cost frontieră"),
            ],
        )
        .properties(height=360)
        .configure_view(stroke=None)
        .configure(background="#162238")
    )


def render_map_panel(figure=None):
    """Punctul de integrare pentru figura Plotly primită de la membrul 2."""
    with st.container(border=True):
        if figure is not None:
            st.plotly_chart(figure, width="stretch")
        else:
            st.markdown(
                '<div class="qr-map-placeholder">'
                '<span class="qr-map-icon">⌖</span>'
                '<strong>Vizualizarea rețelei</strong>'
                '<p>Harta interactivă va fi disponibilă după integrarea modulului de rețea.</p>'
                '<span class="qr-status">MODUL ÎN CURS DE DEZVOLTARE</span>'
                '</div>',
                unsafe_allow_html=True,
            )


# Inițializarea se face înaintea widgeturilor pentru ca resetarea să fie sigură.
for route in ROUTES:
    st.session_state.setdefault(
        f"selected_route_{route['id']}",
        st.session_state.get(f"route_{route['id']}", route["id"] in DEMO_IDS),
    )

styles = Path(__file__).with_name("styles.css").read_text(encoding="utf-8")
st.markdown(f"<style>{styles}</style>", unsafe_allow_html=True)

national_routes = [route for route in ROUTES if not route["international"]]
international_routes = [route for route in ROUTES if route["international"]]
selected_count = sum(st.session_state[f"selected_route_{route['id']}"] for route in ROUTES)

with st.sidebar:
    st.markdown(
        '<div class="qr-side-brand"><span class="qr-side-icon">🚆</span>'
        '<div><strong>Q-FORCE</strong><small>RAILWAY INTELLIGENCE</small></div></div>',
        unsafe_allow_html=True,
    )
    st.caption("Configurează un scenariu pentru rețeaua fictivă din laborator.")
    st.divider()

    st.subheader("Bugetul proiectului")
    budget = st.slider(
        "Buget disponibil",
        min_value=1,
        max_value=15,
        value=DEFAULT_BUDGET,
        step=1,
        key="budget",
        help="Bugetul limitează suma costurilor rutelor recomandate ulterior.",
    )
    st.markdown(
        f'<div class="qr-budget-readout"><span>Buget selectat</span>'
        f'<strong>{budget}<small> / 15</small></strong></div>',
        unsafe_allow_html=True,
    )
    st.caption("Buget exprimat în unități fictive.")
    st.divider()

    st.subheader("Rute eligibile")
    st.markdown(
        f'<div class="qr-selection-count"><strong>{selected_count}</strong> din '
        f'{len(ROUTES)} rute bifate</div>',
        unsafe_allow_html=True,
    )
    st.caption("Bifarea face ruta disponibilă pentru analiză, nu o aprobă pentru construcție.")
    reset_col, clear_col = st.columns(2, gap="small")
    with reset_col:
        st.button(
            "↺ Resetează",
            key="reset_selection",
            on_click=reset_selection,
            width="stretch",
            disabled=not ROUTES,
        )
    with clear_col:
        st.button(
            "Golește",
            key="clear_selection",
            on_click=clear_selection,
            width="stretch",
            disabled=not ROUTES,
        )

    search_query = st.text_input(
        "Caută rută sau oraș",
        placeholder="Ex.: Brașov, Sofia sau #06",
        key="route_search",
    )
    matching_routes = filter_routes(ROUTES, search_query)

    if ROUTES:
        if search_query.strip():
            st.caption(f"{len(matching_routes)} din {len(ROUTES)} rute găsite")
            if matching_routes:
                show_route_checks(matching_routes)
            else:
                st.info("Nu am găsit nicio rută. Încearcă alt oraș sau alt nume.")
        else:
            national_tab, international_tab = st.tabs(["Naționale", "Internaționale"])
            with national_tab:
                st.caption(f"{len(national_routes)} rute · cost și punctaj")
                show_route_checks(national_routes)
            with international_tab:
                st.caption(f"{len(international_routes)} rute · cost total cu frontieră")
                show_route_checks(international_routes)
    else:
        st.info("Nu există rute în catalogul curent.")

    st.info(
        "Bifarea unei rute o face disponibilă pentru analiză. Nu înseamnă că ruta "
        "va fi construită. Algoritmul va decide ulterior ce combinație respectă bugetul."
    )

# Rutele bifate definesc intrarea algoritmilor, nu un plan deja construit.
available_routes = [
    route for route in ROUTES if st.session_state.get(f"selected_route_{route['id']}", False)
]
available_international = sum(route["international"] for route in available_routes)

st.markdown(
    f"""
    <div class="qr-hero">
      <div class="qr-hero-copy">
        <span class="qr-kicker">Q-FORCE / RAILWAY INTELLIGENCE</span>
        <h1>Quantum Railways</h1>
        <strong class="qr-tagline">Planifică. Optimizează. Conectează.</strong>
        <p>Alege bugetul și rutele disponibile pentru un viitor plan de investiții feroviare.</p>
      </div>
      <div class="qr-hero-facts" aria-label="Datele rețelei">
        <div><strong>{len(ROUTES)}</strong><span>rute</span></div>
        <div><strong>{len(POSITIONS)}</strong><span>orașe</span></div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="qr-section-label">01 / SCENARIU</div>', unsafe_allow_html=True)
st.subheader("Privire de ansamblu")
st.markdown(
    f"""
    <section class="qr-kpi-grid" aria-label="Indicatorii scenariului">
      <article class="qr-kpi"><span class="qr-kpi-icon">◎</span>
        <span class="qr-kpi-label">Buget disponibil</span>
        <strong>{budget}</strong><small>unități fictive</small></article>
      <article class="qr-kpi"><span class="qr-kpi-icon">✓</span>
        <span class="qr-kpi-label">Rute eligibile</span>
        <strong>{len(available_routes)}</strong><small>disponibile pentru analiză</small></article>
      <article class="qr-kpi"><span class="qr-kpi-icon">◇</span>
        <span class="qr-kpi-label">Total rute</span>
        <strong>{len(ROUTES)}</strong><small>în catalogul complet</small></article>
      <article class="qr-kpi"><span class="qr-kpi-icon">⌖</span>
        <span class="qr-kpi-label">Orașe conectate</span>
        <strong>{len(POSITIONS)}</strong><small>în datele laboratorului</small></article>
    </section>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="qr-section-label">02 / EXPLORARE</div>', unsafe_allow_html=True)
st.subheader("Explorerul de rute")
st.caption(
    f"{len(available_routes)} rute eligibile · "
    f"{len(available_routes) - available_international} naționale · "
    f"{available_international} internaționale"
)

table_tab, chart_tab = st.tabs(["📋 Tabelul rutelor", "📈 Cost și punctaj"])
with table_tab:
    if available_routes:
        st.dataframe(
            route_rows(available_routes),
            hide_index=True,
            width="stretch",
            height=350,
            column_config={
                "ID": st.column_config.NumberColumn("ID", format="%d", width=55),
                "Rută": st.column_config.TextColumn("Rută", width=175),
                "Cost": st.column_config.NumberColumn("Cost", format="%d", width=70),
                "Puncte": st.column_config.NumberColumn("Puncte", format="%d", width=75),
                "Tip": st.column_config.TextColumn("Tip", width="medium"),
                "Cost frontieră": st.column_config.NumberColumn("Frontieră", format="%d", width="small"),
            },
        )
        st.caption(
            "Costul internațional include frontiera. Pe ecrane înguste, glisează "
            "tabelul pentru a vedea și celelalte coloane."
        )
    else:
        st.info("Nu există rute eligibile. Bifează o rută în bara laterală pentru a o analiza.")

with chart_tab:
    if available_routes:
        st.altair_chart(cost_value_chart(available_routes), width="stretch")
        st.caption(
            "Graficul compară rutele individuale. Nu reprezintă soluția optimă "
            "și nu indică rutele construite. Punctele cu cost și punctaj identice "
            "sunt deplasate puțin doar pentru vizibilitate; tooltipul arată valorile reale."
        )
    else:
        st.info("Selectează cel puțin o rută pentru a vedea graficul cost–punctaj.")

with st.expander("Vezi toate rutele din catalog"):
    if ROUTES:
        st.dataframe(route_rows(ROUTES), hide_index=True, width="stretch")
    else:
        st.info("Catalogul este gol.")

st.markdown('<div class="qr-section-label">03 / REȚEA</div>', unsafe_allow_html=True)
st.subheader("Railway Network Map")
render_map_panel()

st.markdown('<div class="qr-section-label">04 / ANALIZĂ</div>', unsafe_allow_html=True)
st.subheader("Optimization Center")
with st.container(border=True):
    action_copy, action_button = st.columns([2.2, 1], gap="medium", vertical_alignment="center")
    with action_copy:
        st.markdown("#### Scenariul tău este gata de pregătire")
        st.caption("Algoritmii clasic și QAOA vor primi rutele eligibile și bugetul după integrare.")
    with action_button:
        prepare_clicked = st.button(
            "Pregătește scenariul",
            key="prepare_scenario",
            type="primary",
            width="stretch",
            disabled=not available_routes,
        )

if prepare_clicked:
    st.info(
        f"Scenariu pregătit: {len(available_routes)} rute eligibile, buget {budget}. "
        "Modulul de optimizare este în curs de dezvoltare."
    )

st.markdown("#### Rezultatul planului")
st.caption("Valorile de mai jos vor apărea numai după executarea unui algoritm conectat.")
st.markdown(
    """
    <div class="qr-result-grid">
      <div><span>Cost total recomandat</span><strong>—</strong></div>
      <div><span>Punctaj obținut</span><strong>—</strong></div>
      <div><span>Starea bugetului</span><strong class="qr-result-pending">În așteptare</strong></div>
    </div>
    <div class="qr-result-routes"><strong>Rute recomandate</strong>
      <p>Nicio recomandare încă. Bifarea indică doar eligibilitatea rutelor.</p></div>
    """,
    unsafe_allow_html=True,
)

with st.container(border=True):
    st.markdown("#### Classical vs Quantum Optimization")
    st.caption("Comparația dintre soluția clasică și QAOA va apărea după integrarea modulelor.")
    st.markdown('<span class="qr-status">MODUL ÎN CURS DE DEZVOLTARE</span>', unsafe_allow_html=True)

st.markdown(
    '<div class="qr-footer">Q-FORCE <span>·</span> QUANTUM RAILWAYS '
    '<span>·</span> DATE FICTIVE PENTRU DEMONSTRAȚIE</div>',
    unsafe_allow_html=True,
)
