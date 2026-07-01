from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from ai_radio.models import ScriptOutput
from ai_radio.timeutil import utc_now_iso


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS programs (
                    id TEXT PRIMARY KEY,
                    generated_at TEXT NOT NULL,
                    topic_title TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    topic_era TEXT NOT NULL,
                    script TEXT NOT NULL,
                    sources_json TEXT NOT NULL,
                    audio_path TEXT,
                    status TEXT NOT NULL,
                    error TEXT
                );
                CREATE TABLE IF NOT EXISTS program_playbacks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    program_id TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    status TEXT NOT NULL,
                    FOREIGN KEY(program_id) REFERENCES programs(id)
                );
                CREATE TABLE IF NOT EXISTS source_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    published_at TEXT,
                    text_excerpt TEXT,
                    tags_json TEXT NOT NULL,
                    UNIQUE(url, fetched_at)
                );
                CREATE TABLE IF NOT EXISTS codex_jobs (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    packet_json TEXT NOT NULL,
                    result_path TEXT,
                    error TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_programs_generated_at ON programs(generated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_playbacks_program_id ON program_playbacks(program_id);
                CREATE INDEX IF NOT EXISTS idx_jobs_status ON codex_jobs(status);
                """
            )
            self._ensure_column(conn, "programs", "llm_model", "TEXT")

    @staticmethod
    def _ensure_column(conn: sqlite3.Connection, table: str, column: str, column_type: str) -> None:
        existing = {
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")

    def save_sources(self, items: list[dict[str, Any]]) -> None:
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT OR IGNORE INTO source_items
                (url, title, fetched_at, published_at, text_excerpt, tags_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        item["url"],
                        item["title"],
                        item["fetched_at"],
                        item.get("published_at"),
                        item.get("text_excerpt", ""),
                        json.dumps(item.get("tags", []), ensure_ascii=False),
                    )
                    for item in items
                ],
            )

    def create_codex_job(self, job_id: str, packet: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO codex_jobs (id, created_at, status, packet_json)
                VALUES (?, ?, 'pending', ?)
                """,
                (job_id, utc_now_iso(), json.dumps(packet, ensure_ascii=False)),
            )

    def mark_job(self, job_id: str, status: str, result_path: str | None = None, error: str | None = None) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE codex_jobs SET status = ?, result_path = ?, error = ? WHERE id = ?",
                (status, result_path, error, job_id),
            )

    def pending_job_count(self) -> int:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM codex_jobs WHERE status IN ('pending', 'running')"
            ).fetchone()
            return int(row["count"])

    def due_for_generation(self, interval_seconds: int) -> bool:
        with self.connect() as conn:
            latest = conn.execute(
                """
                SELECT created_at FROM codex_jobs
                ORDER BY created_at DESC LIMIT 1
                """
            ).fetchone()
        if latest is None:
            return True
        from datetime import datetime, timezone

        last = datetime.fromisoformat(latest["created_at"])
        delta = datetime.now(timezone.utc) - last
        return delta.total_seconds() >= interval_seconds

    def completed_jobs(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(
                conn.execute(
                    "SELECT * FROM codex_jobs WHERE status = 'completed' ORDER BY created_at ASC"
                ).fetchall()
            )

    def save_program(
        self,
        output: ScriptOutput,
        audio_path: Path | None,
        status: str,
        llm_model: str | None = None,
        error: str | None = None,
    ) -> str:
        program_id = str(uuid.uuid4())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO programs
                (id, generated_at, topic_title, llm_model, tags_json, topic_era, script, sources_json, audio_path, status, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    program_id,
                    utc_now_iso(),
                    output.topic_title,
                    llm_model,
                    json.dumps(output.tags, ensure_ascii=False),
                    output.topic_era,
                    output.script,
                    output.model_dump_json(),
                    str(audio_path) if audio_path else None,
                    status,
                    error,
                ),
            )
        return program_id

    def set_program_audio(
        self,
        program_id: str,
        audio_path: Path | None,
        status: str = "ready",
        error: str | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE programs SET audio_path = ?, status = ?, error = ? WHERE id = ?",
                (str(audio_path) if audio_path else None, status, error, program_id),
            )

    def latest_programs(self, limit: int = 2) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(
                conn.execute(
                    """
                    SELECT * FROM programs
                    WHERE status = 'ready' AND audio_path IS NOT NULL
                    ORDER BY generated_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            )

    def all_programs(self, limit: int = 50) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(
                conn.execute(
                    "SELECT * FROM programs ORDER BY generated_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            )

    def get_program(self, program_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM programs WHERE id = ?", (program_id,)).fetchone()

    def record_playback_start(self, program_id: str) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO program_playbacks (program_id, started_at, status)
                VALUES (?, ?, 'started')
                """,
                (program_id, utc_now_iso()),
            )
            return int(cur.lastrowid)

    def record_playback_end(self, playback_id: int, status: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE program_playbacks SET ended_at = ?, status = ? WHERE id = ?",
                (utc_now_iso(), status, playback_id),
            )
