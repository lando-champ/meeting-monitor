"""Post-meeting orchestration: intelligence + deterministic Kanban rebuild."""
from __future__ import annotations

import logging
from typing import Optional

from app.core.database import get_database
from app.services.meeting_intelligence import analyze_meeting_transcript
from app.services.kanban_agentic_automation import rebuild_kanban_from_meeting_history
from app.services.transcript_task_reconciliation import reconcile_project_tasks
from app.consilium.services.meeting_signals import (
    build_meeting_signal_v1_from_intel,
    insert_meeting_signal,
)

logger = logging.getLogger(__name__)


async def run_meeting_intelligence(
    meeting_id: str,
    language: str = "en",
    project_id: Optional[str] = None,
    sync_kanban: bool = True,
) -> None:
    intel = await analyze_meeting_transcript(meeting_id, language=language)
    if project_id and intel and isinstance(intel.get("summary"), dict):
        try:
            db = await get_database()
            sig = build_meeting_signal_v1_from_intel(
                project_id=str(project_id),
                meeting_id=str(meeting_id),
                summary_dict=intel["summary"],
                action_items=[str(x) for x in (intel.get("action_items") or []) if str(x).strip()],
            )
            await insert_meeting_signal(db, sig)
        except Exception:
            logger.exception("insert_meeting_signal failed meeting_id=%s project_id=%s", meeting_id, project_id)
    if sync_kanban and project_id:
        try:
            await rebuild_kanban_from_meeting_history(project_id, trigger_meeting_id=meeting_id)
        except Exception:
            logger.exception("rebuild_kanban_from_meeting_history failed project_id=%s", project_id)
    if project_id:
        try:
            await reconcile_project_tasks(project_id, trigger_meeting_id=meeting_id)
        except Exception:
            logger.exception("reconcile_project_tasks failed project_id=%s", project_id)
