# KitchenWatch

Won't put dinner on your calendar that your fridge cannot feed.

Built for autonomous kitchen planning: real shelf state in, verified calendar action out.

## What it does

1. You point a camera (or talk) at what is actually in the kitchen.
2. Gemini 3.5 extracts items. Weak guesses never enter the ledger.
3. Cloud Scheduler wakes the agent.
4. Trust is Python rules: every ingredient must already be on the shelf, with enough quantity, and a real expiry in the next 48 hours.
5. If Trust passes, one Google Calendar event is written. If it fails, nothing is written.
6. The same day cannot get a second event.

## Stack

Gemini 3.5 Flash (Vertex, `global`) · Google GenAI SDK · Cloud Run · Firestore · Cloud Scheduler · Google Calendar API

The hosted demo runs on Cloud Run and keeps its runtime settings in Secret Manager.

## Repo map

```
src/kitchenwatch/          models, normalize, trust (no LLM)
tests/                     planted pass / fail / idempotent
fixtures/                  gold inventory + proposed actions
docs/architecture.svg      system diagram
docs/ARCHITECTURE.md
docs/GCP.md
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
gcloud run deploy kitchenwatch --source=. --project=$GCP_PROJECT --region=us-central1
```

Hosted: https://kitchenwatch-466851852100.us-central1.run.app/

## Demo

Use `DEMO_SCRIPT.md` for a short walkthrough of the hosted app, Calendar write, and Cloud Run/Scheduler deployment.

## Status

Live on Cloud Run. The demo kitchen is `demo`.
