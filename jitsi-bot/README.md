# Jitsi Meeting Assistant Bot

The bot **joins your self-hosted Jitsi meeting as a participant**, captures **separate audio per participant**, and streams it to the backend for transcription. Output format: **`Speaker name : what they said`**. No screen recording, no system audio; speaker is identified by Jitsi (one track per participant).

## Prerequisites

- **Node.js** 18+
- **Backend** running (Python FastAPI with Groq; see repo root and `backend/`).
- **Self-hosted Jitsi** (or use `meet.jit.si` for testing).

## Quick start

1. **Start the backend** (from repo root):

   ```bash
   cd backend && python run.py
   ```

   Ensure `GROQ_API_KEY` is set in `backend/.env` for transcription.

2. **Install and run the bot**:

   ```bash
   cd jitsi-bot
   npm install
   npm start
   ```

   Default: joins `meet.jit.si` room `MeetingMonitor` as "Meeting Assistant".

3. **Join the same room** from your browser (or Jitsi app). Speak; transcriptions appear in the bot’s browser console and in the terminal (if you pipe browser logs).

## Configuration

Use environment variables or edit `runner.js`:

| Variable        | Default             | Description                          |
|----------------|---------------------|--------------------------------------|
| `JITSI_DOMAIN` | `meet.jit.si`       | Your Jitsi server (e.g. `meet.mycompany.com`) |
| `ROOM_NAME`    | `MeetingMonitor`    | Jitsi room name                      |
| `BOT_NAME`     | `Meeting Assistant` | Bot’s display name in the meeting   |
| `BACKEND_URL`  | `http://localhost:8000` | Backend URL (for capture page and WebSocket) |
| `HEADLESS`     | `1`                 | Set to `0` to see the browser       |

Example for self-hosted Jitsi:

```bash
JITSI_DOMAIN=meet.yourdomain.com ROOM_NAME=DailyStandup BOT_NAME="Transcription Bot" node runner.js
```

## How it works

1. **Runner** (`runner.js`) launches Playwright (Chromium), opens the **capture page** served by your backend at `/static/jitsi-bot/capture.html`, with query params for Jitsi domain, room, and bot name.
2. **Capture page** loads `lib-jitsi-meet` from your Jitsi domain, joins the room with the bot name (audio only, muted). On **TRACK_ADDED** for each remote participant it:
   - Resolves **display name** from the participant object (so speaker = no guessing).
   - Pipes the track’s audio through the **Web Audio API** to get PCM.
   - Buffers ~8 s of Int16 PCM and sends it to the backend over a **WebSocket** (`/api/v1/ws/jitsi-live`) with `participantId` and `displayName`.
3. **Backend** builds a WAV from the PCM (resampling 48k→16k if needed), calls **Groq Whisper**, and returns `"Display Name : transcribed text"`.

See **[docs/JITSI_MEETING_ASSISTANT_ARCHITECTURE.md](../docs/JITSI_MEETING_ASSISTANT_ARCHITECTURE.md)** for full architecture, pitfalls, and scaling.
