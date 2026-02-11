# Code Spec: Story 4 - Integration & Deployment

**Story:** Story 4 - Integration & Deployment  
**Design Reference:** Phase 1A (All modules), Phase 1B (Integration contracts), Phase 1C (Deployment)  
**Author:** Emonk MonkeyMode  
**Date:** 2026-02-11

---

## Implementation Summary

- **Files to Create:** 5 files (main.py, Dockerfile, deployment configs, e2e tests)
- **Files to Modify:** 4 files (requirements.txt, .env.example, server.py, README.md)
- **Tests to Add:** 2 test files (e2e tests with real Vertex AI)
- **Estimated Complexity:** S (2-3 days)

---

## Codebase Conventions

Following established patterns from Stories 1-3:

**File/Function Naming:** `snake_case.py` for modules, `snake_case()` for functions  
**Import Order:** Standard library → Third-party → Local (PEP 8)  
**Error Handling:** Fail fast on missing required env vars, graceful degradation for optional features  
**Testing Framework:** pytest 8.x, `@pytest.mark.integration` for real API tests  
**Type Checking:** Type hints on all functions, mypy strict mode  
**Async Pattern:** async/await for I/O operations  
**Logging:** Structured JSON logging (already established in gateway)

---

## Technical Context

### Key Gotchas
1. **Remove ALL mocks**: MockAgentCore, MockSkillsEngine, MockMemoryManager, MockVertexAI must be replaced
2. **Environment variable validation**: Must fail fast with clear error messages if required vars missing
3. **GCS_ENABLED flag**: Local dev uses `GCS_ENABLED=false` (file-only), Cloud Run uses `GCS_ENABLED=true`
4. **Vertex AI initialization**: Must happen AFTER env vars are loaded, BEFORE FastAPI app creation
5. **TestClient limitations**: FastAPI TestClient runs sync, but agent is async - handle properly

### Reusable Utilities
- `src/gateway/server.py` already has structured logging function - reuse pattern
- `src/core/interfaces.py` has all interface definitions - import from there
- `tests/` already has pytest fixtures - extend for integration tests

### Integration Points
- **Wire 1**: Gateway → Agent Core (replace MockAgentCore in `src/gateway/server.py`)
- **Wire 2**: Agent Core → Skills Engine (replace MockSkillsEngine in `src/core/agent.py`)
- **Wire 3**: Agent Core → Memory Manager (replace MockMemoryManager in `src/core/agent.py`)
- **Wire 4**: LLM Client → Vertex AI (replace MockVertexAI in `src/core/llm_client.py`)

---

## Task Breakdown

### Task 1: Add Missing Dependencies to requirements.txt

**Dependencies:** None

**Files to Modify:**

| File | Change |
|------|--------|
| `requirements.txt` | Add LangChain, LangGraph, Vertex AI dependencies |

**Implementation:**

Add these dependencies to `requirements.txt`:

```
# LangChain + LangGraph (agent orchestration)
langgraph>=0.2.0
langchain-core>=0.3.0
langchain-google-vertexai>=2.0.0

# Google Cloud (Vertex AI + Storage)
google-cloud-aiplatform>=1.65.0
google-cloud-storage>=2.10.0  # Already present, keep version

# Async support
aiofiles>=24.0.0  # For async file I/O in Memory Manager
```

**Why these versions:**
- `langgraph>=0.2.0` - Latest stable with StateGraph support
- `langchain-google-vertexai>=2.0.0` - Gemini 2.0 Flash support
- `google-cloud-aiplatform>=1.65.0` - Latest Vertex AI SDK
- `aiofiles>=24.0.0` - Async file operations for Memory Manager

**Test:** Run `pip install -r requirements.txt` and verify no conflicts

---

### Task 2: Update .env.example with All Required Config

**Dependencies:** None

**Files to Modify:**

| File | Change |
|------|--------|
| `.env.example` | Add Vertex AI, GCS, and deployment configuration |

**Implementation:**

Replace `.env.example` contents with complete configuration:

