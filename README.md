# Q-FORCE | Quantum Railways 2.0 — Live Control Center

Dashboard interactiv pentru rețeaua **fictivă** din `Quantum_Railways_Labb.ipynb`.
Orașele au coordonate geografice, însă conexiunile sunt segmente schematice,
iar costurile și beneficiile sunt date didactice.

## Demonstrația live

Pagina pornește cu planul fezabil observat în măsurările QAOA salvate. Butonul
**START LIVE SIMULATION** capturează un snapshot independent al selecției și
pornește ceasul virtual. Evenimentele programate sunt determinate de seed:
rețea operațională la 08:03, blocaj la 08:05, recalculare la 08:07,
restabilire la 08:10 și încheiere la 08:12. Viteza poate fi 0.5×, 1×, 2× sau 5×.

Tabul **TIMELINE & REPLAY** permite Pause, Resume, Replay, Restart și navigarea
cu sliderul. Evenimentele sunt păstrate în jurnal, iar starea este reconstruită
din snapshotul inițial la timpul ales. **SIMULATE EMERGENCY** și **RESTORE ROUTE**
adaugă evenimente în sesiunea curentă. Tabul **BEFORE / AFTER** compară snapshotul
inițial cu starea curentă sau două momente alese din Timeline. Blocarea unei rute
nu modifică automat selecția recomandată și nu rulează QAOA din nou.

Actualizarea automată folosește `st.fragment(run_every="1s")`, fără bucle de
refresh. Fiecare sesiune Streamlit are propria stare. Fundalul online poate fi
dezactivat pentru folosire fără tile-uri externe. **Reduced Motion** reduce
efectele luminoase și oprește animația indicatorului LIVE.

## Pornire

Necesită Python 3.11+; pentru versiunile exacte ale laboratorului QAOA folosește
Python 3.11–3.13. Din acest director:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

Deschide adresa locală afișată de Streamlit. Interacțiunile din sidebar
actualizează pagina în aceeași sesiune. Selectorul de fundal poate dezactiva
tile-urile online; harta și hoverul rămân disponibile fără token API.

## Structură

- `railway_data.py` — copia datelor de rețea din notebook: 8 orașe, 12 rute,
  ID-uri și ordinea celor 5 decizii QAOA.
- `railway_map.py` — validare, graf `networkx.MultiGraph`, calcule de plan și
  figură Plotly importabilă independent de Streamlit.
- `railway_simulation.py` — evenimente, ceas virtual, Replay și reconstrucția pură
  a stării la un moment ales.
- `railway_scenarios.py` — incidente și comparații de plan Before / After.
- `app.py` — dashboard, controale, scenarii și export HTML/CSV.
- `railway_results.json` — măsurările salvate ale experimentului existent.
- `tests/` — teste pentru date, hartă, simulare și comparații.

## Integrarea QAOA

`ids_din_decizii(bits, decision_route_ids)` asociază fiecare bit cu **ID-ul
fizic** al rutei în ordinea deciziilor, de exemplu:

```python
from railway_map import ids_din_decizii, deseneaza_harta
from railway_data import DEMO_IDS, ROUTES

selected_ids = ids_din_decizii([1, 0, 0, 1, 0], DEMO_IDS)  # [0, 6]
fig = deseneaza_harta(ROUTES, rute_alese=selected_ids)
```

Pentru o cheie de măsurare Qiskit, funcția inversează șirul înainte de
asociere, deoarece `x0` este la dreapta. Butonul **Aplică QAOA** alege planul
fezabil cu cel mai mare beneficiu *observat în `ideal_counts`* la bugetul de 7.
Nu rulează un nou optimizer; schimbarea bugetului sau a blocajelor actualizează
doar planul afișat și validitatea lui.

## Teste

```powershell
python -m pytest -q
```
