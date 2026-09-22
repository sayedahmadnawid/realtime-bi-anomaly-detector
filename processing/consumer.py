"""
Processing v1: consumes the Redis Stream published by ingestion/ingest.py
and persists each batch of events to Postgres (raw_events).

Uses a Redis Stream consumer group, not a plain read, specifically so
this has real at-least-once delivery semantics:
    - XREADGROUP hands out messages that haven't been acknowledged yet
    - we only XACK a message after the Postgres write succeeds
    - if this process crashes mid-batch, the un-acked message is still
      claimable by a future consumer instead of being silently lost

This is the same durability guarantee a Laravel queue worker gets from
`--tries` + not calling `$job->delete()` until the handler succeeds.
"""

import json
import logging
import os
import time
from datetime import datetime

import redis

from ingestion.db import get_connection, insert_events

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("consumer")

STREAM_KEY = "novacart:events"
GROUP_NAME = "processors"
CONSUMER_NAME = "consumer-1"


def _deserialize(payload: str) -> list[dict]:
    events = json.loads(payload)
    for e in events:
        e["event_time"] = datetime.fromisoformat(e["event_time"])
    return events


def _ensure_group(r: redis.Redis) -> None:
    """Create the consumer group if it doesn't exist yet. mkstream=True
    also creates the stream itself if this is the very first run."""
    try:
        r.xgroup_create(STREAM_KEY, GROUP_NAME, id="0", mkstream=True)
        log.info("Created consumer group '%s' on stream '%s'", GROUP_NAME, STREAM_KEY)
    except redis.ResponseError as e:
        if "BUSYGROUP" in str(e):
            log.info("Consumer group '%s' already exists", GROUP_NAME)
        else:
            raise


def main() -> None:
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        raise RuntimeError("REDIS_URL environment variable is not set")

    r = redis.from_url(redis_url, decode_responses=True)
    r.ping()
    log.info("Connected to Redis")

    _ensure_group(r)

    conn = get_connection()
    log.info("Connected to Postgres")

    try:
        while True:
            # block=5000: wait up to 5s for new messages before looping
            # again (lets us stay responsive to e.g. future shutdown
            # signals without a tight busy-loop)
            response = r.xreadgroup(
                GROUP_NAME, CONSUMER_NAME, {STREAM_KEY: ">"}, count=10, block=5000
            )
            if not response:
                continue

            for _stream_key, messages in response:
                for message_id, fields in messages:
                    try:
                        events = _deserialize(fields["payload"])
                        insert_events(conn, events)
                        r.xack(STREAM_KEY, GROUP_NAME, message_id)
                        log.info(
                            "Processed message %s: %d events written",
                            message_id, len(events),
                        )
                    except Exception:
                        log.exception(
                            "Failed to process message %s - leaving unacked for retry",
                            message_id,
                        )
                        conn.rollback()

    except KeyboardInterrupt:
        log.info("Shutting down (keyboard interrupt)")
    finally:
        conn.close()


if __name__ == "__main__":
    main()