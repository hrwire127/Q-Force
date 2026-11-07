"""Sabina features must be reachable through the unified incident/QAOA pipeline."""
from dataclasses import asdict
import json
from pathlib import Path
import numpy as np
from streamlit.testing.v1 import AppTest
from experiment import run_experiment
from railway_data import ROUTES,DEMO_IDS
from railway_incidents import Incident
from classical_optimizer import optimize_routes
from classical_bridge import classical_routes
from reporting import html_report,pdf_report

BASE=[r for r in ROUTES if r['id'] in DEMO_IDS]


def test_sabina_reference_explanations_and_budget_frontier():
    result=run_experiment(BASE,maxiter=8,shots=128,mode='compare')
    analysis=result['classical_analysis']
    sabina=optimize_routes(classical_routes(result['routes']),7)
    assert result['classical']['bits']==sabina['vector_binar']
    assert analysis['result']['full_bits']==result['classical']['full_bits']
    assert analysis['audit']['planuri_valide']==result['feasible_plan_count']
    assert analysis['result']['planuri_evaluate']==32
    assert analysis['result']['punctaj_total']==15 and analysis['result']['cost_total']==7
    assert len(analysis['result']['solutii_optime'])==len(result['classical_optima'])==2
    profile={p['buget']:p['punctaj_total'] for p in analysis['budget_profile']}
    assert [profile[i] for i in (6,7,8)]==[14,15,18]
    for backend,audit in result['distribution_audits'].items():
        assert np.isclose(audit['probabilitate_planuri_valide'],result['samples'][backend]['p_feasible'])
        assert np.isclose(audit['probabilitate_solutii_optime'],result['samples'][backend]['p_optimal_feasible'])
        assert np.isclose(audit['punctaj_mediu'],result['samples'][backend]['mean_true_score'])
        assert audit['total_masurari']==128
        best=result['sampled_plan_audits'][backend]['best_feasible']
        if best: assert best['este_valid'] and best['full_bits']==result['samples'][backend]['best_feasible']['full_bits']
    html=html_report(result)
    assert 'SABINA CLASSICAL ANALYSIS' in html and 'Classical explanation and investment trade-offs' in html
    assert analysis['explanation']['rezumat'] in html
    assert pdf_report(result).startswith(b'%PDF')


def test_classical_analysis_honors_closures_and_construction_surcharges():
    incidents=[asdict(Incident('close-x1',1)),asdict(Incident('cost-route6',6,'technical',construction_cost_delta=2))]
    result=run_experiment(BASE,incidents=incidents,maxiter=8,shots=128)
    analysis=result['classical_analysis']
    assert analysis['decision_ids']==[0,2,6,8]
    assert 1 not in analysis['result']['ids_rute']
    assert next(r for r in result['routes'] if r['id']==6)['cost']==6
    for rows in (analysis['pareto'],analysis['alternatives']['planuri'],analysis['budget_profile']):
        assert all(p['full_bits'][1]==0 and 1 not in p['ids_rute'] for p in rows)
    assert analysis['result']['punctaj_total']==result['classical']['valoare_totala']
    assert analysis['result']['cost_total']==result['classical']['cost_total']
    closed=run_experiment(BASE,incidents=[asdict(Incident(str(r['id']),r['id'])) for r in BASE],maxiter=8,shots=128)
    assert closed['classical_analysis']['result']['full_bits']==[0]*5
    assert closed['classical_analysis']['result']['planuri_evaluate']==1
    assert not closed['distribution_audits']


def test_sabina_analysis_is_accessible_in_existing_ui_and_exports():
    app=AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py',default_timeout=60).run()
    next(b for b in app.button if b.label=='Rulează simularea').click().run()
    assert not app.exception,app.exception
    result=json.loads(app.session_state['experiment_json'])
    assert any('Niciun plan valid' in item.value for item in app.markdown)
    assert 'classical_analysis' in result
    next(b for b in app.button if b.label=='Pregătește rapoartele HTML și PDF').click().run()
    assert not app.exception,app.exception
    bundle=app.session_state['report_bundle']
    assert bundle[0]==app.session_state['experiment_json']
    assert 'SABINA CLASSICAL ANALYSIS' in bundle[1]
    assert bundle[2].startswith(b'%PDF')
