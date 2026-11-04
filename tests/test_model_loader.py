import json

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

from src.services.model_loader import ModelLoadError, load_package
from tests.model_fixture import FEATURE_NAMES, write_package


def test_load_package_rejects_a_missing_file(tmp_path):
    write_package(tmp_path)
    (tmp_path / "metrics.json").unlink()

    try:
        load_package(tmp_path)
    except FileNotFoundError as exc:
        assert "metrics.json" in str(exc)
    else:
        raise AssertionError("missing metrics.json should fail the load")


def test_load_package_rejects_unexpected_class_order(tmp_path):
    generator = np.random.default_rng(1)
    features = generator.normal(size=(20, len(FEATURE_NAMES)))
    labels = np.where(features[:, 0] > 0, 2, 1)
    model = LogisticRegression(random_state=0).fit(features, labels)
    write_package(tmp_path)
    joblib.dump(model, tmp_path / "model.joblib")

    try:
        load_package(tmp_path)
    except ModelLoadError as exc:
        assert "classes" in str(exc)
    else:
        raise AssertionError("classes other than [0, 1] should fail the load")


def test_load_package_rejects_disagreement_between_schema_and_metadata(tmp_path):
    write_package(tmp_path)
    metadata = json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))
    metadata["feature_names"] = list(reversed(FEATURE_NAMES))
    (tmp_path / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    try:
        load_package(tmp_path)
    except ModelLoadError as exc:
        assert "disagree" in str(exc)
    else:
        raise AssertionError("feature list disagreement should fail the load")
