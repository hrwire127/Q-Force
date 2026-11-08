"""Read-only IBM job refresh and conditional presentation rebuild.

This file never submits a QPU job. Run with the isolated .venv-ibm Python.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
RUN = ROOT / "output" / "script_20261107_231254_822277"
SOURCE = HERE / "source_data"


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def exact_reference(routes: list[dict], budget: int) -> tuple[int, set[str]]:
    best = -1
    optima: set[str] = set()
    for mask in range(1 << len(routes)):
        cost = sum(route["cost"] for i, route in enumerate(routes) if mask & (1 << i))
        if cost > budget:
            continue
        score = sum(route["value"] for i, route in enumerate(routes) if mask & (1 << i))
        if score > best:
            best, optima = score, {format(mask, f"0{len(routes)}b")}
        elif score == best:
            optima.add(format(mask, f"0{len(routes)}b"))
    return best, optima


def metrics(counts: dict[str, int], routes: list[dict], budget: int, shots: int) -> dict:
    optimum, optima = exact_reference(routes, budget)
    feasible = optimal = 0
    best_observed = -1
    for key, count in counts.items():
        if len(key) != len(routes) or set(key) - {"0", "1"} or count < 0:
            raise ValueError("QPU bitstring width or contents do not match the recorded scenario")
        # Qiskit count keys put logical qubit/route zero at the right.
        bits = key[::-1]
        cost = sum(route["cost"] for i, route in enumerate(routes) if bits[i] == "1")
        score = sum(route["value"] for i, route in enumerate(routes) if bits[i] == "1")
        if cost <= budget:
            feasible += count
            best_observed = max(best_observed, score)
            if key in optima:
                optimal += count
    if sum(counts.values()) != shots:
        raise ValueError("QPU counts do not add to the recorded shot count")
    return {"p_feasible": feasible / shots,
            "p_optimal_feasible": optimal / shots,
            "over_budget_rate": 1 - feasible / shots,
            "best_feasible_score": best_observed if feasible else None,
            "exact_best_feasible_score": optimum,
            "exact_optimum_count": len(optima)}


def retrieve() -> dict:
    from qiskit_ibm_runtime import QiskitRuntimeService

    record = json.loads((RUN / "ibm_job.json").read_text(encoding="utf-8"))
    scenario = json.loads((RUN / "scenario.json").read_text(encoding="utf-8"))
    cfg_file = ROOT / "ibm_credentials.local.json"
    config = json.loads(cfg_file.read_text(encoding="utf-8-sig")) if cfg_file.exists() else {}
    token = os.getenv("IBM_QUANTUM_TOKEN") or os.getenv("QISKIT_IBM_TOKEN") or config.get("token")
    instance = os.getenv("IBM_QUANTUM_INSTANCE") or os.getenv("QISKIT_IBM_INSTANCE") or config.get("instance")
    kwargs = {"channel": "ibm_quantum_platform"}
    if token:
        kwargs["token"] = token
    if instance:
        kwargs["instance"] = instance
    if not token and not (Path.home() / ".qiskit" / "qiskit-ibm.json").exists():
        raise RuntimeError("No configured IBM account was found")
    service = QiskitRuntimeService(**kwargs)
    job = service.job(record["job_id"])
    raw_status = job.status()
    status = str(getattr(raw_status, "name", raw_status)).upper().split(".")[-1]
    result = {"checked_utc": datetime.now(timezone.utc).isoformat(),
              "job_id": record["job_id"], "status": status,
              "backend": job.backend().name, "recorded_backend": record["backend"],
              "recorded_shots": record["shots"], "scenario_route_count": len(scenario["routes"]),
              "scenario_budget": scenario["budget"], "validation": "pending"}
    if result["backend"] != record["backend"]:
        raise ValueError("Recovered job backend differs from recorded backend")
    if status != "DONE":
        return result
    measured = getattr(job.result()[0].data, "plan", None)
    if measured is None or measured.num_bits != len(scenario["routes"]):
        raise ValueError("Completed job lacks matching plan register")
    counts = dict(measured.get_counts())
    result["shots"] = sum(counts.values())
    if result["shots"] != record["shots"]:
        raise ValueError("Completed job shot count differs from record")
    result["counts"] = counts
    result["metrics"] = metrics(counts, scenario["routes"], scenario["budget"], result["shots"])
    # A counts file alone does not prove that the bound circuit matches the saved
    # railway scenario. Require preserved angles and bound QPY identity.
    qpy_path = RUN / "bound_circuit.qpy"
    expected_hash = record.get("bound_circuit_sha256")
    angles = record.get("gamma"), record.get("beta")
    if (qpy_path.exists() and expected_hash and all(isinstance(v, list) and v for v in angles)
            and hashlib.sha256(qpy_path.read_bytes()).hexdigest() == expected_hash
            and record.get("qaoa_depth") == len(angles[0]) == len(angles[1])):
        result.update(validation="verified", gamma=angles[0], beta=angles[1],
                      bound_circuit_sha256=expected_hash,
                      source_scenario=str((RUN / "scenario.json").relative_to(ROOT)))
    else:
        result["validation"] = "counts_retrieved_circuit_match_unverified"
        result["limitation"] = "Missing or mismatched saved bound circuit and gamma/beta metadata"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild", action="store_true", help="Rebuild the deck/PDF after status refresh")
    args = parser.parse_args()
    try:
        result = retrieve()
    except Exception as error:
        # Do not print SDK exception details: they may include account identifiers.
        result = {"checked_utc": datetime.now(timezone.utc).isoformat(),
                  "job_id": "dbnpc00ou4as73b4u830", "validation": "unverified",
                  "status": type(error).__name__, "message": "Recorded job could not be verified with the configured account"}
    write_json(SOURCE / "ibm_refresh_status.json", result)
    if result.get("counts"):
        write_json(SOURCE / "ibm_retrieved_counts.json", result)
    if result.get("validation") == "verified":
        write_json(SOURCE / "ibm_verified_result.json", result)
    print(f"IBM {result['job_id']}: {result['status']} / {result['validation']}")
    if args.rebuild:
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        str(HERE / "rebuild.ps1")], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
