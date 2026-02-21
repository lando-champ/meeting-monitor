# Jitsi Meeting Assistant – Architecture & Implementation Guide

A bot that joins your self-hosted Jitsi meeting as a participant, captures **separate audio per participant**, uses **Jitsi’s own track→participant mapping** for speaker identity (no guessing), transcribes with Whisper, and outputs:

```text
Speaker name : what the speaker spoke
```

---

## 1. Overall System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Self-hosted Jitsi Meet                                │
│  (JVB, Jicofo, Meet frontend – no changes required)                          │
└─────────────────────────────────────────────────────────────────────────────┘
                    │
                    │ WebRTC (one audio track per participant)
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Bot (runs in browser controlled by Playwright)                              │
│  • Loads Meet / lib-jitsi-meet from YOUR Jitsi domain                        │
│  • Joins room with fixed display name (e.g. "Meeting Assistant")              │
│  • Listens to TRACK_ADDED → one remote track per participant                 │
│  • Speaker = participant ID + display name (from Jitsi, no diarization)     │
│  • Captures per-participant audio (Web Audio API → PCM)                       │
│  • Sends PCM chunks per participant to Backend over WebSocket                 │
└─────────────────────────────────────────────────────────────────────────────┘
                    │
                    │ WebSocket (participantId, displayName, PCM chunks)
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Backend (Python or Node)                                                    │
│  • Buffers ~5–10 s of PCM per participant                                    │
│  • Converts PCM → WAV (or keeps PCM) → sends to Whisper (e.g. Groq)           │
│  • Receives "text" per chunk                                                 │
│  • Emits: "Display Name : text" to UI / storage / real-time API             │
└─────────────────────────────────────────────────────────────────────────────┘
```

- **No screen recording, no system audio**: the bot is a normal Jitsi participant; it only uses remote audio tracks provided by Jitsi.
- **Speaker identification**: each WebRTC track is tied to one participant; we get participant ID and display name from lib-jitsi-meet, so every transcribed segment is attributed to the correct speaker without any diarization model.

---

## 2. Recommended Tech Stack

| Layer              | Option A (recommended)     | Option B                |
|--------------------|----------------------------|--------------------------|
| **Bot runner**     | **Node.js** + Playwright   | Python + Playwright      |
| **In-browser**     | JavaScript (lib-jitsi-meet)| Same                     |
| **Backend**        | **Python** (FastAPI)       | Node.js (Express/Fastify)|
| **STT**            | **Groq Whisper**           | OpenAI Whisper / local   |
| **Audio decode**   | Browser: Web Audio → PCM   | Server: Opus → PCM if needed |

- **Why Node + Playwright for the bot**: Stable browser automation, easy to drive a real Chromium instance that runs the Jitsi Meet script. Python + Playwright is also fine if you prefer one language.
- **Why Python backend**: Fits your existing FastAPI + Groq stack; WebSocket endpoint can buffer chunks and call your existing `transcribe_audio` (or a chunk-accepting variant).
- **Why Groq Whisper**: You already use it; low latency, good for near–real-time transcription of short segments.

---

## 3. How the Recording Bot Works

1. **Start bot** (e.g. `node jitsi-bot/runner.js` or `python -m jitsi_bot.runner`):  
   Playwright launches a browser and opens a local HTML page (or a page served by your backend).

2. **Bot page**:
   - Loads `lib-jitsi-meet` from your **self-hosted** Jitsi (e.g. `https://meet.yourdomain.com/libs/lib-jitsi-meet.min.js`).
   - Creates `JitsiConnection` and `JitsiConference` with `roomName` and bot `displayName` (e.g. `"Meeting Assistant"`).
   - Joins with **audio only** (no camera), optionally muted so it doesn’t add noise.
   - On **TRACK_ADDED**: for each remote track, you get a `JitsiTrack` and the **participant ID**. You resolve display name via `room.getParticipantById(participantId)` (or the equivalent in your lib-jitsi-meet version).

3. **Per-participant capture**:
   - Attach the track’s `MediaStream` to a **Web Audio API** `AudioContext` → `createMediaStreamSource(track)`.
   - Use **ScriptProcessorNode** or **AudioWorklet** to get raw PCM (Float32 or Int16).
   - Buffer a few seconds (e.g. 5–10 s), then send to backend over WebSocket with `{ participantId, displayName, pcmBase64 }` (or binary frames with a small JSON header).

4. **Backend**:
   - Receives chunks per participant.
   - Builds a WAV (or passes PCM) and calls Whisper (e.g. Groq).
   - Returns or broadcasts: `"Display Name : transcribed text"`.

No JVB or Jicofo code changes; no Jibri; works with any self-hosted Meet that serves lib-jitsi-meet.

---

## 4. Extracting and Decoding Audio (Opus → PCM)

