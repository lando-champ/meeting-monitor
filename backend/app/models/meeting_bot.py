"""
Pydantic models for meeting bot: Meeting, AttendanceRecord, TranscriptSegment, Summary, ActionItem.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class Meeting(BaseModel):
    """Meeting metadata for bot lifecycle."""
    id: Optional[str] = None
    project_id: Optional[str] = None
    title: Optional[str] = None
    status: str = "scheduled"  # scheduled | live | ended
    meeting_url: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class AttendanceRecord(BaseModel):
    """One join record: participant_id, join_time, leave_time."""
    meeting_id: str
    participant_id: str
    participant_name: str
    join_time: datetime
    leave_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    meeting_role: Optional[str] = None


class TranscriptSegment(BaseModel):
    """One segment of transcript (from Whisper)."""
    meeting_id: str
    speaker_id: Optional[str] = None
    text: str
    timestamp: datetime
    language: Optional[str] = None


class Summary(BaseModel):
    """Meeting summary from NLP."""
    meeting_id: str
    language: str = "en"
    summary_text: str
    summary_english: Optional[str] = None
    key_points: Optional[List[str]] = None
    created_at: Optional[datetime] = None


class ActionItem(BaseModel):
    """Action item extracted from transcript."""
    meeting_id: str
    text: str
    text_english: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None
    status: str = "pending"
    language: str = "en"
    created_at: Optional[datetime] = None
