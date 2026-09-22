"""
Ingestion v2: runs the NovaCart generator in a loop and publishes each
tick's events onto a Redis Stream, rather than writing to Postgres
directly. This is the "producer" half of Phase 2's queue architecture -
see processing/consumer.py for the "consumer" half that actually persists
the data.

Decoupling generation from persistence this way means a slow/unavailable
database no longer blocks generation, and multiple consumers could later
read the same stream for different purposes (raw storage, real-time
aggregation, alerting) without the producer knowing or caring.

Simulated time advances by 1 minute per tick. How fast that happens in
real time is controlled by SIM_SPEED_SECONDS_PER_TICK.
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone

import redis

from generator.generator import NovaCartGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("ingest")

STREAM_KEY = "novacart:events"


def _serialize(events: list[dict]) -> str:
    """Redis Stream fields must be strings, so we serialize the whole
    tick's batch of events as one JSON payload (datetimes -> ISO strings)
    rather than one stream entry per event."""
    return json.dumps(
        [{**e, "event_time": e["event_time"].isoformat()} for e in events]
    )


def main() -> None:
    sim_speed = float(os.environ.get("SIM_SPEED_SECONDS_PER_TICK", "1"))
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        raise RuntimeError("REDIS_URL environment variable is not set")

    log.info("Starting ingestion (producer): %.2f real seconds per simulated minute", sim_speed)

    r = redis.from_url(redis_url, decode_responses=True)
    r.ping()
    log.info("Connected to Redis")

    generator = NovaCartGenerator()
    sim_time = datetime.now(timezone.utc)

    try:
        while True:
            events = generator.tick(sim_time)
            r.xadd(STREAM_KEY, {"payload": _serialize(events)})

            log.info(
                "sim_time=%s  published %d events (orders=%s)",
                sim_time.isoformat(),
                len(events),
                sum(e["value"] for e in events if e["metric"] == "orders"),
            )

            sim_time += timedelta(minutes=1)
            time.sleep(sim_speed)

    except KeyboardInterrupt:
        log.info("Shutting down (keyboard interrupt)")


if __name__ == "__main__":
    main()