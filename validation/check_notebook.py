"""Execute notebook code headlessly; only rich display is replaced by a no-op."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

parser=argparse.ArgumentParser()
parser.add_argument('--small',action='store_true')
parser.add_argument('--noisy',action='store_true')
args=parser.parse_args()
nb=json.loads((Path(__file__).resolve().parents[1]/'Quantum_Railways_Labb.ipynb').read_text(encoding='utf-8'))
ns={'__name__':'__main__','input':lambda prompt:'7' if args.small else '20',
    'display':lambda *a,**kw:None,'Markdown':lambda text:text}
for i,c in enumerate(nb['cells']):
    if c['cell_type']!='code': continue
    source=''.join(c['source'])
    if i==2:
        source=source.replace('from IPython.display import display,Markdown','')
    print('Executing cell',i,flush=True)
    exec(compile(source,f'notebook_cell_{i}','exec'),ns)
    if i==4 and args.small:
        ns['demo_routes']=[ns['ROUTES'][i] for i in (0,1,2,6,8)]
        ns['N_DECISIONS']=5
    if i==28 and args.noisy:
        if not args.small: raise ValueError('Noisy verification uses the small scenario')
        ns['RUN_NOISY']=True
        ns['backend']=ns['local_backend'](ns['N_DECISIONS'])
    plt.close('all')
assert sum(ns['ideal_counts'].values())==ns['IDEAL_SHOTS']
assert ns['classical_best']['score']==(15 if args.small else 46)
assert ns['best_sample'] is None or ns['best_sample']['cost']<=ns['BUDGET']
assert ns['backend_counts'] is None or sum(ns['backend_counts'].values())==ns['BACKEND_SHOTS']
assert set(ns['qaoa_results'])=={1,2}
for depth,result in ns['qaoa_results'].items():
    assert len(result['unghiuri_optime'])==2*depth
    assert sum(result['counts'].values())==ns['IDEAL_SHOTS']
    assert not result['valid'] or result['cost_total']<=ns['BUDGET']
print('FULL NOTEBOOK CHECK OK:',ns['N_DECISIONS'],'qubits;',
      'best sample:',ns['best_sample'],'noisy:',ns['backend_counts'] is not None)
