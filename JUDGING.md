# 1-minute judge route

Hosted: https://kitchenwatch-466851852100.us-central1.run.app/

No API key. One kitchen (`demo`).

## Tape path (12 seconds)

1. Open the URL. Click **Reset demo shelf**.
2. Optional: **Choose photo** → `fixtures/fridge_honest.jpg` (generate with `python -m kitchenwatch.render_fixture`) or **Record voice** (speak, then **Stop voice** — or wait 12s). Mic blocked: **Choose voice memo**.
3. **Run watch**. Do not click through a chat.
4. Google Calendar **KitchenWatch** already open. If today already wrote, UI shows `skipped_idempotent` and the same `calendar_event_id` — that is the Scheduler retry rule. To force a new insert, set the date picker to tomorrow, then Run watch.
5. Flash Cloud Run + Cloud Scheduler (`kitchenwatch-watch`, 07:00 IST, OIDC, last cron 200).

## Fail-closed (10 seconds)

Same shelf. If a plan names chicken (not on the ledger), status is `trust_fail`. No new calendar event.

## What is not an LLM

Trust is Python (`src/kitchenwatch/trust.py`). Uncertain extract (`confidence < 0.7`) never enters Firestore. Same `job_id` (`watch:{kitchen}:{YYYY-MM-DD}`) does not insert twice.

## Stack

Gemini 3.5 Flash via Vertex (`global`) and the **Google GenAI SDK**. Cloud Run, Firestore, Cloud Scheduler, Google Calendar. GCP project `truemerge` is a reused cloud project (account at project quota), not leftover TrueMerge product code.

## Honest limits

One demo kitchen. Small synonym map. Shared service-account calendar, not the user's full personal calendar. Prototype, not a consumer app. ADK `SequentialAgent` in `adk_watch.py` names the same five steps; **production watch is `run_watch`** (same order).
