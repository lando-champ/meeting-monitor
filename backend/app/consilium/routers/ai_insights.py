"""AI project insights: Gemini-powered Q&A over workspace data."""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.config import settings
from app.consilium.database import get_db
from app.consilium.dependencies import ensure_workspace_member, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai"])

# Supported Gemini models (stable). Primary first, then fallbacks.
# See https://ai.google.dev/gemini-api/docs/models
GEMINI_MODELS = [
    "gemini-2.5-flash",       # Best price-performance, low latency
    "gemini-2.5-pro",         # More capable, complex reasoning
    "gemini-2.5-flash-lite",  # Fastest, budget-friendly
]

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
REQUEST_TIMEOUT = 60.0


class ProjectInsightsRequest(BaseModel):
    workspace_id: str = Field(..., alias="workspaceId")
    question: str


class ProjectInsightsResponse(BaseModel):
    answer: str


def _build_workspace_context(workspace: dict, tasks: list[dict]) -> str:
    """Build a text summary of workspace and tasks for the LLM."""
    parts = []

    parts.append("## Workspace")
    parts.append(f"Name: {workspace.get('name', 'N/A')}")
    if workspace.get("description"):
        parts.append(f"Description: {workspace.get('description')}")
    if workspace.get("tech_stack"):
        parts.append(f"Tech stack: {workspace.get('tech_stack')}")
    if workspace.get("status"):
        parts.append(f"Status: {workspace.get('status')}")

    members = workspace.get("members") or []
    if members:
        parts.append("\n## Team members")
        for m in members:
            name = m.get("name") or "Unnamed"
            role = m.get("role", "")
            skills = m.get("skills") or []
            parts.append(
                f"- {name} (role: {role}, skills: {', '.join(skills) if skills else 'none'})"
            )

    if tasks:
        parts.append("\n## Tasks")
        by_status: dict[str, list[dict]] = {}
        for t in tasks:
            s = t.get("status") or "todo"
            by_status.setdefault(s, []).append(t)
        for status, items in by_status.items():
            parts.append(f"\n### {status} ({len(items)} tasks)")
            for t in items[:20]:
                title = t.get("title") or "No title"
                assignee = t.get("assignee_name") or "Unassigned"
                due = t.get("due_date")
                due_str = str(due)[:10] if due else "No due date"
                blocker = t.get("blocker_reason")
                line = f"- {title} | Assignee: {assignee} | Due: {due_str}"
                if blocker:
                    line += f" | Blocker: {blocker}"
                parts.append(line)

    return "\n".join(parts)


def _build_prompt(context: str, question: str) -> str:
    return (
        "You are a project insight assistant. Use ONLY the following workspace and task data to answer the user's question. "
        "Be concise and factual. If the data does not contain enough information, say so.\n\n"
        "--- WORKSPACE AND TASK DATA ---\n"
        f"{context}\n"
        "--- END DATA ---\n\n"
        f"User question: {question}"
    )


def _parse_error_response(resp: httpx.Response) -> str:
    """Extract user-friendly error message from Gemini error response."""
    try:
        data = resp.json()
        err = data.get("error", {})
        msg = err.get("message", resp.text)
        code = err.get("code", 0)
        status = err.get("status", "")
        if "not found" in msg.lower() or "not supported" in msg.lower():
            return f"Model unavailable: {msg}"
        if code == 429 or status == "RESOURCE_EXHAUSTED":
            return "Rate limit exceeded. Please try again in a moment."
        if code >= 500 or "INTERNAL" in status:
            return "Gemini service is temporarily unavailable. Please try again."
        return msg or resp.text
    except Exception:
        return resp.text or "Unknown error"


def _parse_success_response(data: dict) -> tuple[str | None, str | None]:
    """
    Parse Gemini generateContent success response.
    Returns (answer_text, error_message). One will be None.
    """
    candidates = data.get("candidates") or []
    if not candidates:
        # No candidates: may be blocked by safety or empty
        prompt_feedback = data.get("promptFeedback", {})
        block_reason = prompt_feedback.get("blockReason") or "No candidates returned."
        return None, f"Response blocked or empty: {block_reason}"

    first = candidates[0]
    finish = first.get("finishReason", "")
    if finish and finish.upper() != "STOP":
        # SAFETY, RECITATION, etc.
        return None, f"Response ended: {finish}"

    content = first.get("content", {})
    parts = content.get("parts") or []
    if not parts:
        return None, "No text in response."

    text = parts[0].get("text", "").strip()
    if not text:
        return None, "Empty response text."
    return text, None


async def _call_gemini_single(
    client: httpx.AsyncClient,
    model: str,
    prompt: str,
    api_key: str,
) -> tuple[str | None, str | None]:
    """
    Call one Gemini model. Returns (answer, error). One will be None.
    """
    url = f"{GEMINI_BASE_URL}/{model}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2048,
        },
    }

    try:
        resp = await client.post(
            f"{url}?key={api_key}",
            headers={"Content-Type": "application/json"},
            json=payload,
        )
    except httpx.TimeoutException:
        return None, "Request timed out. Please try again."
    except httpx.RequestError as e:
        logger.warning("Gemini request failed for model=%s: %s", model, e)
        return None, f"Network error: {e!s}"

    if resp.status_code != 200:
        err_msg = _parse_error_response(resp)
        logger.warning(
            "Gemini API error model=%s status=%s: %s",
            model,
            resp.status_code,
            err_msg,
        )
        return None, err_msg

    try:
        data = resp.json()
    except json.JSONDecodeError as e:
        return None, f"Invalid response: {e!s}"

    return _parse_success_response(data)


async def _call_gemini(context: str, question: str) -> str:
    """
    Call Gemini API with primary model and fallbacks.
    All API key and model logic is server-side; key is never exposed.
    """
    api_key = getattr(settings, "GEMINI_API_KEY", None) or ""
    if not api_key:
        return (
            "Project insights are not available: GEMINI_API_KEY is not configured. "
            "Add GEMINI_API_KEY to your backend environment variables."
        )

    prompt = _build_prompt(context, question)
    last_error: str = "No response from any model."

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        for model in GEMINI_MODELS:
            answer, error = await _call_gemini_single(client, model, prompt, api_key)
            if answer:
                if model != GEMINI_MODELS[0]:
                    logger.info("Used fallback model: %s", model)
                return answer
            if error:
                last_error = error
                logger.debug("Model %s failed: %s", model, error)

    return f"Unable to get AI insight: {last_error}"


@router.post("/project-insights", response_model=ProjectInsightsResponse)
async def project_insights(
    body: ProjectInsightsRequest,
    current_user=Depends(get_current_user),
):
    """Fetch workspace data, send context + question to Gemini, return AI-generated insight."""
    ws = await ensure_workspace_member(body.workspace_id, current_user)

    db = await get_db()
    tasks_cursor = db["tasks"].find({"workspace_id": body.workspace_id})
    tasks = await tasks_cursor.to_list(length=500)

    context = _build_workspace_context(ws, tasks)
    answer = await _call_gemini(context, body.question)
    return ProjectInsightsResponse(answer=answer)
