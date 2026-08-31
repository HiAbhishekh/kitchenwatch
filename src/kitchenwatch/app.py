from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

import os

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from kitchenwatch.calendar_io import CalendarPort, GoogleCalendar
from kitchenwatch.ingest import ingest_photo, ingest_voice
from kitchenwatch.jobstore import FirestoreJobStore, JobStore
from kitchenwatch.ledger import FirestoreLedger, Ledger
from kitchenwatch.plan import Planner, vertex_planner
from kitchenwatch.vision import GeminiCaller, vertex_caller
from kitchenwatch.voice import audio_suffix, vertex_audio_caller
from kitchenwatch.seed import plant_demo_kitchen
from kitchenwatch.watch import job_public, run_watch


STATIC = Path(__file__).resolve().parent / "static"


class WatchRequest(BaseModel):
    kitchen_id: str = "demo"
    as_of: str | None = None


def _run(
    *,
    kitchen_id: str,
    as_of: str | None,
    ledger: Ledger,
    job_store: JobStore,
    cal: CalendarPort,
    plan: Planner,
):
    day = date.fromisoformat(as_of) if as_of else date.today()
    return run_watch(
        ledger=ledger,
        jobs=job_store,
        calendar=cal,
        planner=plan,
        kitchen_id=kitchen_id,
        as_of=day,
    )


