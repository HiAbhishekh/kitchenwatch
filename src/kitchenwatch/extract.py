from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from kitchenwatch.models import InventoryItem, Unit
from kitchenwatch.normalize import canonical_item_id

MIN_CONFIDENCE = 0.7

_UNIT_TO_CANON: dict[str, tuple[Unit, float]] = {
    "count": ("count", 1),
    "carton": ("count", 1),
    "bottle": ("count", 1),
    "piece": ("count", 1),
    "pieces": ("count", 1),
    "pcs": ("count", 1),
    "bunch": ("count", 1),
    "pack": ("count", 1),
    "g": ("g", 1),
    "gram": ("g", 1),
    "grams": ("g", 1),
    "kg": ("g", 1000),
    "ml": ("ml", 1),
    "l": ("ml", 1000),
    "liter": ("ml", 1000),
    "litre": ("ml", 1000),
}


class ExtractedRow(BaseModel):
    name: str
    qty: float = Field(gt=0)
    unit: str
    expiry: date | None = None
    confidence: float = Field(ge=0, le=1)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("empty name")
        return text

    @field_validator("expiry", mode="before")
    @classmethod
    def parse_expiry(cls, value: object) -> date | None:
        if value is None or value == "" or value == "null":
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        text = str(value).strip()
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%b %d %Y", "%B %d %Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"unreadable expiry: {value}")


class ExtractPayload(BaseModel):
    items: list[ExtractedRow]


def coerce_unit(raw: str) -> tuple[Unit, float] | None:
    key = raw.strip().lower()
    return _UNIT_TO_CANON.get(key)


def accept_extract(
    payload: ExtractPayload | dict[str, Any],
    *,
    kitchen_id: str = "demo",
    source: Literal["photo", "voice"] = "photo",
    min_confidence: float = MIN_CONFIDENCE,
) -> tuple[list[InventoryItem], list[str]]:
    """Keep only rows Trust can use. Returns (accepted, drop_reasons)."""
    parsed = (
        payload
        if isinstance(payload, ExtractPayload)
        else ExtractPayload.model_validate(payload)
    )
    accepted: list[InventoryItem] = []
    dropped: list[str] = []

    for row in parsed.items:
        if row.confidence < min_confidence:
            dropped.append(f"low_confidence:{row.name}:{row.confidence}")
            continue
        unit_map = coerce_unit(row.unit)
        if unit_map is None:
            dropped.append(f"bad_unit:{row.name}:{row.unit}")
            continue
        unit, factor = unit_map
        qty = row.qty * factor
        item_id = canonical_item_id(row.name)
        accepted.append(
            InventoryItem(
                item_id=item_id,
                name=row.name,
                qty=qty,
                unit=unit,
                expiry=row.expiry,
                source=source,
                confidence=row.confidence,
                kitchen_id=kitchen_id,
            )
        )
    return accepted, dropped
