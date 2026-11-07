import json
from pathlib import Path
import numpy as np
from streamlit.testing.v1 import AppTest
from experiment import references, run_experiment, summarize
from quantum_optimizer import construct_qubo, qubo_to_ising, qubo_energy, ising_energy
from railway_data import ROUTES, DEMO_IDS
from railway_catalog import ROUTES as CATALOG
from railway_map import calculeaza_plan
from reporting import html_report,pdf_report

BASE=[r for r in ROUTES if r['id'] in DEMO_IDS]

def test_baseline_and_all_32_energies():
    plans,c,m=references(BASE,7,.7)
    assert len(plans)==32 and (c['valoare_totala'],c['cost_total'])==(15,7)
    assert np.isclose(m['energie'],-17.3)
    assert (m['cost_total'],m['valoare_totala'],m['valid'])==(8,18,False)
    qubo=construct_qubo(BASE,7,.7); ising=qubo_to_ising(qubo)
    for plan in plans:
        assert np.isclose(qubo_energy(plan['bits'],qubo),plan['energie'])
        assert np.isclose(ising_energy(plan['bits'],ising),plan['energie'])
    tied={p['bitstring']:1 for p in plans if p['valid'] and p['valoare_totala']==15}
    assert summarize(tied,plans)['p_optimal_feasible']==1

def test_pipeline_parameters_maps_reports(tmp_path):
    result=run_experiment(BASE,budget=6,penalty=1.2,p=2,shots=128,maxiter=8,seed=42,mode='compare')
    assert result['config']['budget']==6 and result['quantum']['statistici']['qaoa_depth']==2
    assert len(result['samples'])==2
    for sample in result['samples'].values():
        assert np.isclose(sum(p['probability'] for p in sample['distribution']),1)
        assert sum(p['count'] for p in sample['distribution'])==128
    for plan in [result['classical'],result['qubo_minimum'],result['samples']['ideal']['most_frequent']]:
        mapped=calculeaza_plan(BASE,plan['ids_rute'],[],6)
        assert (mapped['cost'],mapped['beneficiu'],mapped['valid'])==(plan['cost_total'],plan['valoare_totala'],plan['valid'])
    frozen=json.dumps(result,sort_keys=True)
    html=html_report(result); pdf=pdf_report(result)
    assert 'data:image/png;base64,' in html and 'penalty: 1.2' in html
    assert pdf.startswith(b'%PDF') and len(pdf)>20000
    assert json.dumps(result,sort_keys=True)==frozen
    assert all(r['border_cost']==1 for r in CATALOG if r['international'])

def test_no_feasible_sample_and_validation():
    plans,_,_=references(BASE,0,.7)
    s=summarize({'11111':2},plans)
    assert s['best_feasible'] is None and s['p_feasible']==0
    import pytest
    for config in ({'shots':0},{'p':4},{'mode':'hardware'}):
        with pytest.raises(ValueError): run_experiment(BASE,**config)

def test_complete_streamlit_workflow():
    root=Path(__file__).resolve().parents[1]
    app=AppTest.from_file(root/'app.py',default_timeout=40).run()
    assert not app.exception
    next(b for b in app.button if b.label=='Rulează simularea').click().run()
    assert not app.exception
    result=json.loads(app.session_state['experiment_json'])
    assert result['classical']['valoare_totala']==15
    next(b for b in app.button if b.label=='Pregătește rapoartele HTML și PDF').click().run()
    assert not app.exception and app.session_state['report_bundle'][2].startswith(b'%PDF')
    app.slider(key='budget').set_value(6).run()
    assert not app.exception
    assert any('Configurația s-a schimbat' in i.value for i in app.info)
    next(b for b in app.button if b.label=='Rulează simularea').click().run()
    assert not app.exception and json.loads(app.session_state['experiment_json'])['config']['budget']==6
    live=AppTest.from_file(root/'pages/2_Live_Network.py',default_timeout=40).run()
    assert not live.exception
