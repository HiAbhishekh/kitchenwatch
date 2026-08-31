from __future__ import annotations

from datetime import date

from kitchenwatch.jobs import already_written, next_status_if_replay, watch_job_id
from kitchenwatch.models import JobRecord


def test_job_id_is_kitchen_and_day():
    assert watch_job_id("demo", date(2026, 8, 29)) == "watch:demo:2026-08-29"


def test_replay_skips_when_event_exists():
    job = JobRecord(
        job_id="watch:demo:2026-08-29",
        kitchen_id="demo",
        as_of=date(2026, 8, 29),
        status="written",
        calendar_event_id="evt_1",
    )
    assert already_written(job) is True
    assert next_status_if_replay(job) == "skipped_idempotent"


def test_trust_fail_may_retry():
    job = JobRecord(
        job_id="watch:demo:2026-08-29",
        kitchen_id="demo",
        as_of=date(2026, 8, 29),
        status="trust_fail",
    )
    assert already_written(job) is False
    assert next_status_if_replay(job) is None


def test_written_without_event_id_is_not_idempotent():
    job = JobRecord(
        job_id="watch:demo:2026-08-29",
        kitchen_id="demo",
        as_of=date(2026, 8, 29),
        status="written",
        calendar_event_id=None,
    )
    assert already_written(job) is False
