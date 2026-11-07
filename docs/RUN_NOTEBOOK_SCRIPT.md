# Notebook export: Quantum_Railways_Labb.py

Run from the repository directory on `zus`:

```powershell
python Quantum_Railways_Labb.py
```

The script contains every notebook code cell, including QUBO/Ising checks,
complete classical enumeration, QAOA training at p=1 and p=2, maps, histograms,
backend/compilation helpers and job recovery. Like the notebook, it imports
`notebook_support.py`, `qaoa_experiments.py` and `quantum_optimizer.py` from this
repository. It does not require Jupyter, Colab or IPython.

The original network is preserved: **19 routes, 14 cities, 19 logical qubits**.
The defaults are budget **20**, penalty **0.7**, seed **2026**, **4096 shots**,
COBYLA **30 iterations**, **1 restart**, transpilation level **1**, baseline
depth **p=1**, with a separate **p=2** comparison. Optional noisy/extension/deep
dive sections retain their disabled notebook defaults. Training is local; real
IBM execution requires `--ibm`. Statevector training for 19 qubits can take minutes.

```powershell
python Quantum_Railways_Labb.py --dry-run
python Quantum_Railways_Labb.py --help
```

Every run saves terminal-compatible tables, PNG maps/histograms/circuit diagrams,
`scenario.json`, `railway_results.json`, and the separate depth-comparison results
under `output/script_<timestamp>/`. Plots are saved rather than opened in UI windows.
Package versions are reported; the script does not install packages automatically.
The notebook also uses the shared IBM environment check and local credentials.

## Notebook kernel

The notebook must use **Quantum Railways (IBM)** to run the IBM cells. This
kernel uses `.venv-ibm`, which contains the compatible IBM SDK and Qiskit.
The ordinary application environment has Qiskit 2.1 and no IBM client.

The kernel is already registered on this machine. On another machine, install
`requirements-ibm.txt` and register it from the repository directory:

```powershell
.\.venv-ibm\Scripts\python.exe -m ipykernel install --user --name quantum-railways-ibm --display-name "Quantum Railways (IBM)"
```

Select that kernel, then **Restart Kernel → Run All**. The setup cell installs
missing local dependencies but preserves installed versions, so it does not
downgrade the IBM environment to Qiskit 2.1. If working in a separate hosted
notebook environment, run `%pip install -r requirements-ibm.txt` there before
restarting its kernel. The real-hardware cell submits only if
`USE_REAL_HARDWARE=True`; calling `choose_backend(True, ...)` alone verifies
the connection without submitting a job.

## IBM connection

The script reads the API key and instance CRN from the ignored local file
`ibm_credentials.local.json`. The credentials supplied in the local notebook
during this task have been copied there without adding them to Python source.
On another machine, configure this local file or environment variables first.

The connection was verified with IBM client **0.50.1** and **ibm_marrakesh**
(156 qubits), without submitting a QPU job. The local configuration selects that
backend. The notebook's original **ibm_aachen** returned `device not found`.

Use a separate environment for the current IBM client, because it may require a
newer Qiskit than the pinned local application environment:

```powershell
python -m venv .venv-ibm
.\.venv-ibm\Scripts\python.exe -m pip install -r requirements-ibm.txt
```

If the credentials file does not exist yet, create it from the example (preserve
the existing configured file on this machine):

```powershell
Copy-Item ibm_credentials.example.json ibm_credentials.local.json
```

Edit **ibm_credentials.local.json** locally:

```json
{
  "token": "YOUR_IBM_CLOUD_API_KEY",
  "instance": "YOUR_IBM_INSTANCE_CRN",
  "backend": "auto"
}
```

This local file is ignored by Git. Alternatively, set `IBM_QUANTUM_TOKEN` and
`IBM_QUANTUM_INSTANCE` in the shell, use a saved IBM account, or enter the token
at the masked terminal prompt and the CRN at the next prompt. Environment
variables take precedence over the JSON file. Keys are never included in results.

Verify connectivity without submitting a job:

```powershell
.\.venv-ibm\Scripts\python.exe Quantum_Railways_Labb.py --check-ibm
```

Train both depths locally, then submit the optimized **p=1** circuit to IBM:

```powershell
.\.venv-ibm\Scripts\python.exe Quantum_Railways_Labb.py --ibm
```

Use `--qpu-depth 2` to submit p=2 instead. Use `--backend auto` to select an
accessible operational backend with enough qubits instead of the locally
configured backend. The service must grant access to the selected backend.

The job ID is saved immediately to `ibm_job.json`, before waiting for results.
If disconnected after submission, recover it without sending another job:

```powershell
.\.venv-ibm\Scripts\python.exe Quantum_Railways_Labb.py --ibm --recover-job YOUR_JOB_ID
```

Recovery still runs the local notebook analysis. It requires the existing job
to use the same 19-bit `plan` register and scenario; supply the original depth
and settings if they were changed. Real counts are saved as `ibm_counts.json`.

The implementation uses the current IBM client-side
[Sampler](https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/executor-sampler-sampler)
and [QiskitRuntimeService](https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service).
Local execution is validated separately from actual IBM account/QPU access.
