# Quantum Railways: QAOA real, local

Modulul `quantum_optimizer.py` este independent de notebook și nu cere tokenuri,
acces IBM Quantum sau date introduse cu `input()`. Folosește circuit Qiskit cu
Hadamard, cost RZ/RZZ, mixer RX și parametri `ParameterVector`, optimizați cu
`scipy.optimize.minimize(method="COBYLA")`.

## Instalare

Din directorul repository-ului, cu Python 3.12 (versiunea folosită la verificare):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Versiunile proiectului sunt păstrate: Qiskit 2.1.0, Qiskit Aer 0.17.0,
NumPy 2.2.6, SciPy 1.15.3, NetworkX 3.5 și Matplotlib 3.10.3.
Nu sunt adăugate dependențe. Testele folosesc `unittest` din biblioteca standard.
Un kernel de notebook sau interfața aplicației poate importa direct modulul,
din directorul repository-ului ori adăugând acest director la `sys.path`.

În sesiunea de implementare, mediul izolat este în `D:\Q-Force\.venv`, deci
comenzile de verificare pot utiliza `..\.venv\Scripts\python.exe` din repository.
Vezi `QAOA_VALIDATION.md` pentru rezultatele efectiv măsurate.

## Contractul public

```python
def optimizeaza_qaoa(
    rute, buget, penalizare=4.0, *, p=1, shots=1024,
    maxiter=30, seed=2026, restarts=1, backend_mode="ideal"
) -> dict:
    ...
```

`rute` este o secvență nevidă de dicționare. Câmpuri obligatorii:
`id` (întreg sau șir nevid unic), `cities` (două nume nevide),
`cost` (întreg nenegativ), `value` (întreg nenegativ).
`border_cost` este opțional, implicit 0, întreg între 0 și cost.
`international` este opțional, implicit False, boolean.
`cost` include deja costul frontierei; modulul nu îl adună din nou.
În scenariul extins curent, toate cele șase rute internaționale au
`border_cost=1`, conform configurației cerute de echipă. Costurile totale sunt
5, 5, 4, 4, 5, 5 pentru ID-urile 13–18; costurile naționale sunt păstrate.
Datele nu sunt modificate. Rutele returnate conțin aceste șase câmpuri normalizate,
cu `cities` ca listă JSON; metadatele suplimentare pot fi regăsite în aplicație prin ID.

Ordinea intrării stabilește ordinea deciziilor: variabila i controlează ruta de pe
poziția i, indiferent de ID. Cheile Qiskit se citesc de la dreapta spre stânga:
`"01001"` selectează pozițiile 0 și 3. Nicio regulă de conectivitate nu este impusă.

`buget` este un întreg nenegativ. `penalizare` este pozitivă și finită.
`p`, `shots`, `maxiter`, `restarts` sunt întregi pozitivi; `seed` este întreg în
[0, 2**32-1]. Booleenii nu sunt acceptați în locul numerelor.
Datele invalide și limitele de resurse sunt raportate prin `ValueError`.
Sumele costurilor, sumelor valorilor și bugetul sunt limitate la 2**50;
combinațiile ce produc overflow în energii sunt respinse.

```python
import json
from quantum_optimizer import optimizeaza_qaoa

rute = [
    {"id": 90, "cities": ("Iași", "Chișinău"), "cost": 4,
     "value": 10, "border_cost": 1, "international": True},
    {"id": 3, "cities": ("Iași", "Brașov"), "cost": 2, "value": 4},
]
rezultat = optimizeaza_qaoa(rute, buget=5, penalizare=0.7, seed=2026)
if rezultat["status"] == "ok":
    # Ruta aleasă poate fi afișată pe hartă folosind cities sau ID-ul stabil.
    for ruta in rezultat["rute_recomandate"]:
        print(ruta["id"], ruta["cities"])
print(json.dumps(rezultat, ensure_ascii=False, allow_nan=False))
```

Pentru helper-ul `draw_board` existent în notebook, transmite lista
`rezultat["ids_rute_recomandate"]` ca `selected_ids` și lista originală de rute
ca `routes`, după verificarea statusului `ok`. Astfel, harta folosește aceleași
ID-uri stabile și coordonatele deja definite în notebook.

### Notebook-ul extins corectat

