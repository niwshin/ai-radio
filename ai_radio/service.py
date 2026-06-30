from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from pydantic import ValidationError

from ai_radio.codex_jobs import ensure_job_dirs, make_packet, write_pending_job
from ai_radio.config import Settings
from ai_radio.db import Database
from ai_radio.models import ProgramSummary, ScriptOutput
from ai_radio.research import Researcher
from ai_radio.tts import VoicevoxSynthesizer


class RadioService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = Database(settings.db_path)
        self.researcher = Researcher(settings.searxng_url, settings.max_candidates)
        self.tts = VoicevoxSynthesizer(settings.voicevox_url, settings.voicevox_speaker, settings.audio_dir)
        ensure_job_dirs(settings.data_dir)

    async def create_generation_job_if_due(self) -> str | None:
        if self.db.pending_job_count() > 0:
            return None
        if not self.db.due_for_generation(self.settings.generation_interval_seconds):
            return None
        items = await self.researcher.collect(self.settings.theme)
        if not items:
            return None
        self.db.save_sources([item.model_dump() for item in items])
        packet = make_packet(self.settings.theme, self.settings.program_target_minutes, items)
        write_pending_job(self.settings.data_dir, packet)
        self.db.create_codex_job(packet.job_id, packet.model_dump())
        return packet.job_id

    async def import_completed_codex_jobs(self) -> list[str]:
        dirs = ensure_job_dirs(self.settings.data_dir)
        imported: list[str] = []
        for result_path in sorted(dirs["completed"].glob("*.result.json")):
            job_id = result_path.name.removesuffix(".result.json")
            try:
                output = ScriptOutput.model_validate_json(result_path.read_text(encoding="utf-8"))
                job_packet_path = dirs["completed"] / f"{job_id}.json"
                if job_packet_path.exists():
                    packet_payload = json.loads(job_packet_path.read_text(encoding="utf-8"))
                    self.validate_sources(output, {item["url"] for item in packet_payload.get("candidates", [])})
                program_id = self.db.save_program(output, None, "synthesizing")
                try:
                    audio_path = await self.tts.synthesize_program(program_id, output.voicevox_text)
                    self.db.set_program_audio(program_id, audio_path, "ready")
                except Exception as exc:
                    self.db.set_program_audio(program_id, None, "failed", str(exc))
                self.db.mark_job(job_id, "imported", str(result_path), None)
                imported.append(program_id)
                result_path.rename(dirs["completed"] / f"{job_id}.imported.json")
            except (ValidationError, OSError, json.JSONDecodeError, ValueError) as exc:
                self.db.mark_job(job_id, "failed", str(result_path), str(exc))
                result_path.rename(dirs["failed"] / f"{job_id}.bad-result.json")
        for error_path in sorted(dirs["failed"].glob("*.error.txt")):
            job_id = error_path.name.removesuffix(".error.txt")
            self.db.mark_job(job_id, "failed", str(error_path), error_path.read_text(encoding="utf-8")[:4000])
        return imported

    def cleanup_old_artifacts(self) -> None:
        cutoff = time.time() - self.settings.retention_days * 86400
        for directory in [self.settings.audio_dir, self.settings.codex_jobs_dir / "failed"]:
            if not directory.exists():
                continue
            for path in directory.iterdir():
                if path.is_file() and path.stat().st_mtime < cutoff:
                    path.unlink(missing_ok=True)

    def latest_queue(self) -> list[ProgramSummary]:
        return [self._row_to_summary(row) for row in self.db.latest_programs(2)]

    def programs(self) -> list[ProgramSummary]:
        return [self._row_to_summary(row) for row in self.db.all_programs(50)]

    def program_audio_path(self, program_id: str) -> Path | None:
        row = self.db.get_program(program_id)
        if row is None or not row["audio_path"]:
            return None
        path = Path(row["audio_path"])
        return path if path.exists() else None

    @staticmethod
    def _row_to_summary(row) -> ProgramSummary:
        sources_payload = json.loads(row["sources_json"])
        return ProgramSummary(
            id=row["id"],
            generated_at=row["generated_at"],
            topic_title=row["topic_title"],
            tags=json.loads(row["tags_json"]),
            topic_era=row["topic_era"],
            sources=sources_payload.get("sources", []),
            audio_url=f"/api/audio/{row['id']}" if row["status"] == "ready" and row["audio_path"] else None,
            status=row["status"],
            error=row["error"],
        )

    @staticmethod
    def validate_sources(output: ScriptOutput, candidate_urls: set[str]) -> None:
        normalized = {normalize_url(url) for url in candidate_urls}
        for source in output.sources:
            if normalize_url(str(source.url)) not in normalized:
                raise ValueError(f"source URL was not in research packet: {source.url}")


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme.lower(), netloc, path, "", "", ""))
