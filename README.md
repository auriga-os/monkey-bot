# Emonk 🐵

**Open-source framework for building single-purpose AI agents**

Emonk is a lightweight, flexible framework that lets you build AI agents that automate tasks via Google Chat. Add custom skills easily, persist memory across invocations, and execute commands safely with allowlist-based security.

> ⚠️ **Security Warning**: Emonk's skill system executes Python scripts from the `./skills/` directory **without validation**. Only add skills from trusted sources and review all code before deployment. See [Security](#security) section below.

## Features

- 🤖 **LangGraph-based Agent** - Intelligent routing and orchestration
- 🎯 **Simple Skill System** - Add custom skills via SKILL.md + Python
- 💾 **Persistent Memory** - File-based with optional GCS sync
- ⏰ **Cloud Scheduler-Ready Jobs** - `/cron/tick` endpoint with metrics
- 🔒 **Secure Execution** - Allowlist-based command/path validation
- 💬 **Google Chat Integration** - Interact via Google Chat webhooks
- 📊 **Structured Logging** - JSON logs with trace IDs

## Quick Start

### Prerequisites

- Python 3.11+
- uv (fast Python package installer)
- Google Cloud account (for Vertex AI)

### Installation

```bash
# Clone repository
git clone https://github.com/auriga-os/emonk.git
cd emonk

# Create virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/core/test_agent.py

# Run with verbose output
pytest -v
```

### Type Checking

```bash
# Check types
mypy src/
```

### Code Formatting

```bash
# Format code
ruff format src/ tests/

# Check linting
ruff check src/ tests/

# Auto-fix linting issues
ruff check src/ tests/ --fix
```

## Deployment

### Local Development

1. **Create `.env` file:**
   ```bash
   cp .env.example .env
   # Edit .env and fill in your GCP credentials
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run locally:**
   ```bash
   python -m src.main
   # Or with auto-reload:
   uvicorn src.main:app --reload --port 8080
   ```

4. **Test:**
   ```bash
   curl http://localhost:8080/health
   ```

### Cloud Run Deployment

1. **Prerequisites:**
   - GCP project with Vertex AI API enabled
   - Service account with roles:
     - Vertex AI User
     - Storage Object Admin
     - Cloud Run Admin
   - GCS bucket created: `gsutil mb gs://your-bucket-name`

2. **Configure `.env`:**
   ```bash
   # Set these in .env:
   VERTEX_AI_PROJECT_ID=your-project-id
   GCS_MEMORY_BUCKET=your-bucket-name
   CLOUD_RUN_SERVICE_NAME=emonk-agent
   CLOUD_RUN_REGION=us-central1
   ALLOWED_USERS=user1@example.com,user2@example.com
   ```

3. **Deploy:**
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

4. **Configure Google Chat webhook:**
   - Go to https://chat.google.com
   - Create app → Webhooks
   - Set webhook URL: `https://YOUR-SERVICE-URL/webhook`

5. **Configure Cloud Scheduler (recommended for production):**
   - Set `SCHEDULER_STORAGE=firestore` in `.env`
   - Run `./setup-scheduler.sh`
   - Verify with `gcloud scheduler jobs run emonk-agent-tick --location us-central1`

6. **Test:**
   - Send message in Google Chat
   - Check logs: `gcloud run logs read emonk-agent --region us-central1`
   - Check scheduler logs: `gcloud run logs read emonk-agent --region us-central1 --filter="jsonPayload.message:scheduler"`

### Scheduler Migration (Recent)

The scheduler architecture has been upgraded from an in-process loop to Cloud Scheduler-triggered ticks:

- `POST /cron/tick` runs one scheduler cycle and returns execution metrics
- Scheduler storage supports:
  - `json` for local/dev
  - `firestore` for production distributed locking
- Optional `CRON_SECRET` auth is supported for non-Scheduler callers

Use these guides for rollout details:
- `SCHEDULER_SETUP.md` - full setup and IAM
- `CLOUD_SCHEDULER_MIGRATION.md` - migration quick start
- `ROLLOUT_GUIDE.md` - staged rollout and rollback plan

## Testing

### Run Unit Tests (Fast, No API Costs)
```bash
pytest
```

### Run Integration Tests (Real Vertex AI API)
```bash
# Set credentials first:
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
export VERTEX_AI_PROJECT_ID=your-project-id

# Run integration tests:
pytest -m integration
```

### Run Scheduler Integration Tests
```bash
pytest tests/integration/test_cron_tick.py -v
pytest tests/core/test_cron_scheduler.py -v
pytest tests/unit/test_scheduler_storage.py -v
```

### Run All Tests with Coverage
```bash
pytest -m "" --cov=src --cov-report=html
open htmlcov/index.html
```

## Environment Variables

See `.env.example` for complete list of configuration options.

**Required:**
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to GCP service account JSON
- `VERTEX_AI_PROJECT_ID` - GCP project ID
- `ALLOWED_USERS` - Comma-separated list of authorized emails

**Optional:**
- `GCS_ENABLED=false` - Enable GCS sync (default: false for local dev)
- `GCS_MEMORY_BUCKET` - GCS bucket for memory (required if GCS_ENABLED=true)
- `VERTEX_AI_LOCATION=us-central1` - Vertex AI region
- `PORT=8080` - Server port
- `LOG_LEVEL=INFO` - Log verbosity

## Troubleshooting

