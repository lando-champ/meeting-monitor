from __future__ import annotations

import logging
from typing import Any, Dict, List, TypedDict

logger = logging.getLogger(__name__)


def agent_log(agent: str, phase: str, workspace_id: str = "", **extra: Any) -> None:
    """
    Standard observability for LangGraph agent nodes: start / end / decision.

    * phase: "start" | "end" | "decision" | other (logged at debug)
    """
    parts = [f"agent={agent}", f"phase={phase}"]
    if workspace_id:
        parts.append(f"workspace_id={workspace_id}")
    for key, val in sorted(extra.items(), key=lambda x: x[0]):
        if val is None or val == "":
            continue
        parts.append(f"{key}={val}")
    msg = " ".join(parts)
    if phase in ("start", "end", "decision"):
        logger.info(msg)
    else:
        logger.debug(msg)


class ProjectState(TypedDict, total=False):
    """Shared LangGraph state for all Consilium agents (Phase 3–4 multi-agent + execution)."""

    workspace_id: str
    prd: Dict[str, Any]
    team: List[Dict[str, Any]]

    roadmap: Dict[str, Any]
    task_graph: Dict[str, Any]
    tasks: List[Dict[str, Any]]

    github_events: List[Dict[str, Any]]
    kanban: Dict[str, str]

    risks: List[Dict[str, Any]]
    notifications: List[Dict[str, Any]]

    project_complete: bool

    blockers: List[Dict[str, Any]]
    github_repo: Dict[str, Any]
    activity_log: List[Dict[str, Any]]
    processed_event_ids: List[str]
    last_monitoring_hash: str | None
    last_risks_hash: str | None
    last_replan_hash: str | None
    last_plan_hash: str | None
    plan_changed: bool
    monitoring_changed: bool
    risks_changed: bool
    replan_changed: bool

    # Phase 4: autonomous actions
    pending_actions: List[Dict[str, Any]]
    applied_action_ids: List[str]
    allow_auto_execute: bool
    require_plan_approval: bool
    approval_granted_plan_hash: str | None
    staged_plan: Dict[str, Any] | None
    plan_pending_approval: bool
    execution_changed: bool

    # Phase 4 completion: decision layer + team context
    decision: Dict[str, Any]
    execution_limit: int
    team_metrics: Dict[str, Any]
    last_github_activity_at: str | None

    # Phase 5: prediction + learning
    risk_score: float
    delay_probability: float
    decision_scores: Dict[str, float]
    historical_metrics: Dict[str, Any]

    # Phase 6: MCP-style tools
    allowed_tools: List[str] | None
    tool_results: List[Dict[str, Any]]
    external_events: List[Dict[str, Any]]

    # Report-aligned: meeting pipeline → monitoring
    meeting_signal: Dict[str, Any]
    transcript_rag_evidence: str
    blocker_recurrence_score: float
