from datetime import datetime
from typing import List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.consilium.database import get_db
from app.consilium.dependencies import ensure_workspace_member, get_current_user
from app.consilium.models.project import ProjectCreate, ProjectPublic

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectPublic, status_code=status.HTTP_201_CREATED)
async def create_project(payload: ProjectCreate, current_user=Depends(get_current_user)):
    # Only managers can create projects
    if current_user["role"] != "manager":
        raise HTTPException(status_code=403, detail="Only managers can create projects")

    await ensure_workspace_member(payload.workspace_id, current_user)

    db = await get_db()
    projects = db["projects"]

    doc = {
        "workspace_id": payload.workspace_id,
        "name": payload.name,
        "description": payload.description,
        "prd": None,
        "phases": [],
        "tech_stack": payload.tech_stack,
        "team_size": payload.team_size,
        "deadline": payload.deadline,
        "status": "planning",
        "created_at": datetime.utcnow(),
    }
    result = await projects.insert_one(doc)

    return ProjectPublic(
        id=str(result.inserted_id),
        workspace_id=doc["workspace_id"],
        name=doc["name"],
        description=doc.get("description"),
        prd=None,
        phases=[],
        tech_stack=doc.get("tech_stack"),
        team_size=doc.get("team_size"),
        deadline=doc.get("deadline"),
        status="planning",
        created_at=doc["created_at"],
    )


@router.get("/workspaces/{workspace_id}", response_model=List[ProjectPublic])
async def list_projects_for_workspace(workspace_id: str, current_user=Depends(get_current_user)):
    await ensure_workspace_member(workspace_id, current_user)

    db = await get_db()
    projects = db["projects"]
    cursor = projects.find({"workspace_id": workspace_id})

    results: List[ProjectPublic] = []
    async for p in cursor:
        results.append(
            ProjectPublic(
                id=str(p["_id"]),
                workspace_id=p["workspace_id"],
                name=p["name"],
                description=p.get("description"),
                prd=p.get("prd"),
                phases=p.get("phases", []),
                tech_stack=p.get("tech_stack"),
                team_size=p.get("team_size"),
                deadline=p.get("deadline"),
                status=p.get("status", "planning"),
                created_at=p.get("created_at", datetime.utcnow()),
            )
        )
    return results


@router.get("/{project_id}", response_model=ProjectPublic)
async def get_project(project_id: str, current_user=Depends(get_current_user)):
    db = await get_db()
    projects = db["projects"]
    try:
        oid = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project id")

    p = await projects.find_one({"_id": oid})
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    # Ensure user is member of the workspace
    await ensure_workspace_member(p["workspace_id"], current_user)

    return ProjectPublic(
        id=str(p["_id"]),
        workspace_id=p["workspace_id"],
        name=p["name"],
        description=p.get("description"),
        prd=p.get("prd"),
        phases=p.get("phases", []),
        tech_stack=p.get("tech_stack"),
        team_size=p.get("team_size"),
        deadline=p.get("deadline"),
        status=p.get("status", "planning"),
        created_at=p.get("created_at", datetime.utcnow()),
    )

