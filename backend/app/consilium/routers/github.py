from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
import asyncio

import httpx
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from pydantic import BaseModel

from app.core.config import settings
from app.consilium.database import get_db
from app.consilium.dependencies import get_current_user
from app.consilium.agents.monitoring_agent import (
    fetch_github_activity,
    build_activity_events,
)
from app.consilium.agents.graph import run_graph_for_workspace
from app.services.github_kanban_sync import handle_github_webhook


router = APIRouter(prefix="/api", tags=["github"])


@router.get("/github/connect")
async def github_connect(workspace_id: str):
    """
    Redirect the user to GitHub OAuth for repository access.
    """
    if not (settings.GITHUB_CLIENT_ID and settings.GITHUB_REDIRECT_URI):
        raise HTTPException(
            status_code=503,
            detail="GitHub OAuth is not configured. Set GITHUB_CLIENT_ID and GITHUB_REDIRECT_URI in backend .env (create an OAuth App at https://github.com/settings/developers).",
        )

    # Basic state carrying workspace id; in production, add CSRF protection
    state = workspace_id
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_REDIRECT_URI,
        "scope": "repo read:user",
        "state": state,
    }
    url = "https://github.com/login/oauth/authorize?" + urlencode(params)
    return RedirectResponse(url)


@router.get("/github/callback")
async def github_callback(code: str, state: str):
    """
    OAuth callback from GitHub. Exchanges code for access token and stores it
    on the workspace document.
    """
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="GitHub OAuth is not configured on the server",
        )

    workspace_id = state
    try:
        oid = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid workspace id in state")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_REDIRECT_URI,
            },
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to obtain access token")

        # Fetch basic user info
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_resp.raise_for_status()
        user = user_resp.json()

    db = await get_db()
    workspaces = db["workspaces"]
    await workspaces.update_one(
        {"_id": oid},
        {
            "$set": {
                "github": {
                    "access_token": access_token,
                    "user_login": user.get("login"),
                }
            }
        },
    )

    # Redirect to frontend (same origin as the app), not the API
    workspace_doc = await workspaces.find_one({"_id": oid}, {"project_id": 1})
    redirect_workspace_id = (
        str(workspace_doc.get("project_id"))
        if workspace_doc and workspace_doc.get("project_id")
        else workspace_id
    )
    base = (settings.FRONTEND_URL or "").rstrip("/")
    redirect_url = (
        f"{base}/business/manager/workspaces/{redirect_workspace_id}/integrations?github=connected"
    )
    return RedirectResponse(redirect_url)


async def _get_workspace_and_github(workspace_id: str) -> Dict[str, Any]:
    db = await get_db()
    workspaces = db["workspaces"]
    try:
        oid = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid workspace id")

    workspace = await workspaces.find_one({"_id": oid})
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    github = workspace.get("github") or {}
    token = github.get("access_token")
    if not token:
        raise HTTPException(
            status_code=400, detail="GitHub is not connected for this workspace"
        )
    return {"workspace": workspace, "github": github, "token": token, "oid": oid}


