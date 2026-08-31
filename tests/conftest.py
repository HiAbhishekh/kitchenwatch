from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from kitchenwatch.models import InventoryItem, ProposedAction

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def as_of() -> date:
    return date(2026, 8, 29)


@pytest.fixture
def ledger(as_of: date) -> list[InventoryItem]:
    payload = _load("ledger_demo.json")
    assert payload["as_of"] == as_of.isoformat()
    return [InventoryItem.model_validate(row) for row in payload["items"]]


@pytest.fixture
def honest_omelette() -> ProposedAction:
    return ProposedAction.model_validate(_load("action_honest_omelette.json"))


@pytest.fixture
def lie_chicken() -> ProposedAction:
    return ProposedAction.model_validate(_load("action_lie_chicken.json"))
