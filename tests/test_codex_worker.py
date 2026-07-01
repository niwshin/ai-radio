import json
import subprocess
from pathlib import Path

from ai_radio.codex_jobs import make_packet, write_pending_job
from ai_radio.codex_worker import run_once
from ai_radio.models import ResearchItem


def test_run_once_uses_absolute_output_paths(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    data_dir = Path("data")
    packet = make_packet(
        "test",
        1,
        "o3",
        [
            ResearchItem(
                title="Example",
                url="https://example.com",
                fetched_at="2026-06-30T00:00:00+00:00",
            )
        ],
    )
    write_pending_job(data_dir, packet)

    def fake_run(command, **kwargs):
        schema_path = Path(command[command.index("--output-schema") + 1])
        output_path = Path(command[command.index("--output-last-message") + 1])
        assert command[command.index("--model") + 1] == "o3"
        assert schema_path.is_absolute()
        assert schema_path.exists()
        assert output_path.is_absolute()
        output_path.write_text(
            json.dumps(
                {
                    "topic_title": "Test program",
                    "tags": ["test"],
                    "topic_era": "2026",
                    "script": "a" * 100,
                    "segments": [{"title": "Test", "script": "Test script"}],
                    "sources": [
                        {
                            "title": "Example",
                            "url": "https://example.com",
                            "published_at": None,
                            "used_for": "test",
                        }
                    ],
                    "voicevox_text": "a" * 100,
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert run_once(data_dir)
    assert (data_dir / "codex_jobs" / "completed" / f"{packet.job_id}.result.json").exists()
