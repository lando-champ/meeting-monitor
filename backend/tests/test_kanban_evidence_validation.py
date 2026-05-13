"""Golden cases for transcript evidence validation used in Kanban + reconciliation."""
from app.services.kanban_agentic_automation import _validate_transcript_evidence


def test_evidence_verbatim_in_chunk():
    assert _validate_transcript_evidence("hello world", "prefix hello world suffix") == "hello world"


def test_evidence_whitespace_normalized_match():
    chunk = "The   team will ship  the   feature"
    ev = "team will ship the feature"
    out = _validate_transcript_evidence(ev, chunk)
    assert "team" in out and "feature" in out


def test_evidence_rejected_when_not_in_chunk():
    assert _validate_transcript_evidence("not present", "only this text") == ""
