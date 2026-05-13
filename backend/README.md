# Meeting Monitor Backend

FastAPI backend for Meeting Monitor application.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
```

3. Start MongoDB (if running locally):
```bash
mongod
```

4. Seed the database with initial data (optional, for development):
```bash
python -m scripts.seed_db
```

This will create:
- Test users (manager, member, teacher, student)
- Sample workspaces and classes
- Default password for all users: `password123`

5. Run the server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or use the run script:
```bash
python run.py
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Environment Variables

See `.env.example` for required configuration.

## Consilium LangGraph + Mongo checkpoints

The workspace agent graph compiles with a LangGraph checkpointer. By default checkpoints are stored in MongoDB collections `langgraph_checkpoints` and `langgraph_checkpoint_writes`, keyed by `thread_id` equal to the workspace id. For unit tests or environments without Mongo, set `CONSILIUM_CHECKPOINTER=memory`. Optional `LANGGRAPH_CHECKPOINT_TTL_SECONDS` sets a TTL index on those collections.

## MCP (Model Context Protocol)

Tool calls routed as `mcp/<server>` use HTTP JSON-RPC to URLs from `MCP_SERVERS` by default (`MCP_TRANSPORT=http`). To use a local **stdio** MCP server (for example the official GitHub MCP via `npx`), set `MCP_TRANSPORT=stdio` and provide `MCP_GITHUB_COMMAND` as a JSON array of argv strings (see `.env.example`). If stdio is enabled but a server has no command configured, execution falls back to HTTP when a URL exists. Anthropic-hosted example URLs in the code defaults are placeholders unless you supply real endpoints and credentials.

## Meeting signals + monitoring RAG

When post-meeting intelligence runs with a `project_id`, a `meeting_signals` document is emitted for Consilium. The next workspace graph run prefetches the latest unprocessed signal and marks it processed after a successful workspace update. Transcript RAG enrichment during monitoring is gated by `MONITORING_TRANSCRIPT_RAG_ENABLED` (default off) and uses the same embedding stack as Kanban RAG.
