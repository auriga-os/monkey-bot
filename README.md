# emonk 🐵

> An opinionated agent framework built on [LangChain Deep Agents](https://docs.langchain.com/oss/python/deepagents/overview) — with pluggable cloud storage, sandbox execution, and a skills engine.

Built by [ez-ai](https://github.com/ez-ai).

---

## What is emonk?

emonk (monkey-bot) is a thin, opinionated layer on top of LangChain's `create_agent`. It adds:

- **Cloud storage backends** — Persist skills, memory, and artifacts to GCS (or bring your own backend)
- **Sandbox execution** — Run shell commands in isolated Modal containers (optional)
- **Skills engine** — Agent-discoverable SKILL.md files with YAML frontmatter
- **Session memory** — Automatic session summaries with cross-conversation recall
- **Job scheduling** — Cloud Scheduler integration for recurring tasks
- **Google Chat gateway** — Webhook handler with PII filtering

Everything is optional and pluggable. The framework works with zero cloud dependencies out of the box.

---

## Features

- 🤖 **LangChain Agent Core** — Built on `create_agent` with middleware support
- 🎯 **Simple Skill System** — Add custom skills via SKILL.md + Python entry points
- 💾 **Persistent Memory** — GCS-backed LangGraph Store with keyword search
- ⏰ **Cloud Scheduler-Ready Jobs** — `/cron/tick` endpoint with metrics and Firestore locking
- 🔧 **Multi-Provider Model Support** — Google Vertex AI, OpenAI, Anthropic (easy switching)
- ⚙️ **Centralized Config Management** — Load secrets from GCP Secret Manager or `.env`
- 📋 **Job Handler Pattern** — Standardized registration for scheduled task handlers
- 💬 **Modern Google Chat Format** — Workspace Add-on support (+ legacy fallback)
- 🔒 **Secure Execution** — Allowlist-based command/path validation (optional)
- 📦 **Pluggable Backends** — Bring your own storage, sandbox, or LLM
- 📊 **Structured Logging** — JSON logs with trace IDs

---

## Quick Start

### Using Config Module (Recommended)

```python
from emonk import build_agent
from emonk.core.config import get_model, load_secrets

# Load secrets (from .env in dev, Secret Manager in prod)
load_secrets()

# Get configured model (provider set via MODEL_PROVIDER env var)
model = get_model()

# Build agent
agent = build_agent(model=model, tools=[])

# Invoke
result = agent.invoke({
    "messages": [{"role": "user", "content": "Hello!"}]
})
print(result["messages"][-1].content)
```

### Manual Configuration (Advanced)

```python
from emonk import build_agent
from langchain_google_vertexai import ChatVertexAI

# Explicit model configuration
model = ChatVertexAI(model="gemini-2.5-flash")
agent = build_agent(model=model, tools=[])

result = agent.invoke({
    "messages": [{"role": "user", "content": "Hello!"}]
})
print(result["messages"][-1].content)
```

---

## Installation

```bash
# Core framework
pip install emonk

# With Google Cloud Storage
pip install emonk[gcs]

# With Modal sandbox
pip install emonk[modal]

# Everything
pip install emonk[all]
```

---

## Architecture

```
┌─────────────────────────────────────────────---┐
│            Gateway (FastAPI)                   │
│   POST /webhook   POST /cron/tick   GET /health
└──────────────┬──────────────────────┬──────────┘
               │                      │
               │                      ▼
               │            ┌──────────────────────┐
               │            │ Cloud Scheduler (GCP)│
               │            │ Trigger cadence      │
               │            └──────────────────────┘
               ▼
┌─────────────────────────────────────────────┐
│         Agent Core (LangChain)              │
│   - create_agent with middleware            │
│   - Conversation context (last 20 msgs)     │
│   - LLM integration (Gemini 2.5 Flash)      │
└──┬──────────────┬──────────────┬────────────┘
   │              │              │
   ▼              ▼              ▼
┌────────┐  ┌──────────┐  ┌──────────┐
│Skills  │  │Terminal  │  │Memory    │
│Engine  │  │Executor  │  │Manager   │
└────────┘  └──────────┘  └──────────┘
                   │
                   ▼
           ┌───────────────────┐
           │ Cron Scheduler    │
           │ JSON / Firestore  │
           └───────────────────┘
```

---

## Configuration

monkey-bot uses environment variables for configuration. See [`.env.example`](.env.example) for all available options.

### Key Configuration Variables

```bash
# Model provider (google_vertexai | openai | anthropic)
MODEL_PROVIDER=google_vertexai

# Model name (provider-specific)
MODEL_NAME=gemini-2.5-flash

# Generation temperature (0.0-1.0)
MODEL_TEMPERATURE=0.7

# GCP Project ID (for Vertex AI)
VERTEX_AI_PROJECT_ID=your-gcp-project-id

# Scheduler storage (json | firestore)
SCHEDULER_STORAGE=json

# Google Chat response format (workspace_addon | legacy)
GOOGLE_CHAT_FORMAT=workspace_addon
```

**For full configuration reference:** See [`.env.example`](.env.example)

**For deployment instructions:** See [`docs/deployment.md`](docs/deployment.md)

---

## Usage Examples

### Basic Agent

```python
from emonk import build_agent
from emonk.core.config import get_model

# Create agent using config module
model = get_model()
agent = build_agent(model=model, tools=[])

# Invoke the agent
result = agent.invoke({
    "messages": [{"role": "user", "content": "What's 2+2?"}]
})
print(result["messages"][-1].content)
```

### With Skills

```python
from emonk import build_agent
from emonk.skills import SkillLoader, SkillExecutor
from langchain_google_vertexai import ChatVertexAI

# Load skills from ./skills/ directory
loader = SkillLoader(skills_dir="./skills")
skills_metadata = loader.load_skills()

# Create executor and convert to LangChain tools
executor = SkillExecutor(skills_metadata)
tools = executor.to_langchain_tools()

# Build agent with skills
model = ChatVertexAI(model="gemini-2.5-flash")
agent = build_agent(model=model, tools=tools)

result = agent.invoke({
    "messages": [{"role": "user", "content": "List files in ./data"}]
})
```

### With Cloud Storage

```python
from emonk import build_agent, GCSStore, create_search_memory_tool
from langchain_google_vertexai import ChatVertexAI

# Create GCS-backed memory store
store = GCSStore(
    bucket_name="my-agent-memory",
    project_id="my-gcp-project"
)

# Create search_memory tool
search_tool = create_search_memory_tool(store)

# Build agent with memory
model = ChatVertexAI(model="gemini-2.5-flash")
agent = build_agent(
    model=model,
    tools=[search_tool],
    store=store  # Enables SessionSummaryMiddleware
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What did we discuss last time?"}]},
    config={"configurable": {"user_id": "user123", "thread_id": "thread456"}}
)
```

### With Sandbox Execution

```python
from emonk import build_agent
from emonk.sandbox import ModalSandboxBackend
from langchain_google_vertexai import ChatVertexAI

# Create Modal sandbox backend
sandbox = ModalSandboxBackend()

# Create sandbox execution tool
from langchain_core.tools import tool

@tool
async def run_code(code: str) -> str:
    """Execute Python code in isolated sandbox."""
    result = await sandbox.execute(code)
    return result.output

# Build agent with sandbox
model = ChatVertexAI(model="gemini-2.5-flash")
agent = build_agent(model=model, tools=[run_code])

result = agent.invoke({
    "messages": [{"role": "user", "content": "Run: print('Hello from sandbox')"}]
})
```

### With Memory

```python
from emonk import GCSStore

# Initialize store
store = GCSStore(bucket_name="my-memory-bucket")

# Store a session summary
store.put(
    namespace=("user123", "session_summaries"),
    key="thread-456",
    value={
        "summary": "User asked about Python best practices",
        "key_topics": ["python", "coding", "best-practices"],
        "timestamp": "2026-02-13T10:30:00Z"
    }
)

# Search memory by keyword
results = store.search(
    namespace=("user123", "session_summaries"),
    query="python best practices",
    limit=5
)

for item in results:
    print(f"Thread: {item.key}")
    print(f"Summary: {item.value['summary']}")
```

### With Scheduling

```python
from emonk.core.scheduler import CronScheduler
from emonk.core.scheduler.handlers import register_handler
from datetime import datetime, timezone, timedelta

# Create scheduler
scheduler = CronScheduler(agent_state=agent_state)

# Define job handler
async def handle_reminder(job: dict):
    """Handle reminder job execution."""
    print(f"Sending reminder: {job['payload']['message']}")
    # Your reminder logic here

# Register handler (NEW: standardized pattern)
register_handler(scheduler, "send_reminder", handle_reminder)

# Or use convenience method
scheduler.register_handler("send_reminder", handle_reminder)

# Schedule a job
job_id = await scheduler.schedule_job(
    job_type="send_reminder",
    schedule_at=datetime.now(timezone.utc) + timedelta(hours=1),
    payload={
        "user_id": "user123",
        "message": "Don't forget to review the PR!"
    }
)

# Start scheduler loop (runs in background)
await scheduler.start()
```

### Full Production Setup

```python
from emonk import build_agent, GCSStore, create_search_memory_tool
from emonk.skills import SkillLoader, SkillExecutor
from emonk.sandbox import ModalSandboxBackend
from emonk.core.scheduler import CronScheduler
from langchain_google_vertexai import ChatVertexAI

# 1. Load skills
loader = SkillLoader(skills_dir="./skills")
executor = SkillExecutor(loader.load_skills())
skill_tools = executor.to_langchain_tools()

# 2. Setup GCS memory
store = GCSStore(bucket_name="prod-agent-memory")
memory_tool = create_search_memory_tool(store)

# 3. Setup sandbox (optional)
sandbox = ModalSandboxBackend()

# 4. Build agent
model = ChatVertexAI(model="gemini-2.5-flash")
agent = build_agent(
    model=model,
    tools=[*skill_tools, memory_tool],
    store=store,
    user_system_prompt="You are a helpful assistant for software engineers."
)

# 5. Setup scheduler
scheduler = CronScheduler(agent_state=agent_state)
await scheduler.start()

# 6. Use agent
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Help me debug this error"}]},
    config={"configurable": {"user_id": "user123", "thread_id": "thread789"}}
)
```

---

## Creating Skills

Skills are discovered from the `./skills/` directory. Each skill is a subdirectory containing:

1. **SKILL.md** — Metadata file with YAML frontmatter
2. **{skill_name}.py** — Python entry point

### SKILL.md Format

```markdown
---
name: file-ops
description: Read, write, and list files in the workspace
version: 1.0.0
author: ez-ai
---

# File Operations Skill

This skill provides file system operations for the agent.

## Functions

- `read_file(path: str) -> str` — Read file contents
- `write_file(path: str, content: str) -> None` — Write to file
- `list_files(directory: str) -> list[str]` — List directory contents
```

### Directory Structure

```
skills/
├── file-ops/
│   ├── SKILL.md
│   └── file_ops.py
├── memory/
│   ├── SKILL.md
│   └── memory.py
└── web-search/
    ├── SKILL.md
    └── web_search.py
```

### Entry Point Example

```python
# skills/file-ops/file_ops.py
from pathlib import Path
from langchain_core.tools import tool

@tool
def read_file(path: str) -> str:
    """Read contents of a file.
    
    Args:
        path: Path to file to read
        
    Returns:
        File contents as string
    """
    return Path(path).read_text()

@tool
def write_file(path: str, content: str) -> str:
    """Write content to a file.
    
    Args:
        path: Path to file to write
        content: Content to write
        
    Returns:
        Success message
    """
    Path(path).write_text(content)
    return f"Wrote {len(content)} bytes to {path}"

# Export tools
__all__ = ["read_file", "write_file"]
```

### How Agent Discovers Skills

1. `SkillLoader` scans `./skills/` for subdirectories
2. Parses YAML frontmatter from each `SKILL.md`
3. Imports the Python entry point (`{skill_name}.py`)
4. Converts functions decorated with `@tool` to LangChain tools
5. Agent receives tools with descriptions from SKILL.md

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes | — | Path to GCP service account JSON |
| `VERTEX_AI_PROJECT_ID` | Yes | — | GCP project ID for Vertex AI |
| `VERTEX_AI_LOCATION` | No | `us-central1` | Vertex AI region |
| `GCS_ENABLED` | No | `false` | Enable GCS memory sync |
| `GCS_MEMORY_BUCKET` | Conditional | — | GCS bucket name (required if `GCS_ENABLED=true`) |
| `ALLOWED_USERS` | No | — | Comma-separated list of authorized emails |
| `PORT` | No | `8080` | Server port |
| `LOG_LEVEL` | No | `INFO` | Log verbosity (DEBUG, INFO, WARNING, ERROR) |
| `SCHEDULER_STORAGE` | No | `json` | Scheduler storage backend (`json` or `firestore`) |
| `CRON_SECRET` | No | — | Optional secret for `/cron/tick` endpoint auth |

### Example `.env` File

```bash
# GCP Configuration
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
VERTEX_AI_PROJECT_ID=my-gcp-project
VERTEX_AI_LOCATION=us-central1

# GCS Memory (optional)
GCS_ENABLED=true
GCS_MEMORY_BUCKET=my-agent-memory

# Security
ALLOWED_USERS=user1@example.com,user2@example.com

# Server
PORT=8080
LOG_LEVEL=INFO

# Scheduler
SCHEDULER_STORAGE=firestore
CRON_SECRET=your-secret-here
```

---

## API Reference

### `build_agent()`

Factory function to create a LangChain agent with middleware and tools.

```python
def build_agent(
    model: BaseChatModel,
    tools: list[BaseTool],
    user_system_prompt: str = "",
    middleware: Optional[list] = None,
    checkpointer = None,
    store: Optional[BaseStore] = None,
    scheduler: Optional[CronScheduler] = None,
) -> CompiledGraph:
    """Build a LangChain agent with emonk middleware.
    
    Args:
        model: LangChain chat model (e.g., ChatVertexAI)
        tools: List of LangChain tools/skills
        user_system_prompt: Optional custom system prompt
        middleware: Custom middleware stack (defaults to SummarizationMiddleware)
        checkpointer: LangGraph checkpointer for conversation persistence
        store: LangGraph Store for long-term memory (enables SessionSummaryMiddleware)
        scheduler: Optional CronScheduler for job scheduling
        
    Returns:
        Compiled LangGraph agent ready for invocation
        
    Example:
        >>> from langchain_google_vertexai import ChatVertexAI
        >>> model = ChatVertexAI(model="gemini-2.5-flash")
        >>> agent = build_agent(model=model, tools=[])
        >>> result = agent.invoke({"messages": [...]})
    """
```

### Backends

#### `GCSStore`

Google Cloud Storage-backed LangGraph Store for long-term memory.

```python
class GCSStore(BaseStore):
    """GCS-backed Store for LangGraph long-term memory.
    
    Args:
        bucket_name: GCS bucket name for storing documents
        project_id: GCP project ID (optional, uses default credentials)
        index: Optional index config for semantic search (future)
    
    Methods:
        put(namespace, key, value): Store a document
        get(namespace, key): Retrieve a document
        delete(namespace, key): Delete a document
        search(namespace, query, limit): Search by keyword
        list(namespace, prefix, limit): List documents in namespace
    """
```

#### `ModalSandboxBackend`

Modal-based sandbox for isolated code execution (optional).

```python
class ModalSandboxBackend:
    """Modal-based sandbox for isolated code execution.
    
    Requires: pip install emonk[modal]
    
    Methods:
        execute(command: str, timeout: int = 60) -> SandboxResult
            Execute command in isolated Modal container
    
    Example:
        >>> sandbox = ModalSandboxBackend()
        >>> result = await sandbox.execute("python -c 'print(2+2)'")
        >>> print(result.output)  # "4"
    """
```

### Skills

#### `SkillLoader`

Discover and load skills from filesystem.

```python
class SkillLoader:
    """Discover and load skills from ./skills/ directory.
    
    Args:
        skills_dir: Path to skills directory (default: ./skills)
    
    Methods:
        load_skills() -> dict[str, dict]:
            Scan directory and return skill metadata
    
    Example:
        >>> loader = SkillLoader("./skills")
        >>> skills = loader.load_skills()
        >>> print(list(skills.keys()))
        ['file-ops', 'memory', 'web-search']
    """
```

#### `SkillExecutor`

Execute skills and convert to LangChain tools.

```python
class SkillExecutor:
    """Execute skills and convert to LangChain tools.
    
    Args:
        skills_metadata: Dict from SkillLoader.load_skills()
    
    Methods:
        to_langchain_tools() -> list[BaseTool]:
            Convert all skills to LangChain tools
    
    Example:
        >>> executor = SkillExecutor(skills_metadata)
        >>> tools = executor.to_langchain_tools()
        >>> agent = build_agent(model=model, tools=tools)
    """
```

---

## Development

```bash
# Clone
git clone https://github.com/ez-ai/monkey-bot.git
cd monkey-bot

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=html
open htmlcov/index.html

# Lint
ruff check .

# Format
ruff format .

# Type check
mypy src/
```

### Project Structure

```
monkey-bot/
├── src/
│   ├── core/
│   │   ├── agent.py           # build_agent factory
│   │   ├── store.py           # GCSStore
│   │   ├── middleware.py      # SessionSummaryMiddleware
│   │   ├── terminal.py        # TerminalExecutor (optional)
│   │   ├── interfaces.py      # Shared interfaces
│   │   └── scheduler/
│   │       ├── cron.py        # CronScheduler
│   │       └── storage.py     # JobStorage backends
│   ├── skills/
│   │   ├── loader.py          # SkillLoader
│   │   └── executor.py        # SkillExecutor
│   ├── sandbox/
│   │   └── modal.py           # ModalSandboxBackend
│   └── gateway/
│       ├── server.py          # FastAPI server
│       ├── pii_filter.py      # PII filtering
│       └── models.py          # Request/response models
├── skills/                     # User skills directory
├── tests/
├── pyproject.toml
└── README.md
```

### Code Quality Standards

- **Type Hints**: All functions must have type annotations (mypy strict mode)
- **Docstrings**: All public functions/classes must have Google-style docstrings
- **Tests**: Minimum 80% code coverage
- **Linting**: Use ruff for linting and formatting
- **Logging**: Structured JSON logs with trace IDs

---

## Security

### ⚠️ Critical Security Considerations

**Arbitrary Code Execution Risk**

emonk's skill system executes Python scripts from `./skills/` **without validation**. This means:

- ⚠️ Skills can execute arbitrary code with full agent permissions
- ⚠️ Only add skills from trusted sources
- ⚠️ Review ALL skill code before deployment
- ⚠️ Skills have access to: GCS buckets, Vertex AI, Google Chat API, local filesystem

**This is by design** to keep the framework simple and flexible. Security is the **developer's responsibility**.

### Production Security Checklist

- [ ] Review every skill script before adding to `./skills/`
- [ ] Use separate GCP projects for dev/prod
- [ ] Limit service account permissions to minimum required
- [ ] Monitor skill execution logs for unexpected behavior
- [ ] Use allowlist for authorized user emails (`ALLOWED_USERS`)
- [ ] Enable GCS encryption at rest
- [ ] Rotate service account keys every 90 days

### Terminal Executor Security (Optional)

The Terminal Executor uses allowlist-based security:

**Allowed Commands** (default):
- `cat` — Read files
- `ls` — List directories
- `python` — Execute Python scripts
- `uv` — Package management

**Allowed Paths** (default):
- `./data/memory/` — Memory storage
- `./skills/` — Skill scripts
- `./content/` — User content

Any command or path not explicitly allowed is **blocked**.

---

## Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run all checks (tests, type checking, linting)
4. Commit your changes (`git commit -m 'feat: add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Support

- **Deployment Guide**: [docs/deployment.md](docs/deployment.md)
- **Configuration Reference**: [.env.example](.env.example)
- **Example Skills**: [examples/skills/diagnostics/](examples/skills/diagnostics/)
- **Issues**: [GitHub Issues](https://github.com/ez-ai/monkey-bot/issues)
- **Documentation**: [GitHub Wiki](https://github.com/ez-ai/monkey-bot/wiki)
- **Community**: [GitHub Discussions](https://github.com/ez-ai/monkey-bot/discussions)

---

## Acknowledgments

Built with:
- [LangChain](https://github.com/langchain-ai/langchain) — LLM abstractions and agent framework
- [LangGraph](https://github.com/langchain-ai/langgraph) — Agent orchestration and state management
- [Vertex AI](https://cloud.google.com/vertex-ai) — Gemini models
- [FastAPI](https://fastapi.tiangolo.com/) — HTTP server
- [Modal](https://modal.com/) — Serverless sandbox execution (optional)
- [pytest](https://pytest.org/) — Testing framework
- [ruff](https://github.com/astral-sh/ruff) — Fast linter/formatter

---

Made with ❤️ by the ez-ai team
