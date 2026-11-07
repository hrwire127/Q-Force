"""Regressions for the notebook's IBM kernel and credential initialization."""
import ast
from importlib import metadata
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

import railway_script_support as support


NOTEBOOK = Path(__file__).resolve().parents[1] / 'Quantum_Railways_Labb.ipynb'


def notebook_source(index):
    return ''.join(json.loads(NOTEBOOK.read_text(encoding='utf-8'))['cells'][index]['source'])


def test_notebook_setup_keeps_compatible_newer_qiskit():
    source = ast.parse(notebook_source(2))
    function = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == 'ensure_environment')
    fake_metadata = Mock()
    fake_metadata.version.return_value = '2.6.2'
    fake_metadata.PackageNotFoundError = metadata.PackageNotFoundError
    namespace = dict(metadata=fake_metadata, subprocess=Mock(), sys=Mock(modules={}))
    exec(compile(ast.Module(body=[function], type_ignores=[]), '<setup>', 'exec'), namespace)
    installer = Mock(side_effect=AssertionError('Must not downgrade Qiskit'))
    assert namespace['ensure_environment']({'qiskit': '2.1.0'}, installer) == {'qiskit': '2.6.2'}
    installer.assert_not_called()


@pytest.mark.parametrize('qiskit,runtime', [('2.1.0', None), ('2.1.0', '0.50.1'), ('2.6.2', '0.43.0')])
def test_wrong_kernel_error_identifies_environment_and_remedy(qiskit, runtime):
    def version(name):
        if name == 'qiskit':
            return qiskit
        if runtime is None:
            raise metadata.PackageNotFoundError(name)
        return runtime
    with patch.object(support.metadata, 'version', side_effect=version):
        with pytest.raises(RuntimeError) as error:
            support.ibm_types()
    message = str(error.value)
    assert support.sys.executable in message
    assert 'Quantum Railways (IBM)' in message
    assert '%pip install -r requirements-ibm.txt' in message
    assert 'Restart Kernel' in message


def test_notebook_uses_local_token_without_colab_or_prompt(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'ibm_credentials.local.json').write_text(json.dumps(dict(
        token='test-token', instance='test-instance', backend='test-backend')), encoding='utf-8')
    namespace = dict(Path=Path, json=json, local_backend=lambda n: ('local', n))
    backend = Mock(num_qubits=127)
    backend.status.return_value.operational = True
    service = Mock()
    service.backend.return_value = backend
    factory, sampler = Mock(return_value=service), Mock()
    with patch.dict('os.environ', {}, clear=True):
        exec(compile(notebook_source(32), '<ibm_helpers>', 'exec'), namespace)
    namespace['getpass'] = Mock(side_effect=AssertionError('Credentials already supplied'))
    with patch.object(support, 'ibm_types', return_value=(factory, sampler)):
        assert namespace['choose_backend'](False, num_qubits=5)[1] == ('local', 5)
        factory.assert_not_called()
        result = namespace['choose_backend'](True, 'test-backend', 'test-instance', num_qubits=19)
    factory.assert_called_once_with(channel='ibm_quantum_platform', token='test-token', instance='test-instance')
    assert result == (service, backend, 'real QPU')
    namespace['getpass'].assert_not_called()
    sampler.assert_not_called()
