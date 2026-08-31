from __future__ import annotations

from datetime import date, datetime, timedelta

from kitchenwatch.models import IngredientNeed, InventoryItem, ProposedAction
from kitchenwatch.trust import judge


def test_honest_omelette_passes(ledger, honest_omelette, as_of):
    verdict = judge(honest_omelette, ledger, as_of=as_of)
    assert verdict.ok is True
    assert verdict.reasons == []
    assert verdict.job_id == "watch:demo:2026-08-29"


def test_chicken_not_on_shelf_fails(ledger, lie_chicken, as_of):
    verdict = judge(lie_chicken, ledger, as_of=as_of)
    assert verdict.ok is False
    assert "not_on_shelf:chicken" in verdict.reasons


def test_qty_short_fails(ledger, as_of):
    action = ProposedAction(
        title="Twelve-egg omelette",
        window_start=datetime(2026, 8, 29, 18, 0),
        window_end=datetime(2026, 8, 29, 19, 0),
        reason_item_id="milk",
        uses=[IngredientNeed(item_id="eggs", qty=12, unit="count")],
    )
    verdict = judge(action, ledger, as_of=as_of)
    assert verdict.ok is False
    assert any(r.startswith("qty_short:eggs") for r in verdict.reasons)


def test_unit_mismatch_fails(ledger, as_of):
    action = ProposedAction(
        title="Spinach in the wrong unit",
        window_start=datetime(2026, 8, 29, 18, 0),
        window_end=datetime(2026, 8, 29, 19, 0),
        reason_item_id="milk",
        uses=[IngredientNeed(item_id="spinach", qty=80, unit="count")],
    )
    verdict = judge(action, ledger, as_of=as_of)
    assert verdict.ok is False
    assert "unit_mismatch:spinach:count!=g" in verdict.reasons


def test_reason_without_expiry_cannot_trigger(ledger, as_of):
    action = ProposedAction(
        title="Cook the onion",
        window_start=datetime(2026, 8, 29, 18, 0),
        window_end=datetime(2026, 8, 29, 19, 0),
        reason_item_id="onion",
        uses=[IngredientNeed(item_id="onion", qty=1, unit="count")],
    )
    verdict = judge(action, ledger, as_of=as_of)
    assert verdict.ok is False
    assert "reason_no_expiry:onion" in verdict.reasons


def test_reason_outside_horizon_fails(ledger, as_of):
    action = ProposedAction(
        title="Eggs in five days",
        window_start=datetime(2026, 8, 29, 18, 0),
        window_end=datetime(2026, 8, 29, 19, 0),
        reason_item_id="eggs",
        uses=[IngredientNeed(item_id="eggs", qty=1, unit="count")],
    )
    verdict = judge(action, ledger, as_of=as_of)
    assert verdict.ok is False
    assert "reason_outside_horizon:eggs" in verdict.reasons


def test_empty_title_and_uses_fail(ledger, as_of):
    action = ProposedAction(
        title="   ",
        window_start=datetime(2026, 8, 29, 18, 0),
        window_end=datetime(2026, 8, 29, 19, 0),
        reason_item_id="milk",
        uses=[],
    )
    verdict = judge(action, ledger, as_of=as_of)
    assert verdict.ok is False
    assert "empty_title" in verdict.reasons
    assert "empty_uses" in verdict.reasons


def test_unknown_reason_fails(ledger, as_of):
    action = ProposedAction(
        title="Ghost ingredient",
        window_start=datetime(2026, 8, 29, 18, 0),
        window_end=datetime(2026, 8, 29, 19, 0),
        reason_item_id="paneer",
        uses=[IngredientNeed(item_id="milk", qty=1, unit="count")],
    )
    extra = InventoryItem(
        item_id="milk",
        name="Milk",
        qty=1,
        unit="count",
        expiry=as_of + timedelta(days=1),
        source="fixture",
        confidence=0.9,
    )
    verdict = judge(action, [extra], as_of=as_of)
    assert verdict.ok is False
    assert "reason_missing:paneer" in verdict.reasons
