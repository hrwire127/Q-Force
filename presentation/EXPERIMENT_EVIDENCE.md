# Quantum Railways presentation evidence

Generated from the `zus` working tree at commit `728ce48302ef094f9f5e69633bd3ba843356de4e` on 8 November 2026. Full, per-run JSON is in [`experiments/`](experiments/); the compact machine-readable index is [`source_data/experiments_summary.json`](source_data/experiments_summary.json). Reproduce local runs with `..\QuissKit\.venv\Scripts\python.exe presentation\run_experiments.py` from the repository root. No IBM hardware job is submitted by this script.

## Baseline and exact check

The five selected binary routes are IDs `0,1,2,6,8`; they touch **five distinct cities**. At budget `B=7`, the implemented additive-score objective has 32 possible plans and 16 feasible plans. Exact enumeration gives two tied optima: `01010` (IDs 1,6) and `00111` (IDs 0,1,2), each score 15 and cost 7. At `λ=0.7`, the exact QUBO minimum is `01101`, score 18, cost 8, energy −17.3: **invalid** under the true budget rule. At `λ=4.0`, the exact model minimum is feasible. Direct, QUBO, and Ising energies were compared for all 32 states; maximum absolute errors were `1.07e−14` and `7.11e−15` respectively.

The squared model is `E(x)=−Σvᵢxᵢ+λ(Σcᵢxᵢ−B)²`. It penalizes underspending as well as overspending, so a stronger `λ` is not a universal encoding of the `≤B` inequality. Absolute energies from different `λ` models must not be compared as though they were the same objective.

## Controlled penalty study — primary result

All six fresh local runs use five routes/five cities, `B=7`, `p=1`, COBYLA, one restart, 30 requested optimizer evaluations and 2,048 shots per backend. Seeds were paired. Within each run, the local ideal and **synthetic** noisy samplers used the same optimized angles. All six optimizers exhausted their evaluation budget; there is no convergence claim.

| Seed | λ | Exact model minimum valid? | Ideal P(feasible) | Noisy P(feasible) | Ideal P(any tied feasible optimum) |
|---:|---:|:---:|---:|---:|---:|
| 2026 | 0.7 | No | 52.54% | 53.03% | 7.42% |
| 2026 | 4.0 | Yes | 51.07% | 52.00% | 2.54% |
| 2027 | 0.7 | No | 62.01% | 59.91% | 11.38% |
| 2027 | 4.0 | Yes | 45.46% | 45.21% | 10.99% |
| 2028 | 0.7 | No | 47.41% | 45.61% | 2.00% |
| 2028 | 4.0 | Yes | 65.43% | 58.50% | 7.23% |

The precise finding: **λ=4 fixes the exact model minimum for this instance; sampled QAOA feasibility changes in both directions over three seeds.** Three seeds and nonconverged training do not establish a general penalty effect. Ideal exact statevector probabilities, finite-shot probabilities, raw counts, optimized angles, optimizer histories, and resource metadata are separately retained in each JSON file. The slide percentages are finite-shot estimates.

For the baseline seed 2026, ideal expected model energy changed from −1.144814 to −6.750649, with `γ=1.6096795943`, `β=3.1372090827`; the optimizer reported evaluation-limit exhaustion. The ideal sampler's most frequent plan was score 14/cost 6, while its best feasible observed plan scored 15/cost 7. Do not confuse either with the exact model minimum.

## Other local studies

* **Shot precision:** [`source_data/shot_sensitivity.json`](source_data/shot_sensitivity.json) contains 12 samplings of **one fixed trained circuit** at 256, 1024, 2048 and 4096 shots across seeds 2026–2028. Wilson 95% intervals are stored per run. More shots improve estimate precision; they do not change the trained state. The slide shows approximate half-widths near P≈0.5, not a performance gain.
* **Budget:** Five routes/five cities; budgets 5, 7 and 9, with each problem retrained at seed 2026. Exact best true scores were 11, 15 and 20. A larger budget changes the optimization problem, so rising score does not prove a better algorithm.
* **Decision-space size:** Five routes/five cities = 32 states; seven routes/seven cities = 128; eight routes/**seven cities** = 256. The number of route decisions, not city count, sets qubit count. The current ideal-plus-noise interface supports at most eight active routes. See the `size_7` and `size_8` JSON files.
* **Ideal versus synthetic noise:** Baseline seed 2026 at 2,048 shots gave ideal P(feasible)=52.54% and local synthetic-noise P(feasible)=53.03%, with best feasible true score 15 for both. One finite-shot difference does not show noise helped.
* **Archived depth comparison:** [`../validation/p_comparison_seed2026/comparison.json`](../validation/p_comparison_seed2026/comparison.json) is an older **19-route**, budget-20, λ=.7, seed-2026, 4096-shot comparison: p=1 observed best feasible score 46, p=2 score 43; compiled two-qubit gates 171 versus 342. Both training runs exhausted 30 evaluations. It is not a paired five-route result.

## Provenance and boundaries

The ten `experiments/*.json` files were executed locally for this presentation using repository `experiment.run_experiment`; the 19-route depth comparison is tracked archived evidence. Real QPU data is absent. The app's current notebook has saved outputs and prose from differing five-route and 19-route configurations; no misleading notebook screenshot was used. Mean true scores in JSON include invalid samples where labeled; slide comparisons use feasibility or true feasible score. Neither quantum speedup nor guaranteed QAOA optimality is claimed.
