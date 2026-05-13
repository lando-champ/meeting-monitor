from datetime import datetime
from typing import List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.consilium.database import get_db
from app.consilium.dependencies import ensure_workspace_member, get_current_user
from app.consilium.models.task import TaskCreate, TaskPublic

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskPublic, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreate, current_user=Depends(get_current_user)):
    await ensure_workspace_member(payload.workspace_id, current_user)

    db = await get_db()
    tasks = db["tasks"]

    now = datetime.utcnow()
    doc = {
        **payload.model_dump(exclude_none=True),
        "created_at": now,
        "updated_at": now,
    }
    result = await tasks.insert_one(doc)

    return TaskPublic(id=str(result.inserted_id), **payload.model_dump(), created_at=now, updated_at=now)


@router.get("/workspaces/{workspace_id}", response_model=List[TaskPublic])
async def list_tasks_for_workspace(workspace_id: str, current_user=Depends(get_current_user)):
    await ensure_workspace_member(workspace_id, current_user)

    db = await get_db()
    tasks = db["tasks"]
    cursor = tasks.find({"workspace_id": workspace_id})

    results: List[TaskPublic] = []
    async for t in cursor:
        results.append(
            TaskPublic(
                id=str(t["_id"]),
                project_id=t["project_id"],
                workspace_id=t["workspace_id"],
                title=t["title"],
                description=t.get("description"),
                assignee_id=t.get("assignee_id"),
                assignee_name=t.get("assignee_name"),
                phase=t.get("phase"),
                priority=t.get("priority", "medium"),
                status=t.get("status", "todo"),
                due_date=t.get("due_date"),
                github_issue=t.get("github_issue"),
                github_pr=t.get("github_pr"),
                blocker_reason=t.get("blocker_reason"),
                created_at=t.get("created_at", datetime.utcnow()),
                updated_at=t.get("updated_at", datetime.utcnow()),
            )
        )
    return results


@router.get("/projects/{project_id}", response_model=List[TaskPublic])
async def list_tasks_for_project(project_id: str, current_user=Depends(get_current_user)):
    db = await get_db()
    tasks = db["tasks"]
    try:
        oid = ObjectId(project_id)
    except Exception:
        # tasks store project_id as string, so just filter by id string
        cursor = tasks.find({"project_id": project_id})
    else:
        cursor = tasks.find({"project_id": str(oid)})

    first = await cursor.to_list(length=1)
    if not first:
        return []

    # Ensure user is member of workspace of first task
    await ensure_workspace_member(first[0]["workspace_id"], current_user)

    results: List[TaskPublic] = []
    for t in first + await tasks.find(
        {"project_id": first[0]["project_id"], "_id": {"$ne": first[0]["_id"]}}
    ).to_list(length=1000):
        results.append(
            TaskPublic(
                id=str(t["_id"]),
                project_id=t["project_id"],
                workspace_id=t["workspace_id"],
                title=t["title"],
                description=t.get("description"),
                assignee_id=t.get("assignee_id"),
                assignee_name=t.get("assignee_name"),
                phase=t.get("phase"),
                priority=t.get("priority", "medium"),
                status=t.get("status", "todo"),
                due_date=t.get("due_date"),
                github_issue=t.get("github_issue"),
                github_pr=t.get("github_pr"),
                blocker_reason=t.get("blocker_reason"),
                created_at=t.get("created_at", datetime.utcnow()),
                updated_at=t.get("updated_at", datetime.utcnow()),
            )
        )
    return results


@router.patch("/{task_id}/status", response_model=TaskPublic)
async def update_task_status(task_id: str, status_value: str, current_user=Depends(get_current_user)):
    if status_value not in {"todo", "in_progress", "blocked", "done"}:
        raise HTTPException(status_code=400, detail="Invalid status")

    db = await get_db()
    tasks = db["tasks"]
    try:
        oid = ObjectId(task_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid task id")

    task = await tasks.find_one({"_id": oid})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await ensure_workspace_member(task["workspace_id"], current_user)

    await tasks.update_one(
        {"_id": oid},
        {"$set": {"status": status_value, "updated_at": datetime.utcnow()}},
    )
    updated = await tasks.find_one({"_id": oid})

    return TaskPublic(
        id=str(updated["_id"]),
        project_id=updated["project_id"],
        workspace_id=updated["workspace_id"],
        title=updated["title"],
        description=updated.get("description"),
        assignee_id=updated.get("assignee_id"),
        assignee_name=updated.get("assignee_name"),
        phase=updated.get("phase"),
        priority=updated.get("priority", "medium"),
        status=updated.get("status", "todo"),
        due_date=updated.get("due_date"),
        github_issue=updated.get("github_issue"),
        github_pr=updated.get("github_pr"),
        blocker_reason=updated.get("blocker_reason"),
        created_at=updated.get("created_at", datetime.utcnow()),
        updated_at=updated.get("updated_at", datetime.utcnow()),
    )

