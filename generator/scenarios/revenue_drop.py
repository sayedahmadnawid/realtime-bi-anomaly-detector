"""
Simulates a sales slump in one category - e.g. "Sales dropped 38%
compared with the expected level" (docs/business.md's example anomaly).

Implementation note: we only need to inject the drop on `orders`. Revenue
is computed downstream from the (already-anomaly-affected) order count in
generator.tick(), so it falls out of the order drop automatically - a
revenue_drop scenario doesn't need its own separate revenue injection to
produce a coherent "sales AND revenue are both down" story.
"""

SCENARIO_NAME = "revenue_drop"
DESCRIPTION = "Orders (and the revenue that follows from them) drop sharply in one category."

DEFAULT_CATEGORY = "electronics"
DEFAULT_DURATION_MINUTES = 120
DEFAULT_MAGNITUDE = 0.62  # ~38% reduction


def apply(generator, start_time, category=DEFAULT_CATEGORY,
          duration_minutes=DEFAULT_DURATION_MINUTES, magnitude=DEFAULT_MAGNITUDE):
    anomaly = generator.schedule_anomaly(
        "sudden_drop",
        metric="orders",
        category=category,
        start_time=start_time,
        duration_minutes=duration_minutes,
        magnitude=magnitude,
    )
    return [anomaly]