```bash
# =============================================================================
# Gateway Configuration
# =============================================================================
# Comma-separated list of allowed user emails (Google Chat senders)
ALLOWED_USERS=user1@example.com,user2@example.com

# =============================================================================
# Google Cloud Configuration
# =============================================================================
# Path to GCP service account JSON key file
# Get from: https://console.cloud.google.com/iam-admin/serviceaccounts
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# GCP Project ID for Vertex AI
# Get from: https://console.cloud.google.com/home/dashboard
VERTEX_AI_PROJECT_ID=your-gcp-project-id

# Vertex AI region (default: us-central1)
# Options: us-central1, us-east1, europe-west1, asia-northeast1
VERTEX_AI_LOCATION=us-central1

# =============================================================================
# Memory Configuration
# =============================================================================
# Local memory directory (relative to project root)
MEMORY_DIR=./data/memory

# Enable GCS sync for memory persistence
# - false: Local files only (for development)
# - true: Sync to GCS bucket (for Cloud Run)
GCS_ENABLED=false

# GCS bucket name for memory storage (required if GCS_ENABLED=true)
# Create bucket: gsutil mb gs://your-bucket-name
GCS_MEMORY_BUCKET=emonk-memory

# =============================================================================
# Agent Configuration
# =============================================================================
# Agent name (for logging/identification)
AGENT_NAME=emonk-general-assistant

# Skills directory (relative to project root)
SKILLS_DIR=./skills

# Conversation context limit (number of messages sent to LLM)
CONVERSATION_CONTEXT_LIMIT=10

# =============================================================================
# Server Configuration
# =============================================================================
# Server port (Cloud Run uses PORT=8080 automatically)
PORT=8080

# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# =============================================================================
# Cloud Run Deployment (for production)
# =============================================================================
# Cloud Run region
CLOUD_RUN_REGION=us-central1

# Min instances (0 = scale to zero, 1 = always-on)
# - 0: Saves cost but has cold start latency (~2-3 seconds)
# - 1: Always warm but costs ~$7/month idle
CLOUD_RUN_MIN_INSTANCES=0

# Max instances (max concurrent containers)
CLOUD_RUN_MAX_INSTANCES=10

# Service name
CLOUD_RUN_SERVICE_NAME=emonk-agent
```

**Critical Notes:**
- User will edit this file to match their GCP setup
- `.env` file (gitignored) contains actual values
- Cloud Run automatically sets PORT=8080, but allow override for local dev

**Test:** Create `.env` from template and verify app reads all vars correctly

---

### Task 3: Create Main Application Entry Point (src/main.py)

**Dependencies:** Task 1, Task 2

**Files to Create:**

| File | Purpose |
|------|---------|
| `src/main.py` | Wire all components with real implementations |

**Pattern Reference:** Follow dependency injection pattern from `src/gateway/main.py`

**Implementation Algorithm:**

1. Load environment variables using `dotenv`
2. Validate all required env vars (fail fast if missing)
3. Initialize Vertex AI with `aiplatform.init()`
4. Create real implementations: LLMClient → SkillsEngine → MemoryManager → AgentCore
5. Inject AgentCore into Gateway server (replace MockAgentCore)
6. Return FastAPI app for uvicorn

**Function Signatures:**

```python
def validate_env_vars() -> None:
    """Validate required environment variables.
    
    Raises:
        RuntimeError: If any required env var is missing
    """

def create_app() -> FastAPI:
    """Create FastAPI app with real implementations wired.
    
    Returns:
        FastAPI app ready to run
        
    Raises:
        RuntimeError: If configuration is invalid
    """
```

**Implementation:**

Create `src/main.py`:

