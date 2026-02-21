# How to Run Meeting Monitor

Follow these steps to run the full app (frontend + backend). Optionally run the Jitsi transcription bot for live meeting transcripts.

---

## Prerequisites

- **Node.js** 18+ and **npm**
- **Python** 3.10+
- **MongoDB** (local or a connection string)
- **Groq API key** (for transcription and summaries) – [get one here](https://console.groq.com/)

---

## 1. Backend (API)

### 1.1 Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 1.2 Configure environment

Create `backend/.env` (copy from below or from `backend/.env.example` if it exists):

```env
# MongoDB
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=meeting_monitor

# JWT (change in production)
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Groq (required for transcription & summaries)
GROQ_API_KEY=your_groq_api_key_here

# Jitsi (optional; default is meet.jit.si)
JITSI_DOMAIN=meet.jit.si

# CORS (frontend origin)
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000","http://localhost:8080"]

# Server
HOST=0.0.0.0
PORT=8000
```

Replace `your_groq_api_key_here` with your real Groq API key.

### 1.3 Start MongoDB

If MongoDB is installed locally:

```bash
# Windows (if installed as service it may already be running)
# Or start manually: mongod

# macOS / Linux
mongod
```

If you use MongoDB Atlas, set `MONGODB_URL` in `.env` to your Atlas connection string.

### 1.4 Seed the database (first time)

Creates test users and sample data. All test passwords: **password123**.

```bash
cd backend
python -m scripts.seed_db
```

(Or from repo root: `python -m backend.scripts.seed_db` – run from where your `PYTHONPATH` includes the repo root, or run from `backend` as above.)

### 1.5 Run the backend

```bash
cd backend
python run.py
```

Backend runs at **http://localhost:8000**.

- API docs: http://localhost:8000/docs  
- Health: http://localhost:8000/health  

---

## 2. Frontend (React + Vite)

### 2.1 Install dependencies

```bash
# From project root
npm install
```

### 2.2 Point frontend at the API (optional)

If the API is not at `http://localhost:8000`, create a `.env` in the **project root**:

```env
VITE_API_URL=http://localhost:8000
```

### 2.3 Run the frontend

```bash
npm run dev
```

Frontend runs at **http://localhost:5173** (or the port Vite prints).

Open that URL in a browser, then:

1. **Sign in** – e.g. manager: use the email from seed (e.g. `manager@example.com`) and password `password123`.
2. Open a **workspace** (or create/join one).
3. Go to **Meetings** – schedule a meeting or create an instant meeting; the Jitsi link is created automatically. Members of the project can **Join** from the same Meetings list.

---

## 3. Jitsi transcription bot (optional)

Use this when a meeting is **live** to get real-time **Speaker : text** transcript on the meeting details page.

### 3.1 Install and run the bot

```bash
cd jitsi-bot
npm install
npm start
```

By default the bot joins **meet.jit.si** room **MeetingMonitor**. To tie it to a specific meeting:

1. **Start the meeting** from the app (Manager → Meetings → View → “Start meeting”).
2. On the meeting details page, click **“Start transcription bot”**.
3. If the backend returns a **bot_url**, open that URL in a browser (or the backend may start the bot automatically if `JITSI_BOT_RUNNER_PATH` is set).

### 3.2 Custom room / domain

```bash
# Use your own Jitsi server and room name
JITSI_DOMAIN=meet.yourdomain.com ROOM_NAME=YourRoomName node runner.js
```

For a meeting created in the app, use the **“Start transcription bot”** button on the meeting details page; it will pass the correct room and `meeting_id` so the transcript appears on that meeting.

---

## Quick checklist

| Step | Command | Where |
|------|--------|--------|
| 1 | `pip install -r requirements.txt` | `backend/` |
| 2 | Create `backend/.env` with `GROQ_API_KEY`, MongoDB, etc. | `backend/` |
| 3 | Start MongoDB | System / Atlas |
| 4 | `python -m scripts.seed_db` | `backend/` |
| 5 | `python run.py` | `backend/` |
| 6 | `npm install` | Project root |
| 7 | `npm run dev` | Project root |
| 8 | Open http://localhost:5173 and sign in | Browser |

---

## Troubleshooting

- **Backend won’t start** – Check MongoDB is running and `MONGODB_URL` in `backend/.env` is correct.
- **“Could not validate credentials”** – Log in again; token may have expired (default 30 min).
- **Upload / transcription fails** – Ensure `GROQ_API_KEY` is set in `backend/.env`.
- **Bot doesn’t join** – Confirm the bot’s room name matches the meeting’s Jitsi room; use “Start transcription bot” from the meeting details page so `meeting_id` is set.
- **CORS errors** – Add your frontend origin (e.g. `http://localhost:5173`, `http://localhost:8080`) to `CORS_ORIGINS` in `backend/.env`.
- **“No 'Access-Control-Allow-Origin' header” / 405 on register or login** – If the response shows **Server: nginx**, your browser is talking to **Nginx**, not the FastAPI app. Nginx is answering OPTIONS with 405 and no CORS headers.
  - **Option A (recommended for local dev):** Bypass Nginx. Run the backend on a port Nginx doesn’t use (e.g. **8001**). In `backend/.env` set `PORT=8001`, restart the backend, and in the **project root** create or edit `.env` with `VITE_API_URL=http://localhost:8001`. Restart the frontend and use that URL. The app will then talk directly to FastAPI and CORS will work.
  - **Option B:** Fix Nginx so it allows CORS and OPTIONS. Use the snippet in **nginx-cors-example.conf** in this repo: add the OPTIONS block and CORS headers to the `location` that proxies to your API, then reload Nginx.

For more on the Jitsi bot and architecture, see **docs/JITSI_MEETING_ASSISTANT_ARCHITECTURE.md**.
