"""
API v2: raw_events (v1) + anomalies + scenario triggering (v2).

Scenario triggering works by pushing a command onto a Redis list that the
running producer (ingestion/ingest.py) polls on each tick - this is how
we get "trigger an incident on demand" against an already-running system,
the same shape as a queued job: POST enqueues, the long-running worker
picks it up on its next loop.
"""

import json
import os
from typing import Optional

import redis
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ingestion.db import get_connection
from generator.scenarios.registery import list_scenarios

app = FastAPI(title="NovaCart BI API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

VALID_METRICS = {
    "orders", "revenue", "traffic", "signups", "inventory_level",
    "payment_attempts", "payment_failures",
}

SCENARIO_TRIGGER_KEY = "novacart:scenario_triggers"


def _get_redis():
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        raise HTTPException(status_code=503, detail="REDIS_URL not configured")
    return redis.from_url(redis_url, decode_responses=True)


@app.get("/health")
def health():
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
    metric: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
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
        {"event_time": r[0].isoformat(), "metric": r[1], "category": r[2], "value": float(r[3])}
        for r in rows
    ]


@app.get("/anomalies")
def get_anomalies(
    metric: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None, description="'medium' or 'high'"),
    limit: int = Query(50, ge=1, le=500),
):
    """Most recently detected anomalies first."""
    if severity is not None and severity not in {"medium", "high"}:
        raise HTTPException(status_code=400, detail="severity must be 'medium' or 'high'")

    query = """
        SELECT metric, category, window_start, window_end,
               expected_value, actual_value, z_score, severity, detected_at
        FROM anomalies
        WHERE 1=1
    """
    params = []
    if metric is not None:
        query += " AND metric = %s"
        params.append(metric)
    if category is not None:
        query += " AND category = %s"
        params.append(category)
    if severity is not None:
        query += " AND severity = %s"
        params.append(severity)
    query += " ORDER BY detected_at DESC LIMIT %s"
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
            "metric": r[0], "category": r[1],
            "window_start": r[2].isoformat(), "window_end": r[3].isoformat(),
            "expected_value": float(r[4]), "actual_value": float(r[5]),
            "z_score": float(r[6]), "severity": r[7],
            "detected_at": r[8].isoformat(),
        }
        for r in rows
    ]


@app.get("/scenarios")
def get_scenarios():
    """List available named scenarios (see generator/scenarios/)."""
    return list_scenarios()


class ScenarioTriggerRequest(BaseModel):
    category: Optional[str] = None
    duration_minutes: Optional[int] = None
    magnitude: Optional[float] = None


@app.post("/scenarios/{name}/trigger")
def trigger_scenario(name: str, overrides: ScenarioTriggerRequest = ScenarioTriggerRequest()):
    """
    Enqueue a scenario for the running producer to pick up on its next
    tick. Doesn't apply it directly (the API has no access to the
    producer's in-memory generator instance) - it just publishes the
    command; ingestion/ingest.py polls for and applies it.
    """
    available = list_scenarios()
    if name not in available:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scenario '{name}'. Available: {sorted(available.keys())}",
        )

    command = {"scenario": name, **overrides.model_dump(exclude_none=True)}

    r = _get_redis()
    r.rpush(SCENARIO_TRIGGER_KEY, json.dumps(command))

    return {"status": "queued", "command": command}