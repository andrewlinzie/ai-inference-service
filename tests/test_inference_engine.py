from src.models.schemas import InferenceRequest
from src.services.inference_engine import run_inference


def test_run_inference_returns_expected_response():
    payload = InferenceRequest(
        request_id="abc-123",
        input_type="text",
        content="I have been feeling overwhelmed this week."
    )

    result = run_inference(payload)

    assert result.summary == "User reports stress and overwhelm."
    assert result.signals == ["stress", "fatigue"]
    assert result.recommendation == "Suggest a short grounding exercise."