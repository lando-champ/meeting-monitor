"""
Deterministic task effort estimation (hours + optional story points).

Uses keyword / complexity heuristics over title + description, dependency count,
and text length — no randomness, stable for the same inputs.
"""

from __future__ import annotations

import re
from typing import Any, Literal

EstimationSource = Literal["heuristic", "blended", "historical_adjusted"]


def parse_effort_value(raw: Any) -> float | None:
    """Parse a numeric effort from LLM or user input; None if missing/invalid."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        v = float(raw)
        return v if v > 0 else None
    text = str(raw).strip()
    if not text:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", text)
    if m:
        return float(m.group(1))
    return None


def _norm_text(*parts: str) -> str:
    return " ".join(p.lower() for p in parts if p).strip()


def _keyword_base_hours(text: str) -> float:
    """
    Highest-matching category wins (deterministic). Defaults to medium generic work.
    """
    t = text
    # (substrings, base_hours) — ordered coarse-to-fine; later tuples can override if we used max
    rules: tuple[tuple[tuple[str, ...], float], ...] = (
        (("research", "spike", "investigate", "evaluate", "compare"), 8.0),
        (("architecture", "rfc", "design doc", "technical design"), 10.0),
        (("schema", "migration", "database", "model", "entity"), 8.0),
        (("auth", "oauth", "jwt", "session", "permission", "rbac"), 12.0),
        (("api", "endpoint", "rest", "graphql", "grpc", "backend", "server"), 12.0),
        (("frontend", "ui", "react", "vue", "component", "css", "layout"), 10.0),
        (("integration", "webhook", "third-party", "stripe", "slack"), 14.0),
        (("deploy", "ci", "cd", "docker", "kubernetes", "pipeline"), 8.0),
        (("test", "e2e", "qa", "regression", "cypress", "playwright"), 8.0),
        (("bug", "fix", "hotfix", "patch"), 4.0),
        (("readme", "docs", "documentation", "markdown"), 3.0),
        (("refactor", "cleanup", "debt"), 8.0),
        (("performance", "optimize", "latency", "cache"), 10.0),
        (("security", "audit", "encryption", "csrf", "xss"), 10.0),
    )
    best = 6.0
    for keys, hours in rules:
        if any(k in t for k in keys):
            best = max(best, hours)
    return best


def _complexity_multipliers(text: str, desc_len: int, dep_count: int) -> float:
    """Scale base hours deterministically."""
    m = 1.0
    t = text

    # Integration surface
    m += min(0.35 * dep_count, 1.75)

    # Scope from description length
    if desc_len > 1200:
        m += 0.45
    elif desc_len > 600:
        m += 0.25
    elif desc_len > 200:
        m += 0.1

    # Explicit complexity words
    if any(w in t for w in ("simple", "minor", "small tweak")):
        m -= 0.15
    if any(w in t for w in ("complex", "large", "major", "critical", "enterprise")):
        m += 0.25

    return max(0.5, m)


def _priority_multiplier(priority: str) -> float:
    p = (priority or "medium").strip().lower()
    if p == "low":
        return 0.9
    if p == "high":
        return 1.15
    return 1.0


def estimate_task_effort_hours(task: dict[str, Any]) -> float:
    """
    Deterministic heuristic: estimated hours from title, description, dependencies, priority.

    Same task dict always yields the same float (for fixed inputs).
    """
    title = str(task.get("title") or "")
    desc = str(task.get("description") or "")
    blob = _norm_text(title, desc)
    dep_count = len(task.get("dependencies") or []) if isinstance(task.get("dependencies"), list) else 0

    base = _keyword_base_hours(blob)
    m = _complexity_multipliers(blob, len(desc), dep_count)
    pm = _priority_multiplier(str(task.get("priority") or "medium"))

    hours = base * m * pm
    # Clamp to practical planning range (sub-day to multi-week single task)
    hours = max(1.0, min(80.0, round(hours, 1)))
    return hours


def hours_to_story_points(hours: float) -> int:
    """Rough Fibonacci-like mapping from hours (deterministic)."""
    if hours <= 2:
        return 1
    if hours <= 4:
        return 2
    if hours <= 8:
        return 3
    if hours <= 13:
        return 5
    if hours <= 21:
        return 8
    return 13


def compute_task_estimated_effort(
    task: dict[str, Any],
    *,
    raw_llm_effort: Any = None,
    blend_llm_weight: float = 0.35,
    historical_anchor_hours: float | None = None,
    historical_anchor_weight: float = 0.28,
) -> tuple[float, EstimationSource, int]:
    """
    Final effort: blend LLM suggestion with heuristic when LLM value exists.

    - If no LLM effort: use heuristic only.
    - Else: ``blend_llm_weight * llm + (1 - blend_llm_weight) * heuristic``, rounded.
    - If ``historical_anchor_hours`` is set (e.g. median from retrieved similar tasks),
      blend it in deterministically to ground estimates in past delivery data.

    Returns (hours, source, story_points).
    """
    h = estimate_task_effort_hours(task)
    llm = parse_effort_value(raw_llm_effort)
    if llm is None:
        out = h
        source: EstimationSource = "heuristic"
    else:
        w = max(0.0, min(1.0, blend_llm_weight))
        out = w * llm + (1.0 - w) * h
        source = "blended"

    out = max(0.5, round(out, 1))
    out = min(120.0, out)

    if historical_anchor_hours is not None:
        ah = float(historical_anchor_hours)
        ah = max(0.5, min(120.0, ah))
        hw = max(0.0, min(0.55, historical_anchor_weight))
        out = max(0.5, round((1.0 - hw) * out + hw * ah, 1))
        out = min(120.0, out)
        source = "historical_adjusted"

    return out, source, hours_to_story_points(out)
