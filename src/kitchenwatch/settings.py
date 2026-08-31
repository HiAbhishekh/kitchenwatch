from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"


def load_env(path: Path = ENV_PATH) -> None:
    if not path.is_file():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def gcp_project() -> str:
    return os.environ.get("GCP_PROJECT", "kitchenwatch-demo")


def gcp_location() -> str:
    return os.environ.get("GCP_LOCATION", "global")


def gemini_model() -> str:
    return os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")


def calendar_id() -> str:
    load_env()
    value = os.environ.get("KITCHENWATCH_CALENDAR_ID", "").strip()
    if not value:
        raise RuntimeError("KITCHENWATCH_CALENDAR_ID is missing")
    return value


def calendar_timezone() -> str:
    return os.environ.get("KITCHENWATCH_TZ", "Asia/Kolkata")


def run_sa_email() -> str:
    return os.environ.get(
        "KITCHENWATCH_RUN_SA",
        f"kitchenwatch-run@{gcp_project()}.iam.gserviceaccount.com",
    )


def horizon_days() -> int:
    return int(os.environ.get("EXPIRY_HORIZON_DAYS", "2"))
