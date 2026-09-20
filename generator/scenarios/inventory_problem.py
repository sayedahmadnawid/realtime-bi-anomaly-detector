"""
Simulates an inventory discrepancy - stock drops faster than sales
explain (shrinkage, miscount, warehouse error). Applied directly to
inventory_level, independent of the actual order-driven decrement, so it
shows up as "inventory fell further than the order volume justifies."
"""

SCENARIO_NAME = "inventory_problems"
DESCRIPTION = "Inventory level drops faster than order volume explains (shrinkage/miscount)."

DEFAULT_CATEGORY = "home_kitchen"
DEFAULT_DURATION_MINUTES = 180
DEFAULT_MAGNITUDE = 0.7  # reported level sits ~30% below what order volume would predict


def apply(generator, start_time, category=DEFAULT_CATEGORY,
          duration_minutes=DEFAULT_DURATION_MINUTES, magnitude=DEFAULT_MAGNITUDE):
    anomaly = generator.schedule_anomaly(
        "sudden_drop",
        metric="inventory_level",
        category=category,
        start_time=start_time,
        duration_minutes=duration_minutes,
        magnitude=magnitude,
    )
    return [anomaly]