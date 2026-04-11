"""Move inactive Kanban tasks to blockers when enabled via settings."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.core.config import settings


def effective_last_activity(task: dict) -> Optional[datetime]:
    """Clock for staleness: prefer last_activity_at, else updated_at, else created_at."""
    for key in ("last_activity_at", "updated_at", "created_at"):
        v = task.get(key)
        if v is not None:
            return v if isinstance(v, datetime) else None
    return None


def task_is_stale(task: dict, cutoff: datetime) -> bool:
    la = effective_last_activity(task)
    if la is None:
        return False
    return la < cutoff


def inactivity_evidence(days: int) -> Dict[str, Any]:
    now = datetime.utcnow()
    return {
        "source": "system",
        "event": "inactivity",
        "sha": "",
        "url": "",
        "actor": "",
        "at": now.isoformat() + "Z",
        "message": f"No activity for {days} days; moved to Blockers.",
    }


async def mark_stale_tasks_in_project(db, project_id: str) -> Dict[str, Any]:
    """
    For auto-generated board tasks in todo/in_progress/in_review, if last activity is older than
    STALE_TASK_INACTIVITY_DAYS, set status=blockers and append system git_evidence.
    """
    if not bool(getattr(settings, "STALE_TASK_AUTO_BLOCKERS_ENABLED", False)):
        return {"enabled": False, "marked": 0}

    days = int(getattr(settings, "STALE_TASK_INACTIVITY_DAYS", 3) or 3)
    days = max(1, min(days, 365))
    cutoff = datetime.utcnow() - timedelta(days=days)

    query = {
        "project_id": project_id,
        "is_auto_generated": True,
        "status": {"$in": ["todo", "in_progress", "in_review"]},
    }
    cursor = db.tasks.find(query)
    tasks: List[dict] = await cursor.to_list(length=5000)

    ev = inactivity_evidence(days)
    now = datetime.utcnow()
    marked = 0
    for task in tasks:
        if not task_is_stale(task, cutoff):
            continue
        await db.tasks.update_one(
            {"_id": task["_id"]},
            {
                "$set": {
                    "status": "blockers",
                    "updated_at": now,
                },
                "$push": {"git_evidence": ev},
            },
        )
        marked += 1

    return {"enabled": True, "marked": marked, "cutoff_iso": cutoff.isoformat() + "Z", "days": days}


async def mark_stale_tasks_all_projects(db) -> Dict[str, Any]:
    """Background sweep: every distinct project_id on auto-generated tasks."""
    if not bool(getattr(settings, "STALE_TASK_AUTO_BLOCKERS_ENABLED", False)):
        return {"enabled": False, "projects": 0, "marked": 0}
    ids = await db.tasks.distinct("project_id", {"is_auto_generated": True})
    total = 0
    for pid in ids:
        if pid is None:
            continue
        r = await mark_stale_tasks_in_project(db, str(pid))
        total += int(r.get("marked") or 0)
    return {"enabled": True, "projects": len(ids), "marked": total}
