# The Business: NovaCart

A fictional mid-size online retailer used as the data source for this
platform. Single channel (web), three product categories. This doc is the
source of truth for the data generator, schema, and dashboard content.

## Product categories

| Category | Description | Volume profile |
|---|---|---|
| Electronics | Headphones, chargers, small gadgets | Highest volume, steady |
| Home & Kitchen | Small appliances, kitchenware | Moderate, steady |
| Apparel | Clothing, accessories | Lower baseline, seasonal spikes |

## Core metrics

| Metric | Unit | Description | Example anomaly |
|---|---|---|---|
| `orders` | count | Orders placed | Orders drop 38% vs. expected for a Tuesday afternoon |
| `revenue` | USD | Dollar value of orders | Revenue spikes 3x — possible bulk order or pricing bug |
| `traffic` | count | Site visits/sessions | Traffic flatlines — possible outage |
| `signups` | count | New customer accounts | Signups spike unusually — possible bot activity |
| `inventory_level` | count | Stock remaining, per category | Inventory drops faster than sales explain — shrinkage/error |

All metrics (except `inventory_level`, which is a running stock level) are
counted/summed per time bucket (e.g. per minute, rolled up to 5-min/hourly
for aggregation) and are further broken out by `category` where applicable
(`orders`, `revenue`, `inventory_level`). `traffic` and `signups` are
site-wide, not category-specific.

## Baseline behavior (what "normal" looks like)

The generator must simulate a realistic baseline so anomalies mean
something against it:

- **Daily seasonality** — traffic/orders peak midday–evening, trough
  overnight (roughly following a sine curve or explicit hourly weights).
- **Weekly seasonality** — weekends run higher than weekdays.
- **Slow trend** — gentle overall growth over weeks (simulates a growing
  business), so the detector must adapt to a moving baseline, not a fixed one.
- **Category mix** — Electronics highest volume, Home & Kitchen steady,
  Apparel has occasional seasonal spikes (e.g. simulate a "sale weekend").
- **Noise** — natural random jitter on top of all the above (e.g. Gaussian).

## Anomaly types to support (injectable)

| Type | Description |
|---|---|
| Sudden drop | Metric drops sharply and stays low |
| Sudden spike | Metric jumps sharply and stays high |
| Slow drift | Metric gradually diverges from baseline over time |
| Flatline / missing data | Metric stops updating (simulates an outage/pipeline failure) |

These are triggered via generator config/API so anomalies can be demoed on
demand rather than waited for.
