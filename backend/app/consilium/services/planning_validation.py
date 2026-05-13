"""
Validation and repair for dependency-aware task planning (DAG).

* dependencies: task T lists prerequisite task ids that must complete before T.
* Edges: source -> target means source blocks target (same as dependency edge).
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

REQUIRED_FIELDS = ("id", "title", "description", "dependencies", "priority", "estimated_effort", "status")


@dataclass
class DagValidationResult:
    """Result of :func:`validate_task_dependency_dag`."""

    valid: bool
    """True only if there are no errors (DAG is acyclic and dependencies are valid)."""

    errors: list[str] = field(default_factory=list)
    """Human-readable issues; empty when ``valid`` is True."""

    topological_order: list[str] | None = None
    """A topological ordering of task ids, or None if the graph is invalid or cyclic."""


def _build_adjacency(tasks: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Directed edge dep -> task for each dependency (prerequisite blocks dependent)."""
    adj: dict[str, list[str]] = defaultdict(list)
    for t in tasks:
        tid = str(t.get("id") or "")
        if not tid:
            continue
        for d in t.get("dependencies") or []:
            ds = str(d)
            if ds and ds != tid:
                adj[ds].append(tid)
    return dict(adj)


def find_dependency_cycle(tasks: list[dict[str, Any]]) -> list[str] | None:
    """
    If the dependency graph contains a directed cycle, return one cycle as a list of task ids
    (path repeats the first id at the end, e.g. ``['a','b','a']``). Otherwise return None.

    Only edges between existing task ids are considered (invalid ids are ignored here).
    """
    ids = {str(t.get("id") or "") for t in tasks if t.get("id")}
    if not ids:
        return None

    adj = _build_adjacency(tasks)
    # 0=white, 1=gray (on recursion stack), 2=black
    color: dict[str, int] = {i: 0 for i in ids}

    def dfs(u: str, stack: list[str]) -> list[str] | None:
        color[u] = 1
        stack.append(u)
        for v in adj.get(u, []):
            if v not in ids:
                continue
            if color[v] == 1:
                try:
                    i = stack.index(v)
                    return stack[i:] + [v]
                except ValueError:
                    return [u, v, u]
            if color[v] == 0:
                cyc = dfs(v, stack)
                if cyc is not None:
                    return cyc
        stack.pop()
        color[u] = 2
        return None

    for tid in sorted(ids):
        if color[tid] == 0:
            cyc = dfs(tid, [])
            if cyc is not None:
                return cyc
    return None


def validate_task_dependency_dag(tasks: list[dict[str, Any]]) -> DagValidationResult:
    """
    Validate that task ``dependencies`` form a **DAG** (no cycles) and only reference existing tasks.

    Does **not** require PRD fields like ``estimated_effort``; only ``id`` and ``dependencies`` matter
    for the graph. Missing ``dependencies`` is treated as an empty list.

    Returns
    -------
    DagValidationResult
        ``valid`` is True iff there are no errors. ``topological_order`` is set when valid.

    Example
    -------
    >>> tasks = [
    ...     {"id": "a", "dependencies": []},
    ...     {"id": "b", "dependencies": ["a"]},
    ... ]
    >>> r = validate_task_dependency_dag(tasks)
    >>> r.valid
    True
    >>> r.topological_order
    ['a', 'b']

    >>> bad = [
    ...     {"id": "a", "dependencies": ["b"]},
    ...     {"id": "b", "dependencies": ["a"]},
    ... ]
    >>> r2 = validate_task_dependency_dag(bad)
    >>> r2.valid
    False
    >>> bool(r2.errors)
    True
    """
    errors: list[str] = []

    if not tasks:
        return DagValidationResult(valid=True, errors=[], topological_order=[])

    # Duplicate ids
    seen: set[str] = set()
    dupes: set[str] = set()
    for t in tasks:
        tid = str(t.get("id") or "")
        if not tid:
            errors.append("Task with missing or empty id")
            continue
        if tid in seen:
            dupes.add(tid)
        seen.add(tid)
    for d in sorted(dupes):
        errors.append(f"Duplicate task id '{d}'")

    id_set = {str(t.get("id") or "") for t in tasks if t.get("id")}

    # Self-dependencies
    for t in tasks:
        tid = str(t.get("id") or "")
        for dep in t.get("dependencies") or []:
            if str(dep) == tid:
                errors.append(f"Task '{tid}': self-dependency is not allowed")

    # Unknown / missing dependency targets
    for t in tasks:
        tid = str(t.get("id") or "")
        if not tid:
            continue
        raw = t.get("dependencies")
        if raw is not None and not isinstance(raw, list):
            errors.append(f"Task '{tid}': dependencies must be a list")
            continue
        for dep in raw or []:
            ds = str(dep)
            if not ds:
                continue
            if ds not in id_set:
                errors.append(f"Task '{tid}': dependency '{ds}' does not match any task id")

    # Cycle detection (only among valid edges)
    if not errors:
        cyc = find_dependency_cycle(tasks)
        if cyc is not None:
            chain = " -> ".join(cyc)
            errors.append(f"Dependency cycle detected: {chain}")

    topo = _topological_order_or_none(tasks) if not errors else None
    if not errors and topo is None:
        errors.append("Could not compute topological order (internal graph error)")

    valid = len(errors) == 0
    return DagValidationResult(valid=valid, errors=errors, topological_order=topo if valid else None)