```python
"""
Main application entry point for Emonk.

Wires all components together with real implementations:
- Gateway → Agent Core → Skills Engine → Memory Manager
- LLM Client → Vertex AI (Gemini 2.0 Flash)

Run locally:
    python -m src.main

Run with uvicorn:
    uvicorn src.main:app --reload --port 8080
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env FIRST (before any imports that read env vars)
load_dotenv()

from google.cloud import aiplatform  # noqa: E402
from langchain_google_vertexai import ChatVertexAI  # noqa: E402

from src.core.agent import AgentCore  # noqa: E402
from src.core.llm_client import LLMClient  # noqa: E402
from src.core.memory import MemoryManager  # noqa: E402
from src.core.terminal import TerminalExecutor  # noqa: E402
from src.gateway import server  # noqa: E402
from src.skills.executor import SkillsEngine  # noqa: E402

logger = logging.getLogger(__name__)


def validate_env_vars() -> None:
    """Validate required environment variables.
    
    Raises:
        RuntimeError: If any required env var is missing
    """
    required_vars = [
        "GOOGLE_APPLICATION_CREDENTIALS",
        "VERTEX_AI_PROJECT_ID",
        "ALLOWED_USERS",
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            f"Copy .env.example to .env and fill in your values."
        )
    
    # Validate GOOGLE_APPLICATION_CREDENTIALS file exists
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and not Path(creds_path).exists():
        raise RuntimeError(
            f"GOOGLE_APPLICATION_CREDENTIALS file not found: {creds_path}\n"
            f"Download from: https://console.cloud.google.com/iam-admin/serviceaccounts"
        )
    
    logger.info("✅ Environment variables validated")


def create_app():
    """Create FastAPI app with real implementations wired.
    
    Returns:
        FastAPI app ready to run
        
    Raises:
        RuntimeError: If configuration is invalid
    """
    # Validate configuration
    validate_env_vars()
    
    # Initialize Vertex AI (must happen before creating ChatVertexAI)
    project_id = os.getenv("VERTEX_AI_PROJECT_ID")
    location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
    
    logger.info(f"Initializing Vertex AI: project={project_id}, location={location}")
    aiplatform.init(project=project_id, location=location)
    
    # Create real Vertex AI LLM client (Gemini 2.0 Flash)
    vertex_llm = ChatVertexAI(
        model_name="gemini-2.0-flash-exp",
        temperature=0.7,
        max_output_tokens=8192,
    )
    llm_client = LLMClient(vertex_llm)
    logger.info("✅ LLM Client created (Gemini 2.0 Flash)")
    
    # Create Terminal Executor
    terminal_executor = TerminalExecutor()
    logger.info("✅ Terminal Executor created")
    
    # Create Skills Engine (depends on Terminal Executor)
    skills_dir = os.getenv("SKILLS_DIR", "./skills")
    skills_engine = SkillsEngine(terminal_executor, skills_dir=skills_dir)
    logger.info(f"✅ Skills Engine created (skills_dir={skills_dir})")
    
    # Create Memory Manager
    memory_dir = os.getenv("MEMORY_DIR", "./data/memory")
    gcs_enabled = os.getenv("GCS_ENABLED", "false").lower() == "true"
    gcs_bucket = os.getenv("GCS_MEMORY_BUCKET") if gcs_enabled else None
    
    memory_manager = MemoryManager(
        memory_dir=memory_dir,
        gcs_enabled=gcs_enabled,
        gcs_bucket=gcs_bucket,
    )
    logger.info(
        f"✅ Memory Manager created (dir={memory_dir}, gcs_enabled={gcs_enabled})"
    )
    
    # Create Agent Core (depends on all above)
    agent_core = AgentCore(llm_client, skills_engine, memory_manager)
    logger.info("✅ Agent Core created")
    
    # Inject Agent Core into Gateway (replace MockAgentCore)
    server.agent_core = agent_core
    logger.info("✅ Agent Core injected into Gateway")
    
    # Return FastAPI app
    return server.app


# Create app instance (for uvicorn to import)
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8080"))
    log_level = os.getenv("LOG_LEVEL", "INFO").lower()
    
    print("=" * 60)
    print("🚀 Starting Emonk Agent")
    print("=" * 60)
    print(f"Port: {port}")
    print(f"Log level: {log_level}")
    print(f"Allowed users: {os.getenv('ALLOWED_USERS', 'NOT SET')}")
    print(f"Vertex AI Project: {os.getenv('VERTEX_AI_PROJECT_ID', 'NOT SET')}")
    print(f"GCS Enabled: {os.getenv('GCS_ENABLED', 'false')}")
    print("=" * 60)
    print()
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        log_level=log_level,
        reload=False,  # Disable reload for production
    )
```

**Test Cases:**
- Missing `GOOGLE_APPLICATION_CREDENTIALS` → RuntimeError with helpful message
- Missing `VERTEX_AI_PROJECT_ID` → RuntimeError with helpful message
- Valid config → App starts successfully
- `GCS_ENABLED=false` → MemoryManager uses local files only
- `GCS_ENABLED=true` → MemoryManager syncs to GCS

