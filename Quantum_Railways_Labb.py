"""Python export of every code cell in Quantum_Railways_Labb.ipynb.

Adaptations: CLI defaults, original 19-route sample, terminal/PNG display,
explicit IBM execution and external credentials. Run --help for options.
Requires the repository's notebook_support.py, qaoa_experiments.py and optimizer.
"""
import json
from pathlib import Path
import sys
from railway_script_support import (
    check_environment, connect_ibm, install_display,
    parse_args, save_job_record,
)


def main(argv=None):
    import sys
    # Preserve Romanian labels when Windows redirects the terminal output.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    args = parse_args(argv)
    prepared_service = prepared_backend = None
    if not args.dry_run and (args.ibm or args.check_ibm):
        prepared_service, prepared_backend = connect_ibm(args)
        print('IBM conectat:', prepared_backend.name, '| qubiti:', prepared_backend.num_qubits)
        if args.check_ibm:
            print('Verificare reusita; niciun job trimis.')
            return
    import matplotlib
    matplotlib.use('Agg')
    display, Markdown = install_display(args.output)

    # %% Notebook code cell 2
    import sys, subprocess, importlib.metadata as metadata
    from pathlib import Path
    import json
    try:
        import google.colab
        IN_COLAB=True
    except ImportError:
        IN_COLAB=False
    TESTED_VERSIONS = {'qiskit': '2.1.0', 'qiskit-aer': '0.17.0', 'numpy': '2.2.6', 'scipy': '1.15.3', 'networkx': '3.5', 'matplotlib': '3.10.3'}

    def ensure_environment(pins, installer=subprocess.check_call):
        missing=[];loaded_changes=[]
        for name,version in pins.items():
            try: current=metadata.version(name)
            except metadata.PackageNotFoundError: current=None
            if current!=version:
                missing.append(f'{name}=={version}')
                root=name.replace('-','_')
                if root in sys.modules: loaded_changes.append(root)
        if missing:
            installer([sys.executable,'-m','pip','install','--quiet',*missing])
        if loaded_changes:
            raise RuntimeError('Restart the runtime/kernel: an imported package was replaced. Then rerun this cell.')
        actual={name:metadata.version(name) for name in pins}
        assert actual==pins,'Environment versions differ; restart and rerun setup.'
        return actual

    installed_versions=check_environment(TESTED_VERSIONS)
    print('Colab' if IN_COLAB else 'Local notebook', '| Python',sys.version.split()[0])
    for name,version in installed_versions.items(): print(name,version)
    import numpy as np
    import matplotlib.pyplot as plt
    import networkx as nx
    from scipy.optimize import minimize

    from qiskit import QuantumCircuit,ClassicalRegister,transpile
    from qiskit.circuit import ParameterVector
    from qiskit.quantum_info import Statevector
    from qiskit_aer import AerSimulator
    from qiskit.providers.fake_provider import GenericBackendV2
    smoke=QuantumCircuit(1);smoke.h(0)
    assert np.allclose(Statevector.from_instruction(smoke).probabilities(),[.5,.5])
    assert GenericBackendV2(num_qubits=2,seed=2026).num_qubits==2
    plt.rcParams.update({'font.family':'DejaVu Sans','figure.dpi':110})
    print('Import and statevector smoke test passed.')

    # %% Notebook code cell 4

    # ==========================================
    # QUANTUM RAILWAYS - RETEA EXTINSA
    # ==========================================

    # Coordonatele geografice sunt definite direct in cod.
    # Rutele, costurile si valorile economice sunt fictive.

    # 1. Coordonatele oraselor
    POSITIONS = {
        'Iași': (27.6, 47.16667),
        'București': (26.10626, 44.43225),
        'Cluj-Napoca': (23.6, 46.76667),
        'Timișoara': (21.22571, 45.75372),
        'Satu Mare': (22.8857, 47.7928),
        'Brașov': (25.60613, 45.64861),
        'Sibiu': (24.15, 45.8),
        'Craiova': (23.8, 44.31667),
        'Constanța': (28.63432, 44.18073),

        # Orase din tarile vecine
        'Budapesta': (19.0402, 47.4979),
        'Sofia': (23.3219, 42.6977),
        'Belgrad': (20.4489, 44.7866),
        'Chișinău': (28.8638, 47.0105),
        'Cernăuți': (25.9358, 48.2915)
    }

    # 2. Rutele nationale
    # (plecare, destinatie, cost constructie, valoare)
    EDGE_DATA = [
        ('Iași', 'Brașov', 2, 4),
        ('Iași', 'Cluj-Napoca', 3, 6),
        ('Cluj-Napoca', 'Brașov', 2, 5),
        ('Timișoara', 'Cluj-Napoca', 4, 7),
        ('Timișoara', 'Sibiu', 3, 6),
        ('Sibiu', 'Brașov', 2, 4),
        ('Brașov', 'București', 4, 9),
        ('Sibiu', 'Craiova', 2, 4),
        ('București', 'Constanța', 4, 7),
        ('Craiova', 'București', 2, 5),
        ('Cluj-Napoca', 'Sibiu', 2, 4),
        ('Iași', 'Constanța', 6, 11),
        ('Satu Mare', 'Cluj-Napoca', 3, 6)
    ]

    # 3. Rutele internationale: cost de frontiera uniform = 1
    # (plecare, destinatie, constructie, valoare, cost frontiera)
    INTERNATIONAL_EDGES = [
        ('Timișoara', 'Budapesta', 4, 8, 1),
        ('București', 'Sofia', 4, 7, 1),
        ('Timișoara', 'Belgrad', 3, 9, 1),
        ('Iași', 'Chișinău', 3, 10, 1),
        ('Iași', 'Cernăuți', 4, 11, 1),
        ('Satu Mare', 'Budapesta', 4, 8, 1)
    ]

    # 4. Construim lista rutelor nationale
    ROUTES = [
        dict(
            id=i,
            cities=(u, v),
            cost=c,
            value=value,
            border_cost=0,
            international=False
        )
        for i, (u, v, c, value) in enumerate(EDGE_DATA)
    ]

    # 5. Adaugam rutele internationale
    for u, v, c, value, border in INTERNATIONAL_EDGES:
        ROUTES.append(
            dict(
                id=len(ROUTES),
                cities=(u, v),
                cost=c + border,
                value=value,
                border_cost=border,
                international=True
            )
        )

    # 6. Selectam toate rutele pentru optimizare
    DEMO_IDS = list(range(len(ROUTES)))
    demo_routes = [ROUTES[i] for i in DEMO_IDS]

    # 7. Buget introdus de utilizator
    BUDGET = args.budget

    # 8. Parametrii experimentului
    WEAK_PENALTY = args.penalty
    SEED = args.seed
    N_DECISIONS = len(demo_routes)
    MATHEMATICAL_DEEP_DIVE = False

    # 9. Verificam configuratia
    assert len(POSITIONS) == 14
    assert len(ROUTES) == 19
    assert N_DECISIONS == 19
    assert all(r['border_cost'] == 1 for r in ROUTES if r['international'])

    print("Numar orase:", len(POSITIONS))
    print("Numar rute nationale:", sum(not r['international'] for r in ROUTES))
    print("Numar rute internationale:", sum(r['international'] for r in ROUTES))
    print("Numar total rute:", len(ROUTES))
    print("Numar qubiti logici:", N_DECISIONS)
    print("Combinatii posibile:", 2 ** N_DECISIONS)
    print("Buget:", BUDGET)
    if args.dry_run:
        print(json.dumps(dict(network='notebook', cities=len(POSITIONS), routes=len(ROUTES),
            qubits=N_DECISIONS, budget=BUDGET, penalty=WEAK_PENALTY, depths=[1, 2],
            maxiter=args.maxiter, restarts=args.restarts, shots=args.shots, seed=SEED,
            real_hardware=False), ensure_ascii=False, indent=2))
        return
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'scenario.json').write_text(json.dumps(dict(network='notebook',
        positions=POSITIONS, routes=ROUTES, budget=BUDGET, penalty=WEAK_PENALTY,
        seed=SEED, maxiter=args.maxiter, restarts=args.restarts, shots=args.shots),
        ensure_ascii=False, indent=2), encoding='utf-8')

    # %% Notebook code cell 5
    # @title Provided helper code — maps, tables and count decoding
    from notebook_support import PlanReference, coefficient_energies

    TEAL, CORAL, GOLD, NAVY, GREY = '#008d83', '#d2554b', '#c18a18', '#17334a', '#bac3c9'

    def all_bitstrings(n):
        for k in range(2**n):
            yield [(k >> i) & 1 for i in range(n)]

    def decode_key(key, n):
        key = key.replace(' ', '')
        if len(key) != n or set(key) - {'0', '1'}:
            raise ValueError('Expected a measured key with exactly n binary bits')
        return [int(c) for c in key[::-1]]

    def show_table(headers, rows):
        def cell(x): return str(x).replace('|', '/').replace('\n', ' ')
        display(Markdown('| ' + ' | '.join(map(cell, headers)) + ' |\n| ' +
            ' | '.join(['---']*len(headers)) + ' |\n' +
            '\n'.join('| '+' | '.join(map(cell,row))+' |' for row in rows)))

    def draw_board(selected_ids=(), valid=True, title='Romanian cities • fictional connections', ax=None, routes=None, positions=None):
        routes=ROUTES if routes is None else routes
        positions=POSITIONS if positions is None else positions
        by_id={r['id']:r for r in routes}
        if ax is None: _, ax = plt.subplots(figsize=(9, 5.5))
        g=nx.Graph(); g.add_nodes_from(positions)
        g.add_edges_from(r['cities'] for r in routes)
        nx.draw_networkx_edges(g, positions, edge_color=GREY, width=1.5, ax=ax)
        if selected_ids:
            nx.draw_networkx_edges(g, positions, edgelist=[by_id[i]['cities'] for i in selected_ids],
                                  edge_color=TEAL if valid else CORAL, width=4, ax=ax)
        nx.draw_networkx_nodes(g,positions,node_size=90,node_color='white',edgecolors=NAVY,ax=ax)
        nx.draw_networkx_labels(g,{n:(x,y+.12) for n,(x,y) in positions.items()},
                               font_size=9,font_family='DejaVu Sans',font_color=NAVY,ax=ax)
        nx.draw_networkx_edge_labels(g,positions,
            edge_labels={r['cities']:f"{r['id']}: {r['cost']}" for r in routes},
            font_size=8,font_color=GOLD,ax=ax)
        ax.set_title(title,color=NAVY); ax.margins(.14); ax.set_axis_off()
        ax.set_aspect(1/np.cos(np.deg2rad(np.mean([lat for lon,lat in positions.values()]))))
        return ax

    def analyse_plan(bits, routes, budget, energy_function):
        if len(bits)!=len(routes) or any(b not in (0,1) for b in bits):
            raise ValueError('One binary decision is required per route')
        selected=selected_routes(bits,routes)
        cost=construction_cost(bits,routes); value=railway_value(bits,routes)
        feasible=is_feasible(bits,routes,budget)
        assert [r['id'] for r in selected]==[r['id'] for b,r in zip(bits,routes) if b]
        assert cost==sum(r['cost'] for r in selected)
        assert value==sum(r['value'] for r in selected)
        assert feasible==(cost<=budget)
        return dict(bits=list(bits),key=''.join(map(str,bits[::-1])),
                    route_ids=[r['id'] for r in selected],cost=cost,score=value,
                    feasible=bool(feasible),energy=float(energy_function(bits)))

    def show_plans(rows):
        show_table(['Plan in decision order','Measured key','Route IDs','Cost','True score','Energy','Feasible'],
            [(r['bits'],r['key'],r['route_ids'],r['cost'],r['score'],round(r['energy'],3),r['feasible']) for r in rows])

    def plot_distribution(counts, routes, budget, title='Sample probabilities'):
        n=len(routes)
        total=sum(counts.values())
        if total<=0: raise ValueError('No shots to plot')
        for key in counts: decode_key(key,n)
        keys=([format(k,f'0{n}b') for k in range(2**n)] if n<=8 else
              sorted(counts,key=lambda key:(-counts[key],key))[:20])
        fig,ax=plt.subplots(figsize=(11,3.8))
        ax.bar(keys,[counts.get(k,0)/total for k in keys],
            color=[TEAL if is_feasible(decode_key(k,n),routes,budget) else CORAL for k in keys])
        ax.axhline(1/(2**n),ls='--',color=NAVY,label='Uniform distribution')
        ax.set(title=title + (' (top 20 observed)' if n>8 else ''),
               xlabel='Measured key (variable 0 at right)',ylabel='Fraction of all shots')
        ax.tick_params(axis='x',rotation=90,labelsize=8)
        ax.legend();fig.tight_layout()
        return fig

    def distribution_metrics(counts, routes, budget, reference_rows):
        return reference_rows.metrics(counts,routes,budget)

    # %% Notebook code cell 6
    draw_board(title='Geographic city locations • fictional routes and costs');plt.show()
    show_table(['Decision','Physical route ID','Connection','Cost','Value'],
        [(f'x{i}',r['id'],'–'.join(r['cities']),r['cost'],r['value']) for i,r in enumerate(demo_routes)])
    my_plan=[int(i < 3) for i in range(N_DECISIONS)]  # Change this to your hand-selected plan.
    # Prediction (edit this Markdown or add a cell): cost __, value __, feasible __.

    # %% Notebook code cell 8
    def selected_routes(bits, routes):
        if len(bits) != len(routes) or any(b not in (0,1) for b in bits):
            raise ValueError('One binary decision is required per route')
        selected = []

        for i in range(len(bits)):
            if bits[i] == 1:
                selected.append(routes[i])

        return selected

    def construction_cost(bits,routes):
        # TODO: sum the construction costs of selected routes.
        return sum(route['cost'] for route in selected_routes(bits, routes))

    def railway_value(bits, routes):
        total_value = 0
        for i in range(len(bits)):
            if bits[i] == 1:
                total_value = total_value + routes[i]['value']

        return total_value

    def is_feasible(bits, routes, budget):
        cost = construction_cost(bits, routes)

        if cost <= budget:
            return True
        else:
            return False
        
    assert selected_routes([1]+[0]*(N_DECISIONS-1),demo_routes)==[demo_routes[0]], 'Exercise A: select routes whose bits are 1.'
    assert construction_cost([1]+[0]*(N_DECISIONS-1),demo_routes)==2, 'Exercise A: sum selected costs.'
    assert railway_value([1]+[0]*(N_DECISIONS-1),demo_routes)==4, 'Exercise A: sum selected values.'
    assert is_feasible([1]+[0]*(N_DECISIONS-1),demo_routes,2) is True, 'An exact-budget plan is feasible.'
    assert is_feasible([1]+[0]*(N_DECISIONS-1),demo_routes,1) is False, 'Do not accept an over-budget plan.'
    print('Our hand-selected plan:',my_plan,'cost',construction_cost(my_plan,demo_routes),
          'value',railway_value(my_plan,demo_routes),'feasible',is_feasible(my_plan,demo_routes,BUDGET))

    # %% Notebook code cell 10
    def model_energy(bits, routes, budget, penalty):

        # Calculam punctele obtinute
        value = railway_value(bits, routes)

        # Calculam cat costa rutele
        cost = construction_cost(bits, routes)

        # Calculam diferenta fata de buget
        difference = cost - budget

        # Calculam penalizarea
        penalty_value = penalty * (difference ** 2)

        # Calculam energia finala
        energy = -value + penalty_value

        return energy


    assert model_energy([0]*N_DECISIONS,demo_routes,BUDGET,WEAK_PENALTY) is not None, 'Exercise B: return the energy.'
    assert np.isclose(model_energy([0]*N_DECISIONS,demo_routes,7,0),0), 'No routes and no penalty gives zero.'
    assert np.isclose(model_energy([1]+[0]*(N_DECISIONS-1),demo_routes,2,.7),-4), 'Exact spending has no penalty.'

    # %% Notebook code cell 12
    def enumerate_demo_plans(penalty):
        # Complete numerical reference, without a dictionary per basis state.
        return PlanReference(demo_routes,BUDGET,penalty)

    classical_rows=enumerate_demo_plans(WEAK_PENALTY)
    assert len(classical_rows)==2**N_DECISIONS
    qubo_best=classical_rows.minimum_plan()
    classical_best=classical_rows.best_valid_plan()
    show_plans([qubo_best,classical_best])
    print('Exact reference states:',len(classical_rows))
    for penalty in [0.7,4.0]:
        plans=enumerate_demo_plans(penalty)
        best=plans.minimum_plan()
        print('Penalty:',penalty,'route IDs:',best['route_ids'],
              'cost:',best['cost'],'value:',best['score'],'energy:',best['energy'],
              'feasible:',best['feasible'])
    # Penalty 0 is evaluated directly: selecting all positive-value routes minimizes -V.
    bits=[int(r['value']>0) for r in demo_routes]
    show_plans([analyse_plan(bits,demo_routes,BUDGET,
        lambda x:model_energy(x,demo_routes,BUDGET,0))])

    # %% Notebook code cell 14
    def construct_qubo(routes, budget, penalty):
        costs = np.array([r['cost'] for r in routes], float)
        values = np.array([r['value'] for r in routes], float)

        linear = -values + penalty * (costs**2 - 2*budget*costs)

        quadratic = np.triu(2*penalty*np.outer(costs, costs), 1)

        if MATHEMATICAL_DEEP_DIVE:
            linear = -values + penalty * (costs**2 - 2*budget*costs)
            quadratic = np.triu(2*penalty*np.outer(costs, costs), 1)

        return dict(
            offset=penalty * budget**2,
            linear=linear,
            quadratic=quadratic
        )

    qubo=construct_qubo(demo_routes,BUDGET,WEAK_PENALTY)
    assert qubo['linear'] is not None and qubo['quadratic'] is not None, 'Exercise D: supply both coefficient arrays.'
    assert np.shape(qubo['linear'])==(N_DECISIONS,) and np.shape(qubo['quadratic'])==(N_DECISIONS,N_DECISIONS)
    assert np.allclose(qubo['quadratic'],np.triu(qubo['quadratic'],1)), 'Count each pair exactly once.'
    def qubo_energy(bits,q=qubo):
        x=np.array(bits)
        return float(q['offset']+q['linear']@x+x@q['quadratic']@x)
    qubo_energies=coefficient_energies(qubo['linear'],qubo['quadratic'],qubo['offset'])
    np.testing.assert_allclose(qubo_energies,classical_rows.energies,atol=1e-9)
    print('Direct and QUBO energies agree on all',2**N_DECISIONS,'plans.')

    # %% Notebook code cell 16
    def qubo_to_ising(q):
        a,b=q['linear'],q['quadratic']
        h=-a/2-(b.sum(axis=0)+b.sum(axis=1))/4
        if MATHEMATICAL_DEEP_DIVE:
            h = -a/2 - (b.sum(axis=0) + b.sum(axis=1))/4
        return dict(constant=float(q['offset']+a.sum()/2+b.sum()/4),h=h,J=b/4)

    ising=qubo_to_ising(qubo)
    assert ising['h'] is not None, 'Exercise E: supply the Z coefficients.'
    ising_energies=coefficient_energies(ising['h'],ising['J'],ising['constant'],spin=True)
    np.testing.assert_allclose(ising_energies,qubo_energies,atol=1e-9)
    print('Direct, QUBO and Ising energies agree on all',2**N_DECISIONS,'states.')

    # %% Notebook code cell 18
    def add_cost(qc, gamma, ising):

        h = ising['h']
        J = ising['J']

        # Calculam o valoare pentru a tine unghiurile mai mici
        scale = max(1, np.max(np.abs(h)), np.max(np.abs(J)))

        # Trecem prin fiecare qubit
        for i in range(len(h)):

            # Calculam unghiul pentru acest qubit
            unghi = 2 * gamma * h[i] / scale

            # Aplicam poarta RZ
            qc.rz(unghi, i)

        # Trecem prin toate perechile de qubiti
        for i in range(len(h)):

            for j in range(i + 1, len(h)):

                # Verificam daca perechea are o contributie
                if J[i][j] != 0:

                    # Calculam unghiul pentru pereche
                    unghi = 2 * gamma * J[i][j] / scale

                    # Aplicam poarta RZZ pe cei doi qubiti
                    qc.rzz(unghi, i, j)

        # Trimitem circuitul modificat inapoi
        return qc

    def add_mixer(qc, beta):

        # Trecem prin fiecare qubit
        for i in range(qc.num_qubits):

            # Aplicam poarta RX
            qc.rx(2 * beta, i)

        # Returnam circuitul
        return qc

    def parameterized_qaoa(q,p=1,measure=False):
        n=len(q['linear']);parameters=ParameterVector('theta',2*p)
        qc=QuantumCircuit(n);qc.h(range(n))
        for layer in range(p):
            add_cost(qc,parameters[2*layer],qubo_to_ising(q))
            add_mixer(qc,parameters[2*layer+1])
        if measure:
            register=ClassicalRegister(n,'plan');qc.add_register(register)
            qc.measure(range(n),register)
        return qc,list(parameters)

    phase_test=QuantumCircuit(N_DECISIONS);phase_test.h(range(N_DECISIONS));add_cost(phase_test,.31,ising)
    state=np.asarray(Statevector.from_instruction(phase_test))
    scale=max(1.,np.max(np.abs(ising['h'])),np.max(np.abs(ising['J'])))
    expected=np.exp(-1j*.31*qubo_energies/scale)
    assert np.allclose(state/state[0],expected/expected[0]), 'Exercise F: cost phases must depend on the model energy.'
    np.testing.assert_allclose(np.abs(state)**2,np.ones(2**N_DECISIONS)/2**N_DECISIONS,atol=1e-12)
    mix_test=QuantumCircuit(1);add_mixer(mix_test,.3)
    assert np.isclose(Statevector.from_instruction(mix_test).probabilities()[1],np.sin(.3)**2), 'Exercise F: check your mixer.'
    P=1
    logical_circuit,logical_parameters=parameterized_qaoa(qubo,p=P)
    print('QAOA parameters:',[p.name for p in logical_parameters])
    # Desene pentru ambele circuite, înainte de antrenare.
    # Blocurile Cost grupează porțile RZ/RZZ ale Hamiltonianului pe toate firele.
    from qaoa_experiments import draw_qaoa_layers, run_depth_comparison, comparison_rows as depth_comparison_rows, plot_depth_comparison
    for depth in (1,2):
        circuit_figure=draw_qaoa_layers(qubo,p=depth)
        display(circuit_figure)
        plt.close(circuit_figure)

    # %% Notebook code cell 20
    energy_array=qubo_energies.copy()
    initial_angles=np.zeros(len(logical_parameters))
    def exact_probabilities(angles):
        bound=logical_circuit.assign_parameters(dict(zip(logical_parameters,angles)))
        return Statevector.from_instruction(bound).probabilities()
    initial_probabilities=exact_probabilities(initial_angles)
    assert np.allclose(initial_probabilities,np.ones(2**N_DECISIONS)/2**N_DECISIONS)
    print('Initial probability of each plan:',initial_probabilities[0])

    # %% Notebook code cell 21
    def expected_energy(angles):
        return float(exact_probabilities(angles) @ energy_array)

    uniform_energy=expected_energy(initial_angles)
    assert np.isclose(uniform_energy,np.mean(energy_array))
    print('Initial uniform expected energy:',uniform_energy)

    # %% Notebook code cell 22
    # Comparație controlată: aceleași date și aceleași opțiuni pentru p=1 și p=2.
    MAXITER=args.maxiter
    RESTARTS=args.restarts
    IDEAL_SHOTS=args.shots
    from datetime import datetime
    DEPTH_OUTPUT_DIR=args.output/'depth_comparison'
    print('Ambele rulări pot dura câteva minute pentru 19 qubiți.',flush=True)
    qaoa_results=run_depth_comparison(demo_routes,BUDGET,WEAK_PENALTY,depths=(1,2),
        maxiter=MAXITER,restarts=RESTARTS,shots=IDEAL_SHOTS,seed=SEED,
        output_dir=DEPTH_OUTPUT_DIR)
    # Celulele originale de hartă/backend continuă să afișeze rezultatul p=1.
    # Rezultatele p=2 și tabelul comparativ sunt afișate în secțiunea de la final.
    baseline_result=qaoa_results[P]
    best_angles=np.array(baseline_result['unghiuri_optime'])
    training_seconds=baseline_result['statistici']['timp_antrenare_secunde']
    ideal_counts=baseline_result['counts']
    measured_circuit=logical_circuit.copy()
    plan_register=ClassicalRegister(len(demo_routes),'plan')
    measured_circuit.add_register(plan_register)
    measured_circuit.measure(range(len(demo_routes)),plan_register)
    ideal_bound=measured_circuit.assign_parameters(dict(zip(logical_parameters,best_angles)))
    print('Initial expected energy:',expected_energy(initial_angles))
    print('Optimised expected energy:',baseline_result['energie_medie'])
    print('Evaluations:',baseline_result['statistici']['evaluari'],
          ' | local training seconds:',round(training_seconds,3))
    selected_run=baseline_result['optimizare']['rulari'][baseline_result['optimizare']['restart_selectat']]
    print('Optimiser success:',selected_run['succes'],'| status:',selected_run['mesaj'])
    print('Rezultatele și desenele circuitelor sunt salvate în:',DEPTH_OUTPUT_DIR.resolve())

    # %% Notebook code cell 24
    baseline_energy=lambda plan:model_energy(plan,demo_routes,BUDGET,WEAK_PENALTY)
    sampled_rows=[analyse_plan(decode_key(key,N_DECISIONS),demo_routes,BUDGET,baseline_energy) for key in ideal_counts]
    most_frequent=analyse_plan(decode_key(max(ideal_counts,key=ideal_counts.get),N_DECISIONS),demo_routes,BUDGET,baseline_energy)
    best_sample=min((r for r in sampled_rows if r['feasible']),
                    key=lambda r:(-r['score'],r['cost'],r['key']),default=None)
    show_plans([r for r in [most_frequent,best_sample,qubo_best,classical_best] if r is not None])
    ideal_metrics=distribution_metrics(ideal_counts,demo_routes,BUDGET,classical_rows)
    show_table(['Metric','Ideal finite-shot result'],[(k,round(v,5) if isinstance(v,float) else v) for k,v in ideal_metrics.items()])
    # TODO: choose one useful visual and explain what it shows.
    # plot_distribution(ideal_counts,demo_routes,BUDGET); plt.show()
    # Add an initial-versus-optimised probability plot if it helps your explanation.

    plot_distribution(ideal_counts, demo_routes, BUDGET)
    plt.show()

    if best_sample is not None:
        draw_board(best_sample['route_ids'],valid=True,title='Best valid QAOA sample',routes=demo_routes)
        plt.show()
    else:
        print('no_valid_sample: no valid recommendation was observed.')

    # %% Notebook code cell 27

    # @title Provided local backend helpers — resources and named-register decoding
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit.primitives import BackendSamplerV2

    def local_backend(num_qubits):
        return GenericBackendV2(num_qubits=max(2,num_qubits),basis_gates=['id','rz','sx','x','cx'],
            coupling_map=[[i,j] for i in range(max(2,num_qubits)) for j in range(max(2,num_qubits)) if abs(i-j)==1],seed=2026)

    def two_qubit_count(circuit):
        return sum(instruction.operation.num_qubits==2 for instruction in circuit.data)

    def isa_resources(circuit, logical_circuit):
        used=sorted({circuit.find_bit(q).index for i in circuit.data
                     if i.operation.name not in ('barrier','delay') for q in i.qubits})
        initial=[circuit.layout.initial_layout[q] for q in logical_circuit.qubits] if circuit.layout else list(range(logical_circuit.num_qubits))
        final=circuit.layout.final_index_layout(filter_ancillas=True) if circuit.layout else initial
        return dict(depth=circuit.depth(),two_qubit_gates=two_qubit_count(circuit),physical_qubits=used,
                    initial_layout=initial,final_layout=final,circuit_width=circuit.num_qubits,
                    output_swap_instructions=int(circuit.count_ops().get('swap',0)))

    def extract_plan_counts(pub_result, n_decisions=None):
        measured=getattr(pub_result.data,'plan',None)
        if measured is None: raise ValueError('Expected the named classical register plan')
        counts=measured.get_counts()
        width=measured.num_bits
        if n_decisions is not None and width!=n_decisions:raise ValueError('Measurement width differs from the decision set')
        for key in counts: decode_key(key,width)
        return dict(counts)

    # %% Notebook code cell 28
    BACKEND_SHOTS = IDEAL_SHOTS
    TRANSPILE_SEED = args.seed

    final_logical_circuit = measured_circuit.assign_parameters(
        dict(zip(logical_parameters, best_angles)))
    assert not final_logical_circuit.parameters
    RUN_NOISY=False  # Explicit opt-in; density-matrix sampling is limited to <=10 qubits.
    if RUN_NOISY and N_DECISIONS>10:
        raise ValueError('Noisy simulation limited to 10 qubits; use the ideal results for 19.')
    backend=local_backend(N_DECISIONS) if RUN_NOISY else None
    backend_kind='Local noisy/synthetic'

    # %% Notebook code cell 29
    chosen_isa=None
    chosen_resources=None
    if RUN_NOISY:
        pass_manager=generate_preset_pass_manager(
            backend=backend, optimization_level=1, seed_transpiler=TRANSPILE_SEED)
        chosen_isa=pass_manager.run(final_logical_circuit)
        chosen_resources=dict(optimization=1,seed=TRANSPILE_SEED,
            **isa_resources(chosen_isa,final_logical_circuit))
        assert not chosen_isa.parameters
        show_table(['Circuit','Depth','Two-qubit gates'],[
            ('Logical',final_logical_circuit.depth(),two_qubit_count(final_logical_circuit)),
            ('Compiled',chosen_isa.depth(),two_qubit_count(chosen_isa))])
        print('Final logical-to-physical mapping:',chosen_resources['final_layout'])
    else:
        print('Noisy compilation omitted: RUN_NOISY=False.')

    # %% Notebook code cell 30
    backend_counts=None
    real_counts=None
    if RUN_NOISY:
        local_sampler=BackendSamplerV2(backend=backend,options={'seed_simulator':SEED})
        local_job=local_sampler.run([chosen_isa],shots=BACKEND_SHOTS)
        backend_counts=extract_plan_counts(local_job.result()[0],N_DECISIONS)
        assert sum(backend_counts.values())==BACKEND_SHOTS
        # Measurements still go into plan[i], even when compilation moves qubits.
        # decode_key returns decision order x0, x1, …; it does not undo the physical layout.
        real_counts=None
        print('Local noisy samples:',sum(backend_counts.values()))
    else:
        print('Noisy sampling omitted: RUN_NOISY=False; ideal results remain available.')

    # %% Notebook code cell 32
    # @title Optional IBM connection helpers
    from getpass import getpass

    USE_REAL_HARDWARE = args.ibm  # Optional continuation below; leave False for the core.
    BACKEND_NAME = prepared_backend.name if prepared_backend is not None else "ibm_aachen"

    def modern_ibm_types():
        from railway_script_support import ibm_types
        return ibm_types()

    def choose_backend(connect=False, assigned_name='', instance='', use_saved=False, num_qubits=5):
        """IBM connection is prepared from the local configuration before training."""
        if not connect:
            return None,local_backend(num_qubits),'synthetic backend (local noisy simulation)'
        if prepared_backend is None or prepared_backend.num_qubits < num_qubits:
            raise RuntimeError('IBM backend is not connected or has insufficient qubits.')
        return prepared_service,prepared_backend,'real QPU'

    # %% Notebook code cell 33
    real_job_id=None
    if USE_REAL_HARDWARE:
        service,real_backend,_=choose_backend(True,num_qubits=N_DECISIONS)
        try:
            if args.recover_job:
                real_job=service.job(args.recover_job)
                real_job_id=args.recover_job
            else:
                hardware_logical,hardware_parameters=parameterized_qaoa(qubo,p=args.qpu_depth,measure=True)
                hardware_logical=hardware_logical.assign_parameters(dict(zip(
                    hardware_parameters,qaoa_results[args.qpu_depth]['unghiuri_optime'])))
                real_isa=generate_preset_pass_manager(backend=real_backend,optimization_level=1,
                    seed_transpiler=TRANSPILE_SEED).run(hardware_logical)
                _,Sampler=modern_ibm_types()
                real_job=Sampler(mode=real_backend).run([real_isa],shots=BACKEND_SHOTS)
                real_job_id=real_job.job_id()
            # Persist immediately, before result(): reconnect using --recover-job, without resubmitting.
            save_job_record(args.output,real_job_id,real_backend.name,args.qpu_depth,
                            BACKEND_SHOTS,recovered=bool(args.recover_job))
            print('Backend:',real_backend.name,'| Job ID:',real_job_id,flush=True)
            real_counts=extract_plan_counts(real_job.result()[0],N_DECISIONS)
            if not args.recover_job:
                assert sum(real_counts.values())==BACKEND_SHOTS
                print('Real compiled depth:',real_isa.depth(),'| Two-qubit gates:',two_qubit_count(real_isa))
            (args.output/'ibm_counts.json').write_text(json.dumps(real_counts,indent=2),encoding='utf-8')
            plot_distribution(real_counts,demo_routes,BUDGET,title=f'IBM QPU p={args.qpu_depth}')
            plt.show()
        except Exception:
            location='ibm_job.json' if real_job_id else 'conexiunea si accesul la backend'
            raise RuntimeError('Executia/citirea IBM nu s-a incheiat. Verifica '+location+
                               '; daca exista Job ID, foloseste --recover-job pentru a evita retrimiterea.') from None
    else:
        print('Real QPU execution skipped; use --ibm to execute on IBM.')

    # %% Notebook code cell 35
    comparison=[('Ideal',distribution_metrics(ideal_counts,demo_routes,BUDGET,classical_rows))]
    if backend_counts is not None:
        comparison.append((backend_kind,distribution_metrics(backend_counts,demo_routes,BUDGET,classical_rows)))
    if real_counts is not None:
        comparison.append((f'Real QPU p={args.qpu_depth}',distribution_metrics(real_counts,demo_routes,BUDGET,classical_rows)))
    comparison_headers=['Source','P(best feasible)','P(feasible)','Expected energy']
    comparison_rows=[(name,round(m['optimal_feasible_probability'],4),round(m['feasible_rate'],4),
                      round(m['expected_energy'],3)) for name,m in comparison]
    show_table(comparison_headers,comparison_rows)
    # TODO: choose one map or distribution plot that helps explain a difference.
    # plot_distribution(backend_counts,demo_routes,BUDGET); plt.show()

    # Afisam distributia rezultatelor cu zgomot
    if backend_counts is not None:
        plot_distribution(backend_counts, demo_routes, BUDGET)
        plt.show()

    # %% Notebook code cell 38
    def enumerate_plans(routes,budget,penalty):
        return PlanReference(routes,budget,penalty)

    def build_qaoa(qubo,p=1):
        return parameterized_qaoa(qubo,p=p,measure=False)

    # %% Notebook code cell 39
    # Optional second experiment: disabled to avoid another long training during Run All.
    RUN_EXTENSION=False
    if RUN_EXTENSION:
        from quantum_optimizer import optimizeaza_qaoa
        extension_result=optimizeaza_qaoa(demo_routes,BUDGET,penalizare=4.0,
            p=1,maxiter=30,restarts=1,shots=1024,seed=SEED)
        print('QAOA status:',extension_result['status'])
        print('Classical reference:',extension_result['referinta_clasica'])
        print('Best observed valid value:',extension_result['valoare_totala'])
        print('Exact ideal P(valid):',extension_result['probabilitate_valida_ideala'])
        print('Exact ideal P(any valid optimum):',extension_result['probabilitate_optim_valid_ideala'])
        if extension_result['valid']:
            draw_board(extension_result['ids_rute_recomandate'],valid=True,routes=demo_routes)
            plt.show()
    else:
        print('Additional extension training omitted: RUN_EXTENSION=False.')

    # %% Notebook code cell 43

    # @title Optional helpers — compilation comparisons and calibration
    def backend_information(backend):
        name=backend.name if isinstance(backend.name,str) else backend.name()
        coupling=backend.coupling_map
        calibration=[]
        for i,prop in enumerate((backend.target.qubit_properties or [])[:3]):
            if prop is not None:
                calibration.append(dict(qubit=i,t1_seconds=prop.t1,t2_seconds=prop.t2,
                                        frequency_hz=prop.frequency))
        return dict(name=name,num_qubits=backend.num_qubits,native_instructions=sorted(backend.operation_names),
                    coupling_edges=list(coupling.get_edges()) if coupling is not None else 'all-to-all/unspecified',
                    calibration_sample=calibration)

    def compile_variants(circuit, backend, levels, seeds):
        rows=[];circuits=[]
        standard={'id','rz','sx','x','cx','ecr','cz','rx','ry','rzz','h','s','t','u'}
        basis=[n for n in backend.operation_names if n in standard]
        for level in levels:
            for seed in seeds:
                isa=generate_preset_pass_manager(backend=backend,optimization_level=level,
                                                seed_transpiler=seed).run(circuit)
                unrestricted=transpile(circuit,basis_gates=basis,optimization_level=level,seed_transpiler=seed)
                row=dict(optimization=level,seed=seed,**isa_resources(isa,circuit))
                row['all_to_all_two_qubit_gates']=two_qubit_count(unrestricted)
                row['routing_delta']=row['two_qubit_gates']-row['all_to_all_two_qubit_gates']
                rows.append(row);circuits.append(isa)
        return rows,circuits

    # %% Notebook code cell 44
    HARDWARE_DEEP_DIVE=False
    if HARDWARE_DEEP_DIVE and backend is None:
        raise ValueError('Enable RUN_NOISY and execute the backend cells first.')
    if HARDWARE_DEEP_DIVE:
        variant_rows,variant_circuits=compile_variants(final_logical_circuit,backend,[0,1,2,3],[2026,2027])
        show_table(['Level','Seed','Depth','Two-qubit gates','Routing delta'],
            [(r['optimization'],r['seed'],r['depth'],r['two_qubit_gates'],r['routing_delta']) for r in variant_rows])
        # Optional: backend_information(backend) inspects native gates, connectivity and calibration.

    # %% Notebook code cell 46

    # @title Optional helpers — parameter ordering and job records
    from datetime import datetime, timezone
    def record_for_compilation(p,row,purpose='Baseline final-circuit comparison'):
        return dict(purpose=purpose,qaoa_depth=p,optimization=row['optimization'],transpiler_seed=row['seed'],
                    initial_layout=row['initial_layout'],final_layout=row['final_layout'],
                    compiled_depth=row['depth'],two_qubit_gates=row['two_qubit_gates'],physical_qubits=row['physical_qubits'])

    def parameter_values_for(isa, logical_parameters, angles):
        binding=dict(zip(logical_parameters,map(float,angles)))
        if len(binding)!=len(logical_parameters) or len(angles)!=len(logical_parameters):
            raise ValueError('Supply one locally optimized angle per logical parameter')
        if not set(isa.parameters).issubset(binding):
            raise ValueError('The ISA circuit contains an unrecognized parameter')
        # Use the ISA circuit's actual parameter ordering, never an assumed gamma/beta order.
        return [binding[p] for p in isa.parameters]

    def submit_and_record(backend, isa, logical_parameters, angles, record, shots=1024, allow_real=False):
        local=isinstance(backend,(AerSimulator,GenericBackendV2))
        if not local and not allow_real:
            raise RuntimeError('Real QPU submission is disabled. Confirm your experiment and enable it explicitly.')
        sampler=BackendSamplerV2(backend=backend,options={'seed_simulator':2026}) if local else modern_ibm_types()[1](mode=backend)
        values=parameter_values_for(isa,logical_parameters,angles)
        backend_name=backend.name if isinstance(backend.name,str) else backend.name()
        job=sampler.run([(isa,values)],shots=shots)
        job_id=job.job_id()
        print('Job ID:',job_id,'(record this before waiting for a result)')
        safe_record=dict(record,backend=backend_name,
            job_id=job_id,shots=shots,optimized_parameters=list(map(float,angles)),
            isa_parameter_order=[p.name for p in isa.parameters],
            execution_kind='local fake/simulator' if local else 'real QPU',
            submitted_utc=datetime.now(timezone.utc).isoformat())
        # Write the job ID immediately, BEFORE waiting for the result. No credential is recorded.
        (args.output/'railway_job_record.json').write_text(json.dumps(safe_record,indent=2))
        history=(args.output/'railway_job_records');history.mkdir(exist_ok=True)
        filename=''.join(c for c in str(job_id) if c.isalnum() or c in '-_')
        (history/(filename+'.json')).write_text(json.dumps(safe_record,indent=2))
        print('Saved job ID:',safe_record['job_id'],'('+safe_record['execution_kind']+')')
        return job,safe_record

    # %% Notebook code cell 47
    PARAMETERIZED_COMPILATION=False
    if PARAMETERIZED_COMPILATION and backend is None:
        raise ValueError('Enable RUN_NOISY and execute the backend cells first.')
    if PARAMETERIZED_COMPILATION:
        symbolic_isa=generate_preset_pass_manager(backend=backend,optimization_level=1,
            seed_transpiler=SEED).run(measured_circuit)
        ordered_angles=parameter_values_for(symbolic_isa,logical_parameters,best_angles)
        assert set(symbolic_isa.parameters).issubset(set(logical_parameters))
        # BackendSamplerV2(backend=backend).run([(symbolic_isa,ordered_angles)],shots=BACKEND_SHOTS)

    # %% Notebook code cell 49
    SAVE_RESULTS=True
    experiment_summary=dict(versions=installed_versions,penalty=WEAK_PENALTY,budget=BUDGET,
        local_training=dict(depth=P,angles=best_angles.tolist(),evaluations=baseline_result['statistici']['evaluari'],seconds=training_seconds,
                            method='exact statevector expectation'),
        ideal_counts=ideal_counts,backend_counts=backend_counts,real_counts=real_counts,
        depth_comparison=qaoa_results,compilation=chosen_resources,metrics={name:m for name,m in comparison})
    if SAVE_RESULTS:
        (args.output/'railway_results.json').write_text(json.dumps(experiment_summary,indent=2,ensure_ascii=False),encoding='utf-8')
    RECOVER_JOB_ID=""
    if RECOVER_JOB_ID:
        if not USE_REAL_HARDWARE:raise RuntimeError('Authenticate in the optional real-QPU section first.')
        recovered_job=service.job(RECOVER_JOB_ID)
        recovered_counts=extract_plan_counts(recovered_job.result()[0],N_DECISIONS)
        print('Recovered existing job:',RECOVER_JOB_ID,'; no new job submitted.')

    # %% Notebook code cell 52
    depth_rows=depth_comparison_rows(qaoa_results)
    show_table(['p','Qubiți','Unghiuri','Cost','Valoare QAOA','Optim clasic','Diferență',
                'Valide (%)','Optime măsurate (%)','P optim ideal (%)','Evaluări','Antrenare (s)','Convergență'],
        [(row['p'],N_DECISIONS,len(qaoa_results[row['p']]['unghiuri_optime']),row['cost'],
          row['value'],row['classical'],row['gap'],round(100*row['valid_rate'],3),
          round(100*row['optimal_rate'],4),round(100*row['ideal_optimal'],6),row['evaluations'],
          round(row['training_seconds'],3),
          qaoa_results[row['p']]['optimizare']['rulari'][qaoa_results[row['p']]['optimizare']['restart_selectat']]['succes'])
         for row in depth_rows])
    comparison_figure=plot_depth_comparison(qaoa_results)
    display(comparison_figure)
    plt.close(comparison_figure)
    # Hartă și distribuție pentru p=2; p=1 este afișat în secțiunea originală.
    p2_result=qaoa_results[2]
    if p2_result['valid']:
        draw_board(p2_result['ids_rute_recomandate'],valid=True,routes=demo_routes,
            title=f"QAOA p=2: valoare {p2_result['valoare_totala']}, cost {p2_result['cost_total']}/{BUDGET}")
        plt.show()
    else:
        print('p=2: no_valid_sample — nicio recomandare validă măsurată.')
    plot_distribution(p2_result['counts'],demo_routes,BUDGET,title='Distribuție măsurată QAOA p=2')
    plt.show()

    print('Rezultate salvate in:', args.output)


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from None
