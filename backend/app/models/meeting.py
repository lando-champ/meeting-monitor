from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime
from bson import ObjectId

class MeetingBase(BaseModel):
    title: str
    description: Optional[str] = None
    project_id: str  # workspace_id or class_id
    jitsi_room: str
    meeting_link: Optional[str] = None
    platform: Literal["jitsi", "gmeet", "zoom", "teams"] = "jitsi"

class MeetingCreate(MeetingBase):
    start_time: datetime

class MeetingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[Literal["scheduled", "live", "ended"]] = None
    ended_at: Optional[datetime] = None

class Meeting(MeetingBase):
    id: str
    status: Literal["scheduled", "live", "ended"]
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Post-meeting data
    summary: Optional[dict] = None  # AI-generated summary
    action_items: Optional[list] = None
    decisions: Optional[list] = None

    class Config:
        from_attributes = True
        json_encoders = {ObjectId: str}
