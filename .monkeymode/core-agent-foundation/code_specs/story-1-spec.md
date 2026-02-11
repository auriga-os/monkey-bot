# Code Spec: Story 1 - Gateway Module

**Story:** Story 1 - Gateway Module - HTTP Interface & Google Chat Integration  
**Design Reference:** Phase 1A (Gateway Module), Phase 1B (POST /webhook, GET /health), Phase 1C (Security Design)  
**Author:** MonkeyMode Agent  
**Date:** 2026-02-11

---

## Implementation Summary

- **Files to Create:** 8 files
- **Files to Modify:** 0 files (greenfield)
- **Tests to Add:** 3 test files
- **Estimated Complexity:** M (3-5 days)

---

## Codebase Conventions

This is a **greenfield project**. We'll establish conventions based on Python best practices:

**File/Function Naming:** `snake_case.py` for modules, `snake_case()` for functions  
**Import Order:** Standard library → Third-party → Local (PEP 8)  
**Error Handling:** Custom exception classes, structured try-except blocks  
**Testing Framework:** pytest 8.x with async support  
**Type Checking:** Type hints on all functions, mypy strict mode  
**Async Pattern:** async/await throughout (FastAPI is async-first)  
**Logging:** Structured JSON logging with trace_id for request tracing

---

## Technical Context

### Key Gotchas
1. **PII Filtering is Security-Critical**: User emails must be hashed before any processing. 100% test coverage required.
2. **Google Chat Payload Structure**: Deeply nested JSON - must handle missing fields gracefully
3. **Mock for Sprint 1**: Gateway will use MockAgentCore - real implementation wired in Story 4
4. **ALLOWED_USERS Validation**: Must happen BEFORE any PII filtering to prevent bypass

### Reusable Utilities
None (greenfield project). We'll create utility functions as part of implementation.

### Integration Points
- **Input:** Google Chat webhook (POST /webhook)
- **Output:** Agent Core interface (to be wired in Story 4)
- **Health Check:** Cloud Run expects GET /health to return 200 for healthy

---

## Task Breakdown

### Task 1: Project Setup & Dependencies

**Dependencies:** None (first task)

**Files to Create:**

| File | Purpose |
|------|---------|
| `requirements.txt` | Python dependencies |
| `pyproject.toml` | Project metadata and tool configuration |
| `.env.example` | Environment variable template |
| `README.md` | Gateway module documentation |

**Implementation:**

1. **requirements.txt** - Pin versions for reproducibility:
   ```
   fastapi==0.109.0
   uvicorn[standard]==0.27.0
   pydantic==2.5.0
   pydantic-settings==2.1.0
   python-dotenv==1.0.0
   
   # Testing
   pytest==8.0.0
   pytest-asyncio==0.23.3
   pytest-cov==4.1.0
   httpx==0.26.0  # For TestClient
   ```

2. **pyproject.toml** - Configure tools (mypy, pytest, black, ruff):
   ```toml
   [tool.pytest.ini_options]
   asyncio_mode = "auto"
   testpaths = ["tests"]
   python_files = "test_*.py"
   
   [tool.mypy]
   python_version = "3.11"
   strict = true
   warn_return_any = true
   warn_unused_configs = true
   ```

3. **.env.example** - Document required env vars:
   ```
   ALLOWED_USERS=user1@example.com,user2@example.com
   LOG_LEVEL=INFO
   ```

4. **README.md** - Basic setup instructions:
   - Installation steps
   - How to run locally
   - How to run tests
   - Environment variables

**Test Cases:**
- Verify requirements.txt can be installed without conflicts
- Verify .env.example has all required variables documented

**Critical Notes:**
- Use Python 3.11+ for best async performance
- Pin all dependencies to avoid breaking changes

---

### Task 2: Create Core Interfaces & Data Models

**Dependencies:** Task 1 (Project Setup)

**Files to Create:**

| File | Purpose |
|------|---------|
| `src/gateway/__init__.py` | Package initialization |
| `src/gateway/interfaces.py` | Agent Core interface definition |
| `src/gateway/models.py` | Pydantic models for request/response |

