# Emonk - Lightweight AI Agent Framework

Emonk is an open-source framework for building single-purpose AI agents that automate tasks via Google Chat. Built with FastAPI, designed for simplicity and maintainability.

## Features

- 🚀 **Google Chat Integration** - Receive messages via webhook, respond with Cards V2
- 🔒 **Privacy-First** - PII filtering with email hashing before processing
- 🛡️ **Secure** - Allowlist-based authorization, secure command execution
- 📦 **Modular** - Clean architecture with independent, testable components
- 🧪 **Well-Tested** - 80%+ test coverage, 100% for security-critical paths
- ☁️ **Cloud-Ready** - Deploy to Cloud Run with minimal configuration

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌────────────┐
│ Google Chat │─────▶│   Gateway    │─────▶│ Agent Core │
│  (Webhook)  │      │ (FastAPI)    │      │  (LLM)     │
└─────────────┘      └──────────────┘      └────────────┘
                            │
                            ├─────▶ Skills Engine
                            ├─────▶ Memory Manager
                            └─────▶ Terminal Executor
```

## Quick Start

### Prerequisites

- Python 3.11+
- Google Chat workspace
- Google Cloud account (for deployment)

### Local Development

1. **Clone and install dependencies:**

```bash
git clone https://github.com/yourusername/emonk.git
cd emonk
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment:**

```bash
cp .env.example .env
# Edit .env and set your ALLOWED_USERS
```

3. **Run the server:**

```bash
python -m src.gateway.main
```

Server will start at `http://localhost:8080`

4. **Test the health endpoint:**

```bash
curl http://localhost:8080/health
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/gateway/test_pii_filter.py

# Run with verbose output
pytest -v
```

### Code Quality Checks

```bash
# Type checking
mypy src/

# Code formatting (check only)
black --check src/ tests/

# Code formatting (apply)
black src/ tests/

# Linting
ruff check src/ tests/
```

## Project Structure

```
emonk/
├── src/
│   ├── gateway/           # HTTP interface & Google Chat integration
│   │   ├── server.py      # FastAPI application
│   │   ├── interfaces.py  # Agent Core interface contract
│   │   ├── models.py      # Pydantic models
│   │   ├── pii_filter.py  # Privacy filtering
│   │   ├── mocks.py       # Mock implementations for testing
│   │   └── main.py        # Entry point
│   ├── core/              # Agent orchestration (Story 2)
│   ├── skills/            # Skills engine (Story 3)
│   └── __init__.py
├── tests/
│   └── gateway/
│       ├── test_server.py
│       ├── test_pii_filter.py
│       └── test_google_chat.py
├── requirements.txt       # Python dependencies
├── pyproject.toml        # Tool configuration
├── .env.example          # Environment variable template
└── README.md
```

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ALLOWED_USERS` | Comma-separated list of authorized emails | `user@example.com,admin@example.com` |
| `LOG_LEVEL` | Logging level | `INFO` (default), `DEBUG`, `WARNING` |
| `PORT` | Server port | `8080` (default) |

## API Endpoints

### POST /webhook

Handle incoming Google Chat messages.

**Request:**
```json
{
  "message": {
    "sender": {"email": "user@example.com"},
    "text": "Your message here"
  }
}
```

**Response:**
```json
{
  "text": "Agent response here"
}
```

### GET /health

Health check endpoint for Cloud Run.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-11T22:00:00Z",
  "version": "1.0.0",
  "checks": {
    "agent_core": "ok"
  }
}
```

## Security

### PII Filtering

Emonk filters all personally identifiable information before processing:

- ✅ Email addresses are hashed (SHA-256, first 16 chars)
- ✅ Google Chat metadata (space IDs, thread IDs) is stripped
- ✅ Only message content is processed by LLM
- ✅ User IDs are stable (same email = same hash)

### Authorization

- Only users in `ALLOWED_USERS` can interact with the agent
- Authorization check happens before any processing
- 401 Unauthorized returned for non-allowlisted users

## Development Workflow

### Adding New Features

1. Create feature branch: `git checkout -b feature/your-feature`
2. Write tests first (TDD approach)
3. Implement feature
4. Run tests: `pytest`
5. Run code quality checks: `mypy`, `black`, `ruff`
6. Commit with clear message
7. Open pull request

### Code Quality Standards

- ✅ Type hints on all functions
- ✅ Docstrings on all public functions
- ✅ Test coverage ≥ 80%
- ✅ 100% coverage for security-critical code
- ✅ All tests passing
- ✅ mypy type checking passing
- ✅ Code formatted with black
- ✅ No linting errors (ruff)

## Deployment

### Cloud Run Deployment

Coming in Story 4 (Integration & Deployment).

## Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch
3. Write tests for new features
4. Ensure all tests pass and code quality checks pass
5. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

- 📖 Documentation: [docs/](docs/)
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/emonk/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/yourusername/emonk/discussions)

## Roadmap

- ✅ Phase 1: Core Foundation (Gateway, Agent Core, Skills Engine, Memory)
- 🔲 Phase 2: Marketing Campaign Agent
- 🔲 Phase 3: Cloud Deployment & Scaling
- 🔲 Phase 4: Production Hardening
- 🔲 Phase 5: Advanced Features

---

Built with ❤️ by the Auriga OS team
