"""Compact exact references for the railway notebook (no per-state dict table)."""
from copy import deepcopy

import numpy as np

from quantum_optimizer import MAX_QUBITS, analyse_plan, classical_reference, construct_qubo, decode_key


class PlanReference:
    def __init__(self, routes, budget, penalty):
        if len(routes) > MAX_QUBITS:
            raise ValueError(f"Exact reference limited to {MAX_QUBITS} routes")
        construct_qubo(routes, budget, penalty)  # use the production input validation
        self.routes, self.budget, self.penalty = deepcopy(routes), int(budget), float(penalty)
        self.n = len(routes)
        self.costs = np.zeros(1 << self.n, dtype=np.int64)
        self.values = np.zeros(1 << self.n, dtype=np.int64)
        for i, route in enumerate(routes):
            k = 1 << i
            self.costs[k:2*k] = self.costs[:k] + route['cost']
            self.values[k:2*k] = self.values[:k] + route['value']
        self.feasible = self.costs <= budget
        self.energies = -self.values.astype(float) + penalty * (self.costs.astype(float)-budget)**2
        self.classical = classical_reference(routes, budget)
        self.optimal_value = self.classical['valoare_optima']

    def __len__(self):
        return len(self.energies)

    def __getitem__(self, index):
        if not isinstance(index, (int, np.integer)) or not 0 <= index < len(self):
            raise IndexError(index)
        key = format(int(index), f'0{self.n}b')
        plan = analyse_plan(decode_key(key, self.n), self.routes, self.budget, self.penalty)
        return dict(bits=plan['bits'], key=key, route_ids=plan['ids_rute'],
                    cost=plan['cost_total'], score=plan['valoare_totala'],
                    feasible=plan['valid'], energy=plan['energie'])

    def minimum_plan(self):
        return self[int(np.argmin(self.energies))]

    def best_valid_plan(self):
        return self[int(self.classical['bitstring'], 2)]

    def metrics(self, counts, routes, budget):
        if routes != self.routes or budget != self.budget:
            raise ValueError('Reference does not match routes/budget; recompute it')
        indices, frequencies = [], []
        for key, count in counts.items():
            decode_key(key, self.n)
            if isinstance(count, bool) or not isinstance(count, (int, np.integer)) or count < 0:
                raise ValueError('Expected nonnegative integer counts')
            if count:
                indices.append(int(key.replace(' ', ''), 2))
                frequencies.append(int(count))
        total = sum(frequencies)
        if total <= 0:
            raise ValueError('At least one shot is required')
        indices = np.array(indices, dtype=np.int64)
        weights = np.array(frequencies, dtype=float)/total
        valid = self.feasible[indices]
        return dict(shots=total, feasible_rate=float(weights[valid].sum()),
                    over_budget_rate=float(weights[~valid].sum()),
                    model_minimum_probability=float(weights[np.isclose(self.energies[indices], self.energies.min())].sum()),
                    optimal_feasible_probability=float(weights[valid & (self.values[indices] == self.optimal_value)].sum()),
                    mean_true_score=float(weights @ self.values[indices]),
                    expected_energy=float(weights @ self.energies[indices]),
                    best_feasible_score=int(self.values[indices][valid].max()) if valid.any() else None)


def coefficient_energies(linear, pairs, constant, *, spin=False):
    """Evaluate a polynomial on every basis state, using bounded temporary blocks."""
    linear, pairs = np.asarray(linear, float), np.asarray(pairs, float)
    n = len(linear)
    if not 1 <= n <= MAX_QUBITS or pairs.shape != (n, n):
        raise ValueError('Invalid polynomial dimensions')
    energies = np.empty(1 << n)
    for start in range(0, len(energies), 4096):
        end = min(start+4096, len(energies))
        indices = np.arange(start, end, dtype=np.uint64)
        x = ((indices[:, None] >> np.arange(n, dtype=np.uint64)) & 1).astype(float)
        if spin:
            x = 1-2*x
        energies[start:end] = constant + x @ linear + np.einsum('bi,ij,bj->b', x, pairs, x)
    return energies
