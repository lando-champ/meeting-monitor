"""
Extract tasks from meeting transcripts (Groq LLM) and sync to Kairox board.
Returns JSON with keys: todo, in_progress, in_review, done, blockers.
Creates or updates tasks with fuzzy duplicate detection on title.
"""
import json
import logging
import re
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Dict, List

from groq import Groq

from app.core.config import settings
from app.core.database import get_database

logger = logging.getLogger(__name__)

# Kairox 5 columns
STATUS_KEYS = ["todo", "in_progress", "in_review", "done", "blockers"]

EXTRACT_PROMPT = """You are a meeting assistant. Given the following meeting transcript, extract all tasks and action items and classify each into exactly one of these statuses:

- **todo**: Tasks not started / to be done later.
- **in_progress**: Tasks currently being worked on.
- **in_review**: Tasks completed and awaiting review or sign-off.
- **done**: Tasks completed and approved.
- **blockers**: Tasks blocked or blocked by dependencies / issues.

Output a JSON object with exactly these 5 keys (no other keys). Each value is an array of task objects.
Each task object must have: "title" (string), and optionally "description" (string), "owner" (string, assignee name), "deadline" (string, e.g. "2025-03-01" or "next week"), "subtasks" (array of strings), "status" (one of: todo, in_progress, in_review, done, blockers).

Example format:
{
  "todo": [{"title": "Review PR", "description": "Check the new API", "owner": "Alice"}],
  "in_progress": [{"title": "Fix login bug", "owner": "Bob"}],
  "in_review": [],
  "done": [{"title": "Deploy staging"}],
  "blockers": [{"title": "Waiting on design", "description": "Blocked until design is ready"}]
}

Output only valid JSON, no markdown or extra text."""


def _get_client() -> Groq:
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set")
    return Groq(api_key=settings.GROQ_API_KEY)


def _normalize_title(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def _title_similarity(a: str, b: str) -> float:
    na, nb = _normalize_title(a), _normalize_title(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def _find_similar_task(existing_tasks: List[dict], title: str, threshold: float = 0.75) -> dict | None:
    for t in existing_tasks:
        if _title_similarity(t.get("title") or "", title) >= threshold:
            return t
    return None


def _parse_extracted_json(text: str) -> Dict[str, List[dict]]:
    text = (text or "").strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    data = json.loads(text)
    result = {k: [] for k in STATUS_KEYS}
    for k in STATUS_KEYS:
        val = data.get(k)
        if isinstance(val, list):
            result[k] = [x for x in val if isinstance(x, dict) and x.get("title")]
    return result


async def _get_project_transcript(project_id: str) -> str:
    db = await get_database()
    meetings = await db.meetings.find({"project_id": project_id}).to_list(length=500)
    if not meetings:
        return ""
    meeting_ids = [str(m["_id"]) for m in meetings]
    segments = await db.transcript_segments.find(
        {"meeting_id": {"$in": meeting_ids}}
    ).sort("timestamp", 1).to_list(length=50000)
    parts = [s.get("text") or "" for s in segments]
    return "\n".join(parts).strip()


async def sync_tasks_to_kairox(project_id: str) -> None:
    """
    Load all meeting transcripts for the project, extract tasks via Groq LLM,
    then create or update tasks in DB (fuzzy match on title).
    """
    db = await get_database()
    transcript = await _get_project_transcript(project_id)
    if not transcript or len(transcript.strip()) < 50:
        logger.info("No transcript text for project %s; skipping extract", project_id)
        return

    try:
        client = _get_client()
    except ValueError as e:
        logger.warning("Task extractor skipped: %s", e)
        return

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": EXTRACT_PROMPT},
            {"role": "user", "content": f"Transcript:\n\n{transcript[:120000]}"},
        ],
        temperature=0.2,
    )
    text = response.choices[0].message.content or "{}"
    try:
        extracted = _parse_extracted_json(text)
    except json.JSONDecodeError as e:
        logger.exception("Groq returned invalid JSON for task extract: %s", e)
        return

    existing = await db.tasks.find({"project_id": project_id}).to_list(length=2000)
    now = datetime.utcnow()

    for status in STATUS_KEYS:
        for item in extracted.get(status) or []:
            title = (item.get("title") or "").strip()
            if not title:
                continue
            description = item.get("description") or ""
            owner = item.get("owner") or ""
            deadline_str = item.get("deadline")
            subtasks = item.get("subtasks")
            if isinstance(subtasks, list):
                subtasks = [str(s) for s in subtasks]
            else:
                subtasks = None

            due_date = None
            if deadline_str and isinstance(deadline_str, str):
                try:
                    from datetime import datetime as dt
                    due_date = dt.fromisoformat(deadline_str.replace("Z", "+00:00"))
                except Exception:
                    pass

            similar = _find_similar_task(existing, title)
            if similar:
                # Update existing task (merge fields, set status)
                update = {
                    "status": status,
                    "updated_at": now,
                    "description": description or similar.get("description"),
                    "subtasks": subtasks if subtasks is not None else similar.get("subtasks"),
                }
                if due_date:
                    update["due_date"] = due_date
                if owner and not similar.get("assignee_id"):
                    update["assignee_id"] = owner  # store as string; could resolve to user id later
                await db.tasks.update_one(
                    {"_id": similar["_id"]},
                    {"$set": update},
                )
                logger.debug("Updated task %s -> %s", similar.get("title"), status)
            else:
                # Create new task
                doc = {
                    "project_id": project_id,
                    "title": title,
                    "description": description or None,
                    "status": status,
                    "priority": "medium",
                    "assignee_id": owner or None,
                    "due_date": due_date,
                    "subtasks": subtasks,
                    "source_meeting_id": None,
                    "is_auto_generated": True,
                    "created_at": now,
                    "updated_at": now,
                }
                result = await db.tasks.insert_one(doc)
                existing.append({**doc, "_id": result.inserted_id})
                logger.debug("Created task %s -> %s", title, status)
