# Quantum Railways: implementation audit

Audit date: 8 November 2026 (Europe/Bucharest). Scope: the integrated `Quantum-Railways-Sequential` working tree on `zus`, plus the supplied beginner materials in the sibling `Hackathon2-Materials/Beginners - Quantum Railway` directory. This is an independent code and execution audit; no application source was changed. Status describes the audited working tree, including its pre-existing uncommitted notebook edit.

## Executive summary

The integrated application has a real, objective-dependent local QAOA circuit, an exact classical reference, QUBO/Ising conversions, synthetic noisy sampling, incident-aware decision removal, maps, statistics, and report generators. The mathematical conversions and 5-route reference are correct for the **implemented additive route-value game**. The central scientific limitation is the model: `E(x)=-V(x)+λ(C(x)-B)^2` encodes a preference for *exact spending*, whereas the actual rule is `C(x)≤B`. At the official baseline (`B=7`, `λ=0.7`), its global minimum is infeasible. The software reports this distinction rather than silently treating the energy minimum as a valid railway plan.

The guided lab's core is implemented through the application, but the current team notebook selects **19 decisions** and its saved execution used **budget 15**; its prose still describes a five-decision/noisy run. It sets `RUN_NOISY=False` and `RUN_EXTENSION=False`; its written penalty-extension question is therefore a proposal, not a completed notebook experiment. Five Streamlit full-workflow tests were not completed in this audit, so a rehearsed live demo remains a gate. No real-QPU execution or quantum advantage is verified.

## Sources, scope, and evidence grades

Official sources actually read: `../../Hackathon2-Materials/Beginners - Quantum Railway/PARTICIPANT_GUIDE.pdf` (4 pages), `Quantum Railways.pptx` (slides), `Quantum_Railways_Lab.ipynb` (50 cells), and `requirements.txt`. The guide says the core is exercises A–C and F/G, supplied D/E conversion, local angle training, binding/compiling and ideal versus **local synthetic noisy** sampling (pp. 1–2). Full D/E derivations, a real QPU, and hardware appendix are optional (pp. 1–3). It accepts a carefully explained guided lab without an extension (p. 3). `SUBMISSION_TEMPLATE.md`, the guide's `README.md`, and its named `01_quantum_railways_lab.ipynb` were **not present** among the supplied beginner files; the actual supplied notebook is named `Quantum_Railways_Lab.ipynb`. The guide's proposed judging weights explicitly await confirmation (p. 4), so none are treated as official.

The challenge slide deck speaks of destination tickets and connectivity (slides 1–3), while the guide explicitly defines the beginner true score as **sum of selected route values** and permits disconnected plans (p. 1). The application implements the guided additive game, not destination-ticket scoring. Present this distinction plainly.

