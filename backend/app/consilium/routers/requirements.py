from datetime import datetime
from typing import Any, Dict, List
from io import BytesIO

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

from app.consilium.agents.requirements_agent import run_requirements_agent
from app.consilium.agents.planning_agent import run_planning_agent
from app.consilium.database import get_db
from app.consilium.dependencies import ensure_workspace_access, get_current_user
from app.core.database import get_database
from app.consilium.services.notification_service import trim_activity_log, trim_notifications
from app.consilium.services.kanban_service import (
    KANBAN_STATUSES,
    build_kanban,
    ensure_task_ids,
    find_task_index,
)
from app.consilium.services.planning_history_retrieval import retrieve_similar_task_evidence


router = APIRouter(prefix="/api/workspaces", tags=["requirements"])
_PROJECT_KANBAN_STATUSES = {"todo", "in_progress", "in_review", "done", "blockers"}
_PROJECT_KANBAN_PRIORITIES = {"low", "medium", "high", "urgent"}


class GeneratePrdRequest(BaseModel):
    product_name: str
    product_description: str
    target_users: str
    key_features: str
    competitors: str | None = None
    constraints: str | None = None
    meeting_id: str | None = None
    kickoff_transcript: str | None = None


class GeneratePrdResponse(BaseModel):
    prd: Dict[str, Any]

_PRD_TEXT_FIELDS = (
    "overview",
    "problem_statement",
)

_PRD_LIST_FIELDS = (
    "target_users",
    "market_analysis",
    "features",
    "user_stories",
    "functional_requirements",
    "non_functional_requirements",
    "tech_stack",
    "system_architecture",
    "database_design",
    "api_design",
    "security",
    "performance",
    "deployment",
    "folder_structure",
    "milestones",
    "mvp_scope",
    "future_enhancements",
)


def _normalize_prd(prd: Dict[str, Any] | None) -> Dict[str, Any]:
    """Ensure PRD always matches the frontend's expected shape."""
    src = prd if isinstance(prd, dict) else {}
    normalized: Dict[str, Any] = {}

    for key in _PRD_TEXT_FIELDS:
        value = src.get(key, "")
        normalized[key] = value if isinstance(value, str) else str(value or "")

    for key in _PRD_LIST_FIELDS:
        value = src.get(key, [])
        if isinstance(value, list):
            normalized[key] = [str(item).strip() for item in value if str(item).strip()]
        elif isinstance(value, str):
            normalized[key] = [line.strip() for line in value.splitlines() if line.strip()]
        else:
            normalized[key] = []

    # Preserve extra keys from agent output for debugging/inspection.
    for key, value in src.items():
        if key not in normalized:
            normalized[key] = value

    return normalized


def _normalize_project_task_status(raw: Any) -> str:
    status = str(raw or "todo").strip().lower().replace("-", "_")
    if status == "review":
        status = "in_review"
    elif status == "blocked":
        status = "blockers"
    return status if status in _PROJECT_KANBAN_STATUSES else "todo"


def _normalize_project_task_priority(raw: Any) -> str:
    priority = str(raw or "medium").strip().lower()
    if priority in {"critical", "p0"}:
        priority = "urgent"
    elif priority in {"p1"}:
        priority = "high"
    return priority if priority in _PROJECT_KANBAN_PRIORITIES else "medium"


def _coerce_datetime(raw: Any) -> datetime | None:
    if isinstance(raw, datetime):
        return raw
    if raw is None:
        return None
    try:
        text = str(raw).strip()
        if not text:
            return None
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None


