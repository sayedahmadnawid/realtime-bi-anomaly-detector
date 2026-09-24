"""
Core detection logic: bucket raw_events into fixed time windows, compute a
rolling baseline (mean/stddev over recent history), and flag windows that
deviate too far from it (z-score thresholding).

Kept separate from the run loop (detector.py) so the actual detection
logic is easy to unit test without a live Postgres connection driving
everything.
"""

import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

BUCKET_MINUTES = 5
LOOKBACK_BUCKETS = 24         # ~2 hours of history for the baseline
MIN_BASELINE_BUCKETS = 6      # need at least this many history points to trust the baseline
Z_THRESHOLD = 3.0
Z_HIGH_SEVERITY = 5.0

# inventory_level is a gauge (a snapshot), not a count - bucket it with
# AVG, not SUM. Everything else is a count/amount that accumulates over
# the window, so SUM is correct.
GAUGE_METRICS = {"inventory_level"}


@dataclass
class Anomaly:
    metric: str
    category: Optional[str]
    window_start: datetime
    window_end: datetime
    expected_value: float
    actual_value: float
    z_score: float
    severity: str


def get_distinct_series(conn) -> list[tuple[str, Optional[str]]]:
    """Every (metric, category) combination currently present in
    raw_events - auto-discovers what's being monitored rather than
    hardcoding it a second time here."""
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT metric, category FROM raw_events")
        return cur.fetchall()


def get_latest_event_time(conn) -> Optional[datetime]:
    """We're driven by simulated time, not wall-clock time, so 'now' for
    the detector is whatever the most recent event_time in the data is."""
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(event_time) FROM raw_events")
        row = cur.fetchone()
        return row[0] if row else None


def get_recent_buckets(
    conn, metric: str, category: Optional[str], reference_time: datetime
) -> list[tuple[datetime, float]]:
    """
    Return up to (LOOKBACK_BUCKETS + 2) buckets ending at reference_time,
    most recent first. Bucket [0] is the newest (likely still filling in),
    bucket [1] is the most recent *complete* bucket (what we evaluate),
    buckets [2:] are the baseline history.
    """
    agg_fn = "AVG" if metric in GAUGE_METRICS else "SUM"
    lower_bound = reference_time - timedelta(minutes=BUCKET_MINUTES * (LOOKBACK_BUCKETS + 3))

    query = f"""
        SELECT
            date_bin(%s, event_time, TIMESTAMP '2000-01-01') AS bucket,
            {agg_fn}(value) AS agg_value
        FROM raw_events
        WHERE metric = %s
          AND category IS NOT DISTINCT FROM %s
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
            (bucket_interval, metric, category, lower_bound, reference_time, LOOKBACK_BUCKETS + 2),
        )
        rows = cur.fetchall()
    return [(row[0], float(row[1])) for row in rows]


def evaluate_series(
    metric: str, category: Optional[str], buckets: list[tuple[datetime, float]]
) -> Optional[Anomaly]:
    """
    Given buckets (most recent first, as returned by get_recent_buckets),
    decide whether the most recent *complete* bucket is anomalous relative
    to the trailing baseline. Returns None if there isn't enough data yet,
    or if the bucket isn't anomalous.
    """
    if len(buckets) < 2:
        return None  # not even one complete bucket yet

    # buckets[0] is still filling in (partial) - skip it.
    current_bucket_start, current_value = buckets[1]
    baseline_values = [v for _, v in buckets[2:]]

    if len(baseline_values) < MIN_BASELINE_BUCKETS:
        return None  # not enough history to trust a baseline yet

    # Median + MAD ("modified z-score") instead of mean/stdev: robust to
    # a minority of the baseline window itself containing anomalous
    # buckets (e.g. a 15-min anomaly sitting inside a 2-hour lookback
    # window) in a way plain mean/stdev is not - a few outliers barely
    # move the median, but can noticeably drag the mean and inflate the
    # stdev, weakening the very signal we're trying to detect.
    median = statistics.median(baseline_values)
    abs_deviations = [abs(v - median) for v in baseline_values]
    mad = statistics.median(abs_deviations)

    # 0.6745 makes MAD comparable to a standard deviation under a normal
    # distribution assumption (the standard "modified z-score" constant).
    mad_scaled = mad * 1.4826
    mad_floor = max(mad_scaled, abs(median) * 0.05, 0.5)

    z_score = (current_value - median) / mad_floor

    if abs(z_score) < Z_THRESHOLD:
        return None

    severity = "high" if abs(z_score) >= Z_HIGH_SEVERITY else "medium"

    return Anomaly(
        metric=metric,
        category=category,
        window_start=current_bucket_start,
        window_end=current_bucket_start + timedelta(minutes=BUCKET_MINUTES),
        expected_value=round(median, 2),
        actual_value=round(current_value, 2),
        z_score=round(z_score, 2),
        severity=severity,
    )


def anomaly_already_recorded(conn, anomaly: Anomaly) -> bool:
    """IS NOT DISTINCT FROM handles NULL category correctly (plain '='
    would never match NULL = NULL)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM anomalies
            WHERE metric = %s
              AND category IS NOT DISTINCT FROM %s
              AND window_start = %s
            LIMIT 1
            """,
            (anomaly.metric, anomaly.category, anomaly.window_start),
        )
        return cur.fetchone() is not None


def insert_anomaly(conn, anomaly: Anomaly) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO anomalies
                (metric, category, window_start, window_end,
                 expected_value, actual_value, z_score, severity)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                anomaly.metric, anomaly.category, anomaly.window_start, anomaly.window_end,
                anomaly.expected_value, anomaly.actual_value, anomaly.z_score, anomaly.severity,
            ),
        )
    conn.commit()