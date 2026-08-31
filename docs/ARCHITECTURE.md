# Architecture

```
[camera / voice]                 [Cloud Scheduler 07:00]
        |                                  |
        v                                  v
 POST /ingest                         POST /cron/watch
        |                                  |
 Gemini 3.5 extract                   Retrieve (Firestore, not a dump)
 items confidence >= 0.7                     |
        |                              Plan (Gemini, one cook)
        v                                  |
 Firestore ledger                    Trust (Python, no LLM)
 kitchen_id / item_id                      |
                                     fail → job trust_fail, no write
                                     pass → Calendar.insert
                                           |
                                     Verify Calendar.get
                                           |
                                     job written + event_id
```

## Why two paths

Ingest is multimodal and user-present. Watch is the autonomous background workflow. Keeping them separate makes the write path easier to reason about and test.

## Watch graph (production is `run_watch`, not ADK)

Required framework in production: **Google GenAI SDK** (vision, voice, plan).  
`adk_watch.py` names the same five steps; Cloud Run and Scheduler call `run_watch`.

| Step | Kind | Job |
|---|---|---|
| Retrieve | tool / code | Load ledger. Return items expiring in 48h plus the rest of the shelf for sides. |
| Plan | Gemini 3.5 | One `ProposedAction`. May only cite `item_id`s from retrieve. |
| Trust | code | Rules below. Uncertain = fail. |
| Write | tool | Calendar.insert. Idempotent on `job_id`. |
| Verify | tool | Calendar.get. Missing event → `verify_fail`. |

Extract is **not** on this graph. It runs only on `/ingest`.

## Trust (the product)

Implemented in `src/kitchenwatch/trust.py`. Tests in `tests/test_trust.py`.

1. `reason_item_id` exists on the ledger.
2. That item has a real `expiry`.
3. That expiry is on or before `as_of + 2 days`.
4. Every `uses[]` item exists on the ledger after normalize.
5. Units match exactly (`count` / `g` / `ml`).
6. `qty` needed ≤ qty on the shelf.
7. `uses` is non-empty. Title is non-empty.

Gemini does not get a vote here.

## Idempotency

`job_id = watch:{kitchen_id}:{YYYY-MM-DD}`

If a job is already `written` with an `event_id`, Watch returns that event. It does not insert a second one. This keeps scheduler retries from creating duplicate Calendar events.

## State

Firestore collections:

- `kitchens/{kitchen_id}/items/{item_id}` — ledger
- `kitchens/{kitchen_id}/jobs/{job_id}` — watch results

The application keeps only the state it needs for the kitchen ledger and watch results.

## Writes we allow

One kind: `cook` → one Google Calendar event on the shared KitchenWatch calendar.

We do not send Gmail. We do not open Jira. We do not scrape Instacart.

## Honest limits

- One demo kitchen (`demo`).
- Synonym map is a small table, not a food ontology.
- Calendar is a service-account-shared calendar, not the user’s whole personal calendar (no OAuth token that dies in 7 days).
- Prototype, not a consumer app.
