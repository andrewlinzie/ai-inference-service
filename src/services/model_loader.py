"""Load the baked fraud package and score one row.

The directory layout matches ml-training's package contract. This service does
not import ml_training.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib

REQUIRED_PACKAGE_FILES = (
    "model.joblib",
    "metadata.json",
    "feature_schema.json",
    "metrics.json",
    "config_snapshot.yaml",
)


class ModelLoadError(Exception):
    """The directory exists but is not a usable fraud package."""


class FeatureMismatch(Exception):
    """The loaded schema asks for a feature the request does not have."""


def load_package(package_dir: str | Path) -> dict[str, Any]:
    root = Path(package_dir)
    missing = [name for name in REQUIRED_PACKAGE_FILES if not (root / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Package incomplete at {root}: missing {missing}")

    model = joblib.load(root / "model.joblib")
    metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    feature_schema = json.loads((root / "feature_schema.json").read_text(encoding="utf-8"))
    feature_names = _feature_names(feature_schema)

    if feature_names != list(metadata.get("feature_names", [])):
        raise ModelLoadError("feature_schema.json and metadata.json feature lists disagree")

    if not hasattr(model, "classes_") or not hasattr(model, "predict_proba"):
        raise ModelLoadError("Model must expose classes_ and predict_proba")

    classes = [int(value) for value in model.classes_]
    if classes != [0, 1]:
        raise ModelLoadError(f"Expected classes [0, 1], got {classes}")

    return {
        "model": model,
        "metadata": metadata,
        "feature_schema": feature_schema,
        "feature_names": feature_names,
    }


def score(package: dict[str, Any], features: dict[str, Any]) -> dict[str, Any]:
    names = package["feature_names"]
    missing = [name for name in names if name not in features]
    if missing:
        raise FeatureMismatch(f"Missing features: {missing}")

    ordered = [float(features[name]) for name in names]
    model = package["model"]
    prediction = int(model.predict([ordered])[0])
    if prediction not in (0, 1):
        raise ModelLoadError(f"Expected prediction 0 or 1, got {prediction}")

    probability = float(model.predict_proba([ordered])[0][1])
    return {
        "model_version": package["metadata"]["model_version"],
        "is_fraud": prediction,
        "probability_fraud": probability,
    }


def _feature_names(feature_schema: dict[str, Any]) -> list[str]:
    rows = feature_schema["features"]
    ordered = sorted(rows, key=lambda row: int(row["position"]))
    return [str(row["name"]) for row in ordered]
