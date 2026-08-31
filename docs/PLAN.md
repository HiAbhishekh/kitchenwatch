# 15-day plan

Day sessions: GCP, deploy, camera, film.  
Night sessions: Trust tests, prompts, fixtures, tape cuts.

| Day | Outcome | Done when |
|---|---|---|
| 1 | Repo + Trust + APIs | `pytest` 14 green. You share the KitchenWatch calendar with `kitchenwatch-run@truemerge.iam.gserviceaccount.com`. |
| 2 | Extract | Planted fridge photo → Gemini 3.5 vision → accept_extract. Offline tests green; live run writes fixtures/extract_live_honest.json. |
| 3 | Ledger | POST /ingest + `python -m kitchenwatch.ingest`. Live write to `kitchens/demo/items`. |
| 4 | ADK watch graph | retrieve → plan → trust → write → verify. Tests: nothing due / chicken blocked / one event. |
| 5 | Calendar | Live `python -m kitchenwatch.watch --as-of 2026-08-29` writes the KitchenWatch calendar. |
| 6 | Cloud Run + Scheduler | https://kitchenwatch-466851852100.us-central1.run.app — private. Job `kitchenwatch-watch` 07:00 IST, OIDC. |
| 7 | Camera UI | Live at Cloud Run `/`. Capture or choose photo. Run watch is the same path as cron. |
| 8 | Voice | `/ingest-voice` + Record voice on the UI. Planted wav through Gemini 3.5. |
| 9 | Live planted | Honest write. Chicken blocked. Cron twice = one event. |
| 10 | Jobs UI | Judge can see job_id, verdict, event_id without an API key dance. |
| 11 | Docs | Architecture diagram + README spin-up. |
| 12 | Tape v1 | 12 seconds: milk in frame → calendar event exists. GCP in the same take. |
| 13 | Fix what the tape shows | No new features. |
| 14 | Submit pack | JUDGING.md, `#AllThingsAgenticHackathon` post, short public build note. |
| 15 | Submit Taskmaster | Then min instances 0, Scheduler paused. |

## Kill list (do not sneak back in)

Calorie goals. Recipe blog. Instacart. Gmail. Chat meal planner. Agent Registry. Model Armor slideware. A second kitchen. A second write type.

## Prize play (reminder)

Enter **Taskmaster**. Build so **Architecture** and **Multimodal** can still catch us. Honorable is the honest floor. Grand is not a plan.
