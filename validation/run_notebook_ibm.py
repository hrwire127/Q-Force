"""Run the full notebook in its old local kernel and verify the isolated real QPU path.

This command SUBMITS to IBM when the notebook enables USE_REAL_HARDWARE.
Use only for an explicitly authorized real QPU integration run.
"""
import copy
from datetime import datetime
import json
from pathlib import Path
from queue import Empty
import time

from jupyter_client import KernelManager


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'output' / ('notebook_ibm_verified_' + datetime.now().strftime('%Y%m%d_%H%M%S'))


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    notebook = json.loads((ROOT / 'Quantum_Railways_Labb.ipynb').read_text(encoding='utf-8'))
    for cell in notebook['cells']:
        if cell['cell_type'] == 'code':
            cell['outputs'] = []
            cell['execution_count'] = None
    manager = KernelManager(kernel_name='quantum-railways-ibm')
    # Reproduce the reported Qiskit 2.1 kernel; IBM execution must work through
    # the bridge rather than requiring the user to select another live kernel.
    interpreter = ROOT.parent / 'QuissKit' / '.venv' / 'Scripts' / 'python.exe'
    manager.kernel_spec.argv[0] = str(interpreter)
    manager.start_kernel(cwd=str(ROOT))
    client = manager.client()
    client.start_channels()
    notebook['metadata']['qpu_verification'] = dict(
        local_interpreter=str(interpreter), budget=20, real_qpu=True,
        purpose='Full notebook, fresh local optimization, isolated IBM execution')

    def save():
        (OUTPUT / 'executed.ipynb').write_text(
            json.dumps(notebook, ensure_ascii=False, indent=1)+'\n', encoding='utf-8')

    def execute(source, cell=None):
        message_id = client.execute(source)
        last_activity = time.monotonic()
        failure = None
        while True:
            try:
                message = client.get_iopub_msg(timeout=15)
            except Empty:
                if time.monotonic() - last_activity > 50:
                    print('Notebook cell still running...', flush=True)
                    last_activity = time.monotonic()
                continue
            if message.get('parent_header', {}).get('msg_id') != message_id:
                continue
            kind, content = message['header']['msg_type'], message['content']
            if kind == 'status' and content['execution_state'] == 'idle':
                break
            if cell is not None:
                if kind == 'execute_input':
                    cell['execution_count'] = content['execution_count']
                elif kind in ('stream', 'display_data', 'execute_result', 'error'):
                    fields = dict(stream=('name', 'text'), display_data=('data', 'metadata'),
                                  execute_result=('data', 'metadata', 'execution_count'),
                                  error=('ename', 'evalue', 'traceback'))[kind]
                    cell['outputs'].append(dict(output_type=kind, **{
                        key: copy.deepcopy(content[key]) for key in fields if key in content}))
                    save()
            if kind == 'stream':
                text = content['text']
                # Persist all notebook output, but keep the terminal progress compact.
                if any(word in text for word in ('IBM', 'QPU', 'p=1:', 'p=2:', 'Terminat', 'Job ID')):
                    print(text.rstrip(), flush=True)
                last_activity = time.monotonic()
            if kind == 'error':
                failure = content['ename'] + ': ' + content['evalue']
        if failure:
            raise RuntimeError(failure)

    try:
        client.wait_for_ready(timeout=45)
        # IPykernel temporarily replaces builtins.input for each execution. A
        # notebook-global input function survives that forwarding and supplies
        # the explicitly selected budget without leaving an unanswered stdin request.
        execute("input=lambda prompt: '20'\n%matplotlib inline")
        for index, cell in enumerate(notebook['cells']):
            if cell['cell_type'] != 'code':
                continue
            print('Executing notebook cell', index, flush=True)
            execute(''.join(cell['source']), cell)
            save()
        execute("assert real_job_id and sum(real_counts.values())==4096\n"
                "assert len(next(iter(real_counts)))==19\n"
                "print('VERIFIED REAL QPU JOB:',real_job_id,'shots:',sum(real_counts.values()))")
        print('Full executed notebook:', OUTPUT / 'executed.ipynb', flush=True)
    finally:
        save()
        client.stop_channels()
        manager.shutdown_kernel(now=True)


if __name__ == '__main__':
    main()
