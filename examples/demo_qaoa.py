"""Run from any working directory; extended QAOA is explicitly opt-in."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quantum_optimizer import classical_reference, optimizeaza_qaoa


from copy import deepcopy
from railway_catalog import ROUTES, demo_routes

DEMO_ROUTES = deepcopy(demo_routes)


def extended_routes():
    return deepcopy(ROUTES)

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
