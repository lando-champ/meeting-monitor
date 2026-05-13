"""Compare auto-generated tasks to meeting transcripts; persist drift report."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.core.database import get_database
from app.services.kanban_agentic_automation import _validate_transcript_evidence

logger = logging.getLogger(__name__)


def _title_tokens(title: str) -> List[str]:
    t = (title or "").lower()
    return [w for w in re.split(r"\W+", t) if len(w) > 2][:12]


async def _transcript_for_meeting(db, meeting_id: str) -> str:
    segs = await db.transcript_segments.find({"meeting_id": meeting_id}).sort("timestamp", 1).to_list(length=10_000)
    return "\n".join((s.get("text") or "").strip() for s in segs if (s.get("text") or "").strip())


def _task_supported_by_transcript(title: str, description: Optional[str], corpus: str) -> bool:
    if not corpus.strip():
        return False
    desc = (description or "").strip()
    if desc and _validate_transcript_evidence(desc[:800], corpus):
        return True
    tokens = _title_tokens(title)
    if len(tokens) < 2:
        return title.strip().lower() in corpus.lower() if title.strip() else False
    corp_l = corpus.lower()
    hits = sum(1 for w in tokens if w in corp_l)
    return hits >= max(2, min(3, len(tokens) // 2))


async def reconcile_project_tasks(
    project_id: str,
    trigger_meeting_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Flag auto tasks whose title/description is not supported by the source meeting transcript.
    Stores a document in ``transcript_task_reconciliation`` for UI / follow-up.
    """
    db = await get_database()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    tasks = await db.tasks.find(
        {"project_id": project_id, "is_auto_generated": True},
    ).to_list(length=5000)

    corpus_by_meeting: Dict[str, str] = {}
    orphan_tasks: List[Dict[str, Any]] = []

    for t in tasks:
        mid = (t.get("source_meeting_id") or "").strip()
        if not mid:
            continue
        if mid not in corpus_by_meeting:
            corpus_by_meeting[mid] = await _transcript_for_meeting(db, mid)
        corpus = corpus_by_meeting[mid]
        title = str(t.get("title") or "")
        desc = t.get("description")
        if not _task_supported_by_transcript(title, desc if isinstance(desc, str) else None, corpus):
            orphan_tasks.append(
                {
                    "task_id": str(t["_id"]),
                    "title": title,
                    "source_meeting_id": mid,
                }
            )

    doc = {
        "project_id": project_id,
        "trigger_meeting_id": trigger_meeting_id,
        "created_at": now,
        "orphan_task_count": len(orphan_tasks),
        "orphan_tasks": orphan_tasks[:200],
    }
    try:
        await db.transcript_task_reconciliation.insert_one(doc)
    except Exception:
        logger.exception("Failed to persist transcript_task_reconciliation project_id=%s", project_id)

    if orphan_tasks and project_id:
        try:
            proj = await db.projects.find_one({"_id": ObjectId(project_id)})
            owner_id = str((proj or {}).get("owner_id") or "").strip()
            if owner_id:
                await db.notifications.insert_one(
                    {
                        "user_id": owner_id,
                        "type": "transcript_task_reconciliation",
                        "message": (
                            f"{len(orphan_tasks)} auto task(s) may lack transcript support "
                            f"after the latest meeting sync."
                        ),
                        "project_id": project_id,
                        "meeting_id": trigger_meeting_id,
                        "read": False,
                        "created_at": now,
                    }
                )
        except Exception:
            logger.exception("Reconciliation notification insert failed project_id=%s", project_id)

    return {
        "project_id": project_id,
        "orphan_task_count": len(orphan_tasks),
        "orphan_tasks": orphan_tasks[:50],
    }
