import pytest

from src.app import app


@pytest.fixture(autouse=True)
def prediction_log_disabled(monkeypatch):
    """Unit tests must not call AWS. A test that wants a sample sets the bucket."""
    monkeypatch.setenv("PREDICTION_LOG_BUCKET", "")
    app.state.prediction_log_client = None
    yield
    app.state.prediction_log_client = None
