# Google Cloud — what you do vs what I do

Account already on this machine: `123abhishekwasekar@gmail.com`  
Billing already open: `017820-F833DF-A6BB7E` (My Billing Account)

We could not create a new project: id `kitchenwatch` is taken globally, and this account is at **project quota**. We are running KitchenWatch on the existing project **`truemerge`** (`466851852100`). Vertex, Firestore (`nam5`), Cloud Run API, and Secret Manager are already there.

The tape shows the Cloud Run URL and the Scheduler job — not the old project name. README states this is a reused GCP project, not leftover TrueMerge product code.

Vertex model: `gemini-3.5-flash` at location `global` (3.5 is not in `us-central1`).

---

## You must do these (I cannot)

### 1. Create a Google Calendar (10 minutes)

Signed into **the same Gmail** you will show on the tape (`123abhishekwasekar@gmail.com`).

1. Open [calendar.google.com](https://calendar.google.com)
2. Left side → **Other calendars** → **+** → **Create new calendar**
3. Name: `KitchenWatch`
4. Description: `Agent writes use-first meals. Do not add events by hand during the demo.`
5. Create calendar
6. Settings for that calendar → **Integrate calendar**
7. Copy **Calendar ID** (looks like `xxxx@group.calendar.google.com`)
8. Paste it into `kitchenwatch/.env` as `KITCHENWATCH_CALENDAR_ID=...`
9. Tell me the Calendar ID in chat (or leave it in `.env` and say done)

Done 2026-08-29: calendar shared with `kitchenwatch-run` as **Make changes and see all event details**. ID is in local `.env` and Secret Manager `kitchenwatch-calendar-id`. Do not commit `.env`.

### 2. Share that calendar with the Cloud Run service account

Service account is already created:

`kitchenwatch-run@truemerge.iam.gserviceaccount.com`

Then:

1. Calendar settings → **KitchenWatch** → **Share with specific people**
2. Add that service account email
3. Permission: **Make changes to events**
4. Send (Google may say the user is not a Google account — that is normal for a service account; save anyway)

Without this share, the agent cannot write. This is the whole Taskmaster proof.

### 3. Budget alert (5 minutes)

1. [console.cloud.google.com/billing/budgets](https://console.cloud.google.com/billing/budgets)
2. Budget name `kitchenwatch-cap`
3. Project: `truemerge` only (this is the KitchenWatch backend)
4. Amount: **$20**
5. Alert at 50% and 90%
6. Email: your Gmail

### 4. Hackathon $150 credits (if you have not)

Devpost Resources tab → credit form. Apply them to this billing account, not a random Qwiklabs project.

### 5. After we deploy — you film these two tabs

Leave them open for the tape:

- Cloud Run service URL ending in `.run.app`
- Cloud Scheduler job `kitchenwatch-watch` (OIDC, not a public cron)

---

## Already done on `truemerge`

- Cloud Scheduler API + Calendar API enabled
- Service accounts `kitchenwatch-run` and `kitchenwatch-scheduler`
- Run SA roles: Vertex (`aiplatform.user`), Firestore (`datastore.user`), Secret Manager accessor, `serviceusage.serviceUsageConsumer` (Calendar API consumer)
- No JSON key on disk

Deployed 2026-08-29:

- Cloud Run `kitchenwatch` → https://kitchenwatch-466851852100.us-central1.run.app
- UI is public (camera + ingest + watch). `/cron/watch` is secret-gated.
- Secrets: calendar id + cron header
- Scheduler `kitchenwatch-watch` daily 07:00 Asia/Kolkata, OIDC + secret header

I will **not** create a JSON key unless Calendar ADC fails. Prefer Cloud Run’s own identity.

---

## What we are not turning on

- Gmail API (that is Google’s own Taskmaster lab)
- App Engine
- A second Firestore database
- Vertex in `us-central1` for Gemini 3.5 (it will 404)
- A new GCP project (quota is full)
