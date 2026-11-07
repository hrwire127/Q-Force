"""Real QAOA for additive railway value with the lab's squared budget penalty.

Decision i always denotes input route i. Public results contain JSON primitives.
The squared equality penalty is NOT an exact encoding of cost <= budget.
"""

from collections.abc import Mapping, Sequence
from numbers import Integral, Real
from time import perf_counter
import warnings

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, transpile
from qiskit.circuit import ParameterVector
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator
from scipy.optimize import minimize


# Explicit resource policy: no arbitrary exponential allocations or circuits.
MAX_QUBITS = 20
MAX_NOISY_QUBITS = 10
MAX_DEPTH = 100
MAX_TWO_QUBIT_GATES = 20_000
MAX_INTEGER_TOTAL = 2**50  # exact integer sums in float64; safe int64 vectors


def _integer(value, name, minimum=0):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral):
        raise ValueError(f"{name} must be an integer >= {minimum}")
    value = int(value)
    if value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _penalty(value):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError("penalizare must be a positive finite number")
    try:
        value = float(value)
    except OverflowError:
        raise ValueError("penalizare must be finite") from None
    if not np.isfinite(value) or value <= 0:
        raise ValueError("penalizare must be a positive finite number")
    return value


def _routes(rute):
    if not isinstance(rute, Sequence) or isinstance(rute, (str, bytes)) or not rute:
        raise ValueError("rute must be a nonempty sequence of route mappings")
    result, ids = [], set()
    for i, route in enumerate(rute):
        if not isinstance(route, Mapping):
            raise ValueError(f"rute[{i}] must be a mapping")
        missing = {'id', 'cities', 'cost', 'value'} - route.keys()
        if missing:
            raise ValueError(f"rute[{i}] missing fields: {sorted(missing)}")
        rid = route['id']
        if isinstance(rid, (bool, np.bool_)) or not isinstance(rid, (str, Integral)):
            raise ValueError("route id must be an integer or nonempty string")
        rid = int(rid) if isinstance(rid, Integral) else rid
        if rid == '' or rid in ids:
            raise ValueError(f"empty or duplicate route id: {rid!r}")
        ids.add(rid)
        cities = route['cities']
        if (not isinstance(cities, (list, tuple)) or len(cities) != 2
                or any(not isinstance(c, str) or not c.strip() for c in cities)):
            raise ValueError("cities must contain two nonempty city names")
        cost = _integer(route['cost'], 'cost')
        value = _integer(route['value'], 'value')
        border = _integer(route.get('border_cost', 0), 'border_cost')
        if border > cost:
            raise ValueError("border_cost must be part of total cost, not exceed it")
        international = route.get('international', False)
        if not isinstance(international, (bool, np.bool_)):
            raise ValueError("international must be boolean")
        result.append(dict(id=rid, cities=list(cities), cost=cost, value=value,
                           border_cost=border, international=bool(international)))
    if max(sum(r['cost'] for r in result), sum(r['value'] for r in result)) > MAX_INTEGER_TOTAL:
        raise ValueError("route totals exceed the supported numeric range (2**50)")
    return result


def _problem(rute, buget, penalizare):
    routes = _routes(rute)
    budget = _integer(buget, 'buget')
    penalty = _penalty(penalizare)
    if budget > MAX_INTEGER_TOTAL:
        raise ValueError("buget exceeds the supported numeric range (2**50)")
    # Bound all energies and coefficient summations, rejecting overflow early.
    extent = max(budget, sum(r['cost'] for r in routes))
    if not np.isfinite(penalty * float(4 * extent**2 + 1)):
        raise ValueError("penalizare and costs exceed finite float64 energy range")
    return routes, budget, penalty


def _bits(bits, n):
    x = np.asarray(bits)
    if x.shape != (n,) or not np.all((x == 0) | (x == 1)):
        raise ValueError("one binary decision is required per route")
    return x.astype(np.int64)


