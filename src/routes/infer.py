from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from src.models.schemas import InferenceRequest, InferenceResponse
from src.services.inference_engine import run_inference
from src.services.model_loader import FeatureMismatch
from src.services.prediction_log import write_prediction_sample

router = APIRouter()


@router.post("/v1/infer", response_model=InferenceResponse)
def infer(
    payload: InferenceRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):
    package = getattr(request.app.state, "package", None)
    if package is None:
        raise HTTPException(status_code=503, detail="model_not_loaded")
    try:
        result = run_inference(payload, package)
    except FeatureMismatch as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    background_tasks.add_task(
        write_prediction_sample,
        payload,
        {
            "model_version": result.model_version,
            "is_fraud": result.is_fraud,
            "probability_fraud": result.probability_fraud,
        },
        getattr(request.app.state, "prediction_log_client", None),
    )
    return result
