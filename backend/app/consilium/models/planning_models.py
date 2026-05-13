"""Structured planning output: DAG task graph + phased decomposition (Phase 2)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Priority = Literal["low", "medium", "high"]
TaskStatus = Literal["todo", "in_progress", "done"]


class TaskGraphEdge(BaseModel):
    """Directed edge: source must complete before target (dependency flow)."""

    source: str = Field(..., description="Upstream task id (prerequisite)")
    target: str = Field(..., description="Downstream task id (dependent)")
    type: str = Field(default="depends_on")


class TaskGraphNode(BaseModel):
    """Minimal node payload for visualization / ordering (full task lives in tasks[])."""

    id: str
    title: str
    phase: str | None = None
    priority: Priority = "medium"


class TaskGraphPayload(BaseModel):
    """Explicit DAG representation alongside flat task list."""

    nodes: list[TaskGraphNode] = Field(default_factory=list)
    edges: list[TaskGraphEdge] = Field(default_factory=list)


class PlannedTask(BaseModel):
    """Single task with dependency and estimation fields."""

    id: str
    title: str
    description: str = ""
    dependencies: list[str] = Field(default_factory=list)
    priority: Priority = "medium"
    estimated_effort: float = Field(default=4.0, description="Hours or story-point scale")
    estimated_duration: str | None = None
    status: TaskStatus = "todo"
    assigned_to: str | None = None
    phase: str | None = None


class PhaseBlock(BaseModel):
    """Named phase containing concrete tasks."""

    name: str
    tasks: list[PlannedTask] = Field(default_factory=list)


class PlanningEngineResult(BaseModel):
    """Strict Phase 2 planning envelope (also serialized under roadmap + top-level keys)."""

    phases: list[PhaseBlock] = Field(default_factory=list)
    task_graph: TaskGraphPayload = Field(default_factory=TaskGraphPayload)

    def model_dump_compat(self) -> dict[str, Any]:
        """JSON-serializable dict for API / Mongo."""
        return self.model_dump(mode="json")
