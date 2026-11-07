"""Controlled comparisons of QAOA depths and compact circuit illustrations."""
from pathlib import Path
import json

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from quantum_optimizer import construct_qubo, optimizeaza_qaoa, parameterized_qaoa


def draw_qaoa_layers(qubo, p=1, output_path=None):
    """Draw every logical wire; each cost block groups the actual RZ/RZZ gates.

    This is a compact logical diagram, not a transpiled hardware gate schedule.
    Gate counts and parameter counts come from the real parameterized circuit.
    """
    circuit, parameters = parameterized_qaoa(qubo, p=p, measure=False)
    n = circuit.num_qubits
    ops = circuit.count_ops()
    rz = int(ops.get('rz', 0)) // p
    rzz = int(ops.get('rzz', 0)) // p
    fig, ax = plt.subplots(figsize=(max(9, 5+4*p), max(3.5, .46*n+2.3)), layout='constrained')
    last = 1.2 + 2.5*p
    ax.set_xlim(-1.6, last+1.1)
    ax.set_ylim(-1.2, n+.9)
    ax.axis('off')
    colors = dict(wire='#17334a', cost='#d9f0eb', mixer='#ffedc6')
    def box(x, y, label, color='white', width=.7):
        ax.add_patch(Rectangle((x-width/2, y-.26), width, .52,
                              facecolor=color, edgecolor=colors['wire'], linewidth=1.2,zorder=2))
        ax.text(x,y,label,ha='center',va='center',fontsize=9,zorder=3)
    for i in range(n):
        y=n-1-i
        ax.plot([-.6,last+.2],[y,y],color=colors['wire'],lw=1,zorder=0)
        ax.text(-.8,y,f'q{i}',ha='right',va='center',fontsize=10)
        box(0,y,'H')
        box(last,y,'M')
    for layer in range(p):
        x=1.2+2.5*layer
        ax.add_patch(Rectangle((x-.6,-.34),1.2,n-1+.68,facecolor=colors['cost'],
                              edgecolor='#008d83',linewidth=1.6,zorder=1))
        ax.text(x,(n-1)/2,f'Cost\nγ{layer+1}\n\n{rz} RZ\n{rzz} RZZ',ha='center',va='center',fontsize=10)
        ax.text(x+.62,n-.05,f'Strat {layer+1}',ha='center',fontsize=11,color=colors['wire'])
        for i in range(n):
            box(x+1.25,n-1-i,f'RX(2β{layer+1})',colors['mixer'],width=1.0)
    ax.text(0,-.78,'Superpoziție',ha='center',fontsize=9)
    ax.text(last,-.78,'Măsurare',ha='center',fontsize=9)
    fig.suptitle(f'Circuit QAOA · p={p} · {n} qubiți · {len(parameters)} unghiuri\n'
                 f"Cost: {ops.get('rz',0)} RZ + {ops.get('rzz',0)} RZZ · mixer: {ops.get('rx',0)} RX",
                 fontsize=14,color=colors['wire'])
    fig.supxlabel('Schemă logică compactă: blocurile Cost grupează porțile RZ/RZZ. Măsurarea se face după ultimul strat.',fontsize=9)
    fig.qaoa_resources = dict(p=p, qubits=n, parameters=len(parameters),
                              rz=int(ops.get('rz',0)), rzz=int(ops.get('rzz',0)), rx=int(ops.get('rx',0)))
    if output_path is not None:
        path=Path(output_path); path.parent.mkdir(parents=True,exist_ok=True)
        fig.savefig(path,dpi=150)
    return fig


