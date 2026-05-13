"""
ai_task_mapper.py

Replaces keyword-based task matching with a provider-agnostic semantic layer.

Two responsibilities:
  1. map_commit_to_task_ai()  - find the most relevant task for a GitHub event
  2. infer_task_status_ai()   - decide the correct kanban status given an event

Supported providers (auto-detected by available API key):
  - OpenRouter  (OPENROUTER_API_KEY)
  - Gemini      (GEMINI_API_KEY)
  - Groq        (GROQ_API_KEY)

Both functions fall back to deterministic logic when API calls are unavailable
or return unusable responses.
"""
from __future__ import annotations
 
import json
import logging
import os
import re
import urllib.request
import urllib.error
from typing import Any, Dict, List

from app.consilium.services.kanban_service import task_identity as _task_identity
 
_log = logging.getLogger(__name__)

_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_MAX_TOKENS = 512
_TIMEOUT_SECONDS = 12
_STOPWORDS = {
    "a",
    "an",
    "and",
    "the",
    "to",
    "for",
    "of",
    "in",
    "on",
    "with",
    "by",
    "at",
    "from",
    "into",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "this",
    "that",
    "it",
}
 
# ──────────────────────────────────────────────────────────────────
# Internal HTTP helper (no extra deps beyond stdlib)
# ──────────────────────────────────────────────────────────────────
 
def _provider() -> str:
    explicit = str(os.environ.get("LLM_PROVIDER") or "").strip().lower()
    if explicit in {"openrouter", "gemini", "groq"}:
        return explicit
    if os.environ.get("OPENROUTER_API_KEY"):
        return "openrouter"
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    if os.environ.get("GROQ_API_KEY"):
        return "groq"
    raise EnvironmentError("No LLM key set. Use OPENROUTER_API_KEY, GEMINI_API_KEY, or GROQ_API_KEY")


def _json_post(url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read())


