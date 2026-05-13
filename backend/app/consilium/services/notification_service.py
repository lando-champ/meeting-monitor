from __future__ import annotations

"""
Notifications: in-memory dicts embedded on workspace documents.

Idempotency:
- create_notification() sets a stable dedupe_key (workspace_id|user_id|event_id) and
  deterministic id when those fields are present.
- filter_notifications_mongo_idempotent() claims keys in collection notification_dedupe
  (unique index on dedupe_key) before persist so duplicates are dropped at the DB layer.

MongoDB index (created by ensure_notification_dedupe_index):

    db.notification_dedupe.create_index(
        [("dedupe_key", 1)],
        unique=True,
        name="uniq_notification_dedupe_key",
    )
"""

from datetime import datetime, timezone
import hashlib
import logging
from typing import Any, Dict, List
import uuid

from pymongo.errors import DuplicateKeyError

from app.consilium.database import get_db

logger = logging.getLogger(__name__)

ACTIVITY_LOG_LIMIT = 20
NOTIFICATION_LIMIT = 30

NOTIFICATION_DEDUPE_COLLECTION = "notification_dedupe"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_notification_id(dedupe_key: str) -> str:
    return "n_" + hashlib.sha256(dedupe_key.encode("utf-8")).hexdigest()[:22]


def create_notification(
    user_id: str | None,
    message: str,
    notification_type: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    workspace_id = kwargs.get("workspace_id")
    event_id = kwargs.get("event_id")
    ws = str(workspace_id).strip() if workspace_id is not None else ""
    uid = str(user_id).strip() if user_id else ""
    eid = str(event_id).strip() if event_id else ""

    dedupe_key: str | None = None
    if ws and uid and eid:
        dedupe_key = f"{ws}|{uid}|{eid}"

    if dedupe_key:
        notif_id = _stable_notification_id(dedupe_key)
        kwargs = {**kwargs, "dedupe_key": dedupe_key}
    else:
        notif_id = str(uuid.uuid4())

    return {
        "id": notif_id,
        "user_id": user_id,
        "message": message,
        "type": notification_type,
        "read": False,
        "created_at": utc_now_iso(),
        **kwargs,
    }


def trim_notifications(notifications: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items = list(notifications)
    seen: set[str] = set()
    deduped_rev: List[Dict[str, Any]] = []
    for n in reversed(items):
        dk = n.get("dedupe_key")
        key = f"dk:{dk}" if dk else f"id:{n.get('id')}"
        if key in seen:
            continue
        seen.add(key)
        deduped_rev.append(n)
    deduped = list(reversed(deduped_rev))
    return deduped[-NOTIFICATION_LIMIT:]


async def ensure_notification_dedupe_index(db: Any) -> None:
    coll = db[NOTIFICATION_DEDUPE_COLLECTION]
    await coll.create_index(
        [("dedupe_key", 1)],
        unique=True,
        name="uniq_notification_dedupe_key",
    )


async def filter_notifications_mongo_idempotent(
    db: Any,
    workspace_id: str,
    notifications: List[Dict[str, Any]],
    *,
    existing_notifications: List[Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    """
    Drop notifications whose dedupe_key was already claimed in notification_dedupe
    (or already present on the workspace). Notifications without dedupe_key pass through.
    """
    coll = db[NOTIFICATION_DEDUPE_COLLECTION]
    already_on_workspace = {
        str(x["dedupe_key"])
        for x in (existing_notifications or [])
        if x.get("dedupe_key")
    }
    out: List[Dict[str, Any]] = []
    for n in notifications:
        dk = n.get("dedupe_key")
        if not dk:
            out.append(n)
            continue
        if dk in already_on_workspace:
            out.append(n)
            continue
        try:
            await coll.insert_one(
                {
                    "dedupe_key": dk,
                    "workspace_id": workspace_id,
                    "created_at": utc_now_iso(),
                }
            )
            out.append(n)
        except DuplicateKeyError:
            logger.info(
                "notification_dedupe_skip workspace_id=%s dedupe_key=%s",
                workspace_id,
                (dk[:80] + "...") if len(dk) > 80 else dk,
            )
    return out


def trim_activity_log(activity_log: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return list(activity_log)[-ACTIVITY_LOG_LIMIT:]


async def reset_workspace_signal_data_once() -> None:
    db = await get_db()
    flags = db["system_flags"]
    existing = await flags.find_one({"_id": "workspace-signal-reset-v1"})
    if existing:
        return

    workspaces = db["workspaces"]
    await workspaces.update_many(
        {},
        {
            "$set": {
                "activity_log": [],
                "risks": [],
                "notifications": [],
                "blockers": [],
                "github_events": [],
                "last_monitoring_hash": None,
                "last_risks_hash": None,
                "last_replan_hash": None,
            }
        },
    )

    users = db["users"]
    await users.update_many({}, {"$set": {"notifications": []}})

    await flags.insert_one({"_id": "workspace-signal-reset-v1", "completed_at": utc_now_iso()})
