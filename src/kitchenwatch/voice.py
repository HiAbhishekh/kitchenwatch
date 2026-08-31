from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from typing import Any

from kitchenwatch.extract import ExtractPayload, accept_extract
from kitchenwatch.models import InventoryItem
from kitchenwatch.settings import gcp_location, gcp_project, gemini_model, load_env
from kitchenwatch.vision import GeminiCaller, RESPONSE_SCHEMA

AUDIO_SUFFIXES = {
    ".webm",
    ".weba",
    ".wav",
    ".mp3",
    ".m4a",
    ".ogg",
    ".aac",
    ".aiff",
    ".caf",
}

_CONTENT_TYPE_SUFFIX = {
    "audio/webm": ".webm",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/wave": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/mp4": ".m4a",
    "audio/m4a": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/aac": ".aac",
    "audio/ogg": ".ogg",
    "audio/opus": ".ogg",
}


def audio_suffix(filename: str | None, content_type: str | None = None) -> str | None:
    """Map an upload to a temp-file suffix Chrome/Safari actually send."""
    suffix = Path(filename or "").suffix.lower()
    if suffix in AUDIO_SUFFIXES:
        return ".webm" if suffix == ".weba" else suffix
    base = (content_type or "").split(";", 1)[0].strip().lower()
    if base in _CONTENT_TYPE_SUFFIX:
        return _CONTENT_TYPE_SUFFIX[base]
    if "webm" in base:
        return ".webm"
    if "mp4" in base or "m4a" in base:
        return ".m4a"
    return None


VOICE_PROMPT = """You extract a kitchen inventory from ONE spoken dump.

Rules:
- Only list food the speaker actually named. Do not invent items.
- Do not add meat or pantry guesses that were not said.
- name: the food as spoken (e.g. whole milk, baby spinach).
- qty: a positive number.
- unit: one of count, carton, bottle, pack, bunch, g, kg, ml, l.
- expiry: ISO date YYYY-MM-DD if a date was spoken, else null.
- confidence: 0 to 1. If you are guessing, use below 0.7.

Return JSON only.
"""


def _audio_mime(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    if guessed and guessed.startswith("audio/"):
        return guessed
    suffix = path.suffix.lower()
    return {
        ".webm": "audio/webm",
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".aac": "audio/aac",
        ".aiff": "audio/aiff",
        ".caf": "audio/x-caf",
    }.get(suffix, "audio/webm")


def vertex_audio_caller() -> GeminiCaller:
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
        response = client.models.generate_content(
            model=model,
            contents=[
                VOICE_PROMPT,
                types.Part.from_bytes(
                    data=path.read_bytes(), mime_type=_audio_mime(path)
                ),
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
            raise RuntimeError("Gemini returned empty voice extract")
        return json.loads(text)

    return call


def ingest_from_audio(
    path: Path,
    *,
    kitchen_id: str = "demo",
    caller: GeminiCaller | None = None,
) -> tuple[list[InventoryItem], list[str], ExtractPayload]:
    call = caller or vertex_audio_caller()
    payload = ExtractPayload.model_validate(call(path))
    accepted, dropped = accept_extract(
        payload, kitchen_id=kitchen_id, source="voice"
    )
    return accepted, dropped, payload
