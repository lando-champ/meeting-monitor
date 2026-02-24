"""
Captures system audio (e.g. Stereo Mix on Windows) or default input (mic) as PCM16, 16 kHz mono.
Uses sounddevice (optional). Puts chunks in asyncio queue; get_audio_chunk() is awaited by the bot.
"""
import asyncio
import logging
import struct
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    sd = None


class SystemAudioCapture:
    """Capture system/default audio; output PCM16 16 kHz mono via async queue."""

    def __init__(
        self,
        sample_rate: int = None,
        channels: int = None,
        chunk_size: int = None,
        device: Optional[int] = None,
    ):
        self.sample_rate = sample_rate or settings.AUDIO_SAMPLE_RATE
        self.channels = channels or settings.AUDIO_CHANNELS
        self.chunk_size = chunk_size or settings.AUDIO_CHUNK_SIZE
        self.device = device
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._stream = None
        self._running = False

    def _callback(self, indata, frames, time_info, status):
        if status:
            return
        # indata is float32; convert to int16 PCM
        buf = []
        for x in indata.flatten():
            s = max(-1, min(1, x))
            buf.append(struct.pack("<h", int(s * 32767)))
        self._queue.put_nowait(b"".join(buf))

    def start(self) -> None:
        """Start capture stream (blocking sounddevice). Call from thread or ensure non-blocking."""
        if not SOUNDDEVICE_AVAILABLE:
            raise RuntimeError("sounddevice is not installed. pip install sounddevice")
        self._running = True
        device = self.device
        if device is None and SOUNDDEVICE_AVAILABLE:
            try:
                default = sd.default.device
                device = default[0] if isinstance(default, tuple) else default
                logger.info("Audio capture using default input device: %s", device)
            except Exception:
                pass
        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                blocksize=self.chunk_size,
                device=device,
                callback=self._callback,
            )
            self._stream.start()
        except Exception as e:
            if device is not None:
                raise
            for idx in range(4):
                try:
                    logger.info("Audio capture trying device index %s", idx)
                    self._stream = sd.InputStream(
                        samplerate=self.sample_rate,
                        channels=self.channels,
                        dtype="float32",
                        blocksize=self.chunk_size,
                        device=idx,
                        callback=self._callback,
                    )
                    self._stream.start()
                    return
                except Exception as e2:
                    logger.debug("Device %s failed: %s", idx, e2)
                    continue
            raise RuntimeError(f"Audio capture start failed: {e}") from e

    def stop(self) -> None:
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    async def get_audio_chunk(self) -> bytes:
        """Await next PCM chunk. Used by bot in a loop to send to WebSocket."""
        return await self._queue.get()

    def put_chunk(self, chunk: bytes) -> None:
        """For testing or alternate source: inject a chunk."""
        self._queue.put_nowait(chunk)
