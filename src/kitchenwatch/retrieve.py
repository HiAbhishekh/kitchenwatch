from __future__ import annotations

from datetime import date, timedelta

from kitchenwatch.models import InventoryItem
from kitchenwatch.normalize import canonical_item_id


def ledger_by_id(items: list[InventoryItem]) -> dict[str, InventoryItem]:
    out: dict[str, InventoryItem] = {}
    for item in items:
        key = canonical_item_id(item.item_id)
        out[key] = item.model_copy(update={"item_id": key})
    return out


def expiring_within(
    items: list[InventoryItem],
    as_of: date,
    horizon_days: int = 2,
) -> list[InventoryItem]:
    """Items that can trigger a watch write: real expiry on or before as_of + horizon."""
    cutoff = as_of + timedelta(days=horizon_days)
    keyed = ledger_by_id(items)
    due: list[InventoryItem] = []
    for item in keyed.values():
        if item.expiry is None:
            continue
        if as_of <= item.expiry <= cutoff:
            due.append(item)
    return due
