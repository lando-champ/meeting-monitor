"""
mcp_tools.py

MCP (Model Context Protocol) server layer for the monitoring agent.

Exposes tools that execution_node() can invoke via the existing
"tool_call" pending_action type. Each tool maps to a named MCP
server and is discoverable at runtime through the registry.

Architecture
────────────
  execution_node
      │  pending_action: {type:"tool_call", tool:"mcp/<server>", operation:"<op>", params:{...}}
      ▼
  execute_tool_action()  ← already in tool_registry.py, routes by tool name
      │
      ▼
  MCPToolExecutor.run()  ← this file
      │
      ├─► GitHub MCP      (create/update issues, link PRs)
      ├─► Kanban MCP      (move cards, add comments)
      ├─► Notification MCP (send alerts, Slack/email)
      └─► Calendar MCP    (schedule reviews when risk is high)

Usage
─────
Wire in tool_registry.py:

    from .mcp_tools import MCPToolExecutor
    _mcp = MCPToolExecutor()

    def execute_tool_action(action, ctx):
        tool = action.get("tool", "")
        if tool.startswith("mcp/"):
            return _mcp.run(action, ctx)
        ...existing routing...
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

_log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────
# MCP server registry
# Add / override entries via the MCP_SERVERS environment variable
# (JSON dict of {name: url}) or by calling register_server().
# ──────────────────────────────────────────────────────────────────

_DEFAULT_SERVERS: Dict[str, str] = {
    # GitHub MCP – create / update issues, comment on PRs
    "github":       "https://github.mcp.claude.com/mcp",
    # Kanban MCP – move cards across columns (Linear, Jira, Trello …)
    "kanban":       "https://kanban.mcp.example.com/mcp",   # replace with your instance
    # Notification MCP – Slack / e-mail alerts
    "notification": "https://notify.mcp.example.com/mcp",
    # Calendar MCP – schedule risk-review meetings
    "calendar":     "https://gcal.mcp.claude.com/mcp",
}


class MCPClient:
    """
    Minimal synchronous MCP client over HTTP/SSE.

    MCP messages use JSON-RPC 2.0.  We send a single `tools/call`
    request and wait for the result (non-streaming path).
    """

    TIMEOUT = 20  # seconds

    def __init__(self, server_url: str, api_key: str = "") -> None:
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    def _rpc(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        payload = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        ).encode()
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept":       "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(
            f"{self.server_url}/rpc",
            data=payload,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.TIMEOUT) as resp:
                body = json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"MCP HTTP {exc.code}: {exc.read()[:200]}") from exc
        except Exception as exc:
            raise RuntimeError(f"MCP network error: {exc}") from exc

        if "error" in body:
            err = body["error"]
            raise RuntimeError(f"MCP RPC error {err.get('code')}: {err.get('message')}")
        return body.get("result", {})

    def list_tools(self) -> List[Dict[str, Any]]:
        result = self._rpc("tools/list", {})
        return result.get("tools", [])

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self._rpc("tools/call", {"name": tool_name, "arguments": arguments})


def _encode_mcp_message(payload: Dict[str, Any]) -> bytes:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body


def _read_one_mcp_message(stream) -> Dict[str, Any]:
    """Read a single MCP message (Content-Length framed) from a binary stream."""
    headers: List[bytes] = []
    while True:
        line = stream.readline()
        if not line:
            raise RuntimeError("MCP stdio: unexpected EOF reading headers")
        if line in (b"\r\n", b"\n"):
            break
        headers.append(line)
    hdr = b"".join(headers).decode("latin-1", errors="replace")
    length = None
    for hline in hdr.split("\r\n"):
        if hline.lower().startswith("content-length:"):
            try:
                length = int(hline.split(":", 1)[1].strip())
            except ValueError:
                length = None
            break
    if length is None or length < 0:
        raise RuntimeError(f"MCP stdio: missing Content-Length in {hdr!r}")
    body = stream.read(length)
    if len(body) != length:
        raise RuntimeError("MCP stdio: short read on message body")
    return json.loads(body.decode("utf-8"))


def _read_until_jsonrpc_id(stream, expect_id: int, max_messages: int = 32) -> Dict[str, Any]:
    for _ in range(max_messages):
        msg = _read_one_mcp_message(stream)
        if msg.get("id") == expect_id:
            return msg
    raise RuntimeError(f"MCP stdio: no response with id={expect_id}")


def mcp_stdio_call_tool(
    argv: List[str],
    tool_name: str,
    arguments: Dict[str, Any],
    *,
    timeout: float = 45.0,
) -> Dict[str, Any]:
    """
    Minimal MCP session over stdio: initialize → notifications/initialized → tools/call.
    `argv` is the server command (e.g. from MCP_GITHUB_COMMAND JSON list).
    """
    if not argv:
        raise RuntimeError("empty MCP stdio argv")
    proc = subprocess.Popen(
        argv,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )
    assert proc.stdin and proc.stdout
    try:
        mid = 1
        init = {
            "jsonrpc": "2.0",
            "id": mid,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "meeting-monitor", "version": "1.0.0"},
            },
        }
        proc.stdin.write(_encode_mcp_message(init))
        proc.stdin.flush()
        init_resp = _read_until_jsonrpc_id(proc.stdout, mid)
        if isinstance(init_resp, dict) and init_resp.get("error"):
            raise RuntimeError(f"MCP initialize error: {init_resp.get('error')}")
        mid += 1
        note = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
        proc.stdin.write(_encode_mcp_message(note))
        proc.stdin.flush()
        call = {
            "jsonrpc": "2.0",
            "id": mid,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        proc.stdin.write(_encode_mcp_message(call))
        proc.stdin.flush()
        resp = _read_until_jsonrpc_id(proc.stdout, mid)
        if isinstance(resp, dict) and resp.get("error"):
            err = resp["error"]
            raise RuntimeError(f"MCP tools/call error: {err}")
        return resp.get("result") or {}
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass
        try:
            proc.terminate()
            proc.wait(timeout=min(timeout, 5.0))
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def _stdio_argv_for_server(server_name: str) -> List[str]:
    """JSON list in MCP_GITHUB_COMMAND / MCP_SEARCH_COMMAND (settings or env)."""
    try:
        from app.core.config import settings
    except Exception:
        settings = None  # type: ignore[assignment]

    def _raw(env_name: str, setting_attr: str) -> str:
        v = os.environ.get(env_name, "")
        if v.strip():
            return v
        if settings is not None:
            return str(getattr(settings, setting_attr, "") or "")
        return ""

    raw = ""
    sn = server_name.lower()
    if sn == "github":
        raw = _raw("MCP_GITHUB_COMMAND", "MCP_GITHUB_COMMAND")
    elif sn in ("search", "ddg", "duckduckgo"):
        raw = _raw("MCP_SEARCH_COMMAND", "MCP_SEARCH_COMMAND")
    raw = (raw or "").strip()
    if not raw:
        return []
    parsed = json.loads(raw)
    if not isinstance(parsed, list) or not all(isinstance(x, str) for x in parsed):
        raise ValueError("MCP_*_COMMAND must be a JSON array of strings")
    return list(parsed)


# ──────────────────────────────────────────────────────────────────
# High-level tool executor
# ──────────────────────────────────────────────────────────────────

class MCPToolExecutor:
    """
    Routes tool_call actions whose `tool` field starts with "mcp/<server>"
    to the correct MCP server and returns a normalised result dict.

    Result schema (mirrors execute_tool_action() contract):
        {"ok": bool, "status": str, "data": dict | None, "error": str | None}
    """

    def __init__(
        self,
        extra_servers: Optional[Dict[str, str]] = None,
        api_key: str = "",
    ) -> None:
        self._servers: Dict[str, str] = {**_DEFAULT_SERVERS}
        # Allow override via environment: MCP_SERVERS='{"kanban":"https://..."}'
        env_override = os.environ.get("MCP_SERVERS", "")
        if env_override:
            try:
                self._servers.update(json.loads(env_override))
            except json.JSONDecodeError:
                _log.warning("MCP_SERVERS env var is not valid JSON – ignored")
        if extra_servers:
            self._servers.update(extra_servers)
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    def register_server(self, name: str, url: str) -> None:
        self._servers[name] = url

    def run(
        self,
        action: Dict[str, Any],
        ctx: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        action = {
            "type":      "tool_call",
            "tool":      "mcp/github",          # "mcp/<server_name>"
            "operation": "create_issue",         # MCP tool name on that server
            "params":    {"title": "...", ...},  # arguments forwarded verbatim
        }
        """
        tool_field  = str(action.get("tool") or "")
        operation   = str(action.get("operation") or "").strip()
        params      = dict(action.get("params") or {})

        # Resolve server name: "mcp/github" → "github"
        server_name = tool_field.removeprefix("mcp/").strip()
        if not server_name:
            return _err("missing MCP server name in tool field")
        if not operation:
            return _err("missing operation")

        # Inject workspace / repo context into params so MCP servers
        # don't have to re-fetch it on every call.
        _inject_context(params, server_name, ctx)

        try:
            from app.core.config import settings as _settings
        except Exception:
            _settings = None  # type: ignore[assignment]

        transport = (os.environ.get("MCP_TRANSPORT") or "").strip().lower()
        if not transport and _settings is not None:
            transport = str(getattr(_settings, "MCP_TRANSPORT", "http") or "http").strip().lower()
        if not transport:
            transport = "http"

        if transport == "off":
            return _err("MCP_TRANSPORT=off disables MCP tool calls")

        if transport == "stdio":
            try:
                argv = _stdio_argv_for_server(server_name)
            except (json.JSONDecodeError, ValueError) as exc:
                return _err(f"invalid MCP stdio command JSON: {exc}")
            if argv:
                to = 45.0
                if _settings is not None:
                    try:
                        to = float(getattr(_settings, "MCP_STDIO_TIMEOUT_SECONDS", 45.0) or 45.0)
                    except (TypeError, ValueError):
                        to = 45.0
                try:
                    result = mcp_stdio_call_tool(argv, operation, params, timeout=to)
                    _log.info("mcp_tool stdio server=%s op=%s ok=True", server_name, operation)
                    return {"ok": True, "status": "ok", "data": result, "error": None}
                except Exception as exc:
                    _log.warning("mcp_tool stdio server=%s op=%s error=%s", server_name, operation, exc)
                    return _err(str(exc))
            _log.info("mcp_tool stdio: no argv for server=%s; falling back to HTTP", server_name)

        server_url = self._servers.get(server_name)
        if not server_url:
            return _err(f"unknown MCP server: {server_name!r}")

        client = MCPClient(server_url, api_key=self._api_key)
        try:
            result = client.call_tool(operation, params)
            _log.info(
                "mcp_tool server=%s op=%s ok=True",
                server_name, operation,
            )
            return {"ok": True, "status": "ok", "data": result, "error": None}
        except RuntimeError as exc:
            _log.warning("mcp_tool server=%s op=%s error=%s", server_name, operation, exc)
            return _err(str(exc))
        except Exception as exc:
            _log.exception("mcp_tool unexpected server=%s op=%s", server_name, operation)
            return _err(f"unexpected: {exc}")


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────

