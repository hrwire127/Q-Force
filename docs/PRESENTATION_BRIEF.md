# Quantum Railways: presentation brief

Prepared 8 November 2026 from the audited `zus` working tree at `728ce48302ef094f9f5e69633bd3ba843356de4e`. See [PROJECT_AUDIT.md](PROJECT_AUDIT.md) for the requirement matrix, code locations, test record and caveats. The notebook has a pre-existing uncommitted edit; these slides should be built from a frozen, explicitly named run after its narrative is reconciled.

## Project in one paragraph

Quantum Railways is a Streamlit teaching and experimentation app for choosing fictional railway connections between real Romanian city locations under a construction budget. Each selected connection adds a fictional value; the true planning rule is to maximize total selected-route value while spending at most the budget. The app enumerates all feasible plans for an exact classical reference, builds a QUBO and Ising Hamiltonian, trains a Qiskit QAOA circuit with ideal statevector expectations, samples it with ideal Aer and optionally a local synthetic noisy backend, then compares measured feasible plans with the exact reference on maps and in reports. Simulated route closures can rebuild both decision spaces. It does **not** optimize destination-ticket connectivity or run on real IBM hardware in the verified evidence.

## Scientific story and exact language

**Main question for the talk:** “Does a larger budget penalty make QAOA return more *feasible* railway plans?” The team notebook states the proposed change `λ=0.7→4.0` in cell 37, but cell 39 has `RUN_EXTENSION=False`. The audit executed three paired seeds at five routes and found a useful qualified answer: `λ=4` moves the exact **model minimum** from an invalid plan to a feasible optimum, while measured QAOA feasibility changes inconsistently across seeds. This is new auditor-run evidence; label it as such until the team records and explains the runs in its submission. A second supported story is the tracked 19-route p=1 versus p=2 experiment, but it has one seed and neither optimizer converged. Keep one primary research question rather than claiming all extensions as one controlled experiment.

**Problem and reference.** A bit `x_i=1` buys route `i` in input decision order. `C(x)=Σc_ix_i`, `V(x)=Σv_ix_i`, and valid means `C(x)≤B`. For demo IDs `[0,1,2,6,8]`, `B=7`, exact enumeration checks 32 plans and finds two tied score-15/cost-7 optima. The canonical application plan is key `01010` (IDs 1,6); another valid tied optimum is `00111` (IDs 0,1,2). Explain why the classical solution is the exact yardstick for this tiny instance, not a competitor beaten by QAOA. Evidence: `railway_data.py:18-39`, `classical_optimizer.py:128-165`, `experiment.py:91-106,226-227`; auditor execution.

**Energy model.** The implemented QUBO is `E(x)=-V(x)+λ(C(x)-B)^2`, with `a_i=-v_i+λ(c_i²-2Bc_i)`, `b_ij=2λc_ic_j` for `i<j`, offset `λB²`. Use `x_i=(1-Z_i)/2` to obtain a diagonal Ising Hamiltonian with constant, Z and ZZ terms. At `λ=.7`, the exact minimum is key `01101`, score 18/cost 8/energy `-17.3`: it violates the actual budget. The conversion is correct; the squared equality penalty is the modeling mismatch. At `λ=4`, the model minimum for this instance is feasible key `00111`, score 15/cost 7/energy `-15`. This is not a general inequality guarantee. Evidence: `quantum_optimizer.py:128-177`; auditor compared all 32 direct/QUBO/Ising energies, max discrepancies below `1.1e-14`.

**QAOA in plain language.** Hadamards put every candidate plan into the initial superposition. A Cost layer adds objective-dependent phases using RZ and RZZ gates; a Mixer layer applies RX gates so amplitudes interfere. One `γ` and one `β` are trained for each layer; depth `p` repeats the pair. COBYLA changes angles to lower the **expected model energy** computed from an ideal statevector. The final bound circuit is measured for a finite number of shots. Printed Qiskit bitstrings place `x_0` on the right, so interpret route IDs via the decision list. A sample is a candidate plan, and the recommendation is the highest-value **feasible observed** sample. Neither low expected energy nor a high-scoring invalid sample is the exact classical optimum. Evidence: `quantum_optimizer.py:105-113,179-220,268-321,357-440`; focused tests.

## Verified results that can go on slides

