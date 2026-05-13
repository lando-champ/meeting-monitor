import random
import string
from datetime import datetime
from typing import List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from pydantic import BaseModel
from pymongo.collection import Collection

from app.consilium.database import get_db
from app.consilium.dependencies import get_current_user
from app.consilium.models.workspace import WorkspaceCreate, WorkspaceMember, WorkspacePublic
from app.core.database import get_database

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


async def get_workspaces_collection() -> Collection:
    db = await get_db()
    return db["workspaces"]


async def _enrich_workspace_members(members_raw: list, created_at=None) -> List[WorkspaceMember]:
    """Fill in name/email/role from users collection when missing on member."""
    db = await get_db()
    users_coll = db["users"]
    enriched = []
    for m in members_raw:
        m = dict(m)
        if not m.get("name") or not m.get("email"):
            try:
                user_doc = await users_coll.find_one({"_id": ObjectId(m["user_id"])})
                if user_doc:
                    m["name"] = m.get("name") or user_doc.get("name")
                    m["email"] = m.get("email") or user_doc.get("email")
                    if not m.get("role"):
                        m["role"] = _normalize_workspace_role(user_doc.get("role"))
                    m["profile_role"] = m.get("profile_role") or user_doc.get("role")
            except Exception:
                pass
        if not m.get("joined_at"):
            m["joined_at"] = created_at or datetime.utcnow()
        enriched.append(WorkspaceMember(**m))
    return enriched


def generate_invite_code() -> str:
    def segment(n: int) -> str:
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))

    return f"PROJ-{segment(4)}-{segment(4)}"


def _normalize_workspace_role(raw_role: str | None, *, is_owner: bool = False) -> str:
    """Map free-form account roles to workspace membership roles."""
    if is_owner:
        return "manager"
    role = (raw_role or "").strip().lower()
    if role in {"manager", "admin", "owner", "project manager"}:
        return "manager"
    return "member"


@router.post("", response_model=WorkspacePublic, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate,
    current_user=Depends(get_current_user),
):
    if current_user["role"] != "manager":
        raise HTTPException(status_code=403, detail="Only managers can create workspaces")

    workspaces = await get_workspaces_collection()
    invite_code = payload.invite_code or generate_invite_code()

    owner_id = str(current_user["_id"])
    member = WorkspaceMember(
        user_id=owner_id,
        name=current_user.get("name"),
        email=current_user.get("email"),
        role="manager",
        profile_role=current_user.get("role"),
        skills=current_user.get("skills") or [],
    )

    doc = {
        "name": payload.name,
        "description": payload.description,
        "owner_id": owner_id,
        "invite_code": invite_code,
        "members": [member.model_dump()],
        "created_at": datetime.utcnow(),
        "status": "active",
        "tech_stack": payload.tech_stack,
        "team_size": payload.team_size,
        "deadline": payload.deadline,
    }

    result = await workspaces.insert_one(doc)

    # add workspace to user document
    db = await get_db()
    await db["users"].update_one(
        {"_id": current_user["_id"]},
        {"$addToSet": {"workspaces": str(result.inserted_id)}},
    )

    return WorkspacePublic(
        id=str(result.inserted_id),
        name=doc["name"],
        description=doc.get("description"),
        invite_code=invite_code,
        tech_stack=doc.get("tech_stack"),
        team_size=doc.get("team_size"),
        deadline=doc.get("deadline"),
        owner_id=owner_id,
        members=[member],
        created_at=doc["created_at"],
        status="active",
    )


@router.get("", response_model=List[WorkspacePublic])
async def list_workspaces(current_user=Depends(get_current_user)):
    workspaces = await get_workspaces_collection()
    user_id = str(current_user["_id"])
    cursor = workspaces.find(
        {
            "$or": [
                {"owner_id": user_id},
                {"members.user_id": user_id},
            ]
        }
    )

    results: List[WorkspacePublic] = []
    async for w in cursor:
        members_enriched = await _enrich_workspace_members(
            w.get("members") or [],
            created_at=w.get("created_at"),
        )
        results.append(
            WorkspacePublic(
                id=str(w["_id"]),
                name=w["name"],
                description=w.get("description"),
                invite_code=w.get("invite_code"),
                tech_stack=w.get("tech_stack"),
                team_size=w.get("team_size"),
                deadline=w.get("deadline"),
                owner_id=w["owner_id"],
                members=members_enriched,
                created_at=w["created_at"],
                status=w.get("status", "active"),
            )
        )
    return results


class JoinPayload(BaseModel):
    invite_code: str


class ResolveWorkspaceResponse(BaseModel):
    workspace_id: str


