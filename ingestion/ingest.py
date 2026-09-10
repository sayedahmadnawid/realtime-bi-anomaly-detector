"""
Ingestion v1: runs the NovaCart generator in a loop and writes each tick's
events directly to Postgres.

No message queue yet (that's Phase 2) — this is the "dumbest possible
version" per docs/roadmap.md Phase 1: generator -> DB, directly.

Simulated time advances by 1 minute per tick. How fast that happens in
real time is controlled by SIM_SPEED_SECONDS_PER_TICK (see infra/docker-
compose.yml) so a full simulated day doesn't take a full real day to
generate.
"""

import logging
import os
import time
from datetime import datetime, timedelta, timezone

from generator.generator import NovaCartGenerator
from ingestion.db import get_connection, insert_events

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("ingest")


def main() -> None:
    sim_speed = float(os.environ.get("SIM_SPEED_SECONDS_PER_TICK", "1"))
    log.info("Starting ingestion: %.2f real seconds per simulated minute", sim_speed)

    conn = get_connection()
    log.info("Connected to Postgres")

    generator = NovaCartGenerator()
    sim_time = datetime.now(timezone.utc)

    try:
        while True:
            events = generator.tick(sim_time)

            try:
                insert_events(conn, events)
            except Exception:
                log.exception("Failed to insert events, rolling back and retrying connection")
                conn.rollback()
                # basic recovery: reconnect if the connection died mid-write
                try:
                    conn.close()
                except Exception:
                    pass
                conn = get_connection()

            log.info(
                "sim_time=%s  wrote %d events (orders=%s)",
                sim_time.isoformat(),
                len(events),
                sum(e["value"] for e in events if e["metric"] == "orders"),
            )

            sim_time += timedelta(minutes=1)
            time.sleep(sim_speed)

    except KeyboardInterrupt:
        log.info("Shutting down (keyboard interrupt)")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
