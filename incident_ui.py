"""Incident controls and geographic inspection within the existing application."""
from dataclasses import asdict
from html import escape
import json
import plotly.graph_objects as go
import streamlit as st
from railway_catalog import POSITIONS
from railway_incidents import (Incident,TYPES,SEVERITIES,scenario,resolve,random_incidents,
                              connectivity,alternative_path)

STATUS_COLORS={'available':'#10B981','blocked':'#EF4444','degraded':'#F59E0B','selected':'#3B82F6','unselected':'#64748B'}


def geographic_figure(state, selected_ids=(), *, online=True, all_routes=None):
    fig=go.Figure(); seen=set(); selected=set(selected_ids)
    eligible={r['id'] for r in state['routes']}
    routes={r['id']:r for r in (all_routes or state['routes'])}
    routes.update({r['id']:r for r in state['routes']})
    for r in routes.values():
        status=r.get('status','available') if r['id'] in eligible else 'unselected'
        if status=='available' and r['id'] in selected: status='selected'
        color=STATUS_COLORS[status]
        a,b=[POSITIONS[c] for c in r['cities']]
        conflict=status=='blocked' and r['id'] in selected
        text=(f"Route {r['id']}: {escape(' - '.join(r['cities']))}<br>Construction cost: {r['cost']} / score: {r['value']}"
              f"<br>Status: {status}{' - SELECTED/BLOCKED CONFLICT' if conflict else ''}"
              f"<br>Selected in displayed result: {r['id'] in selected}"
              f"<br>Delay: {r.get('delay_minutes',0)} min / operating delta: {r.get('operating_cost_delta',0)}"
              f"<br>Capacity: {r.get('capacity_percent',100)}%<br>Schematic fictional connection<extra></extra>")
        points=[a,((a[0]+b[0])/2,(a[1]+b[1])/2),b]
        if status=='degraded' and r['id'] in selected:
            fig.add_trace(go.Scattermap(lon=[p[0] for p in points],lat=[p[1] for p in points],
                mode='lines',line={'color':STATUS_COLORS['selected'],'width':10},
                hoverinfo='skip',showlegend=False))
        fig.add_trace(go.Scattermap(lon=[p[0] for p in points],lat=[p[1] for p in points],
            mode='lines+markers',line={'color':color,'width':5 if status!='unselected' else 2},
            marker={'size':10 if conflict else 7,'color':color},customdata=[['route',r['id']]]*3,
            name=status,legendgroup=status,showlegend=status not in seen,hovertemplate=text))
        seen.add(status)
    for inc in state['active_incidents']:
        r=routes[inc['route_id']]; a,b=[POSITIONS[c] for c in r['cities']]
        fig.add_trace(go.Scattermap(lon=[(a[0]+b[0])/2],lat=[(a[1]+b[1])/2],mode='markers+text',
            marker={'size':16,'color':STATUS_COLORS[r['status']]},text=['!'],textfont={'color':'white'},
            name='Simulated incident',showlegend=False,customdata=[['route',r['id']]],
            hovertemplate=f"Simulated: {escape(TYPES[inc['incident_type']])}<br>{inc['severity']}<br>{escape(inc['description'])}<extra></extra>"))
    cities=sorted({city for route in routes.values() for city in route['cities']})
    fig.add_trace(go.Scattermap(lon=[POSITIONS[c][0] for c in cities],lat=[POSITIONS[c][1] for c in cities],
        mode='markers+text',text=cities,textposition='top center',marker={'size':11,'color':'#172554'},
        textfont={'color':'#172554'},customdata=[['city',c] for c in cities],name='Cities',
        hovertemplate='%{text}<extra></extra>'))
    fig.update_layout(map={'style':'carto-positron' if online else 'white-bg',
                          'center':{'lon':25,'lat':46},'zoom':5.3},
                      uirevision='incident-geography',clickmode='event+select',height=610,
                      margin={'l':0,'r':0,'t':0,'b':0},legend={'orientation':'h'})
    return fig


def regenerate_incident(routes):
    """Regenerate only the location, keeping incident effects and solver settings fixed."""
    from random import Random
    revision=st.session_state.get('simple_incident_revision',0)+1
    previous={i['route_id'] for i in st.session_state.get('qr_incidents',[])}
    candidates=[r for r in routes if r['id'] not in previous] or routes
    if not candidates:
        st.session_state.qr_incidents=[]; return
    route=Random(2026+revision).choice(candidates)
    st.session_state.simple_incident_revision=revision
    st.session_state.qr_incidents=[asdict(Incident(f'SIM-{revision}',route['id'],description='Închidere simulată - loc regenerat'))]
    st.session_state.scenario_time_internal=0


