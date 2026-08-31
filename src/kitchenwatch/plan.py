from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any

from kitchenwatch.models import InventoryItem, ProposedAction
from kitchenwatch.settings import gcp_location, gcp_project, gemini_model, load_env

Planner = Callable[[list[InventoryItem], list[InventoryItem], date], ProposedAction]

PLAN_PROMPT = """You propose ONE cook so food that expires soon gets used.

Rules:
- reason_item_id MUST be one of the expiring item_id values.
- uses[] may only cite item_id values from the shelf list.
- qty must be <= the shelf qty. unit must match the shelf unit exactly (count, g, or ml).
- title: short, starts with Use.
- window_start and window_end: ISO datetimes on as_of, 18:00 to 19:00 local.
- Do not invent food. No chicken unless chicken is on the shelf.
- kind must be cook.

Return JSON only.
"""

PLAN_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "kind": {"type": "STRING"},
        "title": {"type": "STRING"},
        "window_start": {"type": "STRING"},
        "window_end": {"type": "STRING"},
        "reason_item_id": {"type": "STRING"},
        "notes": {"type": "STRING"},
        "uses": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "item_id": {"type": "STRING"},
                    "qty": {"type": "NUMBER"},
                    "unit": {"type": "STRING"},
                },
                "required": ["item_id", "qty", "unit"],
            },
        },
    },
    "required": ["title", "window_start", "window_end", "reason_item_id", "uses"],
}


def _dump_item(item: InventoryItem) -> dict[str, Any]:
    return {
        "item_id": item.item_id,
        "name": item.name,
        "qty": item.qty,
        "unit": item.unit,
        "expiry": item.expiry.isoformat() if item.expiry else None,
    }


def vertex_planner() -> Planner:
    from google import genai
    from google.genai import types

    load_env()
    client = genai.Client(
        vertexai=True,
        project=gcp_project(),
        location=gcp_location(),
    )
    model = gemini_model()

    def plan(
        shelf: list[InventoryItem],
        expiring: list[InventoryItem],
        as_of: date,
    ) -> ProposedAction:
        payload = {
            "as_of": as_of.isoformat(),
            "expiring": [_dump_item(item) for item in expiring],
            "shelf": [_dump_item(item) for item in shelf],
        }
        response = client.models.generate_content(
            model=model,
            contents=f"{PLAN_PROMPT}\n\n{json.dumps(payload)}",
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
                response_schema=PLAN_SCHEMA,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
            ),
        )
        text = response.text
        if not text:
            raise RuntimeError("Gemini returned empty cook plan")
        return ProposedAction.model_validate(json.loads(text))

    return plan


def fixture_omelette_planner(
    shelf: list[InventoryItem],
    expiring: list[InventoryItem],
    as_of: date,
) -> ProposedAction:
    start = datetime(as_of.year, as_of.month, as_of.day, 18, 0, 0)
    return ProposedAction(
        title="Use the milk — spinach omelette",
        window_start=start,
        window_end=start + timedelta(hours=1),
        reason_item_id="milk",
        notes="Fixture planner. Not Gemini.",
        uses=[
            {"item_id": "milk", "qty": 1, "unit": "count"},
            {"item_id": "eggs", "qty": 2, "unit": "count"},
            {"item_id": "spinach", "qty": 80, "unit": "g"},
        ],
    )
