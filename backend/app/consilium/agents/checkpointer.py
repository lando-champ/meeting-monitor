"""LangGraph checkpointer for Consilium workspace runs (thread_id = workspace_id)."""
from __future__ import annotations

import os
import threading
from typing import Any

_lock = threading.Lock()
_checkpointer: Any = None


def get_consilium_checkpointer():
    """
    Mongo-backed saver by default; use CONSILIUM_CHECKPOINTER=memory for CI / unit tests.
    Optional TTL (seconds) via LANGGRAPH_CHECKPOINT_TTL_SECONDS on the checkpoint collections.
    """
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer
    with _lock:
        if _checkpointer is not None:
            return _checkpointer
        mode = (os.environ.get("CONSILIUM_CHECKPOINTER") or "mongo").strip().lower()
        if mode == "memory":
            from langgraph.checkpoint.memory import MemorySaver

            _checkpointer = MemorySaver()
            return _checkpointer

        from pymongo import MongoClient
        from langgraph.checkpoint.mongodb import MongoDBSaver

        from app.core.config import settings

        ttl_val = getattr(settings, "LANGGRAPH_CHECKPOINT_TTL_SECONDS", None)
        ttl: int | None
        try:
            ttl = int(ttl_val) if ttl_val is not None and str(ttl_val).strip() != "" else None
        except (TypeError, ValueError):
            ttl = None

        client = MongoClient(settings.MONGODB_URL)
        _checkpointer = MongoDBSaver(
            client,
            db_name=settings.MONGODB_DB_NAME,
            checkpoint_collection_name="langgraph_checkpoints",
            writes_collection_name="langgraph_checkpoint_writes",
            ttl=ttl,
        )
        return _checkpointer


def reset_consilium_checkpointer_for_tests() -> None:
    """Clear singleton (pytest)."""
    global _checkpointer
    with _lock:
        _checkpointer = None
