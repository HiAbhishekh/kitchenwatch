from __future__ import annotations

from datetime import date, timedelta

from kitchenwatch.jobs import watch_job_id
from kitchenwatch.models import InventoryItem, ProposedAction, TrustVerdict
from kitchenwatch.normalize import canonical_item_id
from kitchenwatch.retrieve import ledger_by_id


def evaluate_trust(
    action: ProposedAction,
    inventory: list[InventoryItem],
    *,
    as_of: date,
    kitchen_id: str = "demo",
    horizon_days: int = 2,
) -> TrustVerdict:
    """Fail-closed. Gemini does not run here."""
    job_id = watch_job_id(kitchen_id, as_of)
    reasons: list[str] = []
    shelf = ledger_by_id(inventory)
    cutoff = as_of + timedelta(days=horizon_days)

    title = action.title.strip()
    if not title:
        reasons.append("empty_title")

    if not action.uses:
        reasons.append("empty_uses")

    reason_id = canonical_item_id(action.reason_item_id)
    trigger = shelf.get(reason_id)
    if trigger is None:
        reasons.append(f"reason_missing:{reason_id}")
    else:
        if trigger.expiry is None:
            reasons.append(f"reason_no_expiry:{reason_id}")
        elif trigger.expiry < as_of:
            reasons.append(f"reason_already_expired:{reason_id}")
        elif trigger.expiry > cutoff:
            reasons.append(f"reason_outside_horizon:{reason_id}")

    for need in action.uses:
        item_id = canonical_item_id(need.item_id)
        have = shelf.get(item_id)
        if have is None:
            reasons.append(f"not_on_shelf:{item_id}")
            continue
        if have.unit != need.unit:
            reasons.append(f"unit_mismatch:{item_id}:{need.unit}!={have.unit}")
            continue
        if need.qty > have.qty:
            reasons.append(f"qty_short:{item_id}:{need.qty}>{have.qty}")

    return TrustVerdict(ok=len(reasons) == 0, reasons=reasons, job_id=job_id)