@router.post("/resolve-project/{project_id}", response_model=ResolveWorkspaceResponse)
async def resolve_workspace_from_project(
    project_id: str,
    current_user=Depends(get_current_user),
):
    """
    Bridge Meeting Monitor project IDs to Consilium workspace IDs.
    Creates a workspace once for the project if none exists yet.
    """
    try:
        project_oid = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project id")

    core_db = await get_database()
    project = await core_db.projects.find_one({"_id": project_oid})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    user_id = str(current_user["_id"])
    project_members = [str(member) for member in (project.get("members") or [])]
    if user_id not in project_members:
        raise HTTPException(status_code=403, detail="Not a member of this project")

    workspaces = await get_workspaces_collection()
    existing = await workspaces.find_one({"project_id": project_id})
    if existing:
        return ResolveWorkspaceResponse(workspace_id=str(existing["_id"]))

    users = core_db.users
    members: list[dict] = []
    for member_id in project_members:
        member_doc = await users.find_one({"_id": ObjectId(member_id)})
        is_owner = str(project.get("owner_id") or "") == member_id
        members.append(
            WorkspaceMember(
                user_id=member_id,
                name=(member_doc or {}).get("name"),
                email=(member_doc or {}).get("email"),
                role=_normalize_workspace_role((member_doc or {}).get("role"), is_owner=is_owner),
                profile_role=(member_doc or {}).get("role"),
                skills=(member_doc or {}).get("skills") or [],
            ).model_dump()
        )

    doc = {
        "project_id": project_id,
        "name": project.get("name") or "Workspace",
        "description": project.get("description"),
        "owner_id": str(project.get("owner_id") or user_id),
        "invite_code": project.get("invite_code") or generate_invite_code(),
        "members": members,
        "created_at": project.get("created_at") or datetime.utcnow(),
        "status": "active",
    }
    result = await workspaces.insert_one(doc)
    return ResolveWorkspaceResponse(workspace_id=str(result.inserted_id))


@router.post("/join", response_model=WorkspacePublic)
async def join_workspace(
    payload: JoinPayload,
    current_user=Depends(get_current_user),
):
    workspaces = await get_workspaces_collection()
    w = await workspaces.find_one({"invite_code": payload.invite_code})
    if not w:
        raise HTTPException(status_code=404, detail="Workspace not found")

    user_id = str(current_user["_id"])
    if any(m.get("user_id") == user_id for m in w.get("members", [])):
        # already a member
        pass
    else:
        member = WorkspaceMember(
            user_id=user_id,
            name=current_user.get("name"),
            email=current_user.get("email"),
            role=current_user["role"],
            profile_role=current_user.get("role"),
            skills=current_user.get("skills") or [],
        )
        from datetime import datetime, timezone
        activity_entry = {
            "action_type": "TEAM_MEMBER_ADDED",
            "description": f"Team member joined: {current_user.get('name') or current_user.get('email') or 'User'}",
            "user_id": user_id,
            "entity_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await workspaces.update_one(
            {"_id": w["_id"]},
            {
                "$addToSet": {"members": member.model_dump()},
                "$push": {"activity_log": {"$each": [activity_entry], "$position": 0}},
            },
        )

        db = await get_db()
        await db["users"].update_one(
            {"_id": current_user["_id"]},
            {"$addToSet": {"workspaces": str(w["_id"])}},
        )
        # refresh workspace doc
        w = await workspaces.find_one({"_id": w["_id"]})

    members = await _enrich_workspace_members(
        w.get("members", []),
        created_at=w.get("created_at"),
    )
    return WorkspacePublic(
        id=str(w["_id"]),
        name=w["name"],
        description=w.get("description"),
        invite_code=w.get("invite_code"),
        tech_stack=w.get("tech_stack"),
        team_size=w.get("team_size"),
        deadline=w.get("deadline"),
        owner_id=w["owner_id"],
        members=members,
        created_at=w["created_at"],
        status=w.get("status", "active"),
    )


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(workspace_id: str, current_user=Depends(get_current_user)):
    workspaces = await get_workspaces_collection()
    try:
        oid = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid workspace id")

    w = await workspaces.find_one({"_id": oid})
    if not w:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if w["owner_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Only the owner can delete a workspace")

    await workspaces.delete_one({"_id": oid})

    db = await get_db()
    await db["users"].update_many(
        {},
        {"$pull": {"workspaces": workspace_id}},
    )

    return None


@router.delete(
    "/{workspace_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_member(
    workspace_id: str,
    member_id: str,
    current_user=Depends(get_current_user),
):
    workspaces = await get_workspaces_collection()
    try:
        oid = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid workspace id")

    w = await workspaces.find_one({"_id": oid})
    if not w:
        raise HTTPException(status_code=404, detail="Workspace not found")

    owner_id = str(w["owner_id"])
    # Only managers (including owner) can remove members
    if current_user.get("role") != "manager":
        raise HTTPException(
            status_code=403, detail="Only managers can remove members"
        )

    if member_id == owner_id:
        raise HTTPException(
            status_code=400, detail="Manager cannot remove themselves from workspace"
        )

    await workspaces.update_one(
        {"_id": oid},
        {"$pull": {"members": {"user_id": member_id}}},
    )

    db = await get_db()
    await db["users"].update_one(
        {"_id": ObjectId(member_id)},
        {"$pull": {"workspaces": workspace_id}},
    )

    return None

