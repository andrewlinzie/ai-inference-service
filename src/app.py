import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config.settings import model_dir
from src.metrics import (
    MODEL_TRAINING_ROC_AUC,
    inference_metrics_middleware,
    metrics_endpoint,
)
from src.routes.health import router as health_router
from src.routes.infer import router as infer_router
from src.services.model_loader import load_package, package_roc_auc

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        loaded_from = model_dir()
        app.state.package = load_package(loaded_from)
        roc_auc = package_roc_auc(app.state.package)
        if roc_auc is not None:
            model_version = app.state.package["metadata"]["model_version"]
            MODEL_TRAINING_ROC_AUC.labels(
                service="ai-inference-service",
                model_version=model_version,
            ).set(roc_auc)
    except FileNotFoundError:
        logger.error("Model package not found at %s", model_dir())
        app.state.package = None
    except Exception:
        logger.exception("Failed to load model from %s", model_dir())
        app.state.package = None
    yield


app = FastAPI(title="AI Inference Service", lifespan=lifespan)

app.include_router(health_router)
app.include_router(infer_router)
app.middleware("http")(inference_metrics_middleware)
app.add_api_route("/metrics", metrics_endpoint, methods=["GET"])
