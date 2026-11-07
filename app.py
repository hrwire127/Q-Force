
from pathlib import Path
import sys

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "Q-Force"))
from classical_optimizer import (
    analizeaza_planuri,
    analyze_budgets,
    explain_classical_solution,
    get_alternative_plans,
    optimize_routes,
)

st.set_page_config(
    page_title="Quantum Railways",
    page_icon="🚆",
    layout="wide"
)

st.title("🚆 Quantum Railways")
st.write("Alege bugetul pentru dezvoltarea retelei feroviare.")

# Exemplu de rute si costuri fictive
rute = [
    {"nume": "Iasi - Brasov", "cost": 2, "puncte": 4},
    {"nume": "Iasi - Cluj-Napoca", "cost": 3, "puncte": 6},
    {"nume": "Cluj-Napoca - Brasov", "cost": 2, "puncte": 5},
    {"nume": "Brasov - Bucuresti", "cost": 4, "puncte": 9},
    {"nume": "Bucuresti - Constanta", "cost": 4, "puncte": 7}
]

# Utilizatorul isi alege bugetul
st.sidebar.header("Bugetul proiectului")
buget_maxim = sum(ruta["cost"] for ruta in rute)

buget = st.sidebar.slider(
    "Alege bugetul disponibil",
    min_value=0,
    max_value=buget_maxim,
    value=7
)

st.metric("Buget disponibil", buget)

# Afisam costurile rutelor
st.subheader("Costurile rutelor")

for ruta in rute:
    st.write(
        ruta["nume"],
        "| Cost:", ruta["cost"],
        "| Puncte:", ruta["puncte"]
    )

rezultat_clasic = optimize_routes(rute, buget)
analiza_clasica = analizeaza_planuri(rute, buget)
alternative_clasice = get_alternative_plans(rute, buget)
explicatie_clasica = explain_classical_solution(rute, buget, rezultat_clasic)
st.subheader("Soluția clasică optimă")
st.write("Rute selectate:")
if rezultat_clasic["rute_selectate"]:
    for ruta in rezultat_clasic["rute_selectate"]:
        st.write(f"• {ruta['nume']}")
else:
    st.write("Nicio rută")

col_cost, col_puncte, col_ramas = st.columns(3)
col_cost.metric("Cost total", rezultat_clasic["cost_total"])
col_puncte.metric("Punctaj total", rezultat_clasic["punctaj_total"])
col_ramas.metric("Buget rămas", rezultat_clasic["buget_ramas"])
st.write("Vector binar:", rezultat_clasic["vector_binar"])
st.caption(f"Planuri evaluate: {rezultat_clasic['planuri_evaluate']}")
if len(rezultat_clasic["solutii_optime"]) > 1:
    st.caption(f"Soluții cu punctaj maxim: {len(rezultat_clasic['solutii_optime'])}")
    with st.expander("Vezi toate soluțiile optime"):
        for plan in rezultat_clasic["solutii_optime"]:
            st.write(
                plan["vector_binar"],
                "| Cost:", plan["cost_total"],
                "| Puncte:", plan["punctaj_total"]
            )

with st.expander("De ce este optim acest plan?"):
    st.write(explicatie_clasica["rezumat"])
    st.caption(f"Planuri valide: {analiza_clasica['planuri_valide']} din {analiza_clasica['planuri_evaluate']}.")
    st.caption(
        f"{analiza_clasica['planuri_peste_buget']} planuri depășesc bugetul; "
        f"{analiza_clasica['planuri_cu_rute_blocate']} includ rute blocate. "
        "Aceste categorii pot avea planuri comune."
    )
    st.write("**Frontiera cost–punctaj**")
    st.caption("Fiecare rând reprezintă cel mai bun punctaj nou atins la acel cost.")
    st.table([
        {"Cost": plan["cost_total"], "Puncte": plan["punctaj_total"],
         "Vector binar": "".join(map(str, plan["vector_binar"]))}
        for plan in analiza_clasica["frontiera_pareto"]
    ])
    st.write("**Cum se schimbă punctajul optim când crește bugetul**")
    profil = analyze_budgets(rute, buget_maxim)
    st.line_chart(
        {"Punctaj maxim": [punct["punctaj_total"] for punct in profil]},
        x_label="Buget", y_label="Puncte"
    )
    if buget < buget_maxim:
        castig = profil[buget + 1]["castig_marginal"]
        mesaj_castig = f"crește cu {castig}" if castig else "rămâne neschimbat"
        st.info(f"Dacă bugetul crește de la {buget} la {buget + 1}, punctajul maxim {mesaj_castig}.")
    st.write("**Top 3 planuri valide**")
    st.table([
        {"Rute": ", ".join(ruta["nume"] for ruta in plan["rute_selectate"]) or "Nicio rută",
         "Vector": "".join(map(str, plan["vector_binar"])),
         "Cost": plan["cost_total"], "Puncte": plan["punctaj_total"],
         "Economie cost": plan["economie_cost"],
         "Pierdere puncte": plan["pierdere_punctaj"]}
        for plan in alternative_clasice["planuri"]
    ])
