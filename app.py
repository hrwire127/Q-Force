"""Configure → Run → Analyze → Map → Export."""
from __future__ import annotations
import pandas as pd
import streamlit as st
from experiment import run_experiment
from railway_data import DEMO_IDS, POSITIONS, ROUTES
from railway_map import deseneaza_harta
from reporting import html_report, pdf_report

st.set_page_config(page_title="Quantum Railways", page_icon="🚆", layout="wide")
st.title("🚆 Quantum Railways")
labels={r['id']:f"{r['id']} · {r['cities'][0]} — {r['cities'][1]} (cost {r['cost']}, scor {r['value']})" for r in ROUTES}
with st.sidebar:
    st.header("Configurează experimentul")
    ids=st.multiselect("Rute (max. 10)",list(labels),default=DEMO_IDS,format_func=labels.get,max_selections=10)
    budget=st.slider("Buget",0,30,7); penalty=st.number_input("Penalizare QUBO",.1,10.,.7,.1)
    depth=st.slider("Adâncime QAOA p",1,3,1); shots=st.select_slider("Măsurări",[256,512,1024,2048,4096],2048)
    seed=st.number_input("Seed",0,2**32-1,2026,1); maxiter=st.slider("Iterații COBYLA",5,80,30)
    restarts=st.slider("Restarturi",1,4,1); noisy=st.toggle("Simulare locală zgomotoasă")
    blocked=st.multiselect("Rute blocate",ids,format_func=labels.get)
    run=st.button("Rulează experimentul",type="primary",width="stretch")
routes=[r for r in ROUTES if r['id'] in ids]
st.dataframe(pd.DataFrame([{'ID':r['id'],'Rută':' — '.join(r['cities']),'Cost':r['cost'],'Scor':r['value']} for r in routes]),hide_index=True,width="stretch")
if run:
    try:
        with st.status("Rulez enumerarea clasică, QUBO și QAOA…",expanded=True) as state:
            st.session_state.result=run_experiment(routes,budget=budget,penalty=penalty,depth=depth,shots=shots,seed=int(seed),maxiter=maxiter,restarts=restarts,noisy=noisy,blocked_ids=blocked)
            state.update(label="Experiment finalizat",state="complete")
    except Exception as exc:
        st.session_state.pop('result',None); st.error(f"Experiment eșuat: {exc}")
result=st.session_state.get('result')
if not result:
    st.info("Baseline: 5 decizii, buget 7, penalizare 0,7, p=1, 2048 măsurări, seed 2026."); st.stop()
c,q,m,s=result['classical'],result['quantum'],result['qubo_minimum'],result['statistics']
st.header("Analiză")
a,b,d,e=st.columns(4)
a.metric("Optim clasic fezabil",c['punctaj_total'],f"cost {c['cost_total']}")
b.metric("Minim energie QUBO",f"{m['energie']:.2f}",f"scor {m['valoare_totala']}, cost {m['cost_total']}")
d.metric("Cel mai bun QAOA fezabil",q['valoare_totala'],f"cost {q['cost_total']}")
e.metric("P(feasible)",f"{s['p_feasible']:.1%}",f"P(optimal) {s['p_optimal_feasible']:.1%}")
if not m['valid']: st.warning("Minimul de energie QUBO nu este fezabil: energia și regula cost ≤ buget sunt raportate separat.")
tmap,tstats,texport=st.tabs(["Hartă","Distribuție & detalii","Export"])
with tmap:
    views={'Optim clasic':c['vector_binar'],'Minim QUBO':m['bits'],'Cel mai bun QAOA fezabil':list(reversed([int(x) for x in q['bitstring_recomandat']]))}
    choice=st.radio("Plan afișat",list(views),horizontal=True)
    chosen=[r['id'] for bit,r in zip(views[choice],result['routes']) if bit]
    st.plotly_chart(deseneaza_harta(result['routes'],chosen,result['config']['blocked_ids'],POSITIONS,fundal_online=False),width="stretch")
with tstats:
    st.json({'expected_energy':s['expected_energy'],'P(model minimum)':s['p_model_minimum'],'over_budget_rate':s['over_budget_rate'],'runtime_seconds':s['runtime_seconds'],'circuit':q['statistici']})
    df=pd.DataFrame([{'bitstring':k,'probability':v/result['config']['shots']} for k,v in sorted(q['counts'].items())])
    st.bar_chart(df.set_index('bitstring')); st.dataframe(df,hide_index=True,width="stretch")
with texport:
    st.download_button("Descarcă raport HTML",html_report(result),"quantum_railways_report.html","text/html")
    st.download_button("Descarcă raport PDF",pdf_report(result),"quantum_railways_report.pdf","application/pdf")
