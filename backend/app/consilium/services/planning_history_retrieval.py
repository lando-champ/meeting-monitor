"""
RAG-style retrieval over historical workspace tasks for planning.

* Token-overlap / Jaccard scoring (deterministic, no embeddings required).
* Builds LLM context from top matches + median effort anchor for calibration.
* Supplies normalized titles to block near-duplicate planned tasks.
"""

from __future__ import annotations

import re
import statistics
from typing import Any

# Minimal English stopwords for lexical overlap (deterministic)
_STOPWORDS = frozenset(
    """
    a an the and or but in on at to for of as is was are were be been being
    it this that these those with from by into through over after before
    then than so if when while do does did done having have has had not no
    yes all any each every both few more most other some such only own same
    can could should would will just also about into through during including
    """.split()
)


def prd_to_search_text(prd: dict[str, Any]) -> str:
    """Flatten PRD fields into one searchable string."""
    parts: list[str] = []
    for key in ("overview", "problem_statement", "product_name", "name"):
        v = prd.get(key)
        if isinstance(v, str) and v.strip():
            parts.append(v)
    for key in ("features", "key_features", "user_stories", "functional_requirements"):
        v = prd.get(key)
        if isinstance(v, list):
            parts.extend(str(x) for x in v[:40] if x)
        elif isinstance(v, str):
            parts.append(v)
    return " ".join(parts)


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return {t for t in tokens if len(t) > 1 and t not in _STOPWORDS}


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _norm_title(title: str) -> str:
    return " ".join((title or "").lower().split())


def _task_effort_hours(task: dict[str, Any]) -> float | None:
    raw = task.get("estimated_effort")
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        v = float(raw)
        return v if v > 0 else None
    if raw is None:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", str(raw))
    if m:
        return float(m.group(1))
    return None


def _is_done_like(task: dict[str, Any]) -> bool:
    s = str(task.get("status") or "").lower()
    return s in ("done", "completed", "closed", "review")


async def retrieve_similar_task_evidence(
    db: Any,
    *,
    exclude_workspace_id: str | None,
    prd: dict[str, Any],
    top_k: int = 14,
    max_workspaces: int = 120,
) -> tuple[str, dict[str, Any]]:
    """
    Scan other workspaces' embedded tasks, rank by Jaccard(query, title+description).

    Returns
    -------
    context_block
        Text block for the planning LLM (retrieved evidence).
    meta
        ``anchor_median_hours`` (median effort of scored tasks that have hours),
        ``title_norms`` (normalized titles from top_k — used to skip duplicate plans),
        ``retrieved_count``, ``scores`` (optional debug).
    """
    query_text = prd_to_search_text(prd)
    q_tokens = _tokenize(query_text)
    meta: dict[str, Any] = {
        "anchor_median_hours": None,
        "title_norms": set(),
        "retrieved_count": 0,
        "scores": [],
    }

    if not q_tokens:
        return "", meta

    workspaces = db["workspaces"]
    cursor = workspaces.find(
        {},
        {"tasks": 1, "name": 1, "prd.overview": 1},
    ).limit(max_workspaces)

    candidates: list[tuple[float, dict[str, Any], str, str]] = []

    async for ws in cursor:
        wid = str(ws.get("_id", ""))
        if exclude_workspace_id and wid == str(exclude_workspace_id):
            continue
        ws_name = str(ws.get("name") or "Workspace")
        for t in ws.get("tasks") or []:
            if not isinstance(t, dict):
                continue
            title = str(t.get("title") or "")
            if not title.strip():
                continue
            desc = str(t.get("description") or "")
            doc_tokens = _tokenize(f"{title} {desc}")
            score = jaccard_similarity(q_tokens, doc_tokens)
            if score <= 0.0:
                continue
            candidates.append((score, t, ws_name, wid))

    candidates.sort(key=lambda x: (-x[0], x[2], str(x[1].get("title") or "")))
    top = candidates[:top_k]
    meta["retrieved_count"] = len(top)
    meta["scores"] = [round(x[0], 4) for x in top]

    efforts: list[float] = []
    lines: list[str] = []
    title_norms: set[str] = set()

    for score, t, ws_name, _wid in top:
        nt = _norm_title(str(t.get("title") or ""))
        if nt:
            title_norms.add(nt)
        eh = _task_effort_hours(t)
        if eh is not None:
            efforts.append(eh)
        status = t.get("status") or "unknown"
        desc_snip = (t.get("description") or "")[:160].replace("\n", " ")
        eff_s = f"~{eh:.1f}h" if eh is not None else "effort n/a"
        done_hint = " [completed]" if _is_done_like(t) else ""
        lines.append(
            f"- (similarity {score:.2f}) [{ws_name}] \"{t.get('title')}\" {eff_s}, status={status}{done_hint}: {desc_snip}"
        )

    meta["title_norms"] = title_norms
    if efforts:
        meta["anchor_median_hours"] = float(statistics.median(efforts))

    if not lines:
        return "", meta

    block = (
        "Retrieved similar tasks from other projects (lexical RAG — use to calibrate effort and avoid "
        "duplicating the same work items; do NOT copy titles verbatim; adapt to this PRD):\n"
        + "\n".join(lines)
    )
    return block, meta
