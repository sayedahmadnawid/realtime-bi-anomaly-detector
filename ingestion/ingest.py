"""
Ingestion v2: runs the NovaCart generator in a loop and publishes each
tick's events onto a Redis Stream, rather than writing to Postgres
directly. Also polls a Redis list each tick for scenario-trigger commands
queued via POST /scenarios/{name}/trigger, so incidents can be demoed on
an already-running system.
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone

import redis

from generator.generator import NovaCartGenerator
from generator.scenarios.registery import run_scenario

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("ingest")

STREAM_KEY = "novacart:events"
SCENARIO_TRIGGER_KEY = "novacart:scenario_triggers"


def _serialize(events: list[dict]) -> str:
    return json.dumps(
        [{**e, "event_time": e["event_time"].isoformat()} for e in events]
    )


def _check_for_triggered_scenarios(r: redis.Redis, generator: NovaCartGenerator, sim_time: datetime) -> None:
    """Non-blocking: pop and apply any scenario commands queued via
    POST /scenarios/{name}/trigger. LPOP returns None immediately if the
    list is empty, so this doesn't slow down the tick loop."""
    while True:
        raw = r.lpop(SCENARIO_TRIGGER_KEY)
        if raw is None:
            return
        try:
            command = json.loads(raw)
            name = command.pop("scenario")
            run_scenario(generator, name, sim_time, **command)
            log.warning("Triggered scenario '%s' at sim_time=%s with %s", name, sim_time.isoformat(), command)
        except Exception:
            log.exception("Failed to apply triggered scenario command: %s", raw)

// 
def main() -> None:
    sim_speed = float(os.environ.get("SIM_SPEED_SECONDS_PER_TICK", "1"))
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        raise RuntimeError("REDIS_URL environment variable is not set")

    log.info("Starting ingestion (producer): %.2f real seconds per simulated minute", sim_speed)

    r = redis.from_url(redis_url, decode_responses=True)
    r.ping()
    log.info("Connected to Redis")
// 
    generator = NovaCartGenerator()
    sim_time = datetime.now(timezone.utc)

// 
    try:
        while True:
            _check_for_triggered_scenarios(r, generator, sim_time)

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