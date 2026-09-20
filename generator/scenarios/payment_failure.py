"""
Simulates a payment gateway issue: failure rate spikes sharply while
traffic and order *attempts* look completely normal. This is deliberately
a different anomaly shape than revenue_drop - it's not a demand problem,
it's a checkout problem, and a good multivariate/root-cause case later
(Phase 3): traffic normal, orders down, payment_failures up.

Site-wide by default (category=None) to simulate a gateway-level outage
rather than a category-specific issue.
"""

SCENARIO_NAME = "payment_failure"
DESCRIPTION = "Payment failure rate spikes sharply (checkout/gateway issue), independent of traffic."

DEFAULT_DURATION_MINUTES = 30
DEFAULT_MAGNITUDE = 15.0  # failure rate jumps ~15x baseline


def apply(generator, start_time, category=None,
          duration_minutes=DEFAULT_DURATION_MINUTES, magnitude=DEFAULT_MAGNITUDE):
    anomaly = generator.schedule_anomaly(
        "sudden_spike",
        metric="payment_failures",
        category=category,
        start_time=start_time,
        duration_minutes=duration_minutes,
        magnitude=magnitude,
    )
    return [anomaly]