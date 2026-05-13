"""Risk agent: analyze workspace activity and blockers to detect project risks."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List

import httpx
from groq import Groq, GroqError

from app.core.config import settings
from .monitoring_agent import _stable_hash, append_activity_once, decide_next_action
from .state import agent_log
from app.consilium.services.notification_service import create_notification, trim_activity_log, trim_notifications

logger = logging.getLogger(__name__)
VALID_SEVERITIES = {"low", "medium", "high"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_client() -> Groq:
    api_key = (
        settings.RISK_AGENT_KEY
        or settings.GROQ_PLANNING_API_KEY
        or settings.GROQ_REQUIREMENTS_API_KEY
        or settings.GROQ_API_KEY
    )
    if not api_key:
        raise RuntimeError("No risk-agent API key configured")
    return Groq(api_key=api_key)


def _risk_key(risk: Dict[str, Any]) -> str:
    title = (risk.get("title") or "").strip().lower()[:80]
    desc = (risk.get("description") or risk.get("impact") or "").strip().lower()[:80]
    task_id = str(risk.get("task_id") or "")
    return f"{task_id}|{title}|{desc}"


def _risk_id(risk_type: str, description: str) -> str:
    normalized = (description or "").strip().lower()[:50]
    return f"{risk_type}-{normalized}"


def _normalize_risk(risk: Dict[str, Any], now_iso: str, default_type: str = "project") -> Dict[str, Any]:
    risk_type = str(risk.get("type") or default_type)
    description = str(risk.get("description") or risk.get("impact") or "Potential delivery or quality risk.")
    severity = str(risk.get("severity") or "medium").lower()
    if severity not in VALID_SEVERITIES:
        severity = "medium"
    return {
        "id": risk.get("id") or _risk_id(risk_type, description),
        "type": risk_type,
        "title": risk.get("title") or "Project risk",
        "description": description,
        "severity": severity,
        "suggested_action": risk.get("suggested_action") or risk.get("mitigation") or "Review project status and adjust plan.",
        "created_at": risk.get("created_at") or now_iso,
        "task_id": risk.get("task_id"),
    }


def _default_risks() -> List[Dict[str, Any]]:
    return [
        {
            "title": "Potential delivery risks",
            "description": "There may be blocked or delayed work based on recent GitHub activity. Review open tasks and pull requests.",
            "severity": "medium",
            "suggested_action": "Review blocked or long-running tasks and reassign or unblock them.",
        }
    ]


def analyze_workspace_risks(
    workspace: Dict[str, Any],
    commits: List[Dict[str, Any]] | None = None,
    pull_requests: List[Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    workspace_id = str(workspace.get("workspace_id") or workspace.get("id") or "")
    commits = commits or []
    pull_requests = pull_requests or []
    tasks = workspace.get("tasks") or []
    team = workspace.get("members") or workspace.get("team") or []
    existing_risks = list(workspace.get("risks") or [])
    if not commits and not pull_requests and not tasks:
        logger.info(
            "risk_analysis_skipped workspace_id=%s reason=no_activity",
            workspace_id,
        )
        return []
    logger.info(
        "risk_analysis_started workspace_id=%s task_count=%s commit_count=%s pr_count=%s",
        workspace_id,
        len(tasks),
        len(commits),
        len(pull_requests),
    )

    summary = {
        "tasks": [
            {
                "title": task.get("title"),
                "status": task.get("status"),
                "assigned_to": task.get("assigned_to_name") or task.get("assigned_to"),
                "deadline": task.get("deadline"),
            }
            for task in tasks[:50]
        ],
        "commits": commits[:50],
        "pull_requests": pull_requests[:50],
        "team": [{"name": member.get("name"), "role": member.get("role")} for member in team[:20]],
    }

    prompt = f"""
You are a senior software project risk analysis agent.

Given the following JSON context about a project, identify concrete delivery or quality risks and propose mitigations.

Context:
{json.dumps(summary)}

