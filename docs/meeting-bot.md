# Meeting bot and live transcription

## Overview

The Jitsi/Selenium bot captures system audio and streams PCM to the API WebSocket `WS /api/v1/ws/audio/{meeting_id}`. The server runs the STT pipeline (`app.stt.stt_pipeline.STTPipeline`), writes `transcript_segments`, and broadcasts text to `WS /api/v1/ws/meeting/{meeting_id}/live` for the corporate meeting page.

## Environment

| Variable | Purpose |
|----------|---------|
| `BACKEND_URL` | Base URL the bot uses for REST + WebSocket (defaults to `http://localhost:{PORT}`). |
| `MEETING_AUDIO_WS_SECRET` | If set, bot must append `?ws_secret=...` to the audio WebSocket URL. |
| `MEETING_LIVE_WS_REQUIRE_AUTH` | If `true`, live transcript subscribers must pass `?access_token=<JWT>`. |
| `GROQ_API_KEY` | Default cloud STT (Groq Whisper). |
| `STT_BACKEND` | `groq` (default) or `faster_whisper` for optional local STT. |
| `STT_FASTER_WHISPER_MODEL` | Model size when using `faster_whisper` (e.g. `base`, `small`). Requires `pip install faster-whisper`. |

Optional transcript RAG (Kanban + Q&A + copilot) is documented in `docs/meeting-stack-dod.md`.

## Chrome / Chromedriver

The bot uses Selenium with `webdriver-manager`. Match Chrome major version to the resolved driver. On Linux servers, install Chromium + Xvfb (or a real display) for headful Jitsi.

## Worker / scale-out

Bots and pipelines are tied to the API process that started them. For HA, run a dedicated API instance with a stable `BACKEND_URL` per bot host, or add a future queue-based worker (see `backend/run_meeting_worker.py` placeholder).

## Troubleshooting

- **No live text in UI:** Confirm the meeting is `live`, the bot joined, and the browser WebSocket connects to the same host as `VITE_API_URL` (or dev proxy to the API port).
- **4401 / immediate WS close:** Check `ws_secret` or JWT query when the corresponding env flags are set.
- **Groq 429:** Logs show backoff; reduce chunk frequency via `STT_BUFFER_SECONDS` / `STT_MIN_INTERVAL_SECONDS`.
