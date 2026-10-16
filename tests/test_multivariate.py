from datetime import datetime, timedelta, timezone

from detection.multivariate import evaluate_latest_bucket

START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_rows(n_baseline=24, candidate=(1000, 20, 100, 5000)):
    """Fake rows, oldest first: [time, traffic, signups, orders, revenue].
    Baseline = normal days with a little wobble, then the candidate bucket,
    then one extra row for the bucket that is still filling."""
    rows = []
    for i in range(n_baseline):
        wobble = (i % 3) - 1                     # -1, 0, +1
        traffic = 1000 + wobble * 20
        orders = 100 + wobble * 5
        revenue = orders * (50 + wobble * 2)     # about $50 per order
        rows.append([START + timedelta(minutes=5 * i), traffic, 20, orders, revenue])

    t = START + timedelta(minutes=5 * n_baseline)
    rows.append([t, *candidate])                              # judged bucket
    rows.append([t + timedelta(minutes=5), 100, 2, 10, 500])  # still filling: ignored
    return rows


def by_name(results):
    return {r[0]: r for r in results}     # (name, time, z, expected, actual)


def test_normal_bucket_flags_nothing():
    results = by_name(evaluate_latest_bucket(make_rows()))
    assert abs(results["orders_per_visitor"][2]) < 3
    assert abs(results["revenue_per_order"][2]) < 3


def test_traffic_spike_with_flat_orders_is_flagged_negative():
    rows = make_rows(candidate=(4000, 20, 100, 5000))   # traffic x4, orders flat
    results = by_name(evaluate_latest_bucket(rows))
    assert results["orders_per_visitor"][2] < -3         # far below normal
    assert abs(results["revenue_per_order"][2]) < 3      # unaffected


def test_revenue_per_order_drop_is_flagged():
    rows = make_rows(candidate=(1000, 20, 100, 2500))   # same orders, half the revenue
    results = by_name(evaluate_latest_bucket(rows))
    assert results["revenue_per_order"][2] < -3
    assert abs(results["orders_per_visitor"][2]) < 3


def test_too_few_rows_returns_empty_list():
    assert evaluate_latest_bucket(make_rows(n_baseline=3)) == []


def test_judges_second_to_last_row_not_the_filling_one():
    rows = make_rows()
    results = evaluate_latest_bucket(rows)
    assert results[0][1] == rows[-2][0]                  # bucket_time is the candidate's