# Quantum Railways / Q-FORCE

Streamlit application for configuring fictional Romanian railway scenarios,
running exact classical enumeration and QAOA, comparing results on the team's
interactive map, and exporting self-contained HTML and PDF reports.

## Install and run

Python 3.12 or 3.13:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open http://localhost:8501. No credentials or environment variables are needed.
For the already installed environment in this workspace:

```powershell
cd C:\Users\artio\Desktop\Hackaton\Quantum-Railways-Sequential
..\QuissKit\.venv\Scripts\python.exe -m streamlit run app.py
```

## Workflow

1. Set the budget, check routes in the sidebar and review the selected connection
   list and route/city counts at the top.
2. Optionally enable **Simulează un incident** and use **Regenerează locul
   incidentului**. Only its location changes; the connection is unavailable.
3. Set penalty and shots. Depth, optimizer evaluations, restarts and backend are
   available under **Setări QAOA**. Seed, tolerance and transpiler level are internal.
4. Click **Rulează simularea**. The best feasible observed quantum plan is shown
   first, with its selected connections, score, energy, cost and outcome histogram.
5. The classical result follows with the same fields, its own solution map and
   probability histogram. **De ce este optim acest plan?** keeps the explanation.
6. **Simulări salvate / Încarcă simularea** restores a saved run without retraining.
   Before/After can compare any two saved runs. **Pregătește PDF-ul simulării**
   exports the displayed frozen result. The HTML export API remains available.

The PDF action follows the presentation page: quantum result for the selected
backend, classical result, matching selected-edge maps and disjoint histograms,
then Sabina's explanation and reproducibility metadata. Changing the displayed
backend hides a PDF generated for another backend until it is regenerated.
`pdf_report(result, presentation_backend='ideal')` generates this compact version;
`pdf_report(result)` keeps the full technical report API for programmatic use.

Completed experiments are immutable JSON snapshots persisted in local SQLite at
`output/simulation_history.sqlite3` (gitignored). Existing session snapshots are
migrated when available; previously lost browser sessions cannot be recovered.
History survives refreshes and app restarts. Override the local path with optional
`QUANTUM_RAILWAYS_HISTORY_DB`. Automated tests use isolated databases and never
write to the user's history. Changing settings hides stale results until rerun
or an explicit history load restores the original settings.

The presentation view shows only checked connections on its configuration map,
and only the actually selected solution connections on each result map. Each map
contains only cities at those connections' endpoints. **Probability samples**
histograms show one bar per plan, colored as optimal feasible, feasible suboptimal
or infeasible. Quantum probabilities are actual counts divided by shots. The
classical algorithm is deterministic: its chosen exact plan has P=1, with no
invented classical samples or uniform random choice among optimal ties. The x-axis
uses full original Qiskit-order bitstrings (x0 on the right). Up to 64 states are
displayed without renormalizing probabilities. PDF charts use the same data.

## Architecture and contracts

- `app.py`, `styles.css`: Livia's explorer and visual design.
- `railway_data.py`: original 12-edge board and five-decision baseline.
- `railway_catalog.py`: shared extended catalogue (19 edges) and coordinates.
  International border costs follow the latest zus notebook (1 per edge).
- `railway_map.py`, `railway_simulation.py`, `railway_scenarios.py`,
  `pages/2_Live_Network.py`: Catalin's map, incidents and replay controls.
- `quantum_optimizer.py`: zus QUBO/Ising conversion, real Qiskit QAOA,
  COBYLA training, Aer sampling, exact dynamic-programming reference.
- `experiment.py`: validated configuration, complete enumeration, shared
  classical/QUBO references, empirical statistics, JSON result snapshot.
- `classical_optimizer.py`: Sabina's exact selection, Pareto/budget analysis,
  alternatives, explanations and true-score QAOA evaluation.
- `classical_bridge.py`: adapter from shared routes to Sabina's API; preserves
  stable physical IDs and keeps hard incident closures outside the search space.
- `experiment_ui.py`: experiment controls, comparison, map and exports.
- `simulation_history.py`: local, append-only compressed snapshots, history
  selection and safe restoration of controls before Streamlit creates widgets.
- `reporting.py`: matching HTML/PDF text, maps and charts using Matplotlib.
- `analysis_qaoa/`, `README_QAOA.md`, `QAOA_VALIDATION.md`: preserved historical
  analysis and API documentation. Historical reports are not current results.

