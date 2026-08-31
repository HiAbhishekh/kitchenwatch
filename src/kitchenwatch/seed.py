from __future__ import annotations

from datetime import date, timedelta

from kitchenwatch.models import InventoryItem


def plant_demo_kitchen(*, kitchen_id: str = "demo", as_of: date | None = None) -> list[InventoryItem]:
    """Planted kitchen that can trigger a watch on as_of (milk tomorrow)."""
    day = as_of or date.today()
    return [
        InventoryItem(
            item_id="milk",
            name="whole milk",
            qty=1,
            unit="count",
            expiry=day + timedelta(days=1),
            source="fixture",
            confidence=1.0,
            kitchen_id=kitchen_id,
        ),
        InventoryItem(
            item_id="spinach",
            name="baby spinach",
            qty=200,
            unit="g",
            expiry=day + timedelta(days=2),
            source="fixture",
            confidence=1.0,
            kitchen_id=kitchen_id,
        ),
        InventoryItem(
            item_id="eggs",
            name="eggs",
            qty=6,
            unit="count",
            expiry=day + timedelta(days=6),
            source="fixture",
            confidence=1.0,
            kitchen_id=kitchen_id,
        ),
    ]
