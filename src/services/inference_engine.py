import time

from src.metrics import MODEL_PROCESSING_TIME_SECONDS
from src.models.schemas import InferenceRequest, InferenceResponse


def run_inference(payload: InferenceRequest) -> InferenceResponse:
    start_time = time.time()
    try:
        raise Exception("test failure")

        return InferenceResponse(
            summary="User reports stress and overwhelm.",
            signals=["stress", "fatigue"],
            recommendation="Suggest a short grounding exercise.",
        )
    finally:
        duration = time.time() - start_time
        MODEL_PROCESSING_TIME_SECONDS.labels(
            service="ai-inference-service",
            model_version="stub-v1",
        ).observe(duration)