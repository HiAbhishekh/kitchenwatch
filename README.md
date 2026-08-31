# KitchenWatch

Won't put dinner on your calendar that your fridge cannot feed.

Hackathon: [All Things Agentic](https://allthingsagentichackathon.devpost.com/) — track **Taskmaster**.  
Greenfield, August 2026. Not a port of Weight Coach, VisionBridge, or TrueMerge.

## What it does

1. You point a camera (or talk) at what is actually in the kitchen.
2. Gemini 3.5 extracts items. Weak guesses never enter the ledger.
3. Cloud Scheduler wakes the agent.
4. Trust is Python rules: every ingredient must already be on the shelf, with enough quantity, and a real expiry in the next 48 hours.
5. If Trust passes, one Google Calendar event is written. If it fails, nothing is written.
6. The same day cannot get a second event.

## Stack

Gemini 3.5 Flash (Vertex, `global`) · Google GenAI SDK · Cloud Run · Firestore · Cloud Scheduler · Google Calendar API

GCP project is `truemerge` (account at project quota; this is a reused cloud project, not leftover TrueMerge product code).

## Repo map

```
src/kitchenwatch/          models, normalize, trust (no LLM)
tests/                     planted pass / fail / idempotent
fixtures/                  gold inventory + proposed actions
docs/architecture.svg      upload this on Devpost
docs/ARCHITECTURE.md
docs/GCP.md
docs/PLAN.md
```

## Local

Needs Python 3.12.

```bash
cd kitchenwatch
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,vision,app]"
pytest
python -m kitchenwatch.render_fixture
python -m kitchenwatch.vision fixtures/fridge_honest.jpg
python -m kitchenwatch.ingest fixtures/fridge_honest.jpg
python -m kitchenwatch.watch --as-of 2026-08-29
uvicorn kitchenwatch.app:app --reload
```

Do not commit `.env`. Calendar ID and cron secret live in Secret Manager.

## Cloud Run (already live)

```bash
gcloud run deploy kitchenwatch --source=. --project=truemerge --region=us-central1
```

Hosted: https://kitchenwatch-466851852100.us-central1.run.app/

## Judge route

Read `JUDGING.md`. Film with `VIDEO.md`. Upload `docs/architecture.svg`.

## Status

Submit **Taskmaster**. Deadline on Devpost is **31 Aug 2026 5:00 PM PT**.