def toggle_simple_incidents(routes):
    if st.session_state.simulate_incidents:
        regenerate_incident(routes)
    else:
        st.session_state.qr_incidents=[]


def render_simple_incidents(routes):
    st.subheader('Simulare incidente')
    st.session_state.setdefault('qr_incidents',[])
    st.toggle('Simulează un incident',key='simulate_incidents',disabled=not routes,
              on_change=toggle_simple_incidents,args=(routes,))
    if st.session_state.get('simulate_incidents'):
        if st.button('Regenerează locul incidentului',disabled=not routes):
            regenerate_incident(routes); st.rerun()
    route_ids={r['id'] for r in routes}
    incidents=[i for i in st.session_state.qr_incidents if i['route_id'] in route_ids]
    current=scenario(routes,incidents,st.session_state.get('scenario_time_internal',0))
    by_id={r['id']:r for r in routes}
    for rid in current['blocked_ids']:
        st.warning('Incident simulat: '+ ' — '.join(by_id[rid]['cities'])+' · conexiune indisponibilă.')
    if not current['active_incidents']:
        st.caption('Rețeaua selectată nu are incidente active.')
    return current


def visible_map_state(state,selected_ids=None,plan_only=False):
    from copy import deepcopy
    displayed=deepcopy(state)
    if plan_only:
        chosen=set(selected_ids or ())
        displayed['routes']=[r for r in displayed['routes'] if r['id'] in chosen]
        displayed['active_incidents']=[i for i in displayed['active_incidents'] if i['route_id'] in chosen]
    return displayed


def render_compact_map(state,selected_ids=None,key='compact_map',plan_only=False):
    """Only checked network edges, or only the actual solution edges, and their cities."""
    displayed=visible_map_state(state,selected_ids,plan_only)
    if not displayed['routes']:
        st.info('Nicio conexiune de afișat pentru acest plan.'); return
    event=st.plotly_chart(geographic_figure(displayed,selected_ids or (),all_routes=None),key=key,
        width='stretch',on_select='rerun',selection_mode='points',config={'scrollZoom':True,'displaylogo':False})
    detail=selected_detail(event,displayed)
    if detail:
        if 'city' in detail: st.caption(detail['city'])
        else: st.caption(' — '.join(detail['cities'])+f" · cost {detail['cost']} · scor {detail['value']}")
    st.caption('Conexiuni schematice fictive · orașe geografice reale · © OpenStreetMap contributors © CARTO')


def selected_detail(event, state):
    points=event.get('selection',{}).get('points',[]) if event else []
    if not points: return None
    data=points[-1].get('customdata',[])
    if len(data)!=2: return None
    if data[0]=='city':
        city=data[1]
        return {'city':city,'coordinates_lon_lat':POSITIONS.get(city),
                'connections':[r['id'] for r in state['routes'] if city in r['cities']]}
    return next((r for r in state['routes'] if str(r['id'])==str(data[1])),None)