def create_app(
    store: Ledger | None = None,
    caller: GeminiCaller | None = None,
    audio_caller: GeminiCaller | None = None,
    jobs: JobStore | None = None,
    calendar: CalendarPort | None = None,
    planner: Planner | None = None,
) -> FastAPI:
    app = FastAPI(title="KitchenWatch", version="0.1.0")
    app.state.store = store
    app.state.caller = caller
    app.state.audio_caller = audio_caller
    app.state.jobs = jobs
    app.state.calendar = calendar
    app.state.planner = planner

    def get_store() -> Ledger:
        if app.state.store is None:
            app.state.store = FirestoreLedger()
        return app.state.store

    def get_caller() -> GeminiCaller:
        if app.state.caller is None:
            app.state.caller = vertex_caller()
        return app.state.caller

    def get_audio_caller() -> GeminiCaller:
        if app.state.audio_caller is None:
            app.state.audio_caller = vertex_audio_caller()
        return app.state.audio_caller

    def get_jobs() -> JobStore:
        if app.state.jobs is None:
            app.state.jobs = FirestoreJobStore()
        return app.state.jobs

    def get_calendar() -> CalendarPort:
        if app.state.calendar is None:
            app.state.calendar = GoogleCalendar()
        return app.state.calendar

    def get_planner() -> Planner:
        if app.state.planner is None:
            app.state.planner = vertex_planner()
        return app.state.planner

    @app.get("/")
    def root():
        page = STATIC / "index.html"
        if not page.is_file():
            raise HTTPException(500, "UI missing")
        return FileResponse(page)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"ok": "kitchenwatch"}

    @app.get("/kitchens/{kitchen_id}/items")
    def list_items(kitchen_id: str, ledger: Ledger = Depends(get_store)):
        return {
            "kitchen_id": kitchen_id,
            "items": [item.model_dump(mode="json") for item in ledger.list_items(kitchen_id)],
        }

    @app.post("/kitchens/{kitchen_id}/items/{item_id}/expiry")
    def update_item_expiry(
        kitchen_id: str,
        item_id: str,
        expiry: str = Form(...),
        ledger: Ledger = Depends(get_store),
    ):
        current = next(
            (item for item in ledger.list_items(kitchen_id) if item.item_id == item_id),
            None,
        )
        if current is None:
            raise HTTPException(404, "item not found")
        try:
            parsed = date.fromisoformat(expiry) if expiry.strip() else None
        except ValueError as exc:
            raise HTTPException(400, "expiry must be YYYY-MM-DD") from exc
        updated = current.model_copy(update={"expiry": parsed, "source": "manual"})
        ledger.upsert([updated])
        return {
            "kitchen_id": kitchen_id,
            "item": updated.model_dump(mode="json"),
            "items": [item.model_dump(mode="json") for item in ledger.list_items(kitchen_id)],
        }

    @app.delete("/kitchens/{kitchen_id}/items/{item_id}")
    def delete_item(
        kitchen_id: str,
        item_id: str,
        ledger: Ledger = Depends(get_store),
    ):
        ledger.delete(kitchen_id, item_id)
        return {
            "kitchen_id": kitchen_id,
            "deleted": item_id,
            "items": [item.model_dump(mode="json") for item in ledger.list_items(kitchen_id)],
        }

    @app.post("/ingest")
    async def ingest(
        photo: UploadFile = File(...),
        kitchen_id: str = Form("demo"),
        ledger: Ledger = Depends(get_store),
        vision: GeminiCaller = Depends(get_caller),
    ):
        suffix = Path(photo.filename or "fridge.jpg").suffix or ".jpg"
        if suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise HTTPException(400, "photo must be jpg, png, or webp")
        raw = await photo.read()
        if not raw:
            raise HTTPException(400, "empty photo")
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(raw)
            path = Path(tmp.name)
        try:
            accepted, dropped, payload = ingest_photo(
                path, store=ledger, kitchen_id=kitchen_id, caller=vision
            )
        finally:
            path.unlink(missing_ok=True)
        return {
            "kitchen_id": kitchen_id,
            "accepted": [item.model_dump(mode="json") for item in accepted],
            "dropped": dropped,
            "extract": payload.model_dump(mode="json"),
            "shelf": [
                item.model_dump(mode="json")
                for item in ledger.list_items(kitchen_id)
            ],
        }

    @app.post("/ingest-voice")
    async def ingest_audio(
        audio: UploadFile = File(...),
        kitchen_id: str = Form("demo"),
        ledger: Ledger = Depends(get_store),
        speech: GeminiCaller = Depends(get_audio_caller),
    ):
        suffix = audio_suffix(audio.filename, audio.content_type)
        if not suffix:
            raise HTTPException(400, "audio must be webm, wav, mp3, or m4a")
        raw = await audio.read()
        if not raw:
            raise HTTPException(400, "empty audio")
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(raw)
            path = Path(tmp.name)
        try:
            accepted, dropped, payload = ingest_voice(
                path, store=ledger, kitchen_id=kitchen_id, caller=speech
            )
        except Exception as exc:
            raise HTTPException(502, f"voice extract failed: {exc}") from exc
        finally:
            path.unlink(missing_ok=True)
        return {
            "kitchen_id": kitchen_id,
            "accepted": [item.model_dump(mode="json") for item in accepted],
            "dropped": dropped,
            "extract": payload.model_dump(mode="json"),
            "shelf": [
                item.model_dump(mode="json")
                for item in ledger.list_items(kitchen_id)
            ],
        }

    @app.get("/kitchens/{kitchen_id}/jobs")
    def list_jobs(kitchen_id: str, job_store: JobStore = Depends(get_jobs)):
        return {
            "kitchen_id": kitchen_id,
            "jobs": [job_public(job) for job in job_store.list_jobs(kitchen_id)],
        }

    @app.post("/demo/seed")
    def seed_demo(
        kitchen_id: str = Form("demo"),
        ledger: Ledger = Depends(get_store),
    ):
        for item in ledger.list_items(kitchen_id):
            ledger.delete(kitchen_id, item.item_id)
        items = plant_demo_kitchen(kitchen_id=kitchen_id)
        ledger.upsert(items)
        return {
            "kitchen_id": kitchen_id,
            "items": [item.model_dump(mode="json") for item in ledger.list_items(kitchen_id)],
        }

    @app.post("/watch")
    def watch(
        kitchen_id: str = Form("demo"),
        as_of: str | None = Form(None),
        ledger: Ledger = Depends(get_store),
        job_store: JobStore = Depends(get_jobs),
        cal: CalendarPort = Depends(get_calendar),
        plan: Planner = Depends(get_planner),
    ):
        return job_public(
            _run(
                kitchen_id=kitchen_id,
                as_of=as_of,
                ledger=ledger,
                job_store=job_store,
                cal=cal,
                plan=plan,
            )
        )

    @app.post("/cron/watch")
    async def cron_watch(
        request: Request,
        ledger: Ledger = Depends(get_store),
        job_store: JobStore = Depends(get_jobs),
        cal: CalendarPort = Depends(get_calendar),
        plan: Planner = Depends(get_planner),
    ):
        expected = os.environ.get("WATCH_CRON_SECRET", "").strip()
        got = request.headers.get("X-Watch-Secret", "")
        if expected and got != expected:
            raise HTTPException(403, "scheduler only")
        raw = await request.body()
        body = WatchRequest.model_validate_json(raw) if raw else WatchRequest()
        return job_public(
            _run(
                kitchen_id=body.kitchen_id,
                as_of=body.as_of,
                ledger=ledger,
                job_store=job_store,
                cal=cal,
                plan=plan,
            )
        )

    return app


app = create_app()
