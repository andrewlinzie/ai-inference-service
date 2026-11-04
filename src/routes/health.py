from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
def health_check(request: Request):
    package = getattr(request.app.state, "package", None)
    if package is None:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unready",
                "service": "ai-inference-service",
            },
        )
    return {
        "status": "ok",
        "service": "ai-inference-service",
        "model_version": package["metadata"]["model_version"],
    }


@router.get("/live")
def live_check():
    return {
        "status": "alive",
        "service": "ai-inference-service",
    }