def decode_key(key, n):
    """Decode Qiskit key (rightmost bit is decision 0), allowing register spaces."""
    n = _integer(n, 'n', 1)
    if not isinstance(key, str):
        raise ValueError("measurement key must be a binary string")
    key = key.replace(' ', '')
    if len(key) != n or set(key) - {'0', '1'}:
        raise ValueError("measurement key must contain exactly n binary bits")
    return [int(c) for c in reversed(key)]


def analyse_plan(bits, rute, buget, penalizare=4.0):
    routes, budget, penalty = _problem(rute, buget, penalizare)
    x = _bits(bits, len(routes))
    selected = [r for bit, r in zip(x, routes) if bit]
    cost = sum(r['cost'] for r in selected)
    value = sum(r['value'] for r in selected)
    return dict(bitstring=''.join(str(int(b)) for b in x[::-1]),
                bits=x.tolist(), ids_rute=[r['id'] for r in selected],
                rute=selected, cost_total=cost, valoare_totala=value,
                valid=cost <= budget, energie=float(-value + penalty * (cost-budget)**2))


def model_energy(bits, rute, buget, penalizare):
    return analyse_plan(bits, rute, buget, penalizare)['energie']


def construct_qubo(rute, buget, penalizare):
    """Upper triangular pairs are stored once, with the constant kept separate."""
    routes, budget, penalty = _problem(rute, buget, penalizare)
    c = np.array([r['cost'] for r in routes], dtype=float)
    v = np.array([r['value'] for r in routes], dtype=float)
    return dict(linear=-v + penalty * (c**2 - 2 * budget * c),
                quadratic=np.triu(2 * penalty * np.outer(c, c), 1),
                offset=float(penalty * budget**2))


def _coefficients(model, linear_name, pair_name, constant_name):
    if not isinstance(model, Mapping):
        raise ValueError("coefficient model must be a mapping")
    try:
        a = np.asarray(model[linear_name], dtype=float)
        b = np.asarray(model[pair_name], dtype=float)
        constant = float(model[constant_name])
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise ValueError("invalid coefficient model") from exc
    if (a.ndim != 1 or not a.size or b.shape != (a.size, a.size)
            or not np.all(np.isfinite(a)) or not np.all(np.isfinite(b))
            or not np.isfinite(constant) or np.any(np.tril(b) != 0)):
        raise ValueError("finite coefficients and strictly upper triangular pairs required")
    return a, b, constant


def qubo_energy(bits, qubo):
    a, b, constant = _coefficients(qubo, 'linear', 'quadratic', 'offset')
    x = _bits(bits, len(a))
    return float(constant + a @ x + x @ b @ x)


def qubo_to_ising(qubo):
    a, b, offset = _coefficients(qubo, 'linear', 'quadratic', 'offset')
    with np.errstate(over='ignore', invalid='ignore'):
        result = dict(h=-a/2 - (b.sum(axis=0) + b.sum(axis=1))/4,
                      J=b/4, constant=float(offset + a.sum()/2 + b.sum()/4))
    _coefficients(result, 'h', 'J', 'constant')
    return result


def ising_energy(bits, ising):
    h, j, constant = _coefficients(ising, 'h', 'J', 'constant')
    z = 1 - 2 * _bits(bits, len(h))
    return float(constant + h @ z + z @ j @ z)


def add_cost(qc, gamma, ising):
    h, j, _ = _coefficients(ising, 'h', 'J', 'constant')
    if qc.num_qubits != len(h):
        raise ValueError("circuit width must match the Hamiltonian")
    scale = max(1.0, float(np.max(np.abs(h))), float(np.max(np.abs(j))))
    for i, coefficient in enumerate(h):
        qc.rz(2 * gamma * float(coefficient / scale), i)
    for i, k in zip(*np.nonzero(j)):
        qc.rzz(2 * gamma * float(j[i, k] / scale), int(i), int(k))
    return qc


def add_mixer(qc, beta):
    for i in range(qc.num_qubits):
        qc.rx(2 * beta, i)
    return qc


