from fastapi.testclient import TestClient

from src.app import app
from tests.model_fixture import write_package

FRAUD_BODY = {
    "request_id": "abc-123",
    "amount": 120.0,
    "hour_of_day": 14,
    "day_of_week": 2,
    "merchant_risk": 0.2,
    "device_trust": 0.9,
    "is_international": 0,
}


def test_infer_returns_loaded_model_version(tmp_path, monkeypatch):
    write_package(tmp_path, model_version="test-logreg")
    monkeypatch.setenv("MODEL_DIR", str(tmp_path))

    with TestClient(app) as client:
        response = client.post("/v1/infer", json=FRAUD_BODY)
        metrics = client.get("/metrics").text

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == "abc-123"
    assert body["model_version"] == "test-logreg"
    assert body["is_fraud"] in (0, 1)
    assert 0 <= body["probability_fraud"] <= 1
    assert 'model_version="test-logreg"' in metrics
    assert "stub-v1" not in metrics


def test_infer_rejects_journal_body(tmp_path, monkeypatch):
    write_package(tmp_path)
    monkeypatch.setenv("MODEL_DIR", str(tmp_path))

    with TestClient(app) as client:
        response = client.post(
            "/v1/infer",
            json={
                "request_id": "abc-123",
                "input_type": "text",
                "content": "I have been feeling overwhelmed this week.",
            },
        )

    assert response.status_code == 422


def test_infer_is_unavailable_when_package_is_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_DIR", str(tmp_path / "missing"))

    with TestClient(app) as client:
        response = client.post("/v1/infer", json=FRAUD_BODY)

    assert response.status_code == 503
    assert response.json()["detail"] == "model_not_loaded"
