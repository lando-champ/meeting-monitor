from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List

from bson import ObjectId
from langgraph.graph import END, StateGraph

from app.consilium.database import get_db
from .checkpointer import (
    get_consilium_checkpointer,
    reset_consilium_checkpointer_for_tests,
)
from app.consilium.services.meeting_signals import mark_meeting_signal_processed
from app.consilium.services.monitoring_prefetch import prefetch_monitoring_context
from .monitoring_agent import (
    _stable_hash,
    build_activity_events,
    dedupe_activity_list,
    decide_next_action,
    execution_node,
    fetch_github_activity,
    monitoring_node,
    update_historical_metrics,
)
from .notification_agent import communication_node
from .planning_agent import run_planning_agent
from .replanning_agent import replanning_node
from .risk_agent import risk_node
from .state import ProjectState, agent_log
from app.consilium.services.notification_service import (
    filter_notifications_mongo_idempotent,
    trim_activity_log,
    trim_notifications,
)


def _derive_kanban(tasks: List[Dict[str, Any]]) -> Dict[str, str]:
    return {str(task.get("id") or ""): str(task.get("status") or "todo") for task in tasks if task.get("id")}


def _plan_fingerprint(roadmap: Any, tasks: List[Dict[str, Any]], task_graph: Any) -> str:
    """Stable hash of planning artifacts for idempotency / skip logic."""
    task_signatures = sorted(
        [
            {
                "id": str(t.get("id") or ""),
                "title": str(t.get("title") or ""),
                "status": str(t.get("status") or ""),
                "depends_on": t.get("depends_on"),
            }
            for t in tasks
        ],
        key=lambda x: x["id"],
    )
    return _stable_hash({"roadmap": roadmap, "tasks": task_signatures, "task_graph": task_graph})


def _normalize_kanban(kanban: Any, tasks: List[Dict[str, Any]]) -> Dict[str, str]:
    if not isinstance(kanban, dict) or not kanban:
        return _derive_kanban(tasks)

    sample_value = next(iter(kanban.values()))
    if isinstance(sample_value, str):
        return {str(task_id): str(status) for task_id, status in kanban.items()}

    normalized: Dict[str, str] = {}
    for status, items in kanban.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict) and item.get("id"):
                normalized[str(item["id"])] = str(status)
    return normalized or _derive_kanban(tasks)


