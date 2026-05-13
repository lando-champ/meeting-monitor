from __future__ import annotations

import json
import re
import uuid
from collections import OrderedDict
from datetime import date, timedelta
from typing import Any, Dict, List, TypedDict

import httpx

from app.core.config import settings
from app.consilium.services.planning_validation import (
    break_cycles_greedy,
    build_edges_from_dependencies,
    strip_invalid_dependencies,
    validate_planning_graph,
)
from app.consilium.services.task_estimation import compute_task_estimated_effort


class PlanningState(TypedDict, total=False):
    prd: Dict[str, Any]
    plan: Dict[str, Any]


GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
REQUEST_TIMEOUT = 90.0
MIN_PLANNER_TASKS = 0
MAX_PLANNER_TASKS = 2


def _get_api_key() -> str:
    api_key = settings.GEMINI_API_KEY or settings.PLANNING_AGENT_KEY
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY or PLANNING_AGENT_KEY is not set")
    return api_key


def _extract_gemini_text(data: Dict[str, Any]) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        return ""
    first = candidates[0] if isinstance(candidates[0], dict) else {}
    content = first.get("content") if isinstance(first.get("content"), dict) else {}
    parts = content.get("parts") if isinstance(content.get("parts"), list) else []
    text_chunks = [str(p.get("text") or "") for p in parts if isinstance(p, dict)]
    return "\n".join(x for x in text_chunks if x).strip()


def _norm_title(title: str) -> str:
    return " ".join((title or "").lower().split())


def _role_text(member: Dict[str, Any]) -> str:
    raw_skills = member.get("skills") or []
    skills = raw_skills if isinstance(raw_skills, str) else " ".join(str(x) for x in raw_skills)
    return (
        f"{member.get('role') or ''} "
        f"{member.get('profile_role') or ''} "
        f"{member.get('job_role') or ''} "
        f"{member.get('title') or ''} "
        f"{skills}"
    ).lower()


def _is_manager(member: Dict[str, Any]) -> bool:
    role = str(member.get("role") or "").lower()
    return "manager" in role or "project manager" in role or role == "pm"


def _member_id(member: Dict[str, Any]) -> str:
    return str(member.get("user_id") or member.get("id") or "")


# ---------------------------------------------------------------------------
# ROOT CAUSE FIX 1: PRD feature cleaning
#
# The requirements agent produces features like:
#   "Face Recognition Attendance System: The SmartCampus AI uses AI-powered..."
#
# When these paragraph-length strings are used as task titles:
#   - Task cards show 500-char truncated titles
#   - The description template "Design, implement, and TEST the '...' feature"
#     contains the word "test" → EVERY task gets workstream="qa"
#   - qa workstream → every task assigned to Priya Nair (QA member)
#
# Fix: split on the first ":" to extract a clean name and a clean description
# before passing anything to the LLM or the fallback task builder.
# ---------------------------------------------------------------------------
def _extract_feature_name(raw: str) -> str:
    """Extract just the feature name from 'Name: description...' format."""
    raw = str(raw or "").strip()
    if ":" in raw:
        return raw.split(":")[0].strip()
    # Truncate at sentence boundary if no colon
    sentence_end = re.search(r"[.!?]", raw)
    if sentence_end and sentence_end.start() < 80:
        return raw[: sentence_end.start()].strip()
    return raw[:80].strip()


def _extract_feature_desc(raw: str) -> str:
    """Extract the description portion from 'Name: description...' format."""
    raw = str(raw or "").strip()
    if ":" in raw:
        desc = ":".join(raw.split(":")[1:]).strip()
        return desc if desc else raw
    return raw


def _simplify_task_title(raw_title: str, fallback: str) -> str:
    base = _extract_feature_name(str(raw_title or "").strip()) or fallback
    base = re.sub(r"\s+", " ", base).strip(" -_:,.;")
    lowered = base.lower()
    for prefix in ("implement build ", "build implement ", "implement ", "build ", "write tests for "):
        if lowered.startswith(prefix):
            base = base[len(prefix):].strip()
            lowered = base.lower()
    if not base:
        base = fallback
    if len(base) > 60:
        base = base[:60].rsplit(" ", 1)[0].strip() or base[:60].strip()
    return f"Implement {base}".strip()


