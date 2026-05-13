from __future__ import annotations

from typing import Any, Dict, List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.consilium.database import get_db
from app.consilium.dependencies import get_current_user
from app.consilium.services.notification_service import trim_notifications


router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class GlobalNotificationsResponse(BaseModel):
    notifications: List[Dict[str, Any]]
    unread_count: int


@router.get("", response_model=GlobalNotificationsResponse, status_code=status.HTTP_200_OK)
async def get_notifications(current_user=Depends(get_current_user)) -> GlobalNotificationsResponse:
    db = await get_db()
    workspaces = db["workspaces"]
    user_id = str(current_user["_id"])

    cursor = workspaces.find(
        {
            "$or": [
                {"owner_id": user_id},
                {"members.user_id": user_id},
            ]
        },
        {"name": 1, "notifications": 1},
    )

    items: List[Dict[str, Any]] = []
    async for workspace in cursor:
        workspace_name = workspace.get("name") or "Workspace"
        for notification in workspace.get("notifications") or []:
            if notification.get("user_id") not in (None, "", user_id):
                continue
            items.append({**notification, "workspace_name": workspace_name, "workspace_id": str(workspace["_id"])})

    items = sorted(items, key=lambda item: item.get("created_at", ""), reverse=True)
    items = trim_notifications(items)
    unread_count = sum(1 for item in items if not item.get("read"))
    return GlobalNotificationsResponse(notifications=items, unread_count=unread_count)


@router.post("/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notifications_read(current_user=Depends(get_current_user)) -> None:
    db = await get_db()
    workspaces = db["workspaces"]
    user_id = str(current_user["_id"])

    cursor = workspaces.find(
        {
            "$or": [
                {"owner_id": user_id},
                {"members.user_id": user_id},
            ]
        },
        {"notifications": 1},
    )

    async for workspace in cursor:
        notifications = list(workspace.get("notifications") or [])
        changed = False
        for notification in notifications:
            if notification.get("user_id") not in (None, "", user_id):
                continue
            if not notification.get("read"):
                notification["read"] = True
                changed = True
        if changed:
            await workspaces.update_one({"_id": workspace["_id"]}, {"$set": {"notifications": notifications}})
