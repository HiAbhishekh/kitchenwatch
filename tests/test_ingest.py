from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from kitchenwatch.app import create_app
from kitchenwatch.ingest import ingest_photo
from kitchenwatch.ledger import MemoryLedger
from kitchenwatch.models import InventoryItem


def _milk(*, qty: float = 1, kitchen_id: str = "demo") -> InventoryItem:
    return InventoryItem(
        item_id="milk",
        name="whole milk",
        qty=qty,
        unit="count",
        expiry=date(2026, 8, 30),
        source="photo",
        confidence=0.95,
        kitchen_id=kitchen_id,
    )


def test_upsert_replaces_same_item_id():
    store = MemoryLedger()
    store.upsert([_milk(qty=1)])
    store.upsert([_milk(qty=2)])
    shelf = store.list_items("demo")
    assert len(shelf) == 1
    assert shelf[0].qty == 2


def test_kitchens_do_not_leak():
    store = MemoryLedger()
    store.upsert([_milk(kitchen_id="demo"), _milk(kitchen_id="other")])
    assert [item.kitchen_id for item in store.list_items("demo")] == ["demo"]


def test_ingest_photo_writes_only_accepted(tmp_path: Path):
    photo = tmp_path / "shelf.jpg"
    photo.write_bytes(b"x")
    store = MemoryLedger()

    def fake(_path: Path) -> dict:
        return {
            "items": [
                {
                    "name": "whole milk",
                    "qty": 1,
                    "unit": "carton",
                    "expiry": "2026-08-30",
                    "confidence": 0.94,
                },
                {
                    "name": "chicken",
                    "qty": 1,
                    "unit": "pack",
                    "expiry": None,
                    "confidence": 0.2,
                },
            ]
        }

    accepted, dropped, _ = ingest_photo(photo, store=store, caller=fake)
    assert [item.item_id for item in accepted] == ["milk"]
    assert any("low_confidence:chicken" in row for row in dropped)
    assert [item.item_id for item in store.list_items("demo")] == ["milk"]


def test_post_ingest_and_get_shelf(tmp_path: Path):
    photo = tmp_path / "fridge.jpg"
    photo.write_bytes(b"not-empty")

    def fake(_path: Path) -> dict:
        return {
            "items": [
                {
                    "name": "eggs",
                    "qty": 6,
                    "unit": "count",
                    "expiry": "2026-09-04",
                    "confidence": 0.9,
                }
            ]
        }

    client = TestClient(create_app(store=MemoryLedger(), caller=fake))
    with photo.open("rb") as handle:
        response = client.post(
            "/ingest",
            files={"photo": ("fridge.jpg", handle, "image/jpeg")},
            data={"kitchen_id": "demo"},
        )
    assert response.status_code == 200
    body = response.json()
    assert [item["item_id"] for item in body["accepted"]] == ["eggs"]
    listed = client.get("/kitchens/demo/items")
    assert listed.json()["items"][0]["item_id"] == "eggs"


def test_reject_empty_photo():
    client = TestClient(create_app(store=MemoryLedger(), caller=lambda _: {"items": []}))
    response = client.post(
        "/ingest",
        files={"photo": ("fridge.jpg", b"", "image/jpeg")},
    )
    assert response.status_code == 400
