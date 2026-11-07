"""Connect the existing route explorer to the quantum experiment pipeline."""
import json
import streamlit as st
import pandas as pd
from dataclasses import fields
from experiment import run_railway_optimization, RailwayScenario, SimulationConfig
from analysis_views import probability_rows, score_rows, resource_rows, distribution_rows
from railway_map import deseneaza_harta
from railway_catalog import POSITIONS
from reporting import html_report, pdf_report
from railway_incidents import comparison, scenario
from incident_ui import render_geography, geographic_figure


def render_experiment(routes,budget,state=None):
    state=state if state is not None else scenario(routes)
    st.session_state.setdefault('experiment_snapshots',{})
    st.subheader('Optimization Center')
    with st.expander('Parametrii simulării',expanded=True):
        a,b,c=st.columns(3)
        penalty=a.number_input('Penalizare',min_value=.01,max_value=10.,value=.7,step=.1)
        p=b.slider('Adâncime QAOA p',1,3,1)
        shots=c.select_slider('Măsurări',options=[256,512,1024,2048,4096,8192],value=2048)
        seed=a.number_input('Seed',min_value=0,max_value=2**32-1,value=2026)
        maxiter=b.slider('Evaluări COBYLA per restart',max(5,2*p+2),100,30)
        restarts=c.slider('Restarturi',1,4,1)
        optimizer=a.selectbox('Optimizator',options=['COBYLA'])
        optimizer_tol=b.number_input('Toleranță optimizator',min_value=1e-6,max_value=.1,value=1e-4,format='%.6f')
        transpilation_level=c.slider('Nivel optimizare transpiler',0,3,1)
        mode=st.selectbox('Backend',options=['ideal','compare'],format_func=lambda m:'Ideal' if m=='ideal' else 'Ideal + zgomot sintetic local (max. 8 rute)')
    config=dict(budget=budget,penalty=penalty,p=p,shots=shots,seed=seed,maxiter=maxiter,restarts=restarts,mode=mode,
                optimizer=optimizer,optimizer_tol=optimizer_tol,transpilation_level=transpilation_level)
    fingerprint=json.dumps([routes,config,state['incidents'],state['time']],sort_keys=True)
    active_count=len(state['available_routes'])
    allowed=bool(routes) and active_count<=10 and (mode!='compare' or active_count<=8)
    if not allowed: st.warning('Selectează 1–10 rute; comparația cu zgomot acceptă maximum 8.')
    if st.button('Rulează baseline fără incidente',disabled=not (0<len(routes)<=10 and (mode!='compare' or len(routes)<=8))):
        try:
            with st.spinner('Rulez referința fără incidente…'):
                baseline=run_railway_optimization(RailwayScenario(routes),SimulationConfig(**config))
                st.session_state.baseline_json=json.dumps(baseline)
                st.session_state.experiment_snapshots[baseline['created_utc']]=st.session_state.baseline_json
                st.success('Baseline salvat separat; incidentele și experimentele existente sunt păstrate.')
        except Exception as exc: st.error(f'Baseline eșuat: {exc}')
    if st.button('Rulează simularea',type='primary',disabled=not allowed):
        st.session_state.pop('experiment_json',None)
        try:
            with st.status('Enumerare exactă, construire QUBO/Ising, antrenare și măsurare QAOA…') as status:
                result=run_railway_optimization(RailwayScenario(routes,state['incidents'],state['time']),SimulationConfig(**config))
                if not state['active_incidents']:
                    st.session_state.baseline_json=json.dumps(result)
                elif 'baseline_json' in st.session_state:
                    baseline=json.loads(st.session_state.baseline_json)
                    result['baseline_comparison']=comparison(baseline,result)
                    result['baseline_metadata']={k:baseline[k] for k in ('created_utc','config','original_routes')}
                    result['baseline_snapshot']=baseline
                st.session_state.experiment_json=json.dumps(result)
                st.session_state.experiment_snapshots[result['created_utc']]=st.session_state.experiment_json
                if state['active_incidents']:
                    st.session_state.disrupted_json=st.session_state.experiment_json
                st.session_state.experiment_fingerprint=fingerprint
                status.update(label='Experiment finalizat',state='complete')
        except Exception as exc:
            st.error(f'Experiment eșuat: {exc}')
    with st.expander('Before / After — snapshot-uri păstrate',expanded=True):
        if 'baseline_json' in st.session_state and 'experiment_json' in st.session_state:
            baseline=json.loads(st.session_state.baseline_json)
            after=json.loads(st.session_state.get('disrupted_json',st.session_state.experiment_json))
            st.dataframe(pd.DataFrame(comparison(baseline,after)))
            st.caption('Fiecare probabilitate de optim este raportată la optimul fezabil al propriului scenariu. Energiile unor modele sau spații de decizie diferite nu măsoară o îmbunătățire directă.')
            if any(baseline['config'].get(f.name)!=after['config'].get(f.name) for f in fields(SimulationConfig)) or baseline['original_routes']!=after['original_routes']:
                st.warning('Snapshot-urile folosesc configurații sau selecții diferite; consultă metadatele înainte de comparație.')
            with st.expander('Metadatele snapshot-urilor'):
                st.json({'baseline':baseline['config'],'after':after['config']})
            st.caption('Planuri complete în ordinea rutelor originale; distribuțiile sunt aliniate numai când ordinea originală coincide.')
            st.dataframe([{'Scenario':name,'Classical bits':r['classical']['full_bits'],
                'QAOA bits':r['samples']['ideal']['best_feasible']['full_bits'] if r['samples']['ideal']['best_feasible'] else None}
                for name,r in [('baseline',baseline),('disrupted',after)]],hide_index=True)
            comparison_df=pd.DataFrame(distribution_rows(baseline,after)).pivot(index='Original plan',columns='Scenario',values='Probability').fillna(0)
            st.bar_chart(comparison_df)
            if st.checkbox('Hărți Before / After',key='before_after_maps'):
                for column,(name,r) in zip(st.columns(2),[('Baseline',baseline),('Disrupted',after)]):
                    with column:
                        st.write(name)
                        mode_plan=st.selectbox('Soluție comparată',['Classical','Best feasible QAOA'],key=name+'_comparison_plan')
                        plan=r['classical'] if mode_plan=='Classical' else r['samples']['ideal']['best_feasible']
                        st.plotly_chart(geographic_figure(r['scenario'],plan['ids_rute'] if plan else []),key=name+'_before_after_map',width='stretch')
        else: st.caption('Rulează un baseline și apoi un scenariu modificat pentru comparație.')
        snapshots=st.session_state.experiment_snapshots
        if snapshots:
            selected_snapshot=st.selectbox('Snapshot arhivat (UTC)',list(snapshots),key='archived_snapshot')
            archived=json.loads(snapshots[selected_snapshot])
            st.caption(f"Arhivă: buget {archived['config']['budget']}, rute blocate {archived['scenario']['blocked_ids']}, scor clasic {archived['classical']['valoare_totala']}. Fiecare rulare rămâne păstrată separat.")
            if st.checkbox('Inspectează harta snapshot-ului arhivat',key='show_archived_map'):
                st.plotly_chart(geographic_figure(archived['scenario'],archived['classical']['ids_rute']),key='archived_map',width='stretch')
            if st.button('Pregătește exportul snapshot-ului arhivat'):
                st.session_state.archived_bundle=(selected_snapshot,html_report(archived),pdf_report(archived))
            bundle=st.session_state.get('archived_bundle')
            if bundle and bundle[0]==selected_snapshot:
                st.download_button('HTML arhivat',bundle[1],'archived_railways.html','text/html')
                st.download_button('PDF arhivat',bundle[2],'archived_railways.pdf','application/pdf')
    if 'experiment_json' not in st.session_state:
        st.info('Configurează și rulează simularea pentru rezultate și rapoarte.'); return
    if st.session_state.experiment_fingerprint!=fingerprint:
        st.info('Configurația s-a schimbat. Rulează din nou pentru rezultatele acestei configurații.'); return
    result=json.loads(st.session_state.experiment_json)
    sample_mode=st.radio('Rezultat afișat',list(result['samples']),horizontal=True)
    sample=result['samples'][sample_mode]
    a,b,c=st.columns(3)
    a.metric('Optim clasic fezabil',result['classical']['valoare_totala'],f"Cost {result['classical']['cost_total']}")
    b.metric('Minim energie QUBO',f"{result['qubo_minimum']['energie']:.3f}",f"Cost {result['qubo_minimum']['cost_total']}")
    best=sample['best_feasible']
    c.metric('Cel mai bun QAOA fezabil',best['valoare_totala'] if best else 'Neobservat',f"Cost {best['cost_total']}" if best else None)
    st.caption('E(x) = −scor(x) + penalizare × (cost(x) − buget)². Energia și fezabilitatea sunt obiective distincte.')
    if not result['qubo_minimum']['valid']: st.warning('Minimul QUBO depășește bugetul.')
    st.caption(f"Enumerare exactă: {result['plan_count']} planuri, {result['feasible_plan_count']} fezabile, {len(result['classical_optima'])} optime fezabile și {len(result['qubo_minima'])} minime de energie.")
    if 'classical_analysis' in result:
        analysis=result['classical_analysis']
        with st.expander('De ce este optim acest plan? — analiza Sabina',expanded=True):
            st.write(analysis['explanation']['rezumat'])
            st.caption('Analiza folosește aceleași rute disponibile, costuri și buget ca QAOA. Rutele închise au fost eliminate înainte de enumerare.')
            st.write('Top 3 planuri fezabile (inclusiv egalități optime)')
            columns=['full_bits','ids_rute','cost_total','punctaj_total','pierdere_punctaj','economie_cost']
            st.dataframe([{k:p[k] for k in columns} for p in analysis['alternatives']['planuri']],hide_index=True)
            st.write('Frontiera Pareto: cost / punctaj')
            st.dataframe([{k:p[k] for k in ('full_bits','ids_rute','cost_total','punctaj_total')} for p in analysis['pareto']],hide_index=True)
            profile=pd.DataFrame(analysis['budget_profile']).set_index('buget')
            st.line_chart(profile['punctaj_total'],x_label='Buget',y_label='Punctaj maxim fezabil')
            st.caption('Graficul bugetului și explicația sunt calcule clasice ipotetice, nu noi rulări QAOA.')
            st.write('Audit clasic al distribuțiilor QAOA')
            st.dataframe([{'Backend':backend,**{k:audit[k] for k in (
                'probabilitate_planuri_valide','probabilitate_solutii_optime','punctaj_mediu','cost_mediu')}}
                for backend,audit in result['distribution_audits'].items()],hide_index=True)
    views={'Rețea disponibilă':None,'Optim clasic':result['classical'],'Minim QUBO':result['qubo_minimum'],'Cel mai frecvent QAOA':sample['most_frequent']}
    if best: views['Cel mai bun QAOA fezabil']=best
    choice=st.selectbox('Plan pe hartă',list(views),index=1); plan=views[choice]
    if plan:
        st.write(f"Rute {plan['ids_rute']} · Cost {plan['cost_total']} · Scor {plan['valoare_totala']} · Energie {plan['energie']:.3f} · Fezabil {plan['valid']}")
        st.caption(f"Mapare decizii active: {result['decision_map']['active_ids']} → ordine originală: {result['decision_map']['original_ids']}. Plan complet: {plan['full_bits']}")
    render_geography(result['scenario'],result['scenario']['routes'],plan['ids_rute'] if plan else [],key='result_map')
    st.subheader('Probabilități exacte versus estimări din măsurări')
    probabilities=pd.DataFrame(probability_rows(result)).set_index('Source')
    st.dataframe(probabilities)
    st.bar_chart(probabilities[['Feasible','Infeasible']],stack=True)
    st.caption(f"Energia medie exactă statevector: {result['exact_ideal_statistics']['expected_energy']:.6f}; energia empirică {sample_mode}: {sample['expected_energy']:.6f}.")
    st.bar_chart(pd.DataFrame(score_rows(result)).set_index('Method')[['Score']])
    st.dataframe(pd.DataFrame(resource_rows(result)),hide_index=True)
    st.dataframe([{'Backend':mode,**{k:v for k,v in s.items() if isinstance(v,(float,int))}} for mode,s in result['samples'].items()],hide_index=True)
    st.write('Cel mai frecvent plan măsurat:',sample['most_frequent'])
    df=pd.DataFrame(sample['distribution']).set_index('bitstring')
    st.bar_chart(df['probability']); st.dataframe(df[['cost_total','valoare_totala','energie','valid','count','probability']])
    history=pd.DataFrame(result['quantum']['optimizare']['history'])
    if not history.empty:
        st.line_chart(history.set_index('evaluation')['energy'])
    else:
        st.info('Toate conexiunile sunt blocate: un singur plan gol determinist, fără circuit sau măsurări QAOA.')
    with st.expander('Configurație, reproducibilitate și resurse circuit'):
        st.json({k:result[k] for k in ('config','resources','versions','runtime_seconds')})
        st.json({'gamma':result['quantum'].get('gamma',[]),'beta':result['quantum'].get('beta',[]),
                 'optimization':result['quantum']['optimizare']})
    with st.expander('Model QUBO / Ising și toate egalitățile optime'):
        st.json(result['model'])
        st.dataframe(result['classical_optima'])
        st.dataframe(result['qubo_minima'])
    if st.button('Pregătește rapoartele HTML și PDF'):
        with st.spinner('Generez rapoartele din snapshot-ul afișat…'):
            st.session_state.report_bundle=(st.session_state.experiment_json,html_report(result),pdf_report(result))
    bundle=st.session_state.get('report_bundle')
    if bundle and bundle[0]==st.session_state.experiment_json:
        st.download_button('Descarcă HTML',bundle[1],'quantum_railways.html','text/html')
        st.download_button('Descarcă PDF',bundle[2],'quantum_railways.pdf','application/pdf')