| Claim | Evidence | Safe wording |
| --- | --- | --- |
| The five-route baseline has 32 plans, 16 feasible plans, two score-15/cost-7 optima. | Fresh `run_experiment` and 46 focused algorithm/classical tests. | “Exact enumeration provides our ground truth.” |
| The `λ=.7` QUBO minimum is invalid (score 18, cost 8, energy −17.3). | Fresh enumeration and all-32 energy equivalence check. | “Our correct QUBO optimizes the *wrong budget preference* for this case.” |
| Default five-route training at seed 2026 reduced ideal expected energy from −1.144814 to −6.750649 with `γ=1.6096795943`, `β=3.1372090827`. | Fresh 2048-shot run, `p=1`, 30 SciPy evaluations, one restart. | “Energy fell at this seed; optimizer reported evaluation-budget exhaustion.” |
| Three paired penalty seeds show mixed feasibility. | Fresh audit runs, table below. | “A stronger penalty fixes the model minimum here, but did not consistently increase feasible sampling.” |
| Ideal and synthetic noisy sampling both execute on one trained circuit. | Fresh 256-shot API run: ideal feasible 131/256, noisy 141/256; `experiment.py:189-198`. | “These are local simulator samples; this small difference does not establish a noise benefit.” |
| The tracked 19-route depth comparison at budget 20 observed score 46 for p=1 and 43 for p=2. | `validation/p_comparison_seed2026/comparison.json` and `raport.md`; depth tests pass. | “One archived seed with equal 30-evaluation budgets; neither optimizer converged.” |
| HTML and PDF are generated from frozen result data. | Auditor generated HTML and a visually inspected three-page focused PDF; reporting code. | “The main UI offers PDF download; HTML is available through an API.” |

Auditor penalty study: same five routes, budget 7, p=1, 2048 ideal shots, 30 SciPy evaluations, one restart, and matched seeds. All six runs exhausted the evaluation budget. Do not compare absolute energies across different `λ` values.

| Seed | P(feasible), λ=.7 | P(feasible), λ=4 | P(any feasible optimum), λ=.7 | P(any feasible optimum), λ=4 |
| ---: | ---: | ---: | ---: | ---: |
| 2026 | 0.525391 | 0.510742 | 0.074219 | 0.025391 |
| 2027 | 0.620117 | 0.454590 | 0.113770 | 0.109863 |
| 2028 | 0.474121 | 0.654297 | 0.020020 | 0.072266 |

The same seed does not make the two trained distributions identical, and three seeds are preliminary. Exact ideal feasible probabilities also moved in mixed directions (`PROJECT_AUDIT.md`, “Executions and numerical evidence”). The precise discovery is that **model correctness and trained sampling quality are different checks**.

## Contribution and limits to say aloud

The most defensible original contribution is the controlled analysis of the budget-penalty failure, supported by the team's explicit question and the auditor's paired runs. The team also built depth-comparison tooling, incident-aware what-if planning, tie-aware classical explanations, a synchronized geographic interface and frozen reports. These are useful extensions beyond the supplied notebook; the interface itself is not a new quantum algorithm. The QAOA training is ideal and classical; the local noisy backend is synthetic. There is no verified real-QPU job, no destination-ticket or network-connectivity reward, no slack-variable inequality QUBO, no claim of quantum advantage, and no guarantee of optimizer convergence. Exact enumeration is practical and scientifically necessary at five bits.

## Proposed 11-slide structure

