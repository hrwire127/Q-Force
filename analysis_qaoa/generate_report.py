"""Compare saved observations, without rerunning QAOA or altering source files."""
import ast
import hashlib
import html
import json
from pathlib import Path
import re
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from quantum_optimizer import classical_reference, decode_key

TEAL, GOLD, NAVY, CORAL = '#008d83', '#bc871d', '#17334a', '#cf574e'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.titleweight': 'bold', 'savefig.facecolor': 'white'})


def notebook_data(path):
    nb = json.loads(path.read_text(encoding='utf-8'))
    data = {}
    for c in nb['cells']:
        if c['cell_type'] != 'code': continue
        for node in ast.parse(''.join(c['source'])).body:
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                name = node.targets[0].id
                if name in ('EDGE_DATA', 'INTERNATIONAL_EDGES', 'POSITIONS'):
                    data[name] = ast.literal_eval(node.value)
    routes = [dict(id=i, cities=[u,v], cost=c, value=vlu, border_cost=0, international=False)
              for i,(u,v,c,vlu) in enumerate(data['EDGE_DATA'])]
    for u,v,c,vlu,b in data['INTERNATIONAL_EDGES']:
        routes.append(dict(id=len(routes), cities=[u,v], cost=c+b, value=vlu,
                           border_cost=b, international=True))
    return nb, routes, data['POSITIONS']


def policy(routes):
    costs = {r['border_cost'] for r in routes if r['international']}
    return 'fără internaționale' if not costs else ('variabilă' if len(costs)>1 else str(next(iter(costs))))


def text_outputs(nb, index):
    return '\n'.join(''.join(o.get('text', [])) for o in nb['cells'][index].get('outputs', []))


def markdown_outputs(nb, index):
    return [''.join(o['data']['text/markdown']) for o in nb['cells'][index].get('outputs', [])
            if 'text/markdown' in o.get('data', {})]


def table_rows(text):
    return [[s.strip() for s in line.strip().strip('|').split('|')]
            for line in text.splitlines() if line.startswith('|')][2:]


def load_nb(path, label):
    nb, routes, _ = notebook_data(path)
    tables = markdown_outputs(nb,24)
    plans = table_rows(tables[0])
    best = plans[1]
    bits = ast.literal_eval(best[0])
    if len(bits) != len(routes):
        raise ValueError('Saved decision width differs from source route data')
    metrics = {row[0]: float(row[1]) for row in table_rows(tables[1])}
    train = text_outputs(nb,22)
    budget = int(re.search(r'Buget:\s*(\d+)',text_outputs(nb,4))[1])
    penalty = float(re.search(r'WEAK_PENALTY\s*=\s*([\d.]+)',''.join(nb['cells'][4]['source']))[1])
    r = dict(label=label, source=str(path.relative_to(ROOT)), kind='notebook',
             routes=routes, border=policy(routes), n=len(routes), budget=budget,
             penalty=penalty, backend='ideal', shots=int(metrics['shots']),
             selected=ast.literal_eval(best[2]), cost=int(best[3]), value=int(best[4]),
             valid_rate=metrics['feasible_rate'], opt_rate=metrics['optimal_feasible_probability'],
             energy=float(re.search(r'Optimised expected energy:\s*([^\n]+)',train)[1]),
             sampled_energy=metrics['expected_energy'],
             evaluations=int(re.search(r'Evaluations:\s*(\d+)',train)[1]),
             training_s=float(re.search(r'local training seconds:\s*([\d.]+)',train)[1]),
             maxiter=int(re.search(r'MAXITER\s*=\s*(\d+)',''.join(nb['cells'][22]['source']))[1]),
             restarts=int(re.search(r'RESTARTS\s*=\s*(\d+)',''.join(nb['cells'][22]['source']))[1]),
             converged='Optimiser success: True' in train,
             counts_available=False, rates_rounded=True)
    # Verify that the saved classical row agrees with source data, not today's data.
    ref = classical_reference(routes,budget)
    assert int(plans[3][4]) == ref['valoare_optima']
    r['reference'] = ref
    return r


