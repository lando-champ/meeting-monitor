"""Build or load cached project-wide transcript RAG indexes for Q&A / copilot."""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

from app.core.config import settings
from app.services.kanban_agentic_automation import _clean_transcript
from app.services.transcript_rag.core import TranscriptRAGIndex, retrieve_context_for_user_query

logger = logging.getLogger(__name__)


def _cache_dir_for_project(project_id: str) -> Optional[Path]:
    raw = (getattr(settings, "TRANSCRIPT_RAG_CACHE_DIR", "") or "").strip()
    if not raw:
        return None
    return Path(raw) / f"proj_{project_id}"


def _fingerprint_meetings(meetings: list) -> str:
    parts = []
    for m in meetings:
        mid = str(m.get("_id", ""))
        sa = m.get("started_at")
        ea = m.get("ended_at")
        parts.append(f"{mid}:{sa}:{ea}")
    blob = "|".join(sorted(parts))
    return hashlib.sha256(blob.encode("utf-8", errors="ignore")).hexdigest()[:24]


async def load_project_rag_index(
    db,
    project_id: str,
) -> Tuple[Optional[TranscriptRAGIndex], str, Dict[str, int]]:
    """
    Load FAISS index for all meetings in a project (disk cache when TRANSCRIPT_RAG_CACHE_DIR is set).
    Returns (index or None, latest_meeting_id, ordinal_by_meeting_id).
    """
    meetings = await db.meetings.find({"project_id": project_id}).sort("started_at", 1).to_list(length=10_000)
    if not meetings:
        return None, "", {}
    ordinal_by_meeting_id: Dict[str, int] = {}
    meeting_cleaned_by_id: Dict[str, str] = {}
    for i, m in enumerate(meetings):
        mid = str(m["_id"])
        ordinal_by_meeting_id[mid] = i
        segs = await db.transcript_segments.find({"meeting_id": mid}).sort("timestamp", 1).to_list(length=10_000)
        text = "\n".join([(s.get("text") or "").strip() for s in segs if (s.get("text") or "").strip()])
        cleaned = _clean_transcript(text)
        if cleaned:
            meeting_cleaned_by_id[mid] = cleaned
    latest_meeting_id = str(meetings[-1]["_id"])
    fp = _fingerprint_meetings(meetings)
    cache_root = _cache_dir_for_project(project_id)
    if cache_root:
        version_dir = cache_root / fp
        cached = TranscriptRAGIndex.load_from_disk(str(version_dir))
        if cached is not None:
            return cached, latest_meeting_id, ordinal_by_meeting_id
    idx = TranscriptRAGIndex.from_meeting_texts(meeting_cleaned_by_id, ordinal_by_meeting_id)
    if idx is not None and cache_root:
        try:
            cache_root.mkdir(parents=True, exist_ok=True)
            version_dir = cache_root / fp
            idx.save_disk(str(version_dir))
            (cache_root / "meta.json").write_text(json.dumps({"fingerprint": fp}, indent=0), encoding="utf-8")
        except Exception as e:
            logger.warning("Transcript RAG cache write failed: %s", e)
    return idx, latest_meeting_id, ordinal_by_meeting_id


async def retrieve_project_rag_snippet(
    db,
    project_id: str,
    query: str,
    prefer_meeting_id: Optional[str] = None,
) -> Tuple[str, float]:
    """Return capped RAG context string and best raw score (empty if disabled or no index)."""
    if not bool(getattr(settings, "KANBAN_RAG_ENABLED", True)):
        return "", 0.0
    idx, latest_mid, _ = await load_project_rag_index(db, project_id)
    if idx is None:
        return "", 0.0
    focus_mid = (prefer_meeting_id or "").strip() or latest_mid
    return retrieve_context_for_user_query(idx, focus_mid, query)
