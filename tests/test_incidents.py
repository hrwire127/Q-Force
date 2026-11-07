from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import json
import numpy as np
import pytest
from streamlit.testing.v1 import AppTest
from railway_incidents import (Incident,scenario,resolve,random_incidents,alternative_path,
                              available_graph,connectivity,reconstruct,comparison,TYPES)
from railway_data import ROUTES,DEMO_IDS,POSITIONS
from experiment import run_experiment,references
from incident_ui import geographic_figure, selected_detail, STATUS_COLORS
from quantum_optimizer import construct_qubo,qubo_to_ising,qubo_energy,ising_energy
from reporting import html_report,pdf_report

BASE=[r for r in ROUTES if r['id'] in DEMO_IDS]


def test_validation_time_resolution_and_reproducibility():
    for kwargs in ({'severity':'INVALID'},{'source':'verified external'},{'delay_minutes':-1},
                   {'end_time':0},{'capacity_percent':0},{'route_id':True}):
        args={'route_id':1,**kwargs}
        with pytest.raises(ValueError): Incident('bad',**args)
    item=asdict(Incident('test',1,start_time=2,end_time=4))
    assert not scenario(BASE,[item],1)['blocked_ids']
    assert scenario(BASE,[item],2)['blocked_ids']==[1]
    assert not scenario(BASE,[item],4)['blocked_ids']
    assert not scenario(BASE,resolve([item],'test'),2)['blocked_ids']
    with pytest.raises(ValueError): scenario(BASE,[asdict(Incident('bad',99))])
    with pytest.raises(ValueError): scenario(BASE,[item,item])
    assert random_incidents(BASE,42,5)==random_incidents(BASE,42,5)
    assert random_incidents(BASE,42,5)!=random_incidents(BASE,43,5)
    for kind in TYPES:
        assert scenario(BASE,[asdict(Incident(kind,1,kind))])['blocked_ids']==([1] if kind in ('closure','maintenance') else [])


def test_available_graph_and_real_alternatives():
    closed=scenario(BASE,[asdict(Incident('closed',1))])
    graph=available_graph(closed)
    assert all(data['route_id']!=1 for *_,data in graph.edges(data=True))
    path=alternative_path(closed,'Iași','Cluj-Napoca')
    assert path['cities']==['Iași','Brașov','Cluj-Napoca'] and path['route_ids']==[0,2]
    isolated=scenario(BASE,[asdict(Incident(str(rid),rid)) for rid in [0,1]])
    assert alternative_path(isolated,'Iași','Cluj-Napoca') is None
    assert 'Iași' in connectivity(isolated)['isolated_cities']
    all_closed=scenario(BASE,[asdict(Incident(str(r['id']),r['id'])) for r in BASE])
    assert available_graph(all_closed).number_of_edges()==0
    assert connectivity(all_closed)['component_count']==5


def test_closure_qaoa_reconstruction_and_energies():
    snapshot=deepcopy(BASE)
    baseline=run_experiment(BASE,maxiter=8,shots=128)
    after=run_experiment(BASE,incidents=[asdict(Incident('closed',1))],maxiter=8,shots=128)
    assert BASE==snapshot
    assert after['decision_map']=={'active_ids':[0,2,6,8],'original_ids':DEMO_IDS}
    assert 1 not in after['classical']['ids_rute']
    for sample in after['samples'].values():
        for plan in sample['distribution']:
            assert 1 not in plan['ids_rute'] and plan['full_bits'][1]==0
            assert len(plan['full_bits'])==5
    plans,c,m=references(after['routes'],7,.7)
    qubo=construct_qubo(after['routes'],7,.7); ising=qubo_to_ising(qubo)
    for plan in plans:
        assert np.isclose(qubo_energy(plan['bits'],qubo),plan['energie'])
        assert np.isclose(ising_energy(plan['bits'],ising),plan['energie'])
    assert reconstruct([1,1],[0,6],DEMO_IDS)==[1,0,0,1,0]
    assert comparison(baseline,after)['disrupted']['available_routes']==4
    assert len(baseline['routes'])==5 and baseline['classical']['valoare_totala']==15


