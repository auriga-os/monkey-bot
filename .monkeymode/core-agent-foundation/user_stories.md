# User Stories: Emonk Core Agent Foundation

**Feature**: Core Agent Foundation  
**Date**: 2026-02-11  
**Team Size**: 3 developers  
**Sprint Strategy**: 3 parallel stories (Sprint 1) + 1 integration story (Sprint 2)

---

## Parallelization Plan

### Sprint 1: Core Components (3 developers, ZERO dependencies)
- **Story 1**: Gateway Module (Dev 1)
- **Story 2**: Agent Core + LLM Client (Dev 2)
- **Story 3**: Skills Engine + Terminal Executor + Memory Manager (Dev 3)

All stories start Day 1. No waiting. ✓

### Sprint 2: Integration
- **Story 4**: Wire components together + end-to-end tests + Cloud Run deployment

---

## Story 1: Gateway Module - HTTP Interface & Google Chat Integration

**Repository**: emonk  
**Type**: Feature  
**Priority**: High  
**Size**: M (3-5 days)  
**Dependencies**: NONE (Sprint 1 - fully parallel)

### Description
As a Google Chat user,  
I want to send messages to Emonk via webhook,  
So that the agent can receive my requests and respond in Google Chat.

### Technical Context
- **Affected modules**: `src/gateway/` (new)
- **Design reference**: 
  - Phase 1A: "Gateway Module" section
  - Phase 1B: "POST /webhook", "GET /health"
  - Phase 1C: "Security Design" (PII filtering)
- **Key files to create**:
  - `src/gateway/__init__.py`
  - `src/gateway/server.py` (FastAPI application)
  - `src/gateway/google_chat.py` (Google Chat API integration)
  - `src/gateway/pii_filter.py` (Strip Google Chat metadata)
  - `src/gateway/interfaces.py` (contracts for Agent Core)
  - `src/gateway/mocks.py` (MockAgentCore for testing)
  - `tests/gateway/test_server.py`
  - `tests/gateway/test_pii_filter.py`
  - `tests/gateway/test_google_chat.py`
- **Patterns to follow**: FastAPI best practices, async/await
- **Dependencies**: NONE (no dependencies on other Sprint 1 stories)
  - Note: Can depend on existing libraries (FastAPI, google-auth, etc.)

### Integration Contracts

**Interfaces Defined by This Story:**

```python
# src/gateway/interfaces.py
from abc import ABC, abstractmethod
from typing import Dict

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
```

**Interfaces Used by This Story:**
- None (Gateway is the entry point)

**Integration Timeline:**
- Sprint 1: Gateway fully functional with MockAgentCore, all tests pass
- Sprint 2: Integration story wires real AgentCore implementation

### Acceptance Criteria

#### Webhook Handling
- [ ] **Given** valid Google Chat webhook POST to `/webhook`, **When** request received, **Then** return 200 with Google Chat Cards V2 format
- [ ] **Given** malformed webhook payload, **When** request received, **Then** return 422 with error details
- [ ] **Given** user email not in `ALLOWED_USERS`, **When** webhook received, **Then** return 401 Unauthorized

#### PII Filtering
- [ ] **Given** webhook with user email "user@example.com", **When** processing, **Then** hash to stable user_id (sha256)
- [ ] **Given** webhook with space ID and thread ID, **When** filtering, **Then** strip all Google Chat metadata before passing to Agent Core
- [ ] **Given** webhook with only message content, **When** passing to Agent Core, **Then** include only user_id, content, trace_id

#### Health Check
- [ ] **Given** GET request to `/health`, **When** all components healthy, **Then** return 200 with status details
- [ ] **Given** GET request to `/health`, **When** Agent Core unavailable, **Then** return 503 with component status

#### Google Chat Response Formatting
- [ ] **Given** response text from Agent Core, **When** formatting for Google Chat, **Then** return Cards V2 format with text
- [ ] **Given** response text > 4000 chars, **When** formatting, **Then** truncate with "..." indicator

#### Testing & Quality
- [ ] Interface defined in `interfaces.py` with complete docstrings and type hints
- [ ] MockAgentCore provided in `mocks.py` (returns canned responses)
- [ ] Unit tests cover: valid webhook, invalid webhook, PII filtering, allowlist validation, health check
- [ ] All tests pass independently (no external dependencies)
- [ ] 100% test coverage for security-critical paths (PII filter, allowlist)

### Implementation Details

#### FastAPI Server Structure
```python
# src/gateway/server.py
from fastapi import FastAPI, Request, HTTPException
from .pii_filter import filter_google_chat_pii
from .interfaces import AgentCoreInterface
from .mocks import MockAgentCore
import os
import uuid

app = FastAPI()

# For Sprint 1: Use mock
agent_core: AgentCoreInterface = MockAgentCore()

@app.post("/webhook")
async def webhook(request: Request):
    """Handle Google Chat webhook."""
    payload = await request.json()
    
    # Validate sender email
    sender_email = payload.get("message", {}).get("sender", {}).get("email")
    allowed_users = os.getenv("ALLOWED_USERS", "").split(",")
    if sender_email not in allowed_users:
        raise HTTPException(status_code=401, detail="Unauthorized user")
    
    # Filter PII
    filtered = filter_google_chat_pii(payload)
    trace_id = str(uuid.uuid4())
    
    # Call Agent Core (mock for Sprint 1)
    response_text = await agent_core.process_message(
        user_id=filtered["user_id"],
        content=filtered["content"],
        trace_id=trace_id
    )
    
    # Format for Google Chat
    return {"text": response_text}

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": "ISO8601",
        "version": "1.0.0",
        "checks": {
            "agent_core": "ok"  # Mock always returns ok
        }
    }
```

