from __future__ import annotations

import argparse
import json
from pathlib import Path

from kitchenwatch.extract import ExtractPayload
from kitchenwatch.ledger import FirestoreLedger, Ledger
from kitchenwatch.models import InventoryItem
from kitchenwatch.vision import GeminiCaller, ingest_from_image
from kitchenwatch.voice import ingest_from_audio


def commit_ingest(
    store: Ledger,
    accepted: list[InventoryItem],
) -> list[InventoryItem]:
    store.upsert(accepted)
    if not accepted:
        return []
    kitchen_id = accepted[0].kitchen_id
    return store.list_items(kitchen_id)


def ingest_photo(
    path: Path,
    *,
    store: Ledger,
    kitchen_id: str = "demo",
    caller: GeminiCaller | None = None,
) -> tuple[list[InventoryItem], list[str], ExtractPayload]:
    accepted, dropped, payload = ingest_from_image(
        path, kitchen_id=kitchen_id, caller=caller
    )
    commit_ingest(store, accepted)
    return accepted, dropped, payload


def ingest_voice(
    path: Path,
    *,
    store: Ledger,
    kitchen_id: str = "demo",
    caller: GeminiCaller | None = None,
) -> tuple[list[InventoryItem], list[str], ExtractPayload]:
    accepted, dropped, payload = ingest_from_audio(
        path, kitchen_id=kitchen_id, caller=caller
    )
    commit_ingest(store, accepted)
    return accepted, dropped, payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a fridge photo into Firestore")
    parser.add_argument("image", type=Path)
    parser.add_argument("--kitchen-id", default="demo")
    args = parser.parse_args()
    store = FirestoreLedger()
    accepted, dropped, payload = ingest_photo(
        args.image, store=store, kitchen_id=args.kitchen_id
    )
    print(json.dumps(payload.model_dump(mode="json"), indent=2))
    print("--- accepted ---")
    print(json.dumps([item.model_dump(mode="json") for item in accepted], indent=2))
    if dropped:
        print("--- dropped ---")
        print(json.dumps(dropped, indent=2))
    print("--- shelf ---")
    print(
        json.dumps(
            [item.model_dump(mode="json") for item in store.list_items(args.kitchen_id)],
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