**Function Signatures:**

```python
# src/gateway/interfaces.py
from abc import ABC, abstractmethod

class AgentCoreInterface(ABC):
    """Contract for Agent Core that Gateway will call."""
    
    @abstractmethod
    async def process_message(
        self, 
        user_id: str, 
        content: str, 
        trace_id: str
    ) -> str:
        """
        Process a user message and return response text.
        
        Args:
            user_id: Hashed user identifier (not email)
            content: Message text (PII already filtered)
            trace_id: Request trace ID for debugging
            
        Returns:
            Response text to send back to user
            
        Raises:
            AgentError: If processing fails
        """
        pass


class AgentError(Exception):
    """Raised when Agent Core processing fails."""
    pass
```

```python
# src/gateway/models.py
from pydantic import BaseModel, Field
from typing import Optional

class GoogleChatSender(BaseModel):
    """Google Chat message sender."""
    email: str
    display_name: Optional[str] = None


class GoogleChatMessage(BaseModel):
    """Google Chat message structure."""
    sender: GoogleChatSender
    text: str


class GoogleChatWebhook(BaseModel):
    """Google Chat webhook payload."""
    message: GoogleChatMessage


class GoogleChatResponse(BaseModel):
    """Google Chat response (Cards V2 format)."""
    text: str


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="'healthy' or 'unhealthy'")
    timestamp: str
    version: str = "1.0.0"
    checks: dict[str, str] = Field(default_factory=dict)
```

**Pattern Reference:**
Follow FastAPI + Pydantic best practices:
- Use Pydantic models for request/response validation
- Use ABC (Abstract Base Classes) for interface contracts
- Type hints on all fields and methods

**Implementation Algorithm:**
1. Define `AgentCoreInterface` as ABC with `process_message()` method
2. Define `AgentError` exception class
3. Create Pydantic models matching Google Chat webhook structure (from Phase 1B design)
4. Add docstrings to all classes and methods

**Test Cases:**
- GoogleChatWebhook validates correct payload → Success
- GoogleChatWebhook rejects missing `message.sender.email` → ValidationError
- GoogleChatWebhook rejects missing `message.text` → ValidationError
- HealthCheckResponse validates correct structure → Success

**Critical Notes:**
- Pydantic validation happens automatically on FastAPI endpoints
- Interface defines the contract - Story 2 will implement AgentCore, Story 4 will wire it

---

### Task 3: Implement PII Filter

**Dependencies:** Task 2 (Interfaces & Models)

**Files to Create:**

| File | Purpose |
|------|---------|
| `src/gateway/pii_filter.py` | Strip Google Chat metadata and hash emails |
| `tests/gateway/test_pii_filter.py` | Unit tests for PII filtering |

**Function Signatures:**

```python
# src/gateway/pii_filter.py
from typing import TypedDict
import hashlib

class FilteredMessage(TypedDict):
    """Filtered message with PII removed."""
    user_id: str  # Hashed email (16 chars)
    content: str  # Message text only


def filter_google_chat_pii(webhook_payload: dict) -> FilteredMessage:
    """
    Extract only safe fields from Google Chat webhook.
    
    Strips all Google Chat metadata (space ID, thread ID, sender name, etc.)
    and hashes the email to create a stable user_id.
    
    Args:
        webhook_payload: Raw Google Chat webhook payload
        
    Returns:
        FilteredMessage with only user_id (hashed) and content
        
    Raises:
        KeyError: If required fields are missing
    """
    sender_email = webhook_payload["message"]["sender"]["email"]
    message_text = webhook_payload["message"]["text"]
    
    # Hash email to create stable user_id (no PII)
    user_id = hashlib.sha256(sender_email.encode()).hexdigest()[:16]
    
    return FilteredMessage(user_id=user_id, content=message_text)
```

**Pattern Reference:**
This establishes the PII filtering pattern used throughout the application.