Route `id` is physical identity; input list position is the binary decision.
Routes have `cities`, `cost`, `value`; cost already includes `border_cost`.
Qiskit strings display decision 0 at the right. A plan returns `bits`,
`bitstring`, `ids_rute`, `cost_total`, `valoare_totala`, `energie`, `valid`.

## Scientific interpretation and limits

Default: IDs [0,1,2,6,8], budget 7, penalty 0.7, p=1, 2048 shots, seed 2026.
There are 32 plans; the exact feasible optimum is score 15 at cost 7.
Energy is `-score + penalty*(cost-budget)^2`. The minimum is -17.3 for an
invalid plan of cost 8 and score 18. These values are computed, not substituted.
The model penalizes underspending too; energy optimization does not guarantee
feasibility. Connectivity-ticket objectives are not part of this additive model.

Interactive limits: 1-10 eligible routes, p<=3, <=8192 shots, <=100 COBYLA
evaluations per restart, <=4 restarts. Noisy comparison is limited to 8 routes
because density-matrix simulation grows exponentially. Training is always ideal.
Both backends sample the same trained angles. Synthetic noise is generated by
GenericBackendV2; no hardware access or claim of quantum advantage is involved.
No feasible observed sample is reported as missing, never replaced by a classical
answer. Finite-shot probabilities are estimates. COBYLA can exhaust its budget.
Larger ideal benchmarks remain available through the preserved CLI/notebook.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests cover QUBO/Ising equivalence, all 32 baseline states, budget boundaries,
decoding, probabilities/ties, QAOA, routing/noise, maps, incidents, parameter
changes, export generation and the Streamlit run/analyze/export workflow.
PDF visual QA uses Poppler (`pdftoppm`); it is optional for application runtime.

## Sequential integration

`livia` was merged into `catalin` first (`fee97c4`) after map tests and both
Streamlit pages passed. That integrated `catalin` was then merged into `zus`.
Main was not modified. Conflicting app implementations became connected pages;
styles and interactions remain. Baseline notebook is archived under
`validation/baseline_notebook.ipynb`; the main notebook retains zus's extended
experiments. Dependencies combine both UI branches; PDF uses existing Matplotlib.

## Geographic map and simulated incidents

Incident features were developed on `feature/railway-incidents-real-map` and are
now preserved on the final integrated `zus` branch together with Sabina's work.

The map now defaults to a real CARTO/OSM basemap centered on Romania, using the
existing Plotly MapLibre technology. Pan/zoom can navigate worldwide and Streamlit
provides fullscreen. Click city markers, connection points, or incident markers
to populate a linked details panel. City coordinates are real; all optimization
connections, construction costs, scores and incidents are fictional. There is no
real railway-track geometry layer, and straight segments never claim to be real
tracks. Online tiles require internet; the underlying map helper also supports
schematic offline rendering. Reports use static schematic maps showing selected
solution connections and never download basemap tiles.

