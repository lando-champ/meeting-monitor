"""
Phase 6: MCP-style external tool layer (single module).
Tools are invoked only via execution_node `tool_call` actions — not from agents directly.
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict

import httpx

from app.core.config import settings
from app.consilium.agents.mcp_tools import MCPToolExecutor

logger = logging.getLogger(__name__)
_mcp_executor = MCPToolExecutor()


def log_tool_event(
    workspace_id: str,
    tool: str,
    operation: str,
    status: str,
    *,
    action_id: str = "",
    error: str = "",
) -> None:
    payload: Dict[str, Any] = {
        "event": "tool_call",
        "workspace_id": workspace_id,
        "tool": tool,
        "operation": operation,
        "status": status,
    }
    if action_id:
        payload["action_id"] = action_id[:24]
    if error:
        payload["error"] = error[:200]
    logger.info(json.dumps(payload, default=str))


class Tool(ABC):
    """Standard tool contract (MCP-style single entrypoint)."""

    name: ClassVar[str] = "abstract"

    @abstractmethod
    def execute(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        action: {type, tool, operation, params, action_id?, ...}
        context: {workspace_id, github_repo, ...}
        Returns: {ok, status, data?, error?}
        """


class SlackTool(Tool):
    name = "slack"

    def execute(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        op = str(action.get("operation") or "")
        params = action.get("params") if isinstance(action.get("params"), dict) else {}
        token = settings.SLACK_BOT_TOKEN or ""
        if not token:
            return {"ok": False, "status": "skipped", "error": "slack_not_configured"}

        channel = str(params.get("channel") or settings.SLACK_DEFAULT_CHANNEL or "")
        text = str(params.get("message") or params.get("text") or "")
        if op == "send_alert":
            text = f"[Consilium Alert] {text}"
        elif op not in ("send_message", "send_alert"):
            return {"ok": False, "status": "error", "error": f"unknown_slack_operation:{op}"}

        if not channel or not text.strip():
            return {"ok": False, "status": "error", "error": "missing_channel_or_message"}

        try:
            r = httpx.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
                json={"channel": channel, "text": text},
                timeout=20.0,
            )
            data = r.json() if r.content else {}
            if r.is_success and data.get("ok"):
                return {"ok": True, "status": "success", "data": {"ts": data.get("ts"), "channel": data.get("channel")}}
            return {"ok": False, "status": "error", "error": str(data.get("error") or r.text)[:300]}
        except Exception as exc:
            return {"ok": False, "status": "error", "error": type(exc).__name__}


