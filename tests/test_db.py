from pathlib import Path

from ai_radio.db import Database
from ai_radio.models import ScriptOutput


def make_output() -> ScriptOutput:
    return ScriptOutput.model_validate(
        {
            "topic_title": "Test program",
            "tags": ["test"],
            "topic_era": "2026",
            "script": "a" * 100,
            "segments": [{"title": "Test", "script": "Test script"}],
            "sources": [{"title": "Example", "url": "https://example.com", "published_at": None, "used_for": "test"}],
            "voicevox_text": "a" * 100,
        }
    )


def test_programs_table_has_llm_model_column(tmp_path):
    db = Database(tmp_path / "ai_radio.sqlite3")
    with db.connect() as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(programs)")}
    assert "llm_model" in columns


def test_save_program_records_llm_model(tmp_path):
    db = Database(tmp_path / "ai_radio.sqlite3")
    program_id = db.save_program(make_output(), Path("/tmp/audio.mp3"), "ready", llm_model="o3")
    row = db.get_program(program_id)
    assert row is not None
    assert row["llm_model"] == "o3"