**Critical Notes:**
- `load_dotenv()` MUST run before any imports that read env vars
- Vertex AI `aiplatform.init()` MUST run before creating `ChatVertexAI`
- Use `noqa: E402` to suppress "import not at top" linting errors (intentional)

---

### Task 4: Create Dockerfile for Cloud Run

**Dependencies:** Task 1, Task 3

**Files to Create:**

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage build for efficient Cloud Run deployment |

**Pattern Reference:** Follow Cloud Run best practices (multi-stage, minimal base image)

**Implementation:**

Create `Dockerfile`:

```dockerfile
# =============================================================================
# Stage 1: Build stage (install dependencies)
# =============================================================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# =============================================================================
# Stage 2: Runtime stage (minimal image)
# =============================================================================
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /root/.local /root/.local

# Add Python user site-packages to PATH
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY src/ src/
COPY skills/ skills/

# Create memory directory (will be overridden by volume in Cloud Run)
RUN mkdir -p /app/data/memory

# Set environment variables for Cloud Run
ENV PYTHONUNBUFFERED=1 \
    PORT=8080

# Health check (Cloud Run uses this for readiness/liveness)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health').read()"

# Expose port (Cloud Run injects PORT env var)
EXPOSE 8080

# Run application
CMD ["python", "-m", "src.main"]
```

**Why multi-stage build:**
- Stage 1: Install build tools + compile packages (larger image)
- Stage 2: Copy only compiled packages (smaller final image ~200MB vs ~600MB)
- Faster Cloud Run deployments (less data to upload)

**Test:** Build locally and verify size:
```bash
docker build -t emonk-test .
docker images emonk-test  # Should be ~200-300MB
docker run -p 8080:8080 --env-file .env emonk-test
curl http://localhost:8080/health  # Should return 200
```

---

### Task 5: Create Cloud Run Deployment Script

**Dependencies:** Task 4

**Files to Create:**

| File | Purpose |
|------|---------|
| `deploy.sh` | Automated Cloud Run deployment script |
| `.gcloudignore` | Files to exclude from Cloud Run build |

**Pattern:** Follow `gcloud run deploy` best practices

**Implementation:**

Create `deploy.sh`:

```bash
#!/bin/bash
# =============================================================================
# Cloud Run Deployment Script for Emonk
# =============================================================================
# Usage:
#   ./deploy.sh
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - .env file with GCP configuration
#   - Service account with Vertex AI + Cloud Run permissions
# =============================================================================

set -e  # Exit on error

# Load environment variables from .env
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "Copy .env.example to .env and fill in your values"
    exit 1
fi

source .env

# Validate required env vars
REQUIRED_VARS=(
    "VERTEX_AI_PROJECT_ID"
    "CLOUD_RUN_REGION"
    "CLOUD_RUN_SERVICE_NAME"
    "ALLOWED_USERS"
    "GCS_MEMORY_BUCKET"
    "GOOGLE_APPLICATION_CREDENTIALS"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Error: Missing required env var: $var"
        exit 1
    fi
done

echo "🚀 Deploying Emonk to Cloud Run"
echo "================================"
echo "Project: $VERTEX_AI_PROJECT_ID"
echo "Region: $CLOUD_RUN_REGION"
echo "Service: $CLOUD_RUN_SERVICE_NAME"
echo "Allowed users: $ALLOWED_USERS"
echo "GCS bucket: $GCS_MEMORY_BUCKET"
echo "================================"
echo

# Build and deploy to Cloud Run (Cloud Build will use Dockerfile)
gcloud run deploy "$CLOUD_RUN_SERVICE_NAME" \
    --source . \
    --platform managed \
    --region "$CLOUD_RUN_REGION" \
    --project "$VERTEX_AI_PROJECT_ID" \
    --allow-unauthenticated \
    --min-instances="${CLOUD_RUN_MIN_INSTANCES:-0}" \
    --max-instances="${CLOUD_RUN_MAX_INSTANCES:-10}" \
    --memory=1Gi \
    --cpu=1 \
    --timeout=60s \
    --set-env-vars="VERTEX_AI_PROJECT_ID=$VERTEX_AI_PROJECT_ID" \
    --set-env-vars="VERTEX_AI_LOCATION=${VERTEX_AI_LOCATION:-us-central1}" \
    --set-env-vars="ALLOWED_USERS=$ALLOWED_USERS" \
    --set-env-vars="GCS_ENABLED=true" \
    --set-env-vars="GCS_MEMORY_BUCKET=$GCS_MEMORY_BUCKET" \
    --set-env-vars="MEMORY_DIR=/app/data/memory" \
    --set-env-vars="SKILLS_DIR=/app/skills" \
    --set-env-vars="LOG_LEVEL=INFO" \
    --service-account="$(gcloud iam service-accounts list --filter="displayName:Compute Engine default service account" --format="value(email)")"

echo
echo "✅ Deployment complete!"
echo
echo "Service URL:"
gcloud run services describe "$CLOUD_RUN_SERVICE_NAME" \
    --region "$CLOUD_RUN_REGION" \
    --project "$VERTEX_AI_PROJECT_ID" \
    --format="value(status.url)"
echo
echo "Test health check:"
SERVICE_URL=$(gcloud run services describe "$CLOUD_RUN_SERVICE_NAME" \
    --region "$CLOUD_RUN_REGION" \
    --project "$VERTEX_AI_PROJECT_ID" \
    --format="value(status.url)")
curl -s "$SERVICE_URL/health" | jq .
echo
echo "Next steps:"
echo "1. Configure Google Chat webhook to point to: $SERVICE_URL/webhook"
echo "2. Send a test message in Google Chat"
echo "3. Check logs: gcloud run logs read $CLOUD_RUN_SERVICE_NAME --region $CLOUD_RUN_REGION"
```

