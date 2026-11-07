# Q-Force

> Integration note: this is the original Sabina API reference, preserved for its
> module contracts and examples. In the unified repository run
> `python -m streamlit run app.py` from the repository root. References below to
> `../app.py` describe the historical standalone layout; use the root README for
> current installation, incident handling, navigation, and HTML/PDF exports.

## Soluția clasică optimă

Aplicația Streamlit existentă este în directorul părinte (`../app.py`).
Optimizatorul și testele sunt în acest repository, în
`classical_optimizer.py` și `tests/test_classical_optimizer.py`.
Optimizatorul primește rutele în ordinea deciziilor din notebook și bugetul ales
în sidebar. Fiecare rută are `nume`, `cost` și `puncte`; opțional,
`blocata=True` interzice selectarea ei (implicit `False`).

Algoritmul evaluează toate cele `2^N` planuri, păstrează numai planurile cu
cost cel mult egal cu bugetul și maximizează suma punctelor. Returnează toate
planurile cu punctaj maxim. Planul principal are cost minim dintre acestea;
la cost egal, este ales primul vector în ordinea enumerării. Vectorul binar
urmează exact ordinea rutelor de intrare. Complexitatea este `O(N * 2^N)` în
timp, adecvată pentru cele cinci rute demonstrative. Soluția nu folosește
energia QUBO/QAOA.

### Interfața pentru ceilalți membri

```python
from classical_optimizer import (
    optimizeaza_clasic, evalueaza_plan, analizeaza_planuri, profil_bugete
)

rezultat = optimizeaza_clasic(rute, buget)
# rezultat["rute_alese"], rezultat["cost_total"], rezultat["puncte_totale"]
# rezultat["vector_binar"], rezultat["solutii_optime"]

evaluare = evalueaza_plan(rute, buget, vector_binar_qaoa)
# evaluare["cost_total"], evaluare["punctaj_total"], evaluare["este_valid"]

raport = analizeaza_planuri(rute, buget)
# raport["planuri_valide"], raport["frontiera_pareto"], raport["alternative"]

profil = profil_bugete(rute, range(16))
# câte puncte maxime poate obține fiecare buget de la 0 la 15
```

`evalueaza_plan` calculează punctajul real și verifică bugetul și rutele
blocate pentru orice vector QAOA, fără a apela modelul energetic. Ordinea
biților trebuie să fie aceeași cu ordinea rutelor transmise ambelor funcții.
`analizeaza_planuri` furnizează un certificat ușor de explicat juriului:
numărul combinațiilor verificate, numărul planurilor valide, frontiera
cost–punctaj și cele mai bune alternative suboptime. Numărătorile „peste
buget” și „rute blocate” se pot suprapune.
`profil_bugete` arată sensibilitatea soluției la buget; aplicația îl afișează
ca grafic în secțiunea clasică.

## Classical Optimization – Advanced Analysis

Motorul clasic încearcă fiecare vector binar posibil (`2^N` planuri pentru
`N` rute). Pentru cele cinci rute demonstrative sunt doar 32 de planuri.
Un plan este valid când nu alege rute blocate și costul lui nu depășește
bugetul. Dintre planurile valide alegem punctajul maxim; la egalitate,
planul principal are costul minim, apoi primul vector în ordinea enumerării.
Nu sunt folosite energia QUBO sau rezultatele QAOA pentru alegerea optimului.

### Bugetul și alternativele

`analyze_budgets(rute, max_budget)` returnează câte un rând pentru fiecare
buget întreg de la 0 la `max_budget`: costul, punctajul, bugetul rămas,
rutele și vectorul alese, numărul soluțiilor optime și câștigul față de
bugetul anterior. `este_salt_maxim` marchează cele mai mari câștiguri
pozitive din interval. În exemplul standard, bugetele 6, 7 și 8 permit
14, 15 și respectiv 18 puncte. Aplicația folosește aceste rânduri pentru
graficul „Buget vs. Punctaj maxim”.