#### PII Filter Implementation
```python
# src/gateway/pii_filter.py
import hashlib
from typing import Dict

def filter_google_chat_pii(webhook_payload: dict) -> Dict[str, str]:
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

#### Mock Agent Core
```python
# src/gateway/mocks.py
from .interfaces import AgentCoreInterface

class MockAgentCore(AgentCoreInterface):
    """Mock Agent Core for Gateway testing."""
    
    async def process_message(self, user_id: str, content: str, trace_id: str) -> str:
        # Simple echo response for testing
        return f"Echo: {content} (trace: {trace_id})"
```

### Out of Scope
- Agent Core implementation (Story 2)
- Skills execution (Story 3)
- Real LLM calls (Story 2)
- GCS sync (Story 3)
- Deployment to Cloud Run (Story 4)

### Notes for Developer
- **Security**: PII filter is critical - test thoroughly! 100% coverage required.
- **Allowlist**: Use `ALLOWED_USERS` env var (comma-separated emails)
- **Testing**: Run FastAPI with MockAgentCore - should work end-to-end
- **Google Chat format**: Response must be `{"text": "..."}` for Cards V2
- **Interface clarity**: Agent Core dev (Story 2) depends on your interface definition

---

## Story 2: Agent Core + LLM Client - Orchestration & Intelligence

**Repository**: emonk  
**Type**: Feature  
**Priority**: High  
**Size**: M (3-5 days)  
**Dependencies**: NONE (Sprint 1 - fully parallel)

### Description
As an agent orchestrator,  
I want to route user messages to skills via LLM reasoning,  
So that the agent can intelligently respond to user requests.

### Technical Context
- **Affected modules**: `src/core/` (new)
- **Design reference**:
  - Phase 1A: "Agent Core Module" section
  - Phase 1B: "Agent Core → LLM Client" contract
  - Phase 1C: "Performance & Scalability" (Flash by default)
- **Key files to create**:
  - `src/core/__init__.py`
  - `src/core/agent.py` (LangGraph agent definition)
  - `src/core/llm_client.py` (Vertex AI client wrapper)
  - `src/core/interfaces.py` (ALL shared interfaces - Story 2 owns this file)
  - `src/core/mocks.py` (MockSkillsEngine, MockMemoryManager, MockVertexAI)
  - `tests/core/test_agent.py`
  - `tests/core/test_llm_client.py`
- **Patterns to follow**: LangGraph patterns, async/await, dependency injection
- **Dependencies**: NONE (no dependencies on other Sprint 1 stories)
  - Note: Can depend on LangGraph, LangChain, google-cloud-aiplatform libraries
- **FILE OWNERSHIP**: Story 2 owns `src/core/interfaces.py` - defines ALL shared interfaces for the entire project

### Integration Contracts

**Interfaces Defined by This Story:**

```python
# src/core/interfaces.py
# Story 2 owns ALL shared interfaces for the entire project
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class Message:
    """Conversation message."""
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: str
    trace_id: str

@dataclass
class SkillResult:
    """Result from skill execution."""
    success: bool
    output: str
    error: Optional[str] = None

@dataclass
class ExecutionResult:
    """Result from terminal command execution."""
    stdout: str
    stderr: str
    exit_code: int

class SkillsEngineInterface(ABC):
    """Contract for Skills Engine."""
    
    @abstractmethod
    async def execute_skill(
        self, 
        skill_name: str, 
        args: Dict[str, Any]
    ) -> SkillResult:
        """
        Execute a skill by name with arguments.
        
        Args:
            skill_name: Skill identifier from SKILL.md
            args: Skill arguments from LLM tool call
            
        Returns:
            SkillResult with success status and output
            
        Raises:
            SkillError: If skill not found or execution fails
        """
        pass
    
    @abstractmethod
    def list_skills(self) -> List[str]:
        """Return list of available skill names."""
        pass