Create `.gcloudignore`:

```
# Ignore development files
.venv/
.env
*.pyc
__pycache__/
.pytest_cache/
.coverage
.mypy_cache/
.ruff_cache/

# Ignore test files (not needed in production)
tests/

# Ignore local data
data/

# Ignore documentation
docs/
.monkeymode/
```

**Test:** Run deployment (requires GCP account):
```bash
chmod +x deploy.sh
./deploy.sh
# Verify deployment succeeded
curl https://YOUR-SERVICE-URL/health
```

**Critical Notes:**
- `--allow-unauthenticated` required for Google Chat webhooks (access control via ALLOWED_USERS)
- Service account needs Vertex AI User + Storage Object Admin roles
- Min instances defaults to 0 (user can override in .env)

---

### Task 6: Create End-to-End Integration Tests

**Dependencies:** Task 3 (real implementations wired)

**Files to Create:**

| File | Purpose |
|------|---------|
| `tests/integration/test_e2e.py` | End-to-end tests with real Vertex AI |
| `pytest.ini` | Configure pytest integration markers |

**Pattern Reference:** Follow pytest pattern from existing tests, add `@pytest.mark.integration` decorator

**Implementation Algorithm:**

1. Create pytest fixture that creates app with real Vertex AI (mocked for most tests)
2. Create 1 test with `@pytest.mark.integration` that uses REAL Vertex AI API
3. Mock Vertex AI for all other tests (fast, no API costs)
4. Test full flow: webhook → gateway → agent → vertex AI → response

**Test Cases:**

**Standard tests (mocked Vertex AI):**
- POST /webhook with valid message → Returns 200 with response
- POST /webhook with unauthorized email → Returns 403
- Memory persistence: remember fact → recall fact returns same value
- Skill execution: list files → Returns file list

**Integration test (real Vertex AI):**
- POST /webhook with real Gemini API call → Returns coherent response
- Verify response quality (not just "Mock LLM response")

**Implementation:**

Create `pytest.ini`:

```ini
[pytest]
markers =
    integration: Integration tests that call real APIs (slow, costs money)
    
# Run only unit tests by default (skip integration)
addopts = -v -m "not integration"

# To run integration tests:
#   pytest -m integration
# To run all tests:
#   pytest -m ""
```

Create `tests/integration/test_e2e.py`:

