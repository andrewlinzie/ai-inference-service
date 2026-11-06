"""Write one sampled score to S3 after the response is already decided.

A failed put increments a counter and does not change the HTTP response.
An empty PREDICTION_LOG_BUCKET leaves the writer idle.
"""

from __future__ import annotations

import json
import logging
import random
from datetime import datetime, timezone
from typing import Any

from src.config.settings import (
    aws_region,
    prediction_log_bucket,
    prediction_log_prefix,
    prediction_log_sample_rate,
)
from src.metrics import PREDICTION_LOG_FAILURES_TOTAL
from src.models.schemas import InferenceRequest

logger = logging.getLogger(__name__)

FEATURE_NAMES = (
    "amount",
    "hour_of_day",
    "day_of_week",
    "merchant_risk",
    "device_trust",
    "is_international",
)


def write_prediction_sample(
    payload: InferenceRequest,
    scored: dict[str, Any],
    client: Any = None,
) -> None:
    if not prediction_log_bucket():
        return
    if not _selected(prediction_log_sample_rate()):
        return

    scored_at = datetime.now(timezone.utc).replace(microsecond=0)
    body = {
        "request_id": payload.request_id,
        "model_version": scored["model_version"],
        "scored_at": scored_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "features": {name: getattr(payload, name) for name in FEATURE_NAMES},
        "is_fraud": scored["is_fraud"],
        "probability_fraud": scored["probability_fraud"],
    }
    key = (
        f"{prediction_log_prefix()}/model_version={scored['model_version']}"
        f"/dt={scored_at.strftime('%Y-%m-%d')}/{payload.request_id}.json"
    )
    try:
        s3 = client if client is not None else _s3_client()
        s3.put_object(
            Bucket=prediction_log_bucket(),
            Key=key,
            Body=json.dumps(body).encode("utf-8"),
            ContentType="application/json",
        )
    except Exception:
        logger.exception("prediction sample put failed for %s", key)
        PREDICTION_LOG_FAILURES_TOTAL.labels(service="ai-inference-service").inc()


def _selected(rate: float) -> bool:
    if rate >= 1:
        return True
    if rate <= 0:
        return False
    return random.random() < rate


def _s3_client() -> Any:
    import boto3

    return boto3.client("s3", region_name=aws_region())