class MemoryManagerInterface(ABC):
    """Contract for Memory Manager."""
    
    @abstractmethod
    async def read_conversation_history(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> List[Message]:
        """
        Read recent conversation history.
        
        Args:
            user_id: Hashed user identifier
            limit: Max messages to return (default 10)
            
        Returns:
            List of recent messages (oldest first)
        """
        pass
    
    @abstractmethod
    async def write_conversation(
        self,
        user_id: str,
        role: str,
        content: str,
        trace_id: str
    ):
        """
        Write a conversation message.
        
        Args:
            user_id: Hashed user identifier
            role: "user" or "assistant"
            content: Message content
            trace_id: Request trace ID
        """
        pass
    
    @abstractmethod
    async def read_fact(self, user_id: str, key: str) -> Optional[str]:
        """Read a fact from knowledge base."""
        pass
    
    @abstractmethod
    async def write_fact(self, user_id: str, key: str, value: str):
        """Write a fact to knowledge base."""
        pass

class AgentCoreInterface(ABC):
    """Contract that Gateway will call."""
    
    @abstractmethod
    async def process_message(
        self, 
        user_id: str, 
        content: str, 
        trace_id: str
    ) -> str:
        """Process user message and return response."""
        pass
```

**Interfaces Used by This Story:**
```python
# Uses mocks for parallel development
from .interfaces import SkillsEngineInterface, MemoryManagerInterface
from .mocks import MockSkillsEngine, MockMemoryManager, MockVertexAI

# Tests use mocks instead of real implementations
```

**Integration Timeline:**
- Sprint 1: Agent Core fully functional with mocks, all tests pass
- Sprint 2: Integration story wires real Skills Engine and Memory Manager

### Acceptance Criteria

#### Agent Orchestration
- [ ] **Given** user message, **When** processing, **Then** load last 10 conversation messages as context
- [ ] **Given** user message + context, **When** calling LLM, **Then** get skill tool call or direct response
- [ ] **Given** LLM returns tool call, **When** processing, **Then** execute skill via SkillsEngine mock
- [ ] **Given** skill result, **When** processing, **Then** format response and save to conversation history

#### LLM Client Integration
- [ ] **Given** Gemini Flash model, **When** calling LLM, **Then** receive response within 5 seconds
- [ ] **Given** LLM API failure, **When** calling, **Then** retry 3x with exponential backoff
- [ ] **Given** LLM rate limit (429), **When** calling, **Then** backoff and return error after 3 retries
- [ ] **Given** response > 200 tokens, **When** generating, **Then** enable streaming (if supported by LangChain)

#### Conversation Context
- [ ] **Given** 20 messages in history, **When** building context, **Then** only send last 10 to LLM
- [ ] **Given** new user (no history), **When** processing, **Then** handle gracefully with empty context
- [ ] **Given** system prompt exists in memory, **When** building context, **Then** prepend to messages

#### Error Handling
- [ ] **Given** SkillsEngine throws error, **When** processing, **Then** return friendly error to user
- [ ] **Given** MemoryManager throws error, **When** processing, **Then** continue without history (log error)
- [ ] **Given** LLM timeout (60s), **When** processing, **Then** return timeout error to user

#### Testing & Quality
- [ ] AgentCoreInterface implemented with `process_message()` method
- [ ] Mocks provided: MockSkillsEngine, MockMemoryManager, MockVertexAI
- [ ] Unit tests cover: message routing, skill calling, context building, error handling
- [ ] All tests pass independently (using mocks)
- [ ] Type hints on all functions, docstrings on all public methods

### Implementation Details

#### Agent Core Implementation
```python
# src/core/agent.py
from typing import List
from .interfaces import (
    AgentCoreInterface, 
    SkillsEngineInterface, 
    MemoryManagerInterface,
    Message
)
from .llm_client import LLMClient
from .mocks import MockSkillsEngine, MockMemoryManager
import logging

logger = logging.getLogger(__name__)

class AgentCore(AgentCoreInterface):
    """LangGraph-based agent orchestration."""
    
    def __init__(
        self,
        llm_client: LLMClient,
        skills_engine: SkillsEngineInterface,
        memory_manager: MemoryManagerInterface
    ):
        self.llm = llm_client
        self.skills = skills_engine
        self.memory = memory_manager
    
    async def process_message(
        self, 
        user_id: str, 
        content: str, 
        trace_id: str
    ) -> str:
        """Process user message and return response."""
        logger.info(f"Processing message for user {user_id}", extra={
            "trace_id": trace_id,
            "component": "agent_core"
        })
        
        # Load conversation context
        history = await self.memory.read_conversation_history(user_id, limit=10)
        
        # Build messages for LLM (history + new user message)
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in history
        ]
        messages.append({"role": "user", "content": content})
        
        # Call LLM
        response = await self.llm.chat(
            messages=messages,
            model="gemini-2.0-flash",
            stream=False  # Streaming handled by LLM client if needed
        )
        
        # Save user message
        await self.memory.write_conversation(user_id, "user", content, trace_id)
        
        # Save assistant response
        await self.memory.write_conversation(user_id, "assistant", response, trace_id)
        
        return response

# For Sprint 1 testing: Use mocks
def create_agent_with_mocks() -> AgentCore:
    """Create agent with mock dependencies for testing."""
    from .mocks import MockVertexAI
    llm_client = LLMClient(vertex_client=MockVertexAI())
    skills_engine = MockSkillsEngine()
    memory_manager = MockMemoryManager()
    return AgentCore(llm_client, skills_engine, memory_manager)
```

#### LLM Client Implementation
```python
# src/core/llm_client.py
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class LLMClient:
    """Vertex AI Gemini client wrapper."""
    
    def __init__(self, vertex_client):
        """
        Args:
            vertex_client: MockVertexAI for Sprint 1 testing
                          (Real Vertex AI client added in Sprint 2/Story 4)
        """
        self.client = vertex_client
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "gemini-2.0-flash",
        stream: bool = False
    ) -> str:
        """
        Call LLM with conversation context.
        
        Args:
            messages: Conversation history [{"role": "user", "content": "..."}]
            model: "gemini-2.0-flash" or "gemini-2.0-pro"
            stream: Enable streaming for long responses
            
        Returns:
            LLM response text
            
        Raises:
            LLMError: If API call fails after retries
        """
        logger.info(f"Calling LLM: {model}", extra={
            "component": "llm_client",
            "model": model,
            "message_count": len(messages)
        })
        
        # For Sprint 1: Use MockVertexAI (passed via constructor)
        # Sprint 2: Story 4 wires real Vertex AI client with retry logic
        response = await self.client.generate(messages, model)
        
        return response
```

#### Mocks for Testing
```python
# src/core/mocks.py
from .interfaces import SkillsEngineInterface, MemoryManagerInterface, SkillResult, Message
from typing import List, Dict, Any, Optional

class MockSkillsEngine(SkillsEngineInterface):
    """Mock Skills Engine for Agent Core testing."""
    
    async def execute_skill(self, skill_name: str, args: Dict[str, Any]) -> SkillResult:
        # Simple mock - returns success with canned output
        return SkillResult(
            success=True,
            output=f"Mock skill '{skill_name}' executed with args: {args}"
        )
    
    def list_skills(self) -> List[str]:
        return ["memory-remember", "memory-recall", "file-ops"]

