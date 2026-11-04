from src.models.schemas import InferenceRequest
from src.services.inference_engine import run_inference
from src.services.model_loader import load_package
from tests.model_fixture import write_package


def test_run_inference_returns_package_version(tmp_path):
    write_package(tmp_path, model_version="engine-logreg")
    package = load_package(tmp_path)
    payload = InferenceRequest(
        request_id="abc-123",
        amount=120.0,
        hour_of_day=14,
        day_of_week=2,
        merchant_risk=0.2,
        device_trust=0.9,
        is_international=0,
    )

    result = run_inference(payload, package)

    assert result.request_id == "abc-123"
    assert result.model_version == "engine-logreg"
    assert result.is_fraud in (0, 1)
    assert 0 <= result.probability_fraud <= 1
