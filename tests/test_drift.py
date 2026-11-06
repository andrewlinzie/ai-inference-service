from src.jobs.drift import assign_bin, population_stability_index, sample_value


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
