import os
import time

import psutil
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.responses import Response

INFERENCE_REQUESTS_TOTAL = Counter(
    "inference_requests_total",
    "Total inference requests",
    ["service", "status"],
)

INFERENCE_DURATION_SECONDS = Histogram(
    "inference_duration_seconds",
    "Inference request duration in seconds",
    ["service"],
)

INFERENCE_ERRORS_TOTAL = Counter(
    "inference_errors_total",
    "Total inference errors",
    ["service"],
)

MODEL_PROCESSING_TIME_SECONDS = Histogram(
    "model_processing_time_seconds",
    "Model processing duration in seconds",
    ["service", "model_version"],
)

INFERENCE_MEMORY_USAGE_BYTES = Gauge(
    "inference_memory_usage_bytes",
    "Memory usage of the inference service process in bytes",
    ["service"],
)


async def metrics_endpoint():
    process = psutil.Process(os.getpid())
    INFERENCE_MEMORY_USAGE_BYTES.labels(service="ai-inference-service").set(
        process.memory_info().rss
    )
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


async def inference_metrics_middleware(request, call_next):
    if request.url.path != "/v1/infer":
        return await call_next(request)

    start_time = time.time()
    try:
        response = await call_next(request)
        status = "success" if response.status_code < 500 else "error"
        INFERENCE_REQUESTS_TOTAL.labels(
            service="ai-inference-service",
            status=status,
        ).inc()
        if response.status_code >= 500:
            INFERENCE_ERRORS_TOTAL.labels(service="ai-inference-service").inc()
        return response
    except Exception:
        INFERENCE_REQUESTS_TOTAL.labels(
            service="ai-inference-service",
            status="error",
        ).inc()
        INFERENCE_ERRORS_TOTAL.labels(service="ai-inference-service").inc()
        raise
    finally:
        duration = time.time() - start_time
        INFERENCE_DURATION_SECONDS.labels(service="ai-inference-service").observe(
            duration
        )
