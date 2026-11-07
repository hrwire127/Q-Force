"""Validated simulated incidents and their explicit effects on the railway graph.

Time is scenario-relative minutes. Delays and operating costs never alter the
construction objective. Only explicit construction_cost_delta changes its cost.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
from math import isfinite
from random import Random
import networkx as nx

TYPES = {'closure': 'Închidere completă', 'maintenance': 'Mentenanță temporară',
         'technical': 'Defecțiune tehnică', 'weather': 'Perturbare meteo',
         'capacity': 'Capacitate redusă', 'delay': 'Întârziere',
         'operating_cost': 'Cost operațional crescut'}
SEVERITIES = ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')


@dataclass(frozen=True)
class Incident:
    incident_id: str
    route_id: int
    incident_type: str = 'closure'
    severity: str = 'HIGH'
    status: str = 'active'
    description: str = 'Incident simulat'
    delay_minutes: int = 0
    cost_delta: int = 0  # operating cost only, NOT the construction objective
    construction_cost_delta: int = 0
    capacity_percent: int = 100
    start_time: int = 0
    end_time: int | None = None
    source: str = 'simulated'

    def __post_init__(self):
        if not isinstance(self.incident_id, str) or not self.incident_id.strip():
            raise ValueError('Incident ID is required.')
        if type(self.route_id) is not int or self.route_id < 0:
            raise ValueError('Route ID must be a nonnegative integer.')
        if self.incident_type not in TYPES or self.severity not in SEVERITIES:
            raise ValueError('Invalid incident type or severity.')
        if self.status not in ('active', 'resolved') or self.source != 'simulated':
            raise ValueError('Only active/resolved simulated incidents are supported.')
        if not isinstance(self.description,str) or not self.description.strip():
            raise ValueError('Description is required.')
        for name in ('delay_minutes','cost_delta','construction_cost_delta','start_time'):
            value=getattr(self,name)
            if type(value) is not int or not 0 <= value <= 100000:
                raise ValueError(f'{name} must be an integer in [0,100000].')
        if type(self.capacity_percent) is not int or not 1 <= self.capacity_percent <= 100:
            raise ValueError('Capacity must be an integer in [1,100]. Use closure for zero capacity.')
        if self.end_time is not None and (type(self.end_time) is not int or self.end_time<=self.start_time):
            raise ValueError('End time must follow start time.')

    def applies(self, time=0):
        return self.status=='active' and self.start_time<=time and (self.end_time is None or time<self.end_time)


def normalize(incidents, routes):
    ids={r['id'] for r in routes}; seen=set(); result=[]
    for item in incidents:
        inc=item if isinstance(item,Incident) else Incident(**item)
        if inc.route_id not in ids or inc.incident_id in seen:
            raise ValueError('Unknown route or duplicate incident ID.')
        seen.add(inc.incident_id); result.append(inc)
    return result


def resolve(incidents, incident_id):
    if incident_id not in {i['incident_id'] for i in incidents}:
        raise ValueError('Unknown incident ID.')
    return [{**i,'status':'resolved'} if i['incident_id']==incident_id else dict(i) for i in incidents]


def scenario(routes, incidents=(), time=0):
    if type(time) is not int or time<0: raise ValueError('Scenario time must be nonnegative integer minutes.')
    items=normalize(incidents,routes)
    active=[i for i in items if i.applies(time)]
    blocked=sorted({i.route_id for i in active if i.incident_type in ('closure','maintenance')})
    modified=[]
    for original in routes:
        route=deepcopy(original); effects=[i for i in active if i.route_id==route['id']]
        route.update(original_cost=route['cost'], delay_minutes=sum(i.delay_minutes for i in effects),
                     operating_cost_delta=sum(i.cost_delta for i in effects),
                     capacity_percent=min([i.capacity_percent for i in effects] or [100]))
        route['cost']+=sum(i.construction_cost_delta for i in effects)
        route['status']='blocked' if route['id'] in blocked else 'degraded' if effects else 'available'
        route['incident_ids']=[i.incident_id for i in effects]
        modified.append(route)
    return dict(routes=modified,available_routes=[r for r in modified if r['id'] not in blocked],
                blocked_ids=blocked, incidents=[asdict(i) for i in items],
                active_incidents=[asdict(i) for i in active], time=time)


def available_graph(state):
    graph=nx.MultiGraph()
    graph.add_nodes_from(city for r in state['routes'] for city in r['cities'])
    for route in state['available_routes']:
        graph.add_edge(*route['cities'],key=route['id'],route_id=route['id'],
                       construction_cost=route['cost'],reward=route['value'],
                       delay_minutes=route['delay_minutes'],operating_cost_delta=route['operating_cost_delta'])
    return graph


def connectivity(state):
    graph=available_graph(state)
    components=sorted([sorted(c) for c in nx.connected_components(graph)],key=lambda c:(-len(c),c))
    return dict(city_count=len(graph),available_route_count=graph.number_of_edges(),
                blocked_route_count=len(state['blocked_ids']),component_count=len(components),
                components=components,isolated_cities=sorted(nx.isolates(graph)))


def alternative_path(state, start, end):
    graph=available_graph(state)
    if start not in graph or end not in graph: return None
    try: cities=nx.shortest_path(graph,start,end,weight='construction_cost')
    except nx.NetworkXNoPath: return None
    ids=[]; cost=0
    for a,b in zip(cities,cities[1:]):
        edge=min(graph[a][b].values(),key=lambda d:(d['construction_cost'],d['route_id']))
        ids.append(edge['route_id']); cost+=edge['construction_cost']
    return dict(cities=cities,route_ids=ids,construction_cost=cost)


def random_incidents(routes, seed=2026, count=2):
    if type(seed) is not int or type(count) is not int or not 0<=count<=len(routes):
        raise ValueError('Invalid random scenario configuration.')
    rng=Random(seed); selected=rng.sample(sorted(routes,key=lambda r:r['id']),count)
    result=[]
    for n,r in enumerate(selected):
        kind=rng.choice(list(TYPES))
        result.append(asdict(Incident(f'RND-{seed}-{n}',r['id'],kind,rng.choice(SEVERITIES),
            delay_minutes=rng.randint(5,60) if kind in ('delay','weather','technical') else 0,
            cost_delta=rng.randint(1,5) if kind=='operating_cost' else 0,
            capacity_percent=rng.choice([25,50,75]) if kind=='capacity' else 100)))
    return result


def reconstruct(bits, active_ids, original_ids):
    if len(bits)!=len(active_ids) or any(b not in (0,1) for b in bits):
        raise ValueError('One binary bit per active decision is required.')
    if len(set(active_ids))!=len(active_ids) or not set(active_ids)<=set(original_ids):
        raise ValueError('Invalid active-to-original decision map.')
    values=dict(zip(active_ids,bits))
    return [int(values.get(rid,0)) for rid in original_ids]


def comparison(before,after):
    def row(result):
        s=result['samples']['ideal']; state=result['scenario']
        return {'available_routes':len(result['routes']), 'blocked_routes':len(state['blocked_ids']),
                'feasible_plans':result['feasible_plan_count'],
                'classical_score':result['classical']['valoare_totala'],
                'classical_cost':result['classical']['cost_total'],
                'qubo_minimum_energy':result['qubo_minimum']['energie'],
                'qaoa_expected_energy':s['expected_energy'],'p_feasible':s['p_feasible'],
                'p_optimal_for_own_scenario':s['p_optimal_feasible'],
                'best_feasible_sample_score':s['best_feasible']['valoare_totala'] if s['best_feasible'] else None,
                'connected_components':result['connectivity']['component_count']}
    return {'baseline':row(before),'disrupted':row(after)}