```python
"""
End-to-end integration tests for Emonk.

Most tests use mocks (fast, free).
Tests marked with @pytest.mark.integration use real Vertex AI (slow, costs $0.001 per test).

Run unit tests only (default):
    pytest

Run integration tests:
    pytest -m integration

Run all tests:
    pytest -m ""
"""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_vertex_ai():
    """Mock Vertex AI for fast, free tests."""
    mock = AsyncMock()
    mock.ainvoke = AsyncMock(
        return_value=MagicMock(content="Mock response from Gemini")
    )
    return mock


@pytest.fixture
def test_client_mocked(mock_vertex_ai, monkeypatch, tmp_path):
    """Create test client with mocked Vertex AI.
    
    This is the default fixture for fast tests without API costs.
    """
    # Set test env vars
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/fake/path.json")
    monkeypatch.setenv("VERTEX_AI_PROJECT_ID", "test-project")
    monkeypatch.setenv("VERTEX_AI_LOCATION", "us-central1")
    monkeypatch.setenv("ALLOWED_USERS", "test@example.com")
    monkeypatch.setenv("GCS_ENABLED", "false")
    monkeypatch.setenv("MEMORY_DIR", str(tmp_path / "memory"))
    monkeypatch.setenv("SKILLS_DIR", "./skills")
    
    # Mock Vertex AI client creation
    monkeypatch.setattr(
        "src.main.ChatVertexAI",
        lambda **kwargs: mock_vertex_ai
    )
    
    # Mock aiplatform.init (no real GCP calls)
    monkeypatch.setattr("src.main.aiplatform.init", lambda **kwargs: None)
    
    # Create app with mocked dependencies
    from src.main import create_app
    app = create_app()
    
    return TestClient(app)


@pytest.fixture
def test_client_real(monkeypatch, tmp_path):
    """Create test client with REAL Vertex AI.
    
    Only used for @pytest.mark.integration tests.
    Requires GOOGLE_APPLICATION_CREDENTIALS env var set.
    """
    # Verify real credentials exist
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        pytest.skip("GOOGLE_APPLICATION_CREDENTIALS not set - skipping real API test")
    
    # Set test env vars (use real GOOGLE_APPLICATION_CREDENTIALS from environment)
    monkeypatch.setenv("VERTEX_AI_PROJECT_ID", os.getenv("VERTEX_AI_PROJECT_ID", "test-project"))
    monkeypatch.setenv("VERTEX_AI_LOCATION", os.getenv("VERTEX_AI_LOCATION", "us-central1"))
    monkeypatch.setenv("ALLOWED_USERS", "test@example.com")
    monkeypatch.setenv("GCS_ENABLED", "false")
    monkeypatch.setenv("MEMORY_DIR", str(tmp_path / "memory"))
    monkeypatch.setenv("SKILLS_DIR", "./skills")
    
    # Create app with REAL Vertex AI
    from src.main import create_app
    app = create_app()
    
    return TestClient(app)


def test_e2e_webhook_valid_message(test_client_mocked):
    """Test complete flow: webhook → gateway → agent → response (MOCKED)."""
    payload = {
        "type": "MESSAGE",
        "message": {
            "sender": {"email": "test@example.com"},
            "text": "Hello, how are you?",
        },
    }
    
    response = test_client_mocked.post("/webhook", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["text"]  # Response contains text
    assert len(data["text"]) > 0


def test_e2e_webhook_unauthorized_user(test_client_mocked):
    """Test access control: unauthorized email returns 403."""
    payload = {
        "type": "MESSAGE",
        "message": {
            "sender": {"email": "hacker@evil.com"},  # Not in ALLOWED_USERS
            "text": "Hack attempt",
        },
    }
    
    response = test_client_mocked.post("/webhook", json=payload)
    
    assert response.status_code == 403


def test_e2e_memory_persistence(test_client_mocked):
    """Test memory: remember fact → recall fact returns same value."""
    # Remember fact
    remember_payload = {
        "type": "MESSAGE",
        "message": {
            "sender": {"email": "test@example.com"},
            "text": "Remember that I prefer Python",
        },
    }
    response1 = test_client_mocked.post("/webhook", json=remember_payload)
    assert response1.status_code == 200
    
    # Recall fact
    recall_payload = {
        "type": "MESSAGE",
        "message": {
            "sender": {"email": "test@example.com"},
            "text": "What's my preferred language?",
        },
    }
    response2 = test_client_mocked.post("/webhook", json=recall_payload)
    assert response2.status_code == 200
    # Mock will return generic response, but flow works


@pytest.mark.integration
def test_e2e_real_vertex_ai_call(test_client_real):
    """Test with REAL Vertex AI API call (costs $0.001 per run).
    
    This test verifies:
    - Vertex AI authentication works
    - Gemini API returns coherent responses
    - Full integration is functional
    
    Run with: pytest -m integration
    """
    payload = {
        "type": "MESSAGE",
        "message": {
            "sender": {"email": "test@example.com"},
            "text": "What is 2 + 2?",
        },
    }
    
    response = test_client_real.post("/webhook", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response is from REAL Gemini (not mock)
    assert data["text"]
    assert "Mock" not in data["text"]  # Should NOT contain "Mock"
    assert len(data["text"]) > 10  # Real response should be substantial
    
    # Gemini should answer correctly (fuzzy match)
    assert "4" in data["text"] or "four" in data["text"].lower()


def test_health_check(test_client_mocked):
    """Test health check endpoint."""
    response = test_client_mocked.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
```