def _call_openrouter(system: str, user: str) -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise EnvironmentError("OPENROUTER_API_KEY not set")
    model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    body = _json_post(
        _OPENROUTER_URL,
        {
            "model": model,
            "max_tokens": _MAX_TOKENS,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )
    choices = body.get("choices") or []
    content = (((choices[0] if choices else {}).get("message") or {}).get("content") or "").strip()
    if not content:
        raise ValueError("No text from OpenRouter response")
    return content


def _call_groq(system: str, user: str) -> str:
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        raise EnvironmentError("GROQ_API_KEY not set")
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    body = _json_post(
        _GROQ_URL,
        {
            "model": model,
            "max_tokens": _MAX_TOKENS,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )
    choices = body.get("choices") or []
    content = (((choices[0] if choices else {}).get("message") or {}).get("content") or "").strip()
    if not content:
        raise ValueError("No text from Groq response")
    return content


def _call_gemini(system: str, user: str) -> str:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise EnvironmentError("GEMINI_API_KEY not set")
    model = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body = _json_post(
        url,
        {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": _MAX_TOKENS},
        },
        {"Content-Type": "application/json"},
    )
    candidates = body.get("candidates") or []
    parts = (((candidates[0] if candidates else {}).get("content") or {}).get("parts") or [])
    text = "".join(str(p.get("text") or "") for p in parts).strip()
    if not text:
        raise ValueError("No text from Gemini response")
    return text


def _call_llm(system: str, user: str) -> str:
    provider = _provider()
    if provider == "openrouter":
        return _call_openrouter(system, user)
    if provider == "gemini":
        return _call_gemini(system, user)
    if provider == "groq":
        return _call_groq(system, user)
    raise ValueError(f"Unsupported provider: {provider}")
 
 
# ──────────────────────────────────────────────────────────────────
# 1. Semantic task matching
# ──────────────────────────────────────────────────────────────────
 
_MATCH_SYSTEM = """\
You are a project management assistant. Given a list of kanban tasks and a
GitHub event (commit or PR), identify which task this event most likely
belongs to.
 
Rules:
- Match on semantic similarity, not just exact string overlap.
- A commit "feat: complete face-recognition attendance UI" maps to a task
  titled "Build AI-based Face Recognition Attendance System UI components".
- If no task is a reasonable match, return null.
- Reply ONLY with a JSON object: {"task_id": "<id>" | null, "confidence": 0..1}
- Do not include any explanation outside the JSON.
"""
 
 
def map_commit_to_task_ai(
    event: Dict[str, Any],
    tasks: List[Dict[str, Any]],
) -> str | None:
    """
    Semantic version of map_commit_to_task().
    Falls back to keyword matching if semantic provider is unavailable.
    """
    if not tasks:
        return None
 
    message = (event.get("message") or event.get("title") or "").strip()
    if not message:
        return _keyword_fallback(event, tasks)
 
    heuristic_match = _semantic_fallback(event, tasks)
    if heuristic_match:
        return heuristic_match

    task_summaries = []
    for t in tasks:
        tid = _task_identity(t)
        if not tid:
            continue
        task_summaries.append(
            {
                "id": tid,
                "title": t.get("title") or "",
                "status": t.get("status") or "todo",
            }
        )
 
    user_prompt = json.dumps(
        {
            "event": {
                "type": event.get("type"),
                "message": message,
                "user": event.get("user"),
                "pr_number": event.get("number"),
            },
            "tasks": task_summaries,
        },
        ensure_ascii=False,
    )
 
    try:
        raw = _call_llm(_MATCH_SYSTEM, user_prompt)
        # Extract the first JSON object from the response
        m = re.search(r"\{.*?\}", raw, re.DOTALL)
        if not m:
            raise ValueError("No JSON in response")
        parsed = json.loads(m.group())
        task_id = parsed.get("task_id")
        confidence = float(parsed.get("confidence") or 0.0)
        if task_id and confidence >= 0.35:
            known_ids = {_task_identity(t) for t in tasks if _task_identity(t)}
            if task_id in known_ids:
                _log.debug("ai_match task_id=%s confidence=%.2f", task_id, confidence)
                return task_id
        return _semantic_fallback(event, tasks)
    except Exception as exc:
        _log.warning("map_commit_to_task_ai fallback: %s", exc)
        return _semantic_fallback(event, tasks)
 
 
def _keyword_fallback(event: Dict[str, Any], tasks: List[Dict[str, Any]]) -> str | None:
    """Original deterministic logic, kept as the safe fallback."""
    message = (event.get("message") or event.get("title") or "").lower()
    pr_number = event.get("number")
    for task in tasks:
        task_id = _task_identity(task)
        title = (task.get("title") or "").lower()
        if task_id and task_id.lower() in message:
            return task_id
        if title and len(title) > 8 and title[:24] in message:
            return task_id
        if pr_number is not None and str(task.get("github_pr") or "") == str(pr_number):
            return task_id
    return None


def _event_text(event: Dict[str, Any]) -> str:
    parts = [
        str(event.get("message") or ""),
        str(event.get("title") or ""),
        str(event.get("body") or ""),
        str(event.get("description") or ""),
        str(event.get("commit_message") or ""),
        str(event.get("head_commit_message") or ""),
        str(event.get("ref") or ""),
    ]
    return " ".join(p for p in parts if p).strip()


def _normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokenize(text: str) -> List[str]:
    norm = _normalize_text(text)
    if not norm:
        return []
    return [tok for tok in norm.split(" ") if tok and tok not in _STOPWORDS]


def _token_overlap_score(a_tokens: List[str], b_tokens: List[str]) -> float:
    if not a_tokens or not b_tokens:
        return 0.0
    a_set = set(a_tokens)
    b_set = set(b_tokens)
    inter = len(a_set & b_set)
    if inter == 0:
        return 0.0
    union = len(a_set | b_set)
    coverage = inter / max(1, len(b_set))
    jaccard = inter / max(1, union)
    return max(jaccard, coverage * 0.9)


def _semantic_fallback(event: Dict[str, Any], tasks: List[Dict[str, Any]]) -> str | None:
    """
    Deterministic semantic-ish mapper for offline reliability.
    """
    message = _event_text(event)
    if not message:
        return _keyword_fallback(event, tasks)

    message_norm = _normalize_text(message)
    message_tokens = _tokenize(message)
    if not message_tokens:
        return _keyword_fallback(event, tasks)

    best_task_id: str | None = None
    best_score = 0.0

    for task in tasks:
        task_id = _task_identity(task)
        title = str(task.get("title") or "")
        if not task_id or not title:
            continue

        title_norm = _normalize_text(title)
        title_tokens = _tokenize(title)
        if not title_tokens:
            continue

        score = _token_overlap_score(message_tokens, title_tokens)

        if title_norm and title_norm in message_norm:
            score = max(score, 0.98)
        elif len(title_norm) >= 22 and title_norm[:22] in message_norm:
            score = max(score, 0.85)

        if task_id.lower() in message_norm:
            score = max(score, 0.99)

        if score > best_score:
            best_score = score
            best_task_id = task_id

    if best_task_id and best_score >= 0.45:
        return best_task_id
    return _keyword_fallback(event, tasks)
 
 
# ──────────────────────────────────────────────────────────────────
# 2. Semantic status inference
# ──────────────────────────────────────────────────────────────────
 
_STATUS_SYSTEM = """\
You are a project management assistant. Given a kanban task and a GitHub
event (commit or PR), decide what kanban status the task should move to.
 
Valid statuses: todo | in_progress | blocked | done
 
Rules:
- A commit or open PR that references work on the task → in_progress
- A merged PR → done
- A closed-without-merge PR, or a commit/PR indicating an error, failure,
  or dependency blocker → blocked
- Purely administrative commits (chore, docs, style) with no clear relation
  to the task's goal → in_progress (assume work is ongoing)
- If the event clearly indicates the work is complete ("done", "complete",
  "finished", "closes #N", "fix: <task title>") → done
 
Reply ONLY with a JSON object:
{"status": "<status>", "confidence": 0..1, "reason": "<one short sentence>"}
Do not include any explanation outside the JSON.
"""
 
 
def infer_task_status_ai(
    event: Dict[str, Any],
    task: Dict[str, Any],
) -> str:
    """
    Semantic replacement for the inline status-inference block in monitoring_node().
    Falls back to keyword heuristics if provider is unavailable.
    """
    message = (event.get("message") or event.get("title") or "").strip()
    event_type = event.get("type", "commit")
    merged = bool(event.get("merged"))
 
    # Short-circuit: merged PR is always done regardless of message
    if event_type == "pull_request" and merged:
        return "done"
 
    user_prompt = json.dumps(
        {
            "event": {
                "type": event_type,
                "message": message,
                "merged": merged,
                "pr_state": event.get("state"),
            },
            "task": {
                "id": str(task.get("id") or ""),
                "title": task.get("title") or "",
                "current_status": task.get("status") or "todo",
                "description": (task.get("description") or "")[:300],
            },
        },
        ensure_ascii=False,
    )
 
    try:
        raw = _call_llm(_STATUS_SYSTEM, user_prompt)
        m = re.search(r"\{.*?\}", raw, re.DOTALL)
        if not m:
            raise ValueError("No JSON in response")
        parsed = json.loads(m.group())
        status = parsed.get("status", "in_progress")
        confidence = float(parsed.get("confidence") or 0.0)
        valid = {"todo", "in_progress", "blocked", "done"}
        if status in valid and confidence >= 0.40:
            _log.debug(
                "ai_status task=%s status=%s confidence=%.2f reason=%s",
                task.get("id"),
                status,
                confidence,
                parsed.get("reason"),
            )
            return status
        # Low confidence → fall back
        return _status_keyword_fallback(event, task)
    except Exception as exc:
        _log.warning("infer_task_status_ai fallback: %s", exc)
        return _status_keyword_fallback(event, task)
 
 
def _status_keyword_fallback(event: Dict[str, Any], task: Dict[str, Any]) -> str:
    """Original keyword heuristics preserved as the safe fallback."""
    message = (event.get("message") or event.get("title") or "").lower()
    if event.get("type") == "pull_request" and event.get("merged"):
        return "done"
    if event.get("type") == "pull_request" and (event.get("state") or "").lower() == "closed":
        return "blocked"
    if any(kw in message for kw in ("fix", "done", "complete", "closes", "resolved")):
        return "done"
    if any(kw in message for kw in ("wip", "progress", "start", "begin", "implement")):
        return "in_progress"
    if any(kw in message for kw in ("error", "fail", "blocked", "broken", "revert")):
        return "blocked"
    return "in_progress"