def _err(msg: str) -> Dict[str, Any]:
    return {"ok": False, "status": "error", "data": None, "error": msg}


def _inject_context(
    params: Dict[str, Any],
    server_name: str,
    ctx: Dict[str, Any],
) -> None:
    """
    Enrich params with execution-context values the MCP server needs
    (workspace id, repo coordinates) without overwriting caller-supplied values.
    """
    workspace_id = ctx.get("workspace_id", "")
    github_repo  = ctx.get("github_repo") or {}

    if server_name == "github":
        params.setdefault("owner", github_repo.get("repo_owner", ""))
        params.setdefault("repo",  github_repo.get("repo_name",  ""))

    if server_name in ("kanban", "notification", "calendar"):
        params.setdefault("workspace_id", workspace_id)


# ──────────────────────────────────────────────────────────────────
# Convenience factory functions used by monitoring_node
# ──────────────────────────────────────────────────────────────────

def make_github_issue_action(
    task_id: str,
    title: str,
    body: str,
    labels: Optional[List[str]] = None,
    priority: str = "medium",
) -> Dict[str, Any]:
    """
    Build a pending_action that creates a GitHub issue for a blocked task.
    Enqueue this in monitoring_node when task_status == 'blocked'.
    """
    return {
        "type":      "tool_call",
        "tool":      "mcp/github",
        "operation": "create_issue",
        "params": {
            "title":  title,
            "body":   body,
            "labels": labels or ["blocker"],
        },
        "priority":  priority,
        "task_id":   task_id,
    }


