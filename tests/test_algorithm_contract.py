"""Regression checks for the complete typed application pipeline, using real Aer."""
from dataclasses import asdict
import json
from pathlib import Path
import numpy as np
import pytest
from streamlit.testing.v1 import AppTest
from experiment import RailwayScenario,SimulationConfig,run_railway_optimization
from railway_incidents import Incident
from railway_data import ROUTES,DEMO_IDS
from quantum_optimizer import qubo_energy,ising_energy,decode_key
from reporting import html_report,pdf_report

BASE=[r for r in ROUTES if r['id'] in DEMO_IDS]


def run(routes=BASE,incidents=(),**options):
    return run_railway_optimization(RailwayScenario(routes,list(incidents)),
        SimulationConfig(**{'shots':128,'maxiter':8,**options}))


def test_typed_snapshot_baseline_coefficients_and_exact_statistics():
    result=run()
    assert result['plan_count']==32
    assert (result['classical']['valoare_totala'],result['classical']['cost_total'])==(15,7)
    assert len(result['classical_optima'])==2
    assert len(result['qubo_minima'])==1
    minimum=result['qubo_minima'][0]
    assert np.isclose(minimum['energie'],-17.3)
    assert (minimum['valoare_totala'],minimum['cost_total'],minimum['valid'])==(18,8,False)
    qubo=result['model']['qubo']; ising=result['model']['ising']
    probabilities=result['quantum']['statevector_probabilities']
    assert np.isclose(sum(probabilities.values()),1)
    expected=0
    for k in range(32):
        key=format(k,'05b'); bits=decode_key(key,5)
        cost=sum(b*r['cost'] for b,r in zip(bits,BASE))
        value=sum(b*r['value'] for b,r in zip(bits,BASE))
        direct=-value+.7*(cost-7)**2
        assert np.isclose(qubo_energy(bits,qubo),direct)
        assert np.isclose(ising_energy(bits,ising),direct)
        expected+=probabilities[key]*direct
    assert np.isclose(result['exact_ideal_statistics']['expected_energy'],expected)
    assert np.isclose(result['quantum']['energie_medie'],expected)
    assert sum(result['counts_by_backend']['ideal'].values())==128
    assert result['experiment_id'] and result['scenario_id']==result['config']['scenario_id']
    assert result==json.loads(json.dumps(result,allow_nan=False))
    changed=run(penalty=1.5,budget=6)
    assert changed['model']['qubo']['linear']!=qubo['linear']
    assert changed['classical']['cost_total']<=6


def test_tied_energy_and_feasible_plans_are_all_retained():
    routes=[{**BASE[0],'id':rid,'cost':1,'value':2} for rid in [9,100]]
    result=run(routes,budget=1,penalty=4)
    assert len(result['classical_optima'])==len(result['qubo_minima'])==2
    optimal_keys={r['bitstring'] for r in result['classical_optima']}
    exact=sum(result['quantum']['statevector_probabilities'][key] for key in optimal_keys)
    empirical=sum(count for key,count in result['counts_by_backend']['ideal'].items() if key in optimal_keys)/128
    assert np.isclose(result['exact_ideal_statistics']['p_optimal_feasible'],exact)
    assert np.isclose(result['samples']['ideal']['p_optimal_feasible'],empirical)


def test_incident_regression_and_both_real_backends():
    result=run(incidents=[asdict(Incident('closed-x1',1))],p=2,mode='compare',transpilation_level=0)
    assert (result['classical']['valoare_totala'],result['classical']['cost_total'])==(14,6)
    assert result['classical']['full_bits']==[0,0,1,1,0]
    assert result['quantum']['statistici']['numar_qubiti']==4
    assert len(result['quantum']['gamma'])==len(result['quantum']['beta'])==2
    for plans in [result['classical_optima'],result['qubo_minima'],result['quantum']['top_planuri']]:
        assert all(plan['full_bits'][1]==0 for plan in plans)
    assert len(result['quantum']['full_recommended_bits'])==5
    for mode in ('ideal','noisy'):
        assert sum(result['counts_by_backend'][mode].values())==128
        assert result['resources'][mode]['optimization_level']==0
        assert result['resources'][mode]['registru_masurare']=='plan'
        measured=result['samples'][mode]
        assert np.isclose(sum(r['probability'] for r in measured['distribution']),1)
        assert all(1 not in plan['ids_rute'] for plan in measured['distribution'])
    restored=run()
    assert restored['classical']['valoare_totala']==15


def test_unsupported_inputs_and_resource_limits_fail_explicitly():
    for options in ({'optimizer':'fake'},{'objective':'time-aware'}, {'transpilation_level':4},
                    {'optimizer_tol':0},{'p':3,'maxiter':5}):
        with pytest.raises(ValueError): run(**options)
    with pytest.raises(ValueError,match='10 decisions'):
        run([{**BASE[0],'id':i} for i in range(11)])


def test_streamlit_parameters_map_switch_and_matching_exports():
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py',default_timeout=60).run()
    assert not app.exception
    next(s for s in app.slider if s.label=='Adâncime QAOA p').set_value(2).run()
    assert not any(s.label=='Nivel optimizare transpiler' for s in app.slider)
    next(s for s in app.selectbox if s.label=='Backend').select('compare').run()
    next(b for b in app.button if b.label=='Rulează simularea').click().run()
    assert not app.exception
    before=app.session_state['experiment_json']
    baseline=json.loads(before)
    assert baseline['config']['p']==2 and baseline['config']['mode']=='compare'
    assert sum(baseline['counts_by_backend']['noisy'].values())==2048
    next(s for s in app.selectbox if s.label=='Varianta cuantică').select('noisy').run()
    assert not app.exception and app.session_state['experiment_json']==before
    app.toggle(key='simulate_incidents').set_value(True).run()
    app.session_state['qr_incidents']=[asdict(Incident('closed-x1',1))]
    app.run()
    next(b for b in app.button if b.label=='Rulează simularea').click().run()
    assert not app.exception
    after=json.loads(app.session_state['experiment_json'])
    assert after['classical']['full_bits']==[0,0,1,1,0]
    assert after['baseline_snapshot']['experiment_id']==baseline['experiment_id']
    assert after['model']['qubo']['linear']!=baseline['model']['qubo']['linear']
    next(b for b in app.button if b.label=='Pregătește PDF-ul simulării').click().run()
    assert not app.exception
    bundle=app.session_state['pdf_bundle']
    assert bundle[0]==app.session_state['experiment_json']
    assert bundle[1].startswith(b'%PDF')
