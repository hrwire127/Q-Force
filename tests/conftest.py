"""Keep automated UI tests isolated from the user's persistent simulation history."""
import pytest


@pytest.fixture(autouse=True)
def isolated_simulation_history(monkeypatch,tmp_path):
    monkeypatch.setenv('QUANTUM_RAILWAYS_HISTORY_DB',str(tmp_path/'history.sqlite3'))
