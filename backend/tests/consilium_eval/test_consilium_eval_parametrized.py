"""Parametrized Consilium eval harness (fixtures + manifest toward 40 cases)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.consilium.agents.graph import (
    _normalize_kanban,
    _route_after_execution_github,
    _route_after_monitoring_merge,
    _route_after_replan_merge,
)
from app.consilium.agents.monitoring_agent import _stable_hash, compute_project_health
from app.consilium.models.meeting_signal import MeetingSignalV1
from app.consilium.services.monitoring_prefetch import compute_blocker_recurrence_score

FIXTURE_ROOT = Path(__file__).resolve().parent.parent / "fixtures" / "consilium_eval"
_MANIFEST = json.loads((FIXTURE_ROOT / "cases.json").read_text(encoding="utf-8"))["cases"]


def _load_case_file(rel: str) -> dict:
    return json.loads((FIXTURE_ROOT / rel).read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", _MANIFEST, ids=lambda c: c.get("id", "?"))
def test_consilium_eval_case(case: dict) -> None:
    if case.get("skip"):
        pytest.skip(str(case["skip"]))
    kind = case.get("kind")
    rel = case.get("fixture")
    assert rel and kind, case
    data = _load_case_file(rel)

    if kind == "health":
        h = compute_project_health(data)
        ex = data.get("expect") or {}
        if "risk_score_max" in ex:
            assert h["risk_score"] <= ex["risk_score_max"] + 1e-6
        if "delay_probability_max" in ex:
            assert h["delay_probability"] <= ex["delay_probability_max"] + 1e-6
        if "risk_score_min" in ex:
            assert h["risk_score"] >= ex["risk_score_min"] - 1e-6
        return

    if kind == "recurrence":
        score = compute_blocker_recurrence_score(
            data.get("snippet") or "",
            list(data.get("blockers") or []),
            data.get("meeting_signal"),
        )
        assert score >= float((data.get("expect") or {}).get("score_min", 0))
        return

    if kind == "route_monitoring":
        r = _route_after_monitoring_merge(data["state"])
        want = data["expect"]["target"]
        if want == "end":
            assert r == "end"
        else:
            assert r == want
        return

    if kind == "route_replan":
        r = _route_after_replan_merge(data["state"])
        want = data["expect"]["target"]
        if want == "end":
            assert r == "end"
        else:
            assert r == want
        return

    if kind == "stable_hash":
        h = _stable_hash(data["payload"])
        assert len(h) == int(data["expect"]["len"])
        return

    if kind == "normalize_kanban":
        out = _normalize_kanban(data.get("kanban"), list(data.get("tasks") or []))
        assert out == data["expect"]
        return

    if kind == "meeting_signal":
        m = MeetingSignalV1.model_validate(data)
        doc = m.to_mongo()
        assert doc["version"] == "1"
        assert doc["project_id"]
        return

    if kind == "github_route":
        route = _route_after_execution_github(data)
        assert route == data["expect"]["route"]
        return

    if kind == "stub":
        pytest.fail("stub case should have been skipped")
    pytest.fail(f"unknown eval kind: {kind}")


@pytest.mark.rouge
def test_rouge_optional_placeholder() -> None:
    pytest.importorskip("rouge_score", reason="optional rouge-score not installed")
    assert True