def _clean_prd_features(prd: Dict[str, Any]) -> tuple[List[str], Dict[str, str]]:
    """
    Returns (clean_feature_names, name_to_description_map).
    Both are used to build the LLM prompt and the fallback task builder.
    """
    raw_features = prd.get("features") or prd.get("key_features") or []
    if not isinstance(raw_features, list):
        raw_features = []

    clean_names: List[str] = []
    name_to_desc: Dict[str, str] = {}

    for feat in raw_features:
        name = _extract_feature_name(str(feat))
        desc = _extract_feature_desc(str(feat))
        if name and name not in clean_names:
            clean_names.append(name)
            name_to_desc[name] = desc

    return clean_names, name_to_desc


# ---------------------------------------------------------------------------
# ROOT CAUSE FIX 2: Workstream detection on TITLE ONLY (not full text)
#
# The old version ran keyword detection on title + description + phase
# concatenated.  Since every fallback description was:
#   "Design, implement, and test the '<full paragraph>' feature."
# the word "test" appeared in EVERY task → everything classified as "qa".
#
# Fix: detect workstream from title only (the first 120 chars).
# The explicit `workstream` field from the LLM still takes precedence.
# ---------------------------------------------------------------------------
def _workstream_from_task(task: Dict[str, Any]) -> str:
    # 1. Trust an explicit workstream field set by the LLM
    explicit = str(task.get("workstream") or "").strip().lower()
    if explicit in ("backend", "frontend", "qa", "devops", "ai", "product", "management", "general"):
        return explicit

    # 2. Use TITLE only for keyword matching — not description
    #    (descriptions often contain "test", "ai", "backend" all at once)
    title = str(task.get("title") or "").lower()[:120]

    # QA / testing — only if the task is explicitly a test/QA task
    if any(k in title for k in (
        "write test", "e2e test", "unit test", "integration test", "qa ", "test suite",
        "test case", "automate test", "regression", "uat", "playwright", "cypress", "selenium",
    )):
        return "qa"

    # DevOps / infra
    if any(k in title for k in (
        "deploy", "ci/cd", "pipeline", "docker", "kubernetes", "k8s",
        "infra", "monitoring", "cloud setup", "server setup", "aws", "linux",
    )):
        return "devops"

    # AI / ML — only tasks that are doing ML work, not just using an AI feature
    if any(k in title for k in (
        "train model", "ml model", "inference", "face recognition model",
        "recommendation engine", "nlp pipeline", "embedding", "fine-tune",
        "data pipeline", "analytics engine",
    )):
        return "ai"

    # Frontend / UI
    if any(k in title for k in (
        "ui ", "frontend", "react", "screen", "component", "dashboard ui",
        "wireframe", "prototype", "design system", "mobile app", "interface",
        "admin panel ui", "notification ui", "attendance ui",
    )):
        return "frontend"

    # Management / product planning
    if any(k in title for k in (
        "project plan", "sprint plan", "stakeholder", "milestone",
        "resource allocation", "scrum", "backlog", "risk register",
    )):
        return "management"

    # Backend / API — broad match, comes after more specific ones
    if any(k in title for k in (
        "api", "backend", "schema", "migration", "database", "auth",
        "endpoint", "service", "webhook", "rest ", "graphql",
        "notification", "attendance", "tracking", "assignment", "report",
        "analytics", "data ", "storage", "cache",
    )):
        return "backend"

    # Product / research
    if any(k in title for k in (
        "user research", "user story", "acceptance criteria", "requirement",
        "discovery", "backlog refinement",
    )):
        return "product"

    return "general"


def _phase_rank(phase_name: str) -> int:
    p = (phase_name or "").lower()
    if any(k in p for k in ("foundation", "setup", "planning", "discovery", "requirements")):
        return 1
    if any(k in p for k in ("backend", "api", "core", "data")):
        return 2
    if any(k in p for k in ("frontend", "ui", "integration")):
        return 3
    if any(k in p for k in ("qa", "test", "hardening", "security")):
        return 4
    if any(k in p for k in ("release", "launch", "deployment")):
        return 5
    return 99


_STREAM_SKILL_KEYWORDS: Dict[str, tuple] = {
    "backend": ("backend", "api", "server", "python", "fastapi", "node", "flask", "database", "sql", "mysql", "mongodb", "rest", "graphql"),
    "frontend": ("frontend", "ui", "ux", "react", "typescript", "javascript", "html", "css", "web", "figma", "design"),
    "ai": ("ai", "ml", "machine learning", "openai", "nlp", "langchain", "tensorflow", "pytorch", "data analysis", "python"),
    "qa": ("qa", "test", "testing", "automation", "selenium", "cypress", "playwright", "pytest", "bug", "quality"),
    "devops": ("devops", "docker", "kubernetes", "k8s", "ci/cd", "aws", "linux", "deployment", "infra", "cloud"),
    "management": ("manager", "project manager", "pm", "scrum", "agile", "planning", "team leadership", "communication", "stakeholder"),
    "product": ("product", "agile", "scrum", "research", "strategy", "backlog", "jira", "user story"),
    "general": (),
}


