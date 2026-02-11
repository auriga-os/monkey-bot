# Phase 1: Core Agent Foundation + Google Chat Integration

**Goal:** Working general-purpose AI agent with chat interface and basic capabilities

**Value Delivered:** Chat-based assistant that can execute commands, manage memory, and interact conversationally through Google Chat. This is your foundation for all future agents.

**Status:** Ready for monkeymode execution

---

## Strategic Context

This phase builds the foundation for the entire Emonk framework. We're creating a general-purpose AI agent that can:
- Communicate via Google Chat
- Execute commands safely
- Maintain persistent memory
- Load and execute modular skills

**Critical Architecture Decision:** Since we're deploying to Cloud Run (serverless), the architecture needs to support stateless invocation while maintaining persistent memory. This means:
- **Memory**: GCP Storage (Cloud Storage) for file-based persistence
- **Cron Jobs**: Cloud Scheduler triggers Cloud Run endpoints (will be refactored in Phase 3)
- **State Management**: Job definitions stored in GCS, execution state tracked externally

---

## Components to Build

### 1. Core Infrastructure

#### LLM Integration (Vertex AI)
- Gemini 2.0 Flash for fast operations
- Gemini 2.0 Pro for complex reasoning
- Streaming support for responsive chat
- Cost tracking and model selection logic

**Key Files:**
- `src/core/llm_client.py` - Vertex AI client wrapper

**Implementation Requirements:**
- Support multiple models with fallback logic
- Track token usage and costs per request
- Implement streaming for long responses
- Handle rate limits and retries

#### Terminal Executor
- Allowlist-based command execution (`cat`, `ls`, `python`, `uv`)
- Security sandboxing (restricted paths: `./data/memory/`, `./skills/`)
- Process timeout management (30s default)
- Structured output capture (stdout/stderr)

**Key Files:**
- `src/core/terminal.py` - Terminal executor

**Security Requirements:**
- Only allowed commands can execute
- Only allowed paths can be accessed
- Process timeouts prevent hanging
- Output size limits prevent memory exhaustion

**Allowed Commands:**
- `cat <file>` - Read files
- `ls <dir>` - List directories
- `python <script>` - Run Python scripts (via uv)
- `uv run <script>` - Run scripts with uv

**Allowed Paths:**
- `./data/memory/` - Memory storage
- `./skills/` - Skill scripts
- `./content/` - Generated content

#### Memory System (File-Based)
- Local storage: `./data/memory/` directory structure
- GCP Storage sync (for Cloud Run persistence)
- Core memory files:
  - `SYSTEM_PROMPT.md` - Agent personality and instructions
  - `CONVERSATION_HISTORY/` - Rolling conversation logs
  - `KNOWLEDGE_BASE/` - User-specific facts and preferences
- File operations: read, write, append, list

**Key Files:**
- `src/core/memory.py` - File-based memory manager

**Memory Structure:**
```
./data/memory/
├── SYSTEM_PROMPT.md          # Agent personality and instructions
├── CONVERSATION_HISTORY/     # Rolling conversation logs
│   ├── 2026-02/
│   │   └── 2026-02-11.md
├── KNOWLEDGE_BASE/           # User-specific facts and preferences
│   └── facts.json
```

**GCS Sync Requirements:**
- Automatic sync to GCS on writes (async, non-blocking)
- Sync from GCS on startup (if local cache missing)
- Skip sync in local development mode
- Handle sync failures gracefully

#### Agent Core (LangGraph)
- Basic message routing and orchestration
- Tool calling with structured output
- Conversation state management
- Error handling and graceful degradation

**Key Files:**
- `src/core/agent.py` - LangGraph agent orchestration

**Core Responsibilities:**
- Route incoming messages to appropriate skills
- Maintain conversation context
- Handle multi-turn conversations
- Format responses for Google Chat
- Track execution with trace IDs

---

### 2. Google Chat Integration

#### Chat Bot Setup
- Google Chat API integration (instead of Telegram)
- Webhook handler for incoming messages
- Message formatting (text, code blocks, buttons)
- Rich cards for structured responses
- Access control (allowed users/spaces)

**Key Files:**
- `src/gateway/google_chat.py` - Google Chat integration
- `src/gateway/server.py` - HTTP server for webhooks

**Google Chat Requirements:**
- Register as Google Chat app
- Set up webhook URL for message events
- Handle message verification
- Format responses using Cards V2 API
- Support rich formatting (bold, code, lists)

**Access Control:**
- Allowlist of user emails or domains
- Allowlist of spaces/rooms
- Reject unauthorized requests