def make_kanban_move_action(
    task_id: str,
    new_status: str,
    priority: str = "high",
) -> Dict[str, Any]:
    """
    Build a pending_action that pushes a kanban card to a new column
    via the kanban MCP server.
    """
    return {
        "type":      "tool_call",
        "tool":      "mcp/kanban",
        "operation": "move_card",
        "params": {
            "card_id": task_id,
            "column":  new_status,
        },
        "priority": priority,
        "task_id":  task_id,
    }


def make_notification_action(
    recipient_ids: List[str],
    message: str,
    event_type: str = "task",
    priority: str = "medium",
) -> Dict[str, Any]:
    """
    Build a pending_action that sends a notification via the notification
    MCP server (Slack / e-mail / push – server decides).
    """
    return {
        "type":      "tool_call",
        "tool":      "mcp/notification",
        "operation": "send",
        "params": {
            "recipients": recipient_ids,
            "message":    message,
            "event_type": event_type,
        },
        "priority": priority,
    }


def make_calendar_review_action(
    workspace_id: str,
    summary: str,
    description: str,
    priority: str = "high",
) -> Dict[str, Any]:
    """
    Build a pending_action that schedules a risk-review calendar event
    when delay_probability is high.
    """
    return {
        "type":      "tool_call",
        "tool":      "mcp/calendar",
        "operation": "create_event",
        "params": {
            "workspace_id": workspace_id,
            "summary":      summary,
            "description":  description,
        },
        "priority": priority,
    }