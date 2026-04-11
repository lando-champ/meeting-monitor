"""GitHub webhook handling: map repo → project, parse task keys, CI (workflow_run), merge → DONE + git_evidence."""
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


def _workflow_name_allowed(name: str) -> bool:
    raw = (getattr(settings, "GITHUB_CI_WORKFLOW_NAME_ALLOWLIST", None) or "").strip()
    if not raw:
        return True
    allowed = {x.strip().lower() for x in raw.split(",") if x.strip()}
    return (name or "").strip().lower() in allowed


def _require_ci_for_done() -> bool:
    return bool(getattr(settings, "GITHUB_REQUIRE_CI_SUCCESS_FOR_DONE", False))


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


def _github_headers(token: str) -> Dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token.strip()}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def _github_get_pull(owner: str, repo: str, number: int, token: str) -> Optional[dict]:
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{int(number)}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers=_github_headers(token))
    except Exception as e:
        logger.warning("GitHub GET pull failed: %s", e)
        return None
    if r.status_code != 200:
        return None
    try:
        return r.json()
    except Exception:
        return None


async def _github_pr_merged_rest(owner: str, repo: str, number: int, token: str) -> Optional[bool]:
    pr = await _github_get_pull(owner, repo, number, token)
    if pr is None:
        return None
    return bool(pr.get("merged"))


async def _github_list_pulls_for_commit(
    owner: str, repo: str, commit_sha: str, token: str
) -> List[dict]:
    if not commit_sha:
        return []
    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_sha}/pulls"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers=_github_headers(token))
    except Exception as e:
        logger.warning("GitHub list pulls for commit failed: %s", e)
        return []
    if r.status_code != 200:
        return []
    try:
        data = r.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []


async def _resolve_pr_for_workflow_run(
    payload: dict, owner: str, repo: str, token: str
) -> Optional[dict]:
    """Full PR dict (title, body, merged, head, html_url, …) for task keys and merge checks."""
    wr = payload.get("workflow_run") or {}
    head_sha = (wr.get("head_sha") or "").strip()
    embedded = wr.get("pull_requests") or []
    if isinstance(embedded, list) and embedded:
        num = embedded[0].get("number")
        if isinstance(num, int) and token:
            pr = await _github_get_pull(owner, repo, num, token)
            if pr:
                return pr
    if token and head_sha:
        pulls = await _github_list_pulls_for_commit(owner, repo, head_sha, token)
        for p in pulls:
            num = p.get("number")
            if isinstance(num, int):
                pr = await _github_get_pull(owner, repo, num, token)
                if pr:
                    return pr
    return None


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
        if task.get("status") == "done":
            continue
        await db.tasks.update_one(
            {"_id": task["_id"]},
            {
                "$set": {
                    "status": "done",
                    "completed_at": now,
                    "updated_at": now,
                    "last_activity_at": now,
                },
                "$push": {"git_evidence": evidence},
            },
        )
        n += 1
    return n


async def _finalize_gated_merge(
    db,
    project_id: str,
    keys: List[str],
    pr: dict,
    merge_evidence: Dict[str, Any],
) -> int:
    """Mark DONE when CI success is recorded for this PR head SHA (skip if already done)."""
    head_sha = ((pr.get("head") or {}).get("sha") or "").strip()
    if not head_sha:
        return 0
    now = datetime.utcnow()
    n = 0
    for key in keys:
        k = (key or "").strip().upper()
        if not k:
            continue
        task = await db.tasks.find_one({"project_id": project_id, "task_key": k})
        if not task or task.get("status") == "done":
            continue
        if task.get("github_ci_conclusion") != "success":
            continue
        if (task.get("github_ci_head_sha") or "").strip() != head_sha:
            continue
        await db.tasks.update_one(
            {"_id": task["_id"]},
            {
                "$set": {
                    "status": "done",
                    "completed_at": now,
                    "updated_at": now,
                    "last_activity_at": now,
                },
                "$push": {"git_evidence": merge_evidence},
            },
        )
        n += 1
    return n


async def _apply_workflow_ci_to_tasks(
    db,
    project_id: str,
    keys: List[str],
    head_sha: str,
    conclusion: str,
    workflow_run_id: Optional[int],
    workflow_url: str,
    workflow_name: str,
    actor: str,
) -> None:
    now = datetime.utcnow()
    ev = _evidence(
        event="workflow_run",
        sha=head_sha,
        url=workflow_url,
        actor=actor,
        message=f"{workflow_name}: {conclusion}",
    )
    for key in keys:
        k = (key or "").strip().upper()
        if not k:
            continue
        task = await db.tasks.find_one({"project_id": project_id, "task_key": k})
        if not task:
            continue
        set_doc: Dict[str, Any] = {
            "github_ci_head_sha": head_sha,
            "github_ci_conclusion": conclusion,
            "github_ci_updated_at": now,
            "github_ci_workflow_url": workflow_url or "",
            "updated_at": now,
            "last_activity_at": now,
        }
        if workflow_run_id is not None:
            set_doc["github_ci_workflow_run_id"] = workflow_run_id
        upd: Dict[str, Any] = {"$set": set_doc, "$push": {"git_evidence": ev}}
        if conclusion == "failure" and task.get("status") != "done":
            set_doc["status"] = "blockers"
        await db.tasks.update_one({"_id": task["_id"]}, upd)


