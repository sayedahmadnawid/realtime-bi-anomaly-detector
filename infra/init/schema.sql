-- Raw event storage for the NovaCart data pipeline.
-- One row per (timestamp, metric, category) reading emitted by the generator.

CREATE TABLE IF NOT EXISTS raw_events (
    id           BIGSERIAL PRIMARY KEY,
    event_time   TIMESTAMPTZ NOT NULL,   -- simulated business time from the generator
    metric       TEXT NOT NULL,          -- 'orders' | 'revenue' | 'traffic' | 'signups' | 'inventory_level'
    category     TEXT,                   -- 'electronics' | 'home_kitchen' | 'apparel' | NULL (site-wide metrics)
    value        NUMERIC NOT NULL,
    inserted_at  TIMESTAMPTZ NOT NULL DEFAULT now()  -- when we actually ingested it
);

-- This is the access pattern every downstream piece (aggregation, detection,
-- API) will use: "give me this metric/category over a time range."
CREATE INDEX IF NOT EXISTS idx_raw_events_metric_category_time
    ON raw_events (metric, category, event_time);