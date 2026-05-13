"""Versioned meeting signal documents for Consilium monitoring (report-aligned)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class MeetingSignalV1(BaseModel):
    """JSON-serializable signal emitted after post-meeting intelligence (or future sources)."""

    version: str = "1"
    project_id: str
    meeting_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed: bool = False
    confirmed_tasks: List[str] = Field(default_factory=list)
    blockers: List[Dict[str, Any]] = Field(default_factory=list)
    scope_mentions: List[str] = Field(default_factory=list)
    summary_excerpt: str = ""
    source: Literal["post_meeting_intelligence", "kanban_sync"] = "post_meeting_intelligence"
    id: Optional[str] = None

    def to_mongo(self) -> Dict[str, Any]:
        d = self.model_dump(exclude={"id"}, exclude_none=True)
        d["version"] = str(d.get("version") or "1")
        return d

    @classmethod
    def from_mongo(cls, doc: Dict[str, Any]) -> "MeetingSignalV1":
        d = dict(doc)
        oid = d.pop("_id", None)
        mid = str(oid) if oid is not None else None
        return cls(**{**d, "id": mid})
