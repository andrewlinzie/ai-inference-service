import json
from datetime import datetime, timedelta, timezone

from prometheus_client import REGISTRY

from src.jobs.drift import (
    assign_bin,
    build_report,
    population_stability_index,
    publish,
    report_key,
    run_once,
    sample_value,
)


def test_psi_matches_the_worked_shift() -> None:
    score = population_stability_index([0.5, 0.5], [0.1, 0.9])
    assert abs(score - 0.8736066829409495) < 1e-12


def test_psi_is_zero_when_shares_match() -> None:
    assert population_stability_index([0.5, 0.5], [0.5, 0.5]) == 0.0


def test_last_edge_lands_in_the_last_bin() -> None:
    profile = {
        "features": {
            "amount": {"edges": [0.0, 0.5, 1.0], "expected_pct": [0.5, 0.5]},
        },
        "probability_fraud": {"edges": [0.0, 1.0], "expected_pct": [1.0]},
    }
    samples = [
        {"features": {"amount": 0.1}, "probability_fraud": 0.2},
        {"features": {"amount": 1.0}, "probability_fraud": 0.2},
    ]
    amount_edges = profile["features"]["amount"]["edges"]
    assert assign_bin(sample_value(samples[0], "amount"), amount_edges) == 0
    assert assign_bin(sample_value(samples[1], "amount"), amount_edges) == 1
    score_edges = profile["probability_fraud"]["edges"]
    assert assign_bin(sample_value(samples[1], "probability_fraud"), score_edges) == 0


class MemoryS3:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_object(self, **kwargs):
        self.objects[kwargs["Key"]] = kwargs["Body"]

    def get_object(self, **kwargs):
        class Body:
            def __init__(self, payload: bytes):
                self._payload = payload

            def read(self) -> bytes:
                return self._payload

        return {"Body": Body(self.objects[kwargs["Key"]])}

    def list_objects_v2(self, **kwargs):
        prefix = kwargs["Prefix"]
        contents = [{"Key": key, "LastModified": datetime.now(timezone.utc)} for key in self.objects if key.startswith(prefix)]
        return {"Contents": contents, "IsTruncated": False}


def _settings() -> dict:
    return {
        "bucket": "sample-bucket",
        "model_version": "pkg",
        "profile_key": "monitoring/reference/pkg/profile.json",
        "prediction_prefix": "monitoring/predictions",
        "report_prefix": "monitoring/reports",
        "min_samples": 100,
        "window_hours": 24,
        "region": "us-east-2",
    }


def _profile() -> dict:
    return {
        "model_version": "pkg",
        "features": {
            "amount": {"edges": [0.0, 0.5, 1.0], "expected_pct": [0.5, 0.5]},
        },
        "probability_fraud": {"edges": [0.0, 1.0], "expected_pct": [1.0]},
    }


def _sample(request_id: str, when: datetime, amount: float) -> dict:
    return {
        "request_id": request_id,
        "model_version": "pkg",
        "scored_at": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "features": {"amount": amount},
        "is_fraud": 0,
        "probability_fraud": 0.2,
    }


def test_short_window_writes_a_report_without_psi() -> None:
    now = datetime(2026, 11, 6, 22, 0, tzinfo=timezone.utc)
    store = MemoryS3()
    store.put_object(
        Key="monitoring/reference/pkg/profile.json",
        Body=json.dumps(_profile()).encode("utf-8"),
    )
    recent = _sample("new", now - timedelta(minutes=5), 0.1)
    stale = _sample("old", now - timedelta(hours=48), 1.0)
    store.put_object(
        Key="monitoring/predictions/model_version=pkg/dt=2026-11-06/new.json",
        Body=json.dumps(recent).encode("utf-8"),
    )
    store.put_object(
        Key="monitoring/predictions/model_version=pkg/dt=2026-11-04/old.json",
        Body=json.dumps(stale).encode("utf-8"),
    )

    report = run_once(store, _settings(), now)

    assert report["sample_count"] == 1
    assert report["samples_sufficient"] is False
    assert report["score_psi"] is None
    assert report["feature_psi"]["amount"] is None
    written = report_key(_settings(), now)
    assert written in store.objects
    assert json.loads(store.objects[written])["sample_count"] == 1


def test_enough_samples_match_the_worked_shift() -> None:
    now = datetime(2026, 11, 6, 22, 0, tzinfo=timezone.utc)
    samples = [_sample("low", now, 0.1)]
    samples.extend(_sample(f"high-{index}", now, 1.0) for index in range(9))
    report = build_report(_profile(), samples, now=now, window_hours=24, min_samples=10)
    assert report["samples_sufficient"] is True
    assert abs(report["feature_psi"]["amount"] - 0.8736066829409495) < 1e-12
    assert report["score_psi"] == 0.0


def test_missing_report_publishes_an_absent_age() -> None:
    now = datetime(2026, 11, 6, 22, 0, tzinfo=timezone.utc)
    publish(None, now, "pkg")
    age = REGISTRY.get_sample_value(
        "model_drift_report_age_seconds",
        {"service": "model-drift", "model_version": "pkg"},
    )
    sufficient = REGISTRY.get_sample_value(
        "model_drift_samples_sufficient",
        {"service": "model-drift", "model_version": "pkg"},
    )
    assert age == -1.0
    assert sufficient == 0.0
