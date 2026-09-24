"""
Detection v1: periodically scans every (metric, category) series in
raw_events, evaluates the most recently completed time bucket against a
rolling baseline, and records anomalies.

Runs as its own long-lived service (same shape as ingestion/worker) so
detection cadence is independent of ingestion speed and API load.
"""

import logging
import os
import time

from ingestion.db import get_connection
from detection.rules import (
    anomaly_already_recorded,
    evaluate_series,
    get_distinct_series,
    get_latest_event_time,
    get_recent_buckets,
    insert_anomaly,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("detector")


def run_once(conn) -> int:
    """One full detection pass over every series. Returns the number of
    new anomalies recorded."""
    reference_time = get_latest_event_time(conn)
    if reference_time is None:
        log.info("No data in raw_events yet - skipping this pass")
        return 0

    series_list = get_distinct_series(conn)
    new_anomalies = 0

    for metric, category in series_list:
        buckets = get_recent_buckets(conn, metric, category, reference_time)
        anomaly = evaluate_series(metric, category, buckets)

        if anomaly is None:
            continue

        if anomaly_already_recorded(conn, anomaly):
            continue

        insert_anomaly(conn, anomaly)
        new_anomalies += 1
        log.warning(
            "ANOMALY  metric=%s category=%s window=%s..%s expected=%.2f actual=%.2f z=%.2f severity=%s",
            anomaly.metric, anomaly.category, anomaly.window_start.isoformat(),
            anomaly.window_end.isoformat(), anomaly.expected_value,
            anomaly.actual_value, anomaly.z_score, anomaly.severity,
        )

    return new_anomalies


def main() -> None:
    interval = float(os.environ.get("DETECTION_INTERVAL_SECONDS", "15"))
    log.info("Starting detector: checking every %.1fs", interval)

    conn = get_connection()
    log.info("Connected to Postgres")

    try:
        while True:
            try:
                count = run_once(conn)
                if count:
                    log.info("Detection pass complete: %d new anomalies", count)
            except Exception:
                log.exception("Detection pass failed, rolling back")
                conn.rollback()

            time.sleep(interval)

    except KeyboardInterrupt:
        log.info("Shutting down (keyboard interrupt)")
    finally:
        conn.close()


if __name__ == "__main__":
    main()