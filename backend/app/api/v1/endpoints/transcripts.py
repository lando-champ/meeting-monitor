from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from app.core.database import get_database
from app.core.dependencies import get_current_user, verify_project_membership
from app.models.transcript import Transcript, TranscriptCreate
from app.models.user import User
from bson import ObjectId
from datetime import datetime

router = APIRouter()

@router.post("", response_model=Transcript, status_code=status.HTTP_201_CREATED)
async def create_transcript(
    transcript_data: TranscriptCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a transcript entry for a meeting"""
    db = await get_database()
    
    # Verify meeting exists and get project_id
    meeting = await db.meetings.find_one({"_id": ObjectId(transcript_data.meeting_id)})
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    # Verify project access
    await verify_project_membership(meeting["project_id"], current_user)
    
    transcript_dict = transcript_data.model_dump()
    transcript_dict["created_at"] = datetime.utcnow()
    
    result = await db.transcripts.insert_one(transcript_dict)
    transcript_dict["id"] = str(result.inserted_id)
    return Transcript(**transcript_dict)

@router.get("/meeting/{meeting_id}", response_model=List[Transcript])
async def get_meeting_transcripts(
    meeting_id: str,
    current_user: User = Depends(get_current_user),
    limit: Optional[int] = 1000
):
    """Get all transcripts for a meeting, ordered by timestamp"""
    db = await get_database()
    
    meeting = await db.meetings.find_one({"_id": ObjectId(meeting_id)})
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    await verify_project_membership(meeting["project_id"], current_user)
    
    transcripts = await db.transcripts.find({
        "meeting_id": meeting_id
    }).sort("timestamp", 1).to_list(length=limit)
    
    return [
        Transcript(
            id=str(t["_id"]),
            **{k: v for k, v in t.items() if k != "_id"}
        )
        for t in transcripts
    ]

@router.get("/meeting/{meeting_id}/full", response_model=str)
async def get_meeting_transcript_full(
    meeting_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get full transcript text for a meeting (concatenated)"""
    db = await get_database()
    
    meeting = await db.meetings.find_one({"_id": ObjectId(meeting_id)})
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    await verify_project_membership(meeting["project_id"], current_user)
    
    transcripts = await db.transcripts.find({
        "meeting_id": meeting_id
    }).sort("timestamp", 1).to_list(length=10000)
    
    # Get user names for better readability
    user_ids = list(set(t["user_id"] for t in transcripts))
    users = {}
    if user_ids:
        user_records = await db.users.find({"_id": {"$in": [ObjectId(uid) for uid in user_ids]}}).to_list(length=100)
        users = {str(u["_id"]): u.get("name", "Unknown") for u in user_records}
    
    # Format transcript
    full_text = []
    for t in transcripts:
        user_name = users.get(t["user_id"], "Unknown")
        timestamp_str = t["timestamp"].strftime("%H:%M:%S")
        full_text.append(f"[{timestamp_str}] {user_name}: {t['text']}")
    
    return "\n".join(full_text)

@router.delete("/{transcript_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transcript(
    transcript_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a transcript entry (admin/owner only)"""
    db = await get_database()
    
    transcript = await db.transcripts.find_one({"_id": ObjectId(transcript_id)})
    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found"
        )
    
    # Get meeting to verify project access
    meeting = await db.meetings.find_one({"_id": ObjectId(transcript["meeting_id"])})
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    await verify_project_membership(meeting["project_id"], current_user)
    
    # Only allow deletion if user is the creator or project owner
    project = await db.projects.find_one({"_id": ObjectId(meeting["project_id"])})
    if transcript["user_id"] != current_user.id and project.get("owner_id") != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    await db.transcripts.delete_one({"_id": ObjectId(transcript_id)})
    return None
