"""Self-contained HTML and PDF exports from the same experiment snapshot."""
import base64
from html import escape
from io import BytesIO
import json
import textwrap
from matplotlib.figure import Figure
from matplotlib.backends.backend_pdf import PdfPages
from railway_catalog import POSITIONS


def report_figures(result):
    figures = []
    plans = [('Classical optimum',result['classical']),('QUBO energy minimum',result['qubo_minimum'])]
    plans += [(f'{mode}: best feasible sample',s['best_feasible']) for mode,s in result['samples'].items()]
    fig = Figure(figsize=(10,7),layout='constrained')
    axes = list(fig.subplots(2,2).flat)
    for ax,(title,plan) in zip(axes,plans):
        ids = set(plan['ids_rute']) if plan else set()
        for route in result['routes']:
            points = [POSITIONS[city] for city in route['cities']]
            selected = route['id'] in ids
            ax.plot(*zip(*points),color=('#008d83' if plan and plan['valid'] else '#d2554b') if selected else '#cbd5e1',lw=3 if selected else 1)
        cities = {c for r in result['routes'] for c in r['cities']}
        for city in cities:
            lon,lat = POSITIONS[city]; ax.scatter(lon,lat,s=12,c='#17334a'); ax.annotate(city,(lon,lat),fontsize=7)
        ax.set_title(title + (f"\nCost {plan['cost_total']}, score {plan['valoare_totala']}, energy {plan['energie']:.2f}, valid={plan['valid']}" if plan else '\nNo feasible sample'),fontsize=9)
        ax.margins(.2); ax.axis('off')
    for ax in list(axes)[len(plans):]: ax.axis('off')
    figures.append(('Railway plans - geographic cities, fictional connections',fig))
    fig = Figure(figsize=(10,5),layout='constrained'); ax=fig.subplots()
    for mode,sample in result['samples'].items():
        rows=sorted(sample['distribution'],key=lambda r:-r['probability'])[:20]
        ax.plot([r['bitstring'] for r in rows],[r['probability'] for r in rows],marker='o',label=mode)
    ax.set(xlabel='Measured key (decision 0 at right); top 20 per backend',ylabel='Probability')
    ax.tick_params(axis='x',rotation=90); ax.legend(); figures.append(('Measurement distribution',fig))
    fig=Figure(figsize=(10,4),layout='constrained'); ax=fig.subplots()
    history=result['quantum']['optimizare']['history']
    for restart in range(result['config']['restarts']):
        points=[r for r in history if r['restart']==restart]
        ax.plot([r['evaluation'] for r in points],[r['energy'] for r in points],label=f'Restart {restart+1}')
    ax.set(xlabel='Objective evaluation',ylabel='Exact ideal expected energy'); ax.legend()
    figures.append(('QAOA convergence (ideal training)',fig))
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
