from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from kitchenwatch.app import create_app
from kitchenwatch.calendar_io import GoogleCalendar, MemoryCalendar
from kitchenwatch.jobstore import MemoryJobStore
from kitchenwatch.ledger import MemoryLedger
from kitchenwatch.models import InventoryItem, ProposedAction
from kitchenwatch.plan import fixture_omelette_planner
from kitchenwatch.watch import run_watch

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
AS_OF = date(2026, 8, 29)


def demo_shelf() -> list[InventoryItem]:
    payload = json.loads((FIXTURES / "ledger_demo.json").read_text())
    return [InventoryItem.model_validate(row) for row in payload["items"]]


def chicken_planner(shelf, expiring, as_of) -> ProposedAction:
    raw = json.loads((FIXTURES / "action_lie_chicken.json").read_text())
    return ProposedAction.model_validate(raw)


def test_nothing_due_does_not_write_calendar():
    store = MemoryLedger()
    store.upsert(
        [
            InventoryItem(
                item_id="onion",
                name="Onion",
                qty=1,
                unit="count",
                expiry=None,
                source="fixture",
                confidence=0.9,
            )
        ]
    )
    cal = MemoryCalendar()
    job = run_watch(
        ledger=store,
        jobs=MemoryJobStore(),
        calendar=cal,
        planner=fixture_omelette_planner,
        as_of=AS_OF,
    )
    assert job.status == "skipped_nothing_due"
    assert cal.insert_count == 0


def test_chicken_plan_is_trust_fail_no_calendar():
    store = MemoryLedger()
    store.upsert(demo_shelf())
    cal = MemoryCalendar()
    job = run_watch(
        ledger=store,
        jobs=MemoryJobStore(),
        calendar=cal,
        planner=chicken_planner,
        as_of=AS_OF,
    )
    assert job.status == "trust_fail"
    assert "not_on_shelf:chicken" in (job.trust.reasons if job.trust else [])
    assert cal.insert_count == 0


def test_honest_watch_writes_once_then_idempotent():
    store = MemoryLedger()
    store.upsert(demo_shelf())
    cal = MemoryCalendar()
    jobs = MemoryJobStore()
    first = run_watch(
        ledger=store,
        jobs=jobs,
        calendar=cal,
        planner=fixture_omelette_planner,
        as_of=AS_OF,
    )
    second = run_watch(
        ledger=store,
        jobs=jobs,
        calendar=cal,
        planner=fixture_omelette_planner,
        as_of=AS_OF,
    )
    assert first.status == "written"
    assert first.calendar_event_id == "evt_1"
    assert second.status == "skipped_idempotent"
    assert second.calendar_event_id == "evt_1"
    assert cal.insert_count == 1


def test_write_fail_when_calendar_raises():
    store = MemoryLedger()
    store.upsert(demo_shelf())
    cal = MemoryCalendar()
    cal.fail_insert = True
    job = run_watch(
        ledger=store,
        jobs=MemoryJobStore(),
        calendar=cal,
        planner=fixture_omelette_planner,
        as_of=AS_OF,
    )
    assert job.status == "write_fail"
    assert cal.insert_count == 0


def test_verify_fail_when_event_missing():
    store = MemoryLedger()
    store.upsert(demo_shelf())
    cal = MemoryCalendar()
    cal.fail_get = True
    job = run_watch(
        ledger=store,
        jobs=MemoryJobStore(),
        calendar=cal,
        planner=fixture_omelette_planner,
        as_of=AS_OF,
    )
    assert job.status == "verify_fail"
    assert cal.insert_count == 1