async def _upsert_planner_tasks_into_project(
    db,
    *,
    workspace_id: str,
    project_id: str,
    tasks: List[Dict[str, Any]],
) -> None:
    if not project_id:
        return
    now = datetime.utcnow()
    for idx, task in enumerate(tasks):
        if not isinstance(task, dict):
            continue
        planner_task_id = str(task.get("id") or "").strip() or f"planner_{idx + 1}"
        title = str(task.get("title") or "").strip()
        if not title:
            continue
        assignee_id = str(task.get("assigned_to") or "").strip() or None
        assignee_name = str(task.get("assigned_to_name") or "").strip() or None
        status = _normalize_project_task_status(task.get("status"))
        priority = _normalize_project_task_priority(task.get("priority"))
        due_date = _coerce_datetime(task.get("deadline")) or _coerce_datetime(task.get("due_date"))
        assigned_at = _coerce_datetime(task.get("assigned_at"))
        completed_at = _coerce_datetime(task.get("completed_at"))
        if status == "done" and completed_at is None:
            completed_at = now
        description = str(task.get("description") or "").strip() or None

        set_doc: Dict[str, Any] = {
            "project_id": project_id,
            "title": title,
            "description": description,
            "description_user_set": bool(description),
            "status": status,
            "priority": priority,
            "assignee_id": assignee_id,
            "assignee_name": assignee_name,
            "assigned_at": assigned_at,
            "due_date": due_date,
            "subtasks": task.get("subtasks") if isinstance(task.get("subtasks"), list) else None,
            "completed_at": completed_at,
            "last_activity_at": now,
            "is_auto_generated": True,
            "planner_generated": True,
            "planner_task_id": planner_task_id,
            "planner_workspace_id": workspace_id,
            "planner_phase": task.get("phase"),
            "planner_assigned_role": task.get("assigned_to_role"),
            "copilot_created": False,
            "updated_at": now,
        }
        await db.tasks.update_one(
            {
                "project_id": project_id,
                "planner_generated": True,
                "planner_workspace_id": workspace_id,
                "planner_task_id": planner_task_id,
            },
            {"$set": set_doc, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )


@router.post(
    "/{workspace_id}/generate-prd",
    response_model=GeneratePrdResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_prd_for_workspace(
    workspace_id: str,
    payload: GeneratePrdRequest,
    current_user=Depends(get_current_user),
) -> GeneratePrdResponse:
    workspace = await ensure_workspace_access(
        workspace_id, current_user, min_role="member"
    )
    oid = workspace["_id"]
    db = await get_db()
    workspaces = db["workspaces"]

    kickoff_transcript = (payload.kickoff_transcript or "").strip()
    if not kickoff_transcript and payload.meeting_id:
        kickoff_transcript = await _resolve_meeting_transcript_for_workspace(
            workspace=workspace,
            meeting_id=payload.meeting_id,
        )

    input_payload = payload.model_dump()
    input_payload["kickoff_transcript"] = kickoff_transcript or None
    prd = _normalize_prd(await _run_agent_async(input_payload))

    # Save PRD only; roadmap is generated when PRD is finalized
    await workspaces.update_one(
        {"_id": oid},
        {
            "$set": {"prd": prd, "prd_status": "draft"},
            "$unset": {"roadmap": "", "plan_generated": ""},
        },
    )

    return GeneratePrdResponse(prd=prd)


class SavePrdRequest(BaseModel):
    prd: Dict[str, Any]


class PrdResponse(BaseModel):
    prd: Dict[str, Any] | None
    prd_status: str = "draft"


@router.get(
    "/{workspace_id}/prd",
    response_model=PrdResponse,
    status_code=status.HTTP_200_OK,
)
async def get_workspace_prd(
    workspace_id: str,
    current_user=Depends(get_current_user),
) -> PrdResponse:
    workspace = await ensure_workspace_access(
        workspace_id, current_user, min_role="viewer"
    )

    return PrdResponse(
        prd=_normalize_prd(workspace.get("prd")),
        prd_status=workspace.get("prd_status", "draft"),
    )


@router.put(
    "/{workspace_id}/prd",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def save_workspace_prd(
    workspace_id: str,
    payload: SavePrdRequest,
    current_user=Depends(get_current_user),
) -> None:
    workspace = await ensure_workspace_access(
        workspace_id, current_user, min_role="member"
    )
    db = await get_db()
    workspaces = db["workspaces"]

    await workspaces.update_one(
        {"_id": workspace["_id"]},
        {"$set": {"prd": _normalize_prd(payload.prd), "prd_status": "draft"}},
    )

    return None


class FinalizePrdResponse(BaseModel):
    prd_status: str
    roadmap: Dict[str, Any] | None


@router.post(
    "/{workspace_id}/finalize-prd",
    response_model=FinalizePrdResponse,
    status_code=status.HTTP_200_OK,
)
async def finalize_workspace_prd(
    workspace_id: str,
    current_user=Depends(get_current_user),
) -> FinalizePrdResponse:
    workspace = await ensure_workspace_access(
        workspace_id, current_user, min_role="member"
    )
    oid = workspace["_id"]
    db = await get_db()
    workspaces = db["workspaces"]

    prd = _normalize_prd(workspace.get("prd"))
    if not prd:
        raise HTTPException(status_code=400, detail="No PRD to finalize")

    print("PRD FOUND:", prd)
    print("RUNNING PLANNING AGENT")

    history_block, history_meta = await retrieve_similar_task_evidence(
        db,
        exclude_workspace_id=workspace_id,
        prd=prd,
        top_k=14,
        max_workspaces=120,
    )
    history_meta_slim = {
        "retrieved_count": history_meta.get("retrieved_count", 0),
        "anchor_median_hours": history_meta.get("anchor_median_hours"),
    }

    from anyio import to_thread

    def _run() -> Dict[str, Any]:
        return run_planning_agent(
            prd,
            workspace.get("members", []),
            existing_tasks=list(workspace.get("tasks") or []),
            history_context=history_block or None,
            historical_anchor_hours=history_meta.get("anchor_median_hours"),
            historical_title_norms=history_meta.get("title_norms") or set(),
            history_meta=history_meta_slim,
        )

    plan = await to_thread.run_sync(_run)
    print("PLANNING AGENT OUTPUT:", plan)

    roadmap = plan.get("roadmap") or {}
    # If the agent accidentally nested roadmap again, unwrap it defensively
    if isinstance(roadmap, dict) and "roadmap" in roadmap and isinstance(
        roadmap.get("roadmap"), dict
    ):
        roadmap = roadmap["roadmap"]

    print("SAVING ROADMAP:", roadmap)

    tasks = plan.get("tasks") or []
    kanban = build_kanban(tasks)
    project_id = str(workspace.get("project_id") or "").strip()
    await _upsert_planner_tasks_into_project(
        db,
        workspace_id=workspace_id,
        project_id=project_id,
        tasks=tasks,
    )

    await workspaces.update_one(
        {"_id": oid},
        {
            "$set": {
                "prd_status": "final",
                "roadmap": roadmap,
                "tasks": tasks,
                "kanban": kanban,
                "task_graph": plan.get("task_graph") or {"nodes": [], "edges": []},
                "plan_generated": True,
            }
        },
    )

    updated = await workspaces.find_one({"_id": oid})
    print("DATABASE ROADMAP:", updated.get("roadmap"))

    # Run the project-management graph once so monitoring/risk/replanning state is initialized.
    try:
        from app.consilium.agents.graph import run_graph_for_workspace
        await run_graph_for_workspace(workspace_id)
    except Exception as e:
        print("Project graph run failed:", e)

    return FinalizePrdResponse(prd_status="final", roadmap=roadmap)


def _prd_to_markdown(prd: Dict[str, Any]) -> str:
    def section(title: str, body: str) -> str:
        return f"## {title}\n\n{body.strip()}\n\n"

    def list_section(title: str, items: list[str]) -> str:
        lines = "\n".join(f"- {item}" for item in items)
        return f"## {title}\n\n{lines}\n\n"

    md = "# Product Requirements Document\n\n"
    md += section("Product Overview", prd.get("overview", ""))
    md += section("Problem Statement", prd.get("problem_statement", ""))
    md += list_section("Target Users", prd.get("target_users", []))
    md += list_section("Market Analysis", prd.get("market_analysis", []))
    md += list_section("Key Features", prd.get("features", []))
    md += list_section("User Stories", prd.get("user_stories", []))
    md += list_section("Functional Requirements", prd.get("functional_requirements", []))
    md += list_section(
        "Non-Functional Requirements",
        prd.get("non_functional_requirements", []),
    )
    md += list_section("Technical Architecture", prd.get("system_architecture", []))
    md += list_section("Recommended Tech Stack", prd.get("tech_stack", []))
    md += list_section("Database Design", prd.get("database_design", []))
    md += list_section("API Design", prd.get("api_design", []))
    md += list_section("Security Considerations", prd.get("security", []))
    md += list_section("Performance Considerations", prd.get("performance", []))
    md += list_section("Deployment Strategy", prd.get("deployment", []))
    md += list_section("Project Folder Structure", prd.get("folder_structure", []))
    md += list_section("Milestones", prd.get("milestones", []))
    md += list_section("MVP Scope", prd.get("mvp_scope", []))
    md += list_section("Future Enhancements", prd.get("future_enhancements", []))
    return md


@router.get(
    "/{workspace_id}/prd/markdown",
    response_class=PlainTextResponse,
)
async def download_prd_markdown(
    workspace_id: str,
    current_user=Depends(get_current_user),
) -> PlainTextResponse:
    workspace = await ensure_workspace_access(
        workspace_id, current_user, min_role="viewer"
    )
    if not workspace or not workspace.get("prd"):
        raise HTTPException(status_code=404, detail="PRD not found")

    md = _prd_to_markdown(workspace["prd"])
    filename = f"workspace-{workspace_id}-prd.md"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    return PlainTextResponse(content=md, media_type="text/markdown", headers=headers)


@router.get(
    "/{workspace_id}/prd/pdf",
)
async def download_prd_pdf(
    workspace_id: str,
    current_user=Depends(get_current_user),
) -> Response:
    workspace = await ensure_workspace_access(
        workspace_id, current_user, min_role="viewer"
    )
    if not workspace or not workspace.get("prd"):
        raise HTTPException(status_code=404, detail="PRD not found")

    md = _prd_to_markdown(workspace["prd"])

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=LETTER)
    width, height = LETTER
    x = 40
    y = height - 40

    for line in md.splitlines():
        if y < 40:
            pdf.showPage()
            y = height - 40
        pdf.drawString(x, y, line)
        y -= 14

    pdf.save()
    buffer.seek(0)

    filename = f"workspace-{workspace_id}-prd.pdf"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers=headers,
    )


class RoadmapResponse(BaseModel):
    roadmap: Dict[str, Any] | None


@router.get(
    "/{workspace_id}/roadmap",
    response_model=RoadmapResponse,
    status_code=status.HTTP_200_OK,
)
async def get_workspace_roadmap(
    workspace_id: str,
    current_user=Depends(get_current_user),
) -> RoadmapResponse:
    workspace = await ensure_workspace_access(
        workspace_id, current_user, min_role="viewer"
    )

    raw_roadmap = workspace.get("roadmap") or {}
    tasks = workspace.get("tasks") or []
    # Frontend expects roadmap to include phases and tasks
    roadmap = {
        "phases": raw_roadmap.get("phases", []),
        "milestone_tracker": raw_roadmap.get("milestone_tracker", []),
        "tasks": tasks,
    }
    return RoadmapResponse(roadmap=roadmap)


class KanbanResponse(BaseModel):
    kanban: Dict[str, Any]
    tasks: List[Dict[str, Any]]


async def _enrich_members_from_users(members_raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fill name/email/role from users collection when missing on workspace members."""
    db = await get_db()
    users_coll = db["users"]
    result = []
    for m in members_raw:
        m = dict(m)
        user_id = m.get("user_id")
        if user_id and (not m.get("name") or not m.get("email")):
            try:
                user_doc = await users_coll.find_one({"_id": ObjectId(user_id)})
                if user_doc:
                    m["name"] = m.get("name") or user_doc.get("name")
                    m["email"] = m.get("email") or user_doc.get("email")
                    m["role"] = m.get("role") or user_doc.get("role", "member")
            except Exception:
                pass
        result.append(m)
    return result


def _enrich_tasks_with_members(
    tasks: List[Dict[str, Any]],
    members: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Join tasks with workspace members; set assigned_user_id, assigned_name, role."""
    member_by_id = {str(m.get("user_id")): m for m in members if m.get("user_id")}
    enriched = []
    for t in tasks:
        task = dict(t)
        assigned_id = str(task.get("assigned_to") or "")
        if assigned_id and assigned_id in member_by_id:
            member = member_by_id[assigned_id]
            name = member.get("name") or task.get("assigned_to_name") or "Unassigned"
            task["assigned_to_name"] = name
            task["assigned_to_role"] = member.get("role")
            task["assigned_user_id"] = assigned_id
            task["assigned_name"] = name
        else:
            if not task.get("assigned_to_name"):
                task["assigned_to_name"] = "Unassigned"
            task["assigned_user_id"] = assigned_id or None
            task["assigned_name"] = task.get("assigned_to_name") or "Unassigned"
        enriched.append(task)
    return enriched


@router.get(
    "/{workspace_id}/kanban",
    response_model=KanbanResponse,
    status_code=status.HTTP_200_OK,
)
async def get_workspace_kanban(
    workspace_id: str,
    current_user=Depends(get_current_user),
) -> KanbanResponse:
    workspace = await ensure_workspace_access(
        workspace_id, current_user, min_role="viewer"
    )
    db = await get_db()
    workspaces = db["workspaces"]
    tasks = list(workspace.get("tasks") or [])
    if ensure_task_ids(tasks):
        await workspaces.update_one({"_id": workspace["_id"]}, {"$set": {"tasks": tasks}})
    members_raw = workspace.get("members") or []
    members = await _enrich_members_from_users(members_raw)
    tasks = _enrich_tasks_with_members(tasks, members)
    kanban = build_kanban(tasks)
    return KanbanResponse(kanban=kanban, tasks=tasks)


class UpdateWorkspaceTaskRequest(BaseModel):
    status: str | None = None
    priority: str | None = None
    deadline: str | None = None
    title: str | None = None
    description: str | None = None
    assigned_to: str | None = None


class CreateWorkspaceTaskRequest(BaseModel):
    title: str
    description: str | None = None
    status: str | None = "todo"
    priority: str | None = "medium"
    deadline: str | None = None
    assigned_to: str | None = None


class TaskResponse(BaseModel):
    task: Dict[str, Any]


@router.post(
    "/{workspace_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace_task(
    workspace_id: str,
    payload: CreateWorkspaceTaskRequest,
    current_user=Depends(get_current_user),
) -> TaskResponse:
    """Create a task on the workspace Kanban (member or admin)."""
    db = await get_db()
    workspaces = db["workspaces"]
    workspace = await ensure_workspace_access(workspace_id, current_user, min_role="member")
    title = (payload.title or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Task title is required")
    st = (payload.status or "todo").lower()
    if st not in KANBAN_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status; use one of: {KANBAN_STATUSES}")
    tasks = list(workspace.get("tasks") or [])
    ensure_task_ids(tasks)
    new_task: Dict[str, Any] = {
        "id": str(ObjectId()),
        "title": title,
        "description": (payload.description or "").strip(),
        "status": st,
        "priority": (payload.priority or "medium").lower(),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    if payload.deadline is not None:
        new_task["deadline"] = payload.deadline
    if payload.assigned_to is not None:
        new_task["assigned_to"] = payload.assigned_to
    tasks.append(new_task)
    await workspaces.update_one({"_id": workspace["_id"]}, {"$set": {"tasks": tasks}})
    members_raw = workspace.get("members") or []
    members = await _enrich_members_from_users(members_raw)
    enriched = _enrich_tasks_with_members([new_task], members)
    return TaskResponse(task=enriched[0] if enriched else new_task)


@router.patch(
    "/{workspace_id}/tasks/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
)
async def update_workspace_task(
    workspace_id: str,
    task_id: str,
    payload: UpdateWorkspaceTaskRequest,
    current_user=Depends(get_current_user),
) -> TaskResponse:
    """Update a workspace task (status, fields). Used for Kanban drag-and-drop and edits."""
    db = await get_db()
    workspaces = db["workspaces"]
    workspace = await ensure_workspace_access(workspace_id, current_user, min_role="member")
    tasks = list(workspace.get("tasks") or [])
    ensure_task_ids(tasks)
    task_index = find_task_index(tasks, task_id)
    if task_index is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if payload.status is not None:
        st = payload.status.lower()
        if st not in KANBAN_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status; use one of: {KANBAN_STATUSES}")
        tasks[task_index]["status"] = st
    if payload.priority is not None:
        tasks[task_index]["priority"] = str(payload.priority).lower()
    if payload.deadline is not None:
        tasks[task_index]["deadline"] = payload.deadline
    if payload.title is not None:
        t = payload.title.strip()
        if not t:
            raise HTTPException(status_code=400, detail="Task title cannot be empty")
        tasks[task_index]["title"] = t
    if payload.description is not None:
        tasks[task_index]["description"] = payload.description
    if payload.assigned_to is not None:
        tasks[task_index]["assigned_to"] = payload.assigned_to
    tasks[task_index]["updated_at"] = datetime.utcnow().isoformat()
    await workspaces.update_one({"_id": workspace["_id"]}, {"$set": {"tasks": tasks}})
    updated = dict(tasks[task_index])
    members_raw = workspace.get("members") or []
    members = await _enrich_members_from_users(members_raw)
    enriched = _enrich_tasks_with_members([updated], members)
    return TaskResponse(task=enriched[0] if enriched else updated)


class NotificationsResponse(BaseModel):
    notifications: List[Dict[str, Any]]
    unread_count: int = 0


@router.get(
    "/{workspace_id}/notifications",
    response_model=NotificationsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_workspace_notifications(
    workspace_id: str,
    current_user=Depends(get_current_user),
) -> NotificationsResponse:
    workspace = await ensure_workspace_access(
        workspace_id, current_user, min_role="viewer"
    )
    user_id = str(current_user["_id"])
    notifications = [
        item
        for item in trim_notifications(workspace.get("notifications") or [])
        if item.get("user_id") in (None, "", user_id)
    ]
    unread_count = sum(1 for item in notifications if not item.get("read"))
    return NotificationsResponse(notifications=notifications, unread_count=unread_count)


class MarkNotificationsReadRequest(BaseModel):
    notification_ids: List[str] | None = None  # if empty/omit, mark all as read


@router.patch(
    "/{workspace_id}/notifications/read",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def mark_notifications_read(
    workspace_id: str,
    payload: MarkNotificationsReadRequest,
    current_user=Depends(get_current_user),
) -> None:
    workspace = await ensure_workspace_access(
        workspace_id, current_user, min_role="viewer"
    )
    db = await get_db()
    workspaces = db["workspaces"]
    notifications = list(workspace.get("notifications") or [])
    user_id = str(current_user["_id"])
    ids_to_mark = set(payload.notification_ids or [])
    for i, n in enumerate(notifications):
        if isinstance(n, dict):
            if n.get("user_id") not in (None, "", user_id):
                continue
            nid = n.get("id") or str(i)
            if not ids_to_mark or nid in ids_to_mark:
                n["read"] = True
    await workspaces.update_one({"_id": workspace["_id"]}, {"$set": {"notifications": notifications}})


class ActivityResponse(BaseModel):
    activity_log: List[Dict[str, Any]]


@router.get(
    "/{workspace_id}/activity",
    response_model=ActivityResponse,
    status_code=status.HTTP_200_OK,
)
async def get_workspace_activity(
    workspace_id: str,
    current_user=Depends(get_current_user),
) -> ActivityResponse:
    workspace = await ensure_workspace_access(
        workspace_id, current_user, min_role="viewer"
    )
    activity_log = trim_activity_log(workspace.get("activity_log") or [])
    activity_log = sorted(activity_log, key=lambda x: x.get("timestamp", ""), reverse=True)
    return ActivityResponse(activity_log=activity_log)


class RisksResponse(BaseModel):
    risks: List[Dict[str, Any]]


@router.get(
    "/{workspace_id}/risks",
    response_model=RisksResponse,
    status_code=status.HTTP_200_OK,
)
async def get_workspace_risks(
    workspace_id: str,
    current_user=Depends(get_current_user),
) -> RisksResponse:
    """
    Return AI-detected risks for the workspace.
    Risks are periodically updated by the background monitoring/risk agents.
    """
    workspace = await ensure_workspace_access(
        workspace_id, current_user, min_role="viewer"
    )
    risks = list(workspace.get("risks") or [])
    risks = sorted(risks, key=lambda x: x.get("created_at", ""), reverse=True)
    return RisksResponse(risks=risks)


async def _run_agent_async(payload: Any) -> Dict[str, Any]:
    # LangGraph / OpenAI client are synchronous; run in thread to avoid blocking event loop
    from anyio import to_thread

    data = payload.model_dump() if isinstance(payload, GeneratePrdRequest) else payload

    def _run() -> Dict[str, Any]:
        return run_requirements_agent(data)

    return await to_thread.run_sync(_run)


async def _resolve_meeting_transcript_for_workspace(
    workspace: Dict[str, Any],
    meeting_id: str,
) -> str:
    core_db = await get_database()
    try:
        meeting_oid = ObjectId(meeting_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid meeting_id")

    meeting = await core_db.meetings.find_one({"_id": meeting_oid})
    if not meeting:
        raise HTTPException(status_code=404, detail="Selected meeting not found")

    workspace_project_id = str(workspace.get("project_id") or "").strip()
    meeting_project_id = str(meeting.get("project_id") or "").strip()
    if workspace_project_id and meeting_project_id and workspace_project_id != meeting_project_id:
        raise HTTPException(
            status_code=400,
            detail="Selected meeting does not belong to this workspace project",
        )

    summary_doc = await core_db.summaries.find_one(
        {"meeting_id": meeting_id},
        sort=[("created_at", -1)],
    )
    if summary_doc:
        cleaned = str(summary_doc.get("cleaned_transcription") or "").strip()
        if cleaned:
            return cleaned[:30000]

    segments = (
        await core_db.transcript_segments.find({"meeting_id": meeting_id})
        .sort("timestamp", 1)
        .to_list(length=5000)
    )
    if not segments:
        return ""
    joined = "\n".join(str(s.get("text") or "").strip() for s in segments if s.get("text"))
    return joined[:30000]
