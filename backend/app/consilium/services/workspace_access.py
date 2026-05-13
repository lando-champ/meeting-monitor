"""
Workspace membership and role resolution (admin / member / viewer).

Used by FastAPI dependencies before mutating workspace data or running agents.
Legacy roles stored on members (e.g. "manager") map to admin.
"""

from __future__ import annotations

from typing import Literal

WorkspaceRole = Literal["admin", "member", "viewer"]

ROLE_RANK: dict[WorkspaceRole, int] = {
    "viewer": 1,
    "member": 2,
    "admin": 3,
}


def is_workspace_member(workspace: dict, user_id: str) -> bool:
    """True if user is owner or listed in members."""
    uid = str(user_id)
    if str(workspace.get("owner_id") or "") == uid:
        return True
    return any(
        str(m.get("user_id") or m.get("id") or "") == uid
        for m in (workspace.get("members") or [])
    )


def _normalize_member_role(raw: object) -> WorkspaceRole:
    r = str(raw or "").strip().lower()
    if r in ("admin", "owner", "manager"):
        return "admin"
    if r == "viewer":
        return "viewer"
    if r in ("member", ""):
        return "member"
    return "member"


def resolve_effective_role(workspace: dict, user_id: str) -> WorkspaceRole | None:
    """
    Effective role for a user on this workspace document.
    Owner is always admin. Members use stored role with defaults.
    """
    if not is_workspace_member(workspace, user_id):
        return None
    uid = str(user_id)
    if str(workspace.get("owner_id") or "") == uid:
        return "admin"
    for m in workspace.get("members") or []:
        mid = str(m.get("user_id") or m.get("id") or "")
        if mid == uid:
            return _normalize_member_role(m.get("role"))
    return "member"


def meets_min_role(role: WorkspaceRole, minimum: WorkspaceRole) -> bool:
    return ROLE_RANK[role] >= ROLE_RANK[minimum]
