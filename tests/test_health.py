from fastapi.testclient import TestClient

from src.app import app
from tests.model_fixture import write_package


def test_health_reports_loaded_model_version(tmp_path, monkeypatch):
    write_package(tmp_path, model_version="health-logreg")
    monkeypatch.setenv("MODEL_DIR", str(tmp_path))

    with TestClient(app) as client:
        health = client.get("/health")
        live = client.get("/live")

    assert health.status_code == 200
    assert health.json() == {
        "status": "ok",
        "service": "ai-inference-service",
        "model_version": "health-logreg",
    }
    assert live.status_code == 200
    assert live.json() == {
        "status": "alive",
        "service": "ai-inference-service",
    }


def test_health_is_unready_when_package_is_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_DIR", str(tmp_path / "missing"))

    with TestClient(app) as client:
        health = client.get("/health")
        live = client.get("/live")

    assert health.status_code == 503
    assert health.json() == {
        "status": "unready",
        "service": "ai-inference-service",
    }
    assert "detail" not in health.json()
    assert live.status_code == 200
    assert live.json()["status"] == "alive"
