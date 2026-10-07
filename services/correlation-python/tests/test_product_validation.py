import pytest

from gcci.product_validation import RankedLabel, investigation_yield, precision_at_k, qualification_precision


def test_precision_at_k_uses_rank_order_and_reviewed_labels():
    rows = [
        RankedLabel("a", 0.95, True),
        RankedLabel("b", 0.90, False),
        RankedLabel("c", 0.85, True),
        RankedLabel("d", 0.20, True),
    ]
    assert precision_at_k(rows, 3) == pytest.approx(2 / 3)


def test_precision_at_k_does_not_treat_unreviewed_as_negative():
    rows = [RankedLabel("a", 0.95, None), RankedLabel("b", 0.90, True)]
    assert precision_at_k(rows, 2) == 1.0


def test_precision_returns_none_without_ground_truth():
    rows = [RankedLabel("a", 0.95, None)]
    assert precision_at_k(rows, 10) is None
    assert qualification_precision(rows) is None


def test_investigation_yield_counts_advanced_outcomes():
    assert investigation_yield(["INVESTIGATED", "ADVANCED", "SIGNED", "DECLINED"]) == pytest.approx(2 / 3)


def test_invalid_k_rejected():
    with pytest.raises(ValueError):
        precision_at_k([], 0)
