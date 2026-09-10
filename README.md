# Real-Time BI & Anomaly Detection Platform

A real-time business intelligence platform that ingests business event data
(orders, revenue, traffic, inventory) through a streaming pipeline, detects
anomalies using statistical and ML-based methods, and surfaces them through
a live dashboard and alerts.

Built as a deliberate technical counterpart to a prior CRUD/AI-search project:
this one focuses on Python, data engineering, streaming architecture, and
statistics/ML rather than REST CRUD + vector search.

## Status

🚧 Early scaffold — see [docs/roadmap.md](docs/roadmap.md) for the phased plan.

## Architecture

```
Data Generator (synthetic business events)
        ↓
Ingestion (producer)
        ↓
Message Queue / Streaming (Redis Streams / Kafka)
        ↓
Processing (Python consumer — aggregation, rollups)
        ↓
PostgreSQL (time-series-oriented storage)
        ↓
Anomaly Detection Engine (statistical → ML)
        ↓
REST API (FastAPI)
        ↓
Dashboard (React)
        ↓
Alerts (Slack / email)
```

## Repo layout

| Folder | Purpose |
|---|---|
| `generator/` | Synthetic business event generator, with injectable anomalies |
| `ingestion/` | Producer(s) that push generated events onto the queue |
| `processing/` | Consumer(s) that read the queue, aggregate, and persist |
| `detection/` | Anomaly detection engine (statistical, later ML) |
| `api/` | FastAPI service exposing metrics, time-series, and anomalies |
| `dashboard/` | React frontend |
| `infra/` | Docker Compose, AWS/IaC, deployment configs |
| `docs/` | Design docs: architecture, data model, roadmap, cost estimates |
| `tests/` | Test suites |
| `scripts/` | One-off / dev utility scripts |

## Getting started

_Coming online as Phase 1 is built out — see roadmap._

## Roadmap

See [docs/roadmap.md](docs/roadmap.md) for the full Day 1 → MVP → Advanced plan.


real-time-bi/
│
├── api/
│   ├── app/
│   │   ├── main.py
│   │   ├── routes/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── dependencies.py
│   └── tests/
│
├── dashboard/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── types/
│   └── package.json
│
├── generator/
│   ├── events/
│   │   ├── orders.py
│   │   ├── payments.py
│   │   └── traffic.py
│   ├── scenarios/
│   │   ├── normal.py
│   │   ├── revenue_drop.py
│   │   ├── payment_spike.py
│   │   └── traffic_spike.py
│   └── main.py
│
├── ingestion/
│   ├── producers/
│   ├── consumers/
│   ├── schemas/
│   └── main.py
│
├── processing/
│   ├── metrics/
│   ├── features/
│   ├── anomaly/
│   │   ├── statistical.py
│   │   ├── isolation_forest.py
│   │   └── detector.py
│   └── main.py
│
├── infra/
│   ├── docker/
│   ├── postgres/
│   ├── kafka/
│   └── docker-compose.yml
│
├── docs/
│   ├── architecture.md
│   ├── data-model.md
│   ├── api.md
│   ├── anomaly-detection.md
│   └── decisions.md
│
├── scripts/
│   ├── setup.sh
│   ├── reset.sh
│   └── seed.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── .env.example
├── .gitignore
├── requirements.txt
├── docker-compose.yml
└── README.md