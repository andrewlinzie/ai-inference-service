import json

from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from src.app import app
from tests.model_fixture import write_package
from tests.test_infer import FRAUD_BODY


class RecordingS3:
    def __init__(self, error: Exception | None = None):
        self.calls: list[dict] = []
        self.error = error

    def put_object(self, **kwargs):
        if self.error is not None:
            raise self.error
        self.calls.append(kwargs)


def _counter(name: str) -> float:
    value = REGISTRY.get_sample_value(
        name,
        {"service": "ai-inference-service"},
    )
    return float(value or 0.0)


def test_successful_score_writes_one_sample(tmp_path, monkeypatch):
    write_package(tmp_path, model_version="test-logreg")
    monkeypatch.setenv("MODEL_DIR", str(tmp_path))
    monkeypatch.setenv("PREDICTION_LOG_BUCKET", "sample-bucket")
    monkeypatch.setenv("PREDICTION_LOG_PREFIX", "monitoring/predictions")
    client_s3 = RecordingS3()
    app.state.prediction_log_client = client_s3

    with TestClient(app) as client:
        response = client.post("/v1/infer", json=FRAUD_BODY)
        metrics = client.get("/metrics").text

    assert response.status_code == 200
    assert len(client_s3.calls) == 1
    put = client_s3.calls[0]
    assert put["Bucket"] == "sample-bucket"
    assert put["Key"].startswith(
        "monitoring/predictions/model_version=test-logreg/dt="
    )
    assert put["Key"].endswith("/abc-123.json")
    body = json.loads(put["Body"])
    assert body["request_id"] == "abc-123"
    assert body["model_version"] == "test-logreg"
    assert body["features"]["amount"] == 120.0
    assert body["is_fraud"] == response.json()["is_fraud"]
    assert "model_training_roc_auc" in metrics
    assert "inference_score" in metrics
    assert "inference_predictions_total" in metrics


def test_empty_bucket_writes_nothing(tmp_path, monkeypatch):
    write_package(tmp_path)
    monkeypatch.setenv("MODEL_DIR", str(tmp_path))
    monkeypatch.setenv("PREDICTION_LOG_BUCKET", "")
    client_s3 = RecordingS3()
    app.state.prediction_log_client = client_s3

    with TestClient(app) as client:
        response = client.post("/v1/infer", json=FRAUD_BODY)

    assert response.status_code == 200
    assert client_s3.calls == []


def test_rejected_body_writes_nothing(tmp_path, monkeypatch):
    write_package(tmp_path)
    monkeypatch.setenv("MODEL_DIR", str(tmp_path))
    monkeypatch.setenv("PREDICTION_LOG_BUCKET", "sample-bucket")
    client_s3 = RecordingS3()
    app.state.prediction_log_client = client_s3

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
    assert client_s3.calls == []


def test_failed_put_keeps_the_score_and_counts_the_failure(tmp_path, monkeypatch):
    write_package(tmp_path)
    monkeypatch.setenv("MODEL_DIR", str(tmp_path))
    monkeypatch.setenv("PREDICTION_LOG_BUCKET", "sample-bucket")
    app.state.prediction_log_client = RecordingS3(error=RuntimeError("denied"))
    before = _counter("prediction_log_failures_total")

    with TestClient(app) as client:
        response = client.post("/v1/infer", json=FRAUD_BODY)

    assert response.status_code == 200
    assert response.json()["model_version"]
    assert _counter("prediction_log_failures_total") == before + 1