def comparison_rows(results):
    rows=[]
    for depth,result in sorted(results.items()):
        s=result['statistici']
        rows.append(dict(p=depth, value=result['valoare_totala'], cost=result['cost_total'],
                         classical=result['referinta_clasica']['valoare_optima'],
                         gap=result['diferenta_valoare'], valid_rate=result['rata_planuri_valide'],
                         optimal_rate=result['probabilitate_optim_valid'],
                         ideal_valid=result['probabilitate_valida_ideala'],
                         ideal_optimal=result['probabilitate_optim_valid_ideala'],
                         energy=result['energie_medie'], evaluations=s['evaluari'],
                         training_seconds=s['timp_antrenare_secunde'],
                         two_qubit_gates=s['porti_doi_qubiti']))
    return rows


def plot_depth_comparison(results, output_path=None):
    rows=comparison_rows(results)
    if not rows: raise ValueError('At least one result is required')
    fig,axes=plt.subplots(2,2,figsize=(11,7.5),layout='constrained')
    labels=[f"p={r['p']}" for r in rows]
    for ax,key,factor,title in zip(axes.flat,
            ['value','ideal_valid','ideal_optimal','training_seconds'],[1,100,100,1],
            ['Valoare QAOA măsurată','Probabilitate ideală exactă validă (%)',
             'Probabilitate ideală exactă a optimului (%)','Timp antrenare (s)']):
        values=[r[key]*factor if r[key] is not None else 0 for r in rows]
        bars=ax.bar(labels,values,color=['#008d83' if i%2==0 else '#bd891e' for i in range(len(rows))])
        ax.set_title(title,fontsize=11)
        ax.set_ylim(0,max(max(values),1e-8)*1.3)
        for bar,row,value in zip(bars,rows,values):
            label='fără plan valid' if row[key] is None else f'{value:.5g}'
            ax.text(bar.get_x()+bar.get_width()/2,value+ax.get_ylim()[1]*.025,label,ha='center',fontsize=10)
    axes[0,0].axhline(rows[0]['classical'],color='#17334a',ls='--',label='Optim clasic')
    axes[0,0].set_ylim(0,max(1,rows[0]['classical'],max(r['value'] or 0 for r in rows))*1.3)
    axes[0,0].legend(fontsize=9,loc='upper right')
    fig.suptitle('Comparație QAOA la același buget de optimizare',fontsize=14)
    if output_path is not None:
        path=Path(output_path); path.parent.mkdir(parents=True,exist_ok=True)
        fig.savefig(path,dpi=150)
    return fig


def run_depth_comparison(rute, buget, penalizare=0.7, *, depths=(1,2), maxiter=30,
                         restarts=1, shots=4096, seed=2026, output_dir=None, progress=print):
    """Train each depth afresh with the same public optimizer and fixed settings."""
    depths=tuple(depths)
    if not depths or any(isinstance(p,bool) or not isinstance(p,int) or p<1 for p in depths) or len(set(depths))!=len(depths):
        raise ValueError('depths must contain distinct positive integers')
    qubo=construct_qubo(rute,buget,penalizare)
    # Validate and draw all requested depths before starting costly optimization.
    output=Path(output_dir) if output_dir is not None else None
    for depth in depths:
        fig=draw_qaoa_layers(qubo,depth,output/f'circuit_p{depth}.png' if output else None)
        plt.close(fig)
    results={}
    for depth in depths:
        if progress: progress(f'Încep p={depth}: {len(rute)} qubiți, maxiter={maxiter}, restarts={restarts}, shots={shots}',flush=True)
        result=optimizeaza_qaoa(rute,buget,penalizare,p=depth,maxiter=maxiter,restarts=restarts,
                               shots=shots,seed=seed,backend_mode='ideal')
        results[depth]=result
        if output:
            (output/f'p{depth}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        if progress:
            progress(f"Terminat p={depth}: valoare={result['valoare_totala']}, cost={result['cost_total']}, "
                     f"antrenare={result['statistici']['timp_antrenare_secunde']:.2f} s",flush=True)
    if output:
        (output/'comparison.json').write_text(json.dumps(comparison_rows(results),ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        fig=plot_depth_comparison(results,output/'comparatie.png'); plt.close(fig)
    return results
