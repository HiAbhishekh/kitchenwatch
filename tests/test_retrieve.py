from __future__ import annotations

from kitchenwatch.retrieve import expiring_within


def test_milk_and_spinach_are_due_eggs_and_onion_are_not(ledger, as_of):
    due = {item.item_id for item in expiring_within(ledger, as_of)}
    assert due == {"milk", "spinach"}


def test_horizon_zero_only_today(ledger, as_of):
    due = expiring_within(ledger, as_of, horizon_days=0)
    assert due == []