def planning_node(state: ProjectState) -> Dict[str, Any]:
    wid = str(state.get("workspace_id") or "")
    agent_log("planner", "start", wid)
    approval_granted = str(state.get("approval_granted_plan_hash") or "")
    staged = state.get("staged_plan")
    if state.get("plan_pending_approval") and isinstance(staged, dict):
        ph = str(staged.get("plan_hash") or "")
        if ph and ph != approval_granted:
            agent_log("planner", "decision", wid, route="staged_plan_awaiting_approval", plan_hash=ph[:16])
            agent_log("planner", "end", wid)
            return {}
        pending = list(state.get("pending_actions") or [])
        if ph and not any(
            isinstance(a, dict) and a.get("type") == "apply_plan" and str(a.get("plan_hash") or "") == ph for a in pending
        ):
            apply_act: Dict[str, Any] = {
                "type": "apply_plan",
                "plan_hash": ph,
                "requires_approval": True,
                "payload": {
                    "tasks": list(staged.get("tasks") or []),
                    "roadmap": staged.get("roadmap") or {},
                    "task_graph": staged.get("task_graph") or {"nodes": [], "edges": []},
                },
            }
            apply_act["action_id"] = f"apply_plan:{ph}"
            apply_act["priority"] = "high"
            apply_act["created_at"] = datetime.now(timezone.utc).isoformat()
            pending = [*pending, apply_act][-200:]
            agent_log("planner", "decision", wid, route="enqueue_approved_plan", plan_hash=ph[:16])
            agent_log("planner", "end", wid)
            return {"pending_actions": pending}
        agent_log("planner", "decision", wid, route="approved_plan_pending_execution")
        agent_log("planner", "end", wid)
        return {}

    roadmap = state.get("roadmap") or {}
    tasks = list(state.get("tasks") or [])
    task_graph = state.get("task_graph") or {"nodes": [], "edges": []}
    prev_hash = state.get("last_plan_hash")

    if roadmap.get("phases") and tasks:
        h = _plan_fingerprint(roadmap, tasks, task_graph)
        plan_changed = h != prev_hash
        agent_log("planner", "decision", wid, route="existing_roadmap", plan_changed=plan_changed)
        agent_log("planner", "end", wid, plan_changed=plan_changed)
        return {
            "kanban": _normalize_kanban(state.get("kanban"), tasks),
            "last_plan_hash": h,
            "plan_changed": plan_changed,
        }

    prd = state.get("prd") or {}
    team = list(state.get("team") or [])
    if not prd:
        h = _plan_fingerprint(roadmap, tasks, task_graph)
        plan_changed = h != prev_hash
        agent_log("planner", "decision", wid, route="no_prd", plan_changed=plan_changed)
        agent_log("planner", "end", wid, plan_changed=plan_changed)
        return {
            "roadmap": roadmap,
            "tasks": tasks,
            "kanban": _normalize_kanban(state.get("kanban"), tasks),
            "last_plan_hash": h,
            "plan_changed": plan_changed,
        }

    existing_tasks = list(state.get("tasks") or [])
    plan = run_planning_agent(
        prd,
        team,
        existing_tasks=existing_tasks,
    )
    planned_tasks = plan.get("tasks") or []
    new_roadmap = plan.get("roadmap") or {}
    new_graph = plan.get("task_graph") or {"nodes": [], "edges": []}
    h = _plan_fingerprint(new_roadmap, planned_tasks, new_graph)
    plan_changed = h != prev_hash
    require_pa = bool(state.get("require_plan_approval", False))
    old_ids = {str(t.get("id") or "") for t in existing_tasks if t.get("id")}
    new_ids = {str(t.get("id") or "") for t in planned_tasks if t.get("id")}
    structural = old_ids != new_ids
    major = bool(structural or (len(existing_tasks) > 0 and len(planned_tasks) != len(existing_tasks)))
    bootstrap = len(existing_tasks) == 0

    if require_pa and major and not bootstrap and plan_changed:
        staged_plan: Dict[str, Any] = {
            "plan_hash": h,
            "roadmap": new_roadmap,
            "tasks": planned_tasks,
            "task_graph": new_graph,
        }
        apply_act: Dict[str, Any] = {
            "type": "apply_plan",
            "plan_hash": h,
            "requires_approval": True,
            "payload": {
                "tasks": planned_tasks,
                "roadmap": new_roadmap,
                "task_graph": new_graph,
            },
        }
        apply_act["action_id"] = f"apply_plan:{h}"
        apply_act["priority"] = "high"
        apply_act["created_at"] = datetime.now(timezone.utc).isoformat()
        pending = list(state.get("pending_actions") or [])
        pending = [*pending, apply_act][-200:]
        agent_log("planner", "decision", wid, route="plan_staged_requires_approval", plan_hash=h[:16])
        agent_log("planner", "end", wid, plan_changed=True, staged_tasks=len(planned_tasks))
        return {
            "roadmap": new_roadmap,
            "task_graph": new_graph,
            "staged_plan": staged_plan,
            "plan_pending_approval": True,
            "pending_actions": pending,
            "last_plan_hash": h,
            "plan_changed": True,
        }

    agent_log("planner", "end", wid, plan_changed=plan_changed, tasks=len(planned_tasks))
    return {
        "roadmap": new_roadmap,
        "task_graph": new_graph,
        "tasks": planned_tasks,
        "kanban": _derive_kanban(planned_tasks),
        "last_plan_hash": h,
        "plan_changed": plan_changed,
        "plan_pending_approval": False,
        "staged_plan": None,
    }


def planning_merge(state: ProjectState) -> Dict[str, Any]:
    u_p = planning_node(state)
    merged = {**dict(state), **u_p}
    u_e = execution_node(merged)
    return {**u_p, **u_e}


