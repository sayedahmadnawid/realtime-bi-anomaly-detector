"""
API v1: minimal FastAPI service exposing raw_events for the dashboard.

Phase 1 scope only: read the most recent N rows, optionally filtered by
metric/category. No aggregation, no anomalies endpoint yet - those come
in Phase 2 once the processing/detection layers exist.
"""

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from ingestion.db import get_connection

app = FastAPI(title="NovaCart BI API", version="0.1.0")

# Wide open for local dev; tighten this once the dashboard has a real
# deployed origin (Phase 2+).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

VALID_METRICS = {"orders", "revenue", "traffic", "signups", "inventory_level", "payment_attempts", "payment_failures"}


@app.get("/health")
def health():
    """Basic liveness/readiness check, including a DB round-trip."""
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        conn.close()
        return {"status": "ok", "database": "reachable"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"database unreachable: {e}")


@app.get("/events")
def get_events(
    metric: Optional[str] = Query(None, description="Filter by metric, e.g. 'orders'"),
    category: Optional[str] = Query(None, description="Filter by category, e.g. 'electronics'"),
    limit: int = Query(100, ge=1, le=1000, description="Max rows to return"),
):
    """
    Return the most recent N events, most recent first.
    Optionally filter by metric and/or category.
    """
    if metric is not None and metric not in VALID_METRICS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown metric '{metric}'. Valid values: {sorted(VALID_METRICS)}",
        )

    query = "SELECT event_time, metric, category, value FROM raw_events WHERE 1=1"
    params = []

    if metric is not None:
        query += " AND metric = %s"
        params.append(metric)

    if category is not None:
        query += " AND category = %s"
        params.append(category)

    query += " ORDER BY event_time DESC LIMIT %s"
    params.append(limit)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "event_time": row[0].isoformat(),
            "metric": row[1],
            "category": row[2],
            "value": float(row[3]),
        }
        for row in rows
    ]