Evidence terms used below: **executed** = run in this audit; **inspected** = code or saved artifact inspected; **archived** = repository result from an earlier run, not rerun now; **unverified** = runtime behavior not established here. Test commands used the existing `../QuissKit/.venv/Scripts/python.exe`, `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, and a workspace-local pytest temp directory.

## Repository, branch, and architecture

The workspace contains three Git repositories (`QuissKit`, `Quantum-Railways-Integration`, `Quantum-Railways-Sequential`) plus the supplied materials and loose root files. This audit targets the most complete integrated application, `Quantum-Railways-Sequential`; it does not assume the other copies are deployed or synchronized. The older `Quantum-Railways-Integration` copy is on `integration/quantum-railways` at `0c5b002`; `QuissKit` is on `livia` at `038523e`, with its own pre-existing edits/untracked files. The loose workspace-root `app.py` inserts a `Q-Force` directory into `sys.path`, but that directory is absent from the workspace inventory; use `Quantum-Railways-Sequential/app.py` as the documented entrypoint. The other copies were inventoried, not exhaustively audited, so findings below apply to the integrated `zus` tree. Current branch: `zus`, HEAD `728ce48302ef094f9f5e69633bd3ba843356de4e` (`Working notepad`, 7 November 2026). Its pre-existing `Quantum_Railways_Labb.ipynb` modification was not touched. Verifiable merge ancestry: `fee97c4` merges Livia into Catalin; `51fa607` merges Catalin into `zus`; `54cd9e5` preserves depth-comparison work; `112c918` merges Sabina's classical analysis. `git show --stat` confirms the latter added `classical_optimizer.py`, `classical_bridge.py`, tests and docs; `35bba12` added incident-aware optimization/map modules. Authorship beyond commit history is not independently proven.

| Layer | Actual implementation and connection |
| --- | --- |
| Frontend | `app.py:9-73` is a Streamlit entry page with sidebar route checkboxes, budget, map and `render_experiment`; `pages/2_Live_Network.py` is a separate synthetic timeline/replay page. CSS is `styles.css`. |
| Scenario | `railway_data.py:18-39` has the 12-edge original board and demo IDs `[0,1,2,6,8]`; `railway_catalog.py:11-27` extends to 19 routes; `railway_incidents.py:75-93` produces available routes, closures and explicit construction-cost changes. Physical route IDs stay separate from decision positions. |
| Orchestration | `experiment_ui.py:114-172` builds `SimulationConfig`, starts the run, stores a frozen snapshot and renders selected backend. `experiment.py:78-88,136-278` validates settings, rebuilds the current decision space, enumerates plans, trains/samples QAOA, computes statistics, and returns one JSON snapshot. |
| Classical | `classical_optimizer.py:128-165` exhaustively selects the best feasible score and retains ties. `classical_bridge.py:11-38` adapts shared routes. `quantum_optimizer.py:226-252` provides an independent exact 0/1 knapsack DP, cross-checked in `experiment.py:173-177`. |
| Quantum | `quantum_optimizer.py:132-220,268-440` constructs QUBO/Ising, QAOA, COBYLA objective, Aer counts and resource metadata. `qaoa_experiments.py:102-128` runs p comparisons. |
| Visualization and persistence | `incident_ui.py:14-55,98-120` renders geographic Plotly maps of the same scenario/result route IDs. `analysis_views.py:7-84` shapes charts. `simulation_history.py:12-76` stores compressed JSON in local SQLite and restores controls. |
| Reports | `reporting.py:13-100,102-272` builds maps/charts and HTML, full technical PDF, or focused presentation PDF from the same snapshot. |
| Tests/docs | `tests/` contains algorithm, classical, incident, map, notebook and UI tests. `README.md`, `README_QAOA.md`, `QAOA_VALIDATION.md`, and `docs/` document contracts; `validation/` contains tracked prior results. |

**Execution trace.** Route checkboxes and budget in `app.py:44-73` enter `render_simple_incidents` and `render_experiment`; visible QAOA controls are passed through `SimulationConfig` (`experiment_ui.py:117-136`). `run_experiment` applies closures before exact enumeration and QAOA (`experiment.py:149-173`), cross-checks DP (`:173-177`), summarizes ideal/noisy counts (`:187-245`), then freezes scenario, coefficients, plans, samples and metadata (`:262-278`). The UI maps/histograms and PDF consume that same result (`experiment_ui.py:154-172`). This is a connected pipeline. The Live Network page instead replays synthetic events and reads saved QAOA results (`pages/2_Live_Network.py:46-57,166-352`); its event timeline is not a live external rail feed.

## Requirements compliance matrix

Statuses are exactly: `IMPLEMENTED AND VERIFIED`, `IMPLEMENTED BUT NOT TESTED`, `PARTIALLY IMPLEMENTED`, `MISSING`, `NOT APPLICABLE`, `UNKNOWN / INSUFFICIENT EVIDENCE`. PG = official participant guide page; Lab = official supplied notebook cell; Slides = official deck slide. “Verified” refers to the cited focused tests/direct executions, not a completed browser rehearsal.

### 1. Mandatory guided-lab functionality

| Requirement | Official source | Status | Evidence in code | Test evidence | Gap or risk |
| --- | --- | --- | --- | --- | --- |
| Explain fictional railway subset game and true budget rule | PG 1; Lab 3–4 | IMPLEMENTED AND VERIFIED | `railway_data.py:18-39`; `quantum_optimizer.py:116-128`; `reporting.py:102-106` | Direct 32-state baseline; 46 algorithm/classical tests pass | Must avoid deck's ticket-connectivity wording for implemented score. |
| Complete A: bits, cost, value, feasibility | PG 1–2; Lab 7–8 | IMPLEMENTED AND VERIFIED | `Quantum_Railways_Labb.ipynb` cell 8; `quantum_optimizer.py:98-128` | Notebook saved outputs; focused tests; direct cost/score run | Team notebook presently selects 19 routes, not the official five-decision starter. |
| Complete B/C: energy and enumerate baseline | PG 2; Lab 9–12 | IMPLEMENTED AND VERIFIED | `Quantum_Railways_Labb.ipynb` cells 10/12; `experiment.py:91-106` | Direct 32 states, 16 feasible, score 15/cost 7; notebook's 19-route cells list 524,288 | Baseline evidence needs its own clearly labeled five-route screenshot. |
| Read/run supplied D/E conversions | PG 1–2; Lab 13–16 | IMPLEMENTED AND VERIFIED | `quantum_optimizer.py:132-177`; team notebook cells 14/16 | Direct 32-state equivalence; notebook saved 524,288-state check | Full derivation is optional. |
| Complete F/G; train local objective | PG 1–2; Lab 17–22 | IMPLEMENTED AND VERIFIED | `quantum_optimizer.py:179-220,357-407`; team notebook cells 18/21/22 | 46 focused tests and auditor run | Training may stop on evaluation budget, not convergence. |
| Bind/compile final circuit and compare ideal with local synthetic noisy samples | PG 1–2; Lab 26–35 | PARTIALLY IMPLEMENTED | `quantum_optimizer.py:268-296`; `experiment.py:189-198`; notebook cells 28–35 | Auditor ideal+noisy API run 256 shots each; focused tests pass | Current 19-route notebook has `RUN_NOISY=False`; app supports comparison only through 8 active routes. |
| Submit completed notebook/visuals/explanation in template structure | PG 4 | PARTIALLY IMPLEMENTED | Team notebook and `QAOA_VALIDATION.md`; `docs/RUN_NOTEBOOK_SCRIPT.md` | Notebook inspected, not rerun in this audit | `SUBMISSION_TEMPLATE.md` absent; notebook conclusion mixes scenarios and skipped noisy result. |

### 2. Quantum correctness

| Requirement | Official source | Status | Evidence in code | Test evidence | Gap or risk |
| --- | --- | --- | --- | --- | --- |
| Correct QUBO for stated squared energy | PG 2; Lab 13–14 | IMPLEMENTED AND VERIFIED | `quantum_optimizer.py:128-164` | Max direct–QUBO error `1.07e-14` over 32 states | Squared energy itself is an inexact ≤-budget model. |
| Correct Ising constant, h and J | PG 2; Lab 15–16 | IMPLEMENTED AND VERIFIED | `quantum_optimizer.py:164-177` | Max QUBO–Ising error `7.11e-15` over 32 states | No mathematical conversion gap. |
| Objective-dependent Cost and RX Mixer; independent p layers | PG 2; Lab 17–18 | IMPLEMENTED AND VERIFIED | `quantum_optimizer.py:179-220`; `tests/test_quantum_optimizer.py` | Gate/phase/layer tests among 46 pass | Circuit represents scaled `H_C`; constant is global phase. |
| Optimize expected energy and use final angles | PG 2; Lab 19–22 | IMPLEMENTED AND VERIFIED | `quantum_optimizer.py:357-407` | Auditor expected energy fell `-1.144814 → -6.750649` at seed 2026/default training | `success=False` at 30 SciPy evaluations; no global-minimum claim. |
| Correct logical measurement decoding and distinct outcomes | PG 2; Lab 23–24 | IMPLEMENTED AND VERIFIED | `quantum_optimizer.py:105-113,220-224,299-321`; `experiment.py:108-134,226-260` | Bit-order, routing and tie tests pass; 256-shot API run | UI emphasizes best feasible, hides several other distinctions in its main view. |
| Model faithfully enforces `C≤B` | PG 1–2 | PARTIALLY IMPLEMENTED | `quantum_optimizer.py:128-140`; `experiment.py:103-105` | `λ=.7`: min `01101`, score 18/cost 8, `E=-17.3`, infeasible | Penalty also penalizes underspending; no slack-variable inequality QUBO exists. |

### 3. Classical comparison

| Requirement | Official source | Status | Evidence in code | Test evidence | Gap or risk |
| --- | --- | --- | --- | --- | --- |
| Exact feasible reference, boundary and ties | PG 2–3; Lab 11–12 | IMPLEMENTED AND VERIFIED | `classical_optimizer.py:128-165`; `experiment.py:91-106,226-227` | 32 combinations, 16 feasible, two optimal-score ties, score 15/cost 7 | Canonical tie rule differs between Sabina and DP; score/cost are cross-checked. |
| Recompute reference on changed scenario/budget | PG 3 | IMPLEMENTED AND VERIFIED | `experiment.py:149-177`; `railway_incidents.py:75-93` | Incident and budget tests in 28-test subset pass | Before/after energies belong to different models. |
| Fair like-for-like quantum versus classical comparison | PG 3 | IMPLEMENTED AND VERIFIED | `experiment.py:170-245`; `analysis_views.py:50-77` | Auditor run uses identical routes/B/p and compares true score | “Best observed” depends on shots; exact enumeration is cheaper for five bits. |
| Compare QAOA with a random/uniform baseline | PG 3 (advanced guidance) | PARTIALLY IMPLEMENTED | Initial uniform Hadamard state in `quantum_optimizer.py:202-206`; notebook initial check | Uniform probability is `1/32`; no matched random-baseline experiment in app | Do not imply QAOA beats uniform from one sampled optimum. |

### 4. Research contribution

| Requirement | Official source | Status | Evidence in code | Test evidence | Gap or risk |
| --- | --- | --- | --- | --- | --- |
| State one question/change/reference/evidence if extending | PG 2–3 | PARTIALLY IMPLEMENTED | Team notebook cell 37 asks whether `λ=.7→4` improves feasibility; cell 39 disables run | Auditor's three-seed study below | Question is stated, but notebook does not execute or interpret the paired extension. |
| Investigate depth p=1 versus p=2 | PG 3 | IMPLEMENTED AND VERIFIED | `qaoa_experiments.py:102-128`; `validation/p_comparison_seed2026/` | Depth tests pass; archived 19-route paired JSON | One seed, equal 30-evaluation budgets, neither converged; not a general p ranking. |
| Study route disruptions and rebuild model | PG 3 (robustness idea) | IMPLEMENTED AND VERIFIED | `railway_incidents.py:75-93`; `experiment.py:149-245` | Incident/map subset passed; direct baseline only | Closures are simulated; no real reliability or operational schedule model. |

### 5. Visualization and user experience

| Requirement | Official source | Status | Evidence in code | Test evidence | Gap or risk |
| --- | --- | --- | --- | --- | --- |
| Configure routes/budget/penalty/p/shots/restarts/backend and run | PG 3–4 (communication/experience option) | IMPLEMENTED BUT NOT TESTED | `app.py:44-73`; `experiment_ui.py:114-150` | Direct API run and focused UI helper tests; full app startup did not complete in AppTest | Seed/tolerance/transpiler level are internal, not visible controls; live widget journey needs rehearsal. |
| Geographic Romanian map and result-specific edges | PG 1; Slides 1–2 | IMPLEMENTED AND VERIFIED | `incident_ui.py:14-55,98-120`; `experiment_ui.py:39-50,154-163` | Map tests in 28-test subset pass | City coordinates real; edges straight, fictional; online tiles need internet. |
| Switch ideal/noisy results without retraining | PG 2–3 | IMPLEMENTED BUT NOT TESTED | `experiment_ui.py:158-170` | Counts from both backends executed; complete UI switch journey not completed | Rehearse before presenting. |
| Visualize infeasible QUBO minimum in main UI | PG 2–3 | PARTIALLY IMPLEMENTED | `reporting.py:13-40` has technical-report QUBO map; `experiment_ui.py:154-165` shows feasible recommendation | Direct report generated | Main presentation page does not offer an explicit infeasible-plan map switch. |
| Progress, stale-result handling and restart | PG 4 (communication) | PARTIALLY IMPLEMENTED | `experiment_ui.py:133-153`; `simulation_history.py:62-76` | History/UI unit tests pass; full workflow unverified | Only a synchronous status spinner; no optimizer-progress stream. |

### 6. Experimental evidence

| Requirement | Official source | Status | Evidence in code | Test evidence | Gap or risk |
| --- | --- | --- | --- | --- | --- |
| Feasibility, optimal-feasible, model-minimum and score statistics | PG 3; Lab 34–35 | IMPLEMENTED AND VERIFIED | `experiment.py:108-134,229-260`; `analysis_views.py:50-77` | Auditor counts and tie tests | Mean true score includes invalid plans; state this on slides. |
| Exact statevector versus finite-shot estimates | PG 2–3 | IMPLEMENTED AND VERIFIED | `quantum_optimizer.py:407-438`; `experiment.py:231-238` | Auditor run and targeted tests | Main UI does not show the full statistical table. |
| Convergence and circuit resources | PG 3 | IMPLEMENTED AND VERIFIED | `quantum_optimizer.py:363-440`; `reporting.py:48-100` | Auditor run/archived p comparison | Optimizer budget exhausted; compiled resources are simulator-target values. |
| Multiple seeds for stochastic extension | PG 3 (at least three) | PARTIALLY IMPLEMENTED | Configurable seed in `experiment.py:28-41`; no repository multi-seed penalty report | Auditor ran 2026/2027/2028 below | These new runs are audit evidence, not a completed team notebook study. |

### 7. Reporting and reproducibility

| Requirement | Official source | Status | Evidence in code | Test evidence | Gap or risk |
| --- | --- | --- | --- | --- | --- |
| Reproducible config, versions, counts and results | PG 3–4 | IMPLEMENTED AND VERIFIED | `experiment.py:262-278`; `simulation_history.py:12-45` | JSON API result and history tests | Local SQLite is gitignored; archive selected public result JSON separately. |
| HTML report | PG 4 (relevant visuals) | IMPLEMENTED AND VERIFIED | `reporting.py:179-187` | Auditor generated 383,884-character HTML with embedded chart images | API only; no HTML export button on main page. |
| PDF report, charts/maps and same frozen run | PG 4 (relevant visuals) | IMPLEMENTED AND VERIFIED | `reporting.py:190-272`; `experiment_ui.py:167-172` | Auditor generated/read/rendered 3-page PDF; focused UI PDF test passes | Focused UI PDF omits detailed probability/model tables contained in full technical API report. |
| A coherent completed notebook submission | PG 4 | PARTIALLY IMPLEMENTED | `Quantum_Railways_Labb.ipynb` cells 4/22/29/30/36/37/39 | Saved cell outputs inspected | 19-route budget-15 results coexist with prose about 5-route budget 7 and a noisy run skipped by current flags. |
| Official submission template | PG 4 | MISSING | No `SUBMISSION_TEMPLATE.md` in supplied materials or repository | File inventory | Use guide's listed structure; do not claim the template was followed. |

### 8. Optional advanced features

| Requirement | Official source | Status | Evidence in code | Test evidence | Gap or risk |
| --- | --- | --- | --- | --- | --- |
| Full D/E derivation | PG 1–2 (optional) | IMPLEMENTED BUT NOT TESTED | Team notebook cells 14/16 include formulas; `MATHEMATICAL_DEEP_DIVE=False` | Conversion tested, derivation narrative not reviewed pedagogically | Optional; can show one coefficient on slide. |
| Real IBM QPU results | PG 2 (optional) | UNKNOWN / INSUFFICIENT EVIDENCE | `Quantum_Railways_Labb.py` and notebook contain guarded IBM path; `docs/RUN_NOTEBOOK_SCRIPT.md` claims connection check | No hardware job, counts or ID verified; credentials not accessed | Do not call local synthetic results hardware data. |
| Destination-ticket/connectivity objective | PG 1/3 (optional); Slides 2–3 | MISSING | `experiment.py:80-88` rejects other objectives; `quantum_optimizer.py:128-140` is additive | Code inspected | Do not say the app optimizes destination connectivity. |
| Slack-variable inequality QUBO or alternative mixer | PG 3 (optional examples) | MISSING | `README_QAOA.md` describes slack only as a proposal; `quantum_optimizer.py:193-197` uses RX | Code inspected | Not needed for core; would address central model limitation. |

## Quantum correctness details

Decision `x_i` controls input route position `i`, regardless of physical ID; Qiskit prints `x_0` at the right (`quantum_optimizer.py:105-113`, `railway_data.py:38`). Demo decision order is IDs `[0,1,2,6,8]` with `(cost,value)` pairs `[(2,4),(3,6),(2,5),(4,9),(4,7)]`. Exact enumeration gives 32 plans, 16 feasible, and two score-15/cost-7 optima. Sabina's canonical plan is key `01010` (IDs 1,6), while the independent DP can choose key `00111` (IDs 0,1,2); both are genuine ties. No comparison should silently treat one tied key as the only optimum.

For `B=7`, `λ=.7`, the implemented QUBO is `offset=34.3`, `a=(-20.8,-29.1,-21.8,-37,-35)` and strictly upper-triangular `b_ij=1.4 c_i c_j`. Substituting `x_i=(1-Z_i)/2` gives `C=-6.75`, `h=(1.3,1.95,1.8,3.1,2.1)`, `J_ij=b_ij/4`. Direct, QUBO and Ising energies agreed to float tolerance for **all 32** plans in this audit. `01101` selects IDs 0,2,6: cost 8, score 18, energy `-17.3`, invalid. Thus energy minimization and feasibility are separate questions. At `λ=4`, the exact model minimum becomes `00111`, score 15/cost 7/energy `-15`; this fixes this particular minimum but does not turn the squared term into a general inequality encoding.

`parameterized_qaoa` prepares `H^{⊗n}`, then repeats RZ/RZZ Cost and RX Mixer layers (`quantum_optimizer.py:179-220`). The Cost angles are `2γ h_i/scale` and `2γ J_ij/scale`, so the unitary is `exp(-iγ H_C/scale)` up to the omitted constant's global phase. The independent `[γ_0,β_0,…]` parameters are bound by identity (`:357-407`). COBYLA minimizes exact ideal `Statevector` probability-weighted model energy; final Aer shots use the selected optimized angles. A fresh default-training run at seed 2026 had initial/final expected energies `-1.144814/-6.750649`, `γ=1.6096795943`, `β=3.1372090827`, 31 recorded evaluations (30 SciPy plus explicit initial), and `success=False` because the evaluation budget was exhausted. Lower energy is not a proof of optimum or better feasibility.

The final circuit measures each logical qubit into the named `plan` register, and `decode_key` reverses printed keys to decision order (`quantum_optimizer.py:105-113,220-224,268-321`). `experiment.py:108-134,226-260` keeps five distinct quantities: exact model minimum, exact ideal expected energy, most frequent sampled key, best **feasible observed** sample, and exact classical optimum. It sums all tied feasible-optimal counts. Ideal training and noisy final sampling use the same angles; the noisy device is a seeded `GenericBackendV2` with Aer density matrix, not a current IBM calibration (`quantum_optimizer.py:268-296`). App “compare” allows at most 8 active routes; ideal UI allows at most 10 (`experiment.py:141-158`).

## Executions and numerical evidence

1. Initial `pytest -q` attempt crashed in Windows during Aer import (`0xc0000008`); retry hit sandbox temp-directory permissions (`99 errors` at fixture setup, no useful assertions). With `TEMP`, `TMP`, and `--basetemp` inside the workspace, focused suites passed: **46 tests + 110 subtests** (quantum/classical/notebook support), **28 tests** (map/incidents/scenarios/depth; 2 UI tests deselected), **4 tests** (presentation data/history/PDF; 1 full UI test deselected), and **16 tests** (algorithm/integration/notebook; 2 full UI tests deselected). Across disjoint subsets: **94 tests passed, five full Streamlit journey tests unverified**. The complete suite stalled after its first four tests at `test_streamlit_parameters_map_switch_and_matching_exports`; it was interrupted. A separate `AppTest.from_file('app.py').run()` startup also stalled and was interrupted. This is an execution limitation, not evidence that those tests pass or fail or that the app opens reliably on the demo machine.
2. Fresh 5-route default-training `run_experiment` at `B=7`, `λ=.7`, `p=1`, seed 2026, **30** COBYLA SciPy evaluations, 2048 ideal shots: initial/final exact expected energy `-1.144814/-6.750649`, `γ=1.6096795943`, `β=3.1372090827`, optimizer not converged; best feasible sampled key `00111` score 15; most frequent key `01100`; P(feasible) `1076/2048=0.525391`, P(any tied feasible optimum) `152/2048=0.074219`, P(model minimum) `60/2048=0.029297`, mean true score including invalid outcomes `15.295898`. Exact ideal P(feasible) `0.497584`, P(any feasible optimum) `0.063045`, P(model minimum) `0.031882`. Compiled ideal depth 10, ten two-qubit gates. This machine reported total runtime `0.208 s` (reference `0.0048 s`, training `0.0416 s`, sampling `0.1544 s`); these local simulator timings are environment-dependent and are not hardware timings. Versions: Qiskit 2.1.0, Aer 0.17.0, NumPy 2.2.6, SciPy 1.15.3, Streamlit 1.67.0, Plotly 6.9.0.
3. Separate short 5-route `run_experiment` at the same `B/λ/p/seed`, **8** COBYLA SciPy evaluations, 256 shots, mode `compare`: exact classical score 15/cost 7 (two ties); QUBO min `-17.3` invalid; initial/final expected energy `-1.144814/-6.627569`, `γ=1.6587668`, `β=3.1928209`, optimizer not converged. Ideal: 131/256 feasible (`0.511719`), 14/256 tied-optimal (`0.054688`), 1/256 model minimum. Noisy synthetic: 141/256 feasible (`0.550781`), 19/256 tied-optimal (`0.074219`), 6/256 model minimum. Those differences are finite-shot observations and do not isolate noise effects.
4. The short fresh result generated a self-contained HTML report (embedded PNG charts) and a **3-page** focused PDF. PDF extraction and visual inspection confirmed both solution pages, maps, score 15, histograms and a configuration/explanation page. Its matplotlib PDF text extraction drops some Romanian diacritics even though visual rendering displayed them; do not use raw extracted text as a fidelity check. The focused PDF and technical HTML have different detail levels. Temporary reports were audit artifacts, not repository deliverables.
5. Auditor-run paired penalty study: same five routes, `B=7`, `p=1`, 2048 ideal shots, 30 SciPy evaluations, one restart, seeds 2026/2027/2028. All six optimizers exhausted their evaluation budget. Values are from actual executions; energies across different penalties are **not** a common objective scale.

| λ | seed | model minimum feasible? | exact ideal P(feasible) | sampled P(feasible) | sampled P(any feasible optimum) | best feasible observed |
| ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 0.7 | 2026 | no | 0.497584 | 0.525391 | 0.074219 | 15 |
| 0.7 | 2027 | no | 0.637446 | 0.620117 | 0.113770 | 15 |
| 0.7 | 2028 | no | 0.472096 | 0.474121 | 0.020020 | 15 |
| 4.0 | 2026 | yes | 0.488762 | 0.510742 | 0.025391 | 15 |
| 4.0 | 2027 | yes | 0.460008 | 0.454590 | 0.109863 | 15 |
| 4.0 | 2028 | yes | 0.639583 | 0.654297 | 0.072266 | 15 |

The higher penalty fixes the *exact model minimum on this instance* but does not consistently raise the measured feasible rate: it falls at seeds 2026/2027 and rises at 2028. It also does not consistently raise P(any feasible optimum). Three seeds are an initial check, not a robust uncertainty estimate. The notebook's cell-37 question is therefore a defensible **negative/mixed result**, if presented with this auditor-generated table and configuration.

6. Tracked archived 19-route comparison (`validation/p_comparison_seed2026/comparison.json`, `raport.md`): at budget 20, `λ=.7`, seed 2026, 4096 shots and 30 SciPy evaluations per depth, p=1 observed score 46/cost 20, 1349/4096 feasible, 1/4096 optimal; p=2 observed 43/cost 20, 238/4096 feasible, 0 optimal. Both report `converged=false`; p=2 has 342 two-qubit gates versus 171. This is one archived run, not a general proof that p=1 is better. The current notebook has a separate **local, gitignored** budget-15 comparison in `output/qaoa_depths/notebook_20261107_235701/comparison.json`: both best scores 35, with sampled feasible rates `0.41919` (p=1) and `0.16968` (p=2). It was inspected, not rerun; this file will not be in a clean clone.

## UI, map, statistics and report audit

The main UI exposes budget, route selection, penalty, shots, depth, COBYLA evaluation budget, restarts and ideal/compare selection. Each visible control enters `SimulationConfig` and the run call (`experiment_ui.py:117-136`). Seed, tolerance and transpilation level are stored internal settings and are not user controls (`:127-130`). The status is synchronous (`:133-150`), with complete/failed feedback but no per-evaluation progress. A changed visible scenario hides old results (`:151-155`); loaded snapshots restore controls (`simulation_history.py:62-76`). The fingerprint excludes the internal-settings dictionary, so a programmatic internal-setting change without changing visible controls may leave an old result visible; the main UI has no control for this, but the contract is weaker than the README's broad stale-data claim.

The Plotly map uses geographic city coordinates, a CARTO/OSM basemap, and straight fictional edges (`incident_ui.py:14-55`). Selected solution maps filter to actual selected IDs and their endpoint cities (`:98-120`); classical and chosen quantum results therefore reflect experiment outputs. Closure/maintenance removes decisions from both algorithms; explicit `construction_cost_delta` changes objective cost; delay, capacity and operating cost remain metadata (`railway_incidents.py:75-93`). The main page offers a simple simulated closure, while richer incident controls are in other helpers/pages (`incident_ui.py:79-95,140-205`). The interface does not offer a main-page invalid-model-minimum switch. An online basemap depends on tile access; reports use schematic plots without external tiles.

`experiment.py:108-134,229-260` computes P(feasible), P(any tied feasible optimum), P(model minimum), over-budget rate, mean true score, sampled expected energy, exact ideal probabilities, convergence history and resources. The mean score includes infeasible plans. The focused presentation page displays only score/energy/cost and per-plan histograms (`experiment_ui.py:39-50,154-165`); deeper metrics require technical report/API/JSON. `analysis_views.py:7-48` displays actual `counts/shots` for quantum and a labeled deterministic P=1 classical choice, not fabricated classical shots. At most 64 plotted plan bars remain unrenormalized. Neither high best-sample score nor modal key alone characterizes the distribution.

`html_report` and full `pdf_report` contain the technical comparison, coefficients, statistics, maps/charts and versions (`reporting.py:102-204`). The UI calls `pdf_report(result,presentation_backend=...)`, a shorter three-page presentation report (`:207-272`), and exposes **PDF only** (`experiment_ui.py:167-172`). The focused PDF mirrors the selected backend and frozen solution maps/histograms, but omits the full technical probability/coefficients tables. HTML is implemented as an API without a download button. No real hardware data is included.

## Original contribution and presentation claim ranking

1. **Strongest scientific result: modeling diagnosis and penalty sensitivity.** The team exposes the weak squared-penalty failure; the working notebook asks a concrete `λ=.7→4` question. The audit's three-seed study now supplies a reproducible preliminary answer: model feasibility changes, QAOA sampled feasibility is mixed. This is an auditor-run result, not yet an integrated team notebook experiment. It should be the proposed core research story only after the team adds its evidence and correct interpretation to the final submission.
2. **Depth comparison on 19 routes.** Implemented p=1/p=2 experiments with tracked JSON and circuit resources are original beyond the supplied five-route notebook. Evidence supports only the stated seed/budget, not a universal depth conclusion. The current 19-route notebook's budget-15 local result is additional but gitignored.
3. **Incident-aware what-if planning.** Simulated closures rebuild both models and show before/after plans; this is a meaningful application extension with tests, though no real incident feed or reliability objective is modeled.
4. **Classical explainability and interactive presentation.** Sabina's tie-aware enumeration, alternatives/Pareto/budget profile and synchronized maps/reports are genuine engineering contributions. The UI alone should not be marketed as a new quantum method.

No improved inequality QUBO, destination-ticket optimization, new mixer, verified real-QPU result or quantum speedup exists in the audited application.

## Bugs, limitations and top priorities

1. **Reconcile the notebook before submission.** Its current cell 4 selects 19 routes and prompts for budget; the saved execution used budget 15. Cell 22 saved outputs show score 35 and optimizer budget exhaustion; cells 29/30 skip noisy sampling; cell 36 still describes five routes/budget 7, different energy/percentages, and a noisy experiment. Split baseline from extension or replace prose with numbers generated from the exact final run. Preserve the existing uncommitted work; review it with the team.
2. **Make the research claim match evidence.** Present the penalty study as “model minimum becomes feasible, but QAOA feasible sampling did not improve consistently across three seeds.” Save run-level JSON/table with training settings and uncertainty if chosen for the final deck. Do not compare absolute expected energies across different λ values as a performance gain.
3. **Rehearse the full Streamlit journey.** Five end-to-end UI tests were unverified here. Open the app, run the default five-route ideal and compare modes, toggle incident, switch results, restore history, export PDF, and confirm no stale result. Keep a frozen JSON/PDF backup for demo.
4. **Expose the decisive metrics and failure visibly.** For a scientific slide/demo show model minimum (invalid), exact classical ties, best feasible sample, modal sample, P(feasible), P(optimal feasible), P(model minimum), expected energy and optimizer status. Currently several are hidden in JSON/report APIs.
5. **Package reproducible evidence.** The official template is absent; use guide p. 4 structure. Track or attach the selected run's config, seed, counts, versions, convergence and charts. Avoid depending on gitignored `output/` or local SQLite for a clean-machine presentation.

Secondary limits: only additive reward and COBYLA are accepted (`experiment.py:80-88,158-166`); no true ticket/connectivity objective; simulation grows exponentially; default 30-evaluation optimizations often do not converge; noisy backend is synthetic; basemap tiles are online; the Live Network timeline is simulated. Live demonstration readiness is **conditional**: algorithm/report APIs work, but the actual full UI flow needs an on-machine rehearsal and backup.