| Slide | Main message and key points | Implemented support and exact evidence | Recommended visual | Missing evidence or condition |
| --- | --- | --- | --- | --- |
| 1. Quantum Railways | Fictional Romanian route-choice game; investigate whether QAOA samples useful budget-feasible plans. | `app.py:38-73`, official guide p. 1. | Title screenshot of selected five-route map. | Capture on the presentation machine; caption fictional edges/costs/rewards. |
| 2. Problem and binary decisions | `x_i` buys one route; cost and value add; budget is `≤7`; disconnected routes allowed. | `railway_data.py:18-39`, `quantum_optimizer.py:116-128`; five demo cost/value pairs in audit. | Five-row route table plus map. | No ticket-connectivity score exists; label destination-ticket art as inspiration only. |
| 3. Classical ground truth | Enumerate 32 plans; 16 feasible; two ties at score 15/cost 7. | Fresh enumeration; `experiment.py:91-106,226-227`; focused tests. | Small feasible-score chart or two tied plan maps. | Capture both keys `01010` and `00111`; the main UI shows only its canonical tie. |
| 4. QUBO: what the model rewards | `-V+λ(C-B)^2`; invalid minimum at `λ=.7`; underspending is penalized too. | Fresh `-17.3`, score 18/cost 8; `quantum_optimizer.py:128-164`. | Energy-versus-cost sketch or three-row table. | Main UI lacks an explicit invalid-minimum map; make the table from frozen result data. |
| 5. Ising and QAOA layers | Binary-to-Z conversion; H initialization; Cost RZ/RZZ; Mixer RX; `γ,β,p`. | All-32 conversion test; `quantum_optimizer.py:164-220`; existing diagram in `output/qaoa_depths/illustrations/`. | Logical circuit/layer diagram with one coefficient or gate angle. | Verify exported diagram's route count and depth; never label it real hardware. |
| 6. Training and measurement | COBYLA minimizes exact ideal expected energy; final circuit uses finite shots; decode Qiskit keys. | Fresh seed-2026 training `−1.144814→−6.750649`, `γ=1.60968`, `β=3.13721`, nonconverged; `quantum_optimizer.py:357-440`. | Convergence line and sample histogram from one frozen run. | Capture chart and optimizer status from the same run; distinguish exact expectation from shot estimate. |
| 7. What we built | Streamlit → incident-aware scenario → exact reference + QAOA → maps/stats/history/PDF. | `app.py:44-73`, `experiment.py:136-278`, `experiment_ui.py:114-172`, `simulation_history.py:12-76`. | One architecture diagram and an application screenshot. | Full Streamlit startup/journey did not complete in this audit; rehearse. Live Network timeline is simulated. |
| 8. Research question: stronger penalty | Change only `λ=.7→4` on five routes; true classical rule stays fixed. | Notebook cell 37 states question; auditor three-seed runs and exact minima. | Paired chart of P(feasible) and P(optimal feasible) by seed. | Freeze run records and update notebook cell 39/conclusion before calling this a team-completed study. |
| 9. Results and interpretation | `λ=4` makes the exact model minimum feasible, but QAOA feasibility is mixed across seeds. | Six auditor runs in this brief; all optimizers hit evaluation limit. | Paired dot plot plus model-minimum table. | More seeds/training budgets are needed for a general trend; cross-penalty energy values are incomparable. |
| 10. Other experiment: depth and noise | p=1/p=2 19-route archived comparison; local synthetic noisy mode is separate from hardware. | Tracked `validation/p_comparison_seed2026/comparison.json`: 46 vs 43 best observed, 171 vs 342 two-qubit gates, both nonconverged. Fresh 256-shot ideal/noisy API result. | Archived depth chart and compiled-resource numbers. | Mark seed=2026, budget=20; do not mix with current notebook's saved budget-15 run. |
| 11. Limits, demo and conclusion | Exact classical benchmark reveals a model failure; QAOA behavior depends on model, training and shots. | Audit findings and code paths above. | One takeaway diagram and live-demo handoff. | Full UI rehearsal and reconciled notebook are still required. |

If the talk must be eight slides, combine 2+3, 5+6, and 10+11 while keeping the penalty result intact.

## Proposed live demonstration

1. Launch `streamlit run app.py` from `Quantum-Railways-Sequential` using the installed environment. Confirm exactly five checked routes and budget 7. Show route cost/value list and geographic map.
2. Set penalty 0.7, p=1, 2048 shots, 30 evaluations, one restart, ideal mode. Run. Explain that the UI's quantum panel is the **best feasible observed** sample, then show the classical exact result and sample histogram. Open the stored detailed JSON/report to show the **invalid** QUBO minimum and P(feasible); the focused UI does not expose all of these metrics.
3. Switch to ideal-plus-local-noise mode and rerun if time permits. Label it “synthetic local noise.” Choose the displayed backend without retraining. Do not infer an improvement from one finite-shot difference.
4. Toggle the simulated incident, rerun, and show that the active decision set and classical reference change; restore the earlier snapshot from history. Generate the PDF for the selected frozen result. Before/after expected energies are not directly comparable when the model changes.
5. Keep a pre-generated result JSON, histogram screenshot and PDF available in case basemap tiles or the live UI are slow. The five full Streamlit journey tests and a separate AppTest startup did not complete in this audit, so rehearse this exact path on the presentation machine.

## Evidence to collect before building the deck

- A clean five-route baseline screenshot and a frozen result file with route IDs, budget, penalty, p, seed, optimizer status, shots, counts, versions and timestamp. Show both tied classical optima and invalid QUBO minimum.
- A paired three-seed penalty chart built from the six audit configurations, with run-level JSON retained; decide whether to replicate/extend those runs in the team's final notebook. Record exact ideal and sampled probabilities separately.
- A convergence plot with initial/final expected energy and “evaluation limit reached,” plus the actual p=1 circuit/layer visual.
- One synchronized map and histogram for the selected quantum sample, one for the classical choice, and a verified PDF export from the same snapshot.
- A single 19-route depth comparison chart from the **tracked budget-20** archive, if it is included. Attach its config and note the one-seed/nonconverged limit.
- A corrected notebook submission: current saved outputs are 19 routes/budget 15, noisy and extension cells are disabled, while cell-36 prose describes a different five-route/noisy result. Reconcile outputs and prose before screenshots or citations. `SUBMISSION_TEMPLATE.md` was not supplied; follow the participant guide's question, baseline, change, reference, experiment, results, insight, limitation and next-step structure.
