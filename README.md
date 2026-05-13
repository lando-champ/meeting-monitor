# CONSILIUM
### AI-Powered Project Intelligence Platform

CONSILIUM is an agentic AI-powered project management platform that automates project planning, monitoring, workflow synchronization, and risk detection using multi-agent orchestration.

The platform combines:
- AI-generated PRDs
- Intelligent project planning
- GitHub-integrated Kanban automation
- Meeting intelligence
- Risk monitoring
- LangGraph-based autonomous workflows

---

# 🚀 Features

## 📄 Requirements Agent
- Generates structured PRDs from product briefs
- Performs competitor research and analysis
- Converts kickoff meeting transcripts into requirement documents

## 🧠 Planning Agent
- Automatically creates:
  - Roadmaps
  - Task graphs
  - Dependencies
  - Kanban workflows
- Generates structured project plans using AI reasoning

## 📋 Intelligent Kanban Board
- Drag-and-drop task management
- Automatic task status synchronization
- AI-assisted task organization

## 🔗 GitHub Integration
- GitHub OAuth & webhook support
- Commit-to-task mapping
- PR-based Kanban updates
- CI/CD-aware task progression

## 🎤 Meeting Intelligence
- Jitsi meeting bot integration
- Speech-to-text transcription pipeline
- Transcript summarization
- Action-item extraction
- Blocker detection

## ⚠️ Monitoring Agent
- Continuous project monitoring
- Risk prediction and scoring
- Stale task detection
- Automated workflow reconciliation

## 📊 Analytics Dashboard
- Sprint velocity tracking
- Burndown monitoring
- Risk visualization
- Activity analytics

---

# 🏗️ System Architecture

CONSILIUM uses a LangGraph-based multi-agent architecture consisting of:

| Agent | Responsibility |
|---|---|
| Requirements Agent | PRD generation & research |
| Planning Agent | Task decomposition & roadmap planning |
| Monitoring Agent | Risk detection & workflow synchronization |

The platform follows a plan-and-execute reasoning loop with:
- Persistent memory
- Conditional routing
- Human-in-the-loop approvals
- Event-driven monitoring

---

# 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Tailwind CSS |
| Backend | FastAPI |
| Agent Orchestration | LangGraph |
| Database | MongoDB Atlas |
| Vector Database | FAISS |
| Speech-to-Text | faster-whisper |
| Embeddings | sentence-transformers |
| LLMs | Ollama llama3.1:70b & 8b |
| Integrations | GitHub MCP Server |

---

# 🧠 AI Capabilities

## Agentic Workflows
- Autonomous decision-making
- Multi-step reasoning
- Continuous monitoring
- Dynamic workflow execution

## Retrieval-Augmented Generation (RAG)
- Task evidence retrieval
- Transcript recurrence analysis
- Historical project grounding

## Meeting Intelligence
- Transcript summarization
- Commitment extraction
- Blocker recurrence scoring

---

# 📂 Project Structure

```bash
CONSILIUM/
│
├── frontend/              # React frontend
├── backend/               # FastAPI backend
├── agents/                # LangGraph agent workflows
├── integrations/          # GitHub + Meeting integrations
├── monitoring/            # Monitoring loop & risk analysis
├── rag/                   # FAISS & embeddings pipeline
├── database/              # MongoDB models & schemas
├── tests/                 # Automated tests
└── docs/                  # Documentation
