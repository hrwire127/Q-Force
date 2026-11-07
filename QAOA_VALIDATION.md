# Verificare efectuată la 7 noiembrie 2026

Repository: `D:\Q-Force\Q-Force`. Mediul izolat folosit:
`D:\Q-Force\.venv\Scripts\python.exe`, Python 3.12.14 pe Windows.
Toate cele șase versiuni din `requirements.txt` au fost instalate exact;
`pip check` a raportat `No broken requirements found.`
Versiunile efective sunt păstrate în [validation/versions.json](validation/versions.json).
Nicio dependență nouă nu a fost adăugată în requirements.

## Teste automate

Comanda executată din repository:

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
..\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
```

Rezultat: **26 de teste trecute, 0 eșuate, 0 omise**, timp raportat de unittest
**1,360 secunde** (nu include pornirea interpretorului/importurile inițiale).
Jurnalul integral este în [validation/unittest.txt](validation/unittest.txt).

Acoperire: validarea argumentelor și a rutelor; cost internațional fără dublare;
ordinea deciziilor și ID-uri neconsecutive; egalitatea direct/QUBO/Ising prin
enumerare; fazele costului până la o fază globală; mixerul; distribuția uniformă;
parametrii și straturile p=1,2; cheile Qiskit; numărul de shots; recomandarea
validă dintre toate planurile observate și egalitățile; nicio recomandare când
toate eșantioanele sunt invalide; plan gol valid; reproducibilitate; restarturi;
referință DP versus enumerare pe 40 de probleme; toate optimele incluse în
probabilități; JSON strict; zgomot local pe 2 qubiți; măsurări corecte după mapare
nenaturală și rutare pe o linie de 3 qubiți.

Datele extinse au fost comparate cu literalurile din notebook, fără executarea
acestuia. DP și enumerarea numerică independentă a celor 524288 de planuri
confirmă optimul clasic **43**, la buget 20. Separat, o implementare simplă de DP
densă, aplicată datelor extrase din notebook, a confirmat aceeași valoare.

## Rulări cuantice efective

Toate au seed=2026, p=1, restarts=1 și aceleași limite de thread-uri de mai sus.
Timpii sunt măsurați de funcție pe acest calculator, fără importuri, și nu sunt
garanții de performanță pe alte sisteme.

| Rulare | Penalizare | maxiter / shots | Valoare QAOA validă | Cost / buget | Optim clasic | Rată validă | Frecvența tuturor optimelor | Timp total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5 rute ideal | 0.7 | 30 / 1024 | 15 | 7 / 7 | 15 | 533/1024 | 80/1024 | 0.2704 s |
| 5 rute noisy | 0.7 | 30 / 1024 | 15 | 7 / 7 | 15 | 530/1024 | 74/1024 | 0.2150 s |
| 19 rute ideal, verificare redusă | 0.7 | 4 / 128 | 41 | 20 / 20 | 43 | 12/128 | 0/128 | 16.9249 s |
| 19 rute ideal, setările implicite ale API | 4.0 | 30 / 1024 | 43 | 20 / 20 | 43 | 425/1024 | 2/1024 | 93.3734 s |

Datele complete, inclusiv counts brute, planurile selectate, unghiurile, stările
optimizatorului și timpii, sunt salvate în:

- [validation/demo_5_ideal.json](validation/demo_5_ideal.json)
- [validation/demo_5_noisy.json](validation/demo_5_noisy.json)
- [validation/smoke_19_ideal.json](validation/smoke_19_ideal.json)
- [validation/benchmark_19_ideal.json](validation/benchmark_19_ideal.json)

Comenzile folosite, cu același mediu de thread-uri:

```powershell
..\.venv\Scripts\python.exe -X utf8 examples/demo_qaoa.py --output validation/demo_5_ideal.json
..\.venv\Scripts\python.exe -X utf8 examples/demo_qaoa.py --noisy --output validation/demo_5_noisy.json
..\.venv\Scripts\python.exe -X utf8 examples/demo_qaoa.py --extended --maxiter 4 --shots 128 --output validation/smoke_19_ideal.json
..\.venv\Scripts\python.exe -X utf8 examples/demo_qaoa.py --extended --penalty 4 --output validation/benchmark_19_ideal.json
```

La 5 qubiți energia medie ideală a scăzut de la -1.1448143260 la -6.7506489286.
În rularea completă de 19 qubiți a scăzut de la 525.7159795927 la 57.2246606378;
antrenarea a durat 89.3908 s, cu 31 de evaluări, inclusiv evaluarea inițială
explicită. Circuitul ideal compilat a avut adâncime 38 și 171 porți pe doi qubiți.
Circuitul noisy de 5 qubiți a avut adâncime 53 și 34 porți pe doi qubiți;
energia medie măsurată a fost -5.9870117188, distinctă de așteptarea ideală.
Timpii scurți ai exemplelor de 5 qubiți variază între apeluri; diferența lor nu
este dovadă că simularea cu zgomot ar fi în general mai rapidă.

În toate cele patru exemple, COBYLA a raportat **status 2**,
`Maximum number of function evaluations has been exceeded.`, `succes=False`.
Bugetele configurate au fost consumate; nu se declară convergență sau minim
global. Statusul principal `ok` înseamnă că există o recomandare validă măsurată.
Observarea valorii 43 în 2 shots nu garantează repetarea succesului cu alte seed-uri
sau mai puține shots și nu reprezintă o demonstrație de avantaj cuantic.

## Verificări suplimentare și limite

- Importul modulului fără notebook: trecut.
- Compilarea sintactică a tuturor fișierelor Python livrate: trecută.
- Citirea strictă a celor cinci fișiere JSON salvate (inclusiv versiunile): trecută.
- `git diff --check`: trecut; Git a emis doar avertismentul de conversie LF/CRLF
  pentru notebook-ul deja modificat înaintea acestui task.
- La livrarea inițială a modulului, notebook-ul echipei a fost păstrat; SHA256 verificat înainte/după:
  `8d126b759fc04bc3a64e02bbc4bba96c07a044a633b3ca9ddb57f40df36ef53f`.

Nu au fost executate simulări cu zgomot pe 19 qubiți: limita implementată este
10 qubiți pentru density-matrix, din motive de memorie și performanță. Respingerea
unei astfel de cereri este testată. Nu au fost executate joburi pe hardware real,
antrenări cu 19 qubiți în suita automată, experimente cu mai multe seed-uri pe
19 qubiți sau căutări ample de adâncime/restarturi. Acestea sunt experimente
separate, nu verificări rapide obligatorii.

Nu există încă un API de aplicație sau modul de hartă separat în repository.
Integrarea disponibilă este funcția publică și rezultatul JSON, cu ID-uri stabile
și orașele rutelor. Formula originală a penalizării și limitările sale sunt
documentate în [README_QAOA.md](README_QAOA.md).

## Actualizare: corectarea notebook-ului extins

La cererea ulterioară a utilizatorului a fost modificat direct
`Quantum_Railways_Labb.ipynb`. Varianta dinaintea corectării, inclusiv rezultatele
sale vechi, este păstrată în `validation/notebook_before_fix.ipynb`.
Datele rutelor și textele originale Markdown au fost păstrate; prima celulă
explicativă primește suplimentar instrucțiunile actuale. Rezultatele vechi ale
celulelor au fost curățate pentru a evita afișarea unor rezultate neactualizate.

Corecții: dimensiunea planurilor și aserțiunile depind de numărul rutelor;
referința exhaustivă folosește vectori numerici din `notebook_support.py`;
energiile QUBO și Ising sunt verificate în blocuri pe toate configurațiile;
energia medie este un produs scalar; graficele mari afișează top 20 de planuri
observate; recomandarea este filtrată și are reguli deterministe de egalitate;
probabilitatea optimului include toate planurile optime; zgomotul și al doilea
experiment sunt opționale și explicit omise implicit pentru 19 rute.

Verificări noi:

- **29/29 teste trecute**, 0 eșuate, 0 omise, 3.181 s raportate de unittest.
  Jurnal: `validation/unittest_notebook_fix.txt`.
- Rulare integrală a codului notebook-ului cu 5 rute, buget 7 și zgomot activ:
  trecută, 1024 măsurări ideale și 1024 cu zgomot; recomandare validă cu valoare 15.
  Jurnal: `validation/notebook_5_noisy.txt`.
- Rulare integrală a codului cu configurația implicită de 19 rute și buget 20:
  trecută; verificările direct/QUBO/Ising acoperă toate cele 524288 configurații.
  Antrenare efectivă cu 30 de evaluări COBYLA, 82.428 s; 1024 măsurări ideale.
  În această rulare, recomandarea observată are valoare **42**, cost **20**,
  față de optimul clasic **43**. Energia medie a scăzut de la 121.05 (uniformă)
  la 39.8575847917. COBYLA a epuizat limita de evaluări; nu se declară convergență.
  Jurnal: `validation/notebook_19_ideal.txt`.

Rulările integrale folosesc `validation/check_notebook.py`: execută în ordine
toate celulele de cod, furnizează bugetul fără interacțiune și înlocuiește numai
afișarea IPython cu un no-op, folosind Matplotlib Agg. Avertismentele privind
afișarea neinteractivă sunt așteptate. Nu s-a verificat interfața Jupyter/VS Code
prin automatizare UI. În scenariul mic, lista deciziilor este restrânsă explicit
la cele cinci rute originale. În scenariul mare, zgomotul, extensia suplimentară
și hardware-ul real sunt omise conform configurației notebook-ului.

Pentru utilizare, reîncarcă notebook-ul de pe disc și folosește
**Restart Kernel → Run All**, introducând bugetul dorit.

## Actualizare: cost de frontieră uniform

La cererea echipei, notebook-ul și exemplul CLI folosesc acum costul de frontieră
2 pentru toate cele șase rute internaționale. Construcția și valorile economice
sunt păstrate. Costurile totale pentru ID-urile 13–18 sunt 6, 6, 5, 5, 6, 6;
costul de frontieră este inclus o singură dată în `cost`.
Varianta notebook-ului anterioară acestei schimbări, inclusiv ieșirile salvate de
utilizator, este păstrată în `validation/notebook_before_uniform_border.ipynb`.

Verificare: **29/29 teste trecute**, 0 eșuate, 0 omise, 1.804 s;
jurnal `validation/unittest_uniform_border.txt`. Celula de construire a rutelor
a fost executată separat, verificând identitatea cu exemplul CLI. DP și enumerarea
confirmă în continuare optimul clasic 43 la buget 20. Testele verifică și
energiile direct/QUBO/Ising pentru toate cele 524288 configurații actualizate.
Nu a fost repetată antrenarea QAOA lungă cu 19 qubiți pentru această modificare
de date. Rezultatele cuantice și imaginile din secțiunile anterioare și fișierele
JSON istorice se referă la costurile de frontieră de dinaintea acestei schimbări;
recomandarea curentă se recalculează prin Restart Kernel → Run All.

## Configurația curentă: cost de frontieră 1

La următoarea cerere a echipei, costul de frontieră a fost redus de la 2 la **1**
pe toate cele șase rute internaționale, atât în notebook, cât și în exemplul CLI.
Costurile totale pentru ID-urile 13–18 sunt acum **5, 5, 4, 4, 5, 5**.
Costurile de construcție, valorile economice și rutele naționale sunt păstrate.
Backup anterior schimbării: `validation/notebook_before_border_one.ipynb`.

**29/29 teste trecute**, 0 eșuate, 0 omise, 1.742 s; jurnal:
`validation/unittest_border_one.txt`. Celula notebook-ului construiește aceleași
rute ca exemplul CLI. DP dens independent, referința DP și enumerarea confirmă
noua valoare optimă clasică **46** la buget 20. Testele verifică toate cele
524288 energii direct/QUBO/Ising pentru noile date.
Antrenarea QAOA lungă de 19 qubiți nu a fost repetată pentru această modificare;
rezultatul său trebuie recalculat. Rulările și fișierele JSON din secțiunile
anterioare sunt rezultate istorice ale configurațiilor precedente.
