"""Command-line, plotting and IBM adapters for the exported railway notebook."""
import argparse
from datetime import datetime, timezone
from getpass import getpass
from importlib import metadata
import json
import os
from pathlib import Path
import sys
import warnings


ROOT = Path(__file__).resolve().parent


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=(
        "Quantum Railways: notebook complet, 19 rute / 14 orase, buget 20; QAOA p=1 si p=2."))
    parser.add_argument('--budget', type=int, default=20)
    parser.add_argument('--penalty', type=float, default=0.7)
    parser.add_argument('--maxiter', type=int, default=30)
    parser.add_argument('--restarts', type=int, default=1)
    parser.add_argument('--shots', type=int, default=4096)
    parser.add_argument('--seed', type=int, default=2026)
    parser.add_argument('--output', type=Path, default=None)
    parser.add_argument('--dry-run', action='store_true', help='verifica doar configuratia, fara antrenare sau IBM')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--ibm', action='store_true', help='antreneaza local, apoi executa circuitul final pe IBM')
    mode.add_argument('--check-ibm', action='store_true', help='verifica accesul IBM, fara a trimite un job')
    parser.add_argument('--backend', default=None, help='din configuratia locala; auto alege backendul cel mai liber')
    parser.add_argument('--qpu-depth', type=int, choices=(1, 2), default=1)
    parser.add_argument('--credentials', type=Path, default=ROOT / 'ibm_credentials.local.json')
    parser.add_argument('--recover-job', default='', help='citeste un job existent; necesita --ibm si nu trimite alt job')
    args = parser.parse_args(argv)
    if args.budget < 0 or args.maxiter < 6 or args.restarts < 1 or args.shots < 1:
        parser.error('Buget >= 0, maxiter >= 6, restarts >= 1 si shots >= 1 sunt necesare.')
    if not 0 <= args.penalty < float('inf'):
        parser.error('Penalizarea trebuie sa fie finita si >= 0.')
    if args.recover_job and not args.ibm:
        parser.error('--recover-job necesita --ibm')
    if args.output is None:
        args.output = ROOT / 'output' / ('script_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    args.output = args.output.resolve()
    return args


def check_environment(pins):
    """Report versions without installing or changing the user's environment."""
    actual = {}
    for name, tested in pins.items():
        try:
            actual[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            raise RuntimeError('Lipsesc dependente. Ruleaza: python -m pip install -r requirements.txt') from None
        if actual[name] != tested:
            warnings.warn(f'{name}: instalat {actual[name]}, notebook testat cu {tested}', stacklevel=2)
    return actual


def ibm_types():
    versions = {}
    for package in ('qiskit', 'qiskit-ibm-runtime'):
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = 'not installed'
    remedy = (
        f"Kernel Python: {sys.executable}\n"
        f"qiskit={versions['qiskit']}; qiskit-ibm-runtime={versions['qiskit-ibm-runtime']}.\n"
        "Selecteaza kernelul 'Quantum Railways (IBM)' din notebook. "
        "Pentru alt mediu, ruleaza intr-o celula: %pip install -r requirements-ibm.txt\n"
        "Apoi Restart Kernel si Run All. Clientul IBM necesita Qiskit >= 2.3 si "
        "qiskit-ibm-runtime >= 0.50."
    )
    try:
        version = versions['qiskit-ibm-runtime']
        if tuple(map(int, version.split('.')[:2])) < (0, 50):
            raise ImportError
        if tuple(map(int, versions['qiskit'].split('.')[:2])) < (2, 3):
            raise ImportError
        from qiskit_ibm_runtime import QiskitRuntimeService
        from qiskit_ibm_runtime.executor_sampler import Sampler
    except (ImportError, metadata.PackageNotFoundError, ValueError):
        raise RuntimeError('Mediul kernelului nu poate incarca clientul IBM.\n' + remedy) from None
    return QiskitRuntimeService, Sampler


def connect_ibm(args):
    """Read existing local credentials; never echo, log or persist the token."""
    Service, _ = ibm_types()
    config = {}
    if args.credentials.is_file():
        try:
            config = json.loads(args.credentials.read_text(encoding='utf-8-sig'))
            if not isinstance(config, dict):
                raise ValueError
        except (ValueError, OSError):
            raise RuntimeError('Configuratia IBM locala trebuie sa fie un obiect JSON valid.') from None
    token = os.getenv('IBM_QUANTUM_TOKEN') or os.getenv('QISKIT_IBM_TOKEN') or config.get('token')
    instance = (os.getenv('IBM_QUANTUM_INSTANCE') or os.getenv('QISKIT_IBM_INSTANCE')
                or config.get('instance'))
    saved = not token and (Path.home() / '.qiskit' / 'qiskit-ibm.json').is_file()
    if not saved:
        if not token:
            if not sys.stdin.isatty():
                raise RuntimeError('Lipseste cheia IBM. Configureaza ibm_credentials.local.json sau IBM_QUANTUM_TOKEN.')
            token = getpass('IBM Cloud API key (ascunsa): ').strip()
        if not instance:
            if not sys.stdin.isatty():
                raise RuntimeError('Lipseste CRN-ul. Configureaza instance in fisierul local sau IBM_QUANTUM_INSTANCE.')
            instance = input('IBM instance CRN: ').strip()
        if not token or not instance:
            raise RuntimeError('Cheia IBM si CRN-ul nu pot fi goale.')
    name = args.backend if args.backend is not None else config.get('backend', 'ibm_aachen')
    try:
        kwargs = dict(channel='ibm_quantum_platform')
        if token:
            kwargs['token'] = token
        if instance:
            kwargs['instance'] = instance
        service = Service(**kwargs)
        if name == 'auto':
            backend = service.least_busy(operational=True, simulator=False, min_num_qubits=19)
        else:
            backend = service.backend(name)
        if backend.num_qubits < 19 or not backend.status().operational:
            raise ValueError
        return service, backend
    except Exception as error:
        if 'does not have access to the instance' in str(error):
            raise RuntimeError('Cheia API IBM nu are acces la CRN-ul configurat. '
                               'Foloseste cheia si CRN-ul aceleiasi instante. Niciun job nu a fost trimis.') from None
        raise RuntimeError('Conectarea IBM a esuat. Verifica cheia, CRN-ul si accesul la backend. Niciun job nu a fost trimis.') from None
    finally:
        token = None


def save_job_record(output, job_id, backend, depth, shots, recovered=False):
    record = dict(job_id=job_id, backend=backend, qaoa_depth=depth, shots=shots,
                  recovered=recovered, timestamp=datetime.now(timezone.utc).isoformat())
    (output / 'ibm_job.json').write_text(json.dumps(record, indent=2), encoding='utf-8')


def install_display(output):
    """Replace notebook rich display by terminal tables and persistent PNG files."""
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    counter = 0

    def save_figure(figure):
        nonlocal counter
        counter += 1
        figure.savefig(output / f'figure_{counter:02d}.png', dpi=150, bbox_inches='tight')

    def display(value):
        if isinstance(value, Figure):
            save_figure(value)
        else:
            print(value)

    def show(*args, **kwargs):
        for number in plt.get_fignums():
            save_figure(plt.figure(number))
        plt.close('all')

    plt.show = show
    return display, str
