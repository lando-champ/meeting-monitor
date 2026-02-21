from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.core.database import get_database
from app.core.dependencies import get_current_user, verify_project_membership
from app.models.meeting import Meeting, MeetingCreate, MeetingUpdate
from app.models.user import User
from bson import ObjectId
from datetime import datetime

class MeetingSummaryUpdate(BaseModel):
    summary: Optional[Dict[str, Any]] = None
    action_items: Optional[List[str]] = None
    decisions: Optional[List[str]] = None

router = APIRouter()

@router.post("", response_model=Meeting, status_code=status.HTTP_201_CREATED)
async def create_meeting(meeting_data: MeetingCreate, current_user: User = Depends(get_current_user)):
    """Create a new meeting"""
    db = await get_database()
    
    # Verify project access
    await verify_project_membership(meeting_data.project_id, current_user)
    
    meeting_dict = meeting_data.model_dump()
    meeting_dict["status"] = "scheduled"
    meeting_dict["started_at"] = None
    meeting_dict["ended_at"] = None
    meeting_dict["created_at"] = datetime.utcnow()
    meeting_dict["updated_at"] = datetime.utcnow()
    
    result = await db.meetings.insert_one(meeting_dict)
    meeting_dict["id"] = str(result.inserted_id)
    return Meeting(**meeting_dict)

