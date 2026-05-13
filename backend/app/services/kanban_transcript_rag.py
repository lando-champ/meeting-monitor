"""
Backward-compatible exports for transcript RAG.

Implementation lives in ``app.services.transcript_rag``.
"""
from app.services.transcript_rag.core import (  # noqa: F401
    BOARD_SYNC_QUERIES,
    DEFAULT_RETRIEVAL_QUERIES,
    TranscriptRAGIndex,
    build_fallback_tail,
    retrieve_board_sync_context,
    retrieve_context_for_kanban,
    retrieve_context_for_user_query,
)
