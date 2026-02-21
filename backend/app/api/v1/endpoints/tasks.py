from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from app.core.database import get_database
from app.core.dependencies import get_current_user, verify_project_membership
from app.models.task import Task, TaskCreate, TaskUpdate
from app.models.user import User
from bson import ObjectId
from datetime import datetime

router = APIRouter()

@router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new task"""
    db = await get_database()
    
    # Verify project access
    await verify_project_membership(task_data.project_id, current_user)
    
    task_dict = task_data.model_dump()
    task_dict["is_auto_generated"] = False
    task_dict["created_at"] = datetime.utcnow()
    task_dict["updated_at"] = datetime.utcnow()
    
    result = await db.tasks.insert_one(task_dict)
    task_dict["id"] = str(result.inserted_id)
    return Task(**task_dict)

@router.get("", response_model=List[Task])
async def list_tasks(
    project_id: Optional[str] = None,
    assignee_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """List tasks"""
    db = await get_database()
    query = {}
    
    if project_id:
        query["project_id"] = project_id
        # Verify access (will raise exception if not member)
        await verify_project_membership(project_id, current_user)
    
    if assignee_id:
        query["assignee_id"] = assignee_id
    
    if status:
        query["status"] = status
    
    tasks = await db.tasks.find(query).sort("created_at", -1).to_list(length=100)
    return [Task(id=str(t["_id"]), **{k: v for k, v in t.items() if k != "_id"}) for t in tasks]

@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: str, current_user: User = Depends(get_current_user)):
    """Get task by ID"""
    db = await get_database()
    task = await db.tasks.find_one({"_id": ObjectId(task_id)})
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Verify project access
    await verify_project_membership(task["project_id"], current_user)
    
    return Task(id=str(task["_id"]), **{k: v for k, v in task.items() if k != "_id"})

@router.patch("/{task_id}", response_model=Task)
async def update_task(
    task_id: str,
    task_update: TaskUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update task"""
    db = await get_database()
    task = await db.tasks.find_one({"_id": ObjectId(task_id)})
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Verify project access
    await verify_project_membership(task["project_id"], current_user)
    
    update_data = task_update.model_dump(exclude_unset=True)
    if task_update.status == "done" and not update_data.get("completed_at"):
        update_data["completed_at"] = datetime.utcnow()
    update_data["updated_at"] = datetime.utcnow()
    
    await db.tasks.update_one(
        {"_id": ObjectId(task_id)},
        {"$set": update_data}
    )
    
    updated = await db.tasks.find_one({"_id": ObjectId(task_id)})
    return Task(id=str(updated["_id"]), **{k: v for k, v in updated.items() if k != "_id"})

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str, current_user: User = Depends(get_current_user)):
    """Delete task"""
    db = await get_database()
    task = await db.tasks.find_one({"_id": ObjectId(task_id)})
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Verify project access
    await verify_project_membership(task["project_id"], current_user)
    
    await db.tasks.delete_one({"_id": ObjectId(task_id)})
    return None