def test_post_watch_endpoint():
    store = MemoryLedger()
    store.upsert(demo_shelf())
    client = TestClient(
        create_app(
            store=store,
            jobs=MemoryJobStore(),
            calendar=MemoryCalendar(),
            planner=fixture_omelette_planner,
        )
    )
    response = client.post(
        "/watch",
        data={"kitchen_id": "demo", "as_of": "2026-08-29"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "written"
    listed = client.get("/kitchens/demo/jobs")
    assert listed.json()["jobs"][0]["job_id"] == "watch:demo:2026-08-29"


def test_demo_seed_plants_tomorrow_milk():
    client = TestClient(create_app(store=MemoryLedger(), jobs=MemoryJobStore(), calendar=MemoryCalendar()))
    response = client.post("/demo/seed", data={"kitchen_id": "demo"})
    assert response.status_code == 200
    ids = {row["item_id"] for row in response.json()["items"]}
    assert ids == {"milk", "spinach", "eggs"}


def test_manual_expiry_edit_and_delete_item():
    store = MemoryLedger()
    store.upsert(
        [
            InventoryItem(
                item_id="cucumber",
                name="cucumber",
                qty=1,
                unit="count",
                expiry=None,
                source="voice",
                confidence=0.9,
            )
        ]
    )
    client = TestClient(
        create_app(
            store=store,
            jobs=MemoryJobStore(),
            calendar=MemoryCalendar(),
            planner=fixture_omelette_planner,
        )
    )

    edited = client.post(
        "/kitchens/demo/items/cucumber/expiry",
        data={"expiry": "2026-09-03"},
    )
    assert edited.status_code == 200
    assert edited.json()["item"]["expiry"] == "2026-09-03"
    assert edited.json()["item"]["source"] == "manual"

    deleted = client.delete("/kitchens/demo/items/cucumber")
    assert deleted.status_code == 200
    assert deleted.json()["items"] == []


def test_ui_serves_camera_page():
    client = TestClient(
        create_app(
            store=MemoryLedger(),
            jobs=MemoryJobStore(),
            calendar=MemoryCalendar(),
            planner=fixture_omelette_planner,
        )
    )
    response = client.get("/")
    assert response.status_code == 200
    assert "KitchenWatch" in response.text
    assert "Camera" in response.text
    assert "Run watch" in response.text
    assert "Save date" in response.text
    assert "Remove" in response.text


def test_cron_watch_rejects_bad_secret(monkeypatch):
    monkeypatch.setenv("WATCH_CRON_SECRET", "test-secret")
    store = MemoryLedger()
    store.upsert(demo_shelf())
    client = TestClient(
        create_app(
            store=store,
            jobs=MemoryJobStore(),
            calendar=MemoryCalendar(),
            planner=fixture_omelette_planner,
        )
    )
    denied = client.post("/cron/watch", json={"kitchen_id": "demo", "as_of": "2026-08-29"})
    assert denied.status_code == 403
    allowed = client.post(
        "/cron/watch",
        json={"kitchen_id": "demo", "as_of": "2026-08-29"},
        headers={"X-Watch-Secret": "test-secret"},
    )
    assert allowed.status_code == 200


def test_cron_watch_json():
    store = MemoryLedger()
    store.upsert(demo_shelf())
    client = TestClient(
        create_app(
            store=store,
            jobs=MemoryJobStore(),
            calendar=MemoryCalendar(),
            planner=fixture_omelette_planner,
        )
    )
    response = client.post(
        "/cron/watch",
        json={"kitchen_id": "demo", "as_of": "2026-08-29"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "written"


class _FakeCalendarEvents:
    def __init__(self) -> None:
        self.insert_kwargs = {}

    def insert(self, **kwargs):
        self.insert_kwargs = kwargs
        return self

    def execute(self):
        return {"id": "calendar_evt"}


class _FakeCalendarService:
    def __init__(self) -> None:
        self.events_resource = _FakeCalendarEvents()

    def events(self):
        return self.events_resource


def test_google_calendar_adds_cook_description_and_reminders(monkeypatch):
    monkeypatch.setenv("KITCHENWATCH_CALENDAR_ID", "demo-calendar")
    service = _FakeCalendarService()
    cal = GoogleCalendar(service=service, calendar="demo-calendar")
    action = fixture_omelette_planner(demo_shelf(), demo_shelf(), AS_OF)

    event_id = cal.insert(action, "watch:demo:2026-08-29")

    assert event_id == "calendar_evt"
    kwargs = service.events_resource.insert_kwargs
    assert kwargs["sendUpdates"] == "none"
    body = kwargs["body"]
    assert {"method": "email", "minutes": 120} in body["reminders"]["overrides"]
    assert "What to cook:" in body["description"]
