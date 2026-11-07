"""Run the same QAOA optimizer at p=1 and p=2, with circuit illustrations."""
import argparse
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from examples.demo_qaoa import DEMO_ROUTES, extended_routes
from qaoa_experiments import comparison_rows, run_depth_comparison


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--small',action='store_true',help='Use the 5-route scenario')
    parser.add_argument('--budget',type=int)
    parser.add_argument('--penalty',type=float,default=.7)
    parser.add_argument('--maxiter',type=int,default=30)
    parser.add_argument('--restarts',type=int,default=1)
    parser.add_argument('--shots',type=int,default=4096)
    parser.add_argument('--seed',type=int,default=2026)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    output=args.output or Path('output/qaoa_depths')/datetime.now().strftime('%Y%m%d_%H%M%S')
    routes=DEMO_ROUTES if args.small else extended_routes()
    budget=args.budget if args.budget is not None else (7 if args.small else 20)
    results=run_depth_comparison(routes,budget,args.penalty,maxiter=args.maxiter,restarts=args.restarts,
                                  shots=args.shots,seed=args.seed,output_dir=output)
    for row in comparison_rows(results): print(row)
    print('Results and circuit diagrams:',output.resolve())


if __name__=='__main__': main()