- **In Jitsi (browser)**: You do **not** handle Opus directly. The browser’s WebRTC stack decodes the remote Opus stream into a `MediaStreamTrack`. You only read decoded PCM from that track via the Web Audio API.
- **Pipeline**:
  1. `remoteTrack.getOriginalStream()` (or the track’s underlying `MediaStream`) → one stream per participant.
  2. `audioContext.createMediaStreamSource(stream)`.
  3. `ScriptProcessorNode` (or AudioWorklet) with `onaudioprocess`: input is Float32 PCM. Convert to Int16 if your backend expects 16-bit, then send (e.g. base64 or binary WebSocket frame).
- **Sample rate**: Jitsi/WebRTC often uses 48 kHz; Whisper commonly expects 16 kHz. Resample in the browser (e.g. with a simple linear interpolator or a small lib) or on the server before calling Whisper. Your backend can use `librosa` or `scipy` to resample 48→16 kHz if needed.

---

## 5. Sending Audio to Speech-to-Text (Whisper)

- **Chunking**: Send segments of ~5–10 seconds per participant so that:
  - Latency is acceptable.
  - You have enough context for Whisper to work well.
- **Format**: Build a WAV (44-byte header + Int16 PCM) or send raw PCM with sample rate and channels; backend converts to WAV and calls Groq’s `audio.transcriptions.create(file=(filename, wav_bytes), ...)`.
- **Concurrency**: Run one transcription request per participant chunk; use a queue so you don’t overload the API. Optionally merge very short segments to reduce API calls.

---

## 6. How Speaker Identification Works in Jitsi

- **No guessing**: In Jitsi (and in WebRTC in general), each remote participant has at least one audio track. When you receive `TRACK_ADDED`, the event payload (or the track object) gives you:
  - The **participant ID** (Jitsi’s internal id).
  - Access to the **participant object** so you can read **display name** (and optionally email if set).
- So for each audio chunk you already know: “this audio is from participant X with display name Y.” You never need to run a separate speaker-diarization model; the format is always:

  `Display Name : transcribed text`

- **Edge cases**: If a participant leaves and rejoins, they may get a new participant ID; treat them as a new “speaker” for that session or map by display name if you want to merge.

---

## 7. Example Code Snippets

### 7.1 Bot page (browser): join + TRACK_ADDED + send PCM

```javascript
// Load lib-jitsi-meet from your self-hosted Jitsi
// <script src="https://meet.yourdomain.com/libs/lib-jitsi-meet.min.js"></script>

const JITSI_DOMAIN = 'meet.yourdomain.com';
const ROOM_NAME = 'MyRoom';
const BOT_DISPLAY_NAME = 'Meeting Assistant';
const WS_URL = 'wss://your-backend.com/ws/jitsi-transcription';

let connection, room, audioContext;
const participantBuffers = new Map(); // participantId -> { displayName, chunks }

function init() {
  JitsiMeetJS.init();
  const options = {
    hosts: { domain: JITSI_DOMAIN },
    serviceUrl: `https://${JITSI_DOMAIN}/http-bind`,
  };
  connection = new JitsiMeetJS.JitsiConnection(null, null, options);
  connection.addEventListener(JitsiMeetJS.events.connection.CONNECTION_ESTABLISHED, () => {
    room = connection.initJitsiConference(ROOM_NAME, {
      startAudioOnly: true,
      startWithAudioMuted: true,
    });
    room.setDisplayName(BOT_DISPLAY_NAME);
    room.on(JitsiMeetJS.events.conference.TRACK_ADDED, onRemoteTrack);
    room.on(JitsiMeetJS.events.conference.CONFERENCE_JOINED, () => console.log('Bot joined'));
    room.join();
  });
  connection.connect();
}

function onRemoteTrack(track) {
  if (track.getType() !== 'audio') return;
  const participantId = track.getParticipantId?.() ?? track.participantId;
  const participant = room.getParticipantById?.(participantId);
  const displayName = participant?.getDisplayName?.() ?? participant?.displayName ?? `Participant ${participantId}`;

  const stream = track.getOriginalStream?.() ?? new MediaStream([track.track]);
  audioContext = audioContext || new (window.AudioContext || window.webkitAudioContext)();
  const source = audioContext.createMediaStreamSource(stream);
  const processor = audioContext.createScriptProcessor(4096, 1, 1);
  const buffer = [];
  const SAMPLE_RATE = audioContext.sampleRate;
  const CHUNK_DURATION_MS = 8000;
  const SAMPLES_PER_CHUNK = (SAMPLE_RATE * CHUNK_DURATION_MS) / 1000;

  processor.onaudioprocess = (e) => {
    const input = e.inputBuffer.getChannelData(0);
    for (let i = 0; i < input.length; i++) buffer.push(input[i]);
    if (buffer.length >= SAMPLES_PER_CHUNK) {
      const chunk = buffer.splice(0, SAMPLES_PER_CHUNK);
      const int16 = new Int16Array(chunk.length);
      for (let i = 0; i < chunk.length; i++) int16[i] = Math.max(-32768, Math.min(32767, chunk[i] * 32768));
      sendToBackend(participantId, displayName, int16.buffer, SAMPLE_RATE);
    }
  };
  source.connect(processor);
  processor.connect(audioContext.destination);
}

