"""GitHub webhook handling: map repo → project, parse task keys, mark tasks done + git_evidence."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.services.task_key import extract_task_keys

logger = logging.getLogger(__name__)

_DONE_KW = re.compile(r"(?i)\b(fix|closes|complete|done)\b")


def verify_github_signature(body: bytes, signature_header: str) -> bool:
    secret = (getattr(settings, "GITHUB_WEBHOOK_SECRET", None) or "").strip()
    if not secret:
        return False
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    want = signature_header.split("=", 1)[1].strip()
    mac = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, want)


def _repo_full_name(payload: dict) -> str:
    repo = payload.get("repository") or {}
    return (repo.get("full_name") or "").strip().lower()


async def _find_project(db, repo_full: str) -> Optional[dict]:
    if not repo_full:
        return None
    return await db.projects.find_one(
        {
            "github_full_name": repo_full,
            "github_webhook_enabled": True,
        }
    )


async def _delivery_seen(db, delivery_id: Optional[str]) -> bool:
    if not delivery_id or not str(delivery_id).strip():
        return False
    try:
        await db.github_webhook_deliveries.insert_one(
            {"_id": delivery_id, "received_at": datetime.utcnow()}
        )
        return False
    except DuplicateKeyError:
        return True


async def _github_pr_merged_rest(owner: str, repo: str, number: int, token: str) -> Optional[bool]:
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{int(number)}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token.strip()}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers=headers)
    except Exception as e:
        logger.warning("GitHub PAT PR fetch failed: %s", e)
        return None
    if r.status_code != 200:
        logger.warning("GitHub PAT PR fetch HTTP %s", r.status_code)
        return None
    try:
        data = r.json()
    except Exception:
        return None
    return bool(data.get("merged"))


async def _mark_tasks_done(
    db,
    project_id: str,
    keys: List[str],
    evidence: Dict[str, Any],
) -> int:
    now = datetime.utcnow()
    n = 0
    for key in keys:
        k = (key or "").strip().upper()
        if not k:
            continue
        task = await db.tasks.find_one({"project_id": project_id, "task_key": k})
        if not task:
            continue
        await db.tasks.update_one(
            {"_id": task["_id"]},
            {
                "$set": {
                    "status": "done",
                    "completed_at": now,
                    "updated_at": now,
                },
                "$push": {"git_evidence": evidence},
            },
        )
        n += 1
    return n


def _evidence(
    *,
    event: str,
    sha: Optional[str],
    url: Optional[str],
    actor: str,
    message: str,
) -> Dict[str, Any]:
    return {
        "source": "github",
        "event": event,
        "sha": sha or "",
        "url": url or "",
        "actor": actor or "",
        "at": datetime.utcnow().isoformat() + "Z",
        "message": (message or "")[:2000],
    }


async def _handle_pull_request(db, payload: dict, project_id: str) -> Dict[str, Any]:
    pr = payload.get("pull_request") or {}
    action = (payload.get("action") or "").strip()
    if action != "closed":
        return {"ok": True, "skipped": "pr_not_closed"}
    merged = bool(pr.get("merged"))
    pat = (getattr(settings, "GITHUB_PAT", None) or "").strip()
    repo_name = _repo_full_name(payload)
    if pat and repo_name and "/" in repo_name:
        owner, repo = repo_name.split("/", 1)
        num = pr.get("number")
        if isinstance(num, int):
            api_merged = await _github_pr_merged_rest(owner, repo, num, pat)
            if api_merged is False:
                merged = False
            elif api_merged is True:
                merged = True
    if not merged:
        return {"ok": True, "skipped": "pr_not_merged"}
    title = pr.get("title") or ""
    body = pr.get("body") or ""
    text = f"{title}\n{body}"
    keys = extract_task_keys(text)
    if not keys:
        return {"ok": True, "skipped": "no_task_keys_in_pr"}
    actor = (payload.get("sender") or {}).get("login") or ""
    ev = _evidence(
        event="pull_request",
        sha=pr.get("merge_commit_sha") or pr.get("head", {}).get("sha"),
        url=pr.get("html_url"),
        actor=actor,
        message=title,
    )
    updated = await _mark_tasks_done(db, project_id, keys, ev)
    return {"ok": True, "event": "pull_request", "keys": keys, "tasks_updated": updated}


async def _handle_push(db, payload: dict, project_id: str) -> Dict[str, Any]:
    if bool(getattr(settings, "GITHUB_REQUIRE_PR_MERGE_FOR_DONE", True)):
        return {"ok": True, "skipped": "push_ignored_require_pr_merge"}
    repo = payload.get("repository") or {}
    default = (repo.get("default_branch") or "main").strip()
    ref = (payload.get("ref") or "").strip()
    if ref != f"refs/heads/{default}":
        return {"ok": True, "skipped": "push_not_default_branch"}
    actor = (payload.get("pusher") or {}).get("name") or (payload.get("sender") or {}).get("login") or ""
    updated_total = 0
    keys_hit: List[str] = []
    for c in payload.get("commits") or []:
        msg = c.get("message") or ""
        if not _DONE_KW.search(msg):
            continue
        keys = extract_task_keys(msg)
        if not keys:
            continue
        ev = _evidence(
            event="push",
            sha=c.get("id"),
            url=c.get("url"),
            actor=actor,
            message=msg.split("\n", 1)[0].strip(),
        )
        updated_total += await _mark_tasks_done(db, project_id, keys, ev)
        keys_hit.extend(keys)
    if not keys_hit:
        return {"ok": True, "skipped": "push_no_matching_commits"}
    return {"ok": True, "event": "push", "keys": keys_hit, "tasks_updated": updated_total}


async def handle_github_webhook(
    db,
    body: bytes,
    headers: Dict[str, str],
) -> Tuple[Dict[str, Any], Optional[int]]:
    """
    Verify signature, dedupe by X-GitHub-Delivery, run handler. Returns (result_dict, http_error_code).
    http_error_code None means 200.
    """
    if not (getattr(settings, "GITHUB_WEBHOOK_SECRET", None) or "").strip():
        return ({"ok": False, "error": "webhook_secret_not_configured"}, 503)

    sig = headers.get("x-hub-signature-256") or headers.get("X-Hub-Signature-256") or ""
    if not verify_github_signature(body, sig):
        return ({"ok": False, "error": "invalid_signature"}, 403)

    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        return ({"ok": False, "error": "invalid_json"}, 400)

    delivery = headers.get("x-github-delivery") or headers.get("X-GitHub-Delivery") or ""
    if await _delivery_seen(db, delivery or None):
        return ({"ok": True, "skipped": "duplicate_delivery"}, None)

    event = (headers.get("x-github-event") or headers.get("X-GitHub-Event") or "").strip()
    if event == "ping":
        return ({"ok": True, "event": "ping"}, None)

    repo_full = _repo_full_name(payload)
    proj = await _find_project(db, repo_full)
    if not proj:
        logger.info("GitHub webhook: no mapped project for repo=%s", repo_full)
        return ({"ok": True, "skipped": "no_project_for_repo", "repo": repo_full}, None)

    project_id = str(proj["_id"])

    if event == "pull_request":
        result = await _handle_pull_request(db, payload, project_id)
        return (result, None)
    if event == "push":
        result = await _handle_push(db, payload, project_id)
        return (result, None)

    return ({"ok": True, "skipped": "unsupported_event", "event": event}, None)
