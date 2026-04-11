"""Stable per-task keys for Git commit/PR references (e.g. MM-A1B2C3D4)."""
from __future__ import annotations

import re
from typing import List, Optional, Set

from bson import ObjectId

from app.core.config import settings


def task_key_prefix() -> str:
    p = (getattr(settings, "GITHUB_TASK_KEY_PREFIX", "MM") or "MM").strip().upper()
    return re.sub(r"[^A-Z0-9]", "", p) or "MM"


def generate_task_key(oid: ObjectId) -> str:
    """Deterministic key from ObjectId (last 8 hex chars, uppercase)."""
    h = str(oid).replace("-", "")[-8:].upper()
    return f"{task_key_prefix()}-{h}"


def task_key_pattern() -> re.Pattern:
    pref = re.escape(task_key_prefix())
    # 8 hex (default) or longer collision form (full ObjectId hex)
    return re.compile(rf"\b{pref}-[A-F0-9]{{8,32}}\b", re.IGNORECASE)


def extract_task_keys(text: str) -> List[str]:
    if not (text or "").strip():
        return []
    pat = task_key_pattern()
    seen: Set[str] = set()
    out: List[str] = []
    for m in pat.finditer(text):
        raw = m.group(0).upper()
        if raw not in seen:
            seen.add(raw)
            out.append(raw)
    return out


async def ensure_task_key_persisted(db, task_doc: dict) -> str:
    """Set task_key on document if missing; return canonical key."""
    oid = task_doc.get("_id")
    if oid is None:
        raise ValueError("task_doc missing _id")
    existing = (task_doc.get("task_key") or "").strip()
    if existing:
        return existing.upper()
    pid = str(task_doc.get("project_id") or "")
    key = generate_task_key(oid)
    if await db.tasks.find_one({"project_id": pid, "task_key": key, "_id": {"$ne": oid}}):
        key = f"{task_key_prefix()}-{str(oid).replace('-', '').upper()}"
    await db.tasks.update_one({"_id": oid}, {"$set": {"task_key": key}})
    return key
