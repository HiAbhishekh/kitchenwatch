from __future__ import annotations

from datetime import date
from pathlib import Path

from kitchenwatch.extract import ExtractedRow
from kitchenwatch.vision import ingest_from_image


def test_vision_uses_injected_caller_not_vertex(tmp_path: Path):
    photo = tmp_path / "shelf.jpg"
    photo.write_bytes(b"not-an-image")

    def fake(_path: Path) -> dict:
        return {
            "items": [
                {
                    "name": "whole milk",
                    "qty": 1,
                    "unit": "carton",
                    "expiry": "2026-08-30",
                    "confidence": 0.93,
                },
                {
                    "name": "ghost chicken",
                    "qty": 1,
                    "unit": "pack",
                    "expiry": None,
                    "confidence": 0.3,
                },
            ]
        }

    accepted, dropped, payload = ingest_from_image(photo, caller=fake)
    assert [row.name for row in payload.items] == ["whole milk", "ghost chicken"]
    assert [item.item_id for item in accepted] == ["milk"]
    assert accepted[0].expiry == date(2026, 8, 30)
    assert any(r.startswith("low_confidence:ghost chicken") for r in dropped)


def test_expiry_reads_month_name():
    row = ExtractedRow(
        name="milk",
        qty=1,
        unit="count",
        expiry="August 30 2026",
        confidence=0.9,
    )
    assert row.expiry == date(2026, 8, 30)
