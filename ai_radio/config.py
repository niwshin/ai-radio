from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return int(raw)


@dataclass(frozen=True)
class Settings:
    db_path: Path = Path(os.getenv("AI_RADIO_DB_PATH", "/data/ai_radio.sqlite3"))
    data_dir: Path = Path(os.getenv("AI_RADIO_DATA_DIR", "/data"))
    searxng_url: str = os.getenv("AI_RADIO_SEARXNG_URL", "http://searxng:8080")
    voicevox_url: str = os.getenv("AI_RADIO_VOICEVOX_URL", "http://voicevox:50021")
    voicevox_speaker: int = _int_env("AI_RADIO_VOICEVOX_SPEAKER", 2)
    generation_interval_seconds: int = _int_env("AI_RADIO_GENERATION_INTERVAL_SECONDS", 3600)
    program_target_minutes: int = _int_env("AI_RADIO_PROGRAM_TARGET_MINUTES", 30)
    theme: str = os.getenv("AI_RADIO_THEME", "tech gadgets trending")
    max_candidates: int = _int_env("AI_RADIO_MAX_CANDIDATES", 20)
    retention_days: int = _int_env("AI_RADIO_RETENTION_DAYS", 7)

    @property
    def audio_dir(self) -> Path:
        return self.data_dir / "audio"

    @property
    def codex_jobs_dir(self) -> Path:
        return self.data_dir / "codex_jobs"


settings = Settings()
