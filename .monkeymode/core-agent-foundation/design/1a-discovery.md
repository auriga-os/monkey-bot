# Design: Emonk Core Agent Foundation - Phase 1A

## Executive Summary

Emonk is an open-source framework for building single-purpose AI agents that automate tasks via Google Chat. Phase 1 delivers a general-purpose agent with modular skill system, persistent file-based memory, secure command execution, and Google Chat integration. Designed for startup team usage (~1 user initially) with clean architecture that scales effortlessly when needed.

---

## Use Case & Business Value

### Problem Statement
Startup teams need a fast, flexible way to build AI agents that automate repetitive tasks (bug fixes, social media posting, data analysis). Existing solutions are either too complex (enterprise agent frameworks) or too rigid (single-purpose bots).

### Solution
Emonk provides a **lightweight agent framework** where developers can:
- Add custom skills via simple SKILL.md + Python files
- Deploy agents to Cloud Run with minimal configuration
- Interact via Google Chat (no custom UI needed)
- Maintain persistent memory across invocations
- Execute commands safely with allowlist-based security

### Success Metrics
- **Response Time:** < 2 seconds for simple queries, < 10 seconds for complex tasks
- **Developer Experience:** Add a new skill in < 30 minutes
- **Reliability:** 99% uptime for Cloud Run deployment
- **Privacy:** Zero Google Chat metadata sent to LLM

### Out of Scope (Phase 1)
- Multi-agent orchestration (future phases)
- Production-grade authentication (token-based is sufficient)
- Advanced observability (basic logging only)
- Web UI (Google Chat only)

---

## Architecture Decision

### Chosen Approach: **Modular Monolith on Cloud Run**

A single Python application deployed to Cloud Run with clear module boundaries. This balances simplicity (single deployment) with maintainability (modular code) and scalability (serverless auto-scaling).

**Why this approach?**
- **Simple:** One codebase, one deployment, one service to monitor
- **Scalable:** Cloud Run auto-scales from 0 to N instances
- **Cost-effective:** Pay only for actual usage (startup with 1 user)
- **Future-proof:** Clear module boundaries enable microservice split if needed later

---

## Architecture Approaches Considered

### Approach A: Microservices Architecture
**Description:** Separate services for Gateway, Agent Core, Skills, Memory, and Cron.