def parameterized_qaoa(qubo, p=1, measure=False):
    """Return (circuit, parameters), ordered gamma0,beta0,gamma1,beta1,..."""
    p = _integer(p, 'p', 1)
    if not isinstance(measure, bool):
        raise ValueError("measure must be boolean")
    ising = qubo_to_ising(qubo)
    n = len(ising['h'])
    if n > MAX_QUBITS or p > MAX_DEPTH or p * np.count_nonzero(ising['J']) > MAX_TWO_QUBIT_GATES:
        raise ValueError(f"resource limit: <= {MAX_QUBITS} qubits, p <= {MAX_DEPTH}, "
                         f"<= {MAX_TWO_QUBIT_GATES} RZZ gates")
    parameters = ParameterVector('theta', 2*p)
    qc = QuantumCircuit(n)
    qc.h(range(n))
    for layer in range(p):
        add_cost(qc, parameters[2*layer], ising)
        add_mixer(qc, parameters[2*layer+1])
    if measure:
        _add_measurements(qc)
    return qc, list(parameters)


def _add_measurements(qc):
    plan = ClassicalRegister(qc.num_qubits, 'plan')
    qc.add_register(plan)
    qc.measure(range(qc.num_qubits), plan)


def classical_reference(rute, buget):
    """Exact sparse 0/1 knapsack DP; remove states dominated in cost/value.

    Equal values prefer lower cost, then lexicographically smaller Qiskit key.
    Zero-cost routes are processed only once by copying the preceding frontier.
    """
    routes, budget, _ = _problem(rute, buget, 1.0)
    frontier = {0: (0, 0)}  # cost -> (value, decision mask)
    for i, route in enumerate(routes):
        following = dict(frontier)
        for cost, (value, mask) in frontier.items():
            new_cost = cost + route['cost']
            if new_cost > budget:
                continue
            candidate = (value + route['value'], mask | (1 << i))
            current = following.get(new_cost)
            if current is None or (-candidate[0], candidate[1]) < (-current[0], current[1]):
                following[new_cost] = candidate
        frontier, highest = {}, -1
        for cost in sorted(following):
            if following[cost][0] > highest:
                frontier[cost] = following[cost]
                highest = following[cost][0]
    cost, (value, mask) = min(frontier.items(), key=lambda kv: (-kv[1][0], kv[0], kv[1][1]))
    return dict(valoare_optima=value, cost_total=cost,
                ids_rute=[r['id'] for i, r in enumerate(routes) if mask & (1 << i)],
                bitstring=format(mask, f'0{len(routes)}b'))


def _basis_totals(routes):
    """O(2**n) memory, never construct an array of per-state dictionaries."""
    size = 1 << len(routes)
    indices = np.arange(size, dtype=np.uint64)
    costs = np.zeros(size, dtype=np.int64)
    values = np.zeros(size, dtype=np.int64)
    for i, route in enumerate(routes):
        bit = ((indices >> i) & 1).astype(np.int64)
        costs += route['cost'] * bit
        values += route['value'] * bit
    return costs, values


def _sample_counts(bound, shots, seed, mode):
    measured = bound.copy()
    _add_measurements(measured)
    if mode == 'noisy':
        from qiskit.providers.fake_provider import GenericBackendV2
        width = max(2, bound.num_qubits)
        backend = GenericBackendV2(
            num_qubits=width, basis_gates=['id', 'rz', 'sx', 'x', 'cx'],
            coupling_map=[[i, j] for i in range(width) for j in range(width) if abs(i-j) == 1],
            seed=seed, noise_info=True)
        compiled = transpile(measured, backend, optimization_level=1, seed_transpiler=seed)
        simulator = AerSimulator.from_backend(backend, method='density_matrix', max_parallel_threads=1)
    else:
        simulator = AerSimulator(method='statevector', max_parallel_threads=1)
        compiled = transpile(measured, simulator, optimization_level=1, seed_transpiler=seed)
    result = simulator.run(compiled, shots=shots, seed_simulator=seed).result()
    # transpile preserves classical plan[i] even when moving logical qubits.
    counts = {str(k): int(v) for k, v in result.get_counts().items()}
    resources = dict(adancime_circuit=int(compiled.depth()),
                     porti_doi_qubiti=sum(inst.operation.num_qubits == 2 for inst in compiled.data),
                     registru_masurare='plan')
    if compiled.layout is not None:
        resources['mapare_finala'] = [int(i) for i in compiled.layout.final_index_layout(filter_ancillas=True)]
    return counts, resources


