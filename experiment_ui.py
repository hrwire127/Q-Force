"""Focused presentation: quantum plan, histogram, classical plan and PDF."""
import json
import sqlite3
import pandas as pd
import altair as alt
import streamlit as st
from experiment import run_railway_optimization,RailwayScenario,SimulationConfig
from railway_incidents import scenario,comparison
from incident_ui import render_compact_map
from reporting import pdf_report
from simulation_history import save_snapshot,list_snapshots,load_snapshot,persist_session_history
from analysis_views import outcome_histogram,plan_probability_histogram,OUTCOME_CATEGORIES,OUTCOME_COLORS

CATEGORIES=OUTCOME_CATEGORIES
COLORS=OUTCOME_COLORS
PDF_VIEW_VERSION='probability-samples-v1'


def draw_histogram(result,backend='ideal',classical=False):
    rows=plan_probability_histogram(result,backend,classical)
    st.markdown('**Probability samples**')
    chart=alt.Chart(pd.DataFrame(rows)).mark_bar(cornerRadiusTopLeft=5,cornerRadiusTopRight=5).encode(
        x=alt.X('Plan:N',sort=sorted(r['Plan'] for r in rows),title='Plan în ordinea Qiskit (x0 la dreapta)',axis=alt.Axis(labelAngle=-90)),
        y=alt.Y('Probabilitate:Q',title='Probabilitate',axis=alt.Axis(format='.0%'),
                scale=alt.Scale(domain=[0,min(1,max(r['Probabilitate'] for r in rows)*1.15 or 1)])),
        color=alt.Color('Categorie:N',scale=alt.Scale(domain=CATEGORIES,range=COLORS),legend=alt.Legend(title=None,orient='bottom')),
        tooltip=['Plan','Categorie',alt.Tooltip('Probabilitate:Q',format='.2%'),'Măsurări','Rute','Cost','Scor','Energie']).properties(height=300)
    st.altair_chart(chart,width='stretch')
    if classical:
        st.caption('Clasic: distribuție deterministă, P=1 pentru planul exact ales. Enumerarea nu produce măsurări sau shots.')
    elif not result['routes']:
        st.caption('Plan gol determinist, P=1. Nu s-au executat circuitul sau măsurări cuantice.')
    else:
        st.caption('Cuantic: probabilitatea fiecărui plan = număr măsurări / total shots. Biții sunt reconstruiți în ordinea rutelor originale.')
    if len(result['samples'][backend]['distribution'])>64:
        st.caption('Sunt afișate cel mult 64 de planuri, fără renormalizarea probabilităților.')


def render_plan(result,plan,key):
    if plan is None:
        st.warning('Nu a fost observat niciun plan fezabil în măsurările acestei rulări.'); return
    by_id={r['id']:r for r in result['scenario']['routes']}
    names=[' — '.join(by_id[rid]['cities']) for rid in plan['ids_rute']]
    st.write('**Conexiunile planului:** '+('; '.join(names) if names else 'Nicio conexiune selectată.'))
    a,b,c=st.columns(3)
    a.metric('Scor',plan['valoare_totala'])
    b.metric('Energie',f"{plan['energie']:.3f}")
    c.metric('Cost',plan['cost_total'])
    st.caption(f"Buget {result['config']['budget']} · "+('Plan fezabil' if plan['valid'] else 'Plan nefezabil'))
    render_compact_map(result['scenario'],plan['ids_rute'],key=key,plan_only=True)


def remember_result(result):
    payload=json.dumps(result)
    st.session_state.experiment_json=payload
    st.session_state.setdefault('experiment_snapshots',{})[result['created_utc']]=payload
    try:
        save_snapshot(result)
        if 'baseline_snapshot' in result: save_snapshot(result['baseline_snapshot'])
    except (OSError,ValueError,sqlite3.Error) as exc:
        st.warning(f'Rezultatul este disponibil în sesiune, dar salvarea locală a eșuat: {exc}')
    return payload


