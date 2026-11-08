"""QPU result validation and recovery never resubmit an existing job."""
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

import ibm_notebook_runner as runner


def result(counts, bits=2):
    return [SimpleNamespace(data=SimpleNamespace(plan=SimpleNamespace(
        num_bits=bits, get_counts=lambda: counts)))]


def test_only_accepts_complete_named_register_measurements():
    assert runner._collect_counts(result({'00': 3, '11': 1}), 2, 4) == {'00': 3, '11': 1}
    for payload, bits, shots in [(result({'0': 4}), 2, 4),
                                 (result({'00': 3}), 2, 4),
                                 (result({'00': 4}, bits=1), 2, 4)]:
        with pytest.raises(RuntimeError):
            runner._collect_counts(payload, bits, shots)


def test_existing_job_is_polled_and_recovered_without_submission(tmp_path):
    request = dict(fingerprint='same-circuit', shots=4, bits=2)
    (tmp_path / 'job.json').write_text(json.dumps(dict(request, job_id='existing-job')), encoding='utf-8')
    job = Mock()
    job.backend.return_value.name = 'test-qpu'
    job.status.side_effect = ['QUEUED', 'RUNNING', 'DONE']
    job.result.return_value = result({'00': 3, '11': 1})
    service = Mock()
    service.job.return_value = job
    sampler = Mock(side_effect=AssertionError('Must never submit'))
    with patch.object(runner.time, 'sleep'):
        record = runner._execute_job(request, tmp_path, service, Mock(), sampler)
    service.job.assert_called_once_with('existing-job')
    sampler.assert_not_called()
    assert record['status'] == 'DONE'
    assert record['counts'] == {'00': 3, '11': 1}
    assert json.loads((tmp_path / 'job.json').read_text())['job_id'] == 'existing-job'


def test_different_circuit_cannot_reuse_job_directory(tmp_path):
    (tmp_path / 'job.json').write_text(json.dumps(dict(fingerprint='old', job_id='old-job')))
    service, sampler = Mock(), Mock()
    with pytest.raises(RuntimeError, match='another circuit'):
        runner._execute_job(dict(fingerprint='new'), tmp_path, service, Mock(), sampler)
    service.job.assert_not_called()
    sampler.assert_not_called()


def test_failed_job_cannot_be_reported_as_success_or_resubmitted(tmp_path):
    request = dict(fingerprint='same', shots=4, bits=2)
    (tmp_path / 'job.json').write_text(json.dumps(dict(request, job_id='failed-job')))
    service, sampler = Mock(), Mock()
    service.job.return_value.backend.return_value.name = 'test-qpu'
    service.job.return_value.status.return_value = 'ERROR'
    with pytest.raises(RuntimeError, match='ERROR'):
        runner._execute_job(request, tmp_path, service, Mock(), sampler)
    service.job.return_value.result.assert_not_called()
    sampler.assert_not_called()


def test_submission_persists_id_before_retrieving_real_measurements(tmp_path):
    from qiskit import QuantumCircuit, ClassicalRegister, qpy
    from qiskit.providers.fake_provider import GenericBackendV2
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.add_register(ClassicalRegister(2, 'plan'))
    circuit.measure(range(2), range(2))
    with (tmp_path / 'circuit.qpy').open('wb') as handle:
        qpy.dump(circuit, handle)
    backend = GenericBackendV2(2, seed=2026)
    request = dict(fingerprint='fresh-circuit', shots=4, bits=2)
    job, sampler = Mock(), Mock()
    job.job_id.return_value = 'new-job'
    job.status.return_value = 'DONE'
    def measurements():
        assert json.loads((tmp_path / 'job.json').read_text())['job_id'] == 'new-job'
        return result({'00': 2, '01': 2})
    job.result.side_effect = measurements
    sampler.return_value.run.return_value = job
    record = runner._execute_job(request, tmp_path, Mock(), backend, sampler)
    sampler.return_value.run.assert_called_once()
    assert record['counts'] == {'00': 2, '01': 2}
    assert not (tmp_path / 'submission.lock').exists()