def _score_member_for_workstream(
    member: Dict[str, Any],
    workstream: str,
    assignment_count: Dict[str, int],
) -> float:
    rt = _role_text(member)
    mid = _member_id(member)
    load = assignment_count.get(mid, 0)
    score = 0.0
    keywords = _STREAM_SKILL_KEYWORDS.get(workstream, ())
    matched = sum(1 for k in keywords if k in rt)
    score += matched * 10.0
    is_mgr = _is_manager(member)
    if workstream in ("management", "product"):
        score += 20.0 if is_mgr else -10.0
    elif workstream in ("backend", "frontend", "ai", "devops", "qa"):
        if is_mgr:
            score -= 15.0
    elif workstream == "general" and not is_mgr:
        score += 3.0
    score -= load * 3.0
    return score


def _pick_member_for_workstream(
    workstream: str,
    members: List[Dict[str, Any]],
    assignment_count: Dict[str, int],
) -> Dict[str, Any] | None:
    if not members:
        return None
    scored = [(_score_member_for_workstream(m, workstream, assignment_count), m) for m in members]
    scored.sort(key=lambda item: (-item[0], assignment_count.get(_member_id(item[1]), 0), _member_id(item[1])))
    best_score, best_member = scored[0]
    if best_score > -20:
        return best_member
    pool = [m for m in members if not _is_manager(m)] or list(members)
    pool.sort(key=lambda m: (assignment_count.get(_member_id(m), 0), _member_id(m)))
    return pool[0] if pool else None


def _pick_assignee(task: Dict[str, Any], members: List[Dict[str, Any]], idx: int) -> Dict[str, Any] | None:
    if not members:
        return None
    workstream = _workstream_from_task(task)
    keywords = _STREAM_SKILL_KEYWORDS.get(workstream, ())
    best_member: Dict[str, Any] | None = None
    best_score = -(10 ** 9)
    for member in members:
        rt = _role_text(member)
        score = sum(8 for k in keywords if k in rt)
        if workstream in ("backend", "frontend", "devops") and _is_manager(member):
            score -= 6
        if workstream == "management" and _is_manager(member):
            score += 10
        if score > best_score:
            best_score = score
            best_member = member
    if best_member is not None and best_score >= 0:
        return best_member
    pool = [m for m in members if not _is_manager(m)] or members
    return pool[idx % len(pool)]


def _synthesize_phases(prd: Dict[str, Any]) -> List[Dict[str, Any]]:
    clean_names, _ = _clean_prd_features(prd)
    if not clean_names:
        clean_names = ["Core MVP capability"]
    buckets: List[List[str]] = [[], [], [], []]
    for idx, name in enumerate(clean_names):
        buckets[idx % 4].append(name)
    phase_templates = [
        ("Phase 1", "Foundation & Setup", "Week 1 - Week 2"),
        ("Phase 2", "Core Backend", "Week 3 - Week 5"),
        ("Phase 3", "Core Frontend", "Week 6 - Week 8"),
        ("Phase 4", "QA & Release", "Week 9 - Week 12"),
    ]
    phases = []
    for (phase, title, date_range), items in zip(phase_templates, buckets):
        if items:
            phases.append({"phase": phase, "title": title, "date_range": date_range, "items": items})
    return phases or [{"phase": "Phase 1", "title": "Foundation & Setup", "date_range": "Week 1-2", "items": clean_names[:8]}]


def _normalize_priority(raw: Any) -> str:
    s = str(raw or "medium").strip().lower()
    return s if s in ("low", "medium", "high") else "medium"


def _normalize_status(raw: Any) -> str:
    s = str(raw or "todo").strip().lower()
    return s if s in ("todo", "in_progress", "done") else "todo"


def _sanitize_task_id(raw: str | None) -> str:
    base = re.sub(r"[^a-zA-Z0-9_\-]", "_", str(raw or "").strip())[:64]
    return base or f"t_{uuid.uuid4().hex[:10]}"


