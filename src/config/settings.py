import os

PORT = int(os.getenv("PORT", "8001"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
MODEL_NAME = os.getenv("MODEL_NAME", "stub-model")