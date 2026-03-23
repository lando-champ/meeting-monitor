"""
Single Groq LLM pass: transcript → summary + action items. Persist to MongoDB.
File uploads still use app.services.groq_processing.transcribe_audio + this module's summarize_and_extract.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, List, Optional, Tuple

from groq import Groq

from app.core.config import settings
from app.core.database import get_database

logger = logging.getLogger(__name__)

MAX_TRANSCRIPT_CHARS = 120_000


def get_groq_client() -> Groq:
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set")
    return Groq(api_key=settings.GROQ_API_KEY)


def summarize_and_extract(transcript: str) -> Tuple[dict, List[str]]:
    """
    One chat completion: overview, key_points, decisions, action_items.
    Returns (summary_dict, action_items_strings).
    """
    text_in = (transcript or "").strip()
    if not text_in:
        return (
            {"overview": "", "key_points": [], "decisions": []},
            [],
        )

    client = get_groq_client()
    prompt = """You are a meeting assistant. Given the following meeting transcript, output a JSON object with exactly these keys (no other keys):
- "overview": one short paragraph summarizing the meeting.
- "key_points": array of strings (main points discussed).
- "decisions": array of strings (decisions made).
- "action_items": array of strings (concrete action items or tasks to do).

Output only valid JSON, no markdown or extra text."""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Transcript:\n\n{text_in[:MAX_TRANSCRIPT_CHARS]}"},
        ],
        temperature=0.2,
    )
    raw = (response.choices[0].message.content or "{}").strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.exception("Groq returned invalid JSON for summarize_and_extract: %s", e)
        raise

    overview = data.get("overview") or ""
    key_points = data.get("key_points")
    decisions = data.get("decisions")
    action_items = data.get("action_items")
    if not isinstance(key_points, list):
        key_points = []
    if not isinstance(decisions, list):
        decisions = []
    if not isinstance(action_items, list):
        action_items = [str(action_items)] if action_items else []
    else:
        action_items = [str(x) for x in action_items]

    summary_dict = {
        "overview": overview,
        "key_points": key_points,
        "decisions": decisions,
    }
    return summary_dict, action_items


def _combine_segments(segments: List[dict]) -> str:
    parts = []
    for s in sorted(segments, key=lambda x: x.get("timestamp") or ""):
        parts.append(s.get("text") or "")
    return "\n".join(parts).strip()


async def analyze_meeting_transcript(
    meeting_id: str,
    language: str = "en",
) -> Optional[dict[str, Any]]:
    """
    Load transcript_segments for meeting_id, call Groq once, write summaries + action_items.
    Returns a small result dict on success, None if no transcript or on failure after logging.
    """
    db = await get_database()
    cursor = db.transcript_segments.find({"meeting_id": meeting_id}).sort("timestamp", 1)
    segments = await cursor.to_list(length=10_000)
    if not segments:
        logger.info("No transcript segments for meeting_id=%s; skipping intelligence", meeting_id)
        return None

    full_text = _combine_segments(segments)
    if not full_text.strip():
        logger.info("Empty combined transcript for meeting_id=%s; skipping intelligence", meeting_id)
        return None

    try:
        summary_dict, action_items = summarize_and_extract(full_text)
    except Exception as e:
        logger.exception("Meeting intelligence failed for meeting_id=%s: %s", meeting_id, e)
        return None

    now = datetime.utcnow()
    overview = summary_dict.get("overview") or ""
    key_points = summary_dict.get("key_points") or []

    await db.summaries.insert_one(
        {
            "meeting_id": meeting_id,
            "language": language,
            "summary_text": overview,
            "key_points": key_points,
            "decisions": summary_dict.get("decisions") or [],
            "created_at": now,
        }
    )

    for text in action_items:
        t = (text or "").strip()
        if not t:
            continue
        await db.action_items.insert_one(
            {
                "meeting_id": meeting_id,
                "text": t,
                "status": "pending",
                "language": language,
                "created_at": now,
            }
        )

    logger.info(
        "Meeting intelligence completed meeting_id=%s action_items=%d",
        meeting_id,
        len(action_items),
    )
    return {
        "meeting_id": meeting_id,
        "overview_len": len(overview),
        "action_items_count": len([x for x in action_items if (x or "").strip()]),
    }