def load_json(path, label, original):
    data = json.loads(path.read_text(encoding='utf-8'))
    st = data['statistici']
    routes = original if st['numar_qubiti']==19 else [original[i] for i in (0,1,2,6,8)]
    ref = classical_reference(routes,data['buget'])
    assert ref['valoare_optima']==data['referinta_clasica']['valoare_optima']
    r = dict(label=label, source=str(path.relative_to(ROOT)), kind='json',
             routes=routes, border=policy(routes), n=len(routes), budget=data['buget'],
             penalty=data['penalizare'], backend=st['backend'], shots=st['shots'],
             selected=data['ids_rute_recomandate'], cost=data['cost_total'], value=data['valoare_totala'],
             valid_rate=data['rata_planuri_valide'], opt_rate=data['probabilitate_optim_valid'],
             energy=data['energie_medie'], sampled_energy=data['energie_medie_masurata'],
             evaluations=st['evaluari'], training_s=st['timp_antrenare_secunde'],
             maxiter=st['maxiter'], restarts=st['restarts'],
             converged=data['optimizare']['rulari'][data['optimizare']['restart_selectat']]['succes'],
             reference=ref, counts_available=True, rates_rounded=False)
    total = valid = optimum = 0
    observed_best = -1
    for key,count in data['counts'].items():
        chosen = [route for bit,route in zip(decode_key(key,len(routes)),routes) if bit]
        cost, value = sum(v['cost'] for v in chosen), sum(v['value'] for v in chosen)
        total += count
        if cost<=r['budget']:
            valid += count
            optimum += count*(value==ref['valoare_optima'])
            observed_best = max(observed_best,value)
    assert total==r['shots'] and observed_best==r['value']
    assert np.isclose(valid/total,r['valid_rate']) and np.isclose(optimum/total,r['opt_rate'])
    assert data['counts'][data['bitstring_recomandat']]>0
    r['valid_count'], r['optimal_count'] = valid, optimum
    r['distribution_hash'] = hashlib.sha256(json.dumps(data['counts'],sort_keys=True).encode()).hexdigest()
    # Saved selected routes must match the archived source scenario.
    by_id={v['id']:v for v in routes}
    for route in data['rute_recomandate']:
        assert route['cost']==by_id[route['id']]['cost'] and route['value']==by_id[route['id']]['value']
    return r


def validate(r):
    selected = [v for v in r['routes'] if v['id'] in r['selected']]
    assert len(selected)==len(r['selected'])
    assert sum(v['cost'] for v in selected)==r['cost']<=r['budget']
    assert sum(v['value'] for v in selected)==r['value']<=r['reference']['valoare_optima']
    r['gap'] = r['reference']['valoare_optima']-r['value']
    r['quality'] = r['value']/r['reference']['valoare_optima']


