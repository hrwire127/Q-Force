"""Execute a notebook's bound circuit with the isolated IBM SDK environment.

Only QPY circuits and plain JSON results cross the interpreter boundary. The
notebook may keep its local Qiskit 2.1 kernel; credentials stay in the local file.
"""
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent


def _write_json(path, data):
    temporary = path.with_name(f'.{path.name}.{os.getpid()}.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def ibm_python():
    override = os.environ.get('QUANTUM_RAILWAYS_IBM_PYTHON')
    candidate = Path(override) if override else ROOT / '.venv-ibm' / (
        'Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if candidate.is_file():
        return candidate.resolve()
    from railway_script_support import ibm_types
    ibm_types()  # Gives the actionable installation message if this kernel cannot run IBM.
    return Path(sys.executable)


def run_notebook_qpu(circuit, shots=4096, backend_name=None, output_dir=None):
    """Submit once, or recover the matching existing job; return actual counts.

    Re-running the same cell reuses its job record. No simulator or fabricated
    result is substituted for a QPU failure.
    """
    from qiskit import qpy
    if circuit.parameters:
        raise ValueError('Bind all QAOA angles before IBM execution.')
    if len(circuit.cregs) != 1 or circuit.cregs[0].name != 'plan':
        raise ValueError('The circuit must measure into the named register plan.')
    if isinstance(shots, bool) or not isinstance(shots, int) or shots < 1:
        raise ValueError('shots must be a positive integer')
    canonical = circuit.copy()
    canonical.name = 'railway_final'
    payload = io.BytesIO()
    qpy.dump(canonical, payload)
    data = payload.getvalue()
    identity = dict(shots=shots, backend=backend_name, bits=circuit.cregs[0].size)
    fingerprint = hashlib.sha256(data + json.dumps(identity, sort_keys=True).encode()).hexdigest()
    output = Path(output_dir).resolve() if output_dir else ROOT / 'output' / 'ibm_notebook' / fingerprint[:20]
    output.mkdir(parents=True, exist_ok=True)
    request = dict(identity, fingerprint=fingerprint)
    record_path = output / 'job.json'
    if record_path.is_file():
        record = json.loads(record_path.read_text(encoding='utf-8'))
        if record.get('fingerprint') != fingerprint:
            raise RuntimeError('Output directory belongs to a different circuit. Choose another directory.')
    (output / 'circuit.qpy').write_bytes(data)
    _write_json(output / 'request.json', request)
    return _run_worker(output)


def recover_notebook_qpu(job_id, shots=4096, bits=19, backend_name=None):
    """Read a known job through the IBM environment; never submit a new circuit."""
    if not job_id or not all(c.isalnum() or c in '-_' for c in job_id):
        raise ValueError('Invalid IBM job ID')
    output = ROOT / 'output' / 'ibm_notebook' / ('recovered_' + job_id)
    output.mkdir(parents=True, exist_ok=True)
    request = dict(shots=shots, bits=bits, backend=backend_name,
                   fingerprint=hashlib.sha256(job_id.encode()).hexdigest())
    _write_json(output / 'request.json', request)
    if not (output / 'job.json').exists():
        _write_json(output / 'job.json', dict(request, job_id=job_id, status='RECOVERING'))
    return _run_worker(output)


def _run_worker(output):
    record_path = output / 'job.json'
    command = [str(ibm_python()), str(Path(__file__).resolve()), '--worker', str(output)]
    environment = dict(os.environ, PYTHONIOENCODING='utf-8')
    print('IBM execution environment:', command[0], flush=True)
    with subprocess.Popen(command, cwd=ROOT, env=environment, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, encoding='utf-8') as process:
        for line in process.stdout:
            print(line.rstrip(), flush=True)
        code = process.wait()
    if code:
        raise RuntimeError(f'Executia IBM nu s-a incheiat. Vezi mesajul de mai sus si {record_path}. '
                           'Daca exista un Job ID, reluarea celulei recupereaza acelasi job.')
    record = json.loads(record_path.read_text(encoding='utf-8'))
    if record.get('status') != 'DONE' or not record.get('counts'):
        raise RuntimeError('IBM did not return a completed measurement result.')
    return record


def _collect_counts(result, bits, shots):
    measured = getattr(result[0].data, 'plan', None)
    if measured is None or measured.num_bits != bits:
        raise RuntimeError('IBM result does not contain the expected plan register.')
    counts = dict(measured.get_counts())
    if sum(counts.values()) != shots or any(
        len(key) != bits or set(key) - {'0', '1'} or value < 0
        for key, value in counts.items()
    ):
        raise RuntimeError('IBM measurement width or shot count differs from the request.')
    return counts


def _execute_job(request, output, service, backend, sampler_type, poll_interval=15):
    path = output / 'job.json'
    record = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None
    if record is not None:
        if record.get('fingerprint') != request['fingerprint']:
            raise RuntimeError('Job record belongs to another circuit.')
        job = service.job(record['job_id'])
        record['backend'] = job.backend().name
        print('Recovering existing IBM job:', record['job_id'], flush=True)
    else:
        from qiskit import qpy
        from qiskit.transpiler import generate_preset_pass_manager
        with (output / 'circuit.qpy').open('rb') as handle:
            circuit = qpy.load(handle)[0]
        isa = generate_preset_pass_manager(backend=backend, optimization_level=1,
                                          seed_transpiler=2026).run(circuit)
        with (output / 'compiled.qpy').open('wb') as handle:
            qpy.dump(isa, handle)
        lock = output / 'submission.lock'
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise RuntimeError('A submission is already in progress. Check IBM jobs before retrying.') from None
        os.close(descriptor)
        try:
            if path.exists():
                # Another notebook process may have finished submission while this
                # process was compiling. Recheck under the lock before submitting.
                record = json.loads(path.read_text(encoding='utf-8'))
                if record.get('fingerprint') != request['fingerprint']:
                    raise RuntimeError('Job record belongs to another circuit.')
                job = service.job(record['job_id'])
            else:
                job = sampler_type(mode=backend).run([isa], shots=request['shots'])
                record = dict(request, job_id=job.job_id(), backend=backend.name, status='SUBMITTED',
                              submitted_utc=datetime.now(timezone.utc).isoformat(),
                              compiled_depth=isa.depth(), compiled_qubits=isa.num_qubits,
                              logical_qubits=circuit.num_qubits)
                # Save BEFORE polling/results, so retries cannot create another job.
                _write_json(path, record)
        except Exception:
            # Keep the lock: a network failure during submission can leave an accepted job.
            raise
        else:
            lock.unlink()
        print('Submitted IBM job:', record['job_id'], '| backend:', backend.name, flush=True)
    previous = None
    last_print = 0
    while True:
        status = str(job.status()).upper()
        if status != previous or time.monotonic() - last_print >= 60:
            print('IBM job', record['job_id'], '| status:', status, flush=True)
            last_print = time.monotonic()
        record['status'] = status
        _write_json(path, record)
        if status == 'DONE':
            break
        if status in ('ERROR', 'CANCELLED'):
            raise RuntimeError('IBM job ended with status '+status+'. Inspect job '+record['job_id']+' in IBM Quantum.')
        previous = status
        time.sleep(poll_interval)
    record['counts'] = _collect_counts(job.result(), request['bits'], request['shots'])
    record['completed_utc'] = datetime.now(timezone.utc).isoformat()
    _write_json(path, record)
    print('Real QPU result:', sum(record['counts'].values()), 'shots,', request['bits'], 'bits.', flush=True)
    return record


def worker(output):
    from railway_script_support import connect_ibm, ibm_types, parse_args
    request = json.loads((output / 'request.json').read_text(encoding='utf-8'))
    arguments = ['--check-ibm', '--credentials', str(ROOT / 'ibm_credentials.local.json')]
    if request.get('backend'):
        arguments += ['--backend', request['backend']]
    service, backend = connect_ibm(parse_args(arguments))
    _, sampler_type = ibm_types()
    return _execute_job(request, output, service, backend, sampler_type)


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] != '--worker':
        raise SystemExit('Use run_notebook_qpu() from the notebook.')
    try:
        worker(Path(sys.argv[2]).resolve())
    except Exception as error:
        # The service wrapper already redacts connection errors. Also redact local
        # credential strings from SDK errors during submission/result retrieval.
        message = str(error)
        config_path = ROOT / 'ibm_credentials.local.json'
        if config_path.is_file():
            config = json.loads(config_path.read_text(encoding='utf-8-sig'))
            for key in ('token', 'instance'):
                if config.get(key):
                    message = message.replace(config[key], '<masked>')
        print(type(error).__name__ + ': ' + message, file=sys.stderr, flush=True)
        raise SystemExit(1) from None
