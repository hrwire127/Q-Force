"""Hardware gating and credential handling for the executable notebook export."""
import contextlib
import io
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

import Quantum_Railways_Labb as script
import railway_script_support as support


def test_dry_run_preserves_notebook_scenario_and_never_connects(tmp_path):
    output = tmp_path / 'not-created'
    stdout = io.StringIO()
    with patch.object(script, 'connect_ibm', side_effect=AssertionError('No connection allowed')):
        with contextlib.redirect_stdout(stdout):
            script.main(['--ibm', '--dry-run', '--output', str(output)])
    text = stdout.getvalue()
    settings = json.loads(text[text.index('{'):])
    assert settings == dict(network='notebook', cities=14, routes=19, qubits=19,
                           budget=20, penalty=0.7, depths=[1, 2], maxiter=30,
                           restarts=1, shots=4096, seed=2026, real_hardware=False)
    assert not output.exists()


def test_ibm_uses_local_credentials_and_environment_overrides_without_submission(tmp_path):
    config = tmp_path / 'credentials.json'
    config.write_text(json.dumps(dict(token='local-test-token', instance='local-test-crn',
                                     backend='test-backend')), encoding='utf-8')
    backend = Mock(num_qubits=127)
    backend.status.return_value.operational = True
    service = Mock()
    service.backend.return_value = backend
    factory = Mock(return_value=service)
    sampler = Mock()
    args = support.parse_args(['--check-ibm', '--credentials', str(config)])
    with patch.dict(os.environ, {'IBM_QUANTUM_TOKEN': 'env-test-token',
                                 'IBM_QUANTUM_INSTANCE': 'env-test-crn'}, clear=True):
        with patch.object(support, 'ibm_types', return_value=(factory, sampler)):
            connected, selected = support.connect_ibm(args)
    factory.assert_called_once_with(channel='ibm_quantum_platform', token='env-test-token',
                                    instance='env-test-crn')
    service.backend.assert_called_once_with('test-backend')
    assert connected is service and selected is backend
    sampler.assert_not_called()
    assert json.loads(config.read_text())['token'] == 'local-test-token'


def test_ibm_error_does_not_echo_credentials(tmp_path):
    secret = 'sensitive-test-marker'
    config = tmp_path / 'credentials.json'
    config.write_text(json.dumps(dict(token=secret, instance='test-crn')), encoding='utf-8')
    factory = Mock(side_effect=ValueError(secret))
    with patch.dict(os.environ, {}, clear=True):
        with patch.object(support, 'ibm_types', return_value=(factory, Mock())):
            with pytest.raises(RuntimeError) as error:
                support.connect_ibm(support.parse_args(['--credentials', str(config)]))
    assert secret not in str(error.value)
    assert error.value.__suppress_context__


def test_missing_credentials_fail_in_noninteractive_run_without_prompt(tmp_path):
    args = support.parse_args(['--credentials', str(tmp_path / 'missing.json')])
    with patch.dict(os.environ, {}, clear=True):
        with patch.object(support, 'ibm_types', return_value=(Mock(), Mock())):
            with patch.object(Path, 'home', return_value=tmp_path):
                with patch.object(support.sys.stdin, 'isatty', return_value=False):
                    with patch.object(support, 'getpass', side_effect=AssertionError('No terminal')):
                        with pytest.raises(RuntimeError, match='Lipseste cheia IBM'):
                            support.connect_ibm(args)
