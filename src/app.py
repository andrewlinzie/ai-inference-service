from fastapi import FastAPI

from src.metrics import inference_metrics_middleware, metrics_endpoint
from src.routes.health import router as health_router
from src.routes.infer import router as infer_router

app = FastAPI(title="AI Inference Service")

app.include_router(health_router)
app.include_router(infer_router)
app.middleware("http")(inference_metrics_middleware)
app.add_api_route("/metrics", metrics_endpoint, methods=["GET"])
