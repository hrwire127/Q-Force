"""Run from any working directory; extended QAOA is explicitly opt-in."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quantum_optimizer import classical_reference, optimizeaza_qaoa


DEMO_ROUTES = [
    {'id': 0, 'cities': ('Iași', 'Brașov'), 'cost': 2, 'value': 4},
    {'id': 1, 'cities': ('Iași', 'Cluj-Napoca'), 'cost': 3, 'value': 6},
    {'id': 2, 'cities': ('Cluj-Napoca', 'Brașov'), 'cost': 2, 'value': 5},
    {'id': 6, 'cities': ('Brașov', 'București'), 'cost': 4, 'value': 9},
    {'id': 8, 'cities': ('București', 'Constanța'), 'cost': 4, 'value': 7},
]


def extended_routes():
    """Team notebook cell 4 data; border charges added exactly once here."""
    domestic = [
        ('Iași', 'Brașov', 2, 4), ('Iași', 'Cluj-Napoca', 3, 6),
        ('Cluj-Napoca', 'Brașov', 2, 5), ('Timișoara', 'Cluj-Napoca', 4, 7),
        ('Timișoara', 'Sibiu', 3, 6), ('Sibiu', 'Brașov', 2, 4),
        ('Brașov', 'București', 4, 9), ('Sibiu', 'Craiova', 2, 4),
        ('București', 'Constanța', 4, 7), ('Craiova', 'București', 2, 5),
        ('Cluj-Napoca', 'Sibiu', 2, 4), ('Iași', 'Constanța', 6, 11),
        ('Satu Mare', 'Cluj-Napoca', 3, 6),
    ]
    international = [
        ('Timișoara', 'Budapesta', 4, 8, 1), ('București', 'Sofia', 4, 7, 1),
        ('Timișoara', 'Belgrad', 3, 9, 1), ('Iași', 'Chișinău', 3, 10, 1),
        ('Iași', 'Cernăuți', 4, 11, 1), ('Satu Mare', 'Budapesta', 4, 8, 1),
    ]
    routes = [dict(id=i, cities=(u, v), cost=c, value=value,
                   border_cost=0, international=False)
              for i, (u, v, c, value) in enumerate(domestic)]
    for u, v, c, value, border in international:
        routes.append(dict(id=len(routes), cities=(u, v), cost=c+border,
                           value=value, border_cost=border, international=True))
    return routes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extended', action='store_true', help='19-qubit benchmark (expensive)')
    parser.add_argument('--classical-only', action='store_true')
    parser.add_argument('--noisy', action='store_true', help='final noisy sampling, <=10 qubits')
    parser.add_argument('--budget', type=int)
    parser.add_argument('--penalty', type=float, default=0.7)
    parser.add_argument('--p', type=int, default=1)
    parser.add_argument('--shots', type=int, default=1024)
    parser.add_argument('--maxiter', type=int, default=30)
    parser.add_argument('--restarts', type=int, default=1)
    parser.add_argument('--seed', type=int, default=2026)
    parser.add_argument('--output', type=Path, help='save complete JSON evidence')
    args = parser.parse_args()
    routes = extended_routes() if args.extended else DEMO_ROUTES
    budget = args.budget if args.budget is not None else (20 if args.extended else 7)
    if args.classical_only:
        result = {'referinta_clasica': classical_reference(routes, budget)}
    else:
        result = optimizeaza_qaoa(
            routes, budget, args.penalty, p=args.p, shots=args.shots,
            maxiter=args.maxiter, restarts=args.restarts, seed=args.seed,
            backend_mode='noisy' if args.noisy else 'ideal')
    encoded = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
    if args.output:
        args.output.write_text(encoded + '\n', encoding='utf-8')
    print(encoded)


if __name__ == '__main__':
    main()
