"""Async prefetch for monitoring graph inputs (meeting signals + optional transcript RAG)."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.consilium.services.meeting_signals import get_latest_meeting_signal
from app.services.transcript_rag.service import retrieve_project_rag_snippet

_TOKEN = re.compile(r"[a-z0-9]{5,}", re.IGNORECASE)


def compute_blocker_recurrence_score(
    snippet: str,
    blockers: List[Dict[str, Any]],
    meeting_signal: Optional[Dict[str, Any]],
) -> float:
    """
    Deterministic overlap score in [0, 1]: RAG text vs blocker phrases + signal excerpt tokens.
    """
    sl = (snippet or "").lower()
    if not sl.strip():
        return 0.0
    hits = 0
    for b in blockers or []:
        msg = str(b.get("message") or b.get("reason") or "").strip().lower()
        if len(msg) >= 8 and msg[:120] in sl:
            hits += 2
        elif len(msg) >= 6:
            for frag in (msg[:40], msg[40:80]):
                if len(frag) >= 6 and frag in sl:
                    hits += 1
                    break
    if meeting_signal:
        ex = str(meeting_signal.get("summary_excerpt") or "").lower()
        toks = set(_TOKEN.findall(ex)) | set(_TOKEN.findall(str(meeting_signal.get("overview") or "")))
        for tok in list(toks)[:60]:
            if len(tok) >= 6 and tok in sl:
                hits += 1
    return max(0.0, min(1.0, hits / 12.0))


async def prefetch_monitoring_context(
    db,
    *,
    workspace_id: str,
    workspace: Dict[str, Any],
) -> Dict[str, Any]:
    """Returns keys to merge into LangGraph initial_state (may include internal ids)."""
    extras: Dict[str, Any] = {}
    project_id = workspace.get("project_id")
    if not project_id:
        return extras
    project_id = str(project_id)

    sig = await get_latest_meeting_signal(db, workspace_id)
    if sig:
        extras["meeting_signal"] = sig.model_dump(exclude={"id"}, exclude_none=True)
        extras["_meeting_signal_mongo_id"] = sig.id

    if not bool(getattr(settings, "MONITORING_TRANSCRIPT_RAG_ENABLED", False)):
        return extras
    if not bool(getattr(settings, "KANBAN_RAG_ENABLED", True)):
        return extras

    query = "blockers delays dependencies cannot proceed blocked waiting risk"
    snippet, _best = await retrieve_project_rag_snippet(db, project_id, query)
    ms_dict = extras.get("meeting_signal") if isinstance(extras.get("meeting_signal"), dict) else None
    blockers = list(workspace.get("blockers") or [])
    score = compute_blocker_recurrence_score(snippet, blockers, ms_dict)
    extras["transcript_rag_evidence"] = snippet or ""
    extras["blocker_recurrence_score"] = score
    if snippet and snippet.strip():
        ev = list(workspace.get("external_events") or [])
        ev.append(
            {
                "source": "transcript_rag",
                "query": query,
                "excerpt_chars": len(snippet),
                "blocker_recurrence_score": score,
                "at": datetime.now(timezone.utc).isoformat(),
            }
        )
        extras["external_events"] = ev[-100:]
    return extras
