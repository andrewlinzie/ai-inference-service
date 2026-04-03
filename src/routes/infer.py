from fastapi import APIRouter
from src.models.schemas import InferenceRequest, InferenceResponse
from src.services.inference_engine import run_inference

router = APIRouter()


@router.post("/v1/infer", response_model=InferenceResponse)
def infer(payload: InferenceRequest):
    return run_inference(payload)