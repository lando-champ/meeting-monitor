"""
Buffers PCM frames; optional VAD (webrtcvad). Outputs combined chunks for STT to reduce duplicate transcriptions.
"""
from typing import Optional, List

from app.core.config import settings


class AudioProcessor:
    """Receives raw PCM frames; optional VAD; returns combined chunk when buffer is full."""

    def __init__(
        self,
        sample_rate: int = None,
        chunk_frames: int = 10,
        use_vad: bool = False,
    ):
        self.sample_rate = sample_rate or settings.AUDIO_SAMPLE_RATE
        self.chunk_frames = chunk_frames
        self.use_vad = use_vad
        self._buffer: List[bytes] = []
        self._vad = None
        if use_vad:
            try:
                import webrtcvad
                self._vad = webrtcvad.Vad(2)
            except ImportError:
                self.use_vad = False

    def process_audio_frame(self, frame: bytes) -> Optional[bytes]:
        """
        Process one PCM frame. Optionally run VAD; buffer frames.
        Returns a combined chunk when enough frames collected, else None.
        """
        if self.use_vad and self._vad and len(frame) >= 640:  # 20 ms at 16 kHz
            # webrtcvad expects 10, 20, or 30 ms frames at 8/16/32 kHz
            if not self._vad.is_speech(frame[:640], self.sample_rate):
                # Drop non-speech; still flush buffer if we have content
                if self._buffer:
                    out = b"".join(self._buffer)
                    self._buffer.clear()
                    return out
                return None
        self._buffer.append(frame)
        if len(self._buffer) >= self.chunk_frames:
            out = b"".join(self._buffer)
            self._buffer.clear()
            return out
        return None

    def flush(self) -> Optional[bytes]:
        """Return any remaining buffered audio."""
        if not self._buffer:
            return None
        out = b"".join(self._buffer)
        self._buffer.clear()
        return out