def monitoring_merge(state: ProjectState) -> Dict[str, Any]:
    s0: Dict[str, Any] = dict(state)
    u_m = monitoring_node(s0)
    s1 = {**s0, **u_m}
    u_e = execution_node(s1)
    s2 = {**s1, **u_e}
    gr = _route_after_execution_github(s2)
    out: Dict[str, Any] = {**u_m, **u_e}
    if gr == "risk":
        u_r = risk_node(s2)
        out = {**out, **u_r}
        s3 = {**s2, **u_r}
        fr = _route_after_risk(s3)
        out["_graph_next"] = fr
    elif gr == "notify":
        out["_graph_next"] = "notify"
    else:
        out["_graph_next"] = "end"
    return out


def replan_merge(state: ProjectState) -> Dict[str, Any]:
    u_r = replanning_node(state)
    merged = {**dict(state), **u_r}
    if not merged.get("replan_changed", True):
        return u_r
    u_e = execution_node(merged)
    return {**u_r, **u_e}


def _route_after_monitoring_merge(state: ProjectState) -> str:
    nxt = str(state.get("_graph_next") or "end")
    if nxt == "replan":
        return "replan_merge"
    if nxt == "notify":
        return "notify"
    return "end"


def _route_after_replan_merge(state: ProjectState) -> str:
    if state.get("replan_changed", True):
        return "notify"
    return "end"


def _route_after_execution_github(state: ProjectState) -> str:
    """After monitor + execution: use decision layer + guards."""
    d = decide_next_action(state)
    if state.get("project_complete"):
        return "notify"
    if not state.get("monitoring_changed", True) and not state.get("execution_changed", False):
        return "end"
    if state.get("blockers"):
        return "risk"
    if d.get("decision") == "replan":
        return "risk"
    if d.get("decision") == "notify" and (state.get("risks") or []):
        return "risk"
    return "end"


def _route_after_risk(state: ProjectState) -> str:
    d = state.get("decision") or decide_next_action(state)
    if d.get("decision") == "replan":
        return "replan"
    if d.get("decision") == "notify":
        return "notify"
    return "end"


builder = StateGraph(ProjectState)
builder.add_node("planning_merge", planning_merge)
builder.add_node("monitoring_merge", monitoring_merge)
builder.add_node("replan_merge", replan_merge)
builder.add_node("notify", communication_node)
builder.set_entry_point("planning_merge")
builder.add_edge("planning_merge", "monitoring_merge")
builder.add_conditional_edges(
    "monitoring_merge",
    _route_after_monitoring_merge,
    {"replan_merge": "replan_merge", "notify": "notify", "end": END},
)
builder.add_conditional_edges(
    "replan_merge",
    _route_after_replan_merge,
    {"notify": "notify", "end": END},
)
builder.add_edge("notify", END)

_compiled_graph = None
_compile_lock = threading.Lock()


def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        with _compile_lock:
            if _compiled_graph is None:
                _compiled_graph = builder.compile(checkpointer=get_consilium_checkpointer())
    return _compiled_graph


def reset_consilium_graph_for_tests() -> None:
    """Drop compiled graph + checkpointer singleton (pytest)."""
    global _compiled_graph
    with _compile_lock:
        _compiled_graph = None
    reset_consilium_checkpointer_for_tests()


