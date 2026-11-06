"""Tiny logistic regression that satisfies the package contract."""

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

FEATURE_NAMES = [
    "amount",
    "hour_of_day",
    "day_of_week",
    "merchant_risk",
    "device_trust",
    "is_international",
]


def write_package(directory: Path, model_version: str = "test-logreg") -> Path:
    generator = np.random.default_rng(0)
    features = generator.normal(size=(20, len(FEATURE_NAMES)))
    labels = (features[:, 0] > 0).astype(int)
    model = LogisticRegression(random_state=0).fit(features, labels)

    directory.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, directory / "model.joblib")
    (directory / "metadata.json").write_text(
        json.dumps(
            {
                "model_version": model_version,
                "feature_names": FEATURE_NAMES,
                "target": "is_fraud",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (directory / "feature_schema.json").write_text(
        json.dumps(
            {
                "features": [
                    {"name": name, "position": index, "dtype": "number"}
                    for index, name in enumerate(FEATURE_NAMES)
                ],
                "target": "is_fraud",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (directory / "metrics.json").write_text(
        json.dumps(
            {
                "metrics": {"roc_auc": 0.5},
                "primary_metric": "roc_auc",
                "primary_direction": "maximize",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (directory / "config_snapshot.yaml").write_text("task: test\n", encoding="utf-8")
    return directory
