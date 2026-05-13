from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class WorkspaceMember(BaseModel):
    user_id: str
    name: str | None = None
    email: str | None = None
    role: Literal["manager", "member"]
    profile_role: str | None = None
    skills: List[str] = []
    joined_at: datetime = Field(default_factory=datetime.utcnow)


class WorkspaceBase(BaseModel):
  name: str
  description: Optional[str] = None
  invite_code: Optional[str] = None
  tech_stack: Optional[str] = None
  team_size: Optional[int] = None
  deadline: Optional[datetime] = None


class WorkspaceCreate(WorkspaceBase):
  pass


class WorkspacePublic(WorkspaceBase):
  id: str
  owner_id: str
  members: List[WorkspaceMember] = []
  created_at: datetime
  status: Literal["active", "completed"] = "active"

  class Config:
    from_attributes = True

