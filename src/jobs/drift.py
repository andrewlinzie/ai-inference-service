"""Population-stability index and the dev drift job.

The smoothing and the worked example are the contract in the Phase D walkthrough.
This module does not import ml_training. A CronJob writes one report. A
Deployment serves that report on /metrics.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest

PSI_EPSILON = 0.001
SERVICE = "model-drift"
FEATURE_NAMES = (
    "amount",
    "hour_of_day",
    "day_of_week",
    "merchant_risk",
    "device_trust",
    "is_international",
)

logger = logging.getLogger(__name__)

FEATURE_PSI = Gauge(
    "model_feature_psi",
    "Population stability index for one model feature",
    ["service", "model_version", "feature"],
)
SCORE_PSI = Gauge(
    "model_score_psi",
    "Population stability index for probability_fraud",
    ["service", "model_version"],
)
SAMPLE_COUNT = Gauge(
    "model_drift_sample_count",
    "Prediction samples inside the drift window",
    ["service", "model_version"],
)
SAMPLES_SUFFICIENT = Gauge(
    "model_drift_samples_sufficient",
    "1 when the drift window has at least the minimum sample count",
    ["service", "model_version"],
)
REPORT_AGE = Gauge(
    "model_drift_report_age_seconds",
    "Age of the newest drift report. -1 when no report exists.",
    ["service", "model_version"],
)


def population_stability_index(
    expected_pct: list[float],
    actual_pct: list[float],
    eps: float = PSI_EPSILON,
) -> float:
    """PSI after adding eps to every share and renormalizing."""
    if len(expected_pct) != len(actual_pct):
        raise ValueError("expected_pct and actual_pct must have the same length")
    expected = [float(value) + eps for value in expected_pct]
    actual = [float(value) + eps for value in actual_pct]
    expected_sum = sum(expected)
    actual_sum = sum(actual)
    total = 0.0
    for exp, act in zip(expected, actual, strict=True):
        share_expected = exp / expected_sum
        share_actual = act / actual_sum
        total += (share_actual - share_expected) * math.log(share_actual / share_expected)
    return total


def assign_bin(value: float, edges: list[float]) -> int:
    """Bin i is [edges[i], edges[i+1]). The last bin includes its right edge."""
    if len(edges) < 2:
        raise ValueError("edges need at least two cut points")
    last = len(edges) - 2
    number = float(value)
    if number >= edges[-1]:
        return last
    for index in range(last):
        if edges[index] <= number < edges[index + 1]:
            return index
    if edges[-2] <= number <= edges[-1]:
        return last
    return 0


def sample_value(sample: dict[str, Any], name: str) -> float:
    if name == "probability_fraud":
        return float(sample["probability_fraud"])
    return float(sample["features"][name])


def format_time(when: datetime) -> str:
    return when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def actual_shares(values: list[float], edges: list[float]) -> list[float]:
    counts = [0 for _ in range(len(edges) - 1)]
    for value in values:
        counts[assign_bin(value, edges)] += 1
    total = sum(counts)
    if total == 0:
        raise ValueError("cannot score an empty window")
    return [count / total for count in counts]


def prediction_prefix_for(settings: dict[str, Any]) -> str:
    prefix = str(settings["prediction_prefix"]).strip("/")
    return f"{prefix}/model_version={settings['model_version']}/"


def report_prefix_for(settings: dict[str, Any]) -> str:
    prefix = str(settings["report_prefix"]).strip("/")
    return f"{prefix}/model_version={settings['model_version']}/"


def report_key(settings: dict[str, Any], when: datetime) -> str:
    day = when.astimezone(timezone.utc).strftime("%Y-%m-%d")
    return f"{report_prefix_for(settings)}dt={day}/report.json"


def samples_in_window(
    samples: list[dict[str, Any]],
    start: datetime,
    end: datetime,
) -> list[dict[str, Any]]:
    kept = []
    for sample in samples:
        scored_at = sample.get("scored_at")
        if not scored_at:
            continue
        when = parse_time(str(scored_at))
        if start <= when <= end:
            kept.append(sample)
    return kept


def build_report(
    profile: dict[str, Any],
    samples: list[dict[str, Any]],
    *,
    now: datetime,
    window_hours: int,
    min_samples: int,
) -> dict[str, Any]:
    sufficient = len(samples) >= min_samples
    feature_psi: dict[str, float | None] = {}
    for name, block in profile["features"].items():
        if not sufficient:
            feature_psi[name] = None
            continue
        shares = actual_shares(
            [sample_value(sample, name) for sample in samples],
            block["edges"],
        )
        feature_psi[name] = population_stability_index(block["expected_pct"], shares)
    score_block = profile["probability_fraud"]
    if not sufficient:
        score_psi = None
    else:
        shares = actual_shares(
            [sample_value(sample, "probability_fraud") for sample in samples],
            score_block["edges"],
        )
        score_psi = population_stability_index(score_block["expected_pct"], shares)
    start = now - timedelta(hours=window_hours)
    return {
        "model_version": profile["model_version"],
        "window_start": format_time(start),
        "window_end": format_time(now),
        "generated_at": format_time(now),
        "sample_count": len(samples),
        "min_samples": min_samples,
        "samples_sufficient": sufficient,
        "score_psi": score_psi,
        "feature_psi": feature_psi,
    }


def list_keys(client: Any, bucket: str, prefix: str) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    token = None
    while True:
        kwargs: dict[str, Any] = {"Bucket": bucket, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        page = client.list_objects_v2(**kwargs)
        objects.extend(page.get("Contents", []))
        if not page.get("IsTruncated"):
            return objects
        token = page.get("NextContinuationToken")


def read_json(client: Any, bucket: str, key: str) -> dict[str, Any]:
    body = client.get_object(Bucket=bucket, Key=key)["Body"].read()
    return json.loads(body)


def load_samples(client: Any, settings: dict[str, Any], now: datetime) -> list[dict[str, Any]]:
    start = now - timedelta(hours=int(settings["window_hours"]))
    loaded = []
    prefix = prediction_prefix_for(settings)
    for item in list_keys(client, settings["bucket"], prefix):
        try:
            sample = read_json(client, settings["bucket"], item["Key"])
        except (json.JSONDecodeError, KeyError, TypeError):
            logger.warning("skipping unreadable prediction %s", item["Key"])
            continue
        loaded.append(sample)
    return samples_in_window(loaded, start, now)


def load_latest_report(client: Any, settings: dict[str, Any]) -> dict[str, Any] | None:
    objects = list_keys(client, settings["bucket"], report_prefix_for(settings))
    if not objects:
        return None
    newest = max(objects, key=lambda item: item["LastModified"])
    return read_json(client, settings["bucket"], newest["Key"])


def run_once(client: Any, settings: dict[str, Any], now: datetime) -> dict[str, Any]:
    profile = read_json(client, settings["bucket"], settings["profile_key"])
    samples = load_samples(client, settings, now)
    report = build_report(
        profile,
        samples,
        now=now,
        window_hours=int(settings["window_hours"]),
        min_samples=int(settings["min_samples"]),
    )
    key = report_key(settings, now)
    client.put_object(
        Bucket=settings["bucket"],
        Key=key,
        Body=json.dumps(report).encode("utf-8"),
        ContentType="application/json",
    )
    return report


def publish(report: dict[str, Any] | None, now: datetime, model_version: str) -> None:
    version = str(report["model_version"]) if report else model_version
    base = {"service": SERVICE, "model_version": version}
    names = list(report["feature_psi"]) if report else list(FEATURE_NAMES)
    for name in names:
        value = 0.0
        if report and report["feature_psi"].get(name) is not None:
            value = float(report["feature_psi"][name])
        FEATURE_PSI.labels(feature=name, **base).set(value)
    score = 0.0
    count = 0.0
    sufficient = 0.0
    age = -1.0
    if report:
        if report.get("score_psi") is not None:
            score = float(report["score_psi"])
        count = float(report["sample_count"])
        sufficient = 1.0 if report["samples_sufficient"] else 0.0
        age = max(0.0, (now - parse_time(str(report["generated_at"]))).total_seconds())
    SCORE_PSI.labels(**base).set(score)
    SAMPLE_COUNT.labels(**base).set(count)
    SAMPLES_SUFFICIENT.labels(**base).set(sufficient)
    REPORT_AGE.labels(**base).set(age)


def settings_from_env() -> dict[str, Any]:
    return {
        "bucket": os.environ["BUCKET"],
        "model_version": os.environ["MODEL_VERSION"],
        "profile_key": os.environ["PROFILE_KEY"],
        "prediction_prefix": os.environ["PREDICTION_PREFIX"],
        "report_prefix": os.environ["REPORT_PREFIX"],
        "min_samples": int(os.environ.get("MIN_SAMPLES", "100")),
        "window_hours": int(os.environ.get("WINDOW_HOURS", "24")),
        "region": os.environ.get("AWS_REGION", "us-east-2"),
    }


def _s3_client(region: str) -> Any:
    import boto3

    return boto3.client("s3", region_name=region)


def serve(port: int, client: Any, settings: dict[str, Any]) -> None:
    latest: dict[str, Any] = {"report": None}

    def refresh() -> None:
        now = datetime.now(timezone.utc)
        try:
            latest["report"] = load_latest_report(client, settings)
        except Exception:
            logger.exception("failed to read the latest drift report")
        publish(latest["report"], now, settings["model_version"])

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path in ("/health", "/live"):
                body = b"ok\n"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path != "/metrics":
                self.send_error(404)
                return
            refresh()
            payload = generate_latest()
            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPE_LATEST)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, fmt: str, *args: Any) -> None:
            logger.info("%s - %s", self.address_string(), fmt % args)

    refresh()
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    logger.info("drift exporter listening on %s", port)
    server.serve_forever()


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", type=int, default=None)
    args = parser.parse_args(argv)
    settings = settings_from_env()
    client = _s3_client(str(settings["region"]))
    if args.serve is None:
        now = datetime.now(timezone.utc)
        report = run_once(client, settings, now)
        print(
            f"sample_count={report['sample_count']} "
            f"samples_sufficient={report['samples_sufficient']}"
        )
        return
    serve(args.serve, client, settings)


if __name__ == "__main__":
    main()