**Pros:**
- Independent scaling per component
- Technology flexibility (different languages per service)
- Fault isolation (one service failure doesn't crash everything)

**Cons:**
- Operational overhead (5+ services to deploy/monitor)
- Network latency between services
- Complex local development
- Overkill for 1-user startup usage

**Recommendation:** ❌ Too complex for current scale

---

### Approach B: Modular Monolith on Cloud Run
**Description:** Single Python application with clear module boundaries (core, gateway, skills, cron), deployed to Cloud Run.

**Pros:**
- Simple deployment (one service, one Docker image)
- No inter-service network latency
- Easy local development (run one process)
- Clear module boundaries enable future microservice split
- Cloud Run auto-scales (0 to N instances)
- Serverless (no infra management)

**Cons:**
- All components scale together (can't scale skills independently)
- Single point of failure (entire app goes down if one module crashes)
- Technology lock-in (all Python)

**Recommendation:** ✅ **Choose this** - Perfect balance for current needs, easy to evolve

---

### Approach C: Serverless Functions (Cloud Functions)
**Description:** Separate Cloud Functions for webhook, skill execution, cron jobs.

**Pros:**
- Finest-grained scaling (per function)
- Pay per invocation
- Simple deployment (no Docker)

**Cons:**
- Cold start latency (2-3 seconds for Python)
- Limited execution time (60s per function)
- Harder to share code between functions
- Debugging is more difficult

**Recommendation:** ❌ Cold starts hurt UX, 60s limit is restrictive for complex tasks

---

## Architecture Diagram

### System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Google Chat User                              │
└────────────────────────┬─────────────────────────────────────────────┘
                         │ HTTPS (Webhook)
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      Cloud Run (Emonk Service)                        │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                     Gateway Module                             │   │
│  │  - HTTP Server (FastAPI)                                       │   │
│  │  - /webhook (Google Chat messages)                             │   │
│  │  - /health (health check)                                      │   │
│  │  - /jobs/execute (cron jobs - Phase 3)                         │   │
│  │  - Message validation & PII filtering                          │   │
│  └────────────────────┬─────────────────────────────────────────┘   │
│                       │                                               │
│                       ▼                                               │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                      Agent Core (LangGraph)                    │   │
│  │  - Message routing & orchestration                             │   │
│  │  - LLM client (Vertex AI: Gemini 2.0 Flash/Pro)               │   │
│  │  - Conversation state management                               │   │
│  │  - Tool calling (skills as tools)                              │   │
│  │  - Streaming support                                           │   │
│  └────┬────────────────────┬────────────────────┬─────────────────┘  │
│       │                    │                    │                     │
│       ▼                    ▼                    ▼                     │
│  ┌─────────┐      ┌──────────────┐     ┌──────────────┐            │
│  │ Memory  │      │   Skills     │     │   Terminal   │            │
│  │ Manager │      │   Engine     │     │   Executor   │            │
│  └────┬────┘      └───────┬──────┘     └──────┬───────┘            │
│       │                   │                    │                     │
└───────┼───────────────────┼────────────────────┼─────────────────────┘
        │                   │                    │
        ▼                   ▼                    ▼
 ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
 │ GCS Bucket  │    │  ./skills/   │    │ Allowlist   │
 │ (Memory     │    │  - file-ops/ │    │ Commands:   │
 │  Sync)      │    │  - shell/    │    │ - cat       │
 │             │    │  - memory/   │    │ - ls        │
 │ *.md files  │    │  - ...       │    │ - python    │
 │ *.json      │    │  SKILL.md    │    │ - uv        │
 └─────────────┘    └──────────────┘    └─────────────┘
```

### Request Flow

```
1. User sends message in Google Chat
   ↓
2. Google Chat sends webhook POST to /webhook
   ↓
3. Gateway validates request & filters PII metadata
   ↓
4. Agent Core receives clean message (only user content)
   ↓
5. LLM (Gemini) decides which skill to invoke
   ↓
6. Skills Engine executes skill (via Terminal Executor if needed)
   ↓
7. Memory Manager persists facts (local + GCS sync)
   ↓
8. Agent Core formats response
   ↓
9. Gateway sends response to Google Chat
   ↓
10. User sees response in Google Chat
```

---

## Module Breakdown

### 1. Gateway Module (`src/gateway/`)
**Purpose:** HTTP interface for Google Chat webhooks

**Responsibilities:**
- Receive and validate Google Chat webhook requests
- **Filter PII metadata** (user email, space ID, etc.) - only pass message content to Agent Core
- Format responses for Google Chat Cards V2 API
- Health check endpoint for Cloud Run
- Future: Cron job execution endpoint (Phase 3)

**Key Files:**
- `server.py` - FastAPI application
- `google_chat.py` - Google Chat API integration
- `pii_filter.py` - Strip Google Chat metadata before sending to LLM

**Security:**
- Allowlist of authorized user emails/domains (env var: `ALLOWED_USERS=user1@example.com,user2@example.com`)
- PII filtering before passing to Agent Core
- **Note:** Webhook signature verification omitted for Phase 1 (MVP simplicity). Google Chat webhooks are HTTPS with URL obscurity. Add in production if needed.

---

### 2. Agent Core Module (`src/core/`)
**Purpose:** LangGraph-based agent orchestration

**Responsibilities:**
- Route messages to appropriate skills
- Maintain conversation context
- Call LLM (Vertex AI Gemini 2.0)
- Execute tool calls (skills)
- Stream responses for long-running tasks
- Track execution with trace IDs

**Key Files:**
- `agent.py` - LangGraph agent definition
- `llm_client.py` - Vertex AI client wrapper
- `memory.py` - File-based memory manager
- `terminal.py` - Terminal command executor

**LLM Strategy:**
- **Default:** Gemini 2.0 Flash (fast, cheap)
- **Complex reasoning:** Gemini 2.0 Pro (manual override via skill parameter, not auto-fallback)
- **Streaming:** For responses > 200 tokens (better UX for long outputs, ~1-2 paragraphs threshold)

**Model Selection:**
- Flash for all requests by default
- Pro only when skill explicitly requests it (e.g., `model="gemini-2.0-pro"` in skill payload)
- No automatic fallback from Flash to Pro (keep it simple for Phase 1)

---

### 3. Skills Module (`src/skills/`)
**Purpose:** Skill discovery, loading, and execution

**Responsibilities:**
- Auto-discover skills from `./skills/` directory
- Parse SKILL.md for metadata and examples
- Register skills as LangGraph tools
- Execute skills via Terminal Executor
- Handle skill errors gracefully

**Key Files:**
- `loader.py` - Skill discovery and parsing
- `executor.py` - Skill execution engine

**Skill Structure:**
```
./skills/
├── file-ops/
│   ├── SKILL.md         # Documentation + metadata
│   └── file_ops.py      # Implementation
├── shell/
│   ├── SKILL.md
│   └── shell.py
└── memory/
    ├── SKILL.md
    └── memory.py
```

**SKILL.md Format (YAML frontmatter + Markdown):**
```markdown
---
name: file-ops
description: "File operations (read, write, list)"
metadata:
  emonk:
    requires:
      bins: ["cat", "ls"]          # Required terminal commands
      files: ["./data/memory/"]     # Required paths
---

# File Operations Skill

## Read File
```bash
python skills/file-ops/file_ops.py read ./data/memory/test.txt
```
(more examples...)
```

---

### 4. Memory Module (`src/core/memory.py`)
**Purpose:** Persistent file-based memory with GCS sync

**Responsibilities:**
- Read/write memory files locally (`./data/memory/`)
- Auto-sync to GCS bucket on writes (async, non-blocking)
- Load from GCS on startup (if local cache missing)
- Handle sync failures gracefully (log error, continue with local)

**Memory Structure:**
```
./data/memory/
├── SYSTEM_PROMPT.md              # Agent personality & instructions
├── CONVERSATION_HISTORY/         # Rolling conversation logs
│   └── 2026-02/
│       └── 2026-02-11.md        # Daily conversation files
└── KNOWLEDGE_BASE/               # User-specific facts
    └── facts.json
```

**Retention Policy:**
- Conversation history: Keep last 90 days (configurable via `CONVERSATION_RETENTION_DAYS`)
- Knowledge facts: No expiration (persistent until explicitly deleted)
- Cron jobs: No expiration (persistent until explicitly deleted)
- Auto-cleanup: Daily background task deletes conversation files older than retention period

**GCS Sync Strategy:**
- **On write:** Async upload to `gs://emonk-memory/{user_id}/...`
- **On startup:** Download from GCS to local cache (`./data/memory/`)
- **Local-first:** Always serve from local cache, sync in background
- **Conflict resolution:** Last-write-wins (single Cloud Run instance for MVP: `--min-instances=1 --max-instances=1`)
- **Sync failures:** Log error, continue with local (GCS is backup, not primary source)
- **Future scaling:** When scaling >1 instance, use GCS object versioning or distributed lock to handle concurrent writes

**Why file-based instead of database?**
- Simple (no DB to manage)
- Human-readable (can inspect/edit memory files)
- Version-controllable (can commit to git for backups)
- Sufficient for single-user scale
- Easy to migrate to DB later if needed

---

### 5. Terminal Executor (`src/core/terminal.py`)
**Purpose:** Secure command execution with allowlist

**Responsibilities:**
- Execute allowed commands only (`cat`, `ls`, `python`, `uv`)
- Restrict access to allowed paths (`./data/memory/`, `./skills/`, `./content/`)
- Timeout protection (30s default, configurable)
- Capture stdout/stderr with size limits
- Handle process errors gracefully

**Security Model:**
```python
ALLOWED_COMMANDS = ["cat", "ls", "python", "uv"]
ALLOWED_PATHS = ["./data/memory/", "./skills/", "./content/"]

def execute(command: str, args: List[str]) -> ExecutionResult:
    # 1. Check if command is in ALLOWED_COMMANDS
    # 2. Check if all path args are in ALLOWED_PATHS
    # 3. Set timeout (30s)
    # 4. Execute with subprocess
    # 5. Capture output (max 1MB)
    # 6. Return result or error
```

**Why allowlist instead of sandbox?**
- Simpler (no Docker-in-Docker complexity)
- Sufficient for controlled environment (only skills we write)
- Clear security boundary (explicit allow, implicit deny)
- Easy to extend (add commands as needed)

**Security Note:**
- Terminal executor trusts all Python scripts in `./skills/` directory
- **No validation of skill script content** - arbitrary code execution is possible
- **Developer responsibility:** Only add trusted skills to production deployments
- **Open source users:** Review all skills before deployment (see README security warning)

---

### 6. Cron Module (`src/cron/scheduler.py`)
**Purpose:** Job scheduling with persistent storage (GCS-backed for Cloud Run)

**Implementation:**
- Threading-based timer system (Python `threading.Timer`)
- Jobs persisted to GCS (`gs://emonk-memory/cron-jobs.json`)
- On startup: Load jobs from GCS and reschedule all active timers
- Supports three schedule types: cron expressions, intervals, one-time

**Job Registry Format:**
```json
{
  "jobs": [
    {
      "id": "daily-report-001",
      "name": "Daily Report",
      "enabled": true,
      "schedule": {
        "kind": "cron",
        "expr": "0 9 * * *",
        "tz": "America/New_York"
      },
      "payload": {
        "kind": "agentTurn",
        "message": "Generate daily social media report"
      },
      "createdAt": 1707667200,
      "updatedAt": 1707667200,
      "lastRunAt": null,
      "lastRunStatus": null
    }
  ]
}
```

**Schedule Types:**
1. **Cron expression:** `{"kind": "cron", "expr": "0 9 * * *", "tz": "America/New_York"}`
2. **Interval:** `{"kind": "every", "everyMs": 3600000}` (every hour)
3. **One-time:** `{"kind": "at", "at": "2026-02-15T09:00:00Z"}`

**Operations:**
- `add_job(id, schedule, payload, name, enabled)` - Create new job
- `remove_job(id)` - Remove job
- `list_jobs()` - List all jobs
- `schedule_job(job)` - Schedule timer for job
- `execute_job(job)` - Execute job payload

**Cloud Run Considerations:**
- Jobs loaded from GCS on instance startup
- Each instance reschedules all enabled jobs
- For MVP (single user): Single Cloud Run instance (min=1, max=1) avoids duplicate execution
- Future scaling: Use distributed lock (GCS object versioning) or Cloud Scheduler

---

## Core Data Model

### Entity: ConversationMessage
```
ConversationMessage
├── id: str (UUID) - Unique message identifier
├── user_id: str - User identifier (hashed Google Chat user ID)
├── content: str - Message content (user input or agent response)
├── role: str - "user" | "assistant" | "system"
├── timestamp: datetime - Message creation time
├── trace_id: str - Request trace ID (for debugging)
└── metadata: dict - Optional metadata (model used, tokens, latency)

Relationships:
- Belongs to conversation thread (via date-based file)

Storage:
- File: ./data/memory/CONVERSATION_HISTORY/{YYYY-MM}/{YYYY-MM-DD}.md
- Format: Markdown with YAML frontmatter per message

Context Window:
- Last 10 messages sent to LLM (5 user + 5 assistant pairs)
- Configurable via CONVERSATION_CONTEXT_LIMIT env var
- Older messages archived but not sent to LLM (reduces token cost)
```

**Example File (2026-02-11.md):**
```markdown
---
date: 2026-02-11
user_id: user_abc123
---

## 09:45:32 - User
Remember that I prefer Python for all code examples

## 09:45:34 - Assistant (trace: trace_xyz)
✅ I'll remember that. Stored: code_language_preference = Python

## 09:46:10 - User
What's my preferred language?

## 09:46:11 - Assistant (trace: trace_abc)
According to my memory, you prefer Python for all code examples.
```

---

### Entity: KnowledgeFact
```
KnowledgeFact
├── key: str - Fact key (e.g., "code_language_preference")
├── value: str - Fact value (e.g., "Python")
├── created_at: datetime - When fact was stored
└── updated_at: datetime - Last modification time

Relationships:
- Belongs to user (via user_id in file path)

Storage:
- File: ./data/memory/KNOWLEDGE_BASE/facts.json
- Format: JSON with timestamps

Indexes:
- In-memory dict for O(1) lookup (file is small)
```

**Example File (facts.json):**
```json
{
  "facts": {
    "code_language_preference": {
      "value": "Python",
      "created_at": "2026-02-11T09:45:34Z",
      "updated_at": "2026-02-11T09:45:34Z"
    },
    "timezone": {
      "value": "US/Eastern",
      "created_at": "2026-02-11T10:00:00Z",
      "updated_at": "2026-02-11T10:00:00Z"
    }
  }
}
```

---

### Entity: CronJob
```
CronJob
├── id: str - Unique job identifier
├── schedule: str - Cron expression (e.g., "0 9 * * *")
├── task: str - Skill name to execute
├── args: dict - Arguments for skill
├── created_at: datetime - Job creation time
├── last_run: datetime | null - Last execution time
├── next_run: datetime - Next scheduled run
└── status: str - "pending" | "running" | "completed" | "failed" | "cancelled"

Relationships:
- None (standalone jobs)

Storage:
- File: ./data/cron_jobs.json (Phase 1 - local only)
- File: gs://emonk-jobs/registry.json (Phase 3 - Cloud Scheduler)

Indexes:
- In-memory list for Phase 1 (simple iteration)
```

---

### Entity: Skill
```
Skill (Metadata Only - No Persistence)
├── name: str - Skill identifier (from SKILL.md)
├── description: str - Human-readable description
├── requires_bins: List[str] - Required terminal commands
├── requires_files: List[str] - Required file paths
├── examples: List[str] - Example invocations from SKILL.md
└── entry_point: str - Path to Python script

Relationships:
- None (loaded at startup from ./skills/)

Storage:
- Discovered from filesystem at startup
- Cached in-memory (no persistence needed)

Conflict Resolution:
- If two skills have same name, log warning and use first discovered (alphabetical by directory name)
- Recommendation: Use unique skill names (e.g., "file-ops", "memory-manager", "shell-exec")
```

---

## Data Flow Examples

### Example 1: User asks to remember a fact

```
1. User (Google Chat): "Remember that I prefer Python"
   ↓
2. Gateway receives webhook:
   POST /webhook
   {
     "message": {
       "sender": {"email": "user@example.com"},  // ← PII, strip this
       "text": "Remember that I prefer Python"
     }
   }
   ↓
3. Gateway filters PII, passes clean message to Agent Core:
   {
     "user_id": "hashed_user_abc123",  // ← hashed, not email
     "content": "Remember that I prefer Python"
   }
   ↓
4. Agent Core calls LLM (Gemini 2.0 Flash):
   LLM decides to invoke "memory-remember" skill
   ↓
5. Skills Engine executes:
   $ python skills/memory/memory.py remember code_language_preference Python
   ↓
6. Memory Manager writes to:
   ./data/memory/KNOWLEDGE_BASE/facts.json
   (adds: {"code_language_preference": {"value": "Python", ...}})
   ↓
7. Memory Manager syncs to GCS (async):
   gs://emonk-memory/user_abc123/KNOWLEDGE_BASE/facts.json
   ↓
8. Agent Core formats response:
   "✅ I'll remember that. Stored: code_language_preference = Python"
   ↓
9. Gateway sends to Google Chat (Cards V2 format)
   ↓
10. User sees response in Google Chat
```

---

### Example 2: User asks to list files

```
1. User: "List files in ./data/memory/"
   ↓
2. Gateway → Agent Core (PII filtered)
   ↓
3. Agent Core → LLM: "What skill should I use?"
   LLM decides: "file-ops-list" skill
   ↓
4. Skills Engine → Terminal Executor:
   execute("python", ["skills/file-ops/file_ops.py", "list", "./data/memory/"])
   ↓
5. Terminal Executor validates:
   - "python" in ALLOWED_COMMANDS? ✅
   - "./data/memory/" in ALLOWED_PATHS? ✅
   - Execute with 30s timeout
   ↓
6. Terminal Executor captures output:
   stdout: "SYSTEM_PROMPT.md\nCONVERSATION_HISTORY/\nKNOWLEDGE_BASE/"
   stderr: ""
   exit_code: 0
   ↓
7. Skills Engine returns result to Agent Core
   ↓
8. Agent Core formats response (with file details)
   ↓
9. Gateway sends to Google Chat
```

---

## Technology Stack

### Core Framework
- **Python 3.11+** (modern async support, type hints)
- **LangGraph** (agent orchestration)
- **LangChain** (LLM abstractions)
- **FastAPI** (HTTP server)
- **Uvicorn** (ASGI server)

### LLM
- **Vertex AI** (Gemini 2.0 Flash, Gemini 2.0 Pro)
- **langchain-google-vertexai** (LangChain integration)

### Google Cloud
- **Cloud Run** (serverless deployment)
- **Cloud Storage** (memory persistence)
- **Cloud Scheduler** (cron jobs - Phase 3)

### Google Chat
- **google-auth** (authentication)
- **google-api-python-client** (Google Chat API)

### Package Management
- **uv** (fast Python package manager)
- **.venv** (virtual environment)

### Testing
- **pytest** (test framework)
- **pytest-asyncio** (async test support)
- **pytest-cov** (coverage)
- **httpx** (HTTP client for integration tests)

---

## Deployment Model

### Local Development
```bash
# Setup
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Run
python -m src.gateway.server

# Test
pytest tests/
```

### Cloud Run Deployment
```bash
# Build Docker image
docker build -t emonk-agent .

# Push to Artifact Registry
docker tag emonk-agent gcr.io/PROJECT_ID/emonk-agent
docker push gcr.io/PROJECT_ID/emonk-agent

# Deploy to Cloud Run
gcloud run deploy emonk-agent \
  --image gcr.io/PROJECT_ID/emonk-agent \
  --platform managed \
  --region us-central1 \
  --min-instances=1 \
  --max-instances=1 \
  --set-env-vars GOOGLE_CHAT_WEBHOOK_SECRET=xxx \
  --set-env-vars GCS_MEMORY_BUCKET=emonk-memory \
  --set-env-vars ALLOWED_USERS=user@example.com \
  --set-env-vars GCS_ENABLED=true \
  --allow-unauthenticated  # Google Chat webhook needs public endpoint (access controlled by ALLOWED_USERS)
```

### Environment Variables
```bash
# GCP Configuration
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
VERTEX_AI_PROJECT_ID=your-gcp-project
VERTEX_AI_LOCATION=us-central1

# Google Chat Configuration
GOOGLE_CHAT_WEBHOOK_SECRET=your-webhook-secret  # Not used for signature verification (MVP)
ALLOWED_USERS=user1@example.com,user2@example.com  # Comma-separated list of authorized emails

# Agent Configuration
AGENT_NAME=emonk-general-assistant
SKILLS_DIR=./skills
MEMORY_DIR=./data/memory

# GCS Configuration (for Cloud Run)
GCS_MEMORY_BUCKET=emonk-memory
GCS_ENABLED=false  # Set to true for Cloud Run, false for local dev

# Development
DEBUG=true
LOG_LEVEL=INFO
```

---

## Security Considerations

### Google Chat PII Filtering
**Problem:** Google Chat webhooks include sensitive metadata (user email, space ID, etc.) that should NOT be sent to LLM.

**Solution:**
```python
# src/gateway/pii_filter.py

def filter_google_chat_pii(webhook_payload: dict) -> dict:
    """
    Extract only safe fields from Google Chat webhook.
    Returns: {user_id: hashed_id, content: message_text}
    """
    sender_email = webhook_payload["message"]["sender"]["email"]
    message_text = webhook_payload["message"]["text"]
    
    # Hash email to create stable user_id (no PII)
    user_id = hashlib.sha256(sender_email.encode()).hexdigest()[:16]
    
    return {
        "user_id": user_id,  # ← Hashed, not email
        "content": message_text
    }
```

**What gets filtered:**
- ❌ User email
- ❌ Space ID
- ❌ Thread ID
- ❌ Google Chat metadata
- ✅ Message content (user explicitly provided)

---

### Terminal Execution Security

**Allowlist-based approach:**
```python
ALLOWED_COMMANDS = ["cat", "ls", "python", "uv"]
ALLOWED_PATHS = ["./data/memory/", "./skills/", "./content/"]

# Example: Safe command
execute("cat", ["./data/memory/facts.json"])  # ✅ Allowed

# Example: Blocked command
execute("rm", ["-rf", "/"])  # ❌ Blocked - "rm" not in allowlist

# Example: Blocked path
execute("cat", ["/etc/passwd"])  # ❌ Blocked - path not in allowlist
```

**Additional protections:**
- 30-second timeout (prevent infinite loops)
- 1MB output limit (prevent memory exhaustion)
- Process isolation (subprocess with restricted permissions)

---

## Observability

### Logging Strategy
- **Structured logging** (JSON format with trace IDs)
- **Log levels:** INFO for flow, DEBUG for details, ERROR for failures
- **Trace IDs:** Track request through entire stack (gateway → agent → skills)

**Example log output:**
```json
{
  "timestamp": "2026-02-11T09:45:34Z",
  "level": "INFO",
  "trace_id": "trace_xyz",
  "component": "agent_core",
  "message": "Executing skill: memory-remember",
  "metadata": {
    "skill": "memory-remember",
    "args": ["code_language_preference", "Python"]
  }
}
```

### Metrics (Phase 1 - Basic)
- Request count (total, success, error)
- Response latency (p50, p95, p99)
- LLM token usage (per request, per day)
- Skill execution time

**Implementation:** 
- Log-based metrics using Cloud Logging
- Structured JSON logs enable queries (e.g., "count where level=ERROR")
- Manual analysis via Cloud Console or gcloud CLI
- Future: Add Prometheus/Grafana if monitoring requirements increase

---

## Performance Considerations

### Response Time Targets
- **Simple queries** (memory recall): < 2 seconds
- **Complex reasoning** (multi-step tasks): < 10 seconds
- **Skill execution** (file ops, shell): < 5 seconds

### Optimization Strategies
1. **LLM model selection:** Gemini 2.0 Flash by default (fast, cheap)
2. **Streaming:** Stream responses for long outputs (better UX)
3. **Memory caching:** Load facts once per request (in-memory cache)
4. **Async I/O:** GCS sync is async, non-blocking
5. **Lazy loading:** Skills loaded at startup, not per request
   - Skills cached in memory for fast access
   - Changes to `./skills/` require restart to take effect
   - Future: Add hot-reload endpoint (`POST /admin/reload-skills`) if needed

### Scalability Path (Future)
When scale increases beyond single user:
1. **Caching:** Add Redis for conversation context (reduce GCS reads)
2. **Database:** Migrate from file-based to PostgreSQL (structured queries)
3. **Async workers:** Move long-running tasks to Cloud Tasks (decouple from HTTP)
4. **Multi-region:** Deploy to multiple regions (geo-distribution)
5. **Microservices:** Split modules if independent scaling is needed

**Current design supports all of these without major refactor.**

---

## Open Source Considerations

### Code Quality Standards
- **Type hints:** All functions must have type annotations
- **Docstrings:** All public functions/classes must have docstrings (Google style)
- **Tests:** Minimum 80% code coverage
- **Linting:** Use `ruff` for linting and formatting
- **Pre-commit hooks:** Auto-format and lint on commit

### Documentation
- **README.md:** Quick start, installation, usage, **SECURITY WARNING**
- **CONTRIBUTING.md:** How to contribute (skills, code, docs)
- **LICENSE:** MIT (permissive open source)
- **docs/:** Architecture, API reference, examples

### Security Warning (README.md)
**CRITICAL: Arbitrary Code Execution Risk**

Emonk's skill system executes Python scripts from the `./skills/` directory **without validation**. This means:

⚠️ **Skills can execute arbitrary code with full permissions of the agent process**
⚠️ **Only add skills from trusted sources**
⚠️ **Review all skill code before deployment**
⚠️ **Skills have access to: GCS buckets, Vertex AI, Google Chat API, local filesystem**

**This is by design** to keep the framework simple and flexible. Security is the **developer's responsibility**, not the framework's.

**For production deployments:**
1. Review every skill script before adding to `./skills/`
2. Use separate GCP projects for dev/prod
3. Limit service account permissions to minimum required
4. Monitor skill execution logs for unexpected behavior

### Example Skills
Include 3 well-documented example skills to demonstrate patterns:
1. **file-ops:** File operations (read, write, list)
2. **shell:** Safe shell command execution
3. **memory:** Memory management (remember, recall, search)

---

## Next Steps

Phase 1A is complete! The design covers:
- ✅ Architecture decision (Modular Monolith on Cloud Run)
- ✅ Module breakdown (Gateway, Agent Core, Skills, Memory, Terminal, Cron)
- ✅ Core data model (ConversationMessage, KnowledgeFact, CronJob, Skill)
- ✅ Data flow examples
- ✅ Security considerations (PII filtering, terminal security)
- ✅ Observability and performance

**Ready for Phase 1B: Detailed Contracts**
- Define API contracts (Google Chat webhook, internal APIs)
- Specify integration points (Vertex AI, GCS, Google Chat)
- Create testing strategy (unit, integration, e2e)