function sendToBackend(participantId, displayName, pcmBuffer, sampleRate) {
  const ws = new WebSocket(WS_URL);
  ws.onopen = () => {
    ws.send(JSON.stringify({ participantId, displayName, sampleRate }));
    ws.send(pcmBuffer);
    ws.close();
  };
}
```

### 7.2 Backend (Python): receive PCM, build WAV, call Groq Whisper

```python
# Pseudocode – adapt to your FastAPI WebSocket
import struct
import base64
import io
from app.services.groq_processing import transcribe_audio

def pcm_to_wav(pcm_int16_bytes: bytes, sample_rate: int = 16000, channels: int = 1) -> bytes:
    n = len(pcm_int16_bytes) // 2
    buf = io.BytesIO()
    buf.write(b'RIFF')
    buf.write(struct.pack('<I', 36 + n * 2))
    buf.write(b'WAVEfmt ')
    buf.write(struct.pack('<IHHIIHH', 16, 1, channels, sample_rate, sample_rate * channels * 2, channels * 2, 16, 0))
    buf.write(b'data')
    buf.write(struct.pack('<I', n * 2))
    buf.write(pcm_int16_bytes)
    return buf.getvalue()

async def websocket_handler(websocket):
    msg = await websocket.receive_json()
    participant_id = msg["participantId"]
    display_name = msg["displayName"]
    sample_rate = msg.get("sampleRate", 48000)
    pcm_b64 = await websocket.receive_bytes()  # or receive_text and base64 decode
    pcm = base64.b64decode(pcm_b64)
    # Resample 48k -> 16k if needed (e.g. with librosa)
    wav = pcm_to_wav(pcm, sample_rate)
    text = transcribe_audio(wav, "segment.wav")
    return f"{display_name} : {text}"
```

---

## 8. Common Pitfalls and How to Avoid Them

| Pitfall | Mitigation |
|--------|------------|
| **CORS / mixed content** | Serve the bot page from the same origin as your backend, or configure your Jitsi and backend to allow the bot’s origin. Load lib-jitsi-meet from your Jitsi domain. |
| **Bot not joining** | Use the same Jitsi domain and room name as the meeting; ensure no firewall blocks WebSocket (BOSH) to `https://meet.yourdomain.com/http-bind`. |
| **No TRACK_ADDED for some users** | Ensure the bot has actually joined the conference and that the other user has granted microphone; check for track type `audio`. |
| **Wrong sample rate for Whisper** | Whisper expects 16 kHz; if you capture at 48 kHz, resample before sending to Whisper (browser or server). |
| **High latency** | Use short chunks (5–10 s), parallelize transcription per participant, and consider streaming Whisper if your provider supports it. |
| **Display name empty** | Fallback to `Participant <id>`; encourage users to set display names in Jitsi. |
| **Memory growth** | Don’t keep unbounded buffers per participant; flush and clear after sending each chunk. |
| **Too many API calls** | Batch small segments (e.g. merge < 3 s) or throttle per participant. |

---

## 9. Scalability and Production

- **One bot per meeting**: Run one Playwright browser (or one bot process) per Jitsi room. Use a job queue (e.g. Celery, Bull) to start/stop bots when meetings are created/ended.
- **Horizontal scaling**: Run multiple worker machines; each runs N bot instances (N limited by RAM/CPU per Chromium). Backend WebSocket servers can be behind a load balancer with sticky sessions if you need state per connection.
- **Resilience**: If the bot crashes, restart it and rejoin the same room; Jitsi will re-send TRACK_ADDED for current participants.
- **Security**: Use JWT or a token for the meeting room if your Jitsi is configured that way; pass the token when joining. Restrict WebSocket endpoint to authenticated clients or to your bot runner only.

---

## 10. References

- [lib-jitsi-meet API (low level)](https://jitsi.github.io/handbook/docs/dev-guide/dev-guide-ljm-api)
- [Jitsi Meet IFrame API](https://jitsi.github.io/handbook/docs/dev-guide/dev-guide-iframe)
- [Jitsi TRACK_ADDED and track API](https://github.com/jitsi/lib-jitsi-meet)
- [Groq Whisper (Speech-to-Text)](https://console.groq.com/docs/speech-to-text)

The implementation in this repo follows this architecture:

- **Bot runner**: `jitsi-bot/runner.js` (Node.js + Playwright) opens the capture page with configurable Jitsi domain, room, and bot name.
- **Capture page**: `backend/static/jitsi-bot/capture.html` loads lib-jitsi-meet, joins the room, captures per-participant audio, and sends PCM chunks to the backend WebSocket. For simplicity it opens one WebSocket per ~8 s chunk; production can keep one WebSocket per participant and send multiple chunks on the same connection.
- **Backend**: `backend/app/api/v1/endpoints/jitsi_live.py` exposes WebSocket `/api/v1/ws/jitsi-live`, builds WAV from PCM (with 48k→16k resampling), and calls Groq Whisper; response format is `"Display Name : text"`.
