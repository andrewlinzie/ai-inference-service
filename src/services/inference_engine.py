import time

from src.metrics import MODEL_PROCESSING_TIME_SECONDS
from src.models.schemas import InferenceRequest, InferenceResponse
from src.services.model_loader import score


def run_inference(payload: InferenceRequest, package: dict) -> InferenceResponse:
    start_time = time.time()
    scored = score(package, payload.model_dump())
    duration = time.time() - start_time
    MODEL_PROCESSING_TIME_SECONDS.labels(
        service="ai-inference-service",
        model_version=scored["model_version"],
    ).observe(duration)
    return InferenceResponse(request_id=payload.request_id, **scored)
