from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class Notification(BaseModel):
    id: str
    message: str
    read: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: str  # "manager" | "member"
    github_link: Optional[str] = None
    skills: List[str] = []


class UserCreate(UserBase):
    password: str


class UserInDB(UserBase):
    id: str | None = None
    password_hash: str
    github_token: Optional[str] = None
    workspaces: List[str] = []
    avatar_initials: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    notifications: List[Notification] = []

    class Config:
        from_attributes = True


class UserPublic(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str
    github_link: Optional[str] = None
    skills: List[str] = []
    avatar_initials: Optional[str] = None

