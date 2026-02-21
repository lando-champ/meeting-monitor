from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.core.database import get_database
from app.core.dependencies import get_current_user, verify_project_membership, verify_project_owner
from app.models.project import Project, ProjectCreate, ProjectOut, MemberInfo
from app.models.user import User
from bson import ObjectId
from datetime import datetime

router = APIRouter()


async def _project_to_out(db, project_dict: dict) -> ProjectOut:
    """Convert project dict to ProjectOut with member_details from users collection."""
    members = project_dict.get("members") or []
    member_details = []
    for uid in members:
        try:
            u = await db.users.find_one({"_id": ObjectId(uid)})
        except Exception:
            u = None
        if u:
            member_details.append(MemberInfo(id=str(u["_id"]), name=u.get("name", ""), email=u.get("email", "")))
    out_id = str(project_dict["_id"])
    rest = {k: v for k, v in project_dict.items() if k not in ("_id", "id")}
    return ProjectOut(id=out_id, **rest, member_details=member_details)


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(project_data: ProjectCreate, current_user: User = Depends(get_current_user)):
    """Create a new project (workspace or class). Stored in database."""
    db = await get_database()
    existing = await db.projects.find_one({"invite_code": project_data.invite_code})
    if existing:
        raise HTTPException(status_code=400, detail="Invite code already exists")
    project_dict = project_data.model_dump(exclude_unset=True)
    project_dict["owner_id"] = project_dict.get("owner_id") or current_user.id
    project_dict["members"] = [current_user.id]
    project_dict["created_at"] = datetime.utcnow()
    project_dict["updated_at"] = datetime.utcnow()
    result = await db.projects.insert_one(project_dict)
    project_dict["_id"] = result.inserted_id
    project_dict["id"] = str(result.inserted_id)
    return await _project_to_out(db, project_dict)


@router.get("", response_model=List[ProjectOut])
async def list_projects(
    project_type: str | None = None,
    current_user: User = Depends(get_current_user)
):
    """List projects user has access to (from database)."""
    db = await get_database()
    query = {"members": current_user.id}
    if project_type:
        query["project_type"] = project_type
    projects = await db.projects.find(query).to_list(length=100)
    return [await _project_to_out(db, {**p, "_id": p["_id"]}) for p in projects]

@router.delete("/all", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_projects(current_user: User = Depends(get_current_user)):
    """Delete all projects owned by the current user."""
    db = await get_database()
    await db.projects.delete_many({"owner_id": current_user.id})


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: str,
    project: dict = Depends(verify_project_membership),
    current_user: User = Depends(get_current_user),
):
    """Get project by ID with member details."""
    db = await get_database()
    return await _project_to_out(db, {**project, "_id": project["_id"]})


@router.post("/join/{invite_code}", response_model=ProjectOut)
async def join_project(invite_code: str, current_user: User = Depends(get_current_user)):
    """Join a project using invite code. Updates project in database."""
    db = await get_database()
    project = await db.projects.find_one({"invite_code": invite_code})
    if not project:
        raise HTTPException(status_code=404, detail="Invalid invite code")
    if current_user.id in project.get("members", []):
        raise HTTPException(status_code=400, detail="Already a member")
    await db.projects.update_one(
        {"_id": project["_id"]},
        {"$addToSet": {"members": current_user.id}, "$set": {"updated_at": datetime.utcnow()}},
    )
    project = await db.projects.find_one({"_id": project["_id"]})
    return await _project_to_out(db, {**project, "_id": project["_id"]})


@router.post("/{project_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_project(
    project_id: str,
    project: dict = Depends(verify_project_membership),
    current_user: User = Depends(get_current_user),
):
    """Leave a project. All users (owner and members) can leave. User is removed from the project and it disappears from their list. If owner leaves, ownership transfers to another member or the project is deleted if empty."""
    db = await get_database()
    members = project.get("members") or []
    if current_user.id not in members:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a member")
    new_members = [m for m in members if m != current_user.id]
    is_owner = project.get("owner_id") == current_user.id
    if not new_members:
        await db.projects.delete_one({"_id": project["_id"]})
        return
    if is_owner:
        await db.projects.update_one(
            {"_id": project["_id"]},
            {
                "$set": {
                    "owner_id": new_members[0],
                    "members": new_members,
                    "updated_at": datetime.utcnow(),
                }
            },
        )
    else:
        await db.projects.update_one(
            {"_id": project["_id"]},
            {
                "$pull": {"members": current_user.id},
                "$set": {"updated_at": datetime.utcnow()},
            },
        )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project: dict = Depends(verify_project_owner),
):
    """Delete a project. Only the project owner can delete it."""
    db = await get_database()
    await db.projects.delete_one({"_id": project["_id"]})
