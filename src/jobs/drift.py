"""Population-stability index for the baked fraud model.

The smoothing and the worked example are the contract in the Phase D walkthrough.
This module does not import ml_training.
"""

from __future__ import annotations

import math
from typing import Any

PSI_EPSILON = 0.001


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
