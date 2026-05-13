from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from .monitoring_agent import _stable_hash
from .state import agent_log
from app.consilium.services.notification_service import create_notification, trim_notifications


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_notification(notification_type: str, message: str, **kwargs: Any) -> Dict[str, Any]:
    return create_notification(kwargs.pop("user_id", None), message, notification_type, **kwargs)


def communication_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Communication agent: fan-in notifications (project / blockers / risks).
    Pure state in → state delta out; persistence happens in graph runner.
    """
    wid = str(state.get("workspace_id") or "")
    agent_log("communication", "start", wid)
    notifications: List[Dict[str, Any]] = list(state.get("notifications") or [])
    recent_ids = {str(item.get("event_id") or "") for item in notifications[-50:] if item.get("event_id")}

    def _append_once(notification: Dict[str, Any]) -> None:
        event_id = _stable_hash(
            {
                "type": notification.get("type"),
                "message": notification.get("message"),
                "severity": notification.get("severity"),
            }
        )
        if event_id in recent_ids:
            return
        notification["event_id"] = event_id
        recent_ids.add(event_id)
        notifications.append(notification)

    if state.get("project_complete"):
        _append_once(
            _new_notification(
                "project_completed",
                "Project completed. All tasks have been finished.",
            )
        )
        agent_log("communication", "decision", wid, kind="project_complete")
        agent_log("communication", "end", wid, appended=1)
        return {"notifications": trim_notifications(notifications)}

    for blocker in (state.get("blockers") or [])[:5]:
        task_title = blocker.get("task_title") or "Task"
        reason = blocker.get("reason") or blocker.get("message") or "Blocker detected"
        severity = blocker.get("severity") or "high"
        _append_once(
            _new_notification(
                "blocker",
                f"Blocker detected for {task_title}: {reason}",
                severity=severity,
            )
        )

    for risk in (state.get("risks") or [])[:3]:
        _append_once(
            _new_notification(
                "risk",
                risk.get("description") or risk.get("title") or "Risk identified",
                severity=risk.get("severity", "medium"),
            )
        )

    agent_log(
        "communication",
        "end",
        wid,
        total_notifications=len(notifications),
    )
    return {"notifications": trim_notifications(notifications)}


# Back-compat alias (same node, multi-agent naming)
notification_node = communication_node
