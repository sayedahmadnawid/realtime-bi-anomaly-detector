-- Adds the anomalies table for the detection engine (Phase 2).
--
-- This is a MIGRATION, not part of infra/init/ - your Postgres volume
-- already exists from Phase 1, and Postgres only runs infra/init/*.sql
-- on a completely fresh (empty) data directory. Apply this by hand:
--
--   docker compose exec -T postgres psql -U novacart -d bi_anomaly < infra/migrations/001_add_anomalies_table.sql
--
-- (or open a psql shell in the postgres container and paste it in)

CREATE TABLE IF NOT EXISTS anomalies (
    id              BIGSERIAL PRIMARY KEY,
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT now(),  -- when the detector found it
    metric          TEXT NOT NULL,
    category        TEXT,                                -- NULL for site-wide metrics
    window_start    TIMESTAMPTZ NOT NULL,                 -- the 5-min bucket being evaluated
    window_end      TIMESTAMPTZ NOT NULL,
    expected_value  NUMERIC NOT NULL,                     -- baseline mean over recent history
    actual_value    NUMERIC NOT NULL,                     -- observed value in this window
    z_score         NUMERIC NOT NULL,                     -- (actual - expected) / stddev
    severity        TEXT NOT NULL                         -- 'medium' | 'high'
);

CREATE INDEX IF NOT EXISTS idx_anomalies_metric_category_window
    ON anomalies (metric, category, window_start);

CREATE INDEX IF NOT EXISTS idx_anomalies_detected_at
    ON anomalies (detected_at DESC);