def migrate_session_history():
    persist_session_history(st.session_state)


def render_history():
    st.subheader('Istoric și Before / After')
    try:
        migrate_session_history()
        entries=list_snapshots()
    except (OSError,ValueError,sqlite3.Error) as exc:
        st.warning(f'Istoricul local nu poate fi accesat: {exc}'); return
    if not entries:
        st.caption('Rulările vor apărea aici și vor fi păstrate local.'); return
    labels={r['id']:r['label'] for r in entries}
    ids=list(labels)
    selected=st.selectbox('Simulări salvate',ids,format_func=labels.get,key='history_selected')
    if st.button('Încarcă simularea'):
        st.session_state.pending_simulation=json.dumps(load_snapshot(selected)); st.rerun()
    with st.expander('Comparație Before / After',expanded=False):
        a,b=st.columns(2)
        before_id=a.selectbox('Înainte (Before)',ids,index=min(1,len(ids)-1),format_func=labels.get,key='compare_before')
        after_id=b.selectbox('După (After)',ids,format_func=labels.get,key='compare_after')
        before,after=load_snapshot(before_id),load_snapshot(after_id)
        rows=[]
        for label,result in [('Before',before),('After',after)]:
            by_id={r['id']:r for r in result['scenario']['routes']}
            for method,plan in [('Cuantic',result['samples']['ideal']['best_feasible']),('Clasic',result['classical'])]:
                rows.append({'Simulare':label,'Metodă':method,'Scor':plan['valoare_totala'] if plan else None,
                    'Energie':plan['energie'] if plan else None,'Cost':plan['cost_total'] if plan else None,
                    'Conexiuni':'; '.join(' — '.join(by_id[rid]['cities']) for rid in plan['ids_rute']) if plan else 'Neobservat',
                    'Incidente':result['scenario']['blocked_ids']})
        st.dataframe(rows,hide_index=True,width='stretch')
        st.caption('Energiile aparțin configurației fiecărei rulări; schimbarea modelului nu reprezintă automat o îmbunătățire.')


def render_sabina(result):
    analysis=result.get('classical_analysis')
    if not analysis: return
    with st.expander('De ce este optim acest plan?',expanded=True):
        st.write(analysis['explanation']['rezumat'])
        st.write('Alternative fezabile')
        fields=('ids_rute','cost_total','punctaj_total','pierdere_punctaj','economie_cost')
        st.dataframe([{k:p[k] for k in fields} for p in analysis['alternatives']['planuri']],hide_index=True)
        st.write('Frontiera Pareto')
        st.dataframe([{k:p[k] for k in ('ids_rute','cost_total','punctaj_total')} for p in analysis['pareto']],hide_index=True)
        profile=pd.DataFrame(analysis['budget_profile']).set_index('buget')
        st.line_chart(profile['punctaj_total'],x_label='Buget',y_label='Punctaj maxim fezabil')


