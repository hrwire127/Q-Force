"""Self-contained HTML and PDF exports from the same experiment snapshot."""
import base64
from html import escape
from io import BytesIO
import json
import textwrap
from matplotlib.figure import Figure
from matplotlib.backends.backend_pdf import PdfPages
from railway_catalog import POSITIONS
from analysis_views import probability_rows,score_rows,resource_rows,distribution_rows


def report_figures(result):
    figures = []
    network=result.get('scenario',{}).get('routes',result['routes'])
    plans = [('Classical optimum',result['classical']),('QUBO energy minimum',result['qubo_minimum'])]
    plans += [(f'{mode}: best feasible sample',s['best_feasible']) for mode,s in result['samples'].items()]
    fig = Figure(figsize=(10,7),layout='constrained')
    axes = list(fig.subplots(2,2).flat)
    for ax,(title,plan) in zip(axes,plans):
        ids = set(plan['ids_rute']) if plan else set()
        for route in network:
            points = [POSITIONS[city] for city in route['cities']]
            selected = route['id'] in ids
            color='#EF4444' if route.get('status')=='blocked' else '#3B82F6' if selected else '#F59E0B' if route.get('status')=='degraded' else '#cbd5e1'
            ax.plot(*zip(*points),color=color,lw=3 if selected or route.get('status')=='blocked' else 1,
                    linestyle='--' if route.get('status')=='blocked' else '-')
            if route.get('incident_ids'):
                ax.annotate('!',tuple(sum(p[i] for p in points)/2 for i in (0,1)),color='#EF4444',weight='bold')
        cities = {c for r in network for c in r['cities']}
        for city in cities:
            lon,lat = POSITIONS[city]; ax.scatter(lon,lat,s=12,c='#17334a'); ax.annotate(city,(lon,lat),fontsize=7)
        ax.set_title(title + (f"\nCost {plan['cost_total']}, score {plan['valoare_totala']}, energy {plan['energie']:.2f}, valid={plan['valid']}" if plan else '\nNo feasible sample'),fontsize=9)
        ax.margins(.2); ax.axis('off')
    for ax in list(axes)[len(plans):]: ax.axis('off')
    figures.append(('Schematic network - blue selected, red closed, orange degraded; ! simulated incident',fig))
    fig = Figure(figsize=(10,5),layout='constrained'); ax=fig.subplots()
    by_mode={mode:{r['bitstring']:r['probability'] for r in sample['distribution']} for mode,sample in result['samples'].items()}
    keys=set().union(*(values.keys() for values in by_mode.values()))
    if len(keys)>32:
        keys=sorted(keys,key=lambda k:-max(values.get(k,0) for values in by_mode.values()))[:32]
    keys=sorted(keys); width=.8/len(by_mode)
    for index,(mode,values) in enumerate(by_mode.items()):
        ax.bar([i+(index-(len(by_mode)-1)/2)*width for i in range(len(keys))],
               [values.get(k,0) for k in keys],width=width,label=mode)
    ax.set_xticks(range(len(keys)),[k or '(empty)' for k in keys],fontsize=7)
    ax.set(xlabel='Measured key (decision 0 at right); up to 32 shared states',ylabel='Probability')
    ax.tick_params(axis='x',rotation=90); ax.legend(); figures.append(('Measurement distribution',fig))
    fig=Figure(figsize=(10,4),layout='constrained'); ax=fig.subplots()
    history=result['quantum']['optimizare']['history']
    if not history:
        ax.text(.5,.5,'All routes closed: deterministic empty plan. No quantum circuit executed.',ha='center',wrap=True)
    for restart in range(result['config']['restarts']):
        points=[r for r in history if r['restart']==restart]
        ax.plot([r['evaluation'] for r in points],[r['energy'] for r in points],label=f'Restart {restart+1}')
    ax.set(xlabel='Objective evaluation',ylabel='Exact ideal expected energy'); ax.legend()
    figures.append(('QAOA convergence (ideal training)',fig))
    fig=Figure(figsize=(10,7),layout='constrained'); axes=fig.subplots(2,2).flat
    ax=axes[0]; rows=probability_rows(result)
    ax.bar(range(len(rows)),[r['Feasible'] for r in rows],label='feasible')
    ax.bar(range(len(rows)),[r['Infeasible'] for r in rows],bottom=[r['Feasible'] for r in rows],label='infeasible')
    ax.set_xticks(range(len(rows)),[r['Source'] for r in rows],rotation=18,fontsize=7)
    ax.set(ylabel='Probability',title='Exact probabilities vs shot estimates'); ax.legend(fontsize=7)
    ax=axes[1]; rows=score_rows(result)
    ax.bar(range(len(rows)),[r['Score'] or 0 for r in rows])
    ax.set_xticks(range(len(rows)),[r['Method']+(' (unobserved)' if r['Score'] is None else '') for r in rows],rotation=18,fontsize=7)
    ax.set(ylabel='True feasible score',title='Classical vs observed feasible samples')
    for index,(key,title) in enumerate([('Compiled depth','Compiled depth'),('Two-qubit gates','Two-qubit gate count')],start=2):
        ax=axes[index]; rows=resource_rows(result)
        ax.bar([r['Backend'] for r in rows],[r[key] for r in rows]); ax.set_title(title)
    figures.append(('Outcome probabilities, planning score and compiled circuit resources',fig))
    if 'baseline_snapshot' in result:
        fig=Figure(figsize=(10,5),layout='constrained'); ax=fig.subplots()
        rows=distribution_rows(result['baseline_snapshot'],result)
        keys=sorted({r['Original plan'] for r in rows})
        if len(keys)>32:
            maxima={k:max(r['Probability'] for r in rows if r['Original plan']==k) for k in keys}
            keys=sorted(sorted(keys,key=lambda k:-maxima[k])[:32])
        for index,name in enumerate(('baseline','disrupted')):
            values={r['Original plan']:r['Probability'] for r in rows if r['Scenario']==name}
            ax.bar([i+(index-.5)*.4 for i in range(len(keys))],[values.get(k,0) for k in keys],width=.4,label=name)
        step=max(1,len(keys)//20)
        ax.set_xticks(range(0,len(keys),step),keys[::step],rotation=90,fontsize=7)
        ax.set(xlabel='Full original plan (up to 32 shared states); each optimum is scenario-local',ylabel='Measured probability')
        ax.legend(); figures.append(('Before/after distributions in original decision order',fig))
    return figures


def report_text(result):
    c,m=result['classical'],result['qubo_minimum']
    lines=['Quantum Railways - experiment report',result['created_utc'],'',
        'Problem: maximize additive construction score with cost <= budget.',
        'Connectivity tickets are not part of this objective. City coordinates are geographic; routes are fictional.',
        '', 'Configuration:']
    lines += [f'{k}: {v}' for k,v in result['config'].items()]
    lines += ['',f"Decision order (physical route IDs): {[r['id'] for r in result['routes']]}",
        f"Enumerated plans: {result['plan_count']}",
        f"Classical: score {c['valoare_totala']}, cost {c['cost_total']}, key {c['bitstring']}",
        f"QUBO minimum: energy {m['energie']:.3f}, score {m['valoare_totala']}, cost {m['cost_total']}, valid={m['valid']}"]
    if 'experiment_id' in result:
        lines += ['',f"Experiment ID: {result['experiment_id']}; Scenario ID: {result['scenario_id']}",
            f"Classical reference: {result['reference_method']}; runtime {result['reference_seconds']:.6f} s",
            f"Optimal feasible ties: {len(result['classical_optima'])}; model minimum ties: {len(result['qubo_minima'])}"]
        for label,plans in [('Classical optimal plans',result['classical_optima']),('QUBO minimum plans',result['qubo_minima'])]:
            lines += [label+' (up to 20; complete lists in snapshot):']
            lines += [f"full bits {plan['full_bits']}, cost {plan['cost_total']}, score {plan['valoare_totala']}, energy {plan['energie']:.6f}, valid={plan['valid']}" for plan in plans[:20]]
        lines += ['QUBO and Ising coefficients in ACTIVE decision order:',json.dumps(result['model']),
                  'Exact ideal statevector statistics (not finite-shot estimates):',str(result['exact_ideal_statistics'])]
        q=result['quantum']
        lines += [f"Optimized gamma: {q.get('gamma',[])}",f"Optimized beta: {q.get('beta',[])}",
            f"Exact initial expected energy: {q.get('energie_medie_initiala','not trained')}",
            f"Exact final expected energy: {q.get('energie_medie','not trained')}",
            'Training runs and optimizer status:']
        lines += [str(run) for run in q['optimizare'].get('rulari',[])]
    if 'scenario' in result:
        state=result['scenario']
        lines += ['',f"Scenario minute: {state['time']}; blocked route IDs: {state['blocked_ids']}",
            f"Feasible plans in current decision space: {result['feasible_plan_count']}",
            'Active-to-original decision map: '+str(result['decision_map']),
            'Full original classical plan: '+str(c['full_bits']),
            'Connectivity of configured disrupted network: '+str(result['connectivity']),
            'Incidents - ALL SIMULATED (including scheduled/resolved):']
        lines += [str(i) for i in state['incidents']] or ['None']
        lines += ['Delay, capacity and operating cost are metadata; only explicit construction-cost changes affect QUBO.',
                  'Map: schematic fictional network at geographic city coordinates. No basemap tiles downloaded for reports.']
    if 'baseline_comparison' in result:
        lines += ['', 'Before/after comparison (each optimum belongs to its own scenario):']
        for label,metrics in result['baseline_comparison'].items():
            lines += [label]+[f'{k}: {v}' for k,v in metrics.items()]
        lines += ['Baseline reproducibility metadata: '+str(result['baseline_metadata']),
                  'Do not interpret energy differences across changed models as direct improvements.']
        if 'baseline_snapshot' in result:
            before=result['baseline_snapshot']
            lines += ['Baseline classical full plan: '+str(before['classical']['full_bits']),
                      'Disrupted classical full plan: '+str(c['full_bits'])]
    for mode,s in result['samples'].items():
        lines += ['',mode.upper()+' LOCAL SIMULATION',f"Best feasible observed: {s['best_feasible']['bitstring'] if s['best_feasible'] else 'none'}",
                  f"Most frequent: {s['most_frequent']['bitstring']} (valid={s['most_frequent']['valid']})"]
        for label,plan in [('Best feasible',s['best_feasible']),('Most frequent',s['most_frequent'])]:
            if plan:
                lines.append(f"{label}: cost {plan['cost_total']}, score {plan['valoare_totala']}, energy {plan['energie']:.3f}, route IDs {plan['ids_rute']}")
        lines += [f'{k}: {v:.6f}' for k,v in s.items() if isinstance(v,(float,int))]
    lines += ['',f"Runtime: {result['runtime_seconds']:.3f} s",'Software: '+str(result['versions']),
        'Circuit/backend resources: '+str(result['resources']), '',
        'Findings and limitations:',
        'Energy = -score + penalty * (cost - budget)^2. The model penalizes underspending too; its minimum can be invalid.',
        'Finite-shot frequencies estimate probabilities. QAOA is not guaranteed to find a global optimum.',
        'Noisy samples use a seeded synthetic GenericBackendV2, not real IBM hardware. Training remains ideal.',
        'No claim of quantum advantage is made. All modes use the same routes and trained angles.']
    if not result['routes']:
        lines += ['ALL ROUTES CLOSED: the sole empty plan is deterministic. No quantum circuit or physical shots were executed; probabilities are exact, not shot estimates.']
    return lines


def html_report(result):
    pictures=[]
    for title,fig in report_figures(result):
        buf=BytesIO(); fig.savefig(buf,format='png',dpi=140)
        pictures.append(f'<h2>{escape(title)}</h2><img style="width:100%" src="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}">')
    table='<table><tr><th>Decision</th><th>Route</th><th>Cost</th><th>Score</th></tr>'
    for i,r in enumerate(result['routes']):
        table+=f"<tr><td>x{i}, ID {r['id']}</td><td>{escape(' - '.join(r['cities']))}</td><td>{r['cost']}</td><td>{r['value']}</td></tr>"
    return '<!doctype html><html><meta charset="utf-8"><title>Quantum Railways report</title><style>body{font:15px system-ui;max-width:1000px;margin:32px auto}pre{white-space:pre-wrap}td,th{padding:8px;border:1px solid #ccc}table{border-collapse:collapse}</style><body><pre>'+escape('\n'.join(report_text(result)))+'</pre>'+table+'</table>'+''.join(pictures)+'</body></html>'


def pdf_report(result):
    buf=BytesIO()
    text=report_text(result)+['','Route catalogue:']+[
        f"x{i}: ID {r['id']} {' - '.join(r['cities'])}, cost {r['cost']}, score {r['value']}" for i,r in enumerate(result['routes'])]
    wrapped=[line for paragraph in text for line in (textwrap.wrap(paragraph,100) or [''])]
    with PdfPages(buf) as pdf:
        for start in range(0,len(wrapped),48):
            fig=Figure(figsize=(8.27,11.69)); ax=fig.subplots(); ax.axis('off')
            ax.text(0,1,'\n'.join(wrapped[start:start+48]),va='top',fontsize=9,linespacing=1.5)
            pdf.savefig(fig)
        for title,fig in report_figures(result):
            fig.suptitle(title,fontsize=12); pdf.savefig(fig)
    return buf.getvalue()
