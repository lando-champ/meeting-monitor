"""Deterministic transcript RAG chunk boundaries (no network)."""
import pytest

from app.services.transcript_rag.core import TranscriptRAGIndex


def test_word_chunks_split_without_embeddings():
    from app.services.transcript_rag.core import _word_chunks

    body = "alpha " * 300
    chunks = _word_chunks("m1", 0, body.strip(), chunk_words=80, overlap_words=10)
    assert len(chunks) >= 3
    assert all("Meeting meeting_id=m1" in c.display for c in chunks)


def test_from_meeting_texts_chunks_non_empty():
    pytest.importorskip("sentence_transformers")
    body = "word " * 400
    idx = TranscriptRAGIndex.from_meeting_texts({"m1": body}, {"m1": 0})
    assert idx is not None
    assert len(idx.chunks) >= 1
    hits = idx.search("word word word", k=3)
    assert len(hits) >= 1
    assert hits[0][1] > 0.1


def test_retrieve_user_query_returns_capped_context():
    pytest.importorskip("sentence_transformers")
    body = "alpha beta gamma " * 200
    idx = TranscriptRAGIndex.from_meeting_texts({"mid": body}, {"mid": 0})
    assert idx is not None
    from app.services.transcript_rag.core import retrieve_context_for_user_query

    ctx, score = retrieve_context_for_user_query(idx, "mid", "gamma beta")
    assert score > 0.1
    assert "gamma" in ctx