class MockMemoryManager(MemoryManagerInterface):
    """Mock Memory Manager for Agent Core testing."""
    
    def __init__(self):
        self.conversation_history: List[Message] = []
        self.facts: Dict[str, str] = {}
    
    async def read_conversation_history(self, user_id: str, limit: int = 10) -> List[Message]:
        return self.conversation_history[-limit:]
    
    async def write_conversation(self, user_id: str, role: str, content: str, trace_id: str):
        self.conversation_history.append(Message(
            role=role,
            content=content,
            timestamp="2026-02-11T20:00:00Z",
            trace_id=trace_id
        ))
    
    async def read_fact(self, user_id: str, key: str) -> Optional[str]:
        return self.facts.get(key)
    
    async def write_fact(self, user_id: str, key: str, value: str):
        self.facts[key] = value

class MockVertexAI:
    """Mock Vertex AI client for LLM testing."""
    
    async def generate(self, messages: List[Dict], model: str) -> str:
        # Simple echo response for testing
        last_message = messages[-1]["content"]
        return f"Mock LLM response to: {last_message}"
```

### Out of Scope
- Real Vertex AI integration (use MockVertexAI for Sprint 1, Story 4 adds real client)
- Real Skills Engine (use MockSkillsEngine for Sprint 1, Story 4 wires real implementation)
- Real Memory Manager (use MockMemoryManager for Sprint 1, Story 4 wires real implementation)
- LangGraph advanced features (streaming, multi-step reasoning - defer to future phases)
- Deployment to Cloud Run (Story 4 handles deployment)

### Notes for Developer
- **Interface clarity**: Story 3 depends on your interface definitions in `src/core/interfaces.py`
- **LangGraph**: Start simple - single-step agent (user message → LLM → response)
- **Testing**: Use mocks for all dependencies - agent should work end-to-end with mocks
- **Mock-only for Sprint 1**: Do NOT import real Vertex AI - use MockVertexAI only
- **Retry logic**: Document retry logic in comments, implement in Story 4 with real client
- **Context window**: Hard limit of 10 messages (configurable via constant)
- **File ownership**: You own `src/core/interfaces.py` - define ALL shared interfaces here

---

## Story 3: Skills Engine + Terminal Executor + Memory Manager

**Repository**: emonk  
**Type**: Feature  
**Priority**: High  
**Size**: L (5-7 days)  
**Dependencies**: NONE (Sprint 1 - fully parallel)

### Description
As an agent,  
I want to execute skills, run terminal commands securely, and persist memory to disk/GCS,  
So that I can perform actions and remember user preferences.

### Technical Context
- **Affected modules**: `src/skills/`, `src/core/terminal.py`, `src/core/memory.py` (new)
- **Design reference**:
  - Phase 1A: "Skills Module", "Terminal Executor", "Memory Module"
  - Phase 1B: "Skills Engine → Terminal Executor", "Agent Core → Memory Manager"
  - Phase 1C: "Security Design" (allowlist), "GCS Sync Strategy"
- **Key files to create**:
  - `src/skills/__init__.py`
  - `src/skills/loader.py` (skill discovery and parsing)
  - `src/skills/executor.py` (skill execution engine)
  - `src/core/terminal.py` (secure command execution)
  - `src/core/memory.py` (file-based memory with GCS sync)
  - `skills/file-ops/SKILL.md` (example skill docs)
  - `skills/file-ops/file_ops.py` (example skill implementation)
  - `skills/memory/SKILL.md`
  - `skills/memory/memory.py`
  - `tests/skills/test_loader.py`
  - `tests/skills/test_executor.py`
  - `tests/core/test_terminal.py`
  - `tests/core/test_memory.py`
- **Patterns to follow**: Plugin architecture, allowlist security, async I/O
- **Dependencies**: NONE (no dependencies on other Sprint 1 stories)
  - Note: Can depend on google-cloud-storage, PyYAML, etc.
- **FILE OWNERSHIP**: Story 3 imports from Story 2's `src/core/interfaces.py` - does NOT create competing interface file

### Integration Contracts

**Interfaces Used by This Story:**

```python
# Import from Story 2's interface definitions (Story 2 owns src/core/interfaces.py)
from src.core.interfaces import (
    SkillsEngineInterface,
    MemoryManagerInterface,
    SkillResult,
    ExecutionResult,
    Message
)
```

**Interfaces Implemented by This Story:**
- `SkillsEngineInterface` → Implemented by `SkillsEngine` class in `src/skills/executor.py`
- `MemoryManagerInterface` → Implemented by `MemoryManager` class in `src/core/memory.py`

**Note:** Story 3 does NOT define new interfaces. All interfaces are defined by Story 2 in `src/core/interfaces.py`. Story 3 only implements them.

**Integration Timeline:**
- Sprint 1: Skills Engine, Terminal Executor, Memory Manager fully functional with local filesystem
- Sprint 2: Integration story wires to Agent Core and tests end-to-end

### Acceptance Criteria

#### Skills Engine
- [ ] **Given** `./skills/` directory with 2+ skills, **When** loading, **Then** discover all skills
- [ ] **Given** skill with SKILL.md, **When** parsing, **Then** extract name, description, metadata
- [ ] **Given** skill execution request, **When** executing, **Then** call Terminal Executor with correct command/args
- [ ] **Given** two skills with same name, **When** loading, **Then** load first, log warning
- [ ] **Given** skill not found, **When** executing, **Then** raise SkillError with clear message

#### Terminal Executor Security
- [ ] **Given** command in ALLOWED_COMMANDS ("cat", "ls", "python", "uv"), **When** executing, **Then** allow execution
- [ ] **Given** command NOT in ALLOWED_COMMANDS ("rm", "curl"), **When** executing, **Then** raise SecurityError
- [ ] **Given** path in ALLOWED_PATHS ("./data/memory/"), **When** executing, **Then** allow execution
- [ ] **Given** path NOT in ALLOWED_PATHS ("/etc/passwd"), **When** executing, **Then** raise SecurityError
- [ ] **Given** command exceeds 30s timeout, **When** executing, **Then** raise TimeoutError and kill process
- [ ] **Given** command outputs > 1MB, **When** capturing, **Then** truncate to 1MB with warning

#### Memory Manager - Local Storage
- [ ] **Given** new conversation message, **When** writing, **Then** save to `./data/memory/CONVERSATION_HISTORY/{date}.md`
- [ ] **Given** user_id request, **When** reading history, **Then** return last 10 messages from disk
- [ ] **Given** new fact, **When** writing, **Then** save to `./data/memory/KNOWLEDGE_BASE/facts.json`
- [ ] **Given** fact key, **When** reading, **Then** retrieve from facts.json
- [ ] **Given** conversation > 90 days old, **When** cleanup runs, **Then** delete old files

#### Memory Manager - GCS Sync
- [ ] **Given** GCS_ENABLED=true, **When** writing conversation, **Then** async upload to GCS (non-blocking)
- [ ] **Given** GCS upload fails, **When** syncing, **Then** log error and continue with local cache
- [ ] **Given** startup with empty local cache, **When** initializing, **Then** download from GCS
- [ ] **Given** GCS download fails on startup, **When** initializing, **Then** use empty memory (fresh start)

#### Example Skills
- [ ] **Given** file-ops skill, **When** executing "read" action, **Then** read file and return contents
- [ ] **Given** file-ops skill, **When** executing "list" action, **Then** list directory contents
- [ ] **Given** memory skill, **When** executing "remember" action, **Then** save fact to memory
- [ ] **Given** memory skill, **When** executing "recall" action, **Then** retrieve fact from memory

#### Testing & Quality
- [ ] All interfaces implemented with complete docstrings and type hints
- [ ] Unit tests cover: skill loading, terminal security, memory persistence, GCS sync
- [ ] Integration tests use real local filesystem (`./test-data/`) with cleanup
- [ ] Mock GCS client for testing (or use local filesystem mock)
- [ ] 100% test coverage for security-critical paths (Terminal Executor allowlist)
- [ ] All tests pass independently (no dependencies on Story 1 or Story 2)

### Implementation Details

#### Skills Engine - Loader
```python
# src/skills/loader.py
from pathlib import Path
from typing import Dict, List
import yaml
import logging