#### Gateway Service (Simplified for Cloud Run)
- HTTP endpoint for Google Chat webhooks
- Message queue for async processing
- Response formatting and sending
- Health check endpoints

**Endpoints:**
- `POST /webhook` - Google Chat message webhook
- `GET /health` - Health check
- `POST /jobs/execute` - Cron job execution (Phase 3)

---

### 3. Basic Skills (CLI-Based)

#### File Operations Skill
**Location:** `skills/file-ops/`

**Files:**
- `SKILL.md` - Documentation with examples
- `file_ops.py` - Python implementation

**Functions:**
- `read_file(path)` - Read file contents
- `write_file(path, content)` - Write file
- `list_dir(path)` - List directory contents

**SKILL.md Template:**
```markdown
---
name: file-ops
description: "File operations (read, write, list)"
metadata:
  emonk:
    requires:
      bins: ["cat", "ls"]
---

# File Operations Skill

## Read File

```bash
python skills/file-ops/file_ops.py read ./data/memory/SYSTEM_PROMPT.md
```

## Write File

```bash
python skills/file-ops/file_ops.py write ./data/memory/test.txt "Hello World"
```

## List Directory

```bash
python skills/file-ops/file_ops.py list ./data/memory/
```
```

#### Shell Executor Skill
**Location:** `skills/shell/`

**Files:**
- `SKILL.md` - Documentation
- `shell.py` - Python implementation

**Functions:**
- `run_command(cmd, args)` - Execute safe command

**Allowed Commands:**
- `cat`, `ls`, `python`, `uv`

#### Memory Management Skill
**Location:** `skills/memory/`

**Files:**
- `SKILL.md` - Documentation
- `memory.py` - Python implementation

**Functions:**
- `remember(key, value)` - Store fact
- `recall(key)` - Retrieve fact
- `search_memory(query)` - Search memory

**Storage Format (JSON):**
```json
{
  "facts": {
    "code_language_preference": "Python",
    "timezone": "US/Eastern",
    "preferred_framework": "LangGraph"
  }
}
```

---

### 4. Cron Job System (Basic, Not Cloud Run Ready Yet)

**Note:** This is a simplified local-only implementation for Phase 1. It will be refactored in Phase 3 for Cloud Scheduler integration.

**Key Files:**
- `src/cron/scheduler.py` - Basic cron (local only)

**Job Registry Format (JSON):**
```json
{
  "jobs": [
    {
      "id": "test-job-001",
      "schedule": "0 9 * * *",
      "task": "test_skill",
      "args": {"message": "Hello"},
      "created_at": "2026-02-11T10:00:00Z",
      "last_run": null,
      "next_run": "2026-02-12T09:00:00Z",
      "status": "pending"
    }
  ]
}
```

**Operations:**
- `list_jobs()` - List all jobs
- `create_job(schedule, task, args)` - Create new job
- `cancel_job(job_id)` - Cancel job

---

## Project Structure

```
emonk/
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── agent.py           # LangGraph agent orchestration
│   │   ├── llm_client.py      # Vertex AI client wrapper
│   │   ├── memory.py          # File-based memory manager
│   │   └── terminal.py        # Terminal executor
│   ├── gateway/
│   │   ├── __init__.py
│   │   ├── google_chat.py     # Google Chat integration
│   │   └── server.py          # HTTP server for webhooks
│   ├── skills/
│   │   ├── __init__.py
│   │   ├── loader.py          # Skill discovery and loading
│   │   └── executor.py        # Skill execution engine
│   └── cron/
│       ├── __init__.py
│       └── scheduler.py       # Basic cron (local only)
├── skills/
│   ├── file-ops/
│   │   ├── SKILL.md
│   │   └── file_ops.py
│   ├── shell/
│   │   ├── SKILL.md
│   │   └── shell.py
│   └── memory/
│       ├── SKILL.md
│       └── memory.py
├── data/
│   └── memory/
│       ├── SYSTEM_PROMPT.md
│       ├── KNOWLEDGE_BASE/
│       │   └── facts.json
│       └── CONVERSATION_HISTORY/
├── tests/
│   ├── test_agent.py
│   ├── test_llm_client.py
│   ├── test_memory.py
│   ├── test_terminal.py
│   └── test_skills.py
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── Dockerfile
```

---

## Demo Scenario

```
User (Google Chat): "Remember that I prefer Python for all code examples"
Agent: "✅ I'll remember that. Stored: code_language_preference = Python"

User: "What's my preferred language?"
Agent: "According to my memory, you prefer Python for all code examples."

User: "List files in ./data/memory/"
Agent: "Found 3 files in ./data/memory/:
- SYSTEM_PROMPT.md (2.3 KB)
- CONVERSATION_HISTORY/2026-02-11.md (15.1 KB)
- KNOWLEDGE_BASE/facts.json (892 bytes)"

User: "Create a file called test.txt with content 'Hello World'"
Agent: "✅ Created test.txt with content 'Hello World'"
```