`Quantum_Railways_Labb.ipynb` este adaptat pentru 19 rute. Deschide-l din acest
repository, păstrând alături `notebook_support.py`, `quantum_optimizer.py`
și `qaoa_experiments.py`,
apoi folosește **Restart Kernel → Run All** și introdu bugetul (de exemplu 20).
Notebook-ul păstrează datele rutelor și explicațiile laboratorului original.
Referința completă este stocată în vectori NumPy; se construiesc dicționare doar
pentru planurile afișate. Graficele mari arată cel mult 20 de rezultate observate.

Antrenarea din notebook compară acum **p=1 și p=2**, fiecare cu `MAXITER=30`,
`RESTARTS=1`, `IDEAL_SHOTS=4096`, aceleași date, penalizare și seed. Ambele sunt
rulate de aceeași funcție publică, folosind opțiunile COBYLA ale modulului.
Desenele circuitelor apar înaintea antrenării; fiecare fir reprezintă un qubit,
iar blocurile Cost grupează porțile RZ/RZZ. Sunt scheme logice compacte, cu numere
de porți extrase din circuitele reale, nu planificări de porți pentru hardware.
La final apar tabelul, graficul comparativ și harta/distribuția pentru p=2.
Celulele originale de backend și harta inițială continuă să folosească p=1.

Poți modifica setările în celula de antrenare. `RUN_NOISY=False` și
`RUN_EXTENSION=False` evită implicit simularea cu zgomot și o a doua antrenare.
Zgomotul poate fi activat numai pentru cel mult 10 rute. După schimbarea unui
parametru, rulează din nou celulele dependente sau întregul notebook.
O copie a versiunii anterioare se află în `validation/notebook_before_fix.ipynb`.

Rezultatele complete și desenele sunt salvate automat într-un director nou
`output/qaoa_depths/notebook_<timestamp>/`: `p1.json`, `p2.json`, `comparison.json`,
`circuit_p1.png`, `circuit_p2.png`, `comparatie.png`. Comparația poate dura câteva
minute cu 19 qubiți. Un singur seed și bugetul fix nu demonstrează superioritatea
generală a unei adâncimi.

Aceeași comparație poate fi executată separat din terminal:

```powershell
python -X utf8 examples/compare_qaoa_depths.py
python -X utf8 examples/compare_qaoa_depths.py --small
```

Modulul `qaoa_experiments.py` furnizează `run_depth_comparison`,
`draw_qaoa_layers` și `plot_depth_comparison`, fără dependențe suplimentare.

## Matematică și implementare

Pentru decizii binare x, V(x)=sum(value[i]*x[i]), C(x)=sum(cost[i]*x[i]),
validitatea reală este C(x)<=B. Modelul original este păstrat exact:

```text
E(x) = -V(x) + lambda * (C(x) - B)**2
a_i = -v_i + lambda * (c_i**2 - 2*B*c_i)
b_ij = 2*lambda*c_i*c_j, numai i<j
offset = lambda*B**2
h = -a/2 - (b.sum(axis=0) + b.sum(axis=1))/4
J = b/4
constant = offset + a.sum()/2 + b.sum()/4
```

Funcțiile independente `construct_qubo`, `qubo_energy`, `qubo_to_ising`,
`ising_energy`, `model_energy`, `analyse_plan` permit verificări externe.
QUBO și Ising sunt dicționare cu array-uri NumPy; acestea sunt obiecte matematice
de lucru. Doar rezultatul funcției principale este garantat serializabil JSON.
Perechile sunt stocate strict în triunghiul superior, fără dublare.

`parameterized_qaoa(qubo, p=1, measure=False)` întoarce `(circuit, parameters)`.
Lista explicită are ordinea `[gamma0,beta0,gamma1,beta1,...]`; legarea folosește
identitatea parametrilor, nu o presupunere despre ordinea internă Qiskit.
Costul folosește RZ(2*gamma*h_i/scale), RZZ(2*gamma*J_ij/scale),
unde scale=max(1,max(abs(h)),max(abs(J))). Mixerul folosește RX(2*beta).
Constanta este omisă numai ca fază globală a circuitului.

