from __future__ import annotations

import argparse
import json
import mimetypes
from collections.abc import Callable
from pathlib import Path
from typing import Any

from kitchenwatch.extract import ExtractPayload, accept_extract
from kitchenwatch.models import InventoryItem
from kitchenwatch.settings import gcp_location, gcp_project, gemini_model, load_env

EXTRACT_PROMPT = """You extract a kitchen inventory from ONE photo.

Rules:
- Only list food you can actually read or clearly see. Do not invent items.
- Do not add meat, recipes, or pantry guesses that are not in the frame.
- name: the food as labeled (e.g. whole milk, baby spinach).
- qty: a positive number.
- unit: one of count, carton, bottle, pack, bunch, g, kg, ml, l. Never invent other units.
- expiry: ISO date YYYY-MM-DD if a date is readable on that item, else null.
- confidence: 0 to 1. If you are guessing, use below 0.7.

Return JSON only.
"""

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "items": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "qty": {"type": "NUMBER"},
                    "unit": {"type": "STRING"},
                    "expiry": {"type": "STRING", "nullable": True},
                    "confidence": {"type": "NUMBER"},
                },
                "required": ["name", "qty", "unit", "confidence"],
            },
        }
    },
    "required": ["items"],
}

GeminiCaller = Callable[[Path], dict[str, Any]]


def _mime(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    if guessed:
        return guessed
    return "image/jpeg"


def vertex_caller() -> GeminiCaller:
    from google import genai
    from google.genai import types

    load_env()
    client = genai.Client(
        vertexai=True,
        project=gcp_project(),
        location=gcp_location(),
    )
    model = gemini_model()

    def call(path: Path) -> dict[str, Any]:
        image_bytes = path.read_bytes()
        response = client.models.generate_content(
            model=model,
            contents=[
                EXTRACT_PROMPT,
                types.Part.from_bytes(data=image_bytes, mime_type=_mime(path)),
            ],
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
                response_schema=RESPONSE_SCHEMA,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
            ),
        )
        text = response.text
        if not text:
            raise RuntimeError("Gemini returned empty vision extract")
        return json.loads(text)

    return call


def extract_from_image(
    path: Path,
    *,
    caller: GeminiCaller | None = None,
) -> ExtractPayload:
    call = caller or vertex_caller()
    raw = call(path)
    return ExtractPayload.model_validate(raw)


def ingest_from_image(
    path: Path,
    *,
    kitchen_id: str = "demo",
    caller: GeminiCaller | None = None,
) -> tuple[list[InventoryItem], list[str], ExtractPayload]:
    payload = extract_from_image(path, caller=caller)
    accepted, dropped = accept_extract(
        payload, kitchen_id=kitchen_id, source="photo"
    )
    return accepted, dropped, payload


def main() -> None:
    parser = argparse.ArgumentParser(description="KitchenWatch vision extract")
    parser.add_argument("image", type=Path)
    parser.add_argument("--save-json", type=Path, default=None)
    args = parser.parse_args()
    accepted, dropped, payload = ingest_from_image(args.image)
    print(json.dumps(payload.model_dump(mode="json"), indent=2))
    print("--- accepted ---")
    print(
        json.dumps(
            [item.model_dump(mode="json") for item in accepted],
            indent=2,
        )
    )
    if dropped:
        print("--- dropped ---")
        print(json.dumps(dropped, indent=2))
    if args.save_json:
        args.save_json.write_text(json.dumps(payload.model_dump(mode="json"), indent=2))
        print(f"wrote {args.save_json}")


if __name__ == "__main__":
    main()
