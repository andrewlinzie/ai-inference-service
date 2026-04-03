from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)


def test_infer_returns_expected_response():
    payload = {
        "request_id": "abc-123",
        "input_type": "text",
        "content": "I have been feeling overwhelmed this week."
    }

    response = client.post("/v1/infer", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "summary": "User reports stress and overwhelm.",
        "signals": ["stress", "fatigue"],
        "recommendation": "Suggest a short grounding exercise."
    }