from __future__ import annotations

from typing import Protocol

from kitchenwatch.models import InventoryItem
from kitchenwatch.settings import gcp_project, load_env


class Ledger(Protocol):
    def upsert(self, items: list[InventoryItem]) -> None: ...
    def list_items(self, kitchen_id: str) -> list[InventoryItem]: ...
    def delete(self, kitchen_id: str, item_id: str) -> None: ...


class MemoryLedger:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], InventoryItem] = {}

    def upsert(self, items: list[InventoryItem]) -> None:
        for item in items:
            self._items[(item.kitchen_id, item.item_id)] = item

    def list_items(self, kitchen_id: str) -> list[InventoryItem]:
        return [
            item
            for (kid, _), item in sorted(self._items.items())
            if kid == kitchen_id
        ]

    def delete(self, kitchen_id: str, item_id: str) -> None:
        self._items.pop((kitchen_id, item_id), None)


def _item_doc(item: InventoryItem) -> dict:
    return item.model_dump(mode="json")


def _item_from_doc(data: dict) -> InventoryItem:
    return InventoryItem.model_validate(data)


class FirestoreLedger:
    def __init__(self, client=None) -> None:
        load_env()
        if client is None:
            from google.cloud import firestore

            client = firestore.Client(project=gcp_project())
        self._db = client

    def _col(self, kitchen_id: str):
        return self._db.collection("kitchens").document(kitchen_id).collection("items")

    def upsert(self, items: list[InventoryItem]) -> None:
        if not items:
            return
        batch = self._db.batch()
        for item in items:
            ref = self._col(item.kitchen_id).document(item.item_id)
            batch.set(ref, _item_doc(item))
        batch.commit()

    def list_items(self, kitchen_id: str) -> list[InventoryItem]:
        docs = self._col(kitchen_id).stream()
        items = [_item_from_doc(doc.to_dict() or {}) for doc in docs]
        return sorted(items, key=lambda item: item.item_id)

    def delete(self, kitchen_id: str, item_id: str) -> None:
        self._col(kitchen_id).document(item_id).delete()
