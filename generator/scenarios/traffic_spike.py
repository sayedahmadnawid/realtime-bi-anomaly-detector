"""
Simulates a sudden surge in site traffic - e.g. a viral moment, a
marketing blast, or bot/scraper activity. Site-wide (category=None),
since traffic itself has no category.
"""

SCENARIO_NAME = "traffic_spike"
DESCRIPTION = "Site-wide traffic jumps sharply for a short window."

DEFAULT_DURATION_MINUTES = 45
DEFAULT_MAGNITUDE = 3.5  # ~3.5x normal traffic


def apply(generator, start_time, duration_minutes=DEFAULT_DURATION_MINUTES,
          magnitude=DEFAULT_MAGNITUDE):
    anomaly = generator.schedule_anomaly(
        "sudden_spike",
        metric="traffic",
        category=None,
        start_time=start_time,
        duration_minutes=duration_minutes,
        magnitude=magnitude,
    )
    return [anomaly]