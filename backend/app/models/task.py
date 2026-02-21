from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime
from bson import ObjectId

class TaskBase(BaseModel):
    project_id: str  # workspace_id or class_id
    title: str
    description: Optional[str] = None
    status: Literal["todo", "in-progress", "review", "done", "blocked"] = "todo"
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    assignee_id: Optional[str] = None
    due_date: Optional[datetime] = None
    source_meeting_id: Optional[str] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[Literal["todo", "in-progress", "review", "done", "blocked"]] = None
    priority: Optional[Literal["low", "medium", "high", "urgent"]] = None
    assignee_id: Optional[str] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class Task(TaskBase):
    id: str
    is_auto_generated: bool = False
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {ObjectId: str}