@router.get("/workspaces/{workspace_id}/github/repos")
async def list_github_repos(
    workspace_id: str, current_user=Depends(get_current_user)
) -> List[Dict[str, Any]]:
    ctx = await _get_workspace_and_github(workspace_id)
    token = ctx["token"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        repos = resp.json()

    # Return a trimmed representation
    return [
        {
            "id": r.get("id"),
            "name": r.get("name"),
            "full_name": r.get("full_name"),
            "owner": r.get("owner", {}).get("login"),
            "private": r.get("private"),
        }
        for r in repos
    ]


class RepoSelection(BaseModel):  # type: ignore[name-defined]
    owner: str
    name: str


@router.post("/workspaces/{workspace_id}/github/repo")
async def select_github_repo(
    workspace_id: str,
    payload: RepoSelection,
    current_user=Depends(get_current_user),
):
    ctx = await _get_workspace_and_github(workspace_id)
    oid = ctx["oid"]
    token = ctx["token"]

    async with httpx.AsyncClient() as client:
        repo_resp = await client.get(
            f"https://api.github.com/repos/{payload.owner}/{payload.name}",
            headers={"Authorization": f"Bearer {token}"},
        )
        repo_resp.raise_for_status()
        repo = repo_resp.json()

    db = await get_db()
    workspaces = db["workspaces"]
    await workspaces.update_one(
        {"_id": oid},
        {
            "$set": {
                "github.repo_owner": payload.owner,
                "github.repo_name": payload.name,
                "github.repo_full_name": repo.get("full_name"),
                "github.stars": repo.get("stargazers_count"),
                "github.forks": repo.get("forks_count"),
            }
        },
    )

    return {"status": "ok"}


@router.post("/workspaces/{workspace_id}/github/sync-issues")
async def sync_github_issues(
    workspace_id: str,
    current_user=Depends(get_current_user),
):
    ctx = await _get_workspace_and_github(workspace_id)
    workspace = ctx["workspace"]
    oid = ctx["oid"]
    token = ctx["token"]
    github = ctx["github"]

    owner = github.get("repo_owner")
    repo = github.get("repo_name")
    if not owner or not repo:
        raise HTTPException(
            status_code=400, detail="No GitHub repository selected for this workspace"
        )

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/issues",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        issues = resp.json()

    members = workspace.get("members") or []
    member_ids = [m.get("user_id") for m in members if m.get("user_id")]

    tasks: List[Dict[str, Any]] = workspace.get("tasks") or []

    for issue in issues:
        if "pull_request" in issue:
            # skip PRs here
            continue
        title = issue.get("title") or ""
        body = issue.get("body") or ""
        assignee = issue.get("assignee") or {}
        assignee_login = assignee.get("login")

        status = "done" if issue.get("state") == "closed" else "todo"

        assigned_to: Optional[str] = None
        if assignee_login:
            # naive mapping: match by email-like field or store login only
            assigned_to = assignee_login

        tasks.append(
            {
                "title": title,
                "description": body,
                "assigned_to": assigned_to,
                "status": status,
                "github_issue_number": issue.get("number"),
                "github_issue_url": issue.get("html_url"),
            }
        )

    db = await get_db()
    workspaces = db["workspaces"]
    await workspaces.update_one(
        {"_id": oid},
        {"$set": {"tasks": tasks}},
    )

    return {"imported": len(issues)}


@router.get("/workspaces/{workspace_id}/github/activity")
async def github_activity(
    workspace_id: str,
    current_user=Depends(get_current_user),
):
    """
    Activity endpoint used by the UI and monitoring dashboards.

    - Uses the stored GitHub repo configuration from the workspace.
    - Fetches commits and pull requests via the monitoring agent (PyGithub).
    - Persists a generic activity timeline to workspace.activity.
    """
    db = await get_db()
    workspaces = db["workspaces"]
    try:
        oid = ObjectId(workspace_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid workspace id")

    workspace = await workspaces.find_one({"_id": oid})
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    github = workspace.get("github") or {}
    token = github.get("access_token")
    owner = github.get("repo_owner")
    repo = github.get("repo_name")

    # If not fully configured yet, just return an empty activity object
    if not token or not owner or not repo:
        return {"repo": None, "commits": [], "pulls": []}

    # Use monitoring agent (PyGithub) so logic is shared with background loop.
    # Call it in a worker thread so we don't block the event loop.
    repo_summary, commits, pull_requests = await asyncio.to_thread(
        fetch_github_activity, owner, repo, token
    )

    # Store generic activity timeline on the workspace for dashboards
    events = build_activity_events(commits, pull_requests)
    await workspaces.update_one(
        {"_id": oid},
        {
            "$set": {
                "github.repo_full_name": repo_summary.get("full_name"),
                "github.stars": repo_summary.get("stars"),
                "github.forks": repo_summary.get("forks"),
                "github.html_url": repo_summary.get("html_url"),
                "activity": events,
            }
        },
    )

    # Keep response backward-compatible with existing frontend (repo/commits/pulls),
    # while also making pull requests available under a clearer key if needed.
    return {
        "repo": repo_summary,
        "commits": commits[:10],
        "pulls": pull_requests[:10],
        "pull_requests": pull_requests[:10],
    }


@router.post("/github/webhook")
async def github_webhook(request: Request):
    """
    Compatibility webhook endpoint.
    Delegates to the canonical `/api/v1/webhooks/github` handler logic.
    """
    body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}
    db = await get_db()
    result, err = await handle_github_webhook(db, body, headers)
    if err:
        raise HTTPException(status_code=err, detail=result.get("error") or "Webhook error")

    project_id = str(result.get("project_id") or "").strip()
    consilium_events = result.get("consilium_events") or []
    if project_id and consilium_events:
        workspaces = db["workspaces"]
        cursor = workspaces.find({"project_id": project_id}, {"_id": 1})
        async for workspace in cursor:
            await run_graph_for_workspace(str(workspace["_id"]), github_events=consilium_events)

    return result


def _extract_github_events_from_webhook(event: str | None, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    if event == "push":
        events: List[Dict[str, Any]] = []
        for commit in payload.get("commits") or []:
            events.append(
                {
                    "id": f"github:commit:{(commit.get('id') or '')[:12]}",
                    "type": "commit",
                    "sha": (commit.get("id") or "")[:12],
                    "message": commit.get("message") or "",
                    "user": (commit.get("author") or {}).get("username") or (commit.get("author") or {}).get("name"),
                    "timestamp": commit.get("timestamp"),
                }
            )
        return events

    if event == "pull_request":
        pr = payload.get("pull_request") or {}
        return [
            {
                "id": f"github:pr:{pr.get('number')}:{'merged' if pr.get('merged') else pr.get('state')}",
                "type": "pull_request",
                "number": pr.get("number"),
                "title": pr.get("title"),
                "message": pr.get("title"),
                "user": (pr.get("user") or {}).get("login"),
                "state": pr.get("state"),
                "merged": pr.get("merged"),
                "timestamp": pr.get("updated_at") or pr.get("created_at"),
                "created_at": pr.get("created_at"),
                "closed_at": pr.get("closed_at"),
                "html_url": pr.get("html_url"),
            }
        ]

    return []
