from __future__ import annotations

import os
from typing import Protocol

from kitchenwatch.models import ProposedAction
from kitchenwatch.settings import (
    calendar_id,
    calendar_timezone,
    gcp_project,
    load_env,
    run_sa_email,
)

CAL_SCOPE = "https://www.googleapis.com/auth/calendar"


class CalendarPort(Protocol):
    def insert(self, action: ProposedAction, job_id: str) -> str: ...
    def get(self, event_id: str) -> bool: ...


class MemoryCalendar:
    def __init__(self) -> None:
        self.events: dict[str, dict] = {}
        self.insert_count = 0
        self.fail_get = False
        self.fail_insert = False

    def insert(self, action: ProposedAction, job_id: str) -> str:
        if self.fail_insert:
            raise RuntimeError("calendar_insert_failed")
        self.insert_count += 1
        event_id = f"evt_{self.insert_count}"
        self.events[event_id] = {
            "job_id": job_id,
            "title": action.title,
        }
        return event_id

    def get(self, event_id: str) -> bool:
        if self.fail_get:
            return False
        return event_id in self.events


def _credentials():
    from google.auth import default, impersonated_credentials

    load_env()
    creds, _ = default(scopes=[CAL_SCOPE], quota_project_id=gcp_project())
    if os.environ.get("K_SERVICE"):
        return creds
    return impersonated_credentials.Credentials(
        source_credentials=creds,
        target_principal=run_sa_email(),
        target_scopes=[CAL_SCOPE],
        lifetime=3600,
    )


class GoogleCalendar:
    def __init__(self, service=None, calendar: str | None = None) -> None:
        load_env()
        self._calendar_id = calendar or calendar_id()
        self._tz = calendar_timezone()
        if service is None:
            from googleapiclient.discovery import build

            service = build(
                "calendar",
                "v3",
                credentials=_credentials(),
                cache_discovery=False,
            )
        self._service = service

    def insert(self, action: ProposedAction, job_id: str) -> str:
        uses = ", ".join(f"{need.item_id} {need.qty}{need.unit}" for need in action.uses)
        body = {
            "summary": action.title,
            "description": (
                "KitchenWatch found food expiring soon and scheduled one safe cook.\n\n"
                f"What to cook: {action.title}\n"
                f"Why now: {action.reason_item_id} is inside the expiry window.\n"
                f"Use: {uses}\n"
                f"Trust: every ingredient was checked against the Firestore shelf.\n\n"
                f"Notes: {action.notes}\n"
                f"job_id={job_id}"
            ),
            "start": {
                "dateTime": action.window_start.isoformat(),
                "timeZone": self._tz,
            },
            "end": {
                "dateTime": action.window_end.isoformat(),
                "timeZone": self._tz,
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 60},
                    {"method": "email", "minutes": 120},
                ],
            },
        }
        created = (
            self._service.events()
            .insert(
                calendarId=self._calendar_id,
                body=body,
                sendUpdates="none",
            )
            .execute()
        )
        event_id = created.get("id")
        if not event_id:
            raise RuntimeError("Calendar insert returned no event id")
        return event_id

    def get(self, event_id: str) -> bool:
        got = (
            self._service.events()
            .get(calendarId=self._calendar_id, eventId=event_id)
            .execute()
        )
        return bool(got.get("id")) and got.get("status") != "cancelled"
