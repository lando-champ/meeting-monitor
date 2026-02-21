from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.core.database import get_database
from app.core.dependencies import get_current_user, verify_project_membership
from app.models.attendance import Attendance, AttendanceCreate, AttendanceUpdate
from app.models.user import User
from bson import ObjectId
from datetime import datetime

router = APIRouter()

@router.post("", response_model=Attendance, status_code=status.HTTP_201_CREATED)
async def join_meeting(
    attendance_data: AttendanceCreate,
    current_user: User = Depends(get_current_user)
):
    """Join a meeting (record attendance)"""
    db = await get_database()
    
    # Verify meeting exists and get project_id
    meeting = await db.meetings.find_one({"_id": ObjectId(attendance_data.meeting_id)})
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    # Verify project access
    await verify_project_membership(meeting["project_id"], current_user)
    
    # Check if attendance already exists
    existing = await db.attendance.find_one({
        "meeting_id": attendance_data.meeting_id,
        "user_id": current_user.id
    })
    
    if existing:
        # Update existing attendance if user rejoins
        await db.attendance.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "joined_at": attendance_data.joined_at,
                    "left_at": None,
                    "duration": None,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        updated = await db.attendance.find_one({"_id": existing["_id"]})
        return Attendance(
            id=str(updated["_id"]),
            **{k: v for k, v in updated.items() if k != "_id"}
        )
    
    # Create new attendance record
    attendance_dict = {
        "meeting_id": attendance_data.meeting_id,
        "user_id": current_user.id,
        "joined_at": attendance_data.joined_at,
        "left_at": None,
        "duration": None,
        "created_at": datetime.utcnow()
    }
    
    result = await db.attendance.insert_one(attendance_dict)
    attendance_dict["id"] = str(result.inserted_id)
    return Attendance(**attendance_dict)

@router.patch("/{attendance_id}", response_model=Attendance)
async def leave_meeting(
    attendance_id: str,
    attendance_update: AttendanceUpdate,
    current_user: User = Depends(get_current_user)
):
    """Leave a meeting (update attendance with leave time)"""
    db = await get_database()
    
    attendance = await db.attendance.find_one({"_id": ObjectId(attendance_id)})
    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found"
        )
    
    # Verify user owns this attendance record
    if attendance["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Calculate duration if both joined_at and left_at are present
    update_data = attendance_update.model_dump(exclude_unset=True)
    if attendance_update.left_at and attendance.get("joined_at"):
        duration = int((attendance_update.left_at - attendance["joined_at"]).total_seconds())
        update_data["duration"] = duration
    
    update_data["updated_at"] = datetime.utcnow()
    
    await db.attendance.update_one(
        {"_id": ObjectId(attendance_id)},
        {"$set": update_data}
    )
    
    updated = await db.attendance.find_one({"_id": ObjectId(attendance_id)})
    return Attendance(
        id=str(updated["_id"]),
        **{k: v for k, v in updated.items() if k != "_id"}
    )

@router.post("/meeting/{meeting_id}/join", response_model=Attendance)
async def join_meeting_by_id(
    meeting_id: str,
    current_user: User = Depends(get_current_user)
):
    """Join a meeting by meeting ID (convenience endpoint)"""
    db = await get_database()
    
    meeting = await db.meetings.find_one({"_id": ObjectId(meeting_id)})
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    await verify_project_membership(meeting["project_id"], current_user)
    
    # Check if attendance already exists
    existing = await db.attendance.find_one({
        "meeting_id": meeting_id,
        "user_id": current_user.id
    })
    
    if existing and not existing.get("left_at"):
        # User already in meeting
        return Attendance(
            id=str(existing["_id"]),
            **{k: v for k, v in existing.items() if k != "_id"}
        )
    
    # Create or update attendance
    attendance_dict = {
        "meeting_id": meeting_id,
        "user_id": current_user.id,
        "joined_at": datetime.utcnow(),
        "left_at": None,
        "duration": None,
        "created_at": datetime.utcnow()
    }
    
    if existing:
        await db.attendance.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "joined_at": attendance_dict["joined_at"],
                    "left_at": None,
                    "duration": None,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        updated = await db.attendance.find_one({"_id": existing["_id"]})
        return Attendance(
            id=str(updated["_id"]),
            **{k: v for k, v in updated.items() if k != "_id"}
        )
    else:
        result = await db.attendance.insert_one(attendance_dict)
        attendance_dict["id"] = str(result.inserted_id)
        return Attendance(**attendance_dict)

@router.post("/meeting/{meeting_id}/leave", response_model=Attendance)
async def leave_meeting_by_id(
    meeting_id: str,
    current_user: User = Depends(get_current_user)
):
    """Leave a meeting by meeting ID (convenience endpoint)"""
    db = await get_database()
    
    meeting = await db.meetings.find_one({"_id": ObjectId(meeting_id)})
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    await verify_project_membership(meeting["project_id"], current_user)
    
    attendance = await db.attendance.find_one({
        "meeting_id": meeting_id,
        "user_id": current_user.id
    })
    
    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found"
        )
    
    if attendance.get("left_at"):
        # Already left
        return Attendance(
            id=str(attendance["_id"]),
            **{k: v for k, v in attendance.items() if k != "_id"}
        )
    
    # Calculate duration
    left_at = datetime.utcnow()
    duration = None
    if attendance.get("joined_at"):
        duration = int((left_at - attendance["joined_at"]).total_seconds())
    
    await db.attendance.update_one(
        {"_id": attendance["_id"]},
        {
            "$set": {
                "left_at": left_at,
                "duration": duration,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    updated = await db.attendance.find_one({"_id": attendance["_id"]})
    return Attendance(
        id=str(updated["_id"]),
        **{k: v for k, v in updated.items() if k != "_id"}
    )

@router.get("/meeting/{meeting_id}", response_model=List[Attendance])
async def get_meeting_attendance(
    meeting_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get all attendance records for a meeting"""
    db = await get_database()
    
    meeting = await db.meetings.find_one({"_id": ObjectId(meeting_id)})
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    await verify_project_membership(meeting["project_id"], current_user)
    
    attendance_records = await db.attendance.find({
        "meeting_id": meeting_id
    }).sort("joined_at", 1).to_list(length=100)
    
    return [
        Attendance(
            id=str(a["_id"]),
            **{k: v for k, v in a.items() if k != "_id"}
        )
        for a in attendance_records
    ]
