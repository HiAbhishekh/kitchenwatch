from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


Unit = Literal["count", "g", "ml"]
JobStatus = Literal[
    "pending",
    "skipped_nothing_due",
    "trust_fail",
    "written",
    "verify_fail",
    "write_fail",
    "skipped_idempotent",
]


class InventoryItem(BaseModel):
    item_id: str
    name: str
    qty: float = Field(gt=0)
    unit: Unit
    expiry: date | None
    source: Literal["photo", "voice", "manual", "fixture"]
    confidence: float = Field(ge=0, le=1)
    kitchen_id: str = "demo"


class IngredientNeed(BaseModel):
    item_id: str
    qty: float = Field(gt=0)
    unit: Unit


class ProposedAction(BaseModel):
    kind: Literal["cook"] = "cook"
    title: str
    window_start: datetime
    window_end: datetime
    uses: list[IngredientNeed]
    reason_item_id: str
    notes: str = ""


class TrustVerdict(BaseModel):
    ok: bool
    reasons: list[str]
    job_id: str


class JobRecord(BaseModel):
    job_id: str
    kitchen_id: str
    as_of: date
    status: JobStatus
    proposed: ProposedAction | None = None
    calendar_event_id: str | None = None
    trust: TrustVerdict | None = None
    error: str | None = None
