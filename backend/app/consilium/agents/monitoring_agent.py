"""Monitoring agent: fetch GitHub activity, map it to tasks, and update kanban."""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Set, Tuple

from github import Github

from .state import agent_log
from app.consilium.services.kanban_service import ensure_task_ids as _kanban_ensure_task_ids
from app.consilium.services.kanban_service import task_identity as _task_identity
from app.consilium.services.notification_service import create_notification, trim_activity_log, trim_notifications
from app.consilium.services.tool_registry import execute_tool_action

from .ai_task_mapper import map_commit_to_task_ai, infer_task_status_ai
from .mcp_tools import (
    MCPToolExecutor,
    make_github_issue_action,
    make_notification_action,
    make_calendar_review_action,
)

_mcp_executor = MCPToolExecutor()

_decision_logger = logging.getLogger(__name__)

# Phase 4 completion: deterministic decision thresholds (days / ratios)
_STALE_ACTIVITY_DAYS = 14
_LOW_PROGRESS_THRESHOLD = 0.25
_PRIORITY_RANK = {"high": 3, "medium": 2, "low": 1}
_DEFAULT_EXECUTION_LIMIT = 10
_MAX_MUTATIONS_PER_RUN = 6
_MAX_TOOL_RETRIES = 3

# Phase 5: scoring weights (explainable heuristics)
_FRESHNESS_WINDOW_DAYS = 7
_SCORE_CONFIDENCE_FLOOR = 0.42


def _parse_iso_datetime(ts: Any) -> datetime | None:
    if not ts or not isinstance(ts, str):
        return None
    try:
        s = ts.replace("Z", "+00:00") if "Z" in ts else ts
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _task_effective_status(task: Dict[str, Any], kanban: Dict[str, Any]) -> str:
    tid = str(task.get("id") or "")
    return str(kanban.get(tid) or task.get("status") or "todo")


def _ensure_task_ids(tasks: List[Dict[str, Any]]) -> None:
    _kanban_ensure_task_ids(tasks)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _graph_max_depth(task_graph: Dict[str, Any]) -> int:
    """Longest dependency chain (nodes are task ids)."""
    edges = task_graph.get("edges") or []
    if not edges:
        return 0
    children: Dict[str, List[str]] = {}
    nodes: Set[str] = set()
    for e in edges:
        if not isinstance(e, dict):
            continue
        a = str(e.get("from") or e.get("source") or "")
        b = str(e.get("to") or e.get("target") or "")
        if not a or not b:
            continue
        children.setdefault(a, []).append(b)
        nodes.add(a)
        nodes.add(b)
    memo: Dict[str, int] = {}

    def depth(nid: str) -> int:
        if nid in memo:
            return memo[nid]
        ch = children.get(nid) or []
        if not ch:
            memo[nid] = 1
            return 1
        memo[nid] = 1 + max(depth(c) for c in ch)
        return memo[nid]

    return max((depth(n) for n in nodes), default=0)


