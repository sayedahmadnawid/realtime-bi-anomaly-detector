"""
Phase 3: build multivariate feature rows from raw_events.

raw_events is long-format (one row per metric per minute). Isolation Forest
needs wide rows: one row per 5-minute bucket, one column per metric.
"""

from datetime import datetime, timedelta

from detection.rules import BUCKET_MINUTES, GAUGE_METRICS, LOOKBACK_BUCKETS
import numpy as np
from sklearn.ensemble import IsolationForest

from detection.rules import MIN_BASELINE_BUCKETS
from typing import Optional
from detection.rules import Anomaly, Z_HIGH_SEVERITY, get_latest_event_time


# Site-wide metrics only. orders/revenue are summed across categories.
FEATURE_METRICS = ["traffic", "signups", "orders", "revenue"]

Z_THRESHOLD_MV = 3.0

RATIO_NAMES = ["orders_per_visitor", "revenue_per_order"]   # signups/traffic dropped: too noisy


def evaluate_latest_bucket(rows):
    """Return [(name, bucket_time, z, expected, actual), ...], one per ratio,
    or [] if there isn't enough history yet."""
    if len(rows) < MIN_BASELINE_BUCKETS + 2:
        return []

    features = np.array([row[1:] for row in rows])      # drop the time column
    ratios = to_ratios(features)[:, [0, 2]]             # orders/traffic, revenue/orders
    bucket_time = rows[-2][0]                           # latest COMPLETE bucket

    baseline = ratios[:-2]                              # everything before it
    candidate = ratios[-2]                              # the bucket we judge

    med = np.median(baseline, axis=0)                   # typical value, per ratio
    mad = np.median(np.abs(baseline - med), axis=0) * 1.4826   # typical spread
    mad = np.maximum(mad, 0.05 * np.abs(med))           # floor: never divide by ~0
    z = (candidate - med) / mad

    results = []
    for name, zi, expected, actual in zip(RATIO_NAMES, z, med, candidate):
        results.append((name, bucket_time, float(zi), float(expected), float(actual)))
    return results


def check_multivariate(conn) -> list[Anomaly]:
    reference_time = get_latest_event_time(conn)
    if reference_time is None:
        return []

    rows = merge_series_into_rows(get_multivariate_series(conn, reference_time))
    anomalies = []
    for name, bucket_time, z, expected, actual in evaluate_latest_bucket(rows):
        if abs(z) < Z_THRESHOLD_MV:
            continue
        anomalies.append(Anomaly(
            metric=name,
            category=None,
            window_start=bucket_time,
            window_end=bucket_time + timedelta(minutes=BUCKET_MINUTES),
            expected_value=round(expected, 3),
            actual_value=round(actual, 3),
            z_score=round(z, 2),
            severity="high" if abs(z) >= Z_HIGH_SEVERITY else "medium",
        ))
    return anomalies

def get_metric_buckets(
    conn, metric: str, reference_time: datetime
) -> dict[datetime, float]:
    """One metric -> {bucket_time: value}, summed across all categories."""
    agg_fn = "AVG" if metric in GAUGE_METRICS else "SUM"
    lower_bound = reference_time - timedelta(minutes=BUCKET_MINUTES * (LOOKBACK_BUCKETS + 3))

    query = f"""
        SELECT
            date_bin(%s, event_time, TIMESTAMP '2000-01-01') AS bucket,
            {agg_fn}(value) AS agg_value
        FROM raw_events
        WHERE metric = %s
          AND event_time >= %s
          AND event_time <= %s
        GROUP BY bucket
        ORDER BY bucket DESC
        LIMIT %s
    """
    bucket_interval = timedelta(minutes=BUCKET_MINUTES)
    with conn.cursor() as cur:
        cur.execute(
            query,
            (bucket_interval, metric, lower_bound, reference_time, LOOKBACK_BUCKETS + 2),
        )
        rows = cur.fetchall()
    return {row[0]: float(row[1]) for row in rows}

def to_ratios(a: np.ndarray) -> np.ndarray:
    """Raw counts -> ratios, so the daily rhythm doesn't look like change."""
    traffic, signups, orders, revenue = a[:, 0], a[:, 1], a[:, 2], a[:, 3]
    safe_traffic = np.maximum(traffic, 1)   # a flatline (traffic 0) must not divide by 0
    return np.column_stack([
        orders / safe_traffic,
        signups / safe_traffic,
        revenue / np.maximum(orders, 1),
    ])

def get_multivariate_series(
    conn, reference_time: datetime
) -> dict[str, dict[datetime, float]]:
    """All feature metrics -> {metric: {bucket_time: value}}."""
    series = {}
    for metric in FEATURE_METRICS:
        series[metric] = get_metric_buckets(conn, metric, reference_time)
    return series


def merge_series_into_rows(series: dict[str, dict]) -> list[list]:
    """{metric: {time: value}} -> [[time, v1, v2, ...], ...] oldest first.
    A metric with no value for a bucket counts as 0."""
    all_times = set()
    for values in series.values():
        all_times |= set(values.keys())

    rows = []
    for t in sorted(all_times):
        row = [t]
        for metric in FEATURE_METRICS:
            row.append(series[metric].get(t, 0))
        rows.append(row)
    return rows


if __name__ == "__main__":
    from ingestion.db import get_connection   # use whatever import you already have here
    conn = get_connection()
    rows = merge_series_into_rows(get_multivariate_series(conn, get_latest_event_time(conn)))
    for r in evaluate_latest_bucket(rows):
        print(r)