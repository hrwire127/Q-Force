from copy import deepcopy
from pathlib import Path
import json
import numpy as np
from streamlit.testing.v1 import AppTest
from experiment import run_experiment
from experiment_ui import outcome_histogram
from incident_ui import geographic_figure,visible_map_state
from railway_data import ROUTES,DEMO_IDS
from simulation_history import save_snapshot,load_snapshot,list_snapshots
from reporting import pdf_report

BASE=[r for r in ROUTES if r['id'] in DEMO_IDS]


def test_disjoint_histograms_and_selected_city_maps():
    result=run_experiment(BASE,shots=128,maxiter=8)
    quantum=outcome_histogram(result)
    assert sum(r['Număr'] for r in quantum)==128
    assert np.isclose(quantum[0]['Proporție'],result['samples']['ideal']['p_optimal_feasible'])
    assert np.isclose(sum(r['Proporție'] for r in quantum),1)
    classical=outcome_histogram(result,classical=True)
    assert [r['Număr'] for r in classical]==[2,14,16]
    frozen=deepcopy(result['scenario'])
    view=visible_map_state(frozen,[1,6],plan_only=True)
    fig=geographic_figure(view,[1,6])
    cities=next(t for t in fig.data if t.name=='Cities')
    assert set(cities.text)=={'Iași','Cluj-Napoca','Brașov','București'}
    assert {r['id'] for r in view['routes']}=={1,6}
    assert frozen==result['scenario']


def test_local_history_is_immutable_and_survives_new_connection():
    result=run_experiment(BASE,shots=128,maxiter=8)
    key=save_snapshot(result)
    changed=deepcopy(result); changed['classical']['valoare_totala']=-99
    save_snapshot(changed)
    assert len(list_snapshots())==1
    assert load_snapshot(key)['classical']['valoare_totala']==15


def test_focused_pdf_uses_requested_backend_and_frozen_data():
    result=run_experiment(BASE,shots=128,maxiter=8,mode='compare')
    original=json.dumps(result,sort_keys=True)
    for backend in ('ideal','noisy'):
        data=pdf_report(result,presentation_backend=backend)
        assert data.startswith(b'%PDF') and len(data)>15000
    assert json.dumps(result,sort_keys=True)==original


def test_presentation_order_regeneration_and_load_previous_runs(monkeypatch):
    root=Path(__file__).resolve().parents[1]
    app=AppTest.from_file(root/'app.py',default_timeout=60).run()
    assert not app.exception
    assert {'Total rute bifate','Orașe selectate'}<={m.label for m in app.metric}
    assert not any(n.label in ('Seed','Toleranță optimizator') for n in app.number_input)
    assert not any(s.label=='Nivel optimizare transpiler' for s in app.slider)
    def click(app,label):
        next(b for b in app.button if b.label==label).click().run()
        assert not app.exception,app.exception
    click(app,'Rulează simularea')
    baseline=json.loads(app.session_state['experiment_json'])
    labels=[s.value for s in app.subheader]
    assert labels.index('Rezultatul cuantic — cel mai bun plan fezabil găsit')<labels.index('Rezultatul prin formula clasică')
    assert not {'Optim clasic fezabil','Minim energie QUBO','Cel mai bun QAOA fezabil'} & {m.label for m in app.metric}
    app.toggle(key='simulate_incidents').set_value(True).run()
    first=app.session_state['qr_incidents'][0]['route_id']
    click(app,'Regenerează locul incidentului')
    assert app.session_state['qr_incidents'][0]['route_id']!=first
    click(app,'Rulează simularea')
    after=json.loads(app.session_state['experiment_json'])
    assert len(list_snapshots())==2
    assert first in DEMO_IDS
    # A completely new UI session can restore earlier runs without running QAOA.
    reopened=AppTest.from_file(root/'app.py',default_timeout=60).run()
    assert not reopened.exception
    def unexpected(*args,**kwargs): raise AssertionError('Loading history must never rerun the optimizer')
    monkeypatch.setattr('experiment_ui.run_railway_optimization',unexpected)
    reopened.selectbox(key='history_selected').select(baseline['experiment_id']).run()
    click(reopened,'Încarcă simularea')
    assert json.loads(reopened.session_state['experiment_json'])['experiment_id']==baseline['experiment_id']
    assert not any('Configurația s-a schimbat' in i.value for i in reopened.info)
    reopened.selectbox(key='history_selected').select(after['experiment_id']).run()
    click(reopened,'Încarcă simularea')
    assert json.loads(reopened.session_state['experiment_json'])['experiment_id']==after['experiment_id']
    assert reopened.toggle(key='simulate_incidents').value is True
    click(reopened,'Pregătește PDF-ul simulării')
    assert reopened.session_state['pdf_bundle'][1].startswith(b'%PDF')
