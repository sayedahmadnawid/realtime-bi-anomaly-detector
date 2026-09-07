"""Basic sanity tests for the NovaCart generator (Phase 1, v1 — no anomaly
injection yet)."""

from datetime import datetime, timedelta, timezone

from generator import config
from generator.generator import NovaCartGenerator, seasonality_multiplier


def test_seasonality_peak_higher_than_trough():
    peak = datetime(2026, 6, 15, 18, 0, tzinfo=timezone.utc)   # Mon 6pm
    trough = datetime(2026, 6, 15, 4, 0, tzinfo=timezone.utc)  # Mon 4am
    assert seasonality_multiplier(peak) > seasonality_multiplier(trough)


def test_weekend_higher_than_weekday_same_hour():
    # Same hour (noon), Wed vs Sat
    weekday = datetime(2026, 6, 17, 12, 0, tzinfo=timezone.utc)  # Wed
    weekend = datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc)  # Sat
    assert seasonality_multiplier(weekend) > seasonality_multiplier(weekday)


def test_tick_returns_expected_metrics():
    gen = NovaCartGenerator(seed=1)
    ts = datetime(2026, 6, 15, 18, 0, tzinfo=timezone.utc)
    events = gen.tick(ts)
    metrics_seen = {e["metric"] for e in events}
    assert metrics_seen == {"traffic", "signups", "orders", "revenue", "inventory_level"}

    categories_seen = {e["category"] for e in events if e["metric"] == "orders"}
    assert categories_seen == set(config.CATEGORIES.keys())


def test_inventory_never_goes_negative():
    gen = NovaCartGenerator(seed=2)
    ts = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
    for m in range(60 * 24 * 3):  # simulate 3 days of minutes
        events = gen.tick(ts + timedelta(minutes=m))
        for e in events:
            if e["metric"] == "inventory_level":
                assert e["value"] >= 0


def test_values_are_non_negative():
    gen = NovaCartGenerator(seed=3)
    ts = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
    for m in range(120):
        for e in gen.tick(ts + timedelta(minutes=m)):
            assert e["value"] >= 0
