"""
Meeting model for Jitsi-based meeting lifecycle (Phase 1).
"""
from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime
from bson import ObjectId


class MeetingBase(BaseModel):
    """Base meeting fields."""

    project_id: str = Field(..., description="Project ID (ObjectId string)")
    room_name: str = Field(..., description="Unique Jitsi room name")
    type: Literal["instant", "scheduled"] = Field(..., description="Meeting type")
    status: Literal["scheduled", "live", "ended"] = Field(..., description="Meeting status")
    start_time: Optional[datetime] = Field(None, description="Scheduled or actual start time")
    created_by: str = Field(..., description="User ID of creator")


class MeetingCreateSchedule(BaseModel):
    """Request body for scheduling a meeting."""

    project_id: str = Field(..., min_length=1, description="Project ID")
    start_time: datetime = Field(..., description="Scheduled start time")


class MeetingCreateInstant(BaseModel):
    """Request body for starting an instant meeting (project_id only)."""

    project_id: str = Field(..., min_length=1, description="Project ID")


class Meeting(MeetingBase):
    """Meeting document as returned from API."""

    id: str = Field(..., description="Meeting ObjectId as string")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True
        json_encoders = {ObjectId: str}
        populate_by_name = True


class StartInstantResponse(BaseModel):
    """Response for POST /meetings/start-instant (camelCase in JSON per spec)."""

    meeting_id: str = Field(..., alias="meetingId", description="Meeting ID")
    room_name: str = Field(..., alias="roomName", description="Jitsi room name")
    jitsi_url: str = Field(..., alias="jitsiUrl", description="Full Jitsi meeting URL")

    model_config = {"populate_by_name": True}