logger = logging.getLogger(__name__)

class SkillLoader:
    """Discover and load skills from ./skills/ directory."""
    
    def __init__(self, skills_dir: str = "./skills"):
        self.skills_dir = Path(skills_dir)
        self.skills: Dict[str, dict] = {}
    
    def load_skills(self) -> Dict[str, dict]:
        """
        Discover all skills in skills_dir.
        Returns dict: {skill_name: {metadata, entry_point}}
        """
        logger.info(f"Loading skills from {self.skills_dir}")
        
        for skill_path in self.skills_dir.iterdir():
            if not skill_path.is_dir():
                continue
            
            skill_md = skill_path / "SKILL.md"
            if not skill_md.exists():
                logger.warning(f"Skipping {skill_path.name} - no SKILL.md found")
                continue
            
            # Parse SKILL.md (YAML frontmatter + Markdown)
            with open(skill_md) as f:
                content = f.read()
                # Extract YAML between --- delimiters
                if content.startswith("---"):
                    _, frontmatter, _ = content.split("---", 2)
                    metadata = yaml.safe_load(frontmatter)
                    
                    skill_name = metadata.get("name")
                    if skill_name in self.skills:
                        logger.warning(f"Duplicate skill name: {skill_name}. Using first.")
                        continue
                    
                    # Find Python entry point
                    entry_point = skill_path / f"{skill_name.replace('-', '_')}.py"
                    if not entry_point.exists():
                        logger.warning(f"Skill {skill_name} missing entry point: {entry_point}")
                        continue
                    
                    self.skills[skill_name] = {
                        "metadata": metadata,
                        "entry_point": str(entry_point),
                        "description": metadata.get("description", "")
                    }
                    logger.info(f"Loaded skill: {skill_name}")
        
        return self.skills
```

#### Skills Engine - Executor
```python
# src/skills/executor.py
from typing import Dict, Any
from .interfaces import SkillsEngineInterface, SkillResult
from .loader import SkillLoader
from src.core.terminal import TerminalExecutor
import logging

logger = logging.getLogger(__name__)

class SkillsEngine(SkillsEngineInterface):
    """Execute skills via Terminal Executor."""
    
    def __init__(self, terminal_executor: TerminalExecutor):
        self.terminal = terminal_executor
        self.loader = SkillLoader()
        self.skills = self.loader.load_skills()
    
    async def execute_skill(
        self, 
        skill_name: str, 
        args: Dict[str, Any]
    ) -> SkillResult:
        """Execute a skill by name."""
        if skill_name not in self.skills:
            return SkillResult(
                success=False,
                output="",
                error=f"Skill '{skill_name}' not found"
            )
        
        skill = self.skills[skill_name]
        entry_point = skill["entry_point"]
        
        # Convert args dict to command line args
        cmd_args = [entry_point]
        for key, value in args.items():
            cmd_args.extend([f"--{key}", str(value)])
        
        # Execute via Terminal Executor
        logger.info(f"Executing skill: {skill_name}", extra={
            "component": "skills_engine",
            "skill": skill_name,
            "args": args
        })
        
        result = await self.terminal.execute("python", cmd_args)
        
        if result.exit_code == 0:
            return SkillResult(success=True, output=result.stdout)
        else:
            return SkillResult(
                success=False,
                output=result.stdout,
                error=result.stderr
            )
    
    def list_skills(self) -> List[str]:
        """Return list of available skill names."""
        return list(self.skills.keys())