def render_incidents(routes, catalog):
    st.subheader('Incidente simulate')
    st.session_state.setdefault('qr_incidents',[])
    route_ids={r['id'] for r in routes}
    # Preserve incidents for deselected routes; apply only within the active scenario.
    labels={r['id']:f"#{r['id']} {' — '.join(r['cities'])}" for r in catalog}
    time=st.number_input('Moment scenariu (minute de la început)',0,100000,0,key='scenario_time')
    with st.expander('Incident Management',expanded=True):
        route=st.selectbox('Conexiune afectată',list(labels),format_func=labels.get,key='incident_route')
        kind=st.selectbox('Tip incident',list(TYPES),format_func=TYPES.get,key='incident_type')
        severity=st.selectbox('Severitate',SEVERITIES,index=2,key='incident_severity')
        a,b,c=st.columns(3)
        delay=a.number_input('Întârziere (minute)',0,1440,0,key='incident_delay')
        operating=b.number_input('Cost operațional suplimentar',0,1000,0,key='incident_operating')
        capacity=c.slider('Capacitate disponibilă (%)',1,100,100,key='incident_capacity')
        construction=st.number_input('Modificare explicită a costului de construcție (afectează obiectivul)',0,100,0,key='incident_construction')
        start=a.number_input('Început (minut)',0,100000,0,key='incident_start')
        end=b.number_input('Sfârșit (0 = fără termen)',0,100001,0,key='incident_end')
        description=st.text_input('Descriere',value='Incident simulat',key='incident_description')
        st.caption('Închidere și mentenanță: conexiune indisponibilă. Celelalte tipuri: degradare. Întârzierile, capacitatea și costul operațional nu modifică scorul sau costul de construcție.')
        if st.button('Adaugă incident simulat',key='add_incident'):
            counter=st.session_state.get('incident_counter',0)+1
            try:
                inc=Incident(f'SIM-{counter}',route,kind,severity,description=description,
                    delay_minutes=delay,cost_delta=operating,construction_cost_delta=construction,
                    capacity_percent=capacity,start_time=start,end_time=end or None)
                st.session_state.qr_incidents.append(asdict(inc)); st.session_state.incident_counter=counter
                st.rerun()
            except ValueError as exc: st.error(str(exc))
        if st.button('Blochează conexiunea',key='block_connection'):
            counter=st.session_state.get('incident_counter',0)+1
            st.session_state.qr_incidents.append(asdict(Incident(f'SIM-{counter}',route,start_time=time)))
            st.session_state.incident_counter=counter; st.rerun()
        if st.button('Deblochează conexiunea',key='unblock_connection'):
            st.session_state.qr_incidents=[{**i,'status':'resolved'} if i['route_id']==route and i['incident_type'] in ('closure','maintenance') else i for i in st.session_state.qr_incidents]
            st.rerun()
        entries=st.session_state.qr_incidents
        if entries:
            edit_id=st.selectbox('Incident existent', [i['incident_id'] for i in entries],key='edit_incident_id')
            a,b,c=st.columns(3)
            if a.button('Rezolvă incidentul'):
                st.session_state.qr_incidents=resolve(entries,edit_id); st.rerun()
            if b.button('Elimină incidentul'):
                st.session_state.qr_incidents=[i for i in entries if i['incident_id']!=edit_id]; st.rerun()
            if c.button('Actualizează din câmpurile de mai sus'):
                try:
                    updated=Incident(edit_id,route,kind,severity,description=description,delay_minutes=delay,
                        cost_delta=operating,construction_cost_delta=construction,capacity_percent=capacity,
                        start_time=start,end_time=end or None)
                    st.session_state.qr_incidents=[asdict(updated) if i['incident_id']==edit_id else i for i in entries]; st.rerun()
                except ValueError as exc: st.error(str(exc))
        seed=st.number_input('Seed incidente',0,2**32-1,2026,key='incident_seed')
        count=st.number_input('Număr incidente aleatoare',0,len(routes),min(2,len(routes)),key='incident_random_count')
        if st.button('Generează scenariu reproductibil',disabled=not routes):
            st.session_state.qr_incidents=random_incidents(routes,seed,count); st.rerun()
        if st.button('Resetează scenariul'):
            st.session_state.qr_incidents=[]; st.rerun()
    incidents=[i for i in st.session_state.qr_incidents if i['route_id'] in route_ids]
    state=scenario(routes,incidents,time)
    if st.session_state.qr_incidents:
        st.dataframe([{**i,'source':'Simulated'} for i in st.session_state.qr_incidents],hide_index=True)
    st.caption(f"{len(state['active_incidents'])} incidente active în selecția curentă; {len(state['blocked_ids'])} rute blocate. Toate incidentele sunt simulate.")
    return state


def render_geography(state,catalog,selected_ids=(),key='scenario_map'):
    online=st.toggle('Fundal geografic online',value=True,key=key+'_online')
    st.caption('Fundal: © OpenStreetMap contributors © CARTO. Rețeaua de optimizare: conexiuni fictive schematice, fără geometrie feroviară reală. Fundalul online necesită internet; harta offline păstrează coordonatele.')
    event=st.plotly_chart(geographic_figure(state,selected_ids,online=online,all_routes=catalog),
        key=key,width='stretch',on_select='rerun',selection_mode='points',config={'scrollZoom':True,'displaylogo':False})
    detail=selected_detail(event,state)
    if detail is None:
        points=event.get('selection',{}).get('points',[]) if event else []
        data=points[-1].get('customdata',[]) if points else []
        if len(data)==2 and data[0]=='route':
            detail=next((r for r in catalog if str(r['id'])==str(data[1])),None)
    if detail: st.write('Detalii selecție:',detail)
    st.caption('Click pe un oraș sau pe punctul unei conexiuni pentru detalii. Folosește zoom, pan și butonul fullscreen al graficului.')
    metrics=connectivity(state)
    st.write(f"Rețeaua configurată: {metrics['available_route_count']} conexiuni disponibile · {metrics['component_count']} componente · orașe izolate: {', '.join(metrics['isolated_cities']) or 'niciunul'}")
    cities=sorted({c for r in state['routes'] for c in r['cities']})
    if cities:
        a,b=st.columns(2)
        start=a.selectbox('Verifică accesibilitatea: de la',cities,key=key+'_start')
        end=b.selectbox('Până la',cities,index=min(1,len(cities)-1),key=key+'_end')
        path=alternative_path(state,start,end)
        if path: st.write('Cale disponibilă (minim de cost de construcție, nu timp de călătorie):',path)
        else: st.warning('Nu există o cale disponibilă între aceste orașe în rețeaua configurată.')
