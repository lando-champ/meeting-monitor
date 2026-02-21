"""
Groq-based processing: transcribe audio/video with Whisper, then summarize and extract action items with LLM.
"""
import json
from typing import Tuple

from groq import Groq

from app.core.config import settings


def _get_client() -> Groq:
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set")
    return Groq(api_key=settings.GROQ_API_KEY)


def transcribe_audio(file_content: bytes, filename: str) -> str:
    """Transcribe audio/video file using Groq Whisper. Returns full text."""
    client = _get_client()
    # Groq expects (filename, content) for multipart; filename must have a supported extension
    ext = (filename or "").split(".")[-1].lower() if "." in (filename or "") else "mp3"
    if ext not in ("flac", "mp3", "mp4", "mpeg", "mpga", "m4a", "ogg", "wav", "webm"):
        ext = "mp3"
    name = f"audio.{ext}"
    transcription = client.audio.transcriptions.create(
        file=(name, file_content),
        model="whisper-large-v3-turbo",
        response_format="text",
        language="en",
    )
    if hasattr(transcription, "text"):
        return transcription.text
    return str(transcription)


def summarize_and_extract(transcript: str) -> Tuple[dict, list]:
    """Use Groq LLM to produce summary (overview, key_points, decisions) and action_items list."""
    client = _get_client()
    prompt = """You are a meeting assistant. Given the following meeting transcript, output a JSON object with exactly these keys (no other keys):
- "overview": one short paragraph summarizing the meeting.
- "key_points": array of strings (main points discussed).
- "decisions": array of strings (decisions made).
- "action_items": array of strings (concrete action items or tasks to do).

Output only valid JSON, no markdown or extra text."""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Transcript:\n\n{transcript[:120000]}"},
        ],
        temperature=0.2,
    )
    text = response.choices[0].message.content or "{}"
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    data = json.loads(text)
    overview = data.get("overview") or ""
    key_points = data.get("key_points")
    decisions = data.get("decisions")
    action_items = data.get("action_items")
    if not isinstance(key_points, list):
        key_points = []
    if not isinstance(decisions, list):
        decisions = []
    if not isinstance(action_items, list):
        action_items = [str(action_items)] if action_items else []
    else:
        action_items = [str(x) for x in action_items]
    summary_dict = {
        "overview": overview,
        "key_points": key_points,
        "decisions": decisions,
    }
    return summary_dict, action_items


def transcribe_and_analyze(file_content: bytes, filename: str) -> Tuple[str, dict, list]:
    """Transcribe with Groq Whisper, then summarize and extract action items with Groq LLM."""
    transcription = transcribe_audio(file_content, filename)
    if not transcription or not transcription.strip():
        transcription = "(No speech detected in the recording.)"
    summary_dict, action_items = summarize_and_extract(transcription)
    return transcription, summary_dict, action_items
