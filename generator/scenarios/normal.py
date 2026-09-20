"""
The "nothing is wrong" scenario. Schedules no anomalies - useful as an
explicit baseline for demos ("here's normal, here's revenue_drop") and as
the default when no scenario is requested.
"""

SCENARIO_NAME = "normal"
DESCRIPTION = "No anomalies. Baseline business activity only."


def apply(generator, start_time, **overrides):
    """No-op: intentionally schedules nothing."""
    return []