Antrenarea construiește o singură dată vectorul numeric al energiilor, în ordinea
bazei Qiskit. Fiecare evaluare leagă parametrii și calculează
`Statevector.from_instruction(bound).probabilities() @ energies`.
Nu creează dicționare pentru fiecare stare în funcția obiectiv.
Punctele inițiale sunt aleatoare, reproductibile prin `numpy.random.default_rng`.
Se păstrează cel mai bun punct evaluat, inclusiv punctul inițial, pentru fiecare
restart, apoi cel mai bun restart. Nu există garanție de minim global.

`maxiter` este bugetul COBYLA pentru fiecare restart (evaluări ale obiectivului în
SciPy 1.15). O evaluare inițială explicită este adăugată fiecărui restart și este
inclusă în `evaluari`, separat de `evaluari_scipy`. Statusul COBYLA poate indica
epuizarea bugetului; rezultatul cuantic măsurat poate avea totuși status `ok`.

## Măsurări, referință și interpretarea rezultatului

După antrenare se adaugă registrul clasic `plan`, se compilează circuitul legat
și se rulează Aer cu exact `shots` măsurări. Recomandarea maximizează valoarea
exclusiv între planurile valide observate; egalitățile preferă costul mai mic,
apoi cheia Qiskit lexicografic mai mică. Planul gol este o soluție validă.
Cel mai frecvent plan este raportat separat și poate depăși bugetul.

`classical_reference(rute, buget)` folosește programare dinamică exactă 0/1
cu frontieră rară, eliminând stările dominate. Nu se folosește ca substitut pentru
recomandarea QAOA. Poate exista mai mult de un optim: probabilitățile optimului
adună toate planurile valide cu valoarea optimă, indiferent de ID-uri sau cost.

Câmpurile principale ale rezultatului:

| Câmp | Semnificație |
| --- | --- |
| `status` | `ok` sau `no_valid_sample` |
| `rute_recomandate`, `ids_rute_recomandate`, `bitstring_recomandat` | Cel mai bun plan valid efectiv observat |
| `cost_total`, `valoare_totala`, `buget`, `buget_ramas`, `valid` | Totaluri și validitate reală |
| `probabilitate_plan_recomandat` | Frecvența empirică a recomandării / shots |
| `rata_planuri_valide` | Fracția empirică de măsurări valide, între 0 și 1 |
| `probabilitate_optim_valid` | Fracția empirică a tuturor optimelor valide |
| `energie_medie` | Așteptarea exactă ideală după antrenare, cu constanta inclusă |
| `energie_medie_initiala` | Energia inițială a restartului selectat |
| `energie_medie_masurata` | Energia empirică a distribuției măsurate, inclusiv planuri invalide |
| `probabilitate_valida_ideala`, `probabilitate_optim_valid_ideala` | Probabilități exacte ideale, distincte de frecvențele măsurate |
| `unghiuri_optime`, `gamma`, `beta` | Unghiuri în radiani, cu ordinea documentată |
| `referinta_clasica` | `valoare_optima`, `cost_total`, `ids_rute`, `bitstring` |
| `diferenta_valoare` | Optim clasic minus valoarea recomandată |
| `cel_mai_frecvent_plan`, `top_planuri`, `counts` | Plan modal, cel mult 20 planuri frecvente, toate frecvențele brute |
| `optimizare` | Metoda, restartul selectat și rezultatele tuturor restarturilor, inclusiv status și mesaj |
| `statistici` | Qubiți, straturi, shots, seed, backend, evaluări, timpi măsurați și resurse de compilare |

Pentru `no_valid_sample`, listele recomandate sunt goale, `valid=False`,
`cost_total`, `valoare_totala`, `buget_ramas`, `bitstring_recomandat` și
`diferenta_valoare` sunt `None` (JSON null). Acest caz nu este prezentat ca un plan
gol valid. Referința clasică și distribuția efectiv măsurată rămân disponibile.

## Limita conceptuală a bugetului

Modelul penalizează și cheltuirea sub buget. Minimul energiei nu garantează nici
validitatea, nici valoarea optimă sub constrângerea C<=B. Exemplul original cu
5 rute, B=7, lambda=0.7: rutele 0,2,6 au cost 8, valoare 18 și energie -17.3;
planul este invalid. Optimul clasic valid are valoare 15 și cost 7.
Acest defect de model este demonstrat prin teste, fără schimbarea formulei.

