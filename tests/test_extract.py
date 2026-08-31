from __future__ import annotations

import json
from pathlib import Path

from kitchenwatch.extract import accept_extract

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_honest_photo_keeps_canonical_ids_and_converts_kg():
    payload = json.loads((FIXTURES / "extract_honest.json").read_text())
    items, dropped = accept_extract(payload)
    assert dropped == []
    by_id = {item.item_id: item for item in items}
    assert set(by_id) == {"milk", "eggs", "spinach"}
    assert by_id["milk"].unit == "count"
    assert by_id["milk"].expiry.isoformat() == "2026-08-30"
    assert by_id["spinach"].unit == "g"
    assert by_id["spinach"].qty == 200
    assert all(item.source == "photo" for item in items)


def test_live_vertex_snapshot_accepts_three_shelf_items():
    payload = json.loads((FIXTURES / "extract_live_honest.json").read_text())
    items, dropped = accept_extract(payload)
    assert dropped == []
    by_id = {item.item_id: item for item in items}
    assert set(by_id) == {"milk", "eggs", "spinach"}
    assert by_id["milk"].expiry.isoformat() == "2026-08-30"
    assert by_id["eggs"].expiry.isoformat() == "2026-09-04"
    assert by_id["spinach"].expiry.isoformat() == "2026-08-31"


def test_noisy_photo_drops_low_confidence_and_unknown_unit():
    payload = json.loads((FIXTURES / "extract_noisy.json").read_text())
    items, dropped = accept_extract(payload)
    assert [item.item_id for item in items] == ["milk"]
    assert "low_confidence:maybe chicken:0.41" in dropped
    assert "bad_unit:mystery sauce:sachet" in dropped