---

## Success Criteria

- [ ] Agent responds to Google Chat messages within 2 seconds
- [ ] Memory persists across restarts (GCS sync working)
- [ ] Can execute shell commands safely (only allowed commands)
- [ ] Conversation history maintained for context
- [ ] Basic skills (file ops, shell, memory) working end-to-end
- [ ] Unit tests pass for core components
- [ ] Can run locally via `python -m src.gateway.server`
- [ ] README with setup and usage instructions

---

## Testing Strategy

### Unit Tests
- `test_agent.py` - Agent core logic
- `test_llm_client.py` - LLM integration
- `test_memory.py` - Memory operations
- `test_terminal.py` - Terminal executor
- `test_skills.py` - Skill loading and execution

### Integration Tests
- End-to-end conversation flow
- Memory persistence across restarts
- Skill execution via agent
- Google Chat webhook handling

### Manual Testing
1. Send message via Google Chat
2. Agent responds correctly
3. Memory persists (restart agent, recall fact)
4. File operations work
5. Shell commands execute safely

---

## Environment Setup

### Required Environment Variables

```bash
# GCP Configuration
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
VERTEX_AI_PROJECT_ID=your-gcp-project
VERTEX_AI_LOCATION=us-central1

# Google Chat Configuration
GOOGLE_CHAT_WEBHOOK_SECRET=your-webhook-secret

# Agent Configuration
AGENT_NAME=emonk-general-assistant
SKILLS_DIR=./skills
MEMORY_DIR=./data/memory

# GCS Configuration (for Cloud Run)
GCS_MEMORY_BUCKET=emonk-memory
GCS_ENABLED=false  # Set to true for Cloud Run

# Development
DEBUG=true
LOG_LEVEL=INFO
```

### `.env.example` Template

Create `.env.example` with the above variables (with placeholder values).

---

## Dependencies (requirements.txt)

```txt
# LLM & Agent Framework
google-cloud-aiplatform==1.40.0
langchain==0.1.0
langgraph==0.0.20
langchain-google-vertexai==0.1.0

# Google Chat Integration
google-auth==2.27.0
google-api-python-client==2.116.0

# Web Server
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.0

# Storage
google-cloud-storage==2.14.0

# Utilities
python-dotenv==1.0.0
pyyaml==6.0.1
structlog==24.1.0
aiofiles==23.2.1

# Testing
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==4.1.0
httpx==0.26.0
```

---

## README Template

```markdown
# Emonk - General Assistant Agent

A general-purpose AI agent built with LangGraph and Vertex AI.

## Features

- 💬 Google Chat integration
- 🧠 Persistent memory (file-based + GCS sync)
- 🛠️ Modular skill system
- 🔒 Secure command execution
- 📊 Structured logging with trace IDs

## Quick Start

### Prerequisites

- Python 3.11+
- GCP account with Vertex AI enabled
- Google Chat app configured

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/emonk.git
cd emonk

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
vim .env
```

### Configuration

1. Set up GCP service account with Vertex AI permissions
2. Create Google Chat app and get webhook secret
3. Update `.env` with your credentials

### Run Locally

```bash
# Start agent
python -m src.gateway.server
```

### Test

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=src tests/
```

## Usage

### Chat with Agent

Send messages to the Google Chat app.

Example:
```
You: Remember that I prefer Python
Agent: ✅ I'll remember that. Stored: code_language_preference = Python

You: What's my preferred language?
Agent: According to my memory, you prefer Python for all code examples.
```

### Add Custom Skills

1. Create directory in `skills/`
2. Add `SKILL.md` with documentation
3. Add Python script with implementation
4. Agent will auto-discover on startup

## Architecture

See [docs/architecture.md](docs/architecture.md) for details.

## License

MIT
```

---

## References

- [Base Agent Abilities](../preplanning/base-agent-abilities.md) - sections 1-8
- [Gateway Daemon Reference](../ref/01_gateway_daemon.md) - simplified for HTTP
- [Skills System Reference](../ref/05_skills_system.md) - CLI-based pattern
- [LLM Integration Reference](../ref/06_llm_integration.md) - Vertex AI patterns

---

## Next Phase

After Phase 1 is complete and working:
- **Phase 2:** Add marketing campaign skills with MCP integration
- Focus: Research, content generation, posting automation
