import os

PORT = int(os.getenv("PORT", "8001"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
MODEL_NAME = os.getenv("MODEL_NAME", "stub-model")
DEFAULT_MODEL_DIR = "/app/model/fraud_classifier"


def model_dir() -> str:
    """Read at call time so tests can point MODEL_DIR at a fixture."""
    return os.getenv("MODEL_DIR", DEFAULT_MODEL_DIR)


def prediction_log_bucket() -> str:
    """Empty means the score path does not write a sample."""
    return os.getenv("PREDICTION_LOG_BUCKET", "").strip()


def prediction_log_prefix() -> str:
    raw = os.getenv("PREDICTION_LOG_PREFIX", "monitoring/predictions").strip()
    return raw.strip("/") or "monitoring/predictions"


def prediction_log_sample_rate() -> float:
    raw = os.getenv("PREDICTION_LOG_SAMPLE_RATE", "1").strip()
    try:
        rate = float(raw)
    except ValueError:
        return 1.0
    if rate < 0:
        return 0.0
    if rate > 1:
        return 1.0
    return rate


def aws_region() -> str:
    return os.getenv("AWS_REGION", "us-east-2").strip() or "us-east-2"