@router.get("", response_model=List[Meeting])
async def list_meetings(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """List meetings"""
    db = await get_database()
    query = {}
    
    if project_id:
        query["project_id"] = project_id
        # Verify access (will raise exception if not member)
        await verify_project_membership(project_id, current_user)
    
    if status:
        query["status"] = status
    
    meetings = await db.meetings.find(query).sort("start_time", -1).to_list(length=100)
    return [Meeting(id=str(m["_id"]), **{k: v for k, v in m.items() if k != "_id"}) for m in meetings]

@router.get("/{meeting_id}", response_model=Meeting)
async def get_meeting(meeting_id: str, current_user: User = Depends(get_current_user)):
    """Get meeting by ID"""
    db = await get_database()
    meeting = await db.meetings.find_one({"_id": ObjectId(meeting_id)})
    
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Verify project access
    await verify_project_membership(meeting["project_id"], current_user)
    
    return Meeting(id=str(meeting["_id"]), **{k: v for k, v in meeting.items() if k != "_id"})

@router.patch("/{meeting_id}", response_model=Meeting)
async def update_meeting(
    meeting_id: str,
    meeting_update: MeetingUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update meeting"""
    db = await get_database()
    meeting = await db.meetings.find_one({"_id": ObjectId(meeting_id)})
    
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Verify project access
    await verify_project_membership(meeting["project_id"], current_user)
    
    update_data = meeting_update.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    
    await db.meetings.update_one(
        {"_id": ObjectId(meeting_id)},
        {"$set": update_data}
    )
    
    updated = await db.meetings.find_one({"_id": ObjectId(meeting_id)})
    return Meeting(id=str(updated["_id"]), **{k: v for k, v in updated.items() if k != "_id"})

@router.post("/{meeting_id}/start", response_model=Meeting)
async def start_meeting(meeting_id: str, current_user: User = Depends(get_current_user)):
    """Start a meeting"""
    db = await get_database()
    meeting = await db.meetings.find_one({"_id": ObjectId(meeting_id)})
    
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Verify project access
    await verify_project_membership(meeting["project_id"], current_user)
    
    await db.meetings.update_one(
        {"_id": ObjectId(meeting_id)},
        {
            "$set": {
                "status": "live",
                "started_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    updated = await db.meetings.find_one({"_id": ObjectId(meeting_id)})
    return Meeting(id=str(updated["_id"]), **{k: v for k, v in updated.items() if k != "_id"})

@router.post("/{meeting_id}/end", response_model=Meeting)
async def end_meeting(meeting_id: str, current_user: User = Depends(get_current_user)):
    """End a meeting (triggers automation)"""
    db = await get_database()
    meeting = await db.meetings.find_one({"_id": ObjectId(meeting_id)})
    
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Verify project access
    await verify_project_membership(meeting["project_id"], current_user)
    
    await db.meetings.update_one(
        {"_id": ObjectId(meeting_id)},
        {
            "$set": {
                "status": "ended",
                "ended_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    # TODO: Trigger automation (transcript processing, summary generation, task creation)
    # This will be implemented in Step 7
    
    updated = await db.meetings.find_one({"_id": ObjectId(meeting_id)})
    return Meeting(id=str(updated["_id"]), **{k: v for k, v in updated.items() if k != "_id"})

@router.get("/{meeting_id}/details")
async def get_meeting_details(meeting_id: str, current_user: User = Depends(get_current_user)):
    """
    Get comprehensive meeting details including:
    - Meeting info
    - Attendance records
    - Transcripts
    - Related tasks
    - Summary and action items
    """
    db = await get_database()
    meeting = await db.meetings.find_one({"_id": ObjectId(meeting_id)})
    
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Verify project access
    await verify_project_membership(meeting["project_id"], current_user)
    
    # Get attendance records
    attendance_records = await db.attendance.find({
        "meeting_id": meeting_id
    }).sort("joined_at", 1).to_list(length=100)
    
    # Get user info for attendance
    user_ids = list(set(a["user_id"] for a in attendance_records))
    users = {}
    if user_ids:
        user_records = await db.users.find({
            "_id": {"$in": [ObjectId(uid) for uid in user_ids]}
        }).to_list(length=100)
        users = {
            str(u["_id"]): {
                "id": str(u["_id"]),
                "name": u.get("name", "Unknown"),
                "email": u.get("email", ""),
                "avatar": u.get("avatar")
            }
            for u in user_records
        }
    
    # Format attendance with user info
    attendance_list = []
    for a in attendance_records:
        user_info = users.get(a["user_id"], {})
        attendance_list.append({
            "id": str(a["_id"]),
            "user": user_info,
            "joined_at": a.get("joined_at"),
            "left_at": a.get("left_at"),
            "duration": a.get("duration")
        })
    
    # Get transcripts
    transcripts = await db.transcripts.find({
        "meeting_id": meeting_id
    }).sort("timestamp", 1).to_list(length=10000)
    
    # Format transcripts with user info
    transcript_list = []
    for t in transcripts:
        user_info = users.get(t["user_id"], {})
        transcript_list.append({
            "id": str(t["_id"]),
            "user": user_info,
            "text": t.get("text", ""),
            "timestamp": t.get("timestamp")
        })
    
    # Get related tasks
    tasks = await db.tasks.find({
        "source_meeting_id": meeting_id
    }).sort("created_at", -1).to_list(length=100)
    
    task_list = []
    for t in tasks:
        assignee_info = None
        if t.get("assignee_id"):
            assignee_info = users.get(t["assignee_id"])
        task_list.append({
            "id": str(t["_id"]),
            "title": t.get("title", ""),
            "description": t.get("description"),
            "status": t.get("status"),
            "priority": t.get("priority"),
            "assignee": assignee_info,
            "due_date": t.get("due_date"),
            "created_at": t.get("created_at")
        })
    
    return {
        "meeting": Meeting(id=str(meeting["_id"]), **{k: v for k, v in meeting.items() if k != "_id"}),
        "attendance": attendance_list,
        "transcripts": transcript_list,
        "tasks": task_list,
        "summary": meeting.get("summary"),
        "action_items": meeting.get("action_items", []),
        "decisions": meeting.get("decisions", [])
    }

@router.patch("/{meeting_id}/summary", response_model=Meeting)
async def update_meeting_summary(
    meeting_id: str,
    summary_update: MeetingSummaryUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update meeting summary, action items, and decisions"""
    db = await get_database()
    meeting = await db.meetings.find_one({"_id": ObjectId(meeting_id)})
    
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Verify project access
    await verify_project_membership(meeting["project_id"], current_user)
    
    update_data = summary_update.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    
    await db.meetings.update_one(
        {"_id": ObjectId(meeting_id)},
        {"$set": update_data}
    )
    
    updated = await db.meetings.find_one({"_id": ObjectId(meeting_id)})
    return Meeting(id=str(updated["_id"]), **{k: v for k, v in updated.items() if k != "_id"})
