"""
WebSocket: /ws/audio/{meeting_id} accepts PCM from bot; process_audio → STT → broadcast.
/ws/meeting/{meeting_id}/live: frontend subscribes for transcript updates.
"""
import asyncio
import logging
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

from app.audio.audio_processor import AudioProcessor
from app.stt.stt_pipeline import STTPipeline

router = APIRouter()


class WebSocketManager:
    """Per-meeting AudioProcessor, STTPipeline; broadcast transcript to frontend subscribers."""

    def __init__(self):
        self._processors: Dict[str, AudioProcessor] = {}
        self._pipelines: Dict[str, STTPipeline] = {}
        self._subscribers: Dict[str, Set[WebSocket]] = {}

    def ensure_pipeline(self, meeting_id: str) -> None:
        if meeting_id in self._pipelines:
            return
        # Use VAD to drop non-speech and reduce hallucinated text
        self._processors[meeting_id] = AudioProcessor(use_vad=True)
        async def push(mid: str, text: str):
            await self.broadcast_transcript(mid, text)
        self._pipelines[meeting_id] = STTPipeline(
            meeting_id,
            push_callback=push,
        )

    async def process_audio(self, meeting_id: str, data: bytes) -> None:
        """Process PCM from bot: processor → pipeline buffer → maybe transcribe and broadcast."""
        self.ensure_pipeline(meeting_id)
        proc = self._processors[meeting_id]
        pipeline = self._pipelines[meeting_id]
        chunk = proc.process_audio_frame(data)
        if chunk:
            pipeline.process_audio(chunk)
            await pipeline.process_buffer()
        # Flush remaining on disconnect is optional

    def subscribe(self, meeting_id: str, ws: WebSocket) -> None:
        if meeting_id not in self._subscribers:
            self._subscribers[meeting_id] = set()
        self._subscribers[meeting_id].add(ws)

    def unsubscribe(self, meeting_id: str, ws: WebSocket) -> None:
        if meeting_id in self._subscribers:
            self._subscribers[meeting_id].discard(ws)

    async def broadcast_transcript(self, meeting_id: str, text: str) -> None:
        dead = set()
        for ws in self._subscribers.get(meeting_id) or set():
            try:
                await ws.send_json({"type": "transcript", "text": text})
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.unsubscribe(meeting_id, ws)

    def remove_meeting(self, meeting_id: str) -> None:
        self._processors.pop(meeting_id, None)
        self._pipelines.pop(meeting_id, None)
        self._subscribers.pop(meeting_id, None)


ws_manager = WebSocketManager()


@router.websocket("/audio/{meeting_id}")
async def websocket_audio(websocket: WebSocket, meeting_id: str):
    """Bot sends raw PCM here. We process and STT; transcript is broadcast to /ws/meeting/{id}/live."""
    await websocket.accept()
    logger.info("Bot audio WebSocket connected for meeting_id=%s", meeting_id)
    try:
        while True:
            data = await websocket.receive_bytes()
            await ws_manager.process_audio(meeting_id, data)
    except WebSocketDisconnect:
        logger.debug("Bot audio WebSocket disconnected for meeting_id=%s", meeting_id)
    except Exception as e:
        logger.exception("Bot audio WebSocket error for meeting_id=%s: %s", meeting_id, e)


@router.websocket("/meeting/{meeting_id}/live")
async def websocket_meeting_live(websocket: WebSocket, meeting_id: str):
    """Frontend connects here to receive live transcript messages."""
    await websocket.accept()
    ws_manager.subscribe(meeting_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.unsubscribe(meeting_id, websocket)