O corecție separată posibilă este introducerea unei variabile slack nenegative s
și penalizarea `(C+s-B)**2`, cu codificare binară suficientă pentru s și o pondere
justificată matematic. Aceasta crește numărul de qubiți și cere un QUBO nou,
teste noi și o nouă politică de decodare. Nu este implementată în versiunea curentă.
`max(0,C-B)**2` nu este înlocuit tacit în QUBO.

## Scalare, benchmark și zgomot

Simularea ideală are cost exponențial în qubiți. Pentru 19 rute sunt 524288 stări,
iar vectorul complex de bază ocupă 8 MiB; se adaugă vectorii de costuri/valori,
energii, probabilități și copii temporare ale simulatorului. La p=1 și costuri
nenule există până la 171 interacțiuni RZZ. Fiecare evaluare reface evoluția
cuantică; reducerea dicționarelor clasice nu elimină acest cost.

Politica explicită: cel mult 20 qubiți, p<=100 și cel mult 20000 RZZ.
Pentru >=19 qubiți se emite `RuntimeWarning`. Limitele pot fi adaptate explicit
în constantele modulului după evaluarea memoriei disponibile; nu sunt o garanție
de durată sau de memorie maximă pentru orice calculator. Referința DP rară poate
avea și ea frontieră mare în cazuri nefavorabile.

Exemplele se execută separat de testele rapide:

```powershell
python -X utf8 examples/demo_qaoa.py
python -X utf8 examples/demo_qaoa.py --p 2 --maxiter 80 --restarts 3
python -X utf8 examples/demo_qaoa.py --extended --classical-only
python -X utf8 examples/demo_qaoa.py --extended --maxiter 30 --output benchmark_19.json
python -X utf8 examples/demo_qaoa.py --noisy --output demo_noisy.json
```

Datele celor 19 rute sunt sincronizate cu notebook-ul echipei, inclusiv costul
uniform de frontieră 1 pentru fiecare rută internațională,
fără a executa notebook-ul. Testele verifică identitatea datelor prin extragere AST
a literalilor, referința DP și enumerarea numerică independentă: optimul clasic
la B=20 este 46. Această valoare nu este introdusă în algoritmul QAOA.

Modul implicit `ideal` folosește Aer statevector pentru măsurarea finală și
marchează zgomotul `omisa_mod_ideal`. `backend_mode="noisy"` păstrează antrenarea
ideală și măsoară apoi pe un `GenericBackendV2` sintetic local, cu topologie liniară
și zgomot generat reproducibil. Se compilează după legarea unghiurilor și se
simulează cu `AerSimulator.from_backend(..., method="density_matrix")`.
Rezultatul raportează adâncimea compilată, porțile pe doi qubiți și maparea finală.
Citirea este din biții clasici `plan[i]`, fără inversarea mapării fizice.
Acest zgomot nu reprezintă calibrarea unui calculator cuantic real.

Zgomotul emite avertisment de performanță și este limitat la 10 qubiți pentru a
evita alocări density-matrix de ordinul 4**n. O cerere noisy cu 19 rute este
respinsă explicit; nu se produce un rezultat ideal etichetat drept noisy.
`energie_medie` și câmpurile sufixate `_ideala` rămân ideal-teoretice chiar în
modul noisy; frecvențele și `energie_medie_masurata` provin exclusiv din backendul
selectat. Nu se amestecă distribuțiile.

## Verificare

```powershell
python -m unittest discover -s tests -v
```

Suita verifică intrările, border_cost, ordinea deciziilor, toate energiile
QUBO/Ising ale unor probleme mici, fazele costului, mixerul, parametrii, distribuția
uniformă, shots, decodarea, referința DP versus enumerare, toate optimele în metrice,
absența eșantioanelor valide, reproductibilitatea, JSON strict și zgomotul local pe
2 qubiți. Un test separat verifică măsurarea după mapare și rutare fizică nenaturală.
Nu execută antrenări cu 19 qubiți în testele automate.

Documentație API folosită:
[Qiskit 2.1 QuantumCircuit](https://quantum.cloud.ibm.com/docs/en/api/qiskit/2.1/qiskit.circuit.QuantumCircuit),
[AerSimulator](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.AerSimulator.html).
