# Google Cloud setup

KitchenWatch runs as a small Cloud Run service with Firestore state, Secret Manager configuration, Cloud Scheduler, Vertex AI, and Google Calendar API.

Default deployment settings:

- Project: set with `GCP_PROJECT`
- Region: `us-central1`
- Vertex location: `global`
- Model: `gemini-3.5-flash`
- Cloud Run service: `kitchenwatch`
- Scheduler job: `kitchenwatch-watch`

## Calendar

Create a dedicated Google Calendar for the agent output:

1. Open [calendar.google.com](https://calendar.google.com).
2. Left side → **Other calendars** → **+** → **Create new calendar**
3. Name: `KitchenWatch`
4. Description: `Agent writes use-first meals.`
5. Create calendar
6. Settings for that calendar → **Integrate calendar**
7. Copy **Calendar ID** (looks like `xxxx@group.calendar.google.com`)
8. Put it in `.env` locally as `KITCHENWATCH_CALENDAR_ID=...`
9. Store it in Secret Manager for Cloud Run.

Share that calendar with the Cloud Run service account:

- `kitchenwatch-run@<your-gcp-project-id>.iam.gserviceaccount.com`
- Permission: **Make changes to events**

Without this share, the service can plan but cannot write Calendar events.

## Cloud resources

Required APIs:

- Cloud Run
- Firestore
- Vertex AI
- Secret Manager
- Cloud Scheduler
- Google Calendar API

Service accounts:

- `kitchenwatch-run` for Cloud Run
- `kitchenwatch-scheduler` for Scheduler OIDC calls

Run service account roles:

- Vertex AI User
- Cloud Datastore User
- Secret Manager Secret Accessor
- Service Usage Consumer

Scheduler service account:

- Cloud Run Invoker on the `kitchenwatch` service

## Deploy

```bash
gcloud run deploy kitchenwatch \
  --source=. \
  --project=$GCP_PROJECT \
  --region=us-central1 \
  --service-account=kitchenwatch-run@$GCP_PROJECT.iam.gserviceaccount.com \
  --set-env-vars=GCP_PROJECT=$GCP_PROJECT,GCP_LOCATION=global,GEMINI_MODEL=gemini-3.5-flash,GEMINI_USE_VERTEX=1,KITCHEN_ID=demo,KITCHENWATCH_TZ=Asia/Kolkata \
  --set-secrets=KITCHENWATCH_CALENDAR_ID=kitchenwatch-calendar-id:latest,WATCH_CRON_SECRET=kitchenwatch-cron-secret:latest \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=2 \
  --memory=1Gi \
  --cpu=1 \
  --timeout=180
```

## Runtime notes

- Do not commit `.env`.
- Use Secret Manager for calendar id and cron secret.
- Keep Cloud Run min instances at 0 for low cost.
- `/cron/watch` is secret-gated and intended for Scheduler.
- Calendar access uses Cloud Run service account identity, not a JSON key.

## Not enabled

- Gmail API
- App Engine
- A second Firestore database
- A JSON service-account key
