from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from .monitoring_agent import _stable_hash, append_activity_once
from .state import agent_log
from app.consilium.services.notification_service import create_notification, trim_activity_log, trim_notifications


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_available_member(
    team: List[Dict[str, Any]],
    excluded_member_id: str | None = None,
    team_metrics: Dict[str, Any] | None = None,
    historical_metrics: Dict[str, Any] | None = None,
    task_id: str | None = None,
) -> Dict[str, Any]:
    """Prefer lower workload; penalize slow finishers, repeat replan targets, and blocked history."""
    candidates = [member for member in team if str(member.get("user_id") or member.get("id") or "") != str(excluded_member_id or "")]
    if not candidates:
        return team[0] if team else {}

    workload = (team_metrics or {}).get("workload_per_user") or {}
    avg_ct = (team_metrics or {}).get("avg_completion_time") or {}
    fp = (historical_metrics or {}).get("failure_patterns") or {}
    blocked_map = fp.get("blocked_assigned") or {}
    recent = list((historical_metrics or {}).get("replan_recent") or [])
    to_counts: Dict[str, int] = {}
    for r in recent[-8:]:
        tid = str(r.get("to") or "")
        if tid:
            to_counts[tid] = to_counts.get(tid, 0) + 1
    pair_bad = {(str(r.get("task_id")), str(r.get("to"))) for r in recent[-6:] if r.get("task_id")}

    avg_vals = [float(v) for v in avg_ct.values() if v is not None]
    avg_overall = sum(avg_vals) / len(avg_vals) if avg_vals else 0.0

    def _score(member: Dict[str, Any]) -> float:
        uid = str(member.get("user_id") or member.get("id") or "")
        load = float(workload.get(uid, int(member.get("active_tasks") or 0)))
        slow = float(avg_ct.get(uid) or 0.0)
        penalty = 0.0
        if avg_overall > 0 and slow > avg_overall * 1.45:
            penalty += 4.0
        penalty += float(blocked_map.get(uid) or 0) * 2.5
        penalty += float(to_counts.get(uid) or 0) * 1.5
        if task_id and (task_id, uid) in pair_bad:
            penalty += 6.0
        return load + penalty

    return sorted(candidates, key=_score)[0]


def replanning_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enqueue reassignment actions; execution_node applies them (Phase 4).
    """
    wid = str(state.get("workspace_id") or "")
    agent_log("replanning", "start", wid)
    if state.get("last_replan_hash") == state.get("last_risks_hash"):
        agent_log("replanning", "decision", wid, route="skip_already_synced")
        agent_log("replanning", "end", wid, replan_changed=False)
        return {
            "last_replan_hash": state.get("last_replan_hash"),
            "replan_changed": False,
        }

    pending_actions = list(state.get("pending_actions") or [])
    notifications = list(state.get("notifications") or [])
    activity_log = list(state.get("activity_log") or [])
    team = list(state.get("team") or [])
    kanban = dict(state.get("kanban") or {})
    changed = False
    new_actions: List[Dict[str, Any]] = []
    hm = dict(state.get("historical_metrics") or {})

    for task in state.get("tasks") or []:
        task_id = str(task.get("id") or "")
        task_status = kanban.get(task_id, task.get("status") or "todo")

        if task_status == "blocked" and team:
            previous_assignee = str(task.get("assigned_to") or "")
            new_member = find_available_member(
                team,
                excluded_member_id=previous_assignee,
                team_metrics=state.get("team_metrics"),
                historical_metrics=state.get("historical_metrics"),
                task_id=task_id,
            )
            new_member_id = str(new_member.get("user_id") or new_member.get("id") or "")

            if new_member_id:
                act: Dict[str, Any] = {
                    "type": "update_task",
                    "task_id": task_id,
                    "source": "replanning",
                    "changes": {
                        "assigned_to": new_member_id,
                        "assigned_to_name": new_member.get("name") or task.get("assigned_to_name"),
                        "status": "todo",
                    },
                    "requires_approval": False,
                }
                act["action_id"] = _stable_hash({**act, "risk_hash": state.get("last_risks_hash")})
                act["priority"] = "high"
                act["created_at"] = _utc_now_iso()
                new_actions.append(act)
                changed = True
                recent = list(hm.get("replan_recent") or [])
                recent.append(
                    {
                        "task_id": task_id,
                        "from": previous_assignee,
                        "to": new_member_id,
                        "at": _utc_now_iso(),
                    }
                )
                hm["replan_recent"] = recent[-12:]
                notifications.append(
                    create_notification(
                        new_member_id,
                        f"Task reassigned to {new_member.get('name') or new_member_id}",
                        "task",
                        severity="medium",
                        workspace_id=state.get("workspace_id"),
                    )
                )

    merged = [*pending_actions, *new_actions]
    if len(merged) > 200:
        merged = merged[-200:]

    if changed:
        activity_log = append_activity_once(
            activity_log,
            "REPLANNING_TRIGGERED",
            "Replanning agent enqueued reassignment actions",
            entity_id=state.get("workspace_id") or "",
            metadata={"risk_hash": state.get("last_risks_hash")},
        )
        recipient_ids = [str(member.get("user_id") or member.get("id") or "") for member in team]
        for recipient_id in [rid for rid in recipient_ids if rid]:
            notifications.append(
                create_notification(
                    recipient_id,
                    "Tasks reassigned due to risks (pending execution)",
                    "replanning",
                    severity="medium",
                    workspace_id=state.get("workspace_id"),
                    event_id=f"replanning:{state.get('last_risks_hash') or ''}:{recipient_id}",
                )
            )

    agent_log("replanning", "end", wid, replan_changed=changed, actions=len(new_actions))
    out: Dict[str, Any] = {
        "pending_actions": merged,
        "notifications": trim_notifications(notifications),
        "activity_log": trim_activity_log(activity_log),
        "last_replan_hash": state.get("last_risks_hash"),
        "replan_changed": changed,
    }
    if changed:
        out["historical_metrics"] = hm
    return out