def run_chart(r):
    selected = [v for v in r['routes'] if v['id'] in r['selected']]
    fig = plt.figure(figsize=(15,7.7),layout='constrained')
    gs=fig.add_gridspec(2,2,width_ratios=[1.7,1])
    ax=fig.add_subplot(gs[:,0])
    y=np.arange(len(selected))
    ax.barh(y-0.18,[v['cost'] for v in selected],height=.34,color=GOLD,label='Cost total (include frontiera)')
    ax.barh(y+0.18,[v['value'] for v in selected],height=.34,color=TEAL,label='Valoare economică')
    ax.set_yticks(y,[f"{v['id']}: {'–'.join(v['cities'])}" for v in selected])
    ax.invert_yaxis(); ax.set_xlabel('Unități fictive'); ax.set_title('Conexiunile recomandate de QAOA',loc='left',pad=42)
    for i,v in enumerate(selected):
        ax.text(v['cost']+.08,i-.18,str(v['cost']),va='center',fontsize=10)
        ax.text(v['value']+.08,i+.18,str(v['value']),va='center',fontsize=10)
    ax.set_xlim(0,max(v['value'] for v in selected)+2)
    ax.legend(loc='lower left',bbox_to_anchor=(0,1.01),fontsize=9,ncol=2)
    ax=fig.add_subplot(gs[0,1])
    ax.bar(['QAOA observat','Optim clasic'],[r['value'],r['reference']['valoare_optima']],color=[TEAL,NAVY])
    for i,v in enumerate([r['value'],r['reference']['valoare_optima']]): ax.text(i,v+.3,str(v),ha='center',fontweight='bold')
    ax.set_ylim(0,r['reference']['valoare_optima']*1.22)
    ax.set_title(f"Cost {r['cost']}/{r['budget']} · diferență {r['gap']}")
    ax=fig.add_subplot(gs[1,1]); ax.axis('off')
    txt=(f"Planuri valide: {100*r['valid_rate']:.2f}%\n"
         f"Optime valide măsurate: {100*r['opt_rate']:.3f}%\n"
         f"Măsurări finale: {r['shots']}\n"
         f"Evaluări: {r['evaluations']} · restarturi: {r['restarts']}\n"
         f"Timp antrenare: {r['training_s']:.2f} s\n"
         f"Convergență COBYLA: {'da' if r['converged'] else 'limită evaluări'}\n"
         f"Energie medie ideală: {r['energy']:.4f}\n"
         f"Energie medie măsurată: {r['sampled_energy']:.4f}")
    ax.text(0,1,txt,va='top',linespacing=1.65,fontsize=11,color=NAVY)
    fig.suptitle(f"{r['id']} · {r['label']}\n{r['n']} rute · frontieră {r['border']} · λ={r['penalty']} · {r['backend']}",fontsize=16,color=NAVY)
    filename=f"{r['id'].lower()}_rezultat.png"
    fig.savefig(OUT/filename,dpi=150); plt.close(fig)
    return filename


def draw_network(ax,routes,ids,positions,title,color):
    g=nx.Graph(); g.add_nodes_from(positions); g.add_edges_from(v['cities'] for v in routes)
    nx.draw_networkx_edges(g,positions,ax=ax,edge_color='#d7dfe3',width=1.3)
    selected=[v for v in routes if v['id'] in ids]
    nx.draw_networkx_edges(g,positions,edgelist=[v['cities'] for v in selected],ax=ax,edge_color=color,width=4)
    used={c for v in selected for c in v['cities']}
    nx.draw_networkx_nodes(g,positions,ax=ax,node_size=65,node_color=['white' if c not in used else color for c in g],edgecolors=NAVY)
    labels={c:(x,y+.15) for c,(x,y) in positions.items()}
    labels['Iași']=(positions['Iași'][0]-.25,positions['Iași'][1]+.20)
    labels['Chișinău']=(positions['Chișinău'][0]+.25,positions['Chișinău'][1]-.27)
    labels['Brașov']=(positions['Brașov'][0]+.6,positions['Brașov'][1])
    labels['Sibiu']=(positions['Sibiu'][0]-.3,positions['Sibiu'][1]-.20)
    nx.draw_networkx_labels(g,labels,ax=ax,font_size=10,font_color=NAVY)
    nx.draw_networkx_edge_labels(g,positions,ax=ax,font_size=9,
        edge_labels={tuple(v['cities']):f"{v['id']}: {v['cost']}/{v['value']}" for v in selected},
        bbox={'facecolor':'white','edgecolor':'none','alpha':.9},rotate=True)
    ax.set_title(title,fontsize=14,color=NAVY)
    ax.set_aspect(1/np.cos(np.deg2rad(46)))
    ax.margins(.16); ax.axis('off')