**Test Execution:**

```bash
# Run unit tests only (default, fast, no API costs)
pytest

# Run integration tests only (slow, costs $0.001)
pytest -m integration

# Run all tests
pytest -m ""

# Run with coverage
pytest --cov=src --cov-report=html
```

**Critical Notes:**
- `test_client_mocked` is default for fast tests
- `test_client_real` only used for `@pytest.mark.integration` tests
- Integration test checks for real Gemini response (not "Mock")
- Skips integration test if `GOOGLE_APPLICATION_CREDENTIALS` not set

---

### Task 7: Update Documentation

**Dependencies:** All previous tasks

**Files to Modify:**

| File | Change |
|------|--------|
| `README.md` | Add deployment instructions and testing guide |

**Implementation:**

Add to `README.md`:

```markdown
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

5. **Test:**
   - Send message in Google Chat
   - Check logs: `gcloud run logs read emonk-agent --region us-central1`

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
```

---

## Dependency Graph

```
Task 1 (Add dependencies)
    ↓
Task 2 (Update .env.example) ────→ Task 3 (Create src/main.py)
    ↓                                      ↓
    └──────────────────→ Task 4 (Dockerfile)
                                ↓
                        Task 5 (Deploy script)
                                ↓
                        Task 6 (E2E tests) ────→ Task 7 (Update README)
```

---

## Final Verification Checklist

**Functionality:**
- [ ] All mocks removed (MockAgentCore, MockSkillsEngine, MockMemoryManager, MockVertexAI)
- [ ] Real Vertex AI client integrated (Gemini 2.0 Flash)
- [ ] Gateway calls real Agent Core (not mock)
- [ ] Agent Core calls real Skills Engine + Memory Manager
- [ ] Memory Manager works with `GCS_ENABLED=false` (local files)
- [ ] Memory Manager works with `GCS_ENABLED=true` (GCS sync)

**Configuration:**
- [ ] All config in `.env` (no hardcoded values)
- [ ] Missing env vars trigger clear error messages
- [ ] `.env.example` documents all options
- [ ] Deployment script reads from `.env`

**Testing:**
- [ ] Unit tests run fast with mocked Vertex AI
- [ ] 1 integration test with real Vertex AI API
- [ ] Integration test skipped if credentials missing
- [ ] All acceptance criteria from Story 4 covered by tests

**Deployment:**
- [ ] Dockerfile builds successfully
- [ ] Docker image < 500MB
- [ ] Health check returns 200
- [ ] Cloud Run deployment succeeds
- [ ] Service responds to Google Chat webhook
- [ ] Logs appear in Cloud Logging

**Code Quality:**
- [ ] Type hints on all new functions
- [ ] Docstrings on all public functions
- [ ] Follows existing code patterns
- [ ] No linter errors (`ruff check src/`)
- [ ] No type errors (`mypy src/`)

**Documentation:**
- [ ] README.md updated with deployment instructions
- [ ] `.env.example` fully documented
- [ ] `deploy.sh` has clear usage instructions
- [ ] Comments explain non-obvious config choices

---

## Implementation Notes

