from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class SourceRef(BaseModel):
    title: str = Field(min_length=1)
    url: HttpUrl
    published_at: str | None = None
    used_for: str | None = None


class Segment(BaseModel):
    title: str = Field(min_length=1)
    script: str = Field(min_length=1)


class ScriptOutput(BaseModel):
    topic_title: str = Field(min_length=1)
    tags: list[str] = Field(min_length=1, max_length=12)
    topic_era: str = Field(description="例: 2026年夏", min_length=1)
    script: str = Field(min_length=100)
    segments: list[Segment] = Field(min_length=1)
    sources: list[SourceRef] = Field(min_length=1)
    voicevox_text: str = Field(min_length=100)


class ResearchItem(BaseModel):
    title: str
    url: str
    snippet: str = ""
    fetched_at: str
    published_at: str | None = None
    text_excerpt: str = ""
    tags: list[str] = []


class CodexJobPacket(BaseModel):
    job_id: str
    created_at: str
    theme: str
    target_minutes: int
    candidates: list[ResearchItem]


class ProgramSummary(BaseModel):
    id: str
    generated_at: str
    topic_title: str
    tags: list[str]
    topic_era: str
    sources: list[SourceRef]
    audio_url: str | None
    status: str
    error: str | None = None


class PlaybackStatus(BaseModel):
    queue: list[ProgramSummary]
    now_playing: ProgramSummary | None = None
    pending_jobs: int
    last_error: str | None = None


PlaybackEventStatus = Literal["started", "completed", "interrupted", "failed"]
