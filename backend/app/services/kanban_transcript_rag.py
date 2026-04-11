"""
Embeddings + FAISS retrieval for Kanban automation: small relevant transcript context → Groq.

Does not import kanban_agentic_automation (avoid circular imports).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from app.core.config import settings
from app.services.transcription_cleaning import clean_transcription_text

logger = logging.getLogger(__name__)

_st_model = None

DEFAULT_RETRIEVAL_QUERIES: Tuple[str, ...] = (
    "task assigned ownership someone will handle who is responsible commit accept yes sure deadline",
    "working on in progress currently doing actively implementation",
    "completed finished done shipped merged deployed ready",
    "blocked stuck waiting dependency cannot proceed issue problem",
)

BOARD_SYNC_QUERIES: Tuple[str, ...] = (
    "done completed finished shipped merged closed",
    "in progress working on actively doing",
    "blocked stuck waiting dependency cannot",
    "status update moved column review",
)


def _clean_transcript_for_rag(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return ""
    t = re.sub(r"(?m)^\s*\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s*", "", t)
    t = re.sub(r"(?m)^\s*[A-Za-z][\w .'-]{0,40}:\s*", "", t)
    t = re.sub(r"[ \t]+", " ", t)
    return clean_transcription_text(t)


def _get_sentence_model():
    global _st_model
    if _st_model is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise RuntimeError(
                "sentence-transformers is required for Kanban RAG. pip install sentence-transformers faiss-cpu"
            ) from e
        name = (getattr(settings, "KANBAN_EMBEDDING_MODEL", None) or "all-MiniLM-L6-v2").strip()
        logger.info("Loading embedding model %s (Kanban RAG)", name)
        _st_model = SentenceTransformer(name)
    return _st_model


def _encode_texts(texts: Sequence[str]) -> np.ndarray:
    model = _get_sentence_model()
    emb = model.encode(list(texts), convert_to_numpy=True, show_progress_bar=False)
    if emb.dtype != np.float32:
        emb = emb.astype(np.float32)
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    return emb / norms


@dataclass
class _Chunk:
    meeting_id: str
    ordinal: int
    text: str  # raw chunk words for embedding
    display: str  # header + text for LLM


def _word_chunks(
    meeting_id: str,
    ordinal: int,
    cleaned_text: str,
    chunk_words: int,
    overlap_words: int,
) -> List[_Chunk]:
    words = cleaned_text.split()
    if not words:
        return []
    out: List[_Chunk] = []
    step = max(1, chunk_words - overlap_words)
    i = 0
    while i < len(words):
        piece = words[i : i + chunk_words]
        if not piece:
            break
        raw = " ".join(piece)
        header = f"=== Meeting meeting_id={meeting_id} ordinal={ordinal} ===\n"
        out.append(_Chunk(meeting_id=meeting_id, ordinal=ordinal, text=raw, display=header + raw))
        i += step
    return out


class TranscriptRAGIndex:
    """In-memory FAISS index over transcript chunks."""

    def __init__(
        self,
        chunks: List[_Chunk],
        vectors: np.ndarray,
    ):
        import faiss

        self.chunks = chunks
        dim = vectors.shape[1]
        self._index = faiss.IndexFlatIP(dim)
        self._index.add(vectors)

    @classmethod
    def from_meeting_texts(
        cls,
        meeting_texts: Dict[str, str],
        ordinal_by_meeting_id: Dict[str, int],
    ) -> Optional["TranscriptRAGIndex"]:
        """meeting_id -> cleaned transcript body (no header)."""
        chunk_words = max(50, int(getattr(settings, "KANBAN_RAG_CHUNK_WORDS", 250) or 250))
        overlap = max(0, int(getattr(settings, "KANBAN_RAG_CHUNK_OVERLAP_WORDS", 40) or 40))

        all_chunks: List[_Chunk] = []
        for mid, body in meeting_texts.items():
            cleaned = _clean_transcript_for_rag(body)
            if not cleaned:
                continue
            ord_ = int(ordinal_by_meeting_id.get(mid, 0))
            all_chunks.extend(_word_chunks(mid, ord_, cleaned, chunk_words, overlap))

        if not all_chunks:
            return None

        texts = [c.text for c in all_chunks]
        vecs = _encode_texts(texts)
        return cls(all_chunks, vecs)

    def search(
        self,
        query: str,
        k: int,
    ) -> List[Tuple[int, float]]:
        """Returns list of (chunk_index, inner_product ~ cosine)."""
        q = _encode_texts([query])
        scores, idxs = self._index.search(q, min(k, len(self.chunks)))
        row_scores = scores[0]
        row_idx = idxs[0]
        out: List[Tuple[int, float]] = []
        for j, i in enumerate(row_idx):
            if i < 0:
                continue
            out.append((int(i), float(row_scores[j])))
        return out


def _parse_queries() -> Tuple[str, ...]:
    raw = (getattr(settings, "KANBAN_RAG_QUERIES", "") or "").strip()
    if not raw:
        return DEFAULT_RETRIEVAL_QUERIES
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return tuple(parts) if parts else DEFAULT_RETRIEVAL_QUERIES


def retrieve_context_for_kanban(
    index: TranscriptRAGIndex,
    latest_meeting_id: str,
    queries: Optional[Sequence[str]] = None,
) -> Tuple[str, float]:
    """
    Multi-query retrieval, dedupe, latest-meeting boost, char cap.
    Returns (context_string, best_raw_score).
    """
    top_k = max(1, int(getattr(settings, "KANBAN_RAG_TOP_K", 5) or 5))
    max_chars = max(2000, int(getattr(settings, "KANBAN_RAG_MAX_CONTEXT_CHARS", 12000) or 12000))
    boost = float(getattr(settings, "KANBAN_RAG_LATEST_MEETING_SCORE_BOOST", 1.12) or 1.0)
    min_sim = float(getattr(settings, "KANBAN_RAG_MIN_SIMILARITY", 0.22) or 0.0)

    qs = tuple(queries) if queries is not None else _parse_queries()
    best_seen = 0.0
    scored: Dict[int, float] = {}

    for q in qs:
        for idx, sc in index.search(q, top_k):
            best_seen = max(best_seen, sc)
            if sc < min_sim:
                continue
            adj = sc * (boost if index.chunks[idx].meeting_id == latest_meeting_id else 1.0)
            if idx not in scored or adj > scored[idx]:
                scored[idx] = adj

    if not scored:
        return "", best_seen

    ordered = sorted(scored.items(), key=lambda x: -x[1])
    parts: List[str] = []
    total = 0
    for idx, _ in ordered:
        block = index.chunks[idx].display.strip()
        if not block:
            continue
        sep_len = 2 if parts else 0
        if total + sep_len + len(block) > max_chars:
            remain = max_chars - total - sep_len
            if remain > 200:
                parts.append(block[:remain] + "…")
            break
        if parts:
            parts.append("\n\n")
        parts.append(block)
        total += sep_len + len(block)

    return "".join(parts), best_seen


def retrieve_board_sync_context(
    latest_meeting_id: str,
    latest_meeting_cleaned: str,
) -> Tuple[str, float]:
    """Single-meeting index + board-oriented queries; capped transcript size."""
    cap = max(2000, int(getattr(settings, "KANBAN_RAG_BOARD_MAX_TRANSCRIPT_CHARS", 10000) or 10000))
    body = (latest_meeting_cleaned or "").strip()
    if len(body) > cap:
        body = body[-cap:]
    if not body:
        return "", 0.0

    idx = TranscriptRAGIndex.from_meeting_texts(
        {latest_meeting_id: body},
        {latest_meeting_id: 0},
    )
    if idx is None:
        return "", 0.0
    return retrieve_context_for_kanban(idx, latest_meeting_id, queries=BOARD_SYNC_QUERIES)


def build_fallback_tail(latest_meeting_cleaned: str, max_chars: int) -> str:
    t = (latest_meeting_cleaned or "").strip()
    if not t:
        return ""
    if len(t) <= max_chars:
        return t
    return t[-max_chars:]
