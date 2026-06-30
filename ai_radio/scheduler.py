from __future__ import annotations

import asyncio
import contextlib
import logging

from ai_radio.service import RadioService

logger = logging.getLogger(__name__)


class BackgroundScheduler:
    def __init__(self, service: RadioService, tick_seconds: int = 30):
        self.service = service
        self.tick_seconds = tick_seconds
        self._task: asyncio.Task | None = None
        self.last_error: str | None = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task

    async def _run(self) -> None:
        while True:
            try:
                await self.service.import_completed_codex_jobs()
                await self.service.create_generation_job_if_due()
                self.service.cleanup_old_artifacts()
                self.last_error = None
            except Exception as exc:
                logger.exception("background scheduler failed")
                self.last_error = str(exc)
            await asyncio.sleep(self.tick_seconds)
