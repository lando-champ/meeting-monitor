"""Lightweight checks for GitHub Kanban sync helpers (no Mongo)."""
from app.services.github_kanban_sync import _workflow_name_allowed


def test_workflow_allowlist_allows_any_when_empty():
    assert _workflow_name_allowed("CI") is True
    assert _workflow_name_allowed("") is True
