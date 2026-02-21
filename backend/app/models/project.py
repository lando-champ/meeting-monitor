from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime
from bson import ObjectId


class MemberInfo(BaseModel):
    id: str
    name: str
    email: str


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    invite_code: str
    project_type: Literal["workspace", "class"]


class ProjectCreate(ProjectBase):
    owner_id: Optional[str] = None  # set from current_user if not provided


class Project(ProjectBase):
    id: str
    owner_id: str
    members: list[str] = []  # user IDs
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {ObjectId: str}


class ProjectOut(Project):
    """Project response with member details (name, email) for display."""
    member_details: list[MemberInfo] = []
