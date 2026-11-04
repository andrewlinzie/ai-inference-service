import os

PORT = int(os.getenv("PORT", "8001"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
MODEL_NAME = os.getenv("MODEL_NAME", "stub-model")
DEFAULT_MODEL_DIR = "/app/model/fraud_classifier"


def model_dir() -> str:
    """Read at call time so tests can point MODEL_DIR at a fixture."""
    return os.getenv("MODEL_DIR", DEFAULT_MODEL_DIR)