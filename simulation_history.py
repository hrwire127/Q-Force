"""Local, append-only experiment history; independent of Streamlit sessions."""
from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import zlib


@contextmanager
def database():
    path=Path(os.environ.get('QUANTUM_RAILWAYS_HISTORY_DB',
              str(Path(__file__).resolve().parent/'output'/'simulation_history.sqlite3')))
    path.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(path,timeout=10) as connection:
        connection.execute('CREATE TABLE IF NOT EXISTS experiments (id TEXT PRIMARY KEY, created TEXT NOT NULL, label TEXT NOT NULL, payload BLOB NOT NULL)')
        yield connection


def save_snapshot(result):
    """Never replace an older experiment with recalculated values."""
    payload=json.dumps(result,ensure_ascii=False,sort_keys=True,allow_nan=False)
    key=result.get('experiment_id') or sha256(payload.encode()).hexdigest()
    config=result['config']; incident_count=len(result.get('scenario',{}).get('active_incidents',[]))
    created=result.get('created_utc','')
    label=f"{created[:19].replace('T',' ')} UTC · buget {config['budget']} · {len(result.get('original_routes',result['routes']))} rute · {incident_count} incidente · {key[:8]}"
    with database() as connection:
        connection.execute('INSERT OR IGNORE INTO experiments VALUES (?,?,?,?)',
                           (key,created,label,zlib.compress(payload.encode('utf-8'))))
    return key


def list_snapshots():
    with database() as connection:
        return [{'id':key,'label':label} for key,label in connection.execute(
            'SELECT id,label FROM experiments ORDER BY created DESC,id DESC')]


def load_snapshot(key):
    with database() as connection:
        row=connection.execute('SELECT payload FROM experiments WHERE id=?',(key,)).fetchone()
    if row is None: raise ValueError('Simularea nu mai este disponibilă în istoric.')
    return json.loads(zlib.decompress(row[0]).decode('utf-8'))


def persist_session_history(session):
    """Upgrade an already-open session before replacing any UI modules."""
    seen=session.setdefault('history_migrated_ids',set())
    payloads=list(session.get('experiment_snapshots',{}).values())
    payloads += [session[k] for k in ('baseline_json','disrupted_json','experiment_json') if k in session]
    for payload in payloads:
        result=json.loads(payload)
        key=result.get('experiment_id',result.get('created_utc',''))
        if key not in seen:
            save_snapshot(result); seen.add(key)
        baseline=result.get('baseline_snapshot')
        if baseline and baseline['experiment_id'] not in seen:
            save_snapshot(baseline); seen.add(baseline['experiment_id'])


def apply_pending_snapshot(session,routes):
    """Restore controls before widgets are created; viewing never reruns QAOA."""
    payload=session.pop('pending_simulation',None)
    if payload is None: return
    result=json.loads(payload); config=result['config']
    selected=set(result['decision_map']['original_ids'])
    for route in routes:
        session[f"selected_route_{route['id']}"]=route['id'] in selected
        session[f"route_{route['id']}"]=route['id'] in selected
    session['budget']=config['budget']
    session['route_search']=''
    for field,key in [('penalty','q_penalty'),('p','q_depth'),('shots','q_shots'),
                      ('maxiter','q_maxiter'),('restarts','q_restarts'),('mode','q_backend')]:
        session[key]=config[field]
    session['internal_simulation_settings']={k:config[k] for k in
        ('seed','optimizer','optimizer_tol','transpilation_level') if k in config}
    state=result['scenario']
    session['qr_incidents']=state['incidents']
    session['simulate_incidents']=bool(state['active_incidents'])
    session['scenario_time_internal']=state['time']
    session['experiment_json']=payload
    session['loaded_experiment_id']=result.get('experiment_id')
    session['loaded_configuration']=json.dumps([result['original_routes'],
        {k:config[k] for k in ('budget','penalty','p','shots','maxiter','restarts','mode')},
        state['incidents'],state['time']],sort_keys=True)
    baseline=result.get('baseline_snapshot')
    if baseline:
        session['baseline_json']=json.dumps(baseline)
        session['disrupted_json']=payload
    elif not state['active_incidents']:
        session['baseline_json']=payload
