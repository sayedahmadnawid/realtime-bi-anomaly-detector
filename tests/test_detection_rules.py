from datetime import datetime, timedelta, timezone

from detection.rules import evaluate_series, MIN_BASELINE_BUCKETS


def _make_buckets(values, start=None):
    """values[0] is treated as the newest (partial) bucket, values[1] as
    current, values[2:] as baseline - matching get_recent_buckets' order
    (most recent first)."""
    start = start or datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
    return [(start - timedelta(minutes=5 * i), v) for i, v in enumerate(values)]


def test_not_enough_history_returns_none():
    # only 3 baseline points, below MIN_BASELINE_BUCKETS
    buckets = _make_buckets([10, 20] + [20, 21, 19])
    assert evaluate_series("orders", "electronics", buckets) is None


def test_normal_value_is_not_flagged():
    baseline = [20, 21, 19, 22, 18, 20, 21, 19] * 3  # well above MIN_BASELINE_BUCKETS
    buckets = _make_buckets([99, 20] + baseline)  # current=20, matches baseline
    assert evaluate_series("orders", "electronics", buckets) is None


def test_sharp_drop_is_flagged():
    baseline = [20, 21, 19, 22, 18, 20, 21, 19] * 3
    buckets = _make_buckets([99, 2] + baseline)  # current=2, way below baseline ~20
    result = evaluate_series("orders", "electronics", buckets)
    assert result is not None
    assert result.actual_value == 2
    assert result.z_score < 0  # a drop -> negative z-score
    assert result.severity in ("medium", "high")


def test_sharp_spike_is_flagged():
    baseline = [20, 21, 19, 22, 18, 20, 21, 19] * 3
    buckets = _make_buckets([99, 90] + baseline)  # current=90, way above baseline ~20
    result = evaluate_series("orders", "electronics", buckets)
    assert result is not None
    assert result.z_score > 0  # a spike -> positive z-score


def test_first_bucket_is_always_skipped_as_partial():
    baseline = [20, 21, 19, 22, 18, 20, 21, 19] * 3
    # first bucket (index 0) is a huge outlier (9999) - if it were
    # mistakenly evaluated as "current" this would obviously be flagged;
    # it should be ignored entirely regardless of its value.
    buckets = _make_buckets([9999, 20] + baseline)
    result = evaluate_series("orders", "electronics", buckets)
    assert result is None  # bucket[1]=20 matches baseline, bucket[0] is irrelevant


def test_minority_outliers_in_baseline_dont_mask_a_real_anomaly():
    # 3 low outlier points mixed into an otherwise-normal ~20 baseline
    # (simulates an anomaly window partially overlapping the lookback
    # window) - median/MAD should still catch the current anomalous value.
    baseline = [20, 21, 19, 22, 18, 20, 21, 19, 23, 22] + [3, 4, 12]
    buckets = _make_buckets([99, 4] + baseline)
    result = evaluate_series("orders", "electronics", buckets)
    assert result is not None
    assert result.severity in ("medium", "high")


def test_near_constant_baseline_does_not_divide_by_zero():
    # MAD would be 0 here without the floor - must not raise, and a small
    # absolute wobble on a near-constant series shouldn't false-positive.
    baseline = [5] * MIN_BASELINE_BUCKETS
    buckets = _make_buckets([99, 5] + baseline)
    result = evaluate_series("orders", "electronics", buckets)
    assert result is None


def test_category_none_handled_like_any_other_series():
    baseline = [40, 42, 39, 41, 38, 40, 41, 39] * 3
    buckets = _make_buckets([99, 5] + baseline)  # sharp drop
    result = evaluate_series("traffic", None, buckets)
    assert result is not None
    assert result.category is None