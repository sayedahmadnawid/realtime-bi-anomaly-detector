"""
Registry of available scenarios. This is the single place that knows
about every scenario module, so callers (ingestion loop, future API
trigger endpoint, demo scripts) don't need to import each scenario
individually.
"""

from generator.scenarios import (
    inventory_problems,
    normal,
    payment_failure,
    revenue_drop,
    traffic_spike,
)

_SCENARIOS = {
    normal.SCENARIO_NAME: normal,
    revenue_drop.SCENARIO_NAME: revenue_drop,
    traffic_spike.SCENARIO_NAME: traffic_spike,
    payment_failure.SCENARIO_NAME: payment_failure,
    inventory_problems.SCENARIO_NAME: inventory_problems,
}


def list_scenarios() -> dict:
    """Return {name: description} for every registered scenario."""
    return {name: mod.DESCRIPTION for name, mod in _SCENARIOS.items()}


def run_scenario(generator, name: str, start_time, **overrides):
    """
    Apply a named scenario to a generator instance, scheduling whatever
    anomalies that scenario defines starting at `start_time`.

    Raises KeyError with the list of valid names if `name` isn't registered.
    """
    if name not in _SCENARIOS:
        raise KeyError(
            f"Unknown scenario '{name}'. Available: {sorted(_SCENARIOS.keys())}"
        )
    return _SCENARIOS[name].apply(generator, start_time, **overrides)