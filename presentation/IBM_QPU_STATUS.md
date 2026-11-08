# IBM Quantum status — 8 November 2026

The repository records job ID `dbnpc00ou4as73b4u830` in `output/script_20261107_231254_822277/ibm_job.json`: backend `ibm_marrakesh`, QAOA depth 1, 4096 requested shots, timestamp `2026-11-07T21:20:00.867967+00:00`. The adjacent scenario is **19 route decisions, 14 cities**, budget 20, penalty 0.7, seed 2026, 30 evaluation limit and one restart. This is distinct from the five-route main experiment.

There is no hardware counts/result file in that output directory. A read-only status query using the locally configured IBM Runtime account returned `RuntimeJobNotFound: Job not found: dbnpc00ou4as73b4u830`. This means the job could not be verified from that account. It does **not** establish whether the job completed, failed or belongs to another instance. No additional QPU job was submitted.

The stored record also lacks a preserved bound circuit, optimized `γ/β`, logical-to-physical layout, and circuit hash. Even if counts are later retrieved, a fair same-circuit local-versus-QPU comparison requires these details. The deck therefore reports no QPU probabilities or score. Its slide 13 is a complete, explicitly unverified status slide.

## Read-only refresh

From the repository root:

```powershell
& .\.venv-ibm\Scripts\python.exe presentation\refresh_qpu_results.py --rebuild
```

This checks the recorded job through the configured account and never calls `Sampler.run`. Completed counts are validated for register width, shot sum and backend, then saved as a retrieval record. They are not promoted to a **verified** comparison until bound-circuit identity and parameters can be matched to the scenario. If those metadata are supplied in the original record, the script writes `presentation/source_data/ibm_verified_result.json`, computes true-score feasibility statistics, and rebuilds PPTX/PDF. Re-running is idempotent and does not submit work.

Credentials remain in the local ignored credential file or environment; no token is in this presentation directory. No background monitor has been created.