```

#### Terminal Executor - Secure Command Execution
```python
# src/core/terminal.py
import asyncio
import subprocess
from typing import List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

ALLOWED_COMMANDS = ["cat", "ls", "python", "uv"]
ALLOWED_PATHS = ["./data/memory/", "./skills/", "./test-data/"]

@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int

class SecurityError(Exception):
    """Raised when command or path not allowed."""
    pass

class TerminalExecutor:
    """Secure terminal command execution with allowlist."""
    
    async def execute(
        self,
        command: str,
        args: List[str],
        timeout: int = 30
    ) -> ExecutionResult:
        """
        Execute a terminal command securely.
        
        Raises:
            SecurityError: If command/path not allowed
            TimeoutError: If execution exceeds timeout
        """
        # Security check: command allowlist
        if command not in ALLOWED_COMMANDS:
            logger.error(f"Blocked command: {command}", extra={
                "component": "terminal_executor",
                "severity": "ERROR"
            })
            raise SecurityError(f"Command '{command}' not allowed")
        
        # Security check: path allowlist
        for arg in args:
            if arg.startswith("./") or arg.startswith("/"):
                # Check if path is in allowed directories
                if not any(arg.startswith(allowed) for allowed in ALLOWED_PATHS):
                    logger.error(f"Blocked path: {arg}", extra={
                        "component": "terminal_executor",
                        "severity": "ERROR"
                    })
                    raise SecurityError(f"Path '{arg}' not allowed")
        
        # Execute with timeout
        logger.info(f"Executing: {command} {' '.join(args)}", extra={
            "component": "terminal_executor",
            "command": command
        })
        
        try:
            process = await asyncio.create_subprocess_exec(
                command,
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            # Truncate output if > 1MB
            MAX_OUTPUT_SIZE = 1024 * 1024  # 1MB
            if len(stdout) > MAX_OUTPUT_SIZE:
                stdout = stdout[:MAX_OUTPUT_SIZE] + b"\n[Output truncated...]"
            
            return ExecutionResult(
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                exit_code=process.returncode or 0
            )
        
        except asyncio.TimeoutError:
            process.kill()
            logger.error(f"Command timeout: {command}", extra={
                "component": "terminal_executor",
                "timeout": timeout
            })
            raise TimeoutError(f"Command exceeded {timeout}s timeout")
```

#### Memory Manager - File-based with GCS Sync
```python
# src/core/memory.py
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

class MemoryManager:
    """File-based memory with GCS sync."""
    
    def __init__(
        self,
        memory_dir: str = "./data/memory",
        gcs_enabled: bool = False,
        gcs_bucket: Optional[str] = None
    ):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.gcs_enabled = gcs_enabled
        self.gcs_bucket = gcs_bucket
        
        # Create subdirectories
        (self.memory_dir / "CONVERSATION_HISTORY").mkdir(exist_ok=True)
        (self.memory_dir / "KNOWLEDGE_BASE").mkdir(exist_ok=True)
        
        # Initialize GCS client if enabled
        if self.gcs_enabled:
            from google.cloud import storage
            self.gcs_client = storage.Client()
        else:
            self.gcs_client = None
    
    async def write_conversation(
        self,
        user_id: str,
        role: str,
        content: str,
        trace_id: str
    ):
        """Write conversation message to daily file."""
        today = datetime.now().strftime("%Y-%m-%d")
        date_dir = self.memory_dir / "CONVERSATION_HISTORY" / today[:7]  # YYYY-MM
        date_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = date_dir / f"{today}.md"
        
        # Append message
        timestamp = datetime.now().strftime("%H:%M:%S")
        message = f"\n## {timestamp} - {role.capitalize()} (trace: {trace_id})\n{content}\n"
        
        with open(file_path, "a") as f:
            f.write(message)
        
        # Async GCS sync (non-blocking)
        if self.gcs_enabled:
            asyncio.create_task(self._sync_to_gcs(file_path))
    
    async def read_conversation_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> List:
        """Read last N messages from conversation history."""
        # For MVP: Read from today's file
        # Future: Implement cross-file reading for multi-day history
        today = datetime.now().strftime("%Y-%m-%d")
        date_dir = self.memory_dir / "CONVERSATION_HISTORY" / today[:7]
        file_path = date_dir / f"{today}.md"
        
        if not file_path.exists():
            return []
        
        # Simple parsing: extract last N messages
        # For Sprint 1: Return empty list (Agent Core will handle)
        # Sprint 2: Implement full parsing
        return []
    
    async def write_fact(self, user_id: str, key: str, value: str):
        """Write fact to knowledge base."""
        facts_file = self.memory_dir / "KNOWLEDGE_BASE" / "facts.json"
        
        # Load existing facts
        if facts_file.exists():
            with open(facts_file) as f:
                facts = json.load(f)
        else:
            facts = {"facts": {}}
        
        # Add/update fact
        facts["facts"][key] = {
            "value": value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Write back
        with open(facts_file, "w") as f:
            json.dump(facts, f, indent=2)
        
        # Async GCS sync
        if self.gcs_enabled:
            asyncio.create_task(self._sync_to_gcs(facts_file))
    
    async def read_fact(self, user_id: str, key: str) -> Optional[str]:
        """Read fact from knowledge base."""
        facts_file = self.memory_dir / "KNOWLEDGE_BASE" / "facts.json"
        
        if not facts_file.exists():
            return None
        
        with open(facts_file) as f:
            facts = json.load(f)
        
        fact = facts.get("facts", {}).get(key)
        return fact["value"] if fact else None
    
    async def _sync_to_gcs(self, file_path: Path):
        """Async upload to GCS (non-blocking)."""
        if not self.gcs_enabled:
            return
        
        try:
            blob_name = str(file_path.relative_to(self.memory_dir))
            bucket = self.gcs_client.bucket(self.gcs_bucket)
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(str(file_path))
            logger.info(f"Synced to GCS: {blob_name}")
        except Exception as e:
            logger.error(f"GCS sync failed: {e}", extra={
                "component": "memory_manager",
                "file": str(file_path)
            })
```

#### Example Skill: File Operations
```markdown
# skills/file-ops/SKILL.md
---
name: file-ops
description: "File operations (read, write, list)"
metadata:
  emonk:
    requires:
      bins: ["cat", "ls"]
      files: ["./data/memory/"]
---

# File Operations Skill

## Read File
```bash
python skills/file-ops/file_ops.py --action read --path ./data/memory/test.txt
```

## List Directory
```bash
python skills/file-ops/file_ops.py --action list --path ./data/memory/
```
```

```python
# skills/file-ops/file_ops.py
import argparse
import os

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=["read", "list"], required=True)
    parser.add_argument("--path", required=True)
    args = parser.parse_args()
    
    if args.action == "read":
        with open(args.path) as f:
            print(f.read())
    elif args.action == "list":
        for item in os.listdir(args.path):
            print(item)

if __name__ == "__main__":
    main()
```

### Out of Scope
- Integration with Agent Core (Story 4)
- Integration with Gateway (Story 4)
- Cloud Run deployment (Story 4)
- Advanced skill features (tool calling from within skills)
- Cron jobs (future phase)

### Notes for Developer
- **Security is critical**: Terminal Executor allowlist must be 100% secure - test thoroughly!
- **GCS sync**: Make it optional via `GCS_ENABLED` env var (false for local dev)
- **Skills**: Start with 2 simple example skills (file-ops, memory)
- **Testing**: Use `./test-data/` directory for integration tests (cleanup after each test)
- **Interface clarity**: Your interfaces are consumed by Agent Core (Story 2)

---

## Story 4: Integration & Deployment

**Repository**: emonk  
**Type**: Integration  
**Priority**: High  
**Size**: S (2-3 days)  
**Dependencies**: Stories 1, 2, 3 must be completed

### Description
As the development team,  
I want to wire all components together and deploy to Cloud Run,  
So that the agent is fully functional in production.

### Technical Context
- **Affected modules**: All modules (integration layer)
- **Design reference**: All Phase 1 docs
- **Key files to create/modify**:
  - `src/__init__.py` (main entry point)
  - `src/main.py` (wire all components)
  - `Dockerfile` (Cloud Run deployment)
  - `requirements.txt` (dependencies)
  - `.env.example` (env var template)
  - `tests/integration/test_e2e.py` (end-to-end tests)
  - `tests/integration/test_user_journeys.py` (critical flows)
- **Patterns to follow**: Dependency injection, env var configuration
- **Dependencies**: Stories 1, 2, 3 complete

### Acceptance Criteria

#### Component Wiring
- [ ] **Given** all modules (Gateway, Agent Core, Skills Engine, Memory Manager), **When** starting app, **Then** wire real implementations (not mocks)
- [ ] **Given** Gateway receives webhook, **When** processing, **Then** call real Agent Core (not MockAgentCore)
- [ ] **Given** Agent Core processes message, **When** executing skills, **Then** call real Skills Engine (not MockSkillsEngine)
- [ ] **Given** Agent Core needs memory, **When** reading/writing, **Then** call real Memory Manager (not MockMemoryManager)
- [ ] **Given** Agent Core calls LLM, **When** processing, **Then** use real Vertex AI client (not MockVertexAI)

#### End-to-End Tests
- [ ] **Given** test webhook (remember Python), **When** POST to /webhook, **Then** fact saved to disk and response returned
- [ ] **Given** test webhook (recall preference), **When** POST to /webhook, **Then** fact retrieved from memory and returned in response
- [ ] **Given** test webhook (list files), **When** POST to /webhook, **Then** Terminal Executor called and file list returned

#### Deployment
- [ ] **Given** Dockerfile, **When** building, **Then** create runnable Cloud Run image
- [ ] **Given** Cloud Run deployment, **When** starting, **Then** health check returns 200
- [ ] **Given** Cloud Run deployment, **When** sending test message, **Then** agent responds correctly
- [ ] **Given** Cloud Run deployment, **When** checking logs, **Then** structured JSON logs visible in Cloud Logging

#### Configuration
- [ ] **Given** `.env.example`, **When** copying to `.env`, **Then** all required env vars documented
- [ ] **Given** missing required env var, **When** starting app, **Then** fail fast with clear error message
- [ ] **Given** GCS_ENABLED=false, **When** running locally, **Then** memory works with local files only

### Implementation Details

#### Main Application Entry Point
```python
# src/main.py
import os
from src.gateway.server import app
from src.core.agent import AgentCore
from src.core.llm_client import LLMClient
from src.skills.executor import SkillsEngine
from src.core.terminal import TerminalExecutor
from src.core.memory import MemoryManager
import logging

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "component": "%(name)s", "message": "%(message)s"}'
)

