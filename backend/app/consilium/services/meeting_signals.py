"""Read/write `meeting_signals` for Consilium monitoring enrichment."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.consilium.models.meeting_signal import MeetingSignalV1


_SCOPE_HINTS = re.compile(
    r"\b(scope|mvp|out of scope|roadmap|milestone|deadline|priority|phase)\b",
    re.IGNORECASE,
)
_BLOCKER_HINTS = re.compile(
    r"\b(blocked|blocker|stuck|waiting on|dependency|cannot proceed|delay|risk)\b",
    re.IGNORECASE,
)


def _excerpt(text: str, max_len: int = 600) -> str:
    t = (text or "").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 3] + "..."


def _scope_mentions_from_text(parts: List[str]) -> List[str]:
    out: List[str] = []
    for p in parts:
        s = (p or "").strip()
        if not s or len(s) < 12:
            continue
        if _SCOPE_HINTS.search(s) and s not in out:
            out.append(s[:500])
    return out[:25]


def _blockers_from_action_items(action_items: List[str]) -> List[Dict[str, Any]]:
    blockers: List[Dict[str, Any]] = []
    for raw in action_items:
        t = (raw or "").strip()
        if not t or not _BLOCKER_HINTS.search(t):
            continue
        blockers.append(
            {
                "message": t[:2000],
                "severity": "high" if "block" in t.lower() else "medium",
            }
        )
    return blockers[:30]


def build_meeting_signal_v1_from_intel(
    *,
    project_id: str,
    meeting_id: str,
    summary_dict: Dict[str, Any],
    action_items: List[str],
) -> MeetingSignalV1:
    overview = str(summary_dict.get("overview") or "")
    key_points = [str(x) for x in (summary_dict.get("key_points") or []) if str(x).strip()]
    decisions = [str(x) for x in (summary_dict.get("decisions") or []) if str(x).strip()]
    scope_mentions = _scope_mentions_from_text([*key_points, *decisions, overview])
    blockers = _blockers_from_action_items(action_items)
    confirmed = [str(x).strip() for x in action_items if str(x).strip()][:80]
    return MeetingSignalV1(
        project_id=str(project_id),
        meeting_id=str(meeting_id),
        summary_excerpt=_excerpt(overview, 800),
        confirmed_tasks=confirmed,
        blockers=blockers,
        scope_mentions=scope_mentions,
        source="post_meeting_intelligence",
    )


async def insert_meeting_signal(db, signal: MeetingSignalV1) -> str:
    coll = db["meeting_signals"]
    doc = signal.to_mongo()
    res = await coll.insert_one(doc)
    return str(res.inserted_id)


async def get_latest_meeting_signal(db, workspace_id: str) -> Optional[MeetingSignalV1]:
    """
    Latest unprocessed signal for the workspace's linked corporate project_id.
    """
    ws = await db["workspaces"].find_one({"_id": ObjectId(workspace_id)}, projection={"project_id": 1})
    if not ws:
        return None
    pid = ws.get("project_id")
    if not pid:
        return None
    pid = str(pid)
    doc = await db["meeting_signals"].find_one(
        {"project_id": pid, "processed": False},
        sort=[("created_at", -1)],
    )
    if not doc:
        return None
    return MeetingSignalV1.from_mongo(doc)


async def mark_meeting_signal_processed(db, signal_mongo_id: str) -> None:
    if not signal_mongo_id:
        return
    try:
        oid = ObjectId(signal_mongo_id)
    except Exception:
        return
    await db["meeting_signals"].update_one(
        {"_id": oid},
        {"$set": {"processed": True, "processed_at": datetime.utcnow()}},
    )
