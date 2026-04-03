from src.models.schemas import InferenceRequest, InferenceResponse


def run_inference(payload: InferenceRequest) -> InferenceResponse:
    return InferenceResponse(
        summary="User reports stress and overwhelm.",
        signals=["stress", "fatigue"],
        recommendation="Suggest a short grounding exercise."
    )