def _summarize_counts(counts, routes, budget, penalty, optimal_value, shots):
    canonical = {}
    for key, count in counts.items():
        bits = decode_key(key, len(routes))
        count = _integer(count, 'measurement count')
        if count:
            key = ''.join(map(str, bits[::-1]))
            canonical[key] = canonical.get(key, 0) + count
    if sum(canonical.values()) != shots:
        raise ValueError("measurement counts must sum to shots")
    rows = []
    for key, count in canonical.items():
        row = analyse_plan(decode_key(key, len(routes)), routes, budget, penalty)
        row.update(frecventa=count, probabilitate=count/shots)
        rows.append(row)
    rows.sort(key=lambda r: (-r['frecventa'], r['bitstring']))
    valid = [r for r in rows if r['valid']]
    best = min(valid, key=lambda r: (-r['valoare_totala'], r['cost_total'], r['bitstring']), default=None)
    return dict(best=best, most_frequent=rows[0], top=rows[:20], counts=canonical,
                valid_rate=sum(r['frecventa'] for r in valid)/shots,
                optimal_rate=sum(r['frecventa'] for r in valid if r['valoare_totala'] == optimal_value)/shots,
                sampled_energy=float(sum(r['energie'] * r['probabilitate'] for r in rows)))


def optimizeaza_qaoa(rute, buget, penalizare=4.0, *, p=1, shots=1024,
                    maxiter=30, seed=2026, restarts=1, backend_mode='ideal') -> dict:
    """Train exact ideal expectation via COBYLA, then sample a real Qiskit circuit.

    Recommendation is the highest-value VALID OBSERVED plan. No classical fallback.
    Noisy mode changes final sampling only; training always remains ideal.
    """
    started = perf_counter()
    routes, budget, penalty = _problem(rute, buget, penalizare)
    p = _integer(p, 'p', 1)
    shots = _integer(shots, 'shots', 1)
    maxiter = _integer(maxiter, 'maxiter', 1)
    restarts = _integer(restarts, 'restarts', 1)
    seed = _integer(seed, 'seed')
    if seed > 2**32 - 1:
        raise ValueError("seed must be <= 2**32 - 1")
    if backend_mode not in ('ideal', 'noisy'):
        raise ValueError("backend_mode must be 'ideal' or 'noisy'")
    n = len(routes)
    if n > MAX_QUBITS:
        raise ValueError(f"statevector resource limit: at most {MAX_QUBITS} routes")
    if backend_mode == 'noisy' and n > MAX_NOISY_QUBITS:
        raise ValueError(f"noisy density-matrix limit: {MAX_NOISY_QUBITS} qubits; use ideal")
    if n >= 19 or backend_mode == 'noisy':
        warnings.warn("Exponential local simulation cost; noisy mode samples only the final circuit.",
                      RuntimeWarning, stacklevel=2)
    qubo = construct_qubo(routes, budget, penalty)
    circuit, parameters = parameterized_qaoa(qubo, p=p)
    costs, values = _basis_totals(routes)
    energies = -values.astype(float) + penalty * (costs.astype(float)-budget)**2
    reference = classical_reference(routes, budget)
    rng = np.random.default_rng(seed)
    runs, evaluations = [], 0
    history = []
    best_energy, best_angles, best_run = float('inf'), None, None
    training_started = perf_counter()
    for restart in range(restarts):
        initial_angles = rng.uniform(0, [2*np.pi, np.pi] * p)
        run_energy, run_angles, run_evaluations = float('inf'), None, 0

        def objective(angles):
            nonlocal evaluations, run_energy, run_angles, run_evaluations
            bound = circuit.assign_parameters(dict(zip(parameters, map(float, angles))))
            probabilities = Statevector.from_instruction(bound).probabilities()
            energy = float(probabilities @ energies)
            if not np.isfinite(energy):
                raise ValueError("nonfinite energy during optimization")
            evaluations += 1
            run_evaluations += 1
            history.append(dict(restart=restart, evaluation=evaluations, energy=energy))
            if energy < run_energy:
                run_energy, run_angles = energy, np.array(angles, dtype=float, copy=True)
            return energy

        run_started = perf_counter()
        initial_energy = objective(initial_angles)
        result = minimize(objective, initial_angles, method='COBYLA', options={'maxiter': maxiter})
        runs.append(dict(restart=restart, energie_initiala=initial_energy,
                         energie_finala=run_energy, unghiuri_initiale=initial_angles.tolist(),
                         unghiuri_optime=run_angles.tolist(), evaluari=run_evaluations,
                         evaluari_scipy=int(result.nfev), status=int(result.status),
                         succes=bool(result.success), mesaj=str(result.message),
                         timp_secunde=float(perf_counter()-run_started)))
        if run_energy < best_energy:
            best_energy, best_angles, best_run = run_energy, run_angles.copy(), restart
    training_seconds = perf_counter()-training_started
    bound = circuit.assign_parameters(dict(zip(parameters, map(float, best_angles))))
    probabilities = Statevector.from_instruction(bound).probabilities()
    sampling_started = perf_counter()
    counts, resources = _sample_counts(bound, shots, seed, backend_mode)
    sampling_seconds = perf_counter()-sampling_started
    summary = _summarize_counts(counts, routes, budget, penalty, reference['valoare_optima'], shots)
    best = summary['best']
    feasible = costs <= budget
    optimum = feasible & (values == reference['valoare_optima'])
    return dict(
        status='ok' if best is not None else 'no_valid_sample',
        rute_recomandate=best['rute'] if best else [],
        ids_rute_recomandate=best['ids_rute'] if best else [],
        bitstring_recomandat=best['bitstring'] if best else None,
        cost_total=best['cost_total'] if best else None,
        valoare_totala=best['valoare_totala'] if best else None,
        buget=budget, buget_ramas=budget-best['cost_total'] if best else None,
        valid=best is not None, penalizare=penalty,
        probabilitate_plan_recomandat=best['probabilitate'] if best else 0.0,
        rata_planuri_valide=summary['valid_rate'],
        probabilitate_optim_valid=summary['optimal_rate'],
        energie_medie=float(probabilities @ energies),
        energie_medie_masurata=summary['sampled_energy'],
        energie_medie_initiala=runs[best_run]['energie_initiala'],
        probabilitate_valida_ideala=float(probabilities[feasible].sum()),
        probabilitate_optim_valid_ideala=float(probabilities[optimum].sum()),
        unghiuri_optime=best_angles.tolist(),
        gamma=best_angles[::2].tolist(), beta=best_angles[1::2].tolist(),
        referinta_clasica=reference,
        diferenta_valoare=reference['valoare_optima']-best['valoare_totala'] if best else None,
        cel_mai_frecvent_plan=summary['most_frequent'], top_planuri=summary['top'],
        counts=summary['counts'],
        optimizare=dict(metoda='COBYLA', restart_selectat=best_run, rulari=runs, history=history),
        statistici=dict(numar_qubiti=n, qaoa_depth=p, shots=shots, maxiter=maxiter,
                        restarts=restarts, evaluari=evaluations,
                        timp_antrenare_secunde=float(training_seconds),
                        timp_masurare_secunde=float(sampling_seconds),
                        timp_total_secunde=float(perf_counter()-started), seed=seed,
                        backend=backend_mode, antrenare='ideal_statevector',
                        simulare_zgomot='executata' if backend_mode == 'noisy' else 'omisa_mod_ideal',
                        **resources))