async def _handle_pull_request(db, payload: dict, project_id: str) -> Dict[str, Any]:
    pr = payload.get("pull_request") or {}
    action = (payload.get("action") or "").strip()
    if action != "closed":
        return {"ok": True, "skipped": "pr_not_closed"}
    merged = bool(pr.get("merged"))
    pat = (getattr(settings, "GITHUB_PAT", None) or "").strip()
    repo_name = _repo_full_name(payload)
    owner, repo = "", ""
    if repo_name and "/" in repo_name:
        owner, repo = repo_name.split("/", 1)
    if pat and owner and repo:
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
    merge_ev = _evidence(
        event="pull_request",
        sha=pr.get("merge_commit_sha") or pr.get("head", {}).get("sha"),
        url=pr.get("html_url"),
        actor=actor,
        message=title,
    )
    if not _require_ci_for_done():
        updated = await _mark_tasks_done(db, project_id, keys, merge_ev)
        return {"ok": True, "event": "pull_request", "keys": keys, "tasks_updated": updated}

    updated = await _finalize_gated_merge(db, project_id, keys, pr, merge_ev)
    return {
        "ok": True,
        "event": "pull_request",
        "keys": keys,
        "tasks_updated": updated,
        "ci_gate": True,
        "note": "merge_with_ci_gate" if updated else "no_tasks_met_ci_requirement",
    }


async def _handle_workflow_run(db, payload: dict, project_id: str) -> Dict[str, Any]:
    action = (payload.get("action") or "").strip()
    if action != "completed":
        return {"ok": True, "skipped": "workflow_run_not_completed"}
    wr = payload.get("workflow_run") or {}
    wf_name = (wr.get("name") or "").strip()
    if not _workflow_name_allowed(wf_name):
        return {"ok": True, "skipped": "workflow_name_not_allowlisted", "workflow": wf_name}
    conclusion = (wr.get("conclusion") or "").strip().lower()
    if not conclusion:
        return {"ok": True, "skipped": "no_conclusion"}
    head_sha = (wr.get("head_sha") or "").strip()
    if not head_sha:
        return {"ok": True, "skipped": "no_head_sha"}

    repo_name = _repo_full_name(payload)
    if not repo_name or "/" not in repo_name:
        return {"ok": True, "skipped": "no_repo"}
    owner, repo = repo_name.split("/", 1)
    pat = (getattr(settings, "GITHUB_PAT", None) or "").strip()

    pr = None
    if pat:
        pr = await _resolve_pr_for_workflow_run(payload, owner, repo, pat)
    if not pr:
        logger.info(
            "workflow_run: could not resolve PR for repo=%s head_sha=%s (PAT empty or no linked PR?)",
            repo_name,
            head_sha[:7],
        )
        return {"ok": True, "skipped": "no_pr_context_for_workflow"}

    pr_head = ((pr.get("head") or {}).get("sha") or "").strip()
    if pr_head and pr_head != head_sha:
        logger.warning(
            "workflow_run head_sha %s != PR head %s; using workflow head_sha for CI fields",
            head_sha[:7],
            pr_head[:7],
        )

    title = pr.get("title") or ""
    body = pr.get("body") or ""
    keys = extract_task_keys(f"{title}\n{body}")
    if not keys:
        return {"ok": True, "skipped": "no_task_keys_in_pr", "workflow": wf_name}

    wf_id = wr.get("id")
    wf_run_id = int(wf_id) if isinstance(wf_id, int) else None
    wf_url = (wr.get("html_url") or "").strip()
    actor_obj = wr.get("actor") or payload.get("sender") or {}
    actor = actor_obj.get("login") if isinstance(actor_obj, dict) else ""
    if not isinstance(actor, str):
        actor = ""

    if conclusion in ("success", "failure"):
        await _apply_workflow_ci_to_tasks(
            db,
            project_id,
            keys,
            head_sha,
            "success" if conclusion == "success" else "failure",
            wf_run_id,
            wf_url,
            wf_name,
            actor,
        )
    else:
        now = datetime.utcnow()
        ev = _evidence(
            event="workflow_run",
            sha=head_sha,
            url=wf_url,
            actor=actor,
            message=f"{wf_name}: {conclusion}",
        )
        for key in keys:
            k = (key or "").strip().upper()
            if not k:
                continue
            await db.tasks.update_one(
                {"project_id": project_id, "task_key": k},
                {
                    "$set": {
                        "github_ci_head_sha": head_sha,
                        "github_ci_conclusion": conclusion,
                        "github_ci_updated_at": now,
                        "github_ci_workflow_url": wf_url,
                        "github_ci_workflow_run_id": wf_run_id,
                        "updated_at": now,
                        "last_activity_at": now,
                    },
                    "$push": {"git_evidence": ev},
                },
            )

    extra: Dict[str, Any] = {
        "ok": True,
        "event": "workflow_run",
        "keys": keys,
        "conclusion": conclusion,
        "workflow": wf_name,
    }

    if conclusion == "success" and _require_ci_for_done() and pat:
        merge_ev = _evidence(
            event="pull_request",
            sha=pr.get("merge_commit_sha") or pr_head or head_sha,
            url=pr.get("html_url"),
            actor=actor,
            message=title,
        )
        done_n = await _finalize_gated_merge(db, project_id, keys, pr, merge_ev)
        extra["tasks_finalized_after_ci"] = done_n

    return extra


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
    if event == "workflow_run":
        result = await _handle_workflow_run(db, payload, project_id)
        return (result, None)
    if event == "push":
        result = await _handle_push(db, payload, project_id)
        return (result, None)

    return ({"ok": True, "skipped": "unsupported_event", "event": event}, None)