def create_app():
    """Wire all components and return FastAPI app."""
    # Validate required env vars
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS env var required")
    if not os.getenv("VERTEX_AI_PROJECT_ID"):
        raise RuntimeError("VERTEX_AI_PROJECT_ID env var required")
    
    # Create real implementations (not mocks!)
    terminal_executor = TerminalExecutor()
    skills_engine = SkillsEngine(terminal_executor)
    
    memory_manager = MemoryManager(
        memory_dir=os.getenv("MEMORY_DIR", "./data/memory"),
        gcs_enabled=os.getenv("GCS_ENABLED", "false").lower() == "true",
        gcs_bucket=os.getenv("GCS_MEMORY_BUCKET")
    )
    
    # Create real Vertex AI client (Story 4 adds this - Sprint 1 used mocks)
    from google.cloud import aiplatform
    aiplatform.init(
        project=os.getenv("VERTEX_AI_PROJECT_ID"),
        location=os.getenv("VERTEX_AI_LOCATION", "us-central1")
    )
    # Use LangChain's Vertex AI wrapper for LangGraph compatibility
    from langchain_google_vertexai import ChatVertexAI
    vertex_llm = ChatVertexAI(model_name="gemini-2.0-flash-exp")
    llm_client = LLMClient(vertex_llm)
    
    # Create Agent Core with real dependencies
    agent_core = AgentCore(llm_client, skills_engine, memory_manager)
    
    # Inject into Gateway
    from src.gateway import server
    server.agent_core = agent_core
    
    return app

