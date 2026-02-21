"""
Meeting lifecycle APIs (Phase 1).
- POST /meetings/start-instant: start an instant meeting (manager only).
- POST /meetings/schedule: schedule a meeting (manager only).
- GET /meetings/{id}: get meeting by ID (authenticated).
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId

from app.core.config import settings
from app.core.database import get_database
from app.core.dependencies import (
    get_current_active_user,
    require_manager,
    verify_project_membership,
)
from app.models.meeting import (
    Meeting,
    MeetingCreateInstant,
    MeetingCreateSchedule,
    StartInstantResponse,
)
from app.models.user import User

router = APIRouter()


def _generate_room_name(project_id: str) -> str:
    """Generate unique Jitsi room name: mm-{projectId}-{uuid}."""
    return f"mm-{project_id}-{uuid.uuid4().hex[:12]}"


def _build_jitsi_url(room_name: str) -> str:
    """Build full Jitsi meeting URL from configured domain."""
    base = settings.JITSI_DOMAIN.rstrip("/")
    return f"{base}/{room_name}"


def _doc_to_meeting(doc: dict) -> Meeting:
    """Map MongoDB meeting document to Meeting model."""
    return Meeting(
        id=str(doc["_id"]),
        project_id=doc["project_id"],
        room_name=doc["room_name"],
        type=doc["type"],
        status=doc["status"],
        start_time=doc.get("start_time"),
        created_by=doc["created_by"],
        created_at=doc["created_at"],
    )


@router.post(
    "/start-instant",
    response_model=StartInstantResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Instant meeting started"},
        400: {"description": "Invalid project ID"},
        403: {"description": "Only managers can start instant meetings"},
        404: {"description": "Project not found"},
    },
)
async def start_instant_meeting(
    body: MeetingCreateInstant,
    current_user: User = Depends(require_manager),
) -> StartInstantResponse:
    """
    Start an instant meeting. Manager only.
    Creates a meeting with type=instant, status=live, and returns the Jitsi URL.
    """
    db = await get_database()

    # Validate project_id and ensure user has access
    try:
        ObjectId(body.project_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID",
        )
    await verify_project_membership(body.project_id, current_user)

    room_name = _generate_room_name(body.project_id)
    now = datetime.utcnow()

    meeting_doc = {
        "project_id": body.project_id,
        "room_name": room_name,
        "type": "instant",
        "status": "live",
        "start_time": now,
        "created_by": current_user.id,
        "created_at": now,
    }

    try:
        result = await db.meetings.insert_one(meeting_doc)
    except Exception as e:
        if "duplicate key" in str(e).lower() or "E11000" in str(e):
            # Collision on room_name; retry once with new name
            room_name = _generate_room_name(body.project_id)
            meeting_doc["room_name"] = room_name
            result = await db.meetings.insert_one(meeting_doc)
        else:
            raise

    meeting_id = str(result.inserted_id)
    jitsi_url = _build_jitsi_url(room_name)

    return StartInstantResponse(
        meeting_id=meeting_id,
        room_name=room_name,
        jitsi_url=jitsi_url,
    )


@router.post(
    "/schedule",
    response_model=Meeting,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Meeting scheduled"},
        400: {"description": "Invalid project ID or start_time"},
        403: {"description": "Only managers can schedule meetings"},
        404: {"description": "Project not found"},
    },
)
async def schedule_meeting(
    body: MeetingCreateSchedule,
    current_user: User = Depends(require_manager),
) -> Meeting:
    """
    Schedule a meeting. Manager only.
    Creates a meeting with type=scheduled, status=scheduled.
    """
    db = await get_database()

    try:
        ObjectId(body.project_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID",
        )
    await verify_project_membership(body.project_id, current_user)

    room_name = _generate_room_name(body.project_id)
    now = datetime.utcnow()

    meeting_doc = {
        "project_id": body.project_id,
        "room_name": room_name,
        "type": "scheduled",
        "status": "scheduled",
        "start_time": body.start_time,
        "created_by": current_user.id,
        "created_at": now,
    }

    try:
        result = await db.meetings.insert_one(meeting_doc)
    except Exception as e:
        if "duplicate key" in str(e).lower() or "E11000" in str(e):
            room_name = _generate_room_name(body.project_id)
            meeting_doc["room_name"] = room_name
            result = await db.meetings.insert_one(meeting_doc)
        else:
            raise

    meeting_doc["_id"] = result.inserted_id
    return _doc_to_meeting(meeting_doc)


@router.get(
    "/{meeting_id}",
    response_model=Meeting,
    responses={
        200: {"description": "Meeting details"},
        404: {"description": "Meeting not found"},
    },
)
async def get_meeting(
    meeting_id: str,
    current_user: User = Depends(get_current_active_user),
) -> Meeting:
    """Get meeting by ID. User must be a member of the meeting's project."""
    db = await get_database()

    try:
        oid = ObjectId(meeting_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid meeting ID",
        )

    meeting = await db.meetings.find_one({"_id": oid})
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )

    await verify_project_membership(meeting["project_id"], current_user)
    return _doc_to_meeting(meeting)
