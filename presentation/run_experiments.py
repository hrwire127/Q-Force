"""Reproduce the local presentation evidence without changing the application.

Run from the repository root with the environment in README.md. Writes full
immutable-style JSON snapshots and a compact index used by build_presentation.mjs.
No IBM service or credential is accessed by this script.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import itertools
import json
from math import sqrt
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from railway_data import ROUTES, DEMO_IDS  # noqa: E402
from railway_catalog import ROUTES as CATALOG  # noqa: E402
from experiment import run_experiment, references, summarize  # noqa: E402
from quantum_optimizer import (  # noqa: E402
    construct_qubo, qubo_to_ising, model_energy, qubo_energy, ising_energy,
    parameterized_qaoa, _sample_counts,
)

OUT = ROOT / "presentation"
RUNS = OUT / "experiments"
SOURCES = OUT / "source_data"


def save(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def wilson(successes: int, total: int, z: float = 1.96) -> list[float]:
    if total == 0:
        return [0.0, 1.0]
    p = successes / total
    den = 1 + z*z/total
    mid = (p + z*z/(2*total)) / den
    half = z*sqrt(p*(1-p)/total + z*z/(4*total*total))/den
    return [max(0.0, mid-half), min(1.0, mid+half)]


def concise(result: dict, name: str, provenance: str = "executed_local") -> dict:
    cfg = result["config"]
    rows = {}
    for backend, sample in result["samples"].items():
        counts = result["counts_by_backend"][backend]
        shots = sum(counts.values())
        feasible_n = sum(x["count"] for x in sample["distribution"] if x["valid"])
        optimal_n = sum(x["count"] for x in sample["distribution"]
                        if x["valid"] and x["valoare_totala"] == result["classical"]["valoare_totala"])
        rows[backend] = {
            "shots": shots,
            "p_feasible": sample["p_feasible"],
            "p_feasible_wilson95": wilson(feasible_n, shots),
            "p_optimal_feasible": sample["p_optimal_feasible"],
            "p_optimal_feasible_wilson95": wilson(optimal_n, shots),
            "p_model_minimum": sample["p_model_minimum"],
            "over_budget_rate": sample["over_budget_rate"],
            "mean_true_score_including_invalid": sample["mean_true_score"],
            "sampled_expected_model_energy": sample["expected_energy"],
            "best_feasible": sample["best_feasible"],
            "most_frequent": sample["most_frequent"],
            "resources": result["resources"][backend],
        }
    q = result["quantum"]
    return {
        "name": name, "provenance": provenance,
        "experiment_id": result["experiment_id"], "created_utc": result["created_utc"],
        "route_ids": [r["id"] for r in result["routes"]],
        "cities": sorted({city for route in result["routes"] for city in route["cities"]}),
        "num_routes": len(result["routes"]),
        "num_cities": len({city for route in result["routes"] for city in route["cities"]}),
        "state_count": result["plan_count"], "feasible_plan_count": result["feasible_plan_count"],
        "config": cfg, "classical": result["classical"],
        "classical_optima": result["classical_optima"],
        "qubo_minimum": result["qubo_minimum"],
        "qubo_minima": result["qubo_minima"],
        "initial_expected_energy": q.get("energie_medie_initiala"),
        "final_expected_energy": q.get("energie_medie"),
        "gamma": q.get("gamma"), "beta": q.get("beta"),
        "optimizer_runs": q["optimizare"].get("rulari", []),
        "exact_ideal_statistics": result["exact_ideal_statistics"],
        "samples": rows, "runtime_seconds": result["runtime_seconds"],
        "versions": result["versions"],
    }


def run(name: str, routes: list[dict], **config: object) -> dict:
    path = RUNS / f"{name}.json"
    result = run_experiment(routes, **config)
    save(path, result)
    row = concise(result, name)
    print(name, "routes", row["num_routes"], "cities", row["num_cities"],
          "budget", row["config"]["budget"], "penalty", row["config"]["penalty"],
          "ideal P(feasible)", round(row["samples"]["ideal"]["p_feasible"], 6), flush=True)
    return row


def main() -> None:
    RUNS.mkdir(parents=True, exist_ok=True)
    baseline = [r for r in ROUTES if r["id"] in DEMO_IDS]
    assert [r["id"] for r in baseline] == [0, 1, 2, 6, 8]

    # Verify the mathematical model against every official baseline decision.
    qubo = construct_qubo(baseline, 7, .7)
    ising = qubo_to_ising(qubo)
    errors = []
    for bits in itertools.product((0, 1), repeat=5):
        direct = model_energy(bits, baseline, 7, .7)
        qenergy = qubo_energy(bits, qubo)
        ienergy = ising_energy(bits, ising)
        errors.append([abs(direct-qenergy), abs(qenergy-ienergy)])
    assert len(errors) == 32 and max(max(x) for x in errors) < 1e-9

    rows: list[dict] = []
    for penalty in (.7, 4.0):
        for seed in (2026, 2027, 2028):
            rows.append(run(f"penalty_{str(penalty).replace('.', '_')}_seed_{seed}", baseline,
                            budget=7, penalty=penalty, p=1, shots=2048, seed=seed,
                            maxiter=30, restarts=1, mode="compare"))

    # Additional budgets: same route set and solver settings, fresh reference and training.
    for budget in (5, 9):
        rows.append(run(f"budget_{budget}_seed_2026", baseline,
                        budget=budget, penalty=.7, p=1, shots=2048, seed=2026,
                        maxiter=30, restarts=1, mode="compare"))

    # Size changes only the available route decisions; budget stays 7.
    catalogue = {r["id"]: r for r in CATALOG}
    for ids in ([0, 1, 2, 6, 8, 9, 10], [0, 1, 2, 6, 8, 9, 10, 11]):
        routes = [catalogue[i] for i in ids]
        rows.append(run(f"size_{len(ids)}_seed_2026", routes,
                        budget=7, penalty=.7, p=1, shots=2048, seed=2026,
                        maxiter=30, restarts=1, mode="compare"))

    # Same trained angles as the seed-2026 weak-penalty baseline, never retrained.
    source = json.loads((RUNS / "penalty_0_7_seed_2026.json").read_text(encoding="utf-8"))
    qaoa = source["quantum"]
    q, params = parameterized_qaoa(construct_qubo(baseline, 7, .7), p=1)
    bound = q.assign_parameters(dict(zip(params, qaoa["unghiuri_optime"])))
    plans, _, _ = references(baseline, 7, .7)
    shots_rows = []
    for shots in (256, 1024, 2048, 4096):
        for seed in (2026, 2027, 2028):
            counts, resources = _sample_counts(bound, shots, seed, "ideal", optimization_level=1)
            stats = summarize(counts, plans)
            feasible_n = sum(x["count"] for x in stats["distribution"] if x["valid"])
            optimal_n = sum(x["count"] for x in stats["distribution"]
                            if x["valid"] and x["valoare_totala"] == 15)
            item = {"shots": shots, "sampling_seed": seed, "training_seed": 2026,
                    "training_result": "penalty_0_7_seed_2026.json",
                    "gamma": qaoa["gamma"], "beta": qaoa["beta"],
                    "counts": counts, "p_feasible": stats["p_feasible"],
                    "p_feasible_wilson95": wilson(feasible_n, shots),
                    "p_optimal_feasible": stats["p_optimal_feasible"],
                    "p_optimal_feasible_wilson95": wilson(optimal_n, shots),
                    "p_model_minimum": stats["p_model_minimum"],
                    "best_feasible": stats["best_feasible"],
                    "resources": resources}
            shots_rows.append(item)
    save(SOURCES / "shot_sensitivity.json", shots_rows)

    # Archived depth evidence is kept separate from newly executed experiments.
    depth_path = ROOT / "validation" / "p_comparison_seed2026" / "comparison.json"
    archived_depth = json.loads(depth_path.read_text(encoding="utf-8"))
    index = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": "Q-Force presentation local replay",
        "source_branch": "zus", "source_commit": "728ce48302ef094f9f5e69633bd3ba843356de4e",
        "energy_equivalence": {"states": 32,
                               "max_direct_qubo_abs_error": max(x[0] for x in errors),
                               "max_qubo_ising_abs_error": max(x[1] for x in errors)},
        "runs": rows,
        "shot_sensitivity": shots_rows,
        "archived_depth": {"provenance": "tracked_archive_not_rerun",
                           "path": str(depth_path.relative_to(ROOT)), "data": archived_depth},
    }
    save(SOURCES / "experiments_summary.json", index)
    print("Saved", len(rows), "full experiments and", len(shots_rows), "fixed-angle shot samples", flush=True)


if __name__ == "__main__":
    main()