Respond with JSON only:
{{
  "risks": [
    {{
      "title": "Short descriptive title",
      "description": "1-3 sentences explaining the risk and impact",
      "severity": "low" | "medium" | "high",
      "suggested_action": "Concrete next steps to mitigate"
    }}
  ]
}}
""".strip()

    import time

    new_risks: List[Dict[str, Any]] | None = None
    text: str | None = None

    for attempt in range(2):
        attempt_t0 = time.perf_counter()
        t0_llm: float | None = None
        try:
            client = _get_client()
            t0_llm = time.perf_counter()
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=800,
            )
            latency_ms = int((time.perf_counter() - t0_llm) * 1000)
            logger.info(
                "risk_analysis_latency",
                extra={
                    "event": "risk_analysis_latency",
                    "workspace_id": workspace_id,
                    "latency_ms": latency_ms,
                },
            )
            content = resp.choices[0].message.content or "{}"
            text = "".join(part.get("text", "") for part in content if isinstance(part, dict)) if isinstance(content, list) else str(content)
            break
        except RuntimeError as exc:
            latency_ms = int((time.perf_counter() - attempt_t0) * 1000)
            logger.info(
                "risk_analysis_latency",
                extra={
                    "event": "risk_analysis_latency",
                    "workspace_id": workspace_id,
                    "latency_ms": latency_ms,
                },
            )
            logger.warning(
                "risk_analysis_fallback workspace_id=%s reason=%s",
                workspace_id,
                str(exc),
            )
            if not tasks and not pull_requests:
                return list(existing_risks)
            new_risks = _default_risks()
            break
        except (GroqError, httpx.HTTPError, TimeoutError) as exc:
            latency_ms = int((time.perf_counter() - t0_llm) * 1000) if t0_llm is not None else int((time.perf_counter() - attempt_t0) * 1000)
            logger.info(
                "risk_analysis_latency",
                extra={
                    "event": "risk_analysis_latency",
                    "workspace_id": workspace_id,
                    "latency_ms": latency_ms,
                },
            )
            if attempt == 0:
                continue
            short_msg = str(exc).strip()
            if len(short_msg) > 300:
                short_msg = short_msg[:297] + "..."
            logger.warning(
                "risk_analysis_provider_error",
                extra={
                    "event": "risk_analysis_provider_error",
                    "workspace_id": workspace_id,
                    "error_type": type(exc).__name__,
                    "message": short_msg,
                },
            )
            if not tasks and not pull_requests:
                return list(existing_risks)
            new_risks = _default_risks()
            break

    if new_risks is None and text is not None:
        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("Risk model response is not a JSON object")
            new_risks = data.get("risks") or []
            if not isinstance(new_risks, list):
                raise ValueError("Risk model response has invalid 'risks' payload")
        except (ValueError, json.JSONDecodeError, TypeError) as exc:
            logger.warning(
                "risk_analysis_fallback workspace_id=%s reason=%s",
                workspace_id,
                str(exc),
            )
            if not tasks and not pull_requests:
                return list(existing_risks)
            new_risks = _default_risks()

    if new_risks is None:
        if not tasks and not pull_requests:
            return list(existing_risks)
        new_risks = _default_risks()

    now_iso = _utc_now_iso()
    merged: Dict[str, Dict[str, Any]] = {}
    for risk in new_risks:
        if not isinstance(risk, dict):
            logger.warning(
                "risk_analysis_invalid_item workspace_id=%s item_type=%s",
                workspace_id,
                type(risk).__name__,
            )
            continue
        normalized = _normalize_risk(risk, now_iso)
        merged[_risk_key(normalized)] = normalized

    logger.info(
        "risk_analysis_completed workspace_id=%s risk_count=%s",
        workspace_id,
        len(merged),
    )
    return list(merged.values())


def risk_node(state: Dict[str, Any]) -> Dict[str, Any]:
    workspace_id = str(state.get("workspace_id") or "")
    agent_log("risk", "start", workspace_id, blockers=len(state.get("blockers") or []))
    user_id = str(state.get("user_id") or state.get("actor_user_id") or "")
    blockers = list(state.get("blockers") or [])
    notifications = list(state.get("notifications") or [])
    existing_risks = list(state.get("risks") or [])
    activity_log = list(state.get("activity_log") or [])
    github_events = list(state.get("github_events") or [])
    workspace_members = list(state.get("team") or [])
    logger.info(
        "risk_node_started workspace_id=%s user_id=%s blocker_count=%s existing_risk_count=%s",
        workspace_id,
        user_id,
        len(blockers),
        len(existing_risks),
    )
    commits = [event for event in github_events if event.get("type") == "commit"]
    pull_requests = [event for event in github_events if event.get("type") == "pull_request"]

    candidate_risks = analyze_workspace_risks(
        {
            "workspace_id": workspace_id,
            "tasks": state.get("tasks") or [],
            "team": state.get("team") or [],
            "members": state.get("team") or [],
            "risks": existing_risks,
        },
        commits,
        pull_requests,
    )

    now_iso = _utc_now_iso()
    risks_by_id: Dict[str, Dict[str, Any]] = {}
    for risk in candidate_risks:
        normalized = _normalize_risk(risk, now_iso)
        risks_by_id[normalized["id"]] = normalized

    for blocker in blockers:
        message = blocker.get("message") or blocker.get("reason") or "Task blocker detected"
        severity = "high" if "error" in message.lower() or blocker.get("severity") == "high" else "medium"
        normalized = _normalize_risk(
            {
                "type": "blocker",
                "title": "Commit Issue",
                "description": message,
                "severity": severity,
                "suggested_action": "Fix commit or reassign task",
                "created_at": now_iso,
                "task_id": blocker.get("task_id"),
            },
            now_iso,
            default_type="blocker",
        )
        risks_by_id[normalized["id"]] = normalized

    risks = list(risks_by_id.values())
    logger.info(
        "risk_node_compiled workspace_id=%s user_id=%s risk_count=%s",
        workspace_id,
        user_id,
        len(risks),
    )
    risk_hash = _stable_hash(
        sorted(
            [
                {
                    "id": risk.get("id"),
                    "severity": risk.get("severity"),
                    "description": risk.get("description"),
                    "task_id": risk.get("task_id"),
                }
                for risk in risks
            ],
            key=lambda item: (str(item.get("id")), str(item.get("severity")), str(item.get("description"))),
        )
    )

    if risk_hash == state.get("last_risks_hash"):
        logger.info(
            "risk_node_no_change workspace_id=%s user_id=%s",
            workspace_id,
            user_id,
        )
        agent_log("risk", "decision", workspace_id, route="risks_unchanged")
        agent_log("risk", "end", workspace_id, risks_changed=False)
        out_unchanged: Dict[str, Any] = {
            "risks": risks,
            "notifications": notifications,
            "last_risks_hash": risk_hash,
            "risks_changed": False,
        }
        merged_u = {**state, **out_unchanged}
        dn = decide_next_action(merged_u)
        out_unchanged["decision"] = dn
        out_unchanged["risk_score"] = dn.get("risk_score")
        out_unchanged["delay_probability"] = dn.get("delay_probability")
        out_unchanged["decision_scores"] = dn.get("decision_scores")
        return out_unchanged

    existing_risk_ids = {str(risk.get("id") or "") for risk in existing_risks}
    newly_identified = sum(1 for r in risks if str(r.get("id") or "") not in existing_risk_ids)
    recipient_ids = [str(member.get("user_id") or member.get("id") or "") for member in workspace_members]
    if not workspace_id:
        logger.warning("risk_notification_skipped reason=missing_workspace_id")
    for risk in risks:
        if risk["id"] in existing_risk_ids:
            continue
        for recipient_id in [rid for rid in recipient_ids if rid]:
            notifications.append(
                create_notification(
                    recipient_id,
                    f"New {risk.get('severity', 'medium')} risk detected: {risk.get('title') or 'Risk identified'}",
                    "risk",
                    severity=risk.get("severity", "medium"),
                    workspace_id=state.get("workspace_id"),
                    risk_id=risk["id"],
                    event_id=_stable_hash({"type": "risk", "risk_id": risk["id"]}),
                )
            )
            logger.info(
                "risk_notification_created workspace_id=%s recipient_id=%s risk_id=%s severity=%s",
                workspace_id,
                recipient_id,
                risk["id"],
                risk.get("severity", "medium"),
            )

    activity_log = append_activity_once(
        activity_log,
        "RISK_UPDATED",
        "Risk agent updated project risks",
        entity_id=state.get("workspace_id") or "",
        metadata={"risk_hash": risk_hash},
    )

    agent_log("risk", "decision", workspace_id, route="risks_updated", new_risks=newly_identified)
    agent_log("risk", "end", workspace_id, risks_changed=True, risks=len(risks))
    out_changed: Dict[str, Any] = {
        "risks": risks,
        "notifications": trim_notifications(notifications),
        "activity_log": trim_activity_log(activity_log),
        "last_risks_hash": risk_hash,
        "risks_changed": True,
    }
    merged_c = {**state, **out_changed}
    dn = decide_next_action(merged_c)
    out_changed["decision"] = dn
    out_changed["risk_score"] = dn.get("risk_score")
    out_changed["delay_probability"] = dn.get("delay_probability")
    out_changed["decision_scores"] = dn.get("decision_scores")
    return out_changed
