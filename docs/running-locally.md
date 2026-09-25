# Running Locally

## Start everything

```bash
cd infra
docker compose up --build
```

Then:
- Dashboard: http://localhost:5173
- API docs: http://localhost:8000/docs
- Postgres: localhost:5432 (user/pass/db: `novacart` / `novacart` / `bi_anomaly`)

## Simulation speed

`SIM_SPEED_SECONDS_PER_TICK` (set on the `app` service in `infra/docker-compose.yml`)
controls how fast simulated business time moves relative to real time. Each
tick advances the simulation by 1 simulated minute.

| Value | Meaning | 1 simulated day takes |
|---|---|---|
| `1` | 1 real second = 1 simulated minute (60x) | ~24 real minutes |
| `5` | 1 real second = 12 simulated seconds (12x) | ~2 real hours |
| `60` | 1 real second = 1 simulated second (1x) | ~24 real hours |

**Lower (faster) is better for:** quickly building up the 30+ minutes of
simulated history the detector needs before it can evaluate anything, and
for rapid iteration while developing the generator/detector themselves.

**Higher (slower) is better for:** demos. At `1`, the dashboard is
effectively time-lapsing — multiple simulated minutes pass between two
consecutive 3-second dashboard polls, which looks chaotic rather than
"live." Something like `5` makes the dashboard feel like an actual
real-time monitor while still reaching a useful baseline in a few minutes.

Change it, then:
```bash
docker compose up -d --build app
```
(only `app` needs to restart - the other services don't care about this value)

## Resetting the database

Useful before a demo, or any time test data has piled up and you want a
clean slate. This wipes **all** data (raw_events, anomalies) - the schema
gets recreated automatically from `infra/init/schema.sql` on next startup.

```bash
docker compose down
docker volume ls              # find the postgres volume, usually <folder>_pg_data
docker volume rm infra_pg_data
docker compose up --build
```

If you've applied `infra/migrations/*.sql` by hand before (e.g. the
anomalies table), you do NOT need to re-apply them after a volume reset -
a fresh volume runs everything in `infra/init/` automatically, and that
file is kept in sync with the migrations (see infra/migrations/README
convention: init/schema.sql = current full schema, migrations/ = the
incremental steps to get an *existing* volume there without wiping it).

## Triggering a scenario live

```bash
curl http://localhost:8000/scenarios

curl -X POST http://localhost:8000/scenarios/revenue_drop/trigger \
  -H "Content-Type: application/json" -d '{"duration_minutes": 20}'
```

Watch it get picked up:
```bash
docker compose logs -f app        # look for "Triggered scenario ..."
docker compose logs -f detector   # look for "ANOMALY ..." (WARNING level)
```

Then check:
```bash
curl http://localhost:8000/anomalies
```

**Timing depends on `SIM_SPEED_SECONDS_PER_TICK`** - the detector only
evaluates the most recently *completed* 5-simulated-minute bucket, checked
every 15 real seconds. At speed `1` (60x), that's ~5-10 real seconds after
triggering. At speed `5` (12x), closer to ~30-60 real seconds. Also
remember the detector needs 30+ minutes of simulated history to exist
*before* your trigger, or it won't evaluate anything yet regardless of
the anomaly.