class GitHubTool(Tool):
    name = "github"

    def execute(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        op = str(action.get("operation") or "")
        params = action.get("params") if isinstance(action.get("params"), dict) else {}
        gh = context.get("github_repo") or {}
        token = str(gh.get("access_token") or "")
        owner = str(gh.get("repo_owner") or "")
        repo = str(gh.get("repo_name") or "")
        if not token or not owner or not repo:
            return {"ok": False, "status": "skipped", "error": "github_repo_not_linked"}

        base = f"https://api.github.com/repos/{owner}/{repo}"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        try:
            if op == "create_issue":
                title = str(params.get("title") or "Consilium task")
                body = str(params.get("body") or "")
                r = httpx.post(f"{base}/issues", headers=headers, json={"title": title, "body": body}, timeout=25.0)
                if r.is_success:
                    j = r.json()
                    return {
                        "ok": True,
                        "status": "success",
                        "data": {"html_url": j.get("html_url"), "number": j.get("number"), "id": j.get("id")},
                    }
                return {"ok": False, "status": "error", "error": r.text[:300]}
            if op == "comment_on_pr":
                pr_number = params.get("pr_number") or params.get("number")
                body = str(params.get("body") or params.get("comment") or "")
                if pr_number is None or not body.strip():
                    return {"ok": False, "status": "error", "error": "missing_pr_number_or_body"}
                r = httpx.post(
                    f"{base}/issues/{int(pr_number)}/comments",
                    headers=headers,
                    json={"body": body},
                    timeout=25.0,
                )
                if r.is_success:
                    j = r.json()
                    return {"ok": True, "status": "success", "data": {"html_url": j.get("html_url"), "id": j.get("id")}}
                return {"ok": False, "status": "error", "error": r.text[:300]}
            return {"ok": False, "status": "error", "error": f"unknown_github_operation:{op}"}
        except Exception as exc:
            return {"ok": False, "status": "error", "error": type(exc).__name__}


class NotionTool(Tool):
    name = "notion"

    def execute(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        op = str(action.get("operation") or "")
        params = action.get("params") if isinstance(action.get("params"), dict) else {}
        token = settings.NOTION_INTEGRATION_TOKEN or ""
        if not token:
            return {"ok": False, "status": "skipped", "error": "notion_not_configured"}

        version = settings.NOTION_API_VERSION
        headers = {"Authorization": f"Bearer {token}", "Notion-Version": version, "Content-Type": "application/json"}
        default_parent = str(settings.NOTION_DEFAULT_PARENT_ID or "")

        def _nid(raw: str) -> str:
            return (raw or "").strip()

        try:
            if op in ("create_page", "create_document"):
                title = str(params.get("title") or "Consilium document")
                body = str(params.get("body") or params.get("content") or "")
                parent = _nid(str(params.get("parent_page_id") or default_parent))
                if not parent:
                    return {"ok": False, "status": "error", "error": "missing_notion_parent_id"}
                children = [
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {"rich_text": [{"type": "text", "text": {"content": title[:2000]}}]},
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {"rich_text": [{"type": "text", "text": {"content": body[:1800]}}]},
                    },
                ]
                r = httpx.patch(
                    f"https://api.notion.com/v1/blocks/{parent}/children",
                    headers=headers,
                    json={"children": children},
                    timeout=25.0,
                )
                if r.is_success:
                    return {"ok": True, "status": "success", "data": {"parent_page_id": parent, "appended_blocks": True}}
                return {"ok": False, "status": "error", "error": r.text[:300]}
            if op in ("update_page", "update_document"):
                page_id = _nid(str(params.get("page_id") or default_parent))
                body = str(params.get("body") or params.get("content") or "")
                if not page_id:
                    return {"ok": False, "status": "error", "error": "missing_page_id"}
                patch = {
                    "children": [
                        {
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {"rich_text": [{"type": "text", "text": {"content": body[:1800]}}]},
                        }
                    ]
                }
                r = httpx.patch(f"https://api.notion.com/v1/blocks/{page_id}/children", headers=headers, json=patch, timeout=25.0)
                if r.is_success:
                    return {"ok": True, "status": "success", "data": {"page_id": page_id}}
                return {"ok": False, "status": "error", "error": r.text[:300]}
            return {"ok": False, "status": "error", "error": f"unknown_notion_operation:{op}"}
        except Exception as exc:
            return {"ok": False, "status": "error", "error": type(exc).__name__}


class CalendarTool(Tool):
    name = "calendar"

    def execute(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        op = str(action.get("operation") or "")
        params = action.get("params") if isinstance(action.get("params"), dict) else {}
        if op != "create_event":
            return {"ok": False, "status": "error", "error": f"unknown_calendar_operation:{op}"}

        summary = str(params.get("title") or params.get("summary") or "Consilium event")
        start = str(params.get("start") or params.get("start_time") or "")
        end = str(params.get("end") or params.get("end_time") or start)
        token = settings.GOOGLE_CALENDAR_ACCESS_TOKEN or ""
        cal_id = settings.GOOGLE_CALENDAR_ID or "primary"

        webhook = settings.CALENDAR_EVENTS_WEBHOOK_URL or ""
        if webhook:
            try:
                r = httpx.post(
                    webhook,
                    json={"summary": summary, "start": start, "end": end, "workspace_id": context.get("workspace_id")},
                    timeout=15.0,
                )
                if r.is_success:
                    return {"ok": True, "status": "success", "data": {"via": "webhook", "status_code": r.status_code}}
                return {"ok": False, "status": "error", "error": r.text[:200]}
            except Exception as exc:
                return {"ok": False, "status": "error", "error": type(exc).__name__}

        if not token or not start:
            return {"ok": False, "status": "skipped", "error": "calendar_not_configured"}

        try:
            event_body = {"summary": summary, "start": {"dateTime": start}, "end": {"dateTime": end}}
            r = httpx.post(
                f"https://www.googleapis.com/calendar/v3/calendars/{cal_id}/events",
                headers={"Authorization": f"Bearer {token}"},
                json=event_body,
                timeout=25.0,
            )
            if r.is_success:
                j = r.json()
                return {"ok": True, "status": "success", "data": {"htmlLink": j.get("htmlLink"), "id": j.get("id")}}
            return {"ok": False, "status": "error", "error": r.text[:300]}
        except Exception as exc:
            return {"ok": False, "status": "error", "error": type(exc).__name__}


TOOLS: Dict[str, Tool] = {
    "slack": SlackTool(),
    "github": GitHubTool(),
    "notion": NotionTool(),
    "calendar": CalendarTool(),
}


def execute_tool_action(action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatch tool_call action with permission check.
    context must include workspace_id, github_repo; optional allowed_tools (list[str]).
    """
    tool_name = str(action.get("tool") or "").lower().strip()
    operation = str(action.get("operation") or "")
    workspace_id = str(context.get("workspace_id") or "")

    if tool_name.startswith("mcp/"):
        return _mcp_executor.run(action, context)

    if tool_name not in TOOLS:
        log_tool_event(workspace_id, tool_name or "?", operation, "error", error="unknown_tool")
        return {"ok": False, "status": "error", "error": "unknown_tool"}

    allowed = context.get("allowed_tools")
    if allowed is not None:
        allowed_set = {str(x).lower() for x in allowed if x}
        if len(allowed_set) == 0:
            log_tool_event(workspace_id, tool_name, operation, "forbidden", error="no_tools_allowed")
            return {"ok": False, "status": "forbidden", "error": "no_tools_allowed"}
        if tool_name not in allowed_set:
            log_tool_event(workspace_id, tool_name, operation, "forbidden", error="tool_not_permitted")
            return {"ok": False, "status": "forbidden", "error": "tool_not_permitted"}

    result = TOOLS[tool_name].execute(action, context)
    st = str(result.get("status") or ("success" if result.get("ok") else "error"))
    log_tool_event(
        workspace_id,
        tool_name,
        operation,
        st,
        action_id=str(action.get("action_id") or ""),
        error=str(result.get("error") or ""),
    )
    return result
