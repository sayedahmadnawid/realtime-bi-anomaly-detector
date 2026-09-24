# Roadmap

## Phase 0 — Define the business
Fictional mid-size e-commerce company. Core metrics: orders, revenue, traffic,
inventory, signups. Multiple channels (web/mobile) and categories, so
anomalies can be channel/category-specific, not just global.

## Phase 1 — Day 1 skeleton
- [ ] Project setup (Python env, Docker, git)
- [x] Data generator v1 (single event, baseline seasonality + noise)
- [x] PostgreSQL (Docker) — raw events table
- [x] Ingestion v1 — generator writes directly to Postgres
- [x] API v1 — FastAPI, read last N rows
- [x] Dashboard v1 — single React page, polls API, line chart

Goal: prove the end-to-end loop works, even if "dumb."

## Phase 2 — MVP
- [ ] Data generator v2 — seasonality, trend, noise, injectable anomaly modes
      (sudden drop, sudden spike, slow drift, flatline)
+ [x] Message queue (Redis Streams or RabbitMQ) between generator and processing
+ [x] Processing worker — consumes queue, writes raw events
      (time-bucketing done at query time by the detection engine, not
      pre-aggregated — raw_events is already at 1-min granularity)
- [x] Anomaly detection v1 (statistical) — moving avg + z-score, seasonal baseline
- [ ] API v2 — metrics, time-series, anomalies list/detail endpoints
- [ ] Dashboard v2 — charts with anomaly markers, live anomaly feed, filters
- [ ] Alerting v1 — Slack webhook / email on detected anomaly
- [ ] Deploy to AWS (smallest footprint: ECS/EC2 + RDS + S3 + SES/SNS)

Goal: demoable, deployable, honestly-described product.

## Phase 3 — Advanced / AI layer (pick 2–3, not all)
- [ ] ML-based detection (Isolation Forest / Prophet) alongside statistical
- [ ] Multivariate / ratio anomaly detection (e.g. traffic normal, conversion collapsed)
- [ ] Root-cause hints (correlated metric/category surfacing)
- [ ] Forecasting (expected band on dashboard, feeds detection)
- [ ] Scale streaming layer (Kafka/Kinesis, windowed processing)
- [ ] Alert intelligence (dedup, severity tiers, suppression during known events)
- [ ] Auth + multi-tenant dashboard

## Discipline
Do not start Phase 3 until Phase 2 is deployed and demoable end-to-end.
