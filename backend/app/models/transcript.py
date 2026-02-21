from pydantic import BaseModel
from datetime import datetime
from bson import ObjectId

class TranscriptBase(BaseModel):
    meeting_id: str
    user_id: str
    text: str
    timestamp: datetime

class TranscriptCreate(TranscriptBase):
    pass

class Transcript(TranscriptBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {ObjectId: str}
