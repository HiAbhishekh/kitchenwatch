from __future__ import annotations

from datetime import date

from kitchenwatch.models import JobRecord, JobStatus


def watch_job_id(kitchen_id: str, as_of: date) -> str:
    return f"watch:{kitchen_id}:{as_of.isoformat()}"


def already_written(job: JobRecord | None) -> bool:
    if job is None:
        return False
    return job.status == "written" and bool(job.calendar_event_id)


def next_status_if_replay(job: JobRecord | None) -> JobStatus | None:
    if already_written(job):
        return "skipped_idempotent"
    return None
