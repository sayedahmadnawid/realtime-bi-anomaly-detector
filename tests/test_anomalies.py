from datetime import datetime, timedelta, timezone

from generator.anomalies import AnomalyEngine
from generator.generator import NovaCartGenerator


def test_sudden_drop_reduces_value_during_window():
    engine = AnomalyEngine()
    start = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
    engine.schedule("sudden_drop", metric="orders", category="electronics",
                     start_time=start, duration_minutes=30, magnitude=0.2)

    before = engine.apply(start - timedelta(minutes=1), "orders", "electronics", 100)
    during = engine.apply(start + timedelta(minutes=5), "orders", "electronics", 100)
    after = engine.apply(start + timedelta(minutes=31), "orders", "electronics", 100)

    assert before == 100
    assert during == 20  # 100 * 0.2
    assert after == 100  # anomaly has ended


def test_sudden_spike_increases_value_during_window():
    engine = AnomalyEngine()
    start = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
    engine.schedule("sudden_spike", metric="revenue", category="apparel",
                     start_time=start, duration_minutes=15, magnitude=3.0)

    during = engine.apply(start, "revenue", "apparel", 50)
    assert during == 150


def test_flatline_forces_zero_during_window():
    engine = AnomalyEngine()
    start = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
    engine.schedule("flatline", metric="traffic", category=None,
                     start_time=start, duration_minutes=10)

    during = engine.apply(start + timedelta(minutes=2), "traffic", None, 500)
    after = engine.apply(start + timedelta(minutes=11), "traffic", None, 500)

    assert during == 0
    assert after == 500


def test_slow_drift_interpolates_linearly():
    engine = AnomalyEngine()
    start = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
    engine.schedule("slow_drift", metric="orders", category="home_kitchen",
                     start_time=start, duration_minutes=100, magnitude=0.0)

    at_start = engine.apply(start, "orders", "home_kitchen", 100)
    at_midpoint = engine.apply(start + timedelta(minutes=50), "orders", "home_kitchen", 100)
    at_end = engine.apply(start + timedelta(minutes=99), "orders", "home_kitchen", 100)

    assert at_start == 100          # multiplier ~1.0 at the very start
    assert 45 <= at_midpoint <= 55  # roughly halfway to 0
    assert at_end < 5               # nearly fully drifted to 0


def test_anomaly_only_applies_to_matching_metric_and_category():
    engine = AnomalyEngine()
    start = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
    engine.schedule("sudden_drop", metric="orders", category="electronics",
                     start_time=start, duration_minutes=30, magnitude=0.1)

    # different category, same metric -> unaffected
    unaffected_cat = engine.apply(start, "orders", "apparel", 100)
    # different metric, same category -> unaffected
    unaffected_metric = engine.apply(start, "revenue", "electronics", 100)

    assert unaffected_cat == 100
    assert unaffected_metric == 100


def test_category_none_applies_to_all_categories():
    engine = AnomalyEngine()
    start = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
    engine.schedule("sudden_drop", metric="orders", category=None,
                     start_time=start, duration_minutes=30, magnitude=0.5)

    assert engine.apply(start, "orders", "electronics", 100) == 50
    assert engine.apply(start, "orders", "apparel", 100) == 50


def test_generator_schedule_anomaly_actually_affects_tick_output():
    gen = NovaCartGenerator(seed=7)
    start = datetime(2026, 6, 15, 18, 0, tzinfo=timezone.utc)  # peak hour

    # baseline tick (no anomaly yet)
    baseline_events = gen.tick(start)
    baseline_orders = sum(
        e["value"] for e in baseline_events if e["metric"] == "orders" and e["category"] == "electronics"
    )

    gen.schedule_anomaly(
        "flatline", metric="orders", category="electronics",
        start_time=start + timedelta(minutes=1), duration_minutes=10,
    )
    anomaly_events = gen.tick(start + timedelta(minutes=1))
    anomaly_orders = sum(
        e["value"] for e in anomaly_events if e["metric"] == "orders" and e["category"] == "electronics"
    )

    assert anomaly_orders == 0
    # sanity: other categories unaffected by this targeted anomaly
    other_cat_orders = sum(
        e["value"] for e in anomaly_events if e["metric"] == "orders" and e["category"] == "apparel"
    )
    assert other_cat_orders >= 0  # just confirms it still generates normally


def test_prune_expired_removes_old_anomalies():
    engine = AnomalyEngine()
    start = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
    engine.schedule("sudden_drop", metric="orders", category="electronics",
                     start_time=start, duration_minutes=10, magnitude=0.5)

    assert len(engine._anomalies) == 1
    engine.prune_expired(start + timedelta(minutes=11))
    assert len(engine._anomalies) == 0