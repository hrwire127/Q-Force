
import streamlit as st

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

buget = st.sidebar.slider(
    "Alege bugetul disponibil",
    min_value=1,
    max_value=15,
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
