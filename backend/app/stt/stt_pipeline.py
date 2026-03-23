"""
Buffers ~6s audio → WAV → Groq Whisper → save to transcript_segments + transcripts; broadcast via callback.
"""
import asyncio
import io
import logging
import struct
import wave
from datetime import datetime
from typing import Callable, Awaitable, Optional

from groq import Groq

from app.core.config import settings
from app.core.database import get_database

logger = logging.getLogger(__name__)

# Whisper often hallucinates these on silence or low-quality audio; filter when repeated
HALLUCINATION_PHRASES = frozenset({
    "thank you", "thank you.", "thanks for watching", "thanks for watching.",
    "subscribe", "subscribe.", "bye", "bye.", "see you", "see you.",
    "goodbye", "goodbye.",
})
# Allow this many consecutive same hallucination phrase, then filter further repeats
MAX_CONSECUTIVE_HALLUCINATION = 1


def _pcm_rms(pcm_bytes: bytes) -> float:
    """Approximate RMS level of PCM16 mono. Used to skip silent chunks."""
    if len(pcm_bytes) < 2:
        return 0.0
    n = len(pcm_bytes) // 2
    total = 0.0
    for i in range(0, len(pcm_bytes) - 1, 2):
        sample = struct.unpack_from("<h", pcm_bytes, i)[0]
        total += sample * sample
    return (total / n) ** 0.5 if n else 0.0


def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 16000, channels: int = 1) -> bytes:
    """Build minimal WAV from PCM16."""
    n_samples = len(pcm_bytes) // 2
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm_bytes)
    return buf.getvalue()


class STTPipeline:
    """
    Accumulates PCM until ~6 seconds, then transcribes with Groq Whisper.
    Saves to transcript_segments and transcripts; calls push_callback(meeting_id, text) to broadcast.
    """

    def __init__(
        self,
        meeting_id: str,
        push_callback: Optional[Callable[[str, str], Awaitable[None]]] = None,
        sample_rate: int = None,
        buffer_seconds: float = None,
    ):
        self.meeting_id = meeting_id
        self.push_callback = push_callback
        self.sample_rate = sample_rate or settings.AUDIO_SAMPLE_RATE
        self.buffer_seconds = buffer_seconds or getattr(
            settings, "STT_BUFFER_SECONDS", 6.0
        )
        self._buffer = bytearray()
        self._bytes_per_chunk = int(self.sample_rate * self.buffer_seconds * 2)
        self._last_transcribe_time = 0.0
        # Minimum interval between Groq calls; tied to buffer size so streaming is continuous
        self._min_interval = self.buffer_seconds
        self._client: Optional[Groq] = None
        self._lock = asyncio.Lock()
        self._rate_limit_until = 0.0  # monotonic time after which we can call Groq again (after 429)
        self._last_texts: list[str] = []  # last few segment texts to filter repeated hallucinations
        self._silence_rms_threshold = settings.STT_SILENCE_RMS_THRESHOLD

    def _get_client(self) -> Groq:
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set")
        if self._client is None:
            self._client = Groq(api_key=settings.GROQ_API_KEY)
        return self._client

    def process_audio(self, pcm_chunk: bytes) -> None:
        """Add PCM to buffer; does not run transcription (call process_buffer() after)."""
        self._buffer.extend(pcm_chunk)

    async def process_buffer(self) -> None:
        """
        If buffer has ~6s of audio, convert to WAV, call Whisper, save and broadcast.
        Rate-limited to avoid 429.
        """
        if len(self._buffer) < self._bytes_per_chunk:
            return
        import time
        now = time.monotonic()
        if now - self._last_transcribe_time < self._min_interval:
            return
        async with self._lock:
            if len(self._buffer) < self._bytes_per_chunk:
                return
            # Take a window of audio for this segment, but keep a small tail
            # in the buffer so successive segments have overlap and better context.
            chunk = bytes(self._buffer[: self._bytes_per_chunk])
            overlap_seconds = min(0.5, self.buffer_seconds / 2.0)
            overlap_bytes = int(self.sample_rate * overlap_seconds * 2)
            trim_bytes = max(0, self._bytes_per_chunk - overlap_bytes)
            del self._buffer[:trim_bytes]
        self._last_transcribe_time = time.monotonic()

        # Skip sending silence to Whisper (reduces "Thank you" hallucinations)
        rms = _pcm_rms(chunk)
        if rms < self._silence_rms_threshold:
            logger.debug("Skipping silent chunk (RMS=%.0f)", rms)
            return

        wav_bytes = _pcm_to_wav(chunk, self.sample_rate)
        try:
            client = self._get_client()
        except ValueError as e:
            logger.warning("STT skipped (no API key): %s", e)
            return
        try:
            transcription = client.audio.transcriptions.create(
                file=("audio.wav", wav_bytes, "audio/wav"),
                model="whisper-large-v3",  # more accurate than turbo, fewer hallucinations
                response_format="verbose_json",
                language="en",
                temperature=0.0,
            )
        except Exception as e:
            err_name = type(e).__name__
            err_str = str(e).lower()
            if "AuthenticationError" in err_name or "401" in err_str or "invalid_api_key" in err_str:
                logger.error(
                    "Groq API key is invalid or expired. Set a valid GROQ_API_KEY in backend/.env (get one at https://console.groq.com). Transcription skipped."
                )
            elif "429" in err_str or "rate" in err_str:
                backoff = 20.0
                self._rate_limit_until = time.monotonic() + backoff
                logger.warning("Groq rate limit (429). Backing off %.0fs; transcription will resume.", backoff)
            else:
                logger.exception("Groq Whisper transcription failed: %s", e)
            return
        text = getattr(transcription, "text", None) or ""
        text_clean = (text or "").strip()
        if not text_clean:
            logger.debug("Whisper returned empty text (silent or inaudible audio)")
            return

        # Filter Whisper hallucinations: skip known short phrases entirely (e.g. repeated "Thank you")
        normalized = text_clean.lower().rstrip(".")
        if normalized in HALLUCINATION_PHRASES:
            logger.debug("Filtering hallucination phrase: %r", text_clean)
            return
        self._last_texts = (self._last_texts + [text_clean])[-5:]  # keep last 5

        db = await get_database()
        now_dt = datetime.utcnow()
        await db.transcript_segments.insert_one({
            "meeting_id": self.meeting_id,
            "text": text_clean,
            "timestamp": now_dt,
            "language": "en",
        })
        await db.transcripts.insert_one({
            "meeting_id": self.meeting_id,
            "text": text_clean,
            "timestamp": now_dt,
        })
        if self.push_callback:
            await self.push_callback(self.meeting_id, text_clean)