def render_experiment(routes,budget,state=None):
    state=state if state is not None else scenario(routes)
    st.subheader('Optimization Center')
    a,b=st.columns(2)
    penalty=a.number_input('Penalizare',min_value=.01,max_value=10.,value=.7,step=.1,key='q_penalty')
    shots=b.select_slider('Măsurări',options=sorted(set([256,512,1024,2048,4096,8192,st.session_state.get('q_shots',2048)])),value=2048,key='q_shots')
    with st.expander('Setări QAOA',expanded=False):
        a,b,c=st.columns(3)
        p=a.slider('Adâncime QAOA p',1,3,1,key='q_depth')
        maxiter=b.slider('Evaluări COBYLA per restart',max(5,2*p+2),100,30,key='q_maxiter')
        restarts=c.slider('Restarturi',1,4,1,key='q_restarts')
        mode=st.selectbox('Backend',['ideal','compare'],format_func=lambda m:'Ideal' if m=='ideal' else 'Ideal + zgomot local',key='q_backend')
    visible=dict(budget=budget,penalty=penalty,p=p,shots=shots,maxiter=maxiter,restarts=restarts,mode=mode)
    internal=st.session_state.get('internal_simulation_settings',{})
    config=SimulationConfig(**visible,**internal)
    fingerprint=json.dumps([routes,visible,state['incidents'],state['time']],sort_keys=True)
    active=len(state['available_routes'])
    allowed=bool(routes)
    if not allowed: st.info('Selectează rutele pe care vrei să le analizezi.')
    if active>10:
        st.caption(f'{active} rute disponibile. Referința clasică se calculează prin programare dinamică; simularea poate dura mai mult pentru selecții mari.')
    if active>20 or (mode=='compare' and active>10):
        st.info('Pentru această dimensiune, simularea locală folosește aproximarea MPS. Referința clasică rămâne exactă.')
    if st.button('Rulează simularea',type='primary',disabled=not allowed):
        try:
            with st.status('Rulez optimizarea cuantică și referința clasică…') as status:
                result=run_railway_optimization(RailwayScenario(routes,state['incidents'],state['time']),config)
                if not state['active_incidents']:
                    st.session_state.baseline_json=json.dumps(result)
                elif 'baseline_json' in st.session_state:
                    baseline=json.loads(st.session_state.baseline_json)
                    result['baseline_snapshot']=baseline
                    result['baseline_metadata']={k:baseline[k] for k in ('created_utc','config','original_routes')}
                    result['baseline_comparison']=comparison(baseline,result)
                    st.session_state.disrupted_json=json.dumps(result)
                remember_result(result)
                st.session_state.loaded_configuration=fingerprint
                status.update(label='Simulare finalizată',state='complete')
        except Exception as exc:
            st.error(f'Simulare eșuată: {exc}')
    render_history()
    payload=st.session_state.get('experiment_json')
    if not payload: return
    if st.session_state.get('loaded_configuration')!=fingerprint:
        st.info('Configurația s-a schimbat. Rulează din nou sau încarcă o simulare din istoric pentru a vedea rezultatele ei.'); return
    result=json.loads(payload)
    if any(resource.get('approximate') for resource in result['resources'].values()):
        st.caption('Rezultatele cuantice includ o simulare MPS aproximată; histogramele folosesc măsurările efectiv generate.')
    st.caption('Simulare: '+result['created_utc'][:19].replace('T',' ')+' UTC')
    st.subheader('Rezultatul cuantic — cel mai bun plan fezabil găsit')
    backend=st.selectbox('Varianta cuantică',list(result['samples']),format_func=lambda m:'Ideal' if m=='ideal' else 'Cu zgomot',key='shown_quantum_backend') if len(result['samples'])>1 else 'ideal'
    if not result['routes']: st.info('Toate conexiunile sunt închise. Planul gol este determinist; QAOA nu a fost executat.')
    render_plan(result,result['samples'][backend]['best_feasible'],key='quantum_solution_map')
    draw_histogram(result,backend)
    st.subheader('Rezultatul prin formula clasică')
    render_plan(result,result['classical'],key='classical_solution_map')
    draw_histogram(result,classical=True)
    render_sabina(result)
    st.subheader('Export PDF')
    if st.button('Pregătește PDF-ul simulării'):
        with st.spinner('Generez PDF-ul din simularea afișată…'):
            st.session_state.pdf_bundle=(payload,pdf_report(result,presentation_backend=backend),backend,PDF_VIEW_VERSION)
    bundle=st.session_state.get('pdf_bundle')
    if bundle and bundle[0]==payload and len(bundle)>3 and bundle[2]==backend and bundle[3]==PDF_VIEW_VERSION:
        st.download_button('Descarcă PDF',bundle[1],'quantum_railways.pdf','application/pdf')
