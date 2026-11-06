import time

from src.metrics import (
    INFERENCE_PREDICTIONS_TOTAL,
    INFERENCE_SCORE,
    MODEL_PROCESSING_TIME_SECONDS,
)
from src.models.schemas import InferenceRequest, InferenceResponse
from src.services.model_loader import score


def run_inference(payload: InferenceRequest, package: dict) -> InferenceResponse:
    start_time = time.time()
    scored = score(package, payload.model_dump())
    duration = time.time() - start_time
    model_version = scored["model_version"]
    MODEL_PROCESSING_TIME_SECONDS.labels(
        service="ai-inference-service",
        model_version=model_version,
    ).observe(duration)
    INFERENCE_SCORE.labels(
        service="ai-inference-service",
        model_version=model_version,
    ).observe(scored["probability_fraud"])
    INFERENCE_PREDICTIONS_TOTAL.labels(
        service="ai-inference-service",
        model_version=model_version,
        is_fraud=str(scored["is_fraud"]),
    ).inc()
    return InferenceResponse(request_id=payload.request_id, **scored)
