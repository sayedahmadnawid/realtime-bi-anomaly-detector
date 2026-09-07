"""
Static configuration for the NovaCart data generator.

Keeping these numbers in one place makes the generator's behavior easy to
reason about and easy to tune later without touching generation logic.
"""

from datetime import date

# --- Categories -------------------------------------------------------
# relative_weight: share of orders/revenue/inventory activity for this
# category, before seasonality/noise is applied. Must roughly sum to 1.0.
CATEGORIES = {
    "electronics": {
        "relative_weight": 0.5,
        "avg_order_value": 65.0,
        "starting_inventory": 5000,
    },
    "home_kitchen": {
        "relative_weight": 0.3,
        "avg_order_value": 40.0,
        "starting_inventory": 3000,
    },
    "apparel": {
        "relative_weight": 0.2,
        "avg_order_value": 30.0,
        "starting_inventory": 4000,
    },
}

# --- Baseline volume (site-wide, before category split) ---------------
# These are "typical" per-minute rates at the *peak* hour of a *typical*
# weekday. Seasonality multipliers (below) scale down from this peak.
BASELINE_PER_MINUTE = {
    "orders": 4.0,
    "traffic": 40.0,
    "signups": 0.8,
}

# --- Daily seasonality --------------------------------------------------
# Multiplier per hour of day (0-23), roughly following typical e-commerce
# traffic: low overnight, rising through morning, peak evening.
HOURLY_WEIGHTS = {
    0: 0.15, 1: 0.10, 2: 0.08, 3: 0.07, 4: 0.07, 5: 0.10,
    6: 0.20, 7: 0.35, 8: 0.50, 9: 0.65, 10: 0.75, 11: 0.80,
    12: 0.85, 13: 0.80, 14: 0.75, 15: 0.75, 16: 0.80, 17: 0.90,
    18: 1.00, 19: 1.00, 20: 0.95, 21: 0.80, 22: 0.55, 23: 0.30,
}

# --- Weekly seasonality --------------------------------------------------
# Multiplier per weekday, Monday=0 ... Sunday=6. Weekends run higher.
WEEKDAY_WEIGHTS = {
    0: 0.90,  # Mon
    1: 0.90,  # Tue
    2: 0.92,  # Wed
    3: 0.95,  # Thu
    4: 1.05,  # Fri
    5: 1.20,  # Sat
    6: 1.15,  # Sun
}

# --- Slow trend -----------------------------------------------------------
# Simulates gentle business growth over time. Expressed as a daily growth
# rate applied from TREND_START_DATE. E.g. 0.0015 ~= +0.15%/day ~= +5%/month.
TREND_START_DATE = date(2026, 1, 1)
DAILY_GROWTH_RATE = 0.0015

# --- Noise -----------------------------------------------------------------
# Relative standard deviation of Gaussian noise applied on top of the
# computed baseline (e.g. 0.15 = +/-15% typical jitter).
NOISE_STD = 0.15

# Signups as a fraction of traffic (rough conversion-to-signup rate),
# with its own small independent noise applied separately.
SIGNUP_RATE_OF_TRAFFIC = 0.02
