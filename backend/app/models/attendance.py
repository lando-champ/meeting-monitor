from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from bson import ObjectId

class AttendanceBase(BaseModel):
    meeting_id: str
    user_id: str

class AttendanceCreate(AttendanceBase):
    joined_at: datetime

class AttendanceUpdate(BaseModel):
    left_at: Optional[datetime] = None
    duration: Optional[int] = None  # seconds

class Attendance(AttendanceBase):
    id: str
    joined_at: datetime
    left_at: Optional[datetime] = None
    duration: Optional[int] = None  # seconds
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {ObjectId: str}