`get_alternative_plans(rute, buget, top_k=3)` returnează `planuri` sortate
după punctaj descrescător, apoi cost crescător și vector binar. Include
egalitățile optime în top și le oferă și separat în `solutii_optime`.
Fiecare plan arată diferența de punctaj și economia de cost față de optimul
principal. `alternativa_mai_ieftina` indică cel mai bun compromis mai ieftin.
La buget 7, primele două planuri au 15 puncte și cost 7; următorul are
14 puncte și cost 6. `get_pareto_plans` returnează toate planurile valide
care nu sunt dominate de alt plan cu cost cel mult egal și punctaj cel puțin
egal, cu cel puțin o inegalitate strictă.

### Explicație și comparație cu QAOA

`explain_classical_solution(rute, buget, rezultat)` returnează un `rezumat`
în română și `indicatori` calculați: rutele, costul, punctajul, bugetul
rămas, numărul de planuri și de egalități, alternativa mai ieftină și
câștigul posibil cu o unitate suplimentară de buget. Primește rezultatul
de la `optimize_routes` sau `optimizeaza_clasic` și îl verifică pentru a nu
explica un rezultat din alt scenariu.

`evaluate_plan(rute, buget, vector)` evaluează costul și punctajul real al
unui vector QAOA, verifică bugetul și blocajele, apoi compară vectorul cu
**toate** soluțiile optime clasice. Diferențele raportate sunt „candidat
minus referința clasică”; un plan invalid poate avea punctaj mai mare decât
optimul valid. Funcția existentă `evalueaza_plan` rămâne disponibilă pentru
evaluarea simplă, fără comparație globală.

`evaluate_qaoa_distribution(rute, buget, distributie, bit_order="qiskit")`
acceptă numărări întregi sau probabilități normalizate. Returnează
probabilitatea planurilor valide, probabilitatea **tuturor** optimelor,
costul și punctajul mediu. Pentru numărări, returnează și cel mai frecvent
plan, cu validitatea lui. Nu execută QAOA și nu compară energii din modele
diferite. `railway_results.json` are câmpurile `ideal_counts` și
`backend_counts`, care pot fi evaluate direct; `real_counts` este încă `null`.

**Ordinea biților:** în vectorul clasic, primul bit corespunde primei rute.
Notebook-ul folosește `decode_key(key, n)` care inversează șirul afișat de
Qiskit. De aceea, pentru cheile de măsurare din notebook folosiți
`bit_order="qiskit"`; pentru chei deja scrise în ordinea rutelor folosiți
`bit_order="route_order"`. De exemplu, cheia Qiskit `00111` devine
vectorul `[1,1,1,0,0]`.

```python
from classical_optimizer import (
    optimize_routes, analyze_budgets, get_alternative_plans,
    explain_classical_solution, evaluate_plan, evaluate_qaoa_distribution,
)

optim = optimize_routes(rute, 7)
profil = analyze_budgets(rute, 8)
top = get_alternative_plans(rute, 7)
explicatie = explain_classical_solution(rute, 7, optim)
plan_qaoa = evaluate_plan(rute, 7, [1, 1, 1, 0, 0])
# counts = json.load(open("railway_results.json", encoding="utf-8"))["ideal_counts"]
# comparatie = evaluate_qaoa_distribution(rute, 7, counts, bit_order="qiskit")
```

Pentru un scenariu cu rute indisponibile, puneți `blocata=True` în copia
rutei sau transmiteți `blocked_routes=[index]` / `blocked_routes=["nume"]`
funcțiilor avansate. Indexul este poziția din lista transmisă, **nu** ID-ul
fizic din notebook. Datele de intrare nu sunt modificate.

Testele se rulează din `Q-Force` cu
`python -m unittest discover -s tests -v`. Aplicația existentă se pornește
cu `python -m streamlit run ../app.py`; secțiunea clasică afișează topul,
explicația și graficul. Când modulul Membrului 4 va fi disponibil,
rezultatele sale pot fi trecute în `evaluate_plan` sau
`evaluate_qaoa_distribution` fără schimbarea algoritmului cuantic.

Din directorul `Q-Force`, rulați testele și aplicația astfel:

```powershell
python -m unittest discover -s tests -v
python -m pip install streamlit  # doar dacă nu este deja instalat
python -m streamlit run ../app.py
```

În aplicație, selectați bugetul în sidebar și verificați secțiunea
„Soluția clasică optimă”. La bugetul 7, punctajul este 15, costul 7, iar
cele două planuri optime sunt `[0,1,0,1,0]` și `[1,1,1,0,0]`.
