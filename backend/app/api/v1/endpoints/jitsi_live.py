"""
WebSocket endpoint for Jitsi live transcription.
Bot sends per-participant PCM chunks; we build WAV, call Whisper, return "Display Name : text".
If meeting_id is sent, transcript is stored and broadcast to the meeting details page.
"""
import asyncio
import base64
import io
import struct
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.database import get_database
from app.services.groq_processing import transcribe_wav_bytes
from app.api.v1.endpoints.websocket import manager as ws_manager

router = APIRouter()


def pcm_int16_to_wav(pcm_bytes: bytes, sample_rate: int = 16000, channels: int = 1) -> bytes:
    """Build a minimal WAV file from raw Int16 PCM."""
    n_samples = len(pcm_bytes) // 2
    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + n_samples * 2))
    buf.write(b"WAVEfmt ")
    buf.write(struct.pack("<IHHIIHH", 16, 1, channels, sample_rate, sample_rate * channels * 2, channels * 2, 16))
    buf.write(b"data")
    buf.write(struct.pack("<I", n_samples * 2))
    buf.write(pcm_bytes)
    return buf.getvalue()


def resample_48k_to_16k(pcm_int16_bytes: bytes) -> bytes:
    """Simple 3:1 decimation (48k -> 16k). One channel assumed."""
    arr = bytearray()
    # Take every 3rd sample (Int16 = 2 bytes)
    for i in range(0, len(pcm_int16_bytes), 6):  # 3 samples = 6 bytes
        if i + 2 <= len(pcm_int16_bytes):
            arr.extend(pcm_int16_bytes[i : i + 2])
    return bytes(arr)


@router.websocket("/jitsi-live")
async def websocket_jitsi_live(websocket: WebSocket):
    """
    Receives from the Jitsi bot:
    1. First message: JSON { participantId, displayName, sampleRate? }
    2. Second message: binary PCM (Int16, mono)
    Responds with JSON { displayName, text } i.e. "Display Name : transcribed text".
    """
    await websocket.accept()
    try:
        # First message: metadata (optional meeting_id for storing and broadcasting)
        msg = await websocket.receive_json()
        participant_id = msg.get("participantId", "unknown")
        display_name = (msg.get("displayName") or msg.get("display_name") or f"Participant_{participant_id}").strip()
        sample_rate = int(msg.get("sampleRate") or msg.get("sample_rate") or 48000)
        meeting_id = msg.get("meeting_id") or msg.get("meetingId")

        # Second message: binary PCM (or base64 text)
        raw = await websocket.receive()
        pcm_bytes = raw.get("bytes") or b""
        if not pcm_bytes and raw.get("text"):
            pcm_bytes = base64.b64decode(raw["text"])
        if not pcm_bytes:
            await websocket.send_json({"error": "No audio data", "displayName": display_name})
            return

        # Resample 48k -> 16k if needed (Whisper works best at 16k)
        if sample_rate == 48000:
            pcm_bytes = resample_48k_to_16k(pcm_bytes)
            sample_rate = 16000
        elif sample_rate != 16000 and sample_rate != 8000:
            pass

        wav_bytes = pcm_int16_to_wav(pcm_bytes, sample_rate=sample_rate)
        text = await asyncio.get_event_loop().run_in_executor(
            None, transcribe_wav_bytes, wav_bytes
        )
        text = (text or "").strip()
        if not text:
            text = "(no speech)"
        result = f"{display_name} : {text}"
        await websocket.send_json({"displayName": display_name, "text": text, "line": result})

        # Store and broadcast when meeting_id is provided
        if meeting_id:
            db = await get_database()
            await db.transcripts.insert_one({
                "meeting_id": meeting_id,
                "user_id": None,
                "display_name": display_name,
                "text": text,
                "timestamp": datetime.utcnow(),
                "source": "jitsi_bot",
            })
            await ws_manager.broadcast_to_meeting(meeting_id, {
                "type": "transcript_update",
                "display_name": display_name,
                "text": text,
                "line": result,
                "timestamp": datetime.utcnow().isoformat(),
            })
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
