# Agentic AI (B24EAS601) — Final Project Report

**CONSILIUM — AI-Powered Project Intelligence Platform**

| Field | Value |
|--------|--------|
| **Team Number** | TEAM - 09 |
| **Course** | Agentic AI (B24EAS601) |
| **Date** | April 2026 |
| **Team Members** | Vyshali NS; BT Chinmayi |

---

## 1. Executive Summary

Modern software teams spread product intent across requirements documents, meetings, task boards, and version control. That fragmentation causes drift, duplicated status updates, and late discovery of risk. **CONSILIUM** is an agentic project intelligence system that treats the workspace as a living state machine: requirements can be researched and structured automatically, plans can be generated and maintained as structured tasks and dependencies, and ongoing signals from meetings and repository activity can be reconciled with the plan through a monitored reasoning loop rather than ad hoc prompting.

The solution combines a web application for managers and engineers with a backend orchestration layer built around **LangGraph**, persistent workspace state, and selective use of large language models for synthesis and decision support. Informal development testing suggests clearer traceability from meetings to tasks when meeting intelligence is enabled, faster first drafts of PRD-style artifacts when research tooling is enabled, and a more defensible automation posture when high-impact plan changes are staged for human review while routine monitoring runs on a schedule.

---

## 2. Problem Statement and Objectives

### 2.1 The problem

Product requirements, standup discussions, Kanban state, and GitHub activity often live in separate tools. Teams manually reconcile them each sprint, which is slow and error-prone. Risks mentioned verbally may never become tracked work; repository events may not map cleanly to roadmap commitments.

### 2.2 Objectives

- Reduce manual synchronization between “what we agreed,” “what we planned,” and “what the code shows.”
- Provide an **agentic** layer that can operate on schedules and events, not only on user chat turns.
- Preserve human judgment for high-impact structural changes while automating repetitive reconciliation.

### 2.3 Why an agentic approach

- **Autonomy:** Monitoring and enrichment can run on a timer and react to external signals (for example repository activity and post-meeting summaries) without a user re-prompting each time.
- **Tool use:** Requirements research benefits from chained steps such as search, retrieval, and structured extraction rather than one-shot generation from memory.
- **Multi-step reasoning:** Converting heterogeneous signals into consistent task updates, risk notes, and notifications benefits from intermediate representations and conditional routing, not a single completion.

### 2.4 Measurable goals (design targets)

Report these as **targets** unless backed by a controlled benchmark:

- Reduce time from product brief to a reviewable structured PRD.
- Reduce manual Kanban updates driven by linked repository activity and meeting-derived signals.
- Surface project risks earlier than “deadline day surprises.”
- Keep human control over consequential plan changes via staging and policy flags.

---

## 3. System Architecture

### 3.1 Agentic framework

CONSILIUM uses **LangGraph** as the orchestration framework because it represents execution as explicit steps with conditional routing, supports checkpointed state for long-running workspace threads, and makes monitoring and escalation flows easier to reason about than a single monolithic prompt chain.

### 3.2 Composite agent personas (product story)

CONSILIUM is described as **two composite agents** that map cleanly to how teams think about work:

**1) Planning and Replanning (single role)**

- **Plan:** From structured requirements, produce roadmap phases, tasks, dependencies, and an initial board mapping.
- **Gate:** Large structural replans can be **human-gated** (staged plan + explicit approval) when workspace policy requires it.
- **Replan:** When monitoring indicates sustained failure modes, propose **minimal corrective deltas** (reassignment, reprioritization, dependency fixes) rather than rewriting the entire plan unless severity demands it.

**2) Monitoring, Risk, and Notification (single role)**

- **Monitor:** Ingest live signals (repository activity when linked; meeting summaries and meeting-derived signals when enabled).
- **Assess risk:** Convert signals into a coherent health picture (blockers, delays, severity-ranked risks).
- **Act and explain:** Emit structured updates and user-visible notifications with enough context for a PM to trust the change.

**Implementation note (for reviewers):** These two roles are implemented as a **LangGraph workflow with multiple steps** (for example: planning combined with execution of queued actions; monitoring combined with execution and conditional routing; replanning combined with execution; notifications as a dedicated step). This preserves an agentic story while remaining **auditable** and modular.