def compute_team_metrics(
    tasks: List[Dict[str, Any]],
    team: List[Dict[str, Any]],
    historical_metrics: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Workload, completions, overdue counts, and duration proxies per user."""
    completed_per_user: Dict[str, int] = {}
    workload_per_user: Dict[str, int] = {}
    overdue_per_user: Dict[str, int] = {}
    duration_samples: Dict[str, List[float]] = {}
    now = datetime.now(timezone.utc)

    for m in team:
        uid = str(m.get("user_id") or m.get("id") or "")
        if uid:
            completed_per_user.setdefault(uid, 0)
            workload_per_user.setdefault(uid, 0)
            overdue_per_user.setdefault(uid, 0)

    for t in tasks:
        uid = str(t.get("assigned_to") or "")
        if not uid:
            continue
        st = str(t.get("status") or "todo")
        if st == "done":
            completed_per_user[uid] = completed_per_user.get(uid, 0) + 1
            est = float(t.get("estimated_effort") or 0) or 8.0
            actual = t.get("actual_effort_hours")
            if actual is not None:
                try:
                    duration_samples.setdefault(uid, []).append(float(actual))
                except (TypeError, ValueError):
                    duration_samples.setdefault(uid, []).append(est)
            else:
                duration_samples.setdefault(uid, []).append(est)
        elif st in ("todo", "in_progress", "blocked"):
            workload_per_user[uid] = workload_per_user.get(uid, 0) + 1
        dl = t.get("deadline")
        parsed = _parse_iso_datetime(dl) if dl else None
        if parsed and parsed < now and st not in ("done",):
            overdue_per_user[uid] = overdue_per_user.get(uid, 0) + 1

    hist = historical_metrics or {}
    hist_avg = float(hist.get("avg_task_duration_hours") or 0.0)
    avg_completion_time: Dict[str, float] = {}
    for uid, samples in duration_samples.items():
        if not samples:
            continue
        local = sum(samples) / len(samples)
        avg_completion_time[uid] = round((local + hist_avg) / 2.0, 3) if hist_avg > 0 else round(local, 3)

    tasks_completed_count = sum(completed_per_user.values())
    overdue_tasks_count = sum(overdue_per_user.values())

    return {
        "completed_per_user": completed_per_user,
        "workload_per_user": workload_per_user,
        "overdue_per_user": overdue_per_user,
        "avg_completion_time": avg_completion_time,
        "tasks_completed_count": tasks_completed_count,
        "overdue_tasks_count": overdue_tasks_count,
    }


def log_prediction_computed(workspace_id: str, health: Dict[str, Any]) -> None:
    _decision_logger.info(
        json.dumps(
            {
                "event": "prediction_computed",
                "workspace_id": workspace_id,
                "risk_score": health.get("risk_score"),
                "delay_probability": health.get("delay_probability"),
                "inputs": health.get("components"),
            },
            default=str,
        )
    )


def compute_project_health(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Heuristic project health: risk_score and delay_probability in [0, 1].
    Deterministic; uses progress, blockers, delays, DAG depth, GitHub freshness, risk list.
    """
    tasks = list(state.get("tasks") or [])
    kanban = state.get("kanban") or {}
    total = len(tasks)
    done_n = sum(1 for t in tasks if _task_effective_status(t, kanban) == "done")
    progress = (done_n / total) if total else 1.0
    blocked = sum(1 for t in tasks if _task_effective_status(t, kanban) == "blocked")
    now = datetime.now(timezone.utc)
    delayed = 0
    for t in tasks:
        dl = t.get("deadline")
        parsed = _parse_iso_datetime(dl) if dl else None
        if parsed and parsed < now and _task_effective_status(t, kanban) not in ("done",):
            delayed += 1

    tg = state.get("task_graph") or {}
    depth = _graph_max_depth(tg if isinstance(tg, dict) else {})
    depth_norm = _clamp01(depth / 12.0)

    fresh = _github_events_recent(state, _FRESHNESS_WINDOW_DAYS)
    freshness_factor = 0.0 if fresh else 1.0

    risks = list(state.get("risks") or [])
    high_n = sum(1 for r in risks if str(r.get("severity") or "").lower() == "high")
    med_n = sum(1 for r in risks if str(r.get("severity") or "").lower() == "medium")
    risk_sev_component = _clamp01(high_n * 0.22 + med_n * 0.1 + min(len(risks), 8) * 0.04)

    br = _clamp01(blocked / max(total, 1))
    dr = _clamp01(delayed / max(total, 1))
    recurrence = _clamp01(float(state.get("blocker_recurrence_score") or 0.0))

    risk_score = _clamp01(
        0.22 * (1.0 - progress)
        + 0.18 * br
        + 0.15 * dr
        + 0.18 * depth_norm
        + 0.22 * risk_sev_component
        + 0.05 * freshness_factor
        + 0.12 * recurrence
    )
    delay_probability = _clamp01(
        0.28 * dr
        + 0.24 * (1.0 - progress)
        + 0.22 * depth_norm
        + 0.16 * freshness_factor
        + 0.10 * br
    )

    components = {
        "progress": round(progress, 4),
        "blocked_ratio": round(br, 4),
        "delayed_ratio": round(dr, 4),
        "dependency_depth": depth,
        "depth_norm": round(depth_norm, 4),
        "github_fresh": fresh,
        "risk_count": len(risks),
        "blocker_recurrence": round(recurrence, 4),
    }
    out = {
        "risk_score": round(risk_score, 4),
        "delay_probability": round(delay_probability, 4),
        "components": components,
    }
    log_prediction_computed(str(state.get("workspace_id") or ""), out)
    return out


def score_decisions(state: Dict[str, Any], health: Dict[str, Any]) -> Dict[str, float]:
    """Weighted scores for notify / replan / auto_execute (higher = stronger signal)."""
    tasks = list(state.get("tasks") or [])
    kanban = state.get("kanban") or {}
    total = len(tasks)
    blocked = sum(1 for t in tasks if _task_effective_status(t, kanban) == "blocked")
    risks = list(state.get("risks") or [])
    rs = float(health.get("risk_score") or 0.0)
    dp = float(health.get("delay_probability") or 0.0)
    br = _clamp01(blocked / max(total, 1))
    fresh = _github_events_recent(state, _FRESHNESS_WINDOW_DAYS)
    freshness = 1.0 if fresh else 0.0
    rc = _clamp01(len(risks) / 6.0)

    replan = _clamp01(
        0.32 * rs + 0.28 * dp + 0.22 * br + 0.18 * (1.0 - freshness)
    )
    notify = _clamp01(
        0.35 * rs + 0.22 * dp + 0.25 * rc + 0.18 * (1.0 - br)
    )
    auto_execute = _clamp01(
        0.45 * (1.0 - rs) + 0.35 * (1.0 - dp) + 0.2 * freshness
    )
    return {"replan": replan, "notify": notify, "auto_execute": auto_execute}


def log_decision_scored(workspace_id: str, scores: Dict[str, float], selected: str) -> None:
    _decision_logger.info(
        json.dumps(
            {
                "event": "decision_scored",
                "workspace_id": workspace_id,
                "scores": scores,
                "selected": selected,
            },
            default=str,
        )
    )


def update_historical_metrics(workspace: Dict[str, Any], tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Lightweight EMA on actual vs estimated effort and blocked counts per assignee.
    """
    prev = dict(workspace.get("historical_metrics") or {})
    runs = int(prev.get("runs") or 0) + 1
    done = [t for t in tasks if str(t.get("status")) == "done"]
    act_sum = 0.0
    n = 0
    for t in done:
        est = float(t.get("estimated_effort") or 0) or 8.0
        raw = t.get("actual_effort_hours")
        try:
            a = float(raw) if raw is not None else est
        except (TypeError, ValueError):
            a = est
        act_sum += a
        n += 1
    old_avg = float(prev.get("avg_task_duration_hours") or 0.0)
    batch_avg = act_sum / n if n else old_avg
    avg_task_duration = round((0.65 * old_avg + 0.35 * batch_avg) if old_avg > 0 else batch_avg, 3) if n else old_avg

    fp_prev = dict((prev.get("failure_patterns") or {}).get("blocked_assigned") or {})
    now = datetime.now(timezone.utc)
    overdue_count = 0
    for t in tasks:
        uid = str(t.get("assigned_to") or "")
        if str(t.get("status")) == "blocked" and uid:
            fp_prev[uid] = fp_prev.get(uid, 0) + 1
        dl = t.get("deadline")
        p = _parse_iso_datetime(dl) if dl else None
        if p and p < now and str(t.get("status")) != "done":
            overdue_count += 1

    out: Dict[str, Any] = {
        "avg_task_duration_hours": avg_task_duration or prev.get("avg_task_duration_hours"),
        "failure_patterns": {"blocked_assigned": fp_prev},
        "common_delays": {
            "overdue_open_tasks": overdue_count,
            "done_tasks_in_sample": n,
        },
        "runs": runs,
        "last_run_at": datetime.now(timezone.utc).isoformat(),
    }
    if prev.get("replan_recent"):
        out["replan_recent"] = prev["replan_recent"]
    return out


def _decide_rules_only(state: Dict[str, Any]) -> Dict[str, Any]:
    """Phase 4 rule fallback (no logging)."""
    tasks = list(state.get("tasks") or [])
    kanban = state.get("kanban") or {}
    risks = list(state.get("risks") or [])
    blocked = sum(1 for t in tasks if _task_effective_status(t, kanban) == "blocked")
    now = datetime.now(timezone.utc)
    delayed = 0
    for t in tasks:
        dl = t.get("deadline")
        parsed = _parse_iso_datetime(dl) if dl else None
        if parsed and parsed < now and _task_effective_status(t, kanban) not in ("done",):
            delayed += 1
    high = any((str(r.get("severity") or "").lower() == "high") for r in risks)
    total = len(tasks)
    done_n = sum(1 for t in tasks if _task_effective_status(t, kanban) == "done")
    progress = (done_n / total) if total else 1.0
    stale = _activity_stale(state)

    if state.get("project_complete"):
        return {"decision": "notify", "reason": "project_complete", "priority": "high"}

    should_replan = (
        (blocked >= 2)
        or (high and progress < _LOW_PROGRESS_THRESHOLD and total >= 2)
        or stale
    )
    if should_replan:
        reason = (
            "multiple_blocked"
            if blocked >= 2
            else ("high_risk_low_progress" if high and progress < _LOW_PROGRESS_THRESHOLD and total >= 2 else "stale_activity")
        )
        pr = "high" if blocked >= 2 else "medium"
        return {"decision": "replan", "reason": reason, "priority": pr}

    if risks and (state.get("risks_changed", True) or delayed > 0 or blocked > 0):
        return {"decision": "notify", "reason": "risks_or_delays_or_blockers_need_visibility", "priority": "medium"}

    return {"decision": "auto_execute", "reason": "no_escalated_conditions", "priority": "low"}


def _github_events_recent(state: Dict[str, Any], within_days: int) -> bool:
    events = list(state.get("github_events") or [])
    if not events:
        last = state.get("last_github_activity_at")
        parsed = _parse_iso_datetime(last)
        if parsed is None:
            return False
        age = (datetime.now(timezone.utc) - parsed).total_seconds() / 86400.0
        return age <= float(within_days)
    now = datetime.now(timezone.utc)
    for ev in events[:30]:
        p = _parse_iso_datetime(ev.get("timestamp") or ev.get("created_at"))
        if p is not None and (now - p).total_seconds() <= within_days * 86400:
            return True
    return False


def _activity_stale(state: Dict[str, Any]) -> bool:
    if state.get("project_complete"):
        return False
    tasks = list(state.get("tasks") or [])
    if not tasks:
        return False
    if _github_events_recent(state, _STALE_ACTIVITY_DAYS):
        return False
    return True


def decide_next_action(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Phase 5: compute health + weighted decision scores; keep rule-based fallback.
    """
    wid = str(state.get("workspace_id") or "")
    health = compute_project_health(state)
    scores = score_decisions(state, health)
    rule_pkg = _decide_rules_only(state)

    best_key = max(scores, key=lambda k: scores[k])
    best_score = scores[best_key]
    log_decision_scored(wid, scores, best_key)

    decision_map = {"replan": "replan", "notify": "notify", "auto_execute": "auto_execute"}
    chosen = decision_map[best_key]

    inputs: Dict[str, Any] = {
        **(health.get("components") or {}),
        "decision_scores": scores,
        "rule_would": rule_pkg.get("decision"),
    }

    base_extra: Dict[str, Any] = {
        "risk_score": health["risk_score"],
        "delay_probability": health["delay_probability"],
        "decision_scores": scores,
    }

    if rule_pkg.get("reason") == "project_complete":
        out = {**rule_pkg, **base_extra}
    elif rule_pkg["decision"] == "replan":
        out = {**rule_pkg, **base_extra}
    elif best_score >= _SCORE_CONFIDENCE_FLOOR:
        pr = "high" if chosen == "replan" else ("medium" if chosen == "notify" else "low")
        out = {
            "decision": chosen,
            "reason": f"scored_{best_key}",
            "priority": pr,
            **base_extra,
        }
    else:
        out = {**rule_pkg, **base_extra}

    pending_actions = list(state.get("pending_actions") or [])
    _maybe_schedule_review(state, health, pending_actions)
    if pending_actions != list(state.get("pending_actions") or []):
        out["pending_actions"] = pending_actions
    log_decision_made(wid, out, inputs)
    return out


def log_decision_made(workspace_id: str, decision_pkg: Dict[str, Any], inputs: Dict[str, Any]) -> None:
    payload = {
        "event": "decision_made",
        "workspace_id": workspace_id,
        "decision": decision_pkg.get("decision"),
        "reason": decision_pkg.get("reason"),
        "priority": decision_pkg.get("priority"),
        "inputs": inputs,
    }
    _decision_logger.info(json.dumps(payload, default=str))


def _to_iso(dt) -> str:
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    return str(dt)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_hash(value: Any) -> str:
    try:
        payload = json.dumps(value, sort_keys=True, default=str)
    except Exception:
        payload = str(value)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def append_activity_once(
    activity_log: List[Dict[str, Any]],
    action_type: str,
    description: str,
    entity_id: str = "",
    user_id: str = "",
    metadata: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    event_id = _stable_hash({"action_type": action_type, "description": description, "entity_id": entity_id})
    recent_ids = {str(entry.get("event_id") or "") for entry in activity_log[-20:] if entry.get("event_id")}
    if event_id in recent_ids:
        return trim_activity_log(activity_log)

    next_log = list(activity_log)
    next_log.append(
        {
            "event_id": event_id,
            "action_type": action_type,
            "description": description,
            "user_id": user_id,
            "entity_id": entity_id,
            "timestamp": _utc_now_iso(),
            **(metadata or {}),
        }
    )
    return trim_activity_log(next_log)


def fetch_github_activity(
    owner: str,
    repo_name: str,
    token: str,
    max_commits: int = 20,
    max_prs: int = 20,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    gh = Github(token, per_page=max(max_commits, max_prs))
    repo = gh.get_repo(f"{owner}/{repo_name}")

    repo_summary: Dict[str, Any] = {
        "full_name": repo.full_name,
        "stars": repo.stargazers_count,
        "forks": repo.forks_count,
        "html_url": repo.html_url,
    }

    commits: List[Dict[str, Any]] = []
    for idx, commit in enumerate(repo.get_commits()):
        if idx >= max_commits:
            break
        try:
            commits.append(
                {
                    "id": f"github:commit:{(commit.sha or '')[:12]}",
                    "type": "commit",
                    "sha": (commit.sha or "")[:12],
                    "message": commit.commit.message,
                    "user": commit.author.login if commit.author is not None else (commit.commit.author.name if commit.commit and commit.commit.author else None),
                    "timestamp": _to_iso(commit.commit.author.date if commit.commit and commit.commit.author else None),
                }
            )
        except Exception:
            continue

    pull_requests: List[Dict[str, Any]] = []
    for idx, pr in enumerate(repo.get_pulls(state="all")):
        if idx >= max_prs:
            break
        try:
            pull_requests.append(
                {
                    "id": f"github:pr:{pr.number}:{'merged' if pr.merged else pr.state}",
                    "type": "pull_request",
                    "number": pr.number,
                    "title": pr.title,
                    "message": pr.title,
                    "user": pr.user.login if pr.user is not None else None,
                    "state": pr.state,
                    "merged": pr.merged,
                    "timestamp": _to_iso(pr.updated_at or pr.created_at),
                    "created_at": _to_iso(pr.created_at),
                    "closed_at": _to_iso(pr.closed_at) if pr.closed_at else None,
                    "html_url": pr.html_url,
                }
            )
        except Exception:
            continue

    return repo_summary, commits, pull_requests


def build_activity_events(
    commits: List[Dict[str, Any]],
    pull_requests: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    events = [
        {
            "type": event.get("type"),
            "title": event.get("message") or event.get("title"),
            "user": event.get("user"),
            "timestamp": event.get("timestamp"),
            "task_id": event.get("task_id"),
        }
        for event in [*commits, *pull_requests]
    ]
    events.sort(key=lambda item: item.get("timestamp") or "", reverse=True)
    return events


def map_commit_to_task(event: Dict[str, Any], tasks: List[Dict[str, Any]]) -> str | None:
    message = (event.get("message") or event.get("title") or "").lower()
    pr_number = event.get("number")

    for task in tasks:
        task_id = str(task.get("id") or "")
        title = (task.get("title") or "").lower()

        if task_id and task_id.lower() in message:
            return task_id
        if title and len(title) > 8 and title[:24] in message:
            return task_id
        if pr_number is not None and str(task.get("github_pr") or "") == str(pr_number):
            return task_id

    return None


def _event_id_pr(pr_num: Any, merged: bool) -> str:
    return f"github:pr:{pr_num}:{'merged' if merged else 'closed'}"


def _event_id_commit(sha: str) -> str:
    return f"github:commit:{sha}"


def apply_github_activity_to_tasks(
    tasks: List[Dict[str, Any]],
    commits: List[Dict[str, Any]],
    pull_requests: List[Dict[str, Any]],
    processed_event_ids: Set[str] | None = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    processed = processed_event_ids or set()
    now = _utc_now_iso()
    activity: List[Dict[str, Any]] = []
    updated_tasks = [dict(task) for task in tasks]
    task_index = {str(task.get("id") or ""): idx for idx, task in enumerate(updated_tasks)}
    newly_processed: List[str] = []

    for pr in pull_requests:
        pr_num = pr.get("number")
        event_id = _event_id_pr(pr_num, bool(pr.get("merged")))
        if event_id in processed:
            continue
        task_id = map_commit_to_task(pr, updated_tasks)
        if not task_id or task_id not in task_index:
            continue
        idx = task_index[task_id]
        if pr.get("merged"):
            updated_tasks[idx]["status"] = "done"
            activity.append({"action_type": "COMMIT_DETECTED", "description": f"PR #{pr_num} merged -> task marked done: {updated_tasks[idx].get('title', '')}", "user_id": "", "entity_id": task_id, "timestamp": now})
        elif (pr.get("state") or "").lower() == "closed":
            updated_tasks[idx]["status"] = "blocked"
            activity.append({"action_type": "BLOCKER_DETECTED", "description": f"PR #{pr_num} closed unmerged -> task blocked: {updated_tasks[idx].get('title', '')}", "user_id": "", "entity_id": task_id, "timestamp": now})
        else:
            updated_tasks[idx]["status"] = "in_progress"
        newly_processed.append(event_id)

    for commit in commits:
        sha = (commit.get("sha") or "")[:12]
        if not sha:
            continue
        event_id = _event_id_commit(sha)
        if event_id in processed:
            continue
        task_id = map_commit_to_task(commit, updated_tasks)
        if not task_id or task_id not in task_index:
            continue
        idx = task_index[task_id]
        updated_tasks[idx]["status"] = "in_progress"
        activity.append({"action_type": "COMMIT_DETECTED", "description": f"Commit references task {task_id} -> in progress: {updated_tasks[idx].get('title', '')}", "user_id": commit.get("user") or "", "entity_id": task_id, "timestamp": now})
        newly_processed.append(event_id)

    return updated_tasks, activity, newly_processed


def _derive_kanban_from_tasks(tasks: List[Dict[str, Any]]) -> Dict[str, str]:
    return {str(t.get("id") or ""): str(t.get("status") or "todo") for t in tasks if t.get("id")}


def _action_stable_id(action: Dict[str, Any]) -> str:
    """Idempotency key for pending actions (excludes volatile/meta keys)."""
    skip = {"action_id", "priority", "created_at", "deferred", "deferred_reason", "last_error"}
    payload = {k: action.get(k) for k in sorted(action.keys()) if k not in skip}
    return _stable_hash(payload)


def _priority_value(action: Dict[str, Any]) -> int:
    return int(_PRIORITY_RANK.get(str(action.get("priority") or "medium").lower(), 2))


def _sort_pending_actions(actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(actions, key=lambda a: (-_priority_value(a), str(a.get("created_at") or "")))


def _validate_tool_call_action(action: Dict[str, Any]) -> Tuple[bool, str]:
    tool = str(action.get("tool") or "").strip()
    operation = str(action.get("operation") or "").strip()
    if not tool:
        return False, "missing_tool"
    if not operation:
        return False, "missing_operation"
    params = action.get("params")
    if params is not None and not isinstance(params, dict):
        return False, "invalid_params"
    return True, ""


def _defer_low_priority_if_backlogged(sorted_actions: List[Dict[str, Any]], backlog_threshold: int = 15) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """When queue is large, process high first and defer low to a later run."""
    if len(sorted_actions) <= backlog_threshold:
        return sorted_actions, []
    highs = [a for a in sorted_actions if _priority_value(a) >= 3]
    meds = [a for a in sorted_actions if _priority_value(a) == 2]
    lows = [a for a in sorted_actions if _priority_value(a) <= 1]
    deferred = [{**dict(a), "deferred": True, "deferred_reason": "backlog_low_priority"} for a in lows]
    return highs + meds, deferred


def execution_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Phase 4 execution: apply structured pending_actions safely (idempotent, gated by flags).
    Prioritizes high-severity actions, throttles count and mutations per run.
    """
    wid = str(state.get("workspace_id") or "")
    pending_raw = [dict(x) if isinstance(x, dict) else {} for x in (state.get("pending_actions") or [])]
    sorted_p = _sort_pending_actions(pending_raw)
    to_consider, low_deferred = _defer_low_priority_if_backlogged(sorted_p)
    _lim = state.get("execution_limit")
    max_actions = _DEFAULT_EXECUTION_LIMIT if _lim is None else max(1, int(_lim))
    queued = to_consider[:max_actions]
    overflow_deferred = to_consider[max_actions:]
    remaining: List[Dict[str, Any]] = [*low_deferred, *overflow_deferred]
    agent_log(
        "execution",
        "start",
        wid,
        pending=len(pending_raw),
        queued=len(queued),
        execution_limit=max_actions,
        deferred_backlog=len(low_deferred),
    )
    allow = bool(state.get("allow_auto_execute", True))
    require_plan = bool(state.get("require_plan_approval", False))
    approval_hash = str(state.get("approval_granted_plan_hash") or "")

    applied_ids = list(state.get("applied_action_ids") or [])
    applied_set = set(applied_ids)
    tasks = [dict(t) for t in state.get("tasks") or []]
    _ensure_task_ids(tasks)
    kanban = dict(state.get("kanban") or {})
    blockers = list(state.get("blockers") or [])
    activity_log = list(state.get("activity_log") or [])
    notifications = list(state.get("notifications") or [])
    processed_event_ids = set(state.get("processed_event_ids") or [])
    workspace_members = list(state.get("team") or [])
    tool_results = list(state.get("tool_results") or [])
    external_events = list(state.get("external_events") or [])

    executed_n = 0
    failures = 0
    mutations = 0
    result_extras: Dict[str, Any] = {}

    task_lookup = {str(t.get("id") or ""): idx for idx, t in enumerate(tasks)}
    _ALLOWED_CHANGES = {
        "status",
        "assigned_to",
        "assigned_to_name",
        "title",
        "description",
        "deadline",
        "github_pr",
    }

    for raw in queued:
        if not isinstance(raw, dict):
            failures += 1
            agent_log("execution", "decision", wid, route="invalid_action_payload")
            continue
        act = dict(raw)
        aid = str(act.get("action_id") or "").strip() or _action_stable_id(act)
        atype = act.get("type")

        if aid in applied_set:
            agent_log("execution", "decision", wid, route="skip_duplicate", action_id=aid[:16])
            continue

        plan_hash_act = str(act.get("plan_hash") or "")

        if atype == "apply_plan":
            if mutations >= _MAX_MUTATIONS_PER_RUN:
                remaining.append(act)
                agent_log("execution", "decision", wid, route="throttled_mutations", action_type="apply_plan")
                continue
            plan_gate = bool(act.get("requires_approval")) and require_plan
            if plan_gate and (not plan_hash_act or plan_hash_act != approval_hash):
                remaining.append(act)
                agent_log("execution", "decision", wid, route="plan_await_approval", plan_hash=plan_hash_act[:16] if plan_hash_act else "")
                continue
            if not allow:
                remaining.append(act)
                agent_log("execution", "decision", wid, route="auto_execute_disabled", action_type="apply_plan")
                continue
            payload = act.get("payload") or {}
            try:
                new_tasks = [dict(x) for x in (payload.get("tasks") or [])]
                _ensure_task_ids(new_tasks)
                tasks = new_tasks
                kanban = _derive_kanban_from_tasks(tasks)
                result_extras["roadmap"] = payload.get("roadmap") or {}
                result_extras["task_graph"] = payload.get("task_graph") or {"nodes": [], "edges": []}
                task_lookup = {str(t.get("id") or ""): idx for idx, t in enumerate(tasks)}
                applied_set.add(aid)
                executed_n += 1
                activity_log = append_activity_once(
                    activity_log,
                    "PLAN_APPLIED",
                    "Staged plan applied via execution node",
                    entity_id=wid,
                    metadata={"plan_hash": plan_hash_act},
                )
                agent_log("execution", "decision", wid, route="apply_plan_ok", tasks=len(tasks))
                result_extras["staged_plan"] = None
                result_extras["plan_pending_approval"] = False
            except Exception:
                failures += 1
                remaining.append(act)
                agent_log("execution", "decision", wid, route="apply_plan_failed")
            continue

        if atype == "tool_call":
            valid, reason = _validate_tool_call_action(act)
            if not valid:
                failures += 1
                tool_results.append(
                    {
                        "action_id": aid,
                        "tool": act.get("tool"),
                        "operation": act.get("operation"),
                        "status": "error",
                        "ok": False,
                        "at": _utc_now_iso(),
                        "error": reason,
                    }
                )
                tool_results = tool_results[-50:]
                applied_set.add(aid)
                agent_log("execution", "decision", wid, route="tool_call_invalid", reason=reason)
                continue
            if bool(act.get("requires_approval")) and require_plan:
                if not plan_hash_act or plan_hash_act != approval_hash:
                    remaining.append(act)
                    agent_log(
                        "execution",
                        "decision",
                        wid,
                        route="tool_call_await_approval",
                        plan_hash=plan_hash_act[:16] if plan_hash_act else "",
                    )
                    continue
            if not allow:
                remaining.append(act)
                agent_log("execution", "decision", wid, route="auto_execute_disabled", action_type="tool_call")
                continue
            ctx = {
                "workspace_id": wid,
                "github_repo": state.get("github_repo") or {},
                "allowed_tools": state.get("allowed_tools"),
            }
            try:
                res = execute_tool_action(act, ctx)
            except Exception as exc:
                res = {"ok": False, "status": "error", "error": type(exc).__name__}
            tool_results.append(
                {
                    "action_id": aid,
                    "tool": act.get("tool"),
                    "operation": act.get("operation"),
                    "status": res.get("status"),
                    "ok": res.get("ok"),
                    "at": _utc_now_iso(),
                    "data": res.get("data"),
                    "error": res.get("error"),
                "retry_count": int(act.get("retry_count") or 0),
                }
            )
            tool_results = tool_results[-50:]
            data = res.get("data") if isinstance(res.get("data"), dict) else {}
            for key in ("html_url", "htmlLink", "url"):
                if data.get(key):
                    external_events.append(
                        {
                            "source": str(act.get("tool")),
                            "operation": str(act.get("operation")),
                            "url": data[key],
                            "at": _utc_now_iso(),
                        }
                    )
            external_events = external_events[-100:]
            status_text = str(res.get("status") or "")
            is_retryable_error = (not res.get("ok")) and status_text not in ("skipped", "forbidden")
            if is_retryable_error:
                retries = int(act.get("retry_count") or 0) + 1
                failures += 1
                if retries < _MAX_TOOL_RETRIES:
                    remaining.append(
                        {
                            **act,
                            "retry_count": retries,
                            "last_error": str(res.get("error") or status_text or "tool_error"),
                            "deferred_reason": "tool_retry",
                        }
                    )
                else:
                    applied_set.add(aid)
                    activity_log = append_activity_once(
                        activity_log,
                        "TOOL_CALL_FAILED",
                        f"Tool call failed after {retries} attempts: {act.get('tool')}:{act.get('operation')}",
                        entity_id=wid,
                        metadata={
                            "tool": str(act.get("tool") or ""),
                            "operation": str(act.get("operation") or ""),
                            "error": str(res.get("error") or "")[:200],
                        },
                    )
            else:
                applied_set.add(aid)
            executed_n += 1
            agent_log(
                "execution",
                "decision",
                wid,
                route="tool_call",
                tool=str(act.get("tool")),
                operation=str(act.get("operation")),
                status=str(res.get("status")),
            )
            continue

        if not allow:
            remaining.append(act)
            agent_log("execution", "decision", wid, route="auto_execute_disabled", action_type=str(atype))
            continue

        if bool(act.get("requires_approval")) and require_plan and atype != "noop_github_event":
            remaining.append(act)
            agent_log("execution", "decision", wid, route="action_await_approval", action_type=str(atype))
            continue

        try:
            if atype == "update_task":
                if mutations >= _MAX_MUTATIONS_PER_RUN:
                    remaining.append(act)
                    agent_log("execution", "decision", wid, route="throttled_mutations", action_type="update_task")
                    continue
                task_id = str(act.get("task_id") or "")
                changes = act.get("changes") if isinstance(act.get("changes"), dict) else {}
                if not task_id or task_id not in task_lookup:
                    failures += 1
                    agent_log("execution", "decision", wid, route="update_task_missing", task_id=task_id)
                    remaining.append(act)
                    continue
                idx = task_lookup[task_id]
                previous_status = str(tasks[idx].get("status") or kanban.get(task_id) or "todo")
                prev_assignee = str(tasks[idx].get("assigned_to") or "")
                for key, val in changes.items():
                    if key in _ALLOWED_CHANGES and val is not None:
                        tasks[idx][key] = val
                new_status = str(tasks[idx].get("status") or previous_status)
                kanban[task_id] = new_status
                new_assignee = str(tasks[idx].get("assigned_to") or "")
                ev = str(act.get("source_event_id") or "")
                if ev:
                    processed_event_ids.add(ev)
                if previous_status != new_status:
                    actor = str(act.get("actor") or "system")
                    activity_log = append_activity_once(
                        activity_log,
                        "TASK_STATUS_CHANGED",
                        f"{tasks[idx].get('title') or task_id} moved to {new_status}",
                        entity_id=task_id,
                        user_id=actor,
                        metadata={"source_event_id": ev, "task_status": new_status, "source": act.get("source")},
                    )
                    if act.get("source") == "github":
                        activity_log = append_activity_once(
                            activity_log,
                            "COMMIT_DETECTED",
                            f"New commit detected from {actor}",
                            entity_id=task_id,
                            user_id=actor,
                            metadata={"source_event_id": ev},
                        )
                        recipient_ids = [str(m.get("user_id") or m.get("id") or "") for m in workspace_members]
                        for recipient_id in [rid for rid in recipient_ids if rid]:
                            notifications.append(
                                create_notification(
                                    recipient_id,
                                    f"New commit pushed by {actor}",
                                    "commit",
                                    workspace_id=state.get("workspace_id"),
                                    event_id=_stable_hash({"type": "commit", "task_id": task_id, "actor": actor, "source_event_id": ev}),
                                )
                            )
                            notifications.append(
                                create_notification(
                                    recipient_id,
                                    f"Task moved to {new_status}",
                                    "task",
                                    workspace_id=state.get("workspace_id"),
                                    event_id=_stable_hash({"type": "task", "task_id": task_id, "status": new_status, "source_event_id": ev}),
                                )
                            )
                applied_set.add(aid)
                executed_n += 1
                if previous_status != new_status or prev_assignee != new_assignee:
                    mutations += 1
                agent_log("execution", "decision", wid, route="update_task_ok", task_id=task_id, status=new_status)

            elif atype == "append_blocker":
                if mutations >= _MAX_MUTATIONS_PER_RUN:
                    remaining.append(act)
                    agent_log("execution", "decision", wid, route="throttled_mutations", action_type="append_blocker")
                    continue
                blocker = act.get("blocker")
                if not isinstance(blocker, dict):
                    failures += 1
                    remaining.append(act)
                    continue
                blockers.append(blocker)
                ev = str(act.get("source_event_id") or blocker.get("event_id") or "")
                if ev:
                    processed_event_ids.add(ev)
                applied_set.add(aid)
                executed_n += 1
                mutations += 1
                agent_log("execution", "decision", wid, route="append_blocker_ok", task_id=blocker.get("task_id"))

            elif atype == "noop_github_event":
                ev = str(act.get("source_event_id") or "")
                if ev:
                    processed_event_ids.add(ev)
                applied_set.add(aid)
                executed_n += 1
                agent_log("execution", "decision", wid, route="noop_event_ok", source_event_id=ev[:24])

            else:
                remaining.append(act)
                agent_log("execution", "decision", wid, route="unknown_action_type", action_type=str(atype))
        except Exception:
            failures += 1
            remaining.append(act)
            agent_log("execution", "decision", wid, route="action_exception", action_type=str(atype))

    all_done = bool(tasks) and all(
        kanban.get(str(t.get("id") or ""), t.get("status") or "todo") == "done" for t in tasks
    )
    new_applied = list(applied_set)
    if len(new_applied) > 500:
        new_applied = new_applied[-500:]

    team_metrics = compute_team_metrics(tasks, workspace_members, state.get("historical_metrics"))
    agent_log(
        "execution",
        "end",
        wid,
        executed=executed_n,
        failures=failures,
        mutations=mutations,
        remaining=len(remaining),
        project_complete=all_done,
    )
    out: Dict[str, Any] = {
        "tasks": tasks,
        "kanban": kanban,
        "blockers": blockers,
        "notifications": trim_notifications(notifications),
        "activity_log": trim_activity_log(activity_log),
        "processed_event_ids": [e for e in processed_event_ids if e],
        "pending_actions": remaining[-200:],
        "applied_action_ids": new_applied,
        "project_complete": all_done,
        "execution_changed": bool(executed_n or failures),
        "team_metrics": team_metrics,
        "tool_results": tool_results,
        "external_events": external_events,
    }
    if "plan_pending_approval" not in result_extras:
        out["plan_pending_approval"] = state.get("plan_pending_approval", False)
    out.update(result_extras)
    return out


def _max_github_timestamp_iso(events_list: List[Dict[str, Any]]) -> str | None:
    best: datetime | None = None
    for ev in events_list:
        p = _parse_iso_datetime(ev.get("timestamp") or ev.get("created_at"))
        if p and (best is None or p > best):
            best = p
    return best.isoformat() if best else None


def _monitoring_node_event_loop(
    events: List[Dict[str, Any]],
    tasks: List[Dict[str, Any]],
    task_lookup: Dict[str, int],
    processed_event_ids: set[str],
    state: Dict[str, Any],
    wid: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], bool, int]:
    """
    Drop-in replacement for event-processing loop in monitoring_node().
    Returns (updates, new_actions, status_changed, blocker_count).
    """
    del wid  # parity with existing call signature
    updates: List[Dict[str, Any]] = []
    new_actions: List[Dict[str, Any]] = []
    status_changed = False
    blocker_count = 0
    workspace_members = list(state.get("team") or [])

    for event in events:
        event_id = str(event.get("id") or event.get("event_id") or "")
        if event_id and event_id in processed_event_ids:
            continue

        task_id = map_commit_to_task_ai(event, tasks)
        if not task_id or task_id not in task_lookup:
            if event_id:
                noop: Dict[str, Any] = {
                    "type": "noop_github_event",
                    "source": "monitor",
                    "source_event_id": event_id,
                }
                noop["action_id"] = _stable_hash(noop)
                noop["priority"] = "low"
                noop["created_at"] = _utc_now_iso()
                new_actions.append(noop)
            continue

        idx = task_lookup[task_id]
        task = tasks[idx]
        kanban_hint = dict(state.get("kanban") or {})
        previous_status = str(task.get("status") or kanban_hint.get(task_id) or "todo")
        task_status = infer_task_status_ai(event, task)
        actor = event.get("user") or "A contributor"
        updates.append({**event, "task_id": task_id})
        # Canonical Git->Kanban status updates are owned by github_kanban_sync.
        # Monitoring consumes events for risk/notification/replanning only.
        if event_id:
            noop: Dict[str, Any] = {
                "type": "noop_github_event",
                "source": "monitor",
                "source_event_id": event_id,
            }
            noop["action_id"] = _stable_hash(noop)
            noop["priority"] = "low"
            noop["created_at"] = _utc_now_iso()
            new_actions.append(noop)

        if previous_status != task_status:
            status_changed = True

        if task_status == "blocked":
            blocker_count += 1

            gh_issue = make_github_issue_action(
                task_id=task_id,
                title=f"[Blocker] {task.get('title', task_id)}",
                body=(
                    f"GitHub event blocked this task.\n\n"
                    f"**Event:** {event.get('message') or event.get('title')}\n"
                    f"**Actor:** {actor}\n"
                    f"**Event ID:** {event_id}"
                ),
                labels=["blocker", "auto-detected"],
                priority="high",
            )
            gh_issue["action_id"] = _stable_hash(gh_issue)
            gh_issue["created_at"] = _utc_now_iso()
            new_actions.append(gh_issue)

            recipient_ids = [str(m.get("user_id") or m.get("id") or "") for m in workspace_members]
            recipient_ids = [r for r in recipient_ids if r]
            if recipient_ids:
                notif = make_notification_action(
                    recipient_ids=recipient_ids,
                    message=(
                        f"Task blocked: {task.get('title', task_id)} "
                        f"\u2014 {event.get('message') or event.get('title')}"
                    ),
                    event_type="blocker",
                    priority="high",
                )
                notif["action_id"] = _stable_hash(notif)
                notif["created_at"] = _utc_now_iso()
                new_actions.append(notif)

    return updates, new_actions, status_changed, blocker_count


def monitoring_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Observe GitHub activity and enqueue Phase 4 pending_actions (execution_node applies them).
    """
    wid = str(state.get("workspace_id") or "")
    agent_log("monitor", "start", wid, events=len(state.get("github_events") or []))
    if state.get("project_complete"):
        agent_log("monitor", "decision", wid, route="project_complete_skip")
        agent_log("monitor", "end", wid, monitoring_changed=False)
        return {"monitoring_changed": False}

    github_repo = state.get("github_repo") or {}
    tasks = [dict(task) for task in state.get("tasks") or []]
    _ensure_task_ids(tasks)
    processed_event_ids = set(state.get("processed_event_ids") or [])
    pending_actions = list(state.get("pending_actions") or [])

    events = list(state.get("github_events") or [])
    commits = [event for event in events if event.get("type") == "commit"]
    pull_requests = [event for event in events if event.get("type") == "pull_request"]

    if not events and github_repo.get("access_token") and github_repo.get("repo_owner") and github_repo.get("repo_name"):
        _, commits, pull_requests = fetch_github_activity(
            github_repo["repo_owner"],
            github_repo["repo_name"],
            github_repo["access_token"],
        )
        events = [*commits, *pull_requests]

    activity_hash = _stable_hash(events)
    if activity_hash == state.get("last_monitoring_hash"):
        agent_log("monitor", "decision", wid, route="no_github_delta")
        agent_log("monitor", "end", wid, monitoring_changed=False)
        return {
            "last_monitoring_hash": activity_hash,
            "monitoring_changed": False,
        }

    task_lookup = {str(task.get("id") or ""): idx for idx, task in enumerate(tasks)}
    updates, new_actions, status_changed, blocker_count = _monitoring_node_event_loop(
        events=events,
        tasks=tasks,
        task_lookup=task_lookup,
        processed_event_ids=processed_event_ids,
        state=state,
        wid=wid,
    )

    merged_pending = [*pending_actions, *new_actions]
    if len(merged_pending) > 200:
        merged_pending = merged_pending[-200:]

    changed = bool(status_changed or updates or new_actions)
    agent_log(
        "monitor",
        "end",
        wid,
        monitoring_changed=changed,
        actions_enqueued=len(new_actions),
        blockers_enqueued=blocker_count,
    )
    out_events = updates or events
    last_gh = _max_github_timestamp_iso(out_events) or state.get("last_github_activity_at")
    return {
        "github_events": out_events,
        "pending_actions": merged_pending,
        "last_monitoring_hash": activity_hash,
        "monitoring_changed": changed,
        "last_github_activity_at": last_gh,
    }


def _maybe_schedule_review(state: Dict[str, Any], health: Dict[str, Any], pending_actions: List[Dict[str, Any]]) -> None:
    """
    If delay_probability > 0.7, enqueue a calendar review action.
    """
    if float(health.get("delay_probability") or 0.0) <= 0.70:
        return
    action = make_calendar_review_action(
        workspace_id=str(state.get("workspace_id") or ""),
        summary="Project risk review - high delay probability",
        description=(
            f"Automated alert: delay_probability={float(health['delay_probability']):.0%}, "
            f"risk_score={float(health.get('risk_score', 0)):.0%}. "
            "Please review blockers and dependencies."
        ),
        priority="high",
    )
    action["action_id"] = _stable_hash(action)
    action["created_at"] = _utc_now_iso()
    pending_actions.append(action)


def _parse_iso(ts: str) -> datetime | None:
    try:
        if "Z" in ts or ts.endswith("+00:00"):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def dedupe_activity_append(
    existing_log: List[Dict[str, Any]],
    new_entries: List[Dict[str, Any]],
    window_seconds: int = 60,
) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    recent_keys: set = set()
    for entry in reversed(existing_log[-100:]):
        ts = entry.get("timestamp")
        if not ts:
            continue
        parsed = _parse_iso(ts)
        if parsed is None:
            continue
        if (now - parsed).total_seconds() > window_seconds:
            break
        recent_keys.add((entry.get("action_type") or "", entry.get("entity_id") or "", (entry.get("description") or "")[:80]))

    out = list(existing_log)
    for entry in new_entries:
        key = (entry.get("action_type") or "", entry.get("entity_id") or "", (entry.get("description") or "")[:80])
        if key in recent_keys:
            continue
        recent_keys.add(key)
        out.append(entry)
    return out


def dedupe_activity_list(
    entries: List[Dict[str, Any]],
    window_seconds: int = 60,
) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for entry in entries:
        key = (entry.get("action_type") or "", entry.get("entity_id") or "", (entry.get("description") or "")[:80])
        ts = entry.get("timestamp")
        parsed = _parse_iso(ts) if ts else None
        is_dup = False
        for existing in result[-50:]:
            existing_ts = existing.get("timestamp")
            existing_parsed = _parse_iso(existing_ts) if existing_ts else None
            existing_key = (existing.get("action_type") or "", existing.get("entity_id") or "", (existing.get("description") or "")[:80])
            if parsed is not None and existing_parsed is not None and key == existing_key and abs((parsed - existing_parsed).total_seconds()) <= window_seconds:
                is_dup = True
                break
        if not is_dup:
            result.append(entry)
    return result
