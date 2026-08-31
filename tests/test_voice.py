from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from kitchenwatch.app import create_app
from kitchenwatch.calendar_io import MemoryCalendar
from kitchenwatch.ingest import ingest_voice
from kitchenwatch.jobstore import MemoryJobStore
from kitchenwatch.ledger import MemoryLedger


def test_voice_ingest_writes_accepted_only(tmp_path: Path):
    audio = tmp_path / "shelf.webm"
    audio.write_bytes(b"not-real-audio")
    store = MemoryLedger()

    def fake(_path: Path) -> dict:
        return {
            "items": [
                {
                    "name": "whole milk",
                    "qty": 1,
                    "unit": "carton",
                    "expiry": "2026-08-30",
                    "confidence": 0.9,
                },
                {
                    "name": "chicken",
                    "qty": 1,
                    "unit": "pack",
                    "expiry": None,
                    "confidence": 0.2,
                },
            ]
        }

    accepted, dropped, _ = ingest_voice(audio, store=store, caller=fake)
    assert [item.item_id for item in accepted] == ["milk"]
    assert accepted[0].source == "voice"
    assert any("low_confidence:chicken" in row for row in dropped)
    assert [item.item_id for item in store.list_items("demo")] == ["milk"]


def test_post_ingest_voice(tmp_path: Path):
    audio = tmp_path / "shelf.wav"
    audio.write_bytes(b"xxxx")

    def fake(_path: Path) -> dict:
        return {
            "items": [
                {
                    "name": "eggs",
                    "qty": 6,
                    "unit": "count",
                    "expiry": "2026-09-04",
                    "confidence": 0.88,
                }
            ]
        }

    client = TestClient(
        create_app(
            store=MemoryLedger(),
            audio_caller=fake,
            jobs=MemoryJobStore(),
            calendar=MemoryCalendar(),
        )
    )
    with audio.open("rb") as handle:
        response = client.post(
            "/ingest-voice",
            files={"audio": ("shelf.wav", handle, "audio/wav")},
            data={"kitchen_id": "demo"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"][0]["item_id"] == "eggs"
    assert body["accepted"][0]["source"] == "voice"


def test_ui_has_record_voice():
    client = TestClient(create_app(store=MemoryLedger()))
    page = client.get("/").text
    assert "Record" in page
    assert "Upload audio" in page


def test_audio_suffix_from_safari_and_chrome_types():
    from kitchenwatch.voice import audio_suffix

    assert audio_suffix("shelf.webm", "audio/webm;codecs=opus") == ".webm"
    assert audio_suffix("blob", "audio/mp4") == ".m4a"
    assert audio_suffix("memo.weba", None) == ".webm"
    assert audio_suffix("notes.txt", "text/plain") is None


def test_voice_prompt_resolves_relative_dates_for_grouped_items():
    from kitchenwatch.voice import voice_prompt

    prompt = voice_prompt(date(2026, 8, 31))

    assert "Today is 2026-08-31" in prompt
    assert '"tomorrow" = 2026-09-01' in prompt
    assert '"after 2 days" / "in 2 days" / "two days from today" = 2026-09-02' in prompt
    assert "lady finger and cucumber have expiry 2026-09-02" in prompt


def test_post_ingest_voice_surfaces_extract_error(tmp_path: Path):
    audio = tmp_path / "shelf.wav"
    audio.write_bytes(b"xxxx")

    def boom(_path: Path) -> dict:
        raise RuntimeError("gemini down")

    client = TestClient(
        create_app(
            store=MemoryLedger(),
            audio_caller=boom,
            jobs=MemoryJobStore(),
            calendar=MemoryCalendar(),
        )
    )
    with audio.open("rb") as handle:
        response = client.post(
            "/ingest-voice",
            files={"audio": ("shelf.wav", handle, "audio/wav")},
            data={"kitchen_id": "demo"},
        )
    assert response.status_code == 502
    assert "gemini down" in response.json()["detail"]
