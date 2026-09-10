"""
Database access for the ingestion pipeline.

Kept deliberately simple for Phase 1: a plain psycopg2 connection and a
bulk-insert helper. This will likely get replaced/wrapped once the
processing/aggregation and API layers need shared DB access (Phase 2+).
"""

import os

import psycopg2
import psycopg2.extras


def get_connection():
    """Open a new connection using DATABASE_URL from the environment."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return psycopg2.connect(database_url)


def insert_events(conn, events: list[dict]) -> None:
    """
    Bulk-insert a batch of event dicts into raw_events.

    Each event dict must have: event_time, metric, category, value
    (category may be None).
    """
    if not events:
        return

    rows = [
        (e["event_time"], e["metric"], e["category"], e["value"])
        for e in events
    ]

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO raw_events (event_time, metric, category, value)
            VALUES %s
            """,
            rows,
        )
    conn.commit()
