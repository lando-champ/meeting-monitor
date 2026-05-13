# Demo script — Meeting stack through analytics

Prerequisites: backend on `BACKEND_URL`, frontend with `VITE_API_URL` pointing at API, valid user JWT, Groq key for STT, Chrome + Chromedriver for bot (if using real bot).

## A. Auth and project

1. Register/login via UI or `POST /api/v1/auth/login/json`.
2. Create or open a workspace project; note `project_id`.

## B. Start meeting and bot

1. `POST /api/v1/meetings` with `{ "project_id": "<id>", "title": "Demo" }` → save `meeting_id`.
2. `POST /api/v1/meetings/{meeting_id}/start` with `{ "meeting_url": "<jitsi-or-meet-url>", "project_id": "<id>", "title": "Demo" }`.
3. Optional: `GET /api/v1/meetings/{meeting_id}/bot-status` → `bot_running`, `bot_audio_streaming`.

## C. Live transcript (UI)

1. Open corporate meeting details for the meeting (manager or member route).
2. Confirm “Server transcript” lines appear when the bot is streaming (WS).
3. Stop meeting from UI; confirm status `ended`.

## D. Meeting Q&A with project RAG

1. `POST /api/v1/meetings/{meeting_id}/ask` with body:
   ```json
   { "question": "What did we decide about deadlines?", "project_rag": true }
   ```
2. Requires `TRANSCRIPT_RAG_FOR_QA_ENABLED=true` and prior transcripts on the project.

## E. Reconciliation

1. After stop, inspect tasks in Mongo or Kanban: fields `transcript_evidence_ok`, `transcript_evidence_note` on `is_auto_generated` tasks.

## F. Analytics

1. `GET /api/v1/projects/{project_id}/analytics/burndown?weeks=8` with `Authorization: Bearer <token>`.
2. Open Manager → Analytics; confirm burndown/velocity section loads.

## G. Tests

```bash
cd backend && pytest tests -q
```