**Implementation Algorithm:**
1. Extract `message.sender.email` and `message.text` from nested payload
2. Use SHA-256 to hash email (stable, deterministic)
3. Take first 16 chars of hash for user_id (sufficient uniqueness for small user base)
4. Return only `user_id` and `content` - NO other fields

**Test Cases** (follow pattern in test file below):
- Valid webhook with email "user@example.com" → Returns hashed user_id + content
- Valid webhook with different email → Returns different user_id (deterministic hashing)
- Same email in two requests → Returns same user_id (stable hashing)
- Webhook missing `message.sender.email` → Raises KeyError
- Webhook missing `message.text` → Raises KeyError
- Webhook with extra metadata (space, thread, etc.) → Stripped from output

**Complete Test File Example:**

```python
# tests/gateway/test_pii_filter.py
import pytest
from src.gateway.pii_filter import filter_google_chat_pii


def test_filter_pii_success():
    """Test successful PII filtering."""
    webhook = {
        "message": {
            "sender": {
                "email": "user@example.com",
                "displayName": "Test User",  # ← Should be stripped
            },
            "text": "Remember that I prefer Python",
            "space": {"name": "spaces/xxx"},  # ← Should be stripped
            "thread": {"name": "spaces/xxx/threads/yyy"},  # ← Should be stripped
        }
    }
    
    result = filter_google_chat_pii(webhook)
    
    assert "user_id" in result
    assert "content" in result
    assert result["content"] == "Remember that I prefer Python"
    assert len(result["user_id"]) == 16  # First 16 chars of SHA-256
    assert "@" not in result["user_id"]  # No PII
    
    # Verify no Google Chat metadata leaked
    assert "space" not in str(result)
    assert "thread" not in str(result)
    assert "displayName" not in str(result)


def test_filter_pii_stable_hashing():
    """Test that same email produces same user_id."""
    webhook1 = {
        "message": {
            "sender": {"email": "user@example.com"},
            "text": "Message 1"
        }
    }
    webhook2 = {
        "message": {
            "sender": {"email": "user@example.com"},
            "text": "Message 2"
        }
    }
    
    result1 = filter_google_chat_pii(webhook1)
    result2 = filter_google_chat_pii(webhook2)
    
    assert result1["user_id"] == result2["user_id"]  # Same user_id for same email


def test_filter_pii_different_emails():
    """Test that different emails produce different user_ids."""
    webhook1 = {
        "message": {
            "sender": {"email": "user1@example.com"},
            "text": "Message"
        }
    }
    webhook2 = {
        "message": {
            "sender": {"email": "user2@example.com"},
            "text": "Message"
        }
    }
    
    result1 = filter_google_chat_pii(webhook1)
    result2 = filter_google_chat_pii(webhook2)
    
    assert result1["user_id"] != result2["user_id"]  # Different user_ids


def test_filter_pii_missing_email():
    """Test error handling when email is missing."""
    webhook = {
        "message": {
            "sender": {},  # ← Missing email
            "text": "Message"
        }
    }
    
    with pytest.raises(KeyError):
        filter_google_chat_pii(webhook)


def test_filter_pii_missing_text():
    """Test error handling when text is missing."""
    webhook = {
        "message": {
            "sender": {"email": "user@example.com"},
            # ← Missing text
        }
    }
    
    with pytest.raises(KeyError):
        filter_google_chat_pii(webhook)
```

