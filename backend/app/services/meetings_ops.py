"""Post-meeting orchestration: one intelligence pass, optional background task sync."""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from app.services.meeting_intelligence import analyze_meeting_transcript
from app.services.project_task_extractor import sync_tasks_to_kairox

logger = logging.getLogger(__name__)


def schedule_task_sync(project_id: str) -> None:
    async def _run() -> None:
        try:
            await sync_tasks_to_kairox(project_id)
        except Exception:
            logger.exception("sync_tasks_to_kairox failed project_id=%s", project_id)

    asyncio.create_task(_run())


async def run_meeting_intelligence(
    meeting_id: str,
    language: str = "en",
    project_id: Optional[str] = None,
    sync_kanban: bool = True,
) -> None:
    await analyze_meeting_transcript(meeting_id, language=language)
    if sync_kanban and project_id:
        schedule_task_sync(project_id)
