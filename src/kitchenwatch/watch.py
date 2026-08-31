from __future__ import annotations

import argparse
import json
from datetime import date

from kitchenwatch.calendar_io import CalendarPort, GoogleCalendar
from kitchenwatch.jobs import already_written, watch_job_id
from kitchenwatch.jobstore import FirestoreJobStore, JobStore
from kitchenwatch.ledger import FirestoreLedger, Ledger
from kitchenwatch.models import JobRecord, ProposedAction
from kitchenwatch.plan import Planner, vertex_planner
from kitchenwatch.retrieve import expiring_within
from kitchenwatch.settings import horizon_days
from kitchenwatch.trust import judge

WATCH_STEPS = ("retrieve", "plan", "trust", "write", "verify")


def run_watch(
    *,
    ledger: Ledger,
    jobs: JobStore,
    calendar: CalendarPort,
    planner: Planner,
    kitchen_id: str = "demo",
    as_of: date | None = None,
    horizon: int | None = None,
) -> JobRecord:
    """Retrieve → plan → trust → write → verify. Trust is not an LLM."""
    as_of = as_of or date.today()
    days = horizon if horizon is not None else horizon_days()
    job_id = watch_job_id(kitchen_id, as_of)
    existing = jobs.get(kitchen_id, job_id)
    if already_written(existing):
        assert existing is not None
        return existing.model_copy(update={"status": "skipped_idempotent"})

    inventory = ledger.list_items(kitchen_id)
    due = expiring_within(inventory, as_of, horizon_days=days)
    if not due:
        job = JobRecord(
            job_id=job_id,
            kitchen_id=kitchen_id,
            as_of=as_of,
            status="skipped_nothing_due",
        )
        jobs.put(job)
        return job

    action = planner(inventory, due, as_of)
    verdict = judge(
        action,
        inventory,
        as_of=as_of,
        kitchen_id=kitchen_id,
        horizon_days=days,
    )
    if not verdict.ok:
        job = JobRecord(
            job_id=job_id,
            kitchen_id=kitchen_id,
            as_of=as_of,
            status="trust_fail",
            proposed=action,
            trust=verdict,
        )
        jobs.put(job)
        return job

    try:
        event_id = calendar.insert(action, job_id)
    except Exception as exc:
        job = JobRecord(
            job_id=job_id,
            kitchen_id=kitchen_id,
            as_of=as_of,
            status="write_fail",
            proposed=action,
            trust=verdict,
            error=str(exc)[:500],
        )
        jobs.put(job)
        return job
    if not calendar.get(event_id):
        job = JobRecord(
            job_id=job_id,
            kitchen_id=kitchen_id,
            as_of=as_of,
            status="verify_fail",
            proposed=action,
            trust=verdict,
            calendar_event_id=event_id,
        )
        jobs.put(job)
        return job

    job = JobRecord(
        job_id=job_id,
        kitchen_id=kitchen_id,
        as_of=as_of,
        status="written",
        proposed=action,
        trust=verdict,
        calendar_event_id=event_id,
    )
    jobs.put(job)
    return job


def job_public(job: JobRecord) -> dict:
    return job.model_dump(mode="json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run KitchenWatch watch")
    parser.add_argument("--kitchen-id", default="demo")
    parser.add_argument("--as-of", default=None, help="YYYY-MM-DD (default today)")
    args = parser.parse_args()
    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    job = run_watch(
        ledger=FirestoreLedger(),
        jobs=FirestoreJobStore(),
        calendar=GoogleCalendar(),
        planner=vertex_planner(),
        kitchen_id=args.kitchen_id,
        as_of=as_of,
    )
    print(json.dumps(job_public(job), indent=2))
    print(f"steps={' → '.join(WATCH_STEPS)}")


if __name__ == "__main__":
    main()