Attribution: [OpenStreetMap contributors](https://www.openstreetmap.org/copyright)
and [CARTO](https://carto.com/attribution/). See the official
[Plotly tile layer documentation](https://plotly.com/python/tile-map-layers/) and
[Streamlit selection API](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart).

`railway_incidents.py` defines immutable validated `Incident` records. Supported
types are closure, maintenance, technical malfunction, weather, reduced capacity,
delay, and increased operating cost. Severity is LOW/MEDIUM/HIGH/CRITICAL. All
sources are **simulated**; no verified external incident feed is implemented.
Start/end times are integer scenario-relative minutes, not real-world timestamps.
End time is exclusive. Change the scenario-time control to inspect scheduled
incidents. Overlapping closures remain effective until all relevant closures or
maintenance incidents are resolved, removed or expired.

Effects are explicit:

- Closure and maintenance remove a connection from the available MultiGraph and
  both optimization search spaces. Original network records remain intact.
- Delay minutes, capacity percentage and `cost_delta` (operating cost) are metadata
  only. They do not silently alter the construction objective or route reward.
- `construction_cost_delta` is a separately labeled optional construction-cost
  surcharge. It changes classical totals, QUBO coefficients, Ising, QAOA training
  and reports consistently. Concurrent surcharges/delays add; capacity uses the
  lowest remaining percentage. Severity itself never implies hidden numerical effects.

The presentation incident panel now has only an enable toggle and a regenerate
button. It chooses one checked connection as a simulated closure, with no manual
seed or extra incident parameters. Regeneration chooses a different connection
when more than one is available. Disabling the toggle restores availability.
The richer validated incident API remains supported for saved experiments and
programmatic scenarios. Incident changes never overwrite older result snapshots.

Graph analysis retains cities as isolated nodes when every adjacent connection is
closed. Reachability and alternative paths use only available edges. Displayed
paths minimize summed construction cost, not travel time; no direct edge is invented.

Closed decisions are removed exactly before rebuilding classical enumeration,
QUBO/Ising and QAOA. `decision_map.active_ids` and `decision_map.original_ids`
retain identity; every displayed sampled plan includes `full_bits` with zeros for
closed decisions in original input order. When all routes close, one empty plan
is evaluated deterministically and no zero-qubit circuit or shots are executed.

### Before/after workflow

1. Select the default five routes and run **Rulează simularea** with incidents off.
2. Enable **Simulează un incident** and optionally regenerate its location.
3. Run **Rulează simularea** again. Both algorithms use the four available
   decisions. Compare available routes, feasible plans, exact scores/costs,
   QUBO energy, QAOA probabilities and connected components in Before / After.
4. Inspect the result map and measurement table. Each optimum probability is
   relative to that snapshot's own feasible optimum, including ties. Energy
   differences across changed decision spaces are not interpreted as advantages.
5. Generate/download HTML and PDF reports. They freeze incident records, blocked
   IDs, decision mapping, statistics and baseline comparison at execution time.
6. Disable **Simulează un incident** and rerun to restore the original scenario,
   or load any prior simulation using **Încarcă simularea**. Earlier runs remain
   available from persistent history and can be compared and exported.

Snapshots now persist beyond the Streamlit session in the local SQLite database.
Simulations are synchronous with visible running/completed/failed states and bounded resources.
The legacy Live Network page and its synthetic timeline remain available; the main
page's incident experiment controls are the ones that rebuild the optimization model.

New tests in `tests/test_incidents.py` cover closures/restoration, times, severity,
all seven types, seeded random generation, paths/no paths, disconnected graphs,
cost semantics, QUBO/Ising equivalence after removal, QAOA original-bit mapping,
all-routes-closed handling, map colors/click details, frozen reports and the full
Streamlit baseline/block/run/export/unblock workflow.

## Full QAOA application contract

The existing `zus` commits are ancestors of this feature branch. The actual
`quantum_optimizer.py` implementation is reused: QUBO/Ising conversion, RZ/RZZ
cost, RX mixer, Qiskit Statevector expectation, COBYLA restarts, and real Aer
measurement. No further branch merge or replacement UI is involved.

The current UI calls the typed entry point:

```python
from experiment import RailwayScenario, SimulationConfig, run_railway_optimization

result = run_railway_optimization(
    RailwayScenario(routes=selected_routes, incidents=incident_records, time=0),
    SimulationConfig(budget=7, penalty=0.7, p=1, shots=2048, seed=2026,
                     maxiter=30, restarts=1, mode='compare',
                     optimizer='COBYLA', optimizer_tol=1e-4,
                     transpilation_level=1),
)
```

`RailwayScenario` and `SimulationConfig` are dataclass inputs; the pipeline takes
a deep snapshot and returns the JSON-compatible `ExperimentResult` TypedDict.
The established `run_experiment` function remains a compatibility entry point to
the same orchestration. Only the additive construction-score objective and COBYLA
are implemented; unsupported methods/objectives raise a clear validation error.
All phases share the effective route list, budget, energy and original-bit mapping.

The result contains:

- Experiment UUID, stable scenario content ID, complete config, selected/available
  IDs, active incident IDs, software versions and backend settings.
- Exact complete-enumeration reference, runtime, feasible count, **all** tied
  feasible optima and **all** tied model minima. The chosen classical plan is
  cross-checked against the exact DP reference from `zus`.
- QUBO linear/upper-triangular quadratic/offset coefficients and Ising h/J/constant
  in the same active-decision order, including the full energy constant.
- Actual ideal and optional noisy counts in `counts_by_backend`; quantum angles,
  restart status, initial/final expected energy, objective history and timings.
- Exact ideal statevector probabilities/statistics stored separately from sampled
  empirical statistics. Noisy uses the same trained angles and logical `plan`
  measurement register, with synthetic topology/noise and no real IBM hardware.
- Reconstructed full original plans for optima, sampled plans, quantum
  recommendations and the DP reference. Blocked positions remain zero.

Backend configuration supports COBYLA tolerance and transpilation level 0-3;
these are internal settings in the presentation UI, together with the seed.
Both ideal and noisy sampling use the chosen level and seeded transpiler.
COBYLA requires at least `2*p+2` evaluations; the UI enforces that minimum and the
pipeline rejects smaller budgets rather than allowing SciPy to increase them
silently. Changing a setting invalidates stale results.

Outcome charts show feasible/infeasible probabilities, exact versus finite-shot
probabilities, classical versus sampled feasible score, convergence, distributions
and compiled circuit resources. Before/after distributions align **full original
bitstrings**, not reduced measurement keys. Each scenario's optimal probability
uses its own reference. The presentation Before/After table compares saved runs;
loading either run restores its complete scenario and displayed solution maps.

HTML/PDF exports include model coefficients, tie counts and up to 20 listed tied
plans (complete lists remain in the snapshot), training settings/status/angles,
exact versus empirical statistics, real ideal/noisy results, comparison charts
and frozen baseline data. Archived older snapshots remain separately accessible.
If every route is blocked, no circuit or shots are executed and the empty-plan
probability is exact; no artificial measurement counts are produced.

Additional regression tests in `tests/test_algorithm_contract.py` verify the
typed result, all 32 energy equivalences, tied model minima, actual ideal/noisy
count totals, parameter propagation, unsupported configuration rejection,
incident optimum `[0,0,1,1,0]` (score 14, cost 6), map switching without retraining,
and matching HTML/PDF exports through Streamlit. No new dependencies are required.

## Final integration of all four branches on zus

The final `sabina -> zus` merge follows the completed `livia -> catalin -> zus`
sequence. Before it, zus was fast-forwarded to the validated incident/QAOA feature
commits and the latest remote zus commit `196288e` was merged without discarding
either history. That remote work adds p=1/p=2 comparisons, circuit illustrations,
notebook updates, examples and tests. Main and the original Sabina working copy
(including its uncommitted deletion of app.py) were not changed.

Sabina's `optimize_routes` now selects the canonical exact feasible plan. All
optimal ties are still retained. Its primary tie rule is maximum score, minimum
cost, then lexicographically smallest bit vector **in input decision order**.
The Qiskit-key tie rule in zus's independent DP may choose another equally good
plan; score and cost are cross-checked. The quantum sampling tie rule is preserved.

`classical_analysis` in each frozen experiment contains the source result,
Romanian explanation, top three plans, cheaper alternative, Pareto frontier,
budget profile and exact plan-count audit. All vectors include original full bits
and physical route IDs. Construction-cost adjustments and route closures are
applied before the adapter. Budget profiles are bounded to 0..100 and are classical
hypothetical analyses, not QAOA reruns. Actual ideal/noisy measurement distributions
are evaluated with Sabina's `evaluate_qaoa_distribution`; feasible probability,
all-optima probability and mean true score are checked and unified in the dashboard.
No synthetic measurement counts are created for a completely closed network.

The **De ce este optim acest plan? — analiza Sabina** panel is inside the existing
Optimization Center. It includes explanations, alternative and Pareto tables,
budget sensitivity and QAOA distribution audits. HTML/PDF exports use the same
snapshot and include the explanation, alternatives and sensitivity charts.

Conflict decisions:

- `app.py`: keep the unified interface and integrate Sabina's widgets/data through
  its existing experiment panel, rather than introduce another application.
- Notebook: keep the current extended p=1/p=2 version; archive Sabina's solved
  five-decision notebook as `validation/sabina_baseline_notebook.ipynb`.
- `railway_results.json`: retain the existing historical baseline. Incoming counts
  and metrics are identical; only training duration differs. Preserve Sabina's
  separate historical record as `validation/sabina_railway_results.json`.
- README: retain the unified run guide and preserve the incoming API reference in
  `docs/SABINA_CLASSICAL_API.md`.
- `.gitignore`: retain the union of cache, environment and generated-output rules.

Recoverable backups: `backup/zus-before-sabina-20261107`,
`backup/feature-before-sabina-20261107`, and
`backup/zus-ready-for-sabina-20261107`. No existing branch was deleted or reset.

All tests, including Sabina's original suite and cross-module workflow checks:

```powershell
python -m pytest -q
```

The preserved remote depth-comparison CLI remains available:

```powershell
python examples/compare_qaoa_depths.py --small --maxiter 30 --shots 2048
```

No new dependency is required by this merge. The current standalone source APIs
remain available for notebooks, while the application uses one shared scenario,
configuration and export snapshot. Historical notebook/output files are evidence
of earlier experiments, not current dashboard values.
