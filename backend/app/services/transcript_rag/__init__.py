"""Shared transcript chunking, embeddings, and FAISS retrieval."""
from app.services.transcript_rag.core import (
    BOARD_SYNC_QUERIES,
    DEFAULT_RETRIEVAL_QUERIES,
    TranscriptRAGIndex,
    build_fallback_tail,
    retrieve_board_sync_context,
    retrieve_context_for_kanban,
    retrieve_context_for_user_query,
)

__all__ = [
    "BOARD_SYNC_QUERIES",
    "DEFAULT_RETRIEVAL_QUERIES",
    "TranscriptRAGIndex",
    "build_fallback_tail",
    "retrieve_board_sync_context",
    "retrieve_context_for_kanban",
    "retrieve_context_for_user_query",
]