### 3.3 Reasoning loop

**Pattern:** Plan-and-execute with **continuous monitoring and conditional escalation**.

1. **Plan or refresh the plan** when requirements change or when a workspace needs initialization.
2. **Monitor** on a scheduled cadence (**deployment-configurable**; default backend monitoring is on the order of **minutes**, not seconds, unless explicitly changed).
3. If monitoring detects meaningful deltas, **execute** structured pending actions subject to automation policy.
4. If health and decision rules indicate escalation, route to **risk analysis** and optionally **replanning**, then **notify** stakeholders.

Conditional routing reduces how often expensive replanning runs, while monitoring can still run regularly.

### 3.4 Architecture diagram (subsystem view)

Five subsystems for the diagram legend:

- **Web client:** workspace UI, Kanban, activity feed, integrations.
- **API service:** authentication, persistence, meeting ingestion, webhook endpoints.
- **Requirements processing:** research and PRD structuring workflows.
- **Planning processing:** roadmap and task graph generation; optional validation and repair of dependency structure.
- **Live signals:** repository connectivity; meeting capture and intelligence pipelines.

**Data store:** MongoDB holds workspace state, tasks, meeting artifacts and signals, notifications, and related operational data. Checkpointing may use dedicated checkpoint collections when enabled.

---

## 4. Implementation Details

### 4.1 Technical stack

- **Frontend:** TypeScript, React, Vite.
- **Backend:** Python, FastAPI, asynchronous I/O.
- **Database:** MongoDB.
- **Orchestration:** LangGraph with checkpointing (memory-oriented checkpointers for automated tests; Mongo-backed checkpoints in integrated deployments when configured).
- **Models:** Hosted LLM APIs for synthesis and monitoring-style decisions; hosted transcription in typical configurations, with optional local speech-to-text where operators enable it.
- **Retrieval (optional / feature-flagged):** Embedding models and vector indexes for grounding planning and monitoring on transcripts when enabled.

### 4.2 Memory architecture

- **Working state:** A workspace-oriented state object loaded for graph invocations, including PRD fields, team roster, roadmap, tasks, dependency graph, Kanban mapping, processed event identifiers, hashes for idempotency, risk-related fields, pending actions, staged plan metadata, and activity history.
- **Longer-horizon grounding (RAG):** When enabled, retrieval supplies analogous task evidence and transcript snippets to reduce hallucinated scope and improve meeting-to-task alignment. Name specific embedding libraries and index sizes only for configurations you actually run in demo or production.

### 4.3 Key engineering challenges (defensible framing)

- **Stateful orchestration:** Checkpointing and stable thread identifiers per workspace.
- **Idempotency:** Skip redundant model work when external signal payloads are unchanged (hashing and deduplication patterns).
- **Action execution policy:** Separate “proposed change” from “applied change” using staged actions and automation toggles.
- **Integration correctness:** OAuth callback URLs, webhook authenticity, and environment-consistent configuration.

### 4.4 Feature completion status

| Capability | Status (example) | Notes |
|------------|------------------|--------|
| PRD generation with research tools | Shipped / Partial | Fill based on demo |
| Planning and dependency-aware tasks | Shipped / Partial | Fill based on demo |
| Scheduled monitoring and GitHub signals | Shipped / Partial | Fill based on demo |
| Meeting intelligence and signals | Shipped / Partial | Fill based on demo |
| Notifications and activity feed | Shipped / Partial | Fill based on demo |
| Production packaging and hardening | Planned / Partial | Fill based on roadmap |

---

## 5. Beta Testing and User Evaluation Report

**Disclaimer:** Quantitative timings, percentages, and satisfaction scores in pilot write-ups should be labeled **illustrative** unless you attach raw survey responses, interview notes, or system logs in Appendix C.

### 5.1 Testing approach

Describe who participated, duration, and scripted tasks (for example: create workspace from brief, review PRD, connect GitHub, respond to a risk or replan prompt). If testing was informal, say so explicitly.

### 5.2 User feedback (qualitative)

Summarize themes: speed of first PRD draft, trust in board updates when repository activity is visible, usefulness of risk or blocker notifications, friction in meeting or bot setup.

### 5.3 Usability testing

Document three workflows you observed and what improved after iteration (navigation, modals, approval diff clarity).