**Critical Notes:**
- **Security-critical code**: 100% test coverage required
- SHA-256 is one-way (can't reverse to get email)
- First 16 chars provide sufficient uniqueness for small user base (~1M users)
- If webhook structure changes, tests will catch it

---

### Task 4: Create Mock Agent Core

**Dependencies:** Task 2 (Interfaces)

**Files to Create:**

| File | Purpose |
|------|---------|
| `src/gateway/mocks.py` | Mock Agent Core for testing |

**Implementation:**

```python
# src/gateway/mocks.py
from src.gateway.interfaces import AgentCoreInterface


class MockAgentCore(AgentCoreInterface):
    """
    Mock Agent Core for Gateway testing.
    
    Returns canned responses for Sprint 1 development.
    Real Agent Core will be wired in Story 4 (Integration).
    """
    
    async def process_message(
        self, 
        user_id: str, 
        content: str, 
        trace_id: str
    ) -> str:
        """Return simple echo response for testing."""
        return f"Echo: {content} (trace: {trace_id})"
```

**Pattern:** Simple mock implementation for parallel development

**Test Cases:**
- MockAgentCore.process_message() returns echo response → Success
- MockAgentCore follows AgentCoreInterface contract → Type checks pass

---

### Task 5: Implement FastAPI Server with Webhook & Health Endpoints

**Dependencies:** Tasks 2, 3, 4 (Interfaces, PII Filter, Mock)

**Files to Create:**

| File | Purpose |
|------|---------|
| `src/gateway/server.py` | FastAPI application with endpoints |
| `tests/gateway/test_server.py` | Integration tests for endpoints |

**Function Signatures:**

```python
# src/gateway/server.py
from fastapi import FastAPI, Request, HTTPException, status
from datetime import datetime
import os
import uuid
from src.gateway.models import (
    GoogleChatWebhook, 
    GoogleChatResponse, 
    HealthCheckResponse
)
from src.gateway.pii_filter import filter_google_chat_pii
from src.gateway.interfaces import AgentCoreInterface
from src.gateway.mocks import MockAgentCore

app = FastAPI(title="Emonk Gateway", version="1.0.0")

# For Sprint 1: Use mock (Story 4 will wire real Agent Core)
agent_core: AgentCoreInterface = MockAgentCore()


@app.post("/webhook", response_model=GoogleChatResponse)
async def webhook(payload: GoogleChatWebhook) -> GoogleChatResponse:
    """
    Handle Google Chat webhook.
    
    Flow:
    1. Validate sender email against allowlist
    2. Filter PII (hash email, strip metadata)
    3. Call Agent Core
    4. Format response for Google Chat
    """
    pass


@app.get("/health", response_model=HealthCheckResponse)
async def health() -> HealthCheckResponse:
    """
    Health check endpoint for Cloud Run.
    
    Returns:
        200 OK if all components healthy
        503 Service Unavailable if any component down
    """
    pass
```

**Pattern Reference:**
Follow FastAPI async patterns:
- Use async def for all endpoints
- Pydantic models for automatic validation
- HTTPException for error responses
- Dependency injection for agent_core (enables testing)

**Implementation Algorithm:**

**POST /webhook:**
1. Pydantic validates payload automatically (GoogleChatWebhook model)
2. Extract sender email from `payload.message.sender.email`
3. Get ALLOWED_USERS from env var (comma-separated)
4. If email NOT in allowlist → Raise HTTPException(401, "Unauthorized user")
5. Call `filter_google_chat_pii()` to get `user_id` and `content`
6. Generate trace_id (UUID v4)
7. Call `agent_core.process_message(user_id, content, trace_id)`
8. Return GoogleChatResponse with response text
9. If any error → Catch and return 500 with error details

**GET /health:**
1. Check if agent_core is available (for Sprint 1, always "ok" with mock)
2. Get current timestamp (ISO8601 format)
3. Return HealthCheckResponse with status and checks
4. For Sprint 1: Always return 200 OK (Story 4 will add real health checks)

**Test Cases:**

**POST /webhook tests:**
- Valid webhook from allowed user → Returns 200 with echo response
- Valid webhook from unauthorized user → Returns 401 Unauthorized
- Malformed webhook payload → Returns 422 Unprocessable Entity
- Missing ALLOWED_USERS env var → Returns 500 Internal Server Error
- Agent Core raises AgentError → Returns 500 with error message

**GET /health tests:**
- Health check request → Returns 200 with status "healthy"
- Response includes version "1.0.0"
- Response includes timestamp in ISO8601 format
- Response includes checks dict with "agent_core": "ok"

**Critical Notes:**
- Allowlist validation BEFORE PII filtering (security defense in depth)
- trace_id enables request tracing in logs (critical for debugging)
- MockAgentCore allows Gateway to work independently in Sprint 1

---

### Task 6: Add Structured Logging

**Dependencies:** Task 5 (FastAPI Server)

**Files to Modify:**

| File | Change |
|------|--------|
| `src/gateway/server.py` | Add logging configuration and request logging |

**Implementation:**

Add logging configuration at top of `server.py`:

```python
import logging
import json
from datetime import datetime

# Configure structured JSON logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(message)s'  # We'll format as JSON ourselves
)

logger = logging.getLogger(__name__)


def log_structured(level: str, message: str, **extra):
    """Log structured JSON for Cloud Logging."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "severity": level,
        "message": message,
        "component": "gateway",
        **extra
    }
    logger.log(getattr(logging, level), json.dumps(log_entry))
```

Add logging to webhook endpoint:

```python
@app.post("/webhook", response_model=GoogleChatResponse)
async def webhook(payload: GoogleChatWebhook) -> GoogleChatResponse:
    trace_id = str(uuid.uuid4())
    
    log_structured("INFO", "Webhook received", trace_id=trace_id, sender=payload.message.sender.email)
    
    # ... existing logic ...
    
    log_structured("INFO", "Webhook processed", trace_id=trace_id, response_length=len(response_text))
    
    return GoogleChatResponse(text=response_text)
```

**Test Cases:**
- Webhook request generates INFO log with trace_id
- Unauthorized request generates WARNING log
- Agent Core error generates ERROR log
- All logs are valid JSON

---

### Task 7: Add Response Truncation for Google Chat

**Dependencies:** Task 5 (FastAPI Server)

**Files to Modify:**

| File | Change |
|------|--------|
| `src/gateway/server.py` | Add truncation logic for responses > 4000 chars |

**Implementation:**

Add helper function:

```python
def truncate_response(text: str, max_length: int = 4000) -> str:
    """
    Truncate response text for Google Chat.
    
    Google Chat has a 4096 character limit for Cards V2.
    We truncate at 4000 to leave room for formatting.
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length] + "\n\n... (response truncated)"
```

Update webhook endpoint:

```python
response_text = await agent_core.process_message(user_id, content, trace_id)
response_text = truncate_response(response_text)  # ← Add truncation
return GoogleChatResponse(text=response_text)
```

**Test Cases:**
- Response < 4000 chars → Not truncated
- Response = 4000 chars → Not truncated
- Response > 4000 chars → Truncated with "... (response truncated)" suffix

---

### Task 8: Create Main Entry Point & Uvicorn Runner

**Dependencies:** Task 5 (FastAPI Server)

**Files to Create:**

| File | Purpose |
|------|---------|
| `src/__init__.py` | Package initialization |
| `src/gateway/main.py` | Entry point for running server locally |

**Implementation:**

```python
# src/gateway/main.py
import os
from dotenv import load_dotenv

# Load .env file for local development
load_dotenv()

# Import app after loading env vars
from src.gateway.server import app

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8080"))
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )
```

**How to Run:**
```bash
# Local development
python -m src.gateway.main

# Or with uvicorn directly
uvicorn src.gateway.server:app --reload --port 8080
```

**Test Cases:**
- Server starts without errors
- Server responds to GET /health → 200 OK
- Server accepts POST /webhook with valid payload → 200 OK

---

## Dependency Graph

```
Task 1 (Project Setup)
    │
    └─→ Task 2 (Interfaces & Models)
            │
            ├─→ Task 3 (PII Filter)
            │       │
            │       └─→ Task 5 (FastAPI Server)
            │               │
            │               ├─→ Task 6 (Logging)
            │               ├─→ Task 7 (Truncation)
            │               └─→ Task 8 (Entry Point)
            │
            └─→ Task 4 (Mock Agent Core)
                    │
                    └─→ Task 5 (FastAPI Server)
```

---

## Reference Code Examples

### FastAPI Endpoint Pattern

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class RequestModel(BaseModel):
    field: str

class ResponseModel(BaseModel):
    result: str

@app.post("/endpoint", response_model=ResponseModel)
async def endpoint(request: RequestModel) -> ResponseModel:
    """
    Endpoint docstring.
    
    Args:
        request: Validated request model
        
    Returns:
        Response model
        
    Raises:
        HTTPException: On error
    """
    try:
        result = await some_async_function(request.field)
        return ResponseModel(result=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Pytest Async Test Pattern

```python
import pytest
from httpx import AsyncClient
from src.gateway.server import app


@pytest.mark.asyncio
async def test_endpoint_success():
    """Test successful endpoint call."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/endpoint", json={"field": "value"})
    
    assert response.status_code == 200
    assert response.json()["result"] == "expected"


@pytest.mark.asyncio
async def test_endpoint_error():
    """Test endpoint error handling."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/endpoint", json={"field": "invalid"})
    
    assert response.status_code == 400
    assert "error" in response.json()["detail"].lower()
```

---

## Implementation Notes

### Security Considerations
- **PII Filtering**: Email hashing is one-way (SHA-256) - cannot be reversed
- **Allowlist Enforcement**: Validation happens before any processing
- **No Metadata Leakage**: Google Chat space/thread IDs never sent to LLM
- **Error Messages**: Don't leak sensitive info (no email addresses in error responses)

### Performance Considerations
- **FastAPI Async**: All endpoints use async/await for non-blocking I/O
- **Response Truncation**: Prevents excessive data transfer for large responses
- **Minimal Dependencies**: Only essential libraries to keep container size small

### Deployment Requirements
- **Environment Variables**: ALLOWED_USERS must be set before deployment
- **Health Check**: Cloud Run will ping GET /health every 30 seconds
- **Logging**: Structured JSON logs for Cloud Logging integration
- **Port**: Defaults to 8080 (Cloud Run standard)

### Post-Deployment Verification
1. Send test webhook to deployed URL → Verify 200 response with echo
2. Send webhook from unauthorized user → Verify 401 response
3. Check Cloud Logging → Verify structured JSON logs appear
4. Check GET /health → Verify returns 200 OK

---

## Final Verification

### Functionality
- [ ] POST /webhook accepts valid Google Chat webhook → Returns 200 with response
- [ ] POST /webhook rejects unauthorized user → Returns 401
- [ ] POST /webhook handles malformed payload → Returns 422
- [ ] GET /health returns 200 OK with status details
- [ ] PII filtering strips all Google Chat metadata
- [ ] User emails are hashed (not stored in plain text)

### Code Quality
- [ ] All functions have type hints
- [ ] All functions have docstrings
- [ ] Follows PEP 8 style guide
- [ ] No hardcoded secrets (use env vars)
- [ ] Structured logging throughout

### Testing
- [ ] All unit tests pass (pytest)
- [ ] Test coverage ≥ 80% overall
- [ ] Test coverage = 100% for PII filter (security-critical)
- [ ] Integration tests pass (FastAPI TestClient)
- [ ] Can run locally with .env file

### Build
- [ ] requirements.txt installs without errors
- [ ] mypy type checking passes (strict mode)
- [ ] Server starts without errors
- [ ] Server responds to health check

---

## Out of Scope for Story 1

❌ Agent Core implementation (Story 2)  
❌ Real LLM integration (Story 2)  
❌ Skills Engine (Story 3)  
❌ Memory Manager (Story 3)  
❌ Terminal Executor (Story 3)  
❌ Deployment to Cloud Run (Story 4)  
❌ Integration with real Agent Core (Story 4)

---

## Success Criteria

✅ Gateway accepts Google Chat webhooks and returns responses  
✅ PII filtering removes all Google Chat metadata before processing  
✅ Allowlist validation blocks unauthorized users  
✅ MockAgentCore enables independent testing  
✅ Health check endpoint works for Cloud Run  
✅ All tests pass with ≥80% coverage  
✅ Can run locally with uvicorn for development

---

**Ready for Implementation!** 🚀

This spec provides everything needed to implement Story 1 independently in Sprint 1. Story 4 will wire the real Agent Core in Sprint 2.
