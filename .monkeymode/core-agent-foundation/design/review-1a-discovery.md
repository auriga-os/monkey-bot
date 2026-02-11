# Review: 1a-discovery.md

**Phase:** Design 1A - Discovery & Core Design
**Reviewed:** 2026-02-11T19:45:00Z

## Overview
Defines Emonk as an open-source AI agent framework with Google Chat integration, file-based memory, modular skill system, and Cloud Run deployment. Architecture uses modular monolith pattern with 6 core modules (Gateway, Agent Core, Skills, Memory, Terminal, Cron).

## Key Artifacts Defined
- Architecture: Modular Monolith on Cloud Run (single Python app, serverless deployment)
- Modules: Gateway (Google Chat webhook), Agent Core (LangGraph + Vertex AI), Skills (auto-discovery), Memory (file-based + GCS sync), Terminal (allowlist executor), Cron (local scheduler)
- Data model: ConversationMessage (markdown files), KnowledgeFact (JSON), CronJob (JSON), Skill (in-memory metadata)
- Security: PII filtering (hash user email), terminal allowlist (cat/ls/python/uv), path restrictions
- Tech stack: Python 3.11+, LangGraph, FastAPI, Vertex AI (Gemini 2.0), uv + .venv

## Dependencies
- Vertex AI API (Gemini 2.0 Flash/Pro models)
- Google Chat API (webhooks, Cards V2)
- GCS bucket for memory persistence (emonk-memory)
- No dependencies on prior phases (this is Phase 1A)

---

## Double Check These Sections

- **Gateway Module > Security**: Mentions "allowlist of authorized user emails/domains" but no implementation details on where/how this is configured
- **Gateway Module > Security**: States "Rate limiting (future)" - clarify if rate limiting is in scope for Phase 1 or explicitly deferred to Phase 3
- **Agent Core > LLM Strategy**: "when Flash fails or user requests" - no criteria defined for detecting Flash failures (error codes? latency threshold?)
- **Agent Core > LLM Strategy**: "Streaming: For responses > 200 tokens" - no justification for 200 token threshold
- **Memory Module > GCS Sync Strategy**: "Download if local doesn't exist or is stale" - "stale" not defined (age threshold? checksum mismatch?)
- **Memory Module > GCS Sync Strategy**: "Conflict resolution: Last-write-wins (single user, no conflicts expected)" - what happens with multiple Cloud Run instances writing simultaneously?
- **Memory Module > GCS Sync**: "Handle sync failures gracefully (log error, continue with local)" - what if sync fails for extended period? Data loss risk on instance restart?
- **Terminal Executor > Security Model**: Allows "python" command but no validation of Python script content - skills could contain arbitrary code
- **Cron Module > Phase 1 Implementation**: "Not suitable for Cloud Run (stateless)" - contradicts deployment model (entire app deployed to Cloud Run in Phase 1)
- **Cron Module > Phase 1 Implementation**: If cron is local-only and Cloud Run is stateless, how does cron work in Phase 1 Cloud Run deployment?
- **Data Model > ConversationMessage**: No conversation context window size defined - how many messages included in LLM context?
- **Data Model > Skill**: No conflict resolution if two skills have same name in ./skills/ directory
- **Data Flow Example 1**: Shows GCS sync after memory write, but no error handling if GCS sync fails
- **Deployment > Cloud Run**: "--allow-unauthenticated" contradicts security requirement of user email allowlist (anyone can hit webhook)
- **Deployment > Environment Variables**: GOOGLE_CHAT_WEBHOOK_SECRET for signature verification - implementation details not in Gateway security section
- **Security > Google Chat PII Filtering**: Shows example code but doesn't specify where in codebase this validation happens (before or after webhook signature check?)
- **Security > Terminal Execution**: ALLOWED_PATHS uses relative paths ("./data/memory/") - no handling for symlinks or path traversal (../)
- **Observability > Metrics**: "Log-based metrics (no Prometheus for Phase 1)" - how are metrics calculated from logs? Manual analysis or Cloud Logging queries?
- **Performance > Optimization Strategies**: "Skills loaded at startup, not per request" - what happens if skills directory changes during runtime?
- **Open Source > Code Quality**: "Minimum 80% code coverage" - no mention of which components require higher coverage (e.g., security modules should be 100%)

---

## Potential Issues

### Gaps
- No webhook signature verification implementation details (only mentioned as bullet point in Gateway security)
- No definition of how user email allowlist is configured (env var? config file? GCS?)
- No error handling strategy for failed LLM calls (retry logic, fallback model, timeout)
- No specification of conversation context pruning (how many messages sent to LLM? token budget?)
- No rollback strategy for bad deployments (Cloud Run revision management not mentioned)

### Conflicts
- Cron module described as "Phase 1: local only" and "not suitable for Cloud Run" but entire Phase 1 deploys to Cloud Run (stateless)
- Security requires user email allowlist but deployment uses "--allow-unauthenticated" flag (webhook endpoint is public)
- Open source goal requires clean code but terminal executor trusts all Python scripts in ./skills/ (arbitrary code execution risk)

### Risks
- GCS sync failures could cause data loss on Cloud Run instance restart (no local persistence across restarts)
- Multiple Cloud Run instances writing to same GCS paths simultaneously (last-write-wins could cause message loss)
- Cron module won't work in Phase 1 if deployed to Cloud Run (stateless environment, in-memory registry lost on restart)
- Terminal executor allows "python" command with no script validation (skills can execute arbitrary code, security risk for open source)
- No authentication on webhook endpoint (anyone can send messages if they know URL, only email allowlist after webhook received)
- Conversation history stored in date-based markdown files could grow unbounded (no retention policy or size limits)

### Scope Creep
- Cron module included in Phase 1 despite being marked "not suitable for Cloud Run" and explicitly deferred to Phase 3 for Cloud Scheduler integration
- Streaming support for responses > 200 tokens adds complexity without clear user requirement (user said "simple but smart")
- Open source code quality standards (type hints, docstrings, 80% coverage, ruff, pre-commit hooks) not mentioned in user requirements - verify this is in scope

---

**Total lines: 78**