def test_degraded_metadata_and_explicit_cost_objective():
    baseline=run_experiment(BASE,shots=128,maxiter=8)
    delay=asdict(Incident('delay',1,'delay',delay_minutes=60,cost_delta=5,capacity_percent=50))
    metadata=run_experiment(BASE,incidents=[delay],shots=128,maxiter=8)
    assert metadata['classical']['energie']==baseline['classical']['energie']
    assert metadata['quantum']['counts']==baseline['quantum']['counts']
    assert metadata['scenario']['routes'][1]['operating_cost_delta']==5
    cost=run_experiment(BASE,incidents=[{**delay,'construction_cost_delta':3}],shots=128,maxiter=8)
    assert cost['routes'][1]['cost']==6
    assert cost['classical']['valoare_totala']<baseline['classical']['valoare_totala']


def test_all_routes_closed_without_qaoa(monkeypatch):
    def forbidden(*a,**kw): raise AssertionError('A zero-qubit circuit must not run')
    monkeypatch.setattr('quantum_optimizer.optimizeaza_qaoa',forbidden)
    all_closed=[asdict(Incident(str(r['id']),r['id'])) for r in BASE]
    result=run_experiment(BASE,incidents=all_closed,maxiter=8,shots=128,mode='compare')
    assert result['routes']==[] and result['plan_count']==result['feasible_plan_count']==1
    assert result['classical']['full_bits']==[0]*5
    assert result['classical']['energie']==.7*49
    assert result['samples']['ideal']['p_feasible']==1
    assert result['quantum']['statistici']['shots']==0
    assert result['quantum']['counts']=={}
    assert result['samples']['ideal']['distribution'][0]['count']==0
    assert pdf_report(result).startswith(b'%PDF')


def test_geographic_layer_click_details_and_report():
    result=run_experiment(BASE,incidents=[asdict(Incident('closure-Iasi-Cluj',1))],shots=128,maxiter=8)
    state=result['scenario']; fig=geographic_figure(state,[1])
    assert fig.layout.map.style=='carto-positron'
    assert (fig.layout.map.center.lon,fig.layout.map.center.lat)==(25,46)
    blocked=[trace for trace in fig.data if trace.name=='blocked']
    assert blocked and blocked[0].line.color==STATUS_COLORS['blocked']
    assert 'CONFLICT' in blocked[0].hovertemplate
    assert selected_detail({'selection':{'points':[{'customdata':['route',1]}]}},state)['status']=='blocked'
    assert selected_detail({'selection':{'points':[{'customdata':['city','Iași']}]}},state)['coordinates_lon_lat']==POSITIONS['Iași']
    text=html_report(result)
    assert 'closure-Iasi-Cluj' in text and 'blocked route IDs: [1]' in text and 'SIMULATED' in text
    assert 'data:image/png;base64,' in text and pdf_report(result).startswith(b'%PDF')


def test_incident_end_to_end_streamlit():
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py',default_timeout=40).run()
    def click(label):
        next(b for b in app.button if b.label==label).click().run()
        assert not app.exception,app.exception
    click('Rulează simularea')
    baseline=app.session_state['baseline_json']
    app.selectbox(key='incident_route').select(1).run()
    click('Blochează conexiunea')
    assert app.session_state['qr_incidents'][0]['route_id']==1
    assert app.session_state['baseline_json']==baseline
    click('Rulează simularea')
    modified=json.loads(app.session_state['experiment_json'])
    assert modified['scenario']['blocked_ids']==[1]
    assert 1 not in modified['classical']['ids_rute']
    assert modified['baseline_comparison']['baseline']['available_routes']==5
    assert modified['baseline_comparison']['disrupted']['available_routes']==4
    click('Pregătește rapoartele HTML și PDF')
    assert 'SIM-1' in app.session_state['report_bundle'][1]
    assert app.session_state['report_bundle'][2].startswith(b'%PDF')
    click('Deblochează conexiunea')
    click('Rulează simularea')
    restored=json.loads(app.session_state['experiment_json'])
    assert restored['classical']['valoare_totala']==15 and len(restored['routes'])==5
    assert json.loads(app.session_state['disrupted_json'])['scenario']['blocked_ids']==[1]
    assert len(app.session_state['experiment_snapshots'])==3