class _CompiledGraphProxy:
    __slots__ = ()

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        return get_compiled_graph().invoke(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(get_compiled_graph(), name)


graph = _CompiledGraphProxy()

_INTERNAL_GRAPH_KEYS = frozenset({"_graph_next", "_meeting_signal_mongo_id"})


def _strip_internal_graph_keys(state: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in state.items() if k not in _INTERNAL_GRAPH_KEYS}


def build_graph_state(
    workspace_id: str,
    workspace: Dict[str, Any],
    github_events: List[Dict[str, Any]] | None = None,
) -> ProjectState:
    tasks = list(workspace.get("tasks") or [])
    team = list(workspace.get("members") or workspace.get("team") or [])
    github = workspace.get("github") or {}
    existing_processed = workspace.get("processed_event_ids") or [
        item.get("event_id") for item in (workspace.get("processed_events") or []) if item.get("event_id")
    ]

    return {
        "workspace_id": workspace_id,
        "prd": workspace.get("prd") or {},
        "team": team,
        "roadmap": workspace.get("roadmap") or {},
        "task_graph": workspace.get("task_graph") or {"nodes": [], "edges": []},
        "tasks": tasks,
        "github_events": github_events or [],
        "kanban": _normalize_kanban(workspace.get("kanban"), tasks),
        "risks": workspace.get("risks") or [],
        "notifications": workspace.get("notifications") or [],
        "project_complete": bool(workspace.get("project_complete")),
        "blockers": workspace.get("blockers") or [],
        "github_repo": {
            "repo_owner": github.get("repo_owner"),
            "repo_name": github.get("repo_name"),
            "repo_full_name": github.get("repo_full_name"),
            "access_token": github.get("access_token"),
        },
        "activity_log": workspace.get("activity_log") or [],
        "processed_event_ids": [event_id for event_id in existing_processed if event_id],
        "last_monitoring_hash": workspace.get("last_monitoring_hash"),
        "last_risks_hash": workspace.get("last_risks_hash"),
        "last_replan_hash": workspace.get("last_replan_hash"),
        "last_plan_hash": workspace.get("last_plan_hash"),
        "plan_changed": False,
        "monitoring_changed": False,
        "risks_changed": False,
        "replan_changed": False,
        "pending_actions": list(workspace.get("pending_actions") or []),
        "applied_action_ids": [str(x) for x in (workspace.get("applied_action_ids") or []) if x],
        "allow_auto_execute": bool(workspace.get("allow_auto_execute", True)),
        "require_plan_approval": bool(workspace.get("require_plan_approval", False)),
        "approval_granted_plan_hash": workspace.get("approval_granted_plan_hash"),
        "staged_plan": workspace.get("staged_plan"),
        "plan_pending_approval": bool(workspace.get("plan_pending_approval", False)),
        "execution_changed": False,
        "decision": workspace.get("decision") or {},
        "execution_limit": 10 if workspace.get("execution_limit") is None else int(workspace.get("execution_limit")),
        "team_metrics": workspace.get("team_metrics") or {},
        "last_github_activity_at": workspace.get("last_github_activity_at"),
        "risk_score": float(workspace.get("risk_score") or 0.0),
        "delay_probability": float(workspace.get("delay_probability") or 0.0),
        "decision_scores": workspace.get("decision_scores") or {},
        "historical_metrics": workspace.get("historical_metrics") or {},
        "allowed_tools": workspace.get("allowed_tools"),
        "tool_results": list(workspace.get("tool_results") or []),
        "external_events": list(workspace.get("external_events") or []),
        "meeting_signal": dict(workspace.get("meeting_signal") or {}),
        "transcript_rag_evidence": str(workspace.get("transcript_rag_evidence") or ""),
        "blocker_recurrence_score": float(workspace.get("blocker_recurrence_score") or 0.0),
    }


async def run_graph_for_workspace(
    workspace_id: str,
    github_events: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    db = await get_db()
    workspaces = db["workspaces"]
    oid = ObjectId(workspace_id)
    workspace = await workspaces.find_one({"_id": oid})
    if not workspace:
        return {}

    prefetch = await prefetch_monitoring_context(db, workspace_id=workspace_id, workspace=workspace)
    initial_state = build_graph_state(workspace_id, workspace, github_events=github_events)
    initial_state.update(prefetch)

    final_raw = graph.invoke(
        initial_state,
        config={"configurable": {"thread_id": workspace_id}},
    )
    final_state = _strip_internal_graph_keys(dict(final_raw))

    tasks = list(final_state.get("tasks") or [])
    kanban = dict(final_state.get("kanban") or _derive_kanban(tasks))
    for task in tasks:
        task_id = str(task.get("id") or "")
        if task_id and task_id in kanban:
            task["status"] = kanban[task_id]

    raw_notifications = list(final_state.get("notifications") or [])
    raw_notifications = await filter_notifications_mongo_idempotent(
        db,
        workspace_id,
        raw_notifications,
        existing_notifications=list(workspace.get("notifications") or []),
    )

    updates: Dict[str, Any] = {
        "roadmap": final_state.get("roadmap") or {},
        "task_graph": final_state.get("task_graph")
        or workspace.get("task_graph")
        or {"nodes": [], "edges": []},
        "tasks": tasks,
        "kanban": kanban,
        "blockers": final_state.get("blockers") or [],
        "risks": list(final_state.get("risks") or []),
        "notifications": trim_notifications(raw_notifications),
        "project_complete": bool(final_state.get("project_complete")),
        "activity_log": trim_activity_log(dedupe_activity_list(final_state.get("activity_log") or [], window_seconds=60)),
        "processed_event_ids": final_state.get("processed_event_ids") or [],
        "github_events": final_state.get("github_events") or [],
        "last_monitoring_hash": final_state.get("last_monitoring_hash"),
        "last_risks_hash": final_state.get("last_risks_hash"),
        "last_replan_hash": final_state.get("last_replan_hash"),
        "last_plan_hash": final_state.get("last_plan_hash"),
        "pending_actions": final_state.get("pending_actions") or [],
        "applied_action_ids": final_state.get("applied_action_ids") or [],
        "staged_plan": final_state.get("staged_plan"),
        "plan_pending_approval": bool(final_state.get("plan_pending_approval", False)),
        "decision": final_state.get("decision") or {},
        "execution_limit": (
            10 if final_state.get("execution_limit") is None else int(final_state.get("execution_limit"))
        ),
        "team_metrics": final_state.get("team_metrics") or {},
        "last_github_activity_at": final_state.get("last_github_activity_at"),
        "risk_score": float(final_state.get("risk_score") or 0.0),
        "delay_probability": float(final_state.get("delay_probability") or 0.0),
        "decision_scores": final_state.get("decision_scores") or {},
        "allowed_tools": final_state.get("allowed_tools"),
        "tool_results": final_state.get("tool_results") or [],
        "external_events": final_state.get("external_events") or [],
    }

    hist = update_historical_metrics(workspace, tasks)
    fs_hist = final_state.get("historical_metrics") or {}
    if fs_hist.get("replan_recent") is not None:
        hist["replan_recent"] = fs_hist["replan_recent"]
    updates["historical_metrics"] = hist

    github_repo = final_state.get("github_repo") or {}
    if github_repo.get("repo_full_name"):
        updates["github.repo_full_name"] = github_repo["repo_full_name"]

    await workspaces.update_one({"_id": oid}, {"$set": updates})

    sig_oid = prefetch.get("_meeting_signal_mongo_id") or initial_state.get("_meeting_signal_mongo_id")
    if sig_oid:
        await mark_meeting_signal_processed(db, str(sig_oid))

    return final_state


async def _run_monitoring_once() -> None:
    db = await get_db()
    workspaces = db["workspaces"]

    cursor = workspaces.find({"github.access_token": {"$exists": True}})
    async for workspace in cursor:
        github: Dict[str, Any] = workspace.get("github") or {}
        owner = github.get("repo_owner")
        repo_name = github.get("repo_name")
        token = github.get("access_token")
        if not (owner and repo_name and token):
            continue

        try:
            repo_summary, commits, pull_requests = await asyncio.to_thread(fetch_github_activity, owner, repo_name, token)
        except Exception:
            continue

        github_events: List[Dict[str, Any]] = [*commits, *pull_requests]
        activity = build_activity_events(commits, pull_requests)

        await workspaces.update_one(
            {"_id": workspace["_id"]},
            {
                "$set": {
                    "activity": activity,
                    "github.repo_full_name": repo_summary.get("full_name"),
                    "github.stars": repo_summary.get("stars"),
                    "github.forks": repo_summary.get("forks"),
                    "github.html_url": repo_summary.get("html_url"),
                }
            },
        )

        await run_graph_for_workspace(str(workspace["_id"]), github_events=github_events)


async def monitoring_loop(poll_interval_seconds: int = 300) -> None:
    await asyncio.sleep(5)
    while True:
        try:
            await _run_monitoring_once()
        except Exception as exc:
            print("Monitoring loop error:", exc)
        await asyncio.sleep(poll_interval_seconds)
