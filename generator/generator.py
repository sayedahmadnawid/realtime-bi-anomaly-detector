"""
NovaCart synthetic event generator (v1).

Produces a realistic baseline of e-commerce activity: orders, revenue,
traffic, signups, and inventory levels, with daily/weekly seasonality,
slow trend growth, category mix, and Gaussian noise.

No anomaly injection yet — that's v2 (see docs/roadmap.md, Phase 2).

Usage:
    from generator.generator import NovaCartGenerator

    gen = NovaCartGenerator()
    events = gen.tick(datetime.now(timezone.utc))
    # events is a list of dicts: {event_time, metric, category, value}
"""

import random
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Optional

from generator import config
from generator.anomalies import AnomalyEngine


def seasonality_multiplier(ts: datetime) -> float:
    """
    Combine hourly weight, weekday weight, and slow trend growth into a
    single multiplier representing "how busy is the business right now,
    relative to baseline peak", ignoring noise.
    """
    hourly = config.HOURLY_WEIGHTS[ts.hour]
    weekday = config.WEEKDAY_WEIGHTS[ts.weekday()]

    days_elapsed = (ts.date() - config.TREND_START_DATE).days
    days_elapsed = max(days_elapsed, 0)
    trend = (1 + config.DAILY_GROWTH_RATE) ** days_elapsed

    return hourly * weekday * trend


def _noisy(value: float, std: float = config.NOISE_STD) -> float:
    """Apply multiplicative Gaussian noise, floored at 0."""
    factor = max(0.0, random.gauss(1.0, std))
    return value * factor


def _sample_count(mean: float) -> int:
    """
    Sample an integer count around a mean using Poisson-like behavior.
    Falls back to a simple noisy-rounded approach to avoid a numpy
    dependency for this small a need.
    """
    if mean <= 0:
        return 0
    noisy_mean = _noisy(mean)
    # Poisson approximation via random.gauss for mean >> 1 is fine here;
    # events are aggregated per-minute so means are usually small-ish.
    return max(0, round(random.gauss(noisy_mean, noisy_mean**0.5 or 0.1)))


@dataclass
class _InventoryState:
    levels: dict = field(default_factory=dict)
    last_restock_date: date = None

    def __post_init__(self):
        if not self.levels:
            self.levels = {
                cat: cfg["starting_inventory"]
                for cat, cfg in config.CATEGORIES.items()
            }


class NovaCartGenerator:
    """
    Stateful generator: call .tick(timestamp) repeatedly (e.g. once per
    simulated minute) to get a fresh batch of events. State (inventory
    levels) persists across calls within one instance.
    """

    def __init__(self, seed: int | None = None):
        if seed is not None:
            random.seed(seed)
        self._inventory = _InventoryState()
        self.anomalies = AnomalyEngine()

    def schedule_anomaly(
        self,
        anomaly_type: str,
        metric: str,
        start_time: datetime,
        duration_minutes: int,
        category: Optional[str] = None,
        magnitude: float = 1.0,
    ):
        """Convenience passthrough so callers don't need to import
        AnomalyEngine directly. See generator/anomalies.py for details."""
        return self.anomalies.schedule(
            anomaly_type=anomaly_type,
            metric=metric,
            start_time=start_time,
            duration_minutes=duration_minutes,
            category=category,
            magnitude=magnitude,
        )


    def _maybe_restock(self, ts: datetime) -> None:
        """Once per day (at hour 3, quiet overnight), restock inventory
        partially back toward its starting level, simulating a warehouse
        replenishment cycle."""
        if ts.hour != 3:
            return
        if self._inventory.last_restock_date == ts.date():
            return
        for cat, cfg in config.CATEGORIES.items():
            target = cfg["starting_inventory"]
            current = self._inventory.levels[cat]
            if current < target:
                # restock 60% of the gap, not a full top-up, so levels
                # still drift realistically rather than resetting sharply
                self._inventory.levels[cat] = current + int(0.6 * (target - current))
        self._inventory.last_restock_date = ts.date()

    def tick(self, ts: datetime) -> list[dict]:
        """
        Generate one batch of events for the given timestamp. Intended to
        be called once per simulated minute.

        Returns a list of event dicts:
            {event_time, metric, category, value}
        `category` is None for site-wide metrics (traffic, signups).
        """
        events = []
        mult = seasonality_multiplier(ts)

        # --- traffic & signups (site-wide) ---
        traffic_mean = config.BASELINE_PER_MINUTE["traffic"] * mult
        traffic_mean = self.anomalies.apply(ts, "traffic", None, traffic_mean)
        traffic = _sample_count(traffic_mean)
        events.append(
            {"event_time": ts, "metric": "traffic", "category": None, "value": traffic}
        )

        signup_mean = traffic * config.SIGNUP_RATE_OF_TRAFFIC
        signup_mean = self.anomalies.apply(ts, "signups", None, signup_mean)
        signups = _sample_count(signup_mean)
        events.append(
            {"event_time": ts, "metric": "signups", "category": None, "value": signups}
        )

        # --- orders, revenue, inventory (per category) ---
        total_orders_mean = config.BASELINE_PER_MINUTE["orders"] * mult
        for cat, cfg in config.CATEGORIES.items():
            cat_order_mean = total_orders_mean * cfg["relative_weight"]
            cat_order_mean = self.anomalies.apply(ts, "orders", cat, cat_order_mean)
            order_count = _sample_count(cat_order_mean)

            revenue = 0.0
            if order_count > 0:
                revenue = order_count * _noisy(cfg["avg_order_value"], std=0.2)
            revenue = self.anomalies.apply(ts, "revenue", cat, revenue)

            events.append(
                {"event_time": ts, "metric": "orders", "category": cat, "value": order_count}
            )
            events.append(
                {"event_time": ts, "metric": "revenue", "category": cat, "value": round(revenue, 2)}
            )

            # inventory decrements by units sold this tick (based on the
            # *true* order count, independent of any revenue/orders anomaly
            # distortion above - inventory anomalies are injected separately)
            self._inventory.levels[cat] = max(
                0, self._inventory.levels[cat] - order_count
            )

            # --- payments ---
            # order_count above represents *successful* orders/payments.
            # failed_mean is independent of order volume - a payment gateway
            # issue can spike failures even while order volume looks normal.
            failed_mean = order_count * config.BASELINE_PAYMENT_FAILURE_RATE
            failed_mean = self.anomalies.apply(ts, "payment_failures", cat, failed_mean)
            failed_count = _sample_count(failed_mean)
            payment_attempts = order_count + failed_count

            events.append(
                {"event_time": ts, "metric": "payment_attempts", "category": cat, "value": payment_attempts}
            )
            events.append(
                {"event_time": ts, "metric": "payment_failures", "category": cat, "value": failed_count}
            )

        self._maybe_restock(ts)

        for cat in config.CATEGORIES:
            level = self.anomalies.apply(
                ts, "inventory_level", cat, self._inventory.levels[cat]
            )
            events.append(
                {
                    "event_time": ts,
                    "metric": "inventory_level",
                    "category": cat,
                    "value": round(level, 0),
                }
            )

        self.anomalies.prune_expired(ts)

        return events


if __name__ == "__main__":
    # Quick manual smoke test: print a few ticks around a plausible peak hour
    gen = NovaCartGenerator(seed=42)
    demo_ts = datetime(2026, 6, 15, 18, 0, tzinfo=timezone.utc)  # Mon 6pm-ish peak
    for i in range(3):
        for e in gen.tick(demo_ts):
            print(e)
        print("---")