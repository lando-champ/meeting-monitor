# Definition of Done — Meeting stack, RAG, reconciliation, analytics, evaluation

Use this checklist before calling a milestone “demo-ready”.

## 1. Meeting bot + live STT

- [ ] Start meeting with valid `meeting_url` creates/updates meeting doc as `live`.
- [ ] Bot joins (or fails with a clear, logged reason: Selenium/Chrome/driver).
- [ ] PCM reaches `/api/v1/ws/audio/{meeting_id}` (when `MEETING_AUDIO_WS_SECRET` is set, URL includes matching `ws_secret`).
- [ ] Transcript segments appear in Mongo within expected latency (Groq + `STT_BUFFER_SECONDS`).
- [ ] Stop meeting sets `ended`, stops bot, clears WS pipeline state, runs post-meeting intelligence.

## 2. Live transcript in UI

- [ ] While meeting is `live`, browser opens `/api/v1/ws/meeting/{id}/live` with `access_token` when `MEETING_LIVE_WS_REQUIRE_AUTH=true` (or without token when auth is disabled for dev).
- [ ] Server-pushed lines appear in the UI without waiting for the 15s poll.
- [ ] Reconnect with backoff after disconnect.

## 3. Transcript RAG (cross-feature)

- [ ] Kanban rebuild still uses embeddings + FAISS when `KANBAN_RAG_ENABLED=true`.
- [ ] Meeting “ask” can optionally use project-wide RAG (`project_rag: true`) when `TRANSCRIPT_RAG_FOR_QA_ENABLED=true` and `sentence-transformers` + `faiss` are installed.
- [ ] Optional disk cache: `TRANSCRIPT_RAG_CACHE_DIR` speeds repeat asks for the same project.

## 4. Transcript–task reconciliation

- [ ] After meeting intelligence + Kanban sync, auto-generated tasks for the project are checked against meeting transcript text.
- [ ] Tasks without verifiable evidence get `transcript_evidence_ok: false` and `transcript_evidence_note` set.
- [ ] No crash when transcript is empty.

## 5. Analytics

- [ ] `GET /api/v1/projects/{project_id}/analytics/burndown` returns weekly buckets for the signed-in member’s project.
- [ ] Manager Analytics page shows burndown/velocity charts from that API (not only pie chart).

## 6. Evaluation (CI)

- [ ] `pytest backend/tests -q` passes in CI (GitHub Actions).
- [ ] Golden tests cover transcript evidence validation and RAG chunking invariants (skip if heavy ML deps unavailable).
