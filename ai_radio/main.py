from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ai_radio.config import settings
from ai_radio.models import PlaybackStatus
from ai_radio.scheduler import BackgroundScheduler
from ai_radio.service import RadioService


service = RadioService(settings)
scheduler = BackgroundScheduler(service)


@asynccontextmanager
async def lifespan(_: FastAPI):
    scheduler.start()
    yield
    await scheduler.stop()


app = FastAPI(title="AI Radio", lifespan=lifespan)


class PlaybackEndRequest(BaseModel):
    playback_id: int
    status: str = "completed"


@app.get("/api/status", response_model=PlaybackStatus)
def status() -> PlaybackStatus:
    queue = service.latest_queue()
    return PlaybackStatus(
        queue=queue,
        now_playing=queue[0] if queue else None,
        pending_jobs=service.db.pending_job_count(),
        last_error=scheduler.last_error,
    )


@app.get("/api/programs")
def programs():
    return service.programs()


@app.get("/api/audio/{program_id}")
def audio(program_id: str):
    path = service.program_audio_path(program_id)
    if path is None:
        raise HTTPException(status_code=404, detail="audio not found")
    return FileResponse(path, media_type="audio/mpeg", filename=f"{program_id}.mp3")


@app.post("/api/playback/{program_id}/start")
def playback_start(program_id: str):
    if service.db.get_program(program_id) is None:
        raise HTTPException(status_code=404, detail="program not found")
    return {"playback_id": service.db.record_playback_start(program_id)}


@app.post("/api/playback/end")
def playback_end(req: PlaybackEndRequest):
    service.db.record_playback_end(req.playback_id, req.status)
    return {"ok": True}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