if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
```

#### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ src/
COPY skills/ skills/

# Create memory directory
RUN mkdir -p /app/data/memory

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Run application
CMD ["python", "-m", "src.main"]
```

#### End-to-End Test
```python
# tests/integration/test_e2e.py
import pytest
from fastapi.testclient import TestClient
from src.main import create_app
import os

@pytest.fixture
def client():
    os.environ["GCS_ENABLED"] = "false"
    os.environ["ALLOWED_USERS"] = "test@example.com"
    os.environ["MEMORY_DIR"] = "./test-data/memory"
    app = create_app()
    return TestClient(app)

def test_e2e_remember_fact(client):
    """Test remembering a fact end-to-end."""
    webhook_payload = {
        "message": {
            "sender": {"email": "test@example.com"},
            "text": "Remember that I prefer Python"
        }
    }
    
    response = client.post("/webhook", json=webhook_payload)
    assert response.status_code == 200
    assert "Python" in response.json()["text"]

def test_e2e_recall_fact(client):
    """Test recalling a fact end-to-end."""
    # First remember
    client.post("/webhook", json={
        "message": {
            "sender": {"email": "test@example.com"},
            "text": "Remember that I prefer Python"
        }
    })
    
    # Then recall
    response = client.post("/webhook", json={
        "message": {
            "sender": {"email": "test@example.com"},
            "text": "What's my preferred language?"
        }
    })
    assert response.status_code == 200
    assert "Python" in response.json()["text"]
```

### Out of Scope
- Advanced deployment (CI/CD pipeline)
- Multi-region deployment
- Load testing
- Production monitoring dashboard (use Cloud Console for MVP)

### Notes for Developer
- **Remove all mocks**: Replace MockAgentCore, MockSkillsEngine, MockMemoryManager with real implementations
- **Test locally first**: Use `.env` file with `GCS_ENABLED=false` before Cloud Run
- **Deployment checklist**: Follow Phase 1C deployment checklist
- **Verify end-to-end**: Send real Google Chat message after deployment

---

## File Ownership Summary

To ensure ZERO merge conflicts during parallel development:

| Story | Files Owned | Interface Responsibilities |
|-------|-------------|---------------------------|
| **Story 1** | `src/gateway/*` | Creates local `AgentCoreInterface` copy in `src/gateway/interfaces.py` (removed in Story 4) |
| **Story 2** | `src/core/agent.py`<br>`src/core/llm_client.py`<br>**`src/core/interfaces.py`** | **Owns ALL shared interfaces**<br>Defines: Message, SkillResult, ExecutionResult, SkillsEngineInterface, MemoryManagerInterface, AgentCoreInterface |
| **Story 3** | `src/skills/*`<br>`src/core/terminal.py`<br>`src/core/memory.py` | Imports from Story 2's `src/core/interfaces.py`<br>Implements: SkillsEngineInterface, MemoryManagerInterface |
| **Story 4** | `src/main.py`<br>`Dockerfile`<br>`requirements.txt` | Wires real implementations<br>Consolidates interfaces (removes Gateway's local copy) |

**Key Rule:** Story 2 owns `src/core/interfaces.py` - ALL developers import from this file.

---

## Summary

### Sprint 1 (Parallel - No dependencies between stories)
- **Story 1**: Gateway Module (Dev 1) - 3-5 days
- **Story 2**: Agent Core + LLM Client (Dev 2) - 3-5 days
- **Story 3**: Skills Engine + Terminal Executor + Memory Manager (Dev 3) - 5-7 days

**All developers start Day 1. No waiting. No file conflicts.**

### Sprint 2 (Sequential - requires Sprint 1 complete)
- **Story 4**: Integration & Deployment

### Total Timeline
- **Sprint 1**: ~5-7 days (parallel)
- **Sprint 2**: Variable (integration complexity)
- **Total**: Depends on integration effort

---

## Success Criteria

✅ All 3 developers can start Day 1 without waiting  
✅ Each story touches completely different files  
✅ All interfaces defined upfront (clear contracts)  
✅ Each story fully testable with mocks  
✅ Integration is straightforward (just wire real implementations)  
✅ Full test coverage (unit + integration + e2e)  
✅ Production deployment on Cloud Run  
✅ Real Google Chat integration working

---

**Status**: Ready for Phase 3 (Code Spec) - Select a story to implement first!