### 5.4 Edge cases observed

List real issues you saw (ambiguous meeting language, long transcripts, duplicate webhook deliveries, concurrent monitoring) and how you mitigated them—without claiming specific numeric lifts unless measured.

### 5.5 Feature requests (prioritized)

Rank follow-ups such as simpler meeting join, richer explanations in the activity feed, chat integrations, multi-repo monitoring, and evaluation harnesses.

---

## 6. Performance Metrics and Results

### 6.1 System observability (recommended)

Report metrics you can extract from logs or dashboards: monitoring loop duration distribution, API error rate, webhook handling latency, graph invocations per workspace per day.

### 6.2 Model and workflow evaluation

Include precision, recall, F1, or latency **only** if you ran a labeled evaluation. Otherwise present **targets** and the planned evaluation protocol (Appendix C).

---

## 7. Ethical Considerations and Safety

- **Schema and validation:** Validate structured agent outputs before persisting; reject or log invalid payloads without corrupting workspace state.
- **Human review:** Major plan changes can be staged behind approval when policy requires; describe the default posture for your deployment honestly.
- **Secrets and scopes:** OAuth tokens and webhook secrets must be protected; use least-privilege GitHub scopes.
- **Privacy:** State clearly whether meeting audio or transcripts are processed by a vendor API or local inference in the configuration you demonstrate; describe data retention and access control at a high level.

Avoid absolute claims (“never applies autonomously,” “never leaves the network”) unless they are true for **every** action type and environment you ship.

---

## 8. Conclusion and Future Work

### 8.1 Conclusion

CONSILIUM demonstrates that binding requirements, execution signals, and meeting-derived context into one workspace—with LangGraph-style orchestration—can reduce coordination overhead while keeping humans in the loop for consequential decisions.

### 8.2 Future work

- Multi-repository monitoring for service-oriented teams.
- Chat integrations (Slack, Microsoft Teams) for notifications and approvals.
- Stronger explainability UI for “why this task moved.”
- Repeatable offline evaluation datasets and regression tests for extraction quality.
- Optional cost controls such as self-hosted inference; phrase as an **option**, not the default, unless it is your actual deployment model.

---

## 9. References and Appendices

### 9.1 References (trim to what you actually used)

- LangGraph documentation — https://langchain-ai.github.io/langgraph/
- FastAPI documentation — https://fastapi.tiangolo.com/
- MongoDB documentation — https://www.mongodb.com/docs/
- GitHub OAuth and webhooks — https://docs.github.com/
- Sentence Transformers — https://www.sbert.net/ (if RAG enabled)
- FAISS — https://github.com/facebookresearch/faiss (if RAG enabled)
- faster-whisper — https://github.com/SYSTRAN/faster-whisper (if local STT enabled)

### 9.2 Project links

- **GitHub repository:** [Insert URL]
- **Demo video (YouTube):** [Insert URL]

---

### Appendix A — Architecture diagram

**Legend update:** Show the LangGraph area as two swimlanes:

- **Planning + Replanning path** (initial plan, staged major replans, minimal deltas).
- **Monitoring + Risk + Notify path** (scheduled pull of signals, health scoring, notifications).

Optionally inset a small “internal steps” box listing graph merge steps for technical readers, without contradicting the two composite roles.

*[Insert architecture diagram image here.]*

---

### Appendix B — Division of labour

| Area | Primary owner | Supporting owner |
|------|----------------|------------------|
| Requirements and PRD flows | [Name] | [Name] |
| Planning, graph, and monitoring | [Name] | [Name] |
| Frontend, integrations, UX | [Name] | [Name] |
| DevOps, evaluation, documentation | [Name] | [Name] |

Both team members may contribute across areas; adjust rows to match reality.

---

### Appendix C — Evaluation and dataset summary

Choose one:

**Option A — Planned evaluation protocol:** Describe intended benchmarks, labeling scheme, and success criteria for PRD validity, task extraction, and monitoring decisions.

**Option B — Actual pilot summary:** Provide anonymized counts, instrument links, and a table of measured metrics with dates and environment notes.

---

*Document generated to match the editorial plan: two composite agents (Planning+Replanning; Monitoring+Risk+Notification), consistent monitoring cadence wording, and defensible claims only.*