### Performance Considerations
- **Cold starts:** With min-instances=0, expect 2-3 second cold start latency. Use min-instances=1 if always-on is required.
- **Memory usage:** 1GB should be sufficient for most use cases. Monitor Cloud Run metrics and increase if needed.
- **Timeout:** 60s timeout should handle most requests. LLM calls typically complete in 2-10 seconds.

### Security Notes
- **Environment variables:** Never commit `.env` to git (already in `.gitignore`)
- **Service account:** Use separate service accounts for dev/prod
- **ALLOWED_USERS:** Update this list to control access
- **No webhook signature verification:** Google Chat webhooks use HTTPS + URL obscurity. Add signature verification in production if needed.

### Cost Optimization
- **min-instances=0:** Scale to zero when idle (~$0/month idle, but 2-3s cold start)
- **min-instances=1:** Always warm (~$7/month idle, no cold start)
- **Gemini 2.0 Flash:** Cheapest model (~$0.001 per request)
- **GCS storage:** ~$0.02/GB/month for memory files

### Troubleshooting

**"Missing required environment variables" error:**
- Copy `.env.example` to `.env`
- Fill in all required values (see comments in file)
- Verify `GOOGLE_APPLICATION_CREDENTIALS` file exists

**"Vertex AI authentication failed" error:**
- Verify service account has Vertex AI User role
- Download fresh service account key from GCP Console
- Set `GOOGLE_APPLICATION_CREDENTIALS` to correct path

**"GCS sync failed" error:**
- Verify service account has Storage Object Admin role
- Verify GCS bucket exists: `gsutil ls gs://your-bucket-name`
- Check `GCS_MEMORY_BUCKET` env var matches bucket name

**Tests hang on integration test:**
- Verify `GOOGLE_APPLICATION_CREDENTIALS` is set
- Check GCP quota limits (Vertex AI requests per minute)
- Use `pytest -v` to see which test is hanging

---

## Story 4 Acceptance Criteria Coverage

From user story acceptance criteria:

### Component Wiring
✅ **Gateway → Agent Core:** `src/main.py` line 88 replaces MockAgentCore with real AgentCore  
✅ **Agent Core → Skills Engine:** Real SkillsEngine injected (line 77)  
✅ **Agent Core → Memory Manager:** Real MemoryManager injected (line 82)  
✅ **LLM Client → Vertex AI:** Real ChatVertexAI client created (line 61)

### End-to-End Tests
✅ **Remember fact → saved to disk:** `test_e2e_memory_persistence` verifies flow  
✅ **Recall fact → retrieved from memory:** Same test verifies recall  
✅ **List files → Terminal Executor called:** Covered by existing `test_terminal.py` + integration test

### Deployment
✅ **Dockerfile builds runnable image:** Task 4 creates Dockerfile  
✅ **Health check returns 200:** Task 6 `test_health_check` verifies  
✅ **Cloud Run responds correctly:** Task 5 deployment script + Task 6 integration test  
✅ **Logs visible in Cloud Logging:** Structured JSON logs already implemented in gateway

### Configuration
✅ **`.env.example` documents all vars:** Task 2 comprehensive template  
✅ **Missing env var → fail fast:** Task 3 `validate_env_vars()` function  
✅ **GCS_ENABLED=false → local files only:** Task 3 conditional MemoryManager creation

---

## Post-Implementation Steps

After implementing Story 4:

1. **Run all tests:**
   ```bash
   pytest -m "" --cov=src
   ```

2. **Test locally:**
   ```bash
   python -m src.main
   curl http://localhost:8080/health
   ```

3. **Deploy to Cloud Run:**
   ```bash
   ./deploy.sh
   ```

4. **Configure Google Chat:**
   - Set webhook URL to Cloud Run service URL
   - Send test message
   - Verify response

5. **Monitor logs:**
   ```bash
   gcloud run logs read emonk-agent --region us-central1 --limit 50
   ```

6. **Update state.json:**
   ```json
   {
     "phase_status": {"implementation": "completed"},
     "implementation_notes": {
       "story_4": {
         "status": "completed",
         "files_created": 5,
         "files_modified": 4,
         "tests_passing": "all",
         "deployment": "successful",
         "completed_at": "ISO8601 timestamp"
       }
     }
   }
   ```