### "Missing required environment variables" error
- Copy `.env.example` to `.env`
- Fill in all required values (see comments in file)
- Verify `GOOGLE_APPLICATION_CREDENTIALS` file exists

### "Vertex AI authentication failed" error
- Verify service account has Vertex AI User role
- Download fresh service account key from GCP Console
- Set `GOOGLE_APPLICATION_CREDENTIALS` to correct path

### "GCS sync failed" error
- Verify service account has Storage Object Admin role
- Verify GCS bucket exists: `gsutil ls gs://your-bucket-name`
- Check `GCS_MEMORY_BUCKET` env var matches bucket name

### Tests hang on integration test
- Verify `GOOGLE_APPLICATION_CREDENTIALS` is set
- Check GCP quota limits (Vertex AI requests per minute)
- Use `pytest -v` to see which test is hanging

## Project Status

### Implemented
- ✅ Core foundation (Gateway + Agent Core + LLM + Skills + Memory)
- ✅ Google Chat webhook integration with allowlist and PII filtering
- ✅ Scheduler engine with persistence, retry, and storage abstraction
- ✅ Cloud Scheduler migration path (`/cron/tick`, setup/rollout docs, tests)
- ✅ Cloud Run deployment scripts and environment configuration

### In Progress / Planned
- 📋 Marketing campaign manager expansion tracked in `.monkeymode/marketing-campaign-manager/`
- 📋 Additional domain skills and platform integrations (see `docs/phases/phase-2-marketing-campaign.md`)
- 📋 Production hardening and advanced features (see `docs/phases/README.md`)

## Architecture

```
┌─────────────────────────────────────────────┐
│            Gateway (FastAPI)                │
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
│            Agent Core (LangGraph)           │
│   - Message routing & orchestration         │
│   - Conversation context (last 10 msgs)     │
│   - LLM integration (Gemini 2.0 Flash)      │
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

## Usage

### Basic Example (with Mocks)

```python
from src.core import create_agent_with_mocks

# Create agent with mock dependencies
agent = create_agent_with_mocks()

# Process a message
response = await agent.process_message(
    user_id="user_123",
    content="Hello, how are you?",
    trace_id="trace_abc"
)

print(response)
# Output: "Hello! I'm Emonk, your AI assistant. How can I help you today?"
```

### Custom Agent (with Real Dependencies)

```python
from src.core import AgentCore, LLMClient
from langchain_google_vertexai import ChatVertexAI

# Create real LLM client (Story 4)
vertex_llm = ChatVertexAI(model_name="gemini-2.5-flash-002")
llm_client = LLMClient(vertex_llm)

# Create agent with real dependencies
agent = AgentCore(
    llm_client=llm_client,
    skills_engine=your_skills_engine,
    memory_manager=your_memory_manager
)

# Process messages
response = await agent.process_message(
    user_id="user_123",
    content="Remember that I prefer Python",
    trace_id="trace_xyz"
)
```

## Security

### ⚠️ Critical Security Considerations

**Arbitrary Code Execution Risk**

Emonk's skill system executes Python scripts from `./skills/` **without validation**. This means:

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

### Terminal Executor Security

The Terminal Executor uses allowlist-based security:

**Allowed Commands** (default):
- `cat` - Read files
- `ls` - List directories
- `python` - Execute Python scripts
- `uv` - Package management

**Allowed Paths** (default):
- `./data/memory/` - Memory storage
- `./skills/` - Skill scripts
- `./content/` - User content

Any command or path not explicitly allowed is **blocked**.

## Development

### Project Structure

```
emonk/
├── src/
│   └── core/
│       ├── __init__.py          # Public API exports
│       ├── interfaces.py        # ALL shared interfaces (single source of truth)
│       ├── agent.py             # Agent Core (LangGraph)
│       ├── llm_client.py        # LLM wrapper (Vertex AI)
│       └── mocks.py             # Mock dependencies for testing
├── tests/
│   └── core/
│       ├── test_agent.py        # Agent Core tests
│       ├── test_llm_client.py   # LLM Client tests
│       └── test_integration.py  # End-to-end tests
├── pyproject.toml               # Project metadata + dependencies
├── .python-version              # Python version (3.11)
└── README.md                    # This file
```

### Code Quality Standards

- **Type Hints**: All functions must have type annotations (mypy strict mode)
- **Docstrings**: All public functions/classes must have Google-style docstrings
- **Tests**: Minimum 80% code coverage
- **Linting**: Use ruff for linting and formatting
- **Logging**: Structured JSON logs with trace IDs

### Running Development Checks

```bash
# Run all checks before committing
pytest --cov=src --cov-report=term-missing  # Tests + coverage
mypy src/                                    # Type checking
ruff check src/ tests/                       # Linting
ruff format src/ tests/                      # Formatting
```

## Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run all checks (tests, type checking, linting)
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/auriga-os/emonk/issues)
- **Documentation**: [GitHub Wiki](https://github.com/auriga-os/emonk/wiki)
- **Community**: [GitHub Discussions](https://github.com/auriga-os/emonk/discussions)

## Acknowledgments

Built with:
- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent orchestration
- [LangChain](https://github.com/langchain-ai/langchain) - LLM abstractions
- [Vertex AI](https://cloud.google.com/vertex-ai) - Gemini models
- [FastAPI](https://fastapi.tiangolo.com/) - HTTP server
- [pytest](https://pytest.org/) - Testing framework
- [ruff](https://github.com/astral-sh/ruff) - Fast linter/formatter

---

Made with ❤️ by the Auriga OS team