def _flatten_phases_from_plan(plan: Dict[str, Any]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    raw_phases = plan.get("phases")
    if not isinstance(raw_phases, list) or not raw_phases:
        return [], []
    phase_blocks: List[Dict[str, Any]] = []
    flat: List[Dict[str, Any]] = []
    for idx, ph in enumerate(raw_phases):
        if not isinstance(ph, dict):
            continue
        name = str(ph.get("name") or ph.get("title") or ph.get("phase") or f"Phase {idx + 1}")
        tasks = ph.get("tasks") or []
        if not isinstance(tasks, list):
            tasks = []
        normalized_tasks: List[Dict[str, Any]] = []
        for t in tasks:
            if isinstance(t, dict):
                t = dict(t)
                t["_phase_name"] = name
                normalized_tasks.append(t)
                flat.append(t)
        items = [str(x.get("title") or x) for x in normalized_tasks if isinstance(x, dict)]
        phase_blocks.append({"phase": f"Phase {idx + 1}", "title": name, "name": name,
                              "date_range": ph.get("date_range") or "", "items": items, "tasks": normalized_tasks})
    return phase_blocks, flat


def _merge_task_graph_from_plan(plan: Dict[str, Any]) -> Dict[str, Any] | None:
    tg = plan.get("task_graph")
    if not isinstance(tg, dict):
        return None
    return {"nodes": tg.get("nodes") or [], "edges": tg.get("edges") or []}


def _normalize_plan_output(
    prd: Dict[str, Any],
    plan: Dict[str, Any],
    members: List[Dict[str, Any]] | None = None,
    existing_tasks: List[Dict[str, Any]] | None = None,
    *,
    historical_title_norms: set[str] | None = None,
    historical_anchor_hours: float | None = None,
    history_meta: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    roadmap = plan.get("roadmap") or {}
    if not isinstance(roadmap, dict):
        roadmap = {}

    existing_titles = {_norm_title(t.get("title", "")) for t in (existing_tasks or []) if t.get("title")}
    blocked_titles = set(existing_titles)
    if historical_title_norms:
        blocked_titles |= {x for x in historical_title_norms if x}

    phase_blocks, phased_tasks = _flatten_phases_from_plan(plan)
    flat_from_plan = plan.get("tasks") or []
    if not isinstance(flat_from_plan, list):
        flat_from_plan = []

    tasks_raw = phased_tasks if phased_tasks else [dict(t) for t in flat_from_plan if isinstance(t, dict)]

    # -----------------------------------------------------------------------
    # Safe fallback task builder (simple mode)
    # - Keep roadmap tasks intentionally small and reviewable
    # - Generate concise action titles only
    # - Never force QA/frontend/backend triplets
    # -----------------------------------------------------------------------
    if not tasks_raw:
        clean_names, name_to_desc = _clean_prd_features(prd)
        tasks_raw = []
        for name in clean_names[:MAX_PLANNER_TASKS]:
            desc = name_to_desc.get(name, f"Implement and validate {name}.")
            tasks_raw.append({
                "title": _simplify_task_title(name, "MVP feature"),
                "description": str(desc).strip()[:220],
                "workstream": "general",
                "dependencies": [],
                "priority": "medium",
                "estimated_effort": 8.0,
                "status": "todo",
            })

    # Dedupe against existing tasks
    tasks_filtered = [
        t for t in tasks_raw
        if not (nt := _norm_title(str(t.get("title") or ""))) or nt not in blocked_titles
    ] or list(tasks_raw)
    tasks_filtered = tasks_filtered[:MAX_PLANNER_TASKS]

    phases = roadmap.get("phases") or []
    if not isinstance(phases, list) or not phases:
        phases = phase_blocks if phase_blocks else _synthesize_phases(prd)
    roadmap["phases"] = phases

    if history_meta:
        roadmap["planning_retrieval"] = {
            "retrieved_count": history_meta.get("retrieved_count", 0),
            "anchor_median_hours": history_meta.get("anchor_median_hours"),
            "historical_titles_considered": len(historical_title_norms or []),
        }

    base_deadline = date.today()
    phase_names = [
        ph.get("name") or ph.get("title") or ph.get("phase") or f"Phase {i + 1}"
        for i, ph in enumerate(roadmap.get("phases") or [])
    ] or ["Phase 1"]

    used_ids: set[str] = set()

    def _unique_id(candidate: str) -> str:
        tid = _sanitize_task_id(candidate)
        base = tid
        n = 0
        while tid in used_ids:
            n += 1
            tid = f"{base[:48]}_{n}"
        used_ids.add(tid)
        return tid

    assignment_count: Dict[str, int] = {}
    normalized_tasks: List[Dict[str, Any]] = []

    for idx, task in enumerate(tasks_filtered):
        normalized_task = dict(task)
        normalized_task["id"] = _unique_id(str(normalized_task.get("id") or f"t_{uuid.uuid4().hex[:10]}"))

        # -----------------------------------------------------------------------
        # ROOT CAUSE FIX 4: Title sanitization
        #
        # If the LLM still returns a paragraph-length title (e.g. because the
        # PRD features were not cleaned before being injected into the prompt),
        # extract the clean name here as a last resort.
        # -----------------------------------------------------------------------
        raw_title = str(normalized_task.get("title") or f"Task {idx + 1}")
        normalized_task["title"] = _simplify_task_title(raw_title, f"Task {idx + 1}")

        description = str(normalized_task.get("description") or "").strip()
        # -----------------------------------------------------------------------
        # ROOT CAUSE FIX 5: Remove "test" from the generic description fallback
        #
        # The old template was: "Design, implement, and test the '...' feature."
        # The word "test" caused workstream=qa for every task.
        # New template does NOT contain "test".
        # -----------------------------------------------------------------------
        if len(description) < 40 or description.startswith("Design, implement, and test"):
            workstream_hint = normalized_task.get("workstream") or _workstream_from_task(normalized_task)
            description_templates = {
                "backend": f"{normalized_task['title']}: implement REST API endpoints, data models, and business logic with proper error handling and auth.",
                "frontend": f"{normalized_task['title']}: implement UI screens, components, and API integration with responsive design.",
                "qa": f"{normalized_task['title']}: write unit, integration, and E2E tests covering happy paths, edge cases, and error states.",
                "devops": f"{normalized_task['title']}: configure infrastructure, CI/CD pipeline, and deployment scripts.",
                "ai": f"{normalized_task['title']}: develop, train, and evaluate the ML model with performance benchmarks.",
                "management": f"{normalized_task['title']}: plan, coordinate, and document project scope, timeline, and stakeholder alignment.",
                "product": f"{normalized_task['title']}: define requirements, acceptance criteria, and success metrics.",
            }
            description = description_templates.get(workstream_hint, f"{normalized_task['title']}: implement end-to-end with clear acceptance criteria and documentation.")
        normalized_task["description"] = description

        if not isinstance(normalized_task.get("acceptance_criteria"), list) or not normalized_task.get("acceptance_criteria"):
            normalized_task["acceptance_criteria"] = [
                "Implementation matches the PRD requirement and works end-to-end.",
                "Relevant automated or manual verification has been completed.",
                "Edge cases, errors, and role permissions are handled where applicable.",
            ]

        normalized_task["assigned_to"] = str(normalized_task.get("assigned_to") or "")
        normalized_task["status"] = _normalize_status(normalized_task.get("status"))
        normalized_task["deadline"] = str(
            normalized_task.get("deadline") or (base_deadline + timedelta(days=(idx + 1) * 7)).isoformat()
        )
        pn = normalized_task.pop("_phase_name", None)
        normalized_task["phase"] = str(normalized_task.get("phase") or pn or phase_names[idx % len(phase_names)])
        normalized_task["priority"] = _normalize_priority(normalized_task.get("priority"))
        normalized_task["_llm_effort_raw"] = normalized_task.get("estimated_effort")
        if normalized_task.get("estimated_duration") is not None:
            normalized_task["estimated_duration"] = str(normalized_task["estimated_duration"])
        deps = normalized_task.get("dependencies")
        normalized_task["dependencies"] = [str(d) for d in (deps if isinstance(deps, list) else []) if d is not None]

        workstream = _workstream_from_task(normalized_task)
        normalized_task["workstream"] = workstream
        assignee = _pick_member_for_workstream(workstream, members or [], assignment_count)
        if assignee is None and workstream == "general":
            assignee = _pick_assignee(normalized_task, members or [], idx)
        if assignee:
            assignee_id = str(assignee.get("user_id") or assignee.get("id") or "")
            normalized_task["assigned_to"] = assignee_id
            normalized_task["assigned_to_name"] = assignee.get("name")
            normalized_task["assigned_user_id"] = assignee_id
            normalized_task["assigned_to_role"] = (
                assignee.get("profile_role")
                or assignee.get("job_role")
                or assignee.get("title")
                or assignee.get("role")
            )
            assignment_count[assignee_id] = assignment_count.get(assignee_id, 0) + 1

        normalized_tasks.append(normalized_task)

    normalized_tasks = normalized_tasks[:MAX_PLANNER_TASKS]
    id_set = {t["id"] for t in normalized_tasks}
    title_to_id = {_norm_title(t["title"]): t["id"] for t in normalized_tasks}
    for t in normalized_tasks:
        fixed: List[str] = []
        for dep in t.get("dependencies") or []:
            ds = str(dep)
            if ds in id_set:
                fixed.append(ds)
            elif _norm_title(ds) in title_to_id:
                fixed.append(title_to_id[_norm_title(ds)])
        t["dependencies"] = list(dict.fromkeys(fixed))

    strip_invalid_dependencies(normalized_tasks)
    removed = break_cycles_greedy(normalized_tasks)
    if removed:
        roadmap.setdefault("planning_warnings", []).append(f"Removed {removed} cyclic dependency edge(s) to form a DAG.")

    for t in normalized_tasks:
        raw_llm = t.pop("_llm_effort_raw", None)
        eff, src, pts = compute_task_estimated_effort(t, raw_llm_effort=raw_llm, historical_anchor_hours=historical_anchor_hours)
        t["estimated_effort"] = eff
        t["estimation_source"] = src
        t["estimated_story_points"] = pts
        t["estimation_unit"] = "hours"

    edges = build_edges_from_dependencies(normalized_tasks)
    llm_graph = _merge_task_graph_from_plan(plan)
    if llm_graph and isinstance(llm_graph.get("edges"), list):
        llm_edges = []
        for e in llm_graph["edges"]:
            if not isinstance(e, dict):
                continue
            src_id, tgt = str(e.get("source", "")), str(e.get("target", ""))
            if src_id in id_set and tgt in id_set:
                llm_edges.append({"source": src_id, "target": tgt, "type": str(e.get("type") or "depends_on")})
        if len(llm_edges) >= len(edges):
            edges = llm_edges

    nodes = [{"id": t["id"], "title": t["title"], "phase": t.get("phase"), "priority": t.get("priority")} for t in normalized_tasks]
    task_graph = {"nodes": nodes, "edges": edges}

    errs, _ = validate_planning_graph(normalized_tasks, check_cycle=False)
    if errs:
        roadmap.setdefault("planning_validation_errors", []).extend(errs)

    phase_task_map: OrderedDict[str, List[Dict[str, Any]]] = OrderedDict()
    for t in normalized_tasks:
        pname = str(t.get("phase") or "General")
        phase_task_map.setdefault(pname, []).append(t)

    source_phases = roadmap.get("phases") if isinstance(roadmap.get("phases"), list) else []
    if not source_phases:
        source_phases = _synthesize_phases(prd)

    # Preserve full roadmap phase sequence even when initial tasks are capped.
    ordered_phase_names: List[str] = []
    source_phase_by_name: Dict[str, Dict[str, Any]] = {}
    for idx, ph in enumerate(source_phases):
        if not isinstance(ph, dict):
            continue
        nm = str(ph.get("name") or ph.get("title") or ph.get("phase") or f"Phase {idx + 1}").strip()
        if not nm:
            nm = f"Phase {idx + 1}"
        if nm not in source_phase_by_name:
            ordered_phase_names.append(nm)
            source_phase_by_name[nm] = ph
    for nm in phase_task_map.keys():
        if nm not in source_phase_by_name:
            ordered_phase_names.append(nm)
            source_phase_by_name[nm] = {"title": nm}

    rebuilt: List[Dict[str, Any]] = []
    milestone_tracker: List[Dict[str, str]] = []
    for i, name in enumerate(ordered_phase_names):
        ptasks = phase_task_map.get(name, [])
        src_phase = source_phase_by_name.get(name) or {}
        deadlines = sorted(str(x.get("deadline") or "") for x in ptasks if x.get("deadline"))
        phase_date_range = f"{deadlines[0]} -> {deadlines[-1]}" if deadlines else str(src_phase.get("date_range") or "")
        workstreams = sorted({_workstream_from_task(t) for t in ptasks})
        how = "Execute in dependency order with design/implementation/testing handoff. Each task includes acceptance validation before moving to next phase."
        owners = sorted(
            {
                str(x.get("assigned_to_name") or "Unassigned")
                for x in ptasks
                if x.get("title")
            }
        )
        stream_groups: Dict[str, List[str]] = {}
        for task in ptasks:
            stream = str(task.get("workstream") or "general")
            stream_groups.setdefault(stream, []).append(str(task.get("title") or "Untitled task"))
        streams = [
            {
                "stream": stream,
                "owner": owners[0] if owners else "Unassigned",
                "actions": titles[:4],
            }
            for stream, titles in sorted(stream_groups.items())
        ]
        deliverables = [pt["title"] for pt in ptasks[:6]]
        if not deliverables:
            src_deliverables = src_phase.get("deliverables")
            if isinstance(src_deliverables, list):
                deliverables = [str(x) for x in src_deliverables if str(x).strip()][:6]
        if not streams:
            src_streams = src_phase.get("streams")
            if isinstance(src_streams, list):
                streams = [s for s in src_streams if isinstance(s, dict)]
        if not owners:
            src_owners = src_phase.get("owners")
            if isinstance(src_owners, list):
                owners = [str(x) for x in src_owners if str(x).strip()]
        goal = f"Deliver {name} outcomes and prepare downstream phases with production-grade quality."
        rebuilt.append({
            "phase": str(src_phase.get("phase") or f"Phase {i + 1}"), "title": str(src_phase.get("title") or name), "name": name,
            "date_range": phase_date_range,
            "goal": str(src_phase.get("goal") or goal),
            "objective": str(src_phase.get("objective") or f"Complete {name} deliverables with production-ready quality."),
            "what_to_do": str(src_phase.get("what_to_do") or f"Deliver {len(ptasks)} scoped work item(s) for {name}."),
            "when_to_do": phase_date_range, "how_to_do": how, "how_to_execute": how,
            "workstreams": workstreams, "subtasks_count": len(ptasks),
            "owners": owners,
            "streams": streams,
            "deliverables": deliverables,
            "execution_notes": str(src_phase.get("execution_notes") or "Track dependency-critical tasks first, review risks weekly, and freeze scope before handoff."),
            "items": [pt["title"] for pt in ptasks] or [str(x) for x in (src_phase.get("items") or []) if str(x).strip()],
            "subtasks": ptasks, "tasks": ptasks,
        })
        milestone_tracker.append(
            {
                "milestone": f"M{i + 1}: {name}",
                "deliverable": deliverables[0] if deliverables else f"Phase {i + 1} completion",
                "primary_owner": owners[0] if owners else "Unassigned",
            }
        )
    roadmap["phases"] = rebuilt
    roadmap["milestone_tracker"] = milestone_tracker

    return {"roadmap": roadmap, "tasks": normalized_tasks, "task_graph": task_graph, "phases": roadmap.get("phases") or []}


def run_planning_agent(
    prd: Dict[str, Any],
    members: List[Dict[str, Any]] | None = None,
    existing_tasks: List[Dict[str, Any]] | None = None,
    *,
    history_context: str | None = None,
    historical_anchor_hours: float | None = None,
    historical_title_norms: set[str] | None = None,
    history_meta: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    api_key = _get_api_key()

    # -----------------------------------------------------------------------
    # ROOT CAUSE FIX 6: Clean the PRD BEFORE building the LLM prompt
    #
    # The old code passed prd directly as json.dumps(prd) — which included
    # paragraph-length feature strings. The LLM received features like:
    #   "AI-based Face Recognition: The SmartCampus AI uses AI-powered face
    #    recognition to automate... trained on 10,000 images..."
    # and produced one monolithic "Implement <paragraph>" task per feature.
    #
    # Now we:
    #   1. Extract clean short feature names
    #   2. Pass a cleaned PRD to the LLM with name + short desc separated
    #   3. Also pass the cleaned names/descs as a structured feature list
    # -----------------------------------------------------------------------
    clean_names, name_to_desc = _clean_prd_features(prd)

    # Build a cleaned copy of the PRD for the LLM
    prd_for_llm = dict(prd)
    if clean_names:
        prd_for_llm["features"] = clean_names          # short names only
        prd_for_llm["feature_descriptions"] = name_to_desc   # name → desc map

    existing_summary = ""
    if existing_tasks:
        lines = [f"- {t.get('title') or t.get('id')}" for t in existing_tasks[:40]]
        existing_summary = "Existing tasks already in the workspace (do NOT duplicate these):\n" + "\n".join(lines)

    team_summary = ""
    workstream_guide = ""
    if members:
        tlines = []
        for m in members[:30]:
            name = m.get("name") or "Unknown"
            role = m.get("role") or "member"
            skills = ", ".join(str(s) for s in (m.get("skills") or [])) or "none"
            tlines.append(f"- {name} | role: {role} | skills: {skills}")
        team_summary = "Team members:\n" + "\n".join(tlines)

        stream_hints: List[str] = []
        tmp_count: Dict[str, int] = {}
        for ws in ("management", "backend", "frontend", "qa", "devops", "ai", "product"):
            best = _pick_member_for_workstream(ws, members, tmp_count)
            if best:
                stream_hints.append(f"  {ws}: {best.get('name')} ({best.get('role')}, skills: {', '.join(str(s) for s in (best.get('skills') or [])[:3])})")
        if stream_hints:
            workstream_guide = "Best-fit member per workstream (use this to set the `workstream` field):\n" + "\n".join(stream_hints)

    system_prompt = """
You are a senior engineering lead producing only the first actionable roadmap tasks.

Return STRICT JSON only — no prose, no markdown fences.

Required JSON shape:
{
  "phases": [
    {
      "name": "Phase name",
      "tasks": [
        {
          "id": "unique_snake_case_id",
          "title": "Simple action title (max 60 chars)",
          "description": "One short sentence.",
          "workstream": "backend|frontend|qa|devops|management|ai|product",
          "dependencies": ["prerequisite_task_id"],
          "priority": "low|medium|high",
          "estimated_effort": <hours as number>,
          "status": "todo"
        }
      ]
    }
  ],
  "task_graph": {
    "nodes": [{"id": "string", "title": "string", "phase": "string", "priority": "string"}],
    "edges": [{"source": "prerequisite_id", "target": "dependent_id", "type": "depends_on"}]
  }
}

MANDATORY RULES:

1. TASK TITLES must be SHORT (under 80 chars) and start with an action verb.
   GOOD: "Build face recognition REST API"
   GOOD: "Implement attendance dashboard UI in React"
   GOOD: "Write E2E tests for attendance flow"
   BAD:  "Implement AI-based Face Recognition Attendance System: The SmartCampus..."

2. Generate MIN 0 and MAX 2 tasks total.
   - If the PRD does not provide enough clear scope, return zero tasks.
   - Do not expand one feature into backend/frontend/qa triplets.

3. WORKSTREAM must be exactly one of: backend | frontend | qa | devops | management | ai | product
   Set it based on the NATURE of the work, NOT the feature name.
   QA tasks must be for TEST WRITING work only — not general feature work.

4. Keep tasks simple and implementation-focused. Avoid long feature paragraphs.
   BAD: "Implement Build ... leverages ... strategic analytics ..."
   GOOD: "Implement deception detection API"

5. DEPENDENCY ORDER must be realistic:
   DB schema → APIs → UI → QA → Release

6. Use only phase labels "Phase 0" or "Phase 1" for initial tasks.
""".strip()

    user_parts = [json.dumps(prd_for_llm, indent=2)]
    if existing_summary:
        user_parts.append(existing_summary)
    if team_summary:
        user_parts.append(team_summary)
    if workstream_guide:
        user_parts.append(workstream_guide)
    if history_context:
        user_parts.append(history_context)

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": "\n\n".join(user_parts)}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 8192,
        },
    }
    url = f"{GEMINI_BASE_URL}/{GEMINI_MODEL}:generateContent"
    text = ""
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.post(
                f"{url}?key={api_key}",
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            text = _extract_gemini_text(data)
    except Exception:
        text = ""

    # Strip markdown fences if model wraps output
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)

    try:
        plan = json.loads(text)
    except json.JSONDecodeError:
        plan = {"phases": [], "task_graph": {"nodes": [], "edges": []}, "tasks": []}

    if not isinstance(plan, dict):
        plan = {"phases": [], "task_graph": {"nodes": [], "edges": []}, "tasks": []}

    if not plan.get("phases") and plan.get("roadmap"):
        r = plan["roadmap"]
        if isinstance(r, dict) and r.get("phases"):
            plan["phases"] = r["phases"]

    return _normalize_plan_output(
        prd,
        plan,
        members,
        existing_tasks=existing_tasks,
        historical_title_norms=historical_title_norms,
        historical_anchor_hours=historical_anchor_hours,
        history_meta=history_meta,
    )