def main():
    _, original, _=notebook_data(ROOT/'validation/notebook_before_uniform_border.ipynb')
    specs=[('validation/demo_5_ideal.json','5 rute: ideal'),
           ('validation/demo_5_noisy.json','5 rute: zgomot'),
           ('rezultat.json','5 rute: rularea utilizatorului'),
           ('validation/smoke_19_ideal.json','19 rute: rulare redusă'),
           ('validation/benchmark_19_ideal.json','19 rute: 30 evaluări COBYLA'),
           ('rezultat19_extins.json','19 rute: 150 evaluări × 3 restarturi')]
    results=[load_json(ROOT/p,label,original) for p,label in specs]
    for p,label in [('validation/notebook_before_uniform_border.ipynb','Notebook: frontieră variabilă'),
                    ('validation/notebook_before_border_one.ipynb','Notebook: frontieră 2'),
                    ('Quantum_Railways_Labb.ipynb','Notebook actual: frontieră 1')]:
        results.append(load_nb(ROOT/p,label))
    for i,r in enumerate(results,1):
        r['id']=f'R{i}'; validate(r); r['chart']=run_chart(r)
    current=results[-1]
    assert current['border']=='1' and current['value']==45 and current['reference']['valoare_optima']==46
    _,_,positions=notebook_data(ROOT/'Quantum_Railways_Labb.ipynb')
    fig,axes=plt.subplots(1,2,figsize=(17,8.5),layout='constrained')
    draw_network(axes[0],current['routes'],current['selected'],positions,'QAOA măsurat: valoare 45 · cost 20',TEAL)
    draw_network(axes[1],current['routes'],current['reference']['ids_rute'],positions,'Un optim clasic exact: valoare 46 · cost 20',GOLD)
    fig.suptitle('Configurația actuală · frontieră 1 · buget 20\nEtichete: ID rută: cost total / valoare · conexiuni fictive, nedirecționate',fontsize=15,color=NAVY)
    fig.savefig(OUT/'harti_configuratie_actuala.png',dpi=150); plt.close(fig)
    fig,ax=plt.subplots(figsize=(13,8),layout='constrained'); y=np.arange(len(results))
    ax.barh(y-.18,[r['value'] for r in results],height=.34,color=TEAL,label='Cel mai bun plan QAOA măsurat')
    ax.barh(y+.18,[r['reference']['valoare_optima'] for r in results],height=.34,color=NAVY,label='Optim clasic în același scenariu')
    ax.set_yticks(y,[f"{r['id']} · {r['n']} rute · frontieră {r['border']}\n{r['label']}" for r in results],fontsize=10)
    for i,r in enumerate(results):
        for dy,v in [(-.18,r['value']),(.18,r['reference']['valoare_optima'])]: ax.text(v+.3,i+dy,str(v),va='center',fontsize=10)
    ax.invert_yaxis(); ax.set_xlim(0,54); ax.set_xlabel('Valoare economică fictivă')
    ax.set_title('Valoarea observată și referința exactă pentru fiecare rulare',color=NAVY,pad=42)
    ax.legend(loc='lower left',bbox_to_anchor=(0,1.01),fontsize=9,ncol=2)
    fig.savefig(OUT/'comparatie_valori.png',dpi=150); plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(16,7),layout='constrained')
    for ax,field,title,factor in zip(axes,['valid_rate','opt_rate','training_s'],
            ['Planuri valide (%)','Optime valide măsurate (%)','Timp de antrenare (secunde, scară log)'],[100,100,1]):
        ax.barh(y,[r[field]*factor for r in results],color=[TEAL if r['id']=='R9' else NAVY for r in results])
        ax.set_yticks(y,[r['id'] for r in results]); ax.invert_yaxis(); ax.set_title(title,fontsize=11)
        if field=='training_s': ax.set_xscale('log')
    fig.suptitle('Distribuție și efort de calcul · compararea modelelor diferite este descriptivă',color=NAVY,fontsize=14)
    fig.savefig(OUT/'comparatie_probabilitati_timpi.png',dpi=150); plt.close(fig)

    headers=['Rulare','Rute','Frontieră','λ','Shots','Cost','Valoare QAOA','Optim clasic','Diferență','Valide %','Optime %','Evaluări','T antr. s','Convergență']
    rows=[]
    for r in results:
        rows.append([r['id'],str(r['n']),r['border'],str(r['penalty']),str(r['shots']),str(r['cost']),str(r['value']),
                     str(r['reference']['valoare_optima']),str(r['gap']),f"{100*r['valid_rate']:.2f}",f"{100*r['opt_rate']:.3f}",
                     str(r['evaluations']),f"{r['training_s']:.2f}",'Da' if r['converged'] else 'Limită evaluări'])
    md=['# Analiza rezultatelor Quantum Railways','',
        'Analiză a rezultatelor salvate; nu au fost executate antrenări QAOA noi.',
        'Configurația actuală este cea cu frontieră 1. Costurile, valorile și referințele sunt verificate pentru fiecare versiune a datelor.',
        '', '## Concluzia pentru configurația actuală','',
        'Cel mai bun plan valid măsurat are **valoare 45, cost 20**. Optimul clasic exact este **46, cost 20**. Raportul valorilor este **97.83%**, diferența 1.',
        'Din 1024 măsurări, rata validă afișată este aproximativ **29.00%**, iar probabilitatea empirică a optimului valid este **0%**. Aceste metrice provin din tabelul rotunjit al notebook-ului; counts brute nu sunt salvate pentru această rulare.',
        'COBYLA a consumat 30 evaluări, fără convergență confirmată; timpul de antrenare este 84.611 s. Energia ideală medie finală este 38.0251363296, iar energia medie măsurată este aproximativ 40.58506.',
        '', '## Tabel final','', '| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']
    md+=['| '+' | '.join(row)+' |' for row in rows]
    md+=['','## Surse și grafice individuale','']
    for r in results:
        md += [f"### {r['id']} — {r['label']}",'',f"Sursă: `{r['source']}`. ID-uri recomandate: `{r['selected']}`.",'',f"![{r['label']}]({r['chart']})",'']
    md+=['## Rutele configurației actuale','', '| ID | Conexiune | Frontieră | Cost total | Valoare | Valoare/cost |','| --- | --- | --- | --- | --- | --- |']
    for v in current['routes']:
        if v['id'] in current['selected']:
            md.append(f"| {v['id']} | {'–'.join(v['cities'])} | {v['border_cost']} | {v['cost']} | {v['value']} | {v['value']/v['cost']:.2f} |")
    md+=['| **Total** | | **2** | **20** | **45** | **2.25** |','',
         'Conexiunea selectată cu cea mai mare valoare individuală este **Iași–Cernăuți: valoare 11, cost 5**. Cele mai bune rapoarte valoare/cost din plan sunt **Cluj-Napoca–Brașov (5/2)** și **Iași–Chișinău (10/4)**, ambele 2.5. Aceste criterii individuale nu garantează cel mai bun ansamblu.',
         'Planul conține Iași–Brașov, Iași–Cluj-Napoca, Cluj-Napoca–Brașov, Brașov–București, Iași–Chișinău și Iași–Cernăuți. Este o rețea cu ramificații și un ciclu; modelul nu definește o origine, o destinație sau un itinerar unic.',
         '', '## Un optim clasic exact pentru aceeași configurație','', '| ID | Conexiune | Cost total | Valoare |','| --- | --- | --- | --- |']
    for v in current['routes']:
        if v['id'] in current['reference']['ids_rute']:
            md.append(f"| {v['id']} | {'–'.join(v['cities'])} | {v['cost']} | {v['value']} |")
    md+=['| **Total** | | **20** | **46** |','',
         'Acest plan este referința clasică, nu o recomandare QAOA măsurată în ultima rulare. Pot exista mai multe planuri cu aceeași valoare optimă.',
         '', '## Comparație și limite','',
         '- R5 și R6 folosesc aceleași 19 rute inițiale, frontieră variabilă și λ=4. R6 consumă 275 evaluări și converge, față de 31 la R5. Ambele măsoară valoarea 43. Frecvența optimelor este 6/4096 la R6 și 2/1024 la R5; numărul mic de observații nu susține o concluzie că una este statistic mai fiabilă.',
         '- R7, R8 și R9 sunt rulări notebook cu λ=0.7 și buget 20, dar costurile problemei diferă. Valorile observate sunt 42, 42 și 45; optimele clasice sunt 43, 43 și 46. Creșterea la 45 nu poate fi atribuită exclusiv algoritmului: s-au ieftinit rutele internaționale.',
         '- R1 și R2 compară idealul cu zgomotul sintetic pe 5 rute. Ambele găsesc valoarea 15. O singură pereche de rulări nu izolează riguros efectul zgomotului.',
         '- R1 și R3 au aceleași counts și aceiași parametri, cu timpi diferiți în fișiere; nu sunt tratate drept replicări independente.',
         '- Energiile din scenarii cu penalizări/costuri diferite nu trebuie clasificate într-un clasament comun. Timpul raportat în tabel este exclusiv timpul de antrenare, nu durata totală.',
         '- Datele notebook sunt rezumate rotunjite. Nu reconstruim counts brute sau unghiuri lipsă. Pentru fișierele JSON, counts și toate metricele de validitate/optim au fost reverificate.',
         '- `validation/notebook_before_fix.ipynb` nu este inclus în comparație: ieșirile salvate au 5 biți, iar sursa definește 19 decizii. Această neconcordanță împiedică atribuirea sigură a rezultatelor la configurația sursă.',
         '- Nu există o garanție de optim QAOA, de minim global COBYLA sau de avantaj cuantic. Referințele clasice și rezultatele QAOA rămân distincte.',
         '', '## Grafice comparative','', '![Valori](comparatie_valori.png)','', '![Probabilități și timp](comparatie_probabilitati_timpi.png)','', '![Hărți actuale](harti_configuratie_actuala.png)']
    (OUT/'raport_comparativ.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    (OUT/'rezultate_verificate.json').write_text(json.dumps(results,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    # Portable static HTML with figures and an exact table; no external resources.
    body=['<h1>Quantum Railways · comparația rezultatelor</h1>',
          '<p class="lead">Configurația actuală: frontieră 1 · QAOA observat <b>45</b> / optim clasic <b>46</b> · cost <b>20/20</b></p>',
          '<p>Analiză a rulărilor salvate, fără antrenări cuantice noi. Datele diferite sunt etichetate separat. Consultați raportul Markdown pentru proveniență și limite.</p>',
          '<nav><a href="raport_comparativ.md">Raport complet și tabele de rute</a> · <a href="rezultate_verificate.json">Date verificate JSON</a></nav>',
          '<h2>Tabel final</h2><div class="scroll"><table><thead><tr>']
    body += ['<th>'+html.escape(x)+'</th>' for x in headers]
    body += ['</tr></thead><tbody>']
    for row in rows: body += ['<tr>'+''.join('<td>'+html.escape(x)+'</td>' for x in row)+'</tr>']
    body+=['</tbody></table></div><p>Timpii sunt de antrenare. R1/R3 au aceeași distribuție salvată. R7–R9 folosesc metrice notebook rotunjite.</p>']
    for filename,title in [('harti_configuratie_actuala.png','Configurația actuală: QAOA și referința clasică'),('comparatie_valori.png','Valoare observată versus optimul fiecărui scenariu'),('comparatie_probabilitati_timpi.png','Distribuție și efort')]:
        body += [f'<h2>{title}</h2><img src="{filename}" alt="{title}">']
    for r in results:
        body += [f"<h2>{r['id']} · {html.escape(r['label'])}</h2><p>Sursă: {html.escape(r['source'])} · ID-uri selectate: {r['selected']}</p><img src=\"{r['chart']}\" alt=\"{r['id']}\">"]
    document='<!doctype html><html lang="ro"><meta charset="utf-8"><title>Analiză QAOA</title><style>body{font:16px system-ui;color:#17334a;max-width:1400px;margin:40px auto;padding:0 24px;background:#f6f8fa}h1{font-size:32px}h2{margin-top:48px}.lead{font-size:22px}img{width:100%;background:white;border-radius:12px}table{border-collapse:collapse;background:white;width:100%;font-size:13px}td,th{padding:10px;border-bottom:1px solid #dce4e8;text-align:left;white-space:nowrap}th{background:#17334a;color:white}.scroll{overflow:auto}nav{margin:24px 0}a{color:#008d83}</style>'+''.join(body)+'</html>'
    (OUT/'raport_comparativ.html').write_text(document,encoding='utf-8')
    print(json.dumps({'verified_results':len(results),'png_charts':len(list(OUT.glob('*.png'))),'current_value':current['value'],'current_reference':current['reference']['valoare_optima'],'current_ids':current['selected']},ensure_ascii=False))


if __name__=='__main__': main()
