# Q-Force — Quantum Railways final presentation

## Deliverables

* [`Q-Force_Quantum_Railways_Final.pptx`](Q-Force_Quantum_Railways_Final.pptx) — 19 editable widescreen slides: 15 main slides plus four technical/evidence appendix slides, with speaker notes.
* [`Q-Force_Quantum_Railways_Final.pdf`](Q-Force_Quantum_Railways_Final.pdf) — matching 19-page PDF.
* [`EXPERIMENT_EVIDENCE.md`](EXPERIMENT_EVIDENCE.md) — numerical provenance and interpretation.
* [`IBM_QPU_STATUS.md`](IBM_QPU_STATUS.md) — read-only job check and missing hardware metadata.
* [`REAL_ROMANIA_FEASIBILITY.md`](REAL_ROMANIA_FEASIBILITY.md) — official-source research roadmap.

The deck uses editable PowerPoint text, shapes, bars and diagrams. Genuine app screenshots are embedded as images on slides 6 and 19. Standalone source-driven plots are in [`charts/`](charts/) and can be regenerated with `..\QuissKit\.venv\Scripts\python.exe presentation\make_charts.py`. The PDF is generated from the slide render PNGs, preserving the approved visual layout. It is a presentation copy, not an editable version.

## Rebuild

From the repository root:

```powershell
& presentation\rebuild.ps1
```

The script invokes the bundled Codex Artifact Tool to regenerate slide images and PowerPoint, validates the PPTX package/layout/import, then creates the PDF. Source is [`build_presentation.mjs`](build_presentation.mjs) and [`export_pdf.py`](export_pdf.py). It reads frozen JSON in [`experiments/`](experiments/) and [`source_data/`](source_data/). A local private `.presentation-build/` directory holds previews and validation artifacts. Update the bundled runtime path in `rebuild.ps1` if the Codex runtime version changes.

To rerun local experiment data:

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
& ..\QuissKit\.venv\Scripts\python.exe presentation\run_experiments.py
& presentation\rebuild.ps1
```

To check the recorded IBM job **without submitting a new job** and rebuild:

```powershell
& .\.venv-ibm\Scripts\python.exe presentation\refresh_qpu_results.py --rebuild
```

The refresh script stores status in `source_data/ibm_refresh_status.json`. It keeps retrieved counts separate until scenario, bound-circuit and angle metadata can be verified. No background monitor was created.

## Evidence boundaries

The main penalty chart is a three-seed, five-route local replay. The archived 19-route depth comparison is isolated in the appendix. Real QPU counts are not verified. The current app's costs, scores and direct rail edges are fictional. CFR and ERA sources inform only the future research slide. See the evidence, IBM and feasibility documents for exact conditions and source links.
