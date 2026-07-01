from __future__ import annotations

import json
import uuid
from pathlib import Path

from ai_radio.models import CodexJobPacket, ResearchItem
from ai_radio.timeutil import utc_now_iso


def ensure_job_dirs(data_dir: Path) -> dict[str, Path]:
    root = data_dir / "codex_jobs"
    dirs = {
        "root": root,
        "pending": root / "pending",
        "running": root / "running",
        "completed": root / "completed",
        "failed": root / "failed",
    }
    for directory in dirs.values():
        directory.mkdir(parents=True, exist_ok=True)
    return dirs


def make_packet(theme: str, target_minutes: int, model: str, candidates: list[ResearchItem]) -> CodexJobPacket:
    return CodexJobPacket(
        job_id=str(uuid.uuid4()),
        created_at=utc_now_iso(),
        theme=theme,
        target_minutes=target_minutes,
        model=model,
        candidates=candidates,
    )


def write_pending_job(data_dir: Path, packet: CodexJobPacket) -> Path:
    dirs = ensure_job_dirs(data_dir)
    path = dirs["pending"] / f"{packet.job_id}.json"
    path.write_text(packet.model_dump_json(indent=2), encoding="utf-8")
    return path


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
