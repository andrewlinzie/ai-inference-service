from fastapi import APIRouter, HTTPException, Request

from src.models.schemas import InferenceRequest, InferenceResponse
from src.services.inference_engine import run_inference
from src.services.model_loader import FeatureMismatch

router = APIRouter()


@router.post("/v1/infer", response_model=InferenceResponse)
def infer(payload: InferenceRequest, request: Request):
    package = getattr(request.app.state, "package", None)
    if package is None:
        raise HTTPException(status_code=503, detail="model_not_loaded")
    try:
        return run_inference(payload, package)
    except FeatureMismatch as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