def validate_task_shapes(tasks: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for t in tasks:
        tid = str(t.get("id") or "")
        for field in REQUIRED_FIELDS:
            if field not in t:
                errors.append(f"Task {tid or '?'} missing field '{field}'")
        if "dependencies" in t and not isinstance(t["dependencies"], list):
            errors.append(f"Task {tid}: dependencies must be a list")
    return errors


def validate_dependency_ids_exist(tasks: list[dict[str, Any]]) -> list[str]:
    ids = {str(t.get("id") or "") for t in tasks if t.get("id")}
    errors: list[str] = []
    for t in tasks:
        tid = str(t.get("id") or "")
        for dep in t.get("dependencies") or []:
            ds = str(dep)
            if ds and ds not in ids:
                errors.append(f"Task {tid}: unknown dependency '{ds}'")
    return errors


def _topological_order_or_none(tasks: list[dict[str, Any]]) -> list[str] | None:
    """Kahn topological sort. Returns None if cycle or invalid structure."""
    id_to_task = {str(t["id"]): t for t in tasks if t.get("id")}
    if len(id_to_task) != len(tasks):
        return None
    indeg: dict[str, int] = {}
    for tid in id_to_task:
        indeg[tid] = len(id_to_task[tid].get("dependencies") or [])

    ready = deque([tid for tid, d in indeg.items() if d == 0])
    order: list[str] = []
    while ready:
        tid = ready.popleft()
        order.append(tid)
        for t in tasks:
            deps = t.get("dependencies") or []
            if tid in deps:
                ot = str(t.get("id") or "")
                if ot in indeg:
                    indeg[ot] -= 1
                    if indeg[ot] == 0:
                        ready.append(ot)
    if len(order) != len(tasks):
        return None
    return order


def graph_has_cycle(tasks: list[dict[str, Any]]) -> bool:
    return _topological_order_or_none(tasks) is None


def strip_invalid_dependencies(tasks: list[dict[str, Any]]) -> None:
    ids = {str(t.get("id") or "") for t in tasks if t.get("id")}
    for t in tasks:
        raw = t.get("dependencies") or []
        if not isinstance(raw, list):
            t["dependencies"] = []
            continue
        cleaned: list[str] = []
        for d in raw:
            ds = str(d)
            if ds and ds in ids and ds != str(t.get("id")):
                cleaned.append(ds)
        t["dependencies"] = list(dict.fromkeys(cleaned))


def break_cycles_greedy(tasks: list[dict[str, Any]], max_iterations: int = 256) -> int:
    """
    Remove dependency entries until the graph is acyclic.
    Returns number of dependency edges removed.
    """
    removed = 0
    for _ in range(max_iterations):
        if not graph_has_cycle(tasks):
            break
        # Remove one dependency from the first task that still has any
        for t in tasks:
            deps = t.get("dependencies") or []
            if deps:
                deps.pop()
                removed += 1
                break
        else:
            break
    return removed


def build_edges_from_dependencies(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Edge source -> target: prerequisite blocks dependent."""
    edges: list[dict[str, Any]] = []
    for t in tasks:
        tid = str(t.get("id") or "")
        if not tid:
            continue
        for dep in t.get("dependencies") or []:
            ds = str(dep)
            if ds:
                edges.append({"source": ds, "target": tid, "type": "depends_on"})
    return edges


def validate_planning_graph(tasks: list[dict[str, Any]], check_cycle: bool = True) -> tuple[list[str], list[str]]:
    """
    Run all checks. Returns (errors, warnings).
    """
    errors: list[str] = []
    errors.extend(validate_task_shapes(tasks))
    errors.extend(validate_dependency_ids_exist(tasks))
    if check_cycle and graph_has_cycle(tasks):
        errors.append("Task dependency graph contains at least one cycle")
    return errors, []
