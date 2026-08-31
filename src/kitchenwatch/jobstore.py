from __future__ import annotations

from typing import Protocol

from kitchenwatch.models import JobRecord
from kitchenwatch.settings import gcp_project, load_env


def job_doc_id(job_id: str) -> str:
    return job_id.replace(":", "__")


class JobStore(Protocol):
    def get(self, kitchen_id: str, job_id: str) -> JobRecord | None: ...
    def put(self, job: JobRecord) -> None: ...
    def list_jobs(self, kitchen_id: str) -> list[JobRecord]: ...


class MemoryJobStore:
    def __init__(self) -> None:
        self._jobs: dict[tuple[str, str], JobRecord] = {}

    def get(self, kitchen_id: str, job_id: str) -> JobRecord | None:
        return self._jobs.get((kitchen_id, job_id))

    def put(self, job: JobRecord) -> None:
        self._jobs[(job.kitchen_id, job.job_id)] = job

    def list_jobs(self, kitchen_id: str) -> list[JobRecord]:
        return [
            job
            for (kid, _), job in sorted(self._jobs.items())
            if kid == kitchen_id
        ]


class FirestoreJobStore:
    def __init__(self, client=None) -> None:
        load_env()
        if client is None:
            from google.cloud import firestore

            client = firestore.Client(project=gcp_project())
        self._db = client

    def _col(self, kitchen_id: str):
        return self._db.collection("kitchens").document(kitchen_id).collection("jobs")

    def get(self, kitchen_id: str, job_id: str) -> JobRecord | None:
        snap = self._col(kitchen_id).document(job_doc_id(job_id)).get()
        if not snap.exists:
            return None
        return JobRecord.model_validate(snap.to_dict())

    def put(self, job: JobRecord) -> None:
        self._col(job.kitchen_id).document(job_doc_id(job.job_id)).set(
            job.model_dump(mode="json")
        )

    def list_jobs(self, kitchen_id: str) -> list[JobRecord]:
        docs = self._col(kitchen_id).stream()
        jobs = [JobRecord.model_validate(doc.to_dict() or {}) for doc in docs]
        return sorted(jobs, key=lambda job: job.job_id)
