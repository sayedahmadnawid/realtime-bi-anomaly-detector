# Demo Script

A concrete, timed walkthrough for showing this project live — in an
interview, a portfolio call, or just to yourself before you rely on it.
Written assuming `SIM_SPEED_SECONDS_PER_TICK: "5"` (see
[running-locally.md](running-locally.md) for why that value).

## Before the call: pre-warm it

Anomaly detection needs ~30 minutes of simulated history before it can
evaluate anything at all — that's ~2.5 real minutes at speed `5`. Don't
start cold in front of someone. 5-10 minutes before you're on:

```bash
cd infra
docker compose up -d --build
```

Open `http://localhost:5173` once, just to confirm the dashboard is
loading and the chart is moving. Leave it running in a browser tab.

## The walkthrough (~4-5 minutes)

**1. Orient them (30s).** Open the dashboard. Say what it is in one
breath: *"This simulates a mid-size e-commerce business — orders,
revenue, traffic — and automatically detects when something goes wrong,
the way a real ops/BI tool would."* Point at the live chart updating.

**2. Show the architecture, briefly (30s).** Don't over-explain. One
sentence: *"It's a real event pipeline — a generator publishes to Redis
Streams, a worker persists to Postgres, a separate detector evaluates a
statistical baseline every few seconds, and alerts go to Slack."* Have
the architecture diagram from the README ready to share your screen if
they want more.

**3. Trigger a real incident, live (the centerpiece).** Switch the
dashboard's dropdowns to **Metric: orders, Category: electronics**, then
run:
```bash
curl -X POST http://localhost:8000/scenarios/revenue_drop/trigger \
  -H "Content-Type: application/json" -d '{"duration_minutes": 20}'
```
Say: *"That just told the running system to simulate a sales crash in
electronics — no restart, no redeploy, it's injected live."*

**4. Wait and narrate (~30-60s real time at speed 5).** While it
processes: *"The detector re-evaluates every 15 seconds, comparing the
latest 5-minute window against a 2-hour rolling baseline."* This is a
natural moment to mention the median/MAD story if they seem technical:
*"I actually switched from mean/stddev to median/MAD here after testing
exposed a real bug — a short anomaly sitting inside the baseline's own
lookback window was contaminating the baseline enough to mask itself."*

**5. Point at the result.** A shaded red/amber band should appear on the
chart over the dip, and a new card should appear in the live anomaly feed
panel. Say what it shows: *"Expected ~21 orders, actual ~4, that's the
z-score, and there's the severity."* If you've configured
`SLACK_WEBHOOK_URL`, switch to Slack and show the message landing there
too — that's usually the most memorable beat of the whole demo.

**6. Show one more scenario if there's time.** `payment_failure` is the
best second choice, because it tells a different story than the first:
```bash
curl -X POST http://localhost:8000/scenarios/payment_failure/trigger \
  -H "Content-Type: application/json" -d '{"duration_minutes": 15}'
```
Say: *"This one's deliberately different — traffic and order attempts
stay completely normal, only the payment failure rate spikes. It's a
checkout problem, not a demand problem, and the detector catches it as an
independent signal rather than a rescaled copy of the first anomaly."*

**7. Close with what's deliberate, not missing.** If asked about
deployment: *"I designed this to map cleanly to AWS — ECS Fargate, RDS,
ElastiCache, ALB — but I run it locally via Docker Compose to avoid
paying for infrastructure on a personal project. That's a cost decision,
not a capability gap."* If asked what's next: *"Phase 3 would add
ML-based detection — Isolation Forest or Prophet — and multivariate
root-cause correlation, but I didn't want to layer that on before the
statistical foundation was solid and provably correct."*

## If something doesn't cooperate live

- **No anomaly showing up after ~90s:** check `docker compose logs app |
  grep -i triggered` — confirms the trigger reached the producer. If
  that's missing, the API→Redis leg is the problem, not detection.
- **Containers not healthy:** `docker compose ps` — this has happened
  before (a crash-looping container), and you already know how to debug
  it from `docker compose logs <service>`.
- **Worst case:** you have a real, previously-recorded anomaly already
  sitting in `/anomalies` from earlier testing — `curl
  http://localhost:8000/anomalies` and walk through that instead of a
  live trigger. A working system with saved evidence beats a live demo
  that stalls.

## One-liner to reset before a repeat demo

```bash
docker compose down
docker volume rm <your_pg_volume_name>   # docker volume ls to find it
docker compose up -d --build
```
Then wait the ~2.5 minutes for baseline history before triggering again.