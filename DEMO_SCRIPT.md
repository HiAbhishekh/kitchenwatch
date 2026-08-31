# KitchenWatch demo script (under 4 minutes)

Hosted: https://kitchenwatch-466851852100.us-central1.run.app/

Open before recording:

- KitchenWatch app
- Google Calendar named **KitchenWatch**
- Google Cloud Console: Cloud Run service + Cloud Scheduler job `kitchenwatch-watch`
- Optional: Firestore `kitchens/demo/items`

Do not open `.env` while recording.

## 0:00-0:20 — Hook

Say:

> Most food apps wait for me to ask what to cook. KitchenWatch does the opposite. It watches the real shelf, finds what is expiring, and puts one safe cooking action on my calendar before the food is wasted.
>
> The key rule is simple: it will not put dinner on my calendar unless the fridge can actually feed it.

On screen:

1. Show KitchenWatch landing page.
2. Show the title and two steps: shelf first, watch second.

## 0:20-1:05 — Show real shelf input

Say:

> First, I give the agent kitchen evidence. That can be a photo, a camera capture, or voice. Gemini 3.5 extracts structured items: name, quantity, unit, and expiry date.
>
> If voice misses an expiry, the user can fix it manually. If voice heard a wrong item, the user can remove it. So the database stays honest before the agent takes action.

On screen:

1. Click **Reset demo shelf** for a clean shelf.
2. Optionally click **Record**, speak: “whole milk expires tomorrow, baby spinach expires in two days, and six eggs expire later.”
3. Show shelf cards.
4. If any item says **No expiry set**, pick a date and click **Save date**.
5. Remove any wrong voice item with **Remove**.

Important line:

> The expiry does not come from guessing. It comes from the label in the photo, the spoken date, or the manual correction.

## 1:05-1:45 — Run the agent

Say:

> Now I run the watch. In production Cloud Scheduler does this every morning at 7 AM. This button calls the same backend path.
>
> The agent retrieves items expiring in the next 48 hours, Gemini proposes one cook, and then a Python trust gate checks every ingredient against Firestore.

On screen:

1. Click **Run watch**.
2. Show result card: `written` or `skipped_idempotent`.
3. Show recipe title like **Use milk and spinach in scrambled eggs**.
4. Show event id.

If status is `skipped_idempotent`, say:

> This means the agent already wrote today's event, so it did not spam my calendar. Same kitchen, same date, one event.

## 1:45-2:20 — Calendar proof

Say:

> This is the action. The output is not chat text. It is a real Google Calendar event with what to cook, why now, and which ingredients to use.
>
> Calendar also carries reminders, so the user sees the cooking plan at the right time.

On screen:

1. Switch to Google Calendar.
2. Open the KitchenWatch event.
3. Show title, time window, and description.

Say:

> This event exists because Trust passed. If Gemini invented chicken, or used more eggs than I have, Calendar would not get a write.

## 2:20-3:05 — Architecture and Google Cloud proof

Say:

> The architecture has two separate paths. Ingest is multimodal: photo or voice into Gemini 3.5, then accepted items into Firestore. Watch is the autonomous path: retrieve, plan, trust, write, verify.
>
> Trust is deliberately not an LLM. It is Python code. It checks expiry, quantity, units, and whether every ingredient exists on the shelf.

On screen:

1. Show `docs/architecture.svg` or `docs/ARCHITECTURE.md`.
2. Show Cloud Run URL ending in `.run.app`.
3. Show Cloud Scheduler `kitchenwatch-watch`, 07:00 Asia/Kolkata.
4. Show Firestore `kitchens/demo/items`.

Say:

> This is running on Cloud Run, stores state in Firestore, wakes up with Cloud Scheduler, uses Secret Manager for credentials, calls Gemini 3.5 through the Google GenAI SDK, and writes the final action through Google Calendar API.

## 3:05-3:40 — Why this fits Taskmaster

Say:

> Taskmaster is about a complete workflow, not a chatbot. KitchenWatch handles a messy chore end to end: understand the kitchen, decide what matters, verify the action is safe, write to another app, and avoid duplicate writes.
>
> It removes real friction: I do not have to remember what is expiring, search recipes, or manually schedule dinner.

On screen:

1. Return to KitchenWatch result card.
2. Show pipeline cards: Retrieve, Plan, Trust, Write, Verify.

## 3:40-3:58 — Close

Say:

> KitchenWatch is small on purpose: one kitchen, one trusted shelf, one calendar action. That discipline is the product. Gemini is creative, but Trust decides. The result is a background agent that turns real food into a verified plan before waste happens.

Stop recording before 4:00.

## Emergency shorter version (90 seconds)

Say:

> KitchenWatch is a Taskmaster agent for food waste. It reads my real kitchen shelf from photo or voice, stores accepted items in Firestore, finds food expiring in 48 hours, asks Gemini 3.5 for one cooking plan, then uses Python trust rules to verify every ingredient before writing Google Calendar.
>
> Here I reset the demo shelf. Milk expires tomorrow, spinach in two days, eggs later. I run watch. The agent proposes scrambled eggs with milk and spinach, Trust passes, and Calendar gets one event. If I run it again, it returns skipped_idempotent, so Scheduler retries do not spam my calendar.
>
> This runs on Cloud Run, uses Firestore for state, Cloud Scheduler for the background job, Secret Manager for secrets, Google GenAI SDK for Gemini, and Calendar API for the final action. It is not a recipe chatbot. It is a verified background workflow that takes useful action.
