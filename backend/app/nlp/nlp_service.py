"""
Transcript → Groq LLM → summary + action items. Saves to summaries and action_items collections.
"""
from datetime import datetime
from typing import List, Optional

from app.core.database import get_database
from app.services.groq_processing import summarize_and_extract


def _combine_transcripts(segments: List[dict]) -> str:
    """Build one text from transcript segments."""
    parts = []
    for s in sorted(segments, key=lambda x: x.get("timestamp") or ""):
        parts.append(s.get("text") or "")
    return "\n".join(parts).strip()


class NLPService:
    """Generate summary and extract action items from meeting transcript using Groq."""

    async def generate_summary(self, meeting_id: str, language: str = "en") -> Optional[str]:
        """Load transcript, call Groq, save to summaries. Returns summary text."""
        db = await get_database()
        cursor = db.transcript_segments.find({"meeting_id": meeting_id}).sort("timestamp", 1)
        segments = await cursor.to_list(length=10000)
        if not segments:
            return None
        full_text = _combine_transcripts(segments)
        if not full_text.strip():
            return None
        try:
            summary_dict, _ = summarize_and_extract(full_text)
        except Exception:
            return None
        overview = summary_dict.get("overview") or ""
        key_points = summary_dict.get("key_points") or []
        now = datetime.utcnow()
        await db.summaries.insert_one({
            "meeting_id": meeting_id,
            "language": language,
            "summary_text": overview,
            "key_points": key_points,
            "created_at": now,
        })
        return overview

    async def extract_action_items(self, meeting_id: str, language: str = "en") -> List[dict]:
        """Load transcript, call Groq, save to action_items. Returns list of {text, ...}."""
        db = await get_database()
        cursor = db.transcript_segments.find({"meeting_id": meeting_id}).sort("timestamp", 1)
        segments = await cursor.to_list(length=10000)
        if not segments:
            return []
        full_text = _combine_transcripts(segments)
        if not full_text.strip():
            return []
        try:
            _, action_items = summarize_and_extract(full_text)
        except Exception:
            return []
        now = datetime.utcnow()
        result = []
        for text in action_items:
            doc = {
                "meeting_id": meeting_id,
                "text": text,
                "status": "pending",
                "language": language,
                "created_at": now,
            }
            await db.action_items.insert_one(doc)
            result.append(doc)
        return result


_nlp_service: Optional[NLPService] = None


def get_nlp_service() -> NLPService:
    global _nlp_service
    if _nlp_service is None:
        _nlp_service = NLPService()
